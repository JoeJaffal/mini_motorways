"""Generate network-independent evaluation requests and account for SUMO trips."""

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree


def generate_requests(endpoint_ids, *, seed, count, departure_window):
    """Sample uniformly over ordered distinct endpoint pairs."""
    endpoints = sorted(endpoint_ids)
    if (len(endpoints) < 2 or len(set(endpoints)) != len(endpoints)
            or any(not isinstance(endpoint, str) or not endpoint for endpoint in endpoints)):
        raise ValueError("Expected at least two unique, nonempty endpoint IDs")
    if count <= 0 or departure_window <= 0:
        raise ValueError("Count and departure window must be positive")

    rng = random.Random(seed)
    requests = []
    for index in range(count):
        origin, destination = rng.sample(endpoints, 2)
        requests.append({
            "id": f"trip-{index}",
            "origin": origin,
            "destination": destination,
            "depart": rng.randrange(departure_window),
        })
    requests.sort(key=lambda request: (request["depart"], request["id"]))
    return {
        "generator": "uniform-distinct-endpoints-v1",
        "seed": seed,
        "departure_window_seconds": departure_window,
        "requests": requests,
    }


def account_requests(manifest, unroutable_ids, tripinfo_path):
    """Join SUMO tripinfo (with unfinished and undeparted output enabled) to requests."""
    requests = manifest["requests"]
    requested_ids = {request["id"] for request in requests}
    failures = set(unroutable_ids)
    if len(requested_ids) != len(requests) or failures - requested_ids:
        raise ValueError("Duplicate request IDs or unknown routing failure IDs")

    observations = {}
    root = ElementTree.parse(tripinfo_path).getroot()
    if root.tag != "tripinfos":
        raise ValueError(f"Expected SUMO tripinfos output, got {root.tag}")
    for trip in root.findall("tripinfo"):
        trip_id = trip.attrib["id"]
        if trip_id not in requested_ids or trip_id in failures or trip_id in observations:
            raise ValueError(f"Unexpected or duplicate SUMO trip ID: {trip_id}")
        observations[trip_id] = trip.attrib

    missing = requested_ids - failures - observations.keys()
    if missing:
        raise ValueError(f"SUMO output is missing {len(missing)} routed requests")

    outcomes = []
    for request in requests:
        trip_id = request["id"]
        duration = None
        if trip_id in failures:
            status = "unroutable"
        else:
            trip = observations[trip_id]
            if float(trip["depart"]) < 0:
                status = "never_departed"
            elif float(trip["arrival"]) < 0:
                status = "unfinished"
            else:
                status = "completed"
                duration = float(trip["duration"])
        outcomes.append({**request, "status": status, "duration_seconds": duration})
    return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("endpoints", type=Path, help="JSON array of stable endpoint IDs")
    generate.add_argument("output", type=Path)
    generate.add_argument("--seed", type=int, required=True)
    generate.add_argument("--count", type=int, required=True)
    generate.add_argument("--departure-window", type=int, required=True)
    account = commands.add_parser("account")
    account.add_argument("manifest", type=Path)
    account.add_argument("unroutable", type=Path, help="JSON array of routing failure IDs")
    account.add_argument("tripinfo", type=Path)
    account.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "generate":
        manifest = generate_requests(
            json.loads(args.endpoints.read_text(encoding="utf-8")),
            seed=args.seed, count=args.count, departure_window=args.departure_window,
        )
        args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    else:
        outcomes = account_requests(
            json.loads(args.manifest.read_text(encoding="utf-8")),
            json.loads(args.unroutable.read_text(encoding="utf-8")),
            args.tripinfo,
        )
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            fields = ["id", "origin", "destination", "depart", "status", "duration_seconds"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(outcomes)
        print(json.dumps(Counter(row["status"] for row in outcomes), sort_keys=True))


if __name__ == "__main__":
    main()

"""gp-8 probe: play (policy file, city, seed) games and report trips, the upgrade types taken, the placements sent
and the full command trace hash (for identity gates). Not a measurement; smoke and calibration only.

  PY -m evolved_rules.ops.probe_gp8 --policy NAME=FILE [...] --cities LosAngeles,Tokyo --seeds 5001-5002
        [--workers 3] [--randomness keyed] --out OUT.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from evolved_rules.host import RANDOMNESS_ENV, check_randomness, check_scenario


def _job(args):
    name, text, city, seed, cap = args
    from evolved_rules import agent, executor
    from evolved_rules.gp import TreePolicy
    from evolved_rules.host import Host
    taken: dict[int, int] = {}
    orig_take, orig_place = agent.take_offer, agent.place_item
    trace = hashlib.sha256()
    placed: dict[int, int] = {}

    offered: dict[int, int] = {}

    def take(session, choice):
        for x in session.state.offers:
            offered[x.type] = offered.get(x.type, 0) + 1
        o = next(o for o in session.state.offers if o.index == choice)
        taken[o.type] = taken.get(o.type, 0) + 1
        return orig_take(session, choice)

    def place(session, pc):
        placed[pc.tool] = placed.get(pc.tool, 0) + 1
        return orig_place(session, pc)

    agent.take_offer, agent.place_item = take, place
    host = Host()
    try:
        r = agent.play_game(host, seed, TreePolicy(text), cap_s=cap, record=True, scenario=city)
    finally:
        host.close()
        agent.take_offer, agent.place_item = orig_take, orig_place
    for a in r.recording["actions"]:
        trace.update(json.dumps(a, sort_keys=True).encode())
    return {"policy": name, "city": city, "seed": seed, "trips": r.trips, "seconds": r.seconds,
            "commands": r.commands, "rejected": r.rejected_actions, "offers_taken": taken, "offered": offered, "placed": placed,
            "trace": trace.hexdigest()[:16], "simulator_version": r.simulator_version}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", action="append", required=True)
    p.add_argument("--cities", required=True)
    p.add_argument("--seeds", required=True)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--randomness", default="keyed")
    p.add_argument("--cap", type=float, default=3600.0)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    os.environ[RANDOMNESS_ENV] = check_randomness(a.randomness)
    lo, hi = (int(v) for v in a.seeds.split("-"))
    pols = [(n, Path(f).read_text(encoding="utf-8")) for n, f in (s.split("=", 1) for s in a.policy)]
    jobs = [(n, t, check_scenario(c), s, a.cap) for c in a.cities.split(",") for s in range(lo, hi + 1)
            for n, t in pols]
    with ProcessPoolExecutor(a.workers) as ex, open(a.out, "w", encoding="utf-8") as f:
        for r in ex.map(_job, jobs):
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(json.dumps(r), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

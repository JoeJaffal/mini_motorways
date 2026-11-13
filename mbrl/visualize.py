"""Watch a checkpoint live, or turn an existing action trace into a visual replay."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path
import random
import time

from environment import (HOST_DLL, Host, MAPS, SnapshotBranch, TrafficEnv, ProtocolError,
                         DEFAULT_FAILURE_PENALTY, DEFAULT_UNANSWERED_PENALTY,
                         DEFAULT_MODIFICATION_PENALTY, DEFAULT_OVERCROWDING_PENALTY)
from live_view import LiveViewer, UnityLiveViewer, add_viewer_arguments
from parallel_search import SearchPool, add_search_arguments, configure_search

REQUEST_FIELDS = ("command", "tool", "x", "y", "toX", "toY", "id", "choice")
COMMANDS = {"wait", "draw", "build", "connect", "driveway", "motorway", "editMotorway", "removeMotorway", "upgrade"}


def replay(host, record, viewer):
    """Re-run only recorded gameplay commands, checking every decision boundary."""
    if (record.get("schemaVersion") != 1 or record.get("version") != "OriginalReference"
            or record.get("scenario") not in MAPS or record.get("variation") != "SameMap"
            or not record.get("actions")):
        raise ValueError("Expected a nonempty OriginalReference mbrl action trace")
    state = host.call(command="reset", version="OriginalReference", scenario=record["scenario"],
                      seed=record["seed"], variation="SameMap")["observation"]
    viewer("reset", state, scenario=record["scenario"], seed=record["seed"],
           weights=record.get("rewardWeights"), mode="Recorded run", source=record.get("source", ""))
    for index, action in enumerate(record["actions"]):
        request = {key:action[key] for key in REQUEST_FIELDS if key in action}
        if request.get("command") not in COMMANDS:
            raise ValueError(f"Unsupported gameplay command at decision {index+1}")
        accepted = True if request["command"] == "wait" else bool(host.call(**request)["accepted"])
        # Old traces say 20 ticks even for the final fractional horizon. Use the
        # actual recorded interval so replay also handles externally capped runs.
        interval = float(action["afterTime"])-state["time"]
        ticks = round(interval/.05)
        if ticks < 0 or ticks > 100000 or not math.isclose(interval, ticks*.05, abs_tol=1e-6):
            raise ValueError(f"Invalid time interval at decision {index+1}")
        state = host.call(command="step", ticks=ticks)["observation"]
        checks = [(accepted == action["accepted"], "acceptance"),
                  (math.isclose(state["time"], action["afterTime"], abs_tol=1e-6), "time"),
                  (state["tripsCompleted"] == action["afterTrips"], "trips")]
        for field, observed in (("afterInventory", "inventory"), ("afterTripsDispatched", "tripsDispatched")):
            if field in action:
                checks.append((state[observed] == action[field], observed))
        for matches, label in checks:
            if not matches:
                raise ProtocolError(f"Replay diverged at decision {index+1}: {label}. Use the matching simulator build.")
        viewer("main", state, decision=action)
    if (state["tripsCompleted"] != record["score"]
            or not math.isclose(state["time"], record["duration"], abs_tol=1e-6)
            or bool(state["failed"]) != record["terminated"]):
        raise ProtocolError("Replay final outcome diverged")
    viewer("finish", state, result={"trips":state["tripsCompleted"], "time":state["time"],
           "terminated":state["failed"], "replayVerified":True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--checkpoint", type=Path)
    source.add_argument("--trace", type=Path)
    source.add_argument("--heuristic", action="store_true", help="Viewer smoke/demo run without a checkpoint")
    parser.add_argument("--map", choices=MAPS, default="DarEsSalaam", help="London explicitly accesses held-out test data")
    parser.add_argument("--seed", type=int, default=200000)
    parser.add_argument("--simulations", type=int, default=0, help="Zero: policy only; positive: MCTS budget")
    parser.add_argument("--search-depth", type=int, default=4)
    parser.add_argument("--cap-seconds", type=float, default=1800,
                        help="Maximum simulated seconds for a new run (default: 1800); ignored for saved traces")
    parser.add_argument("--dotnet", default="dotnet")
    parser.add_argument("--host-dll", type=Path, default=HOST_DLL, help="Use the same headless build as training")
    parser.add_argument("--output", type=Path, default=Path("output/mbrl/visualization/run.html"))
    parser.add_argument("--no-live", dest="live", action="store_false", help="Only write a portable HTML replay")
    parser.add_argument("--exit-when-done", action="store_true", help="Stop serving after saving the replay")
    add_viewer_arguments(parser)
    add_search_arguments(parser)
    parser.set_defaults(live=True)
    args = parser.parse_args()
    try:
        configure_search(args)
    except ValueError as exc:
        parser.error(str(exc))
    if args.simulations < 0 or args.search_depth < 1 or (args.cap_seconds is not None and
            (not math.isfinite(args.cap_seconds) or args.cap_seconds < .05)):
        parser.error("Use nonnegative simulations, positive search depth and a horizon of at least .05 seconds")
    if not 0 <= args.viewer_port <= 65535 or any(not math.isfinite(v) or not 0 <= v <= 5
                                               for v in (args.view_delay,args.search_view_delay)):
        parser.error("Invalid viewer port or delay (expected 0 to 5 seconds)")
    if args.view_mcts and (args.trace or args.heuristic or args.simulations == 0):
        parser.error("--view-mcts needs --checkpoint and a positive --simulations budget")
    if args.output.suffix.lower() != ".html":
        parser.error("--output must be an .html file")
    if args.live and args.viewer == "unity":
        viewer = UnityLiveViewer(executable=args.unity_exe,directory=args.output.parent/(args.output.stem+"-live"),
                                 delay=args.view_delay,search_delay=args.search_view_delay,show_search=args.view_mcts)
    else:
        viewer = LiveViewer(args.viewer_port, args.view_delay if args.live else 0,
                            args.search_view_delay if args.live else 0, args.view_mcts)
    with ExitStack() as stack:
        if args.live:
            stack.enter_context(viewer)
        try:
            with Host(dotnet=args.dotnet,dll=args.host_dll) as host:
                if args.trace:
                    replay(host, json.loads(args.trace.read_text(encoding="utf-8")), viewer)
                else:
                    import torch
                    from alphazero import Network
                    from proposals import Cooldowns
                    from train import run_episode
                    config, model = {}, None
                    if args.checkpoint:
                        state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
                        config = state["config"]
                        model = Network(value_scale=config.get("valueScale",10))
                        model.load_compatible_state_dict(state["model"])
                        model.eval()
                    env = TrafficEnv(host, cap_seconds=args.cap_seconds,
                                     alpha=config.get("alpha",.05), lam=config.get("lambdaCost",DEFAULT_MODIFICATION_PENALTY),
                                     beta=config.get("betaCongestion",0),
                                     failure_penalty=config.get("failurePenalty",DEFAULT_FAILURE_PENALTY),
                                     unanswered_penalty=config.get("unansweredPenalty",DEFAULT_UNANSWERED_PENALTY),
                                     overcrowding_penalty=config.get("overcrowdingPenalty",
                                         0 if args.checkpoint else DEFAULT_OVERCROWDING_PENALTY),
                                     trip_reward=config.get("tripReward",1.0 if args.checkpoint else 10.0),
                                     clear_trip_bonus=config.get("clearTripBonus",0. if args.checkpoint else .1),
                                     congestion_fraction_penalty=config.get("congestionFractionPenalty",0. if args.checkpoint else .02),
                                     congestion_wait_threshold=config.get("congestionWaitThreshold",2.))
                    with Host(dotnet=args.dotnet,dll=args.host_dll) as other:
                        with SearchPool(SnapshotBranch(other,env),args.search_workers) as branch:
                            _, result, record = run_episode(env,branch,args.map,args.seed,
                                model,args.simulations,random.Random(args.seed+900000),False,
                                baseline=args.heuristic,collect_samples=False,depth=args.search_depth,
                                safety=config.get("safety",True),cooldowns=Cooldowns(**config.get("cooldowns",{})),
                                discount=config.get("discount",.999),observer=viewer)
                    if args.checkpoint:
                        record["checkpoint"] = str(args.checkpoint)
                        record["checkpointSha256"] = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
                    args.output.parent.mkdir(parents=True,exist_ok=True)
                    args.output.with_suffix(".trace.json").write_text(json.dumps(record),encoding="utf-8")
                    print(json.dumps(result),flush=True)
        except KeyboardInterrupt:
            viewer.session["status"] = "Interrupted (partial run)"
        except Exception:
            viewer.session["status"] = "Failed (partial run; replay not verified)"
            viewer.save(args.output)
            raise
        finally:
            viewer.save(args.output)
            print(f"Visual replay saved: {args.output.resolve()}",flush=True)
        if args.live and args.viewer == "browser" and not args.exit_when_done:
            print("Viewer remains open for inspection. Ctrl+C closes the server; the HTML replay is saved.",flush=True)
            try:
                while True:
                    time.sleep(.25)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()

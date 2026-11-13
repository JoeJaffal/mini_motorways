"""Run goal-proposal baseline without PyTorch, before learner integration."""

from __future__ import annotations

import argparse
import json

from actions import candidates
from proposals import ActionGuard, Cooldowns, proposals
from environment import HOST_DLL, Host, TrafficEnv, material_use
from protocol import TRAIN_CITIES, TRAIN_SEED_BASE, VALIDATION_CITY, VALIDATION_SEED_BASE


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", choices=("train", "validation") + TRAIN_CITIES +
                        (VALIDATION_CITY,), default="train")
    parser.add_argument("--seed", type=int, help="Default: 100000 for training cities, 200000 for validation")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--cap-seconds", type=float, default=1800)
    parser.add_argument("--dotnet", default="dotnet")
    parser.add_argument("--raw-proposals",action="store_true",help="Disable native preflight and cooldowns for a control")
    parser.add_argument("--driveway-cooldown",type=float,default=20)
    parser.add_argument("--motorway-cooldown",type=float,default=30)
    args = parser.parse_args()
    if args.episodes < 1:
        parser.error("episodes must be positive")
    if args.cap_seconds <= 0:
        parser.error("cap-seconds must be positive")
    if not HOST_DLL.is_file():
        parser.error("Headless host missing; run dotnet build simulation/Headless first")
    maps = TRAIN_CITIES if args.map == "train" else (
        (VALIDATION_CITY,) if args.map == "validation" else (args.map,))
    seed_start = args.seed if args.seed is not None else (
        VALIDATION_SEED_BASE if args.map in ("validation", VALIDATION_CITY) else TRAIN_SEED_BASE)
    with Host(dotnet=args.dotnet) as host:
        env = TrafficEnv(host, cap_seconds=args.cap_seconds)
        for scenario in maps:
            for seed in range(seed_start, seed_start + args.episodes):
                observation = env.reset(scenario, seed)
                invalid = 0
                guard=ActionGuard(Cooldowns(driveway=args.driveway_cooldown,motorway=args.motorway_cooldown))
                waiting, modifications, congestion = 0.0, 0.0, 0.0
                decisions = 0
                while not env.done:
                    available = candidates(observation) if args.raw_proposals else proposals(observation,host,guard)
                    action = max(enumerate(available), key=lambda pair: (pair[1].priority, -pair[0]))[1]
                    transition = env.step(action.request)
                    guard.record(observation,transition.observation,action.request,transition.accepted)
                    invalid += not transition.accepted
                    waiting += transition.components["waitingSeconds"]
                    modifications += transition.components["modificationCost"]
                    active = [v for v in transition.observation["vehicles"] if v["stage"] not in ("Home", "Parking")]
                    congestion += sum(v["waiting"] > 0 for v in active) / max(1, len(active))
                    decisions += 1
                    observation = transition.observation
                print(json.dumps({
                    "policy": "goal-baseline", "map": scenario, "seed": seed,
                    "time": observation["time"], "trips": observation["tripsCompleted"],
                    "meanWaiting": observation["meanWaiting"],
                    "materialsUsed": material_use(observation), "invalidActions": invalid,
                    "waitingSeconds": waiting, "modificationCost": modifications,
                    "tripsDispatched": observation["tripsDispatched"],
                    "completionRate": observation["tripsCompleted"] / max(1, observation["tripsDispatched"]),
                    "congestion": congestion / max(1, decisions),
                    "congestionSeconds": observation["congestionSeconds"],
                    "reversals":guard.reversals+guard.motorway_reversals,
                    "drivewayChanges":guard.driveway_changes,"motorwayChanges":guard.motorway_changes,
                    "terminated": observation["failed"], "truncated": not observation["failed"],
                }), flush=True)


if __name__ == "__main__":
    main()

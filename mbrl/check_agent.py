"""Focused AlphaZero feature, reward, snapshot and route checks.

Run from the repository root after building Headless:
    python mbrl/check_agent.py --dotnet .\\tmp\\dotnet\\dotnet.exe
"""

from __future__ import annotations

import argparse
import copy

import numpy as np

from actions import _features, candidate_matrix, candidates, reachable_pairs
from alphazero import Sample, finish_episode
from environment import Host, TrafficEnv, modification_cost, visible_grid, visible_scalar
from smoke import observation


def synthetic_checks() -> None:
    obs = observation()
    obs["upgradeChoices"] = [
        {"type": 1, "amount": 1, "roads": 20},
        {"type": 3, "amount": 2, "roads": 20},
    ]
    items = candidates(obs)
    features, _ = candidate_matrix(items)
    upgrades = [i for i, c in enumerate(items) if c.request["command"] == "upgrade"]
    assert len(upgrades) == 2 and not np.array_equal(features[upgrades[0]], features[upgrades[1]])
    assert _features(4, (5, 5), tool="Road") != _features(4, (5, 5), tool="TrafficLight")
    original_grid, original_scalar = visible_grid(obs), visible_scalar(obs)
    changed = copy.deepcopy(obs)
    changed["buildings"][0]["drivewayDirection"] = 2
    changed["motorways"] = [{"id": 4, "start": {"x": 5, "y": 5},
                              "end": {"x": 10, "y": 5}, "pendingRemoval": False}]
    changed["upgradeChoices"][0]["type"] = 2
    assert not np.array_equal(visible_grid(changed), original_grid)
    assert not np.array_equal(visible_scalar(changed), original_scalar)
    after = copy.deepcopy(obs)
    after["infrastructure"][5 * 50 + 5] = 1
    after["connections"][5 * 50 + 5] = 1
    after["connections"][5 * 50 + 6] = 16
    after["buildings"][0]["drivewayDirection"] = 2
    assert modification_cost(obs, after) == 3
    samples = [Sample(None, None, None, None, None, 1),
               Sample(None, None, None, None, None, 2)]
    finish_episode(samples, discount=0.5, bootstrap_value=3)
    assert samples[1].value_target == 3.5 and samples[0].value_target == 2.75

    class RewardHost:
        def __init__(self):
            self.obs = observation()

        def call(self, **request):
            command = request["command"]
            if command == "reset":
                self.obs = observation()
            elif command == "build":
                self.obs = copy.deepcopy(self.obs)
                self.obs["infrastructure"][5 * 50 + 5] = 1
            elif command == "step":
                self.obs = copy.deepcopy(self.obs)
                self.obs["time"] += 1
                self.obs["tripsCompleted"] += 1
                self.obs["waitingSeconds"] += 2
                self.obs["congestionSeconds"] += 0.5
            return {"accepted": True, "terminated": False, "truncated": False,
                    "spendingDelta": 0, "observation": self.obs}

    env = TrafficEnv(RewardHost(), cap_seconds=2, alpha=0.05, lam=0.005, beta=0.02)
    env.reset("LosAngeles", 42)
    transition = env.step({"command": "build", "tool": "Road", "x": 5, "y": 5})
    assert transition.components["trips"] == 1
    assert transition.components["waitingSeconds"] == 2
    assert transition.components["congestionSeconds"] == 0.5
    assert transition.components["modificationCost"] == 1
    assert transition.components["unansweredRequestSeconds"] == 3
    assert transition.components["failure"] == 0
    assert abs(transition.reward - 9.955) < 1e-9


def host_checks(dotnet: str) -> None:
    with Host(dotnet=dotnet) as host:
        host.call(command="reset", version="OriginalReference", scenario="LosAngeles", seed=42)
        host.call(command="reference")
        root = host.call(command="step", ticks=1000)["observation"]
        host.call(command="saveSnapshot", id=7)
        forward = host.call(command="step", ticks=200)["observation"]
        restored = host.call(command="loadSnapshot", id=7)["observation"]
        assert restored == root
        repeated = host.call(command="step", ticks=200)["observation"]
        assert repeated == forward, "Snapshot did not preserve vehicles or random state"
        host.call(command="loadSnapshot", id=7)
        future = host.call(command="forkFuture", seed=123456)["observation"]
        assert future["time"] == root["time"]
        assert future["infrastructure"] == root["infrastructure"]
        assert future["vehicles"] == root["vehicles"]
        assert future["scheduledSpawns"] != root["scheduledSpawns"]
        assert np.array_equal(visible_grid(future), visible_grid(root))
        assert np.array_equal(visible_scalar(future), visible_scalar(root))

        env = TrafficEnv(host, cap_seconds=120)
        current = env.reset("LosAngeles", 100000)
        invalid = 0
        rejected = []
        while not env.done:
            choice = max(enumerate(candidates(current)), key=lambda pair: (pair[1].priority, -pair[0]))[1]
            transition = env.step(choice.request)
            invalid += not transition.accepted
            if not transition.accepted and len(rejected) < 5:
                a, b = choice.request["x"], choice.request["y"]
                x, y = choice.request["toX"], choice.request["toY"]
                rejected.append((current["time"], choice.request,
                                 current["terrain"][y*50+x], current["infrastructure"][y*50+x],
                                 current["inventory"],
                                 current["connections"][17*50+21],current["connections"][16*50+20],
                                 [(z["id"], z["drivewayDirection"]) for z in current["buildings"]
                                  if z["isHouse"] and z["cell"] == {"x": a, "y": b}]))
            current = transition.observation
        assert current["tripsDispatched"] > 0 and current["tripsCompleted"] > 0
        assert reachable_pairs(current) > 0
        assert invalid == 0, rejected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet", default="dotnet")
    args = parser.parse_args()
    synthetic_checks()
    host_checks(args.dotnet)
    print("PASS: distinct action/state features, rewards, future isolation, snapshot replay, route completion")


if __name__ == "__main__":
    main()

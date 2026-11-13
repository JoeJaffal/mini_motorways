"""Dependency-light checks for goal generation and the episode contract."""

from __future__ import annotations

import copy

import numpy as np

from actions import candidate_matrix, candidates
from environment import ProtocolError, ReplayBranch, TrafficEnv, material_use, visible_grid, visible_scalar
from protocol import (TEST_CITY, TRAIN_CITIES, VALIDATION_CITY, aggregate_rank,
                      test_cases, training_case, validation_cases, SingleCitySeeds)


def observation(time=0.0, trips=0):
    size = 50 * 30
    house = {"id": 0, "isHouse": True, "color": 1, "cell": {"x": 4, "y": 5},
             "entrance": {"x": 4, "y": 5}, "width": 1, "height": 1,
             "drivewayDirection": 0, "demand": 0, "reserved": 0, "overcrowdedFor": 0}
    shop = {"id": 1, "isHouse": False, "color": 1, "cell": {"x": 12, "y": 5},
            "entrance": {"x": 12, "y": 5}, "width": 1, "height": 1,
            "entrances": [{"x": 12, "y": 5}], "entranceDirections": [4],
            "drivewayDirection": 4, "demand": 3, "reserved": 0, "overcrowdedFor": 2, "demandCapacity": 6}
    return {
        "version": "OriginalReference", "unlimitedConstruction": False,
        "width": 50, "height": 30, "time": time, "tripsCompleted": trips, "tripsDispatched": trips,
        "meanWaiting": 0.0, "waitingSeconds": 0.0, "congestionSeconds": 0.0,
        "playableXMin": 0, "playableXMax": 50,
        "playableYMin": 0, "playableYMax": 30,
        "terrain": [0] * size, "infrastructure": [0] * size,
        "connections": [0] * size, "buildingColors": [-1] * size,
        "buildingKinds": [0] * size, "demand": [0] * size,
        "reservations": [0] * size, "pendingRemovals": [0] * size,
        "inventory": [20, 1, 0, 1, 1, 0], "upgradeChoices": [],
        "buildings": [house, shop], "vehicles": [], "motorways": [], "railLines": [],
        "scheduledSpawns": [{"time": 1e9}], "randomDraws": 123,
    }


class FakeHost:
    def __init__(self):
        self.obs = observation()
        self.commands = []

    def call(self, **request):
        self.commands.append(request)
        if request["command"] == "reset":
            self.obs = observation()
        elif request["command"] == "step":
            self.obs = copy.deepcopy(self.obs)
            self.obs["time"] += request["ticks"] * .05
        return {"accepted": request["command"] != "build", "terminated": False,
                "truncated": False, "spendingDelta": 0, "observation": self.obs}


def main():
    cases=SingleCitySeeds(sequence_seed=42)
    training=[cases.training_case() for _ in range(6)]
    assert all(city=="LosAngeles" for city,seed in training)
    assert len({seed for city,seed in training})==6
    assert not {seed for city,seed in training}&{200000,300000}
    # Retain checks for the historical city-split helpers used by old tools.
    assert [training_case(i)[0] for i in range(6)] == list(TRAIN_CITIES) * 2
    assert VALIDATION_CITY not in TRAIN_CITIES and TEST_CITY not in TRAIN_CITIES
    assert VALIDATION_CITY != TEST_CITY
    assert {seed for _, seed in validation_cases(3)}.isdisjoint(
        {seed for _, seed in test_cases(3)})
    assert aggregate_rank([{"time": 2, "trips": 1, "waitingSeconds": 4,
                            "modificationCost": 5}]) < aggregate_rank([
                                {"time": 1, "trips": 100, "waitingSeconds": 0,
                                 "modificationCost": 0}])
    obs = observation()
    proposals = candidates(obs)
    assert proposals[0].request == {"command": "wait"}
    assert any(item.request["command"] == "draw" for item in proposals)
    matrix, mask = candidate_matrix(proposals)
    assert matrix.shape == (48, 26) and mask.sum() == len(proposals)
    assert matrix[0, -1] == 0
    grid = visible_grid(obs)
    scalar = visible_scalar(obs).copy()
    assert grid.shape == (42, 30, 50) and visible_scalar(obs).shape == (19,)
    obs["playableXMax"] = 10
    assert np.all(visible_grid(obs)[:, :, 10:] == 0)
    obs["scheduledSpawns"][0]["time"] = -1e9
    assert np.array_equal(grid[:, :, :10], visible_grid(obs)[:, :, :10])
    assert np.array_equal(scalar, visible_scalar(obs))
    fake = FakeHost()
    env = TrafficEnv(fake, cap_seconds=2)
    env.reset("LosAngeles", 42)
    result = env.step({"command": "build", "tool": "Road", "x": 1, "y": 1})
    assert not result.accepted and result.observation["time"] == 1.0
    branch_host = FakeHost()
    branch = ReplayBranch(branch_host, env)
    branch.restore([{"command": "build", "tool": "Road", "x": 1, "y": 1}], env.observation)
    hypothetical = branch.transition({"command": "wait"}, 1234)
    assert hypothetical.observation["time"] == 2.0 and env.observation["time"] == 1.0
    result = env.step({"command": "wait"})
    assert result.truncated and result.observation["time"] == 2.0
    assert fake.commands[-1] == {"command": "step", "ticks": 20}
    assert material_use(result.observation) == 0
    class LegacyHost(FakeHost):
        def call(self, **request):
            response = super().call(**request)
            response["observation"].pop("tripsDispatched", None)
            return response
    try:
        TrafficEnv(LegacyHost()).reset("LosAngeles", 42)
    except ProtocolError as error:
        assert "tripsDispatched" in str(error) and "--host-dll" in str(error)
    else:
        raise AssertionError("Legacy simulator host was accepted")
    print("PASS: single-city seed isolation, legacy city split, goal proposals, observation filtering, action clock, episode cap")


if __name__ == "__main__":
    main()

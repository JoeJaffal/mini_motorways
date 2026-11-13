"""Focused regressions for destination coverage, road costs and reward penalties."""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from actions import candidates, clear_caches
from environment import ProtocolError, ReplayBranch, SnapshotBranch, TrafficEnv, capacity_pressure
from smoke import FakeHost, observation


class OutcomeHost(FakeHost):
    def __init__(self, *, failed=False, truncated=False, demand=3, reserved=0, trips=0, capacity=6):
        super().__init__()
        self.failed, self.truncated = failed, truncated
        self.demand, self.reserved, self.trips = demand, reserved, trips
        self.capacity = capacity

    def call(self, **request):
        response = super().call(**request)
        if request["command"] == "step":
            self.obs["failed"] = self.failed
            self.obs["buildings"][1].update(demand=self.demand, reserved=self.reserved, demandCapacity=self.capacity)
            self.obs["tripsCompleted"] += self.trips
            response.update(terminated=self.failed, truncated=self.truncated)
        return response


class RequestedChanges(unittest.TestCase):
    def test_destination_coverage_and_cutoff(self):
        for count in (9, 20, 21):
            with self.subTest(destinations=count):
                obs = observation()
                template = obs["buildings"][1]
                shops = []
                for i in range(count):
                    shop = copy.deepcopy(template)
                    x, y = (10 + 8*(i % 5), 8 + 5*(i // 5)) if i < 20 else (46, 28)
                    cell = {"x": x, "y": y}
                    shop.update(id=i+1, cell=cell, entrance=cell, entrances=[cell])
                    shops.append(shop)
                obs["buildings"] = obs["buildings"][:1] + shops
                clear_caches()
                with patch("actions._path", return_value=[]) as route:
                    items = candidates(obs, limit=1000)
                self.assertEqual(route.call_count, min(count, 20))
                local_cells = {(c.request["x"], c.request["y"]) for c in items
                               if c.request["command"] == "build"}
                for shop in shops[:20]:
                    self.assertIn((shop["cell"]["x"]-1, shop["cell"]["y"]), local_cells)
                if count == 21:
                    self.assertNotIn((45, 28), local_cells)
                self.assertLessEqual(len(candidates(obs)), 48)

    def transition(self, *, cap=1, failure_penalty=10, unanswered_penalty=.01, **outcome):
        env = TrafficEnv(OutcomeHost(**outcome), cap_seconds=cap,
                         failure_penalty=failure_penalty, unanswered_penalty=unanswered_penalty)
        env.reset("LosAngeles", 42)
        return env, env.step({"command": "wait"})

    def test_loss_penalty_once(self):
        env, step = self.transition(failed=True, demand=0, trips=2)
        self.assertTrue(step.terminated)
        self.assertFalse(step.truncated)
        self.assertEqual(step.components["failure"], 1)
        self.assertAlmostEqual(step.reward, 10.2)
        with self.assertRaises(RuntimeError):
            env.step({"command": "wait"})

    def test_cutoffs_do_not_count_as_losing(self):
        for options in ({"cap": .25}, {"cap": 5, "truncated": True}):
            with self.subTest(options=options):
                _, step = self.transition(demand=0, **options)
                self.assertTrue(step.truncated)
                self.assertEqual(step.components["failure"], 0)
                self.assertEqual(step.reward, 0)

    def test_backlog_includes_reserved_and_uses_elapsed_seconds(self):
        _, full = self.transition(demand=4, reserved=3)
        _, fractional = self.transition(cap=.25, demand=4, reserved=3)
        self.assertEqual(full.components["unansweredRequestSeconds"], 4)
        self.assertAlmostEqual(full.reward, -.04)
        self.assertEqual(fractional.components["unansweredRequestSeconds"], 1)
        self.assertAlmostEqual(fractional.reward, -.01)
        _, delivered = self.transition(demand=0, trips=1)
        self.assertAlmostEqual(delivered.reward, 10.1)

    def test_both_penalties_and_zero_overrides(self):
        _, step = self.transition(failed=True, demand=4, failure_penalty=7, unanswered_penalty=.2)
        self.assertAlmostEqual(step.reward, -7.8)
        _, legacy = self.transition(failed=True, demand=4, failure_penalty=0, unanswered_penalty=0)
        self.assertEqual(legacy.reward, 0)

    def test_branches_inherit_reward_weights(self):
        env = TrafficEnv(FakeHost(), lam=.02, failure_penalty=7, unanswered_penalty=.2, overcrowding_penalty=.3)
        for kind in (ReplayBranch, SnapshotBranch):
            branch = kind(FakeHost(), env)
            self.assertEqual(branch.env.failure_penalty, 7)
            self.assertEqual(branch.env.unanswered_penalty, .2)
            self.assertEqual(branch.env.overcrowding_penalty, .3)
            self.assertEqual(branch.env.lam, .02)
            self.assertEqual(branch.env.trip_reward, 10)
            self.assertEqual(branch.env.clear_trip_bonus,.1)
            self.assertEqual(branch.env.congestion_fraction_penalty,.02)
            self.assertEqual(branch.env.congestion_wait_threshold,2.)

    def test_capacity_threshold_progression_and_relief(self):
        host = OutcomeHost()
        env = TrafficEnv(host, cap_seconds=10, unanswered_penalty=0)
        env.reset("LosAngeles", 42)
        for demand, expected in ((5, 0), (6, -.05), (6, -.05), (7, -.10), (8, -.15), (5, 0)):
            host.demand = demand
            host.reserved = demand  # Assignment does not relieve outstanding demand.
            step = env.step({"command": "wait"})
            self.assertAlmostEqual(step.reward, expected)
            self.assertAlmostEqual(step.components["capacityPressureSeconds"], -expected/.05)

    def test_actual_capacity_and_fractional_duration(self):
        for capacity in (6, 9):
            for demand in (capacity-1, capacity, capacity+1):
                host = OutcomeHost(demand=demand, capacity=capacity)
                env = TrafficEnv(host, cap_seconds=.25, unanswered_penalty=0, overcrowding_penalty=.2)
                env.reset("LosAngeles", 42)
                step = env.step({"command": "wait"})
                pressure = max(0, demand-capacity+1)*.25
                self.assertAlmostEqual(step.reward, -.2*pressure)
                self.assertEqual(step.components["capacityPressureSeconds"], pressure)

    def test_pressure_sums_destinations_and_excludes_houses(self):
        obs = observation()
        obs["buildings"][0]["demand"] = 100
        obs["buildings"][1]["demand"] = 6
        other = copy.deepcopy(obs["buildings"][1])
        other.update(id=2, demand=10, demandCapacity=9)
        obs["buildings"].append(other)
        self.assertEqual(capacity_pressure(obs), 3)

    def test_capacity_validation_and_disabled_legacy_support(self):
        for capacity in (None, 0, -1, float("nan"), float("inf")):
            host = FakeHost()
            original = host.call
            def call(**request):
                result = original(**request)
                result["observation"]["buildings"][1]["demandCapacity"] = capacity
                return result
            host.call = call
            with self.assertRaisesRegex(ProtocolError, "demandCapacity"):
                TrafficEnv(host).reset("LosAngeles", 42)
            env = TrafficEnv(host, overcrowding_penalty=0, unanswered_penalty=0)
            env.reset("LosAngeles", 42)
            self.assertEqual(env.step({"command": "wait"}).reward, 0)

    def test_modification_default_charges_new_link_on_existing_roads(self):
        class RoadHost(OutcomeHost):
            def call(self, **request):
                result = super().call(**request)
                if request["command"] == "reset":
                    self.obs["infrastructure"][255] = self.obs["infrastructure"][256] = 1
                if request["command"] == "connect":
                    self.obs = copy.deepcopy(self.obs)
                    self.obs["connections"][255] = 1
                    self.obs["connections"][256] = 16
                    result["observation"] = self.obs
                return result
        env = TrafficEnv(RoadHost(demand=0), cap_seconds=3)
        env.reset("LosAngeles", 42)
        self.assertEqual(env.lam, .01)
        request = {"command": "connect", "x": 5, "y": 5, "toX": 6, "toY": 5}
        changed = env.step(request)
        self.assertEqual(changed.components["modificationCost"], 1)
        self.assertAlmostEqual(changed.reward, -.01)
        unchanged = env.step(request)
        self.assertEqual(unchanged.components["modificationCost"], 0)
        self.assertEqual(unchanged.reward, 0)

    def test_protocol_errors_are_not_game_losses(self):
        host = FakeHost()
        env = TrafficEnv(host)
        env.reset("LosAngeles", 42)
        with patch.object(host, "call", side_effect=RuntimeError("host failure")):
            with self.assertRaisesRegex(RuntimeError, "host failure"):
                env.step({"command": "wait"})

    def test_connection_bonus_requires_traffic_on_endpoint_roads(self):
        for stage, cell, expected_bonus in (
                (None, (11, 5), 0), ("Home", (11, 5), 0), ("Parking", (11, 5), 0),
                ("Outbound", (11, 5), 2), ("Returning", (10, 5), 2),
                ("Outbound", (12, 5), 0), ("Outbound", (11, 6), 0)):
            with self.subTest(stage=stage, cell=cell):
                obs = observation()
                for x in (10, 11):
                    obs["infrastructure"][5*50+x] = 1
                obs["vehicles"] = [{"x":cell[0]+.5,"y":cell[1]+.5,
                                    "stage":stage,"waiting":7,"speed":0}]
                items = candidates(obs, limit=1000)
                connections = [c for c in items if c.request["command"] == "connect" and
                    {(c.request["x"],c.request["y"]),(c.request["toX"],c.request["toY"])} == {(10,5),(11,5)}]
                self.assertTrue(connections)
                for c in connections:
                    # The feature stores capped urgency/10; these fixture urgencies are < 10.
                    urgency = c.features[18]*10
                    self.assertAlmostEqual(c.priority, urgency+expected_bonus)

    def test_connection_without_vehicles_has_no_bonus(self):
        obs = observation()
        obs["infrastructure"][5*50+10] = obs["infrastructure"][5*50+11] = 1
        items = candidates(obs, limit=1000)
        connections = [c for c in items if c.request["command"] == "connect"]
        self.assertTrue(connections)
        self.assertTrue(all(c.priority == 4 for c in connections))  # shop urgency: 1 + demand 3

    def test_invalid_penalties_rejected(self):
        for value in (-1, float("nan"), float("inf")):
            for name in ("failure_penalty", "unanswered_penalty", "overcrowding_penalty"):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        TrafficEnv(FakeHost(), **{name: value})


if __name__ == "__main__":
    unittest.main()

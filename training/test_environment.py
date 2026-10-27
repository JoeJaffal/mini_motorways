"""Adapter checks: protocol integration, information boundary and tool decoding."""
import argparse
from collections import deque
import copy
import hashlib
import json
import sys
import unittest
from unittest.mock import patch

import numpy as np
from gymnasium.utils.env_checker import check_env

from environment import TrafficEnv, CELLS, MAPS, DIRS

DOTNET = 'dotnet'


class EnvironmentChecks(unittest.TestCase):
    def setUp(self):
        self.env = TrafficEnv(dotnet=DOTNET, seconds=300)
        self.env.reset(seed=42, options={'scenario_seed': 1000})

    def tearDown(self):
        self.env.close()

    def select(self, tool, *points):
        result = self.env.step(CELLS+tool)
        for p in points:
            result = self.env.step(p[1]*50+p[0])
        return result

    def test_gym_contract(self):
        check_env(self.env, skip_render_check=True)

    def test_information_boundary(self):
        env = self.env
        before = env.encode()
        env.raw['scheduledSpawns'] = [{'time': -100, 'color': 7}]
        env.raw['randomDraws'] = 123456789
        env.raw['randomAlgorithm'] = 'secret'
        for b in env.raw['buildings']:
            b['upgradeAt'], b['plannedDemandMultiplier'] = -1, 999
        outside = np.flatnonzero(~env.visible)
        for k in outside:
            env.raw['terrain'][k] = 2
            env.raw['demand'][k] = 999
            env.raw['buildingColors'][k] = 7
        env._refresh()
        after = env.encode()
        for key in before:
            np.testing.assert_array_equal(before[key], after[key])
        self.assertTrue((after['grid'].reshape(50, -1)[:, outside] == 0).all())

    def test_invalid_time_and_truncation(self):
        env = self.env
        env.seconds = 2
        _, reward, terminated, truncated, info = env.step(-1)
        self.assertEqual(reward, 0)
        self.assertAlmostEqual(info['seconds'], 1)
        self.assertFalse(terminated or truncated)
        _, _, terminated, truncated, _ = env.step(CELLS)
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        with self.assertRaises(RuntimeError):
            env.step(CELLS)
        env.reset(options={'scenario_seed': 1000})
        self.assertEqual(env.raw['tripsCompleted'], 0)
        self.assertEqual(env.raw['time'], 0)

    def test_failure_is_termination(self):
        env = self.env
        while True:
            _, _, terminated, truncated, _ = env.step(CELLS)
            if terminated or truncated:
                break
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        with self.assertRaises(RuntimeError):
            env.step(CELLS)

    def test_all_tool_decoders(self):
        # Protocol decoding is tested separately from legality; core self-tests
        # exercise real stock, motorway editing, deferred removals and driveways.
        env = self.env
        home = next(iter(env.houses))
        a, b, c = home, (home[0]+1, home[1]), (home[0]+2, home[1])
        m = dict(id=77, start=dict(x=a[0], y=a[1]), end=dict(x=c[0], y=c[1]))
        cases = [(0, [], None), (1, [a, b], 'draw'), (2, [a], 'build'),
                 (3, [a], 'build'), (4, [a], 'build'), (5, [a], 'build'),
                 (6, [a], 'build'), (7, [a, b], 'driveway'), (8, [a, c], 'motorway'),
                 (9, [a, b, c], 'editMotorway'), (10, [a], 'removeMotorway'),
                 (11, [], 'upgrade'), (12, [], 'upgrade')]
        for tool, points, command in cases:
            env.reset(options={'scenario_seed': 1000})
            env.active_motorways[a] = m
            calls = []
            raw = copy.deepcopy(env.raw)
            def fake_call(**request):
                calls.append(request)
                if request['command'] == 'step':
                    raw['time'] += 1
                    raw['tripsCompleted'] += 2
                return dict(accepted=True, terminated=False, truncated=False, observation=raw)
            with patch.object(env, 'action_masks', return_value=np.ones(env.action_space.n, bool)), patch.object(env.host, 'call', side_effect=fake_call):
                result = self.select(tool, *points)
            self.assertTrue(result[4]['command_completed'])
            self.assertEqual(result[1], 2)
            self.assertEqual(calls[-1], dict(command='step', ticks=20))
            if command is None:
                self.assertEqual(len(calls), 1)
            else:
                self.assertEqual(calls[0]['command'], command)
                self.assertEqual(len(calls), 2)
                if tool in (7, 9, 10):
                    self.assertEqual(calls[0]['id'], env.houses[a]['id'] if tool == 7 else 77)
                if 2 <= tool <= 6:
                    self.assertEqual(calls[0]['tool'], ['Road', 'Bridge', 'TrafficLight', 'Roundabout', 'Remove'][tool-2])
                if tool >= 11:
                    self.assertEqual(calls[0]['choice'], tool-11)

    def test_normal_roads_and_positive_reward(self):
        env = self.env
        # Scripted diagnostic route, never used by the training policy.
        free = {tuple((int(k%50), int(k//50))) for k in np.flatnonzero(env.land)}
        best = None
        for h, home in env.houses.items():
            dx, dy = DIRS[home['drivewayDirection']]
            start = h[0]+dx, h[1]+dy
            queue, parent = deque([start]), {start: None}
            while queue:
                p = queue.popleft()
                for dx, dy in DIRS[::2]:
                    q = p[0]+dx, p[1]+dy
                    if q in free and q not in parent:
                        parent[q] = p
                        queue.append(q)
            for shop in env.buildings:
                if shop['isHouse'] or shop['color'] != home['color']:
                    continue
                end = tuple(shop['entrance'][k] for k in ('x', 'y'))
                dx, dy = DIRS[shop['drivewayDirection']]
                target = end[0]+dx, end[1]+dy
                if target not in parent:
                    continue
                path = [target]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                path = [h]+list(reversed(path))+[end]
                if best is None or len(path) < len(best):
                    best = path
        self.assertIsNotNone(best)
        total = 0
        for a, b in zip(best, best[1:]):
            before = env.raw['time']
            result = self.select(1, a, b)
            self.assertTrue(result[4]['accepted'])
            self.assertAlmostEqual(env.raw['time']-before, 1)
            total += result[1]
        while not env.done:
            result = env.step(CELLS)
            total += result[1]
        self.assertGreater(total, 0)
        self.assertEqual(total, env.raw['tripsCompleted'])

    def test_all_maps_replay(self):
        for city in MAPS:
            env = TrafficEnv(dotnet=DOTNET, city=city, seconds=15)
            try:
                digests = []
                for _ in range(2):
                    obs, _ = env.reset(seed=5, options={'scenario_seed': 42})
                    rng, digest, stages = np.random.default_rng(5), hashlib.sha256(), 0
                    while not env.done:
                        self.assertTrue(env.observation_space.contains(obs))
                        for k in sorted(obs):
                            digest.update(obs[k].tobytes())
                        mask = env.action_masks()
                        action = int(rng.choice(np.flatnonzero(mask)))
                        obs, reward, terminated, truncated, info = env.step(action)
                        digest.update(json.dumps([reward, terminated, truncated, info], sort_keys=True).encode())
                        stages = 0 if info['command_completed'] else stages+1
                        self.assertLessEqual(stages, 3)
                    digests.append(digest.hexdigest())
                self.assertEqual(*digests, msg=city)
            finally:
                env.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dotnet', default='dotnet')
    args, remaining = parser.parse_known_args()
    DOTNET = args.dotnet
    unittest.main(argv=[sys.argv[0]]+remaining)

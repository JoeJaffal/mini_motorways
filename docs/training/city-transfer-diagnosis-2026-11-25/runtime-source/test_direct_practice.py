"""Direct Stage 1 action and frozen evaluation checks, without learning."""
import os
from pathlib import Path
import tempfile
from time import monotonic
import unittest
from unittest.mock import patch

import numpy as np

from compare_stage1 import evaluate, summarize
from connection_practice import ConnectionPractice, DIRECT_STAGE, WAIT
from practice_replay import PracticeRecorder, verify
from test_one_gap import gap


DLL = os.environ.get('STAGE1_DIRECT_DLL', 'simulation/Headless/bin/Release/net8.0/TrafficHost.dll')


class DirectPracticeChecks(unittest.TestCase):
    def setUp(self):
        self.env = ConnectionPractice(host_dll=DLL, split='validation', stage=DIRECT_STAGE)
        self.addCleanup(self.env.close)

    def test_action_mask_matches_native_draw_in_both_orientations(self):
        env = self.env
        seed = 20000
        env.reset(seed=seed)
        mask = env.action_masks()
        self.assertTrue(mask[WAIT])
        xmin, xmax, ymin, ymax = env.practice_bounds
        for action in range(1, len(mask)):
            start, end = env.direct_endpoints(action)
            x, y = end
            if not (xmin <= x < xmax and ymin <= y < ymax):
                self.assertFalse(mask[action])
                continue
            outcomes = []
            for a, b in ((start, end), (end, start)):
                env.reset(seed=seed)
                old = np.array(env.raw['connections'])
                old_driveways = [building['drivewayDirection'] for building in env.raw['buildings']]
                result = env._call(command='draw', x=a[0], y=a[1], toX=b[0], toY=b[1])
                new = np.array(env.raw['connections'])
                driveways = [building['drivewayDirection'] for building in env.raw['buildings']]
                index = start[1] * 50 + start[0]
                selected = 1 << ((action - 1) % 4)
                legal = (result['accepted'] and not old[index] & selected and bool(new[index] & selected)
                         and np.array_equal(new & old, old) and old_driveways == driveways)
                self.assertEqual(bool(mask[action]), legal, (start, end, a))
                if legal:
                    outcomes.append((env.raw['connections'], env.raw['infrastructure'], env.raw['inventory']))
            if len(outcomes) == 2:
                self.assertEqual(outcomes[0], outcomes[1])

    def test_single_action_repairs_and_native_trip_reward_replays(self):
        env = self.env
        for seed in (20000, 20001, 20002, 20003):
            recorder = PracticeRecorder(env, seed=seed)
            repair = set(gap(env))
            action, = [i for i in np.flatnonzero(env.action_masks()) if i and set(env.direct_endpoints(i)) == repair]
            _, reward, _, _, info = recorder.step(action)
            self.assertEqual(reward, 0.)
            self.assertEqual(info['seconds'], 0.)
            self.assertEqual(info['new_connections'], 1)
            self.assertFalse(env.action_masks()[action])
            with self.assertRaises(ValueError):
                env.step(action)
            total_reward = 0.
            while not env.done:
                total_reward += recorder.step(WAIT)[1]
            self.assertEqual(total_reward, env.raw['tripsCompleted'])
            self.assertGreaterEqual(total_reward, 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'direct.json'
            recorder.save(path)
            self.assertEqual(verify(path, host_dll=DLL)['result'], 'PASS')

    def test_frozen_metrics_capture_a_repair_at_simulated_time_zero(self):
        env = self.env
        env.seconds = 1

        def scripted_mask():
            mask = np.zeros(env.action_space.n, dtype=bool)
            if env.decisions == 0:
                repair = set(gap(env))
                action, = [i for i in range(1, len(mask)) if set(env.direct_endpoints(i)) == repair]
                mask[action] = True
            else:
                mask[WAIT] = True
            return mask

        with patch.object(env, 'action_masks', side_effect=scripted_mask):
            rows = evaluate(None, [env], [20000], deadline=monotonic() + 30, max_decisions=5)
        self.assertEqual(rows[0]['first_connection_seconds'], 0.)
        self.assertEqual(rows[0]['first_connection_decision'], 1)
        self.assertEqual(rows[0]['road_units_spent'], 1)
        self.assertEqual(summarize(rows)['repair_rate'], 1.)
        self.assertTrue(rows[0]['natural'])

    def test_uniform_reference_is_repeatable_and_caps_invalidate_games(self):
        def run():
            return evaluate(None, [self.env], [20000, 20001],
                            deadline=monotonic() + 30, max_decisions=5)
        rows = run()
        self.assertEqual(rows, run())
        self.assertEqual(summarize(rows)['natural_games'], 0)
        self.assertTrue(all(row['ending'] == 'external_decision_limit' for row in rows))
        self.assertTrue(all('first_connection_seconds' in row for row in rows))


if __name__ == '__main__':
    unittest.main()

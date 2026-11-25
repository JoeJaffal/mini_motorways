"""Single-build binary reward and evaluation checks without learning."""
import os
from pathlib import Path
import tempfile
from time import monotonic
import unittest
from unittest.mock import patch

import numpy as np
import torch

from compare_stage1 import evaluate, paired, summarize
from connection_practice import ConnectionPractice, SINGLE_BUILD_STAGE, WAIT
from hierarchy_policy import practice_policy
from hierarchy_rollout import policy_fingerprint
from parallel_stage1 import ParallelCollector, parallel_batches
from practice_replay import PracticeRecorder, verify
from test_one_gap import gap


DLL = os.environ.get('STAGE1_SINGLE_BUILD_DLL', 'simulation/Headless/bin/Release/net8.0/TrafficHost.dll')


class SingleBuildChecks(unittest.TestCase):
    def setUp(self):
        self.env = ConnectionPractice(host_dll=DLL, stage=SINGLE_BUILD_STAGE, split='validation')
        self.addCleanup(self.env.close)

    def repair_action(self):
        repair = set(gap(self.env))
        action, = [i for i in np.flatnonzero(self.env.action_masks())
                   if set(self.env.direct_endpoints(i)) == repair]
        return action

    def test_wrong_build_ends_episode_with_zero_and_no_wait(self):
        env = self.env
        env.reset(seed=20000)
        mask = env.action_masks()
        self.assertFalse(mask[WAIT])
        with self.assertRaises(ValueError):
            env.step(WAIT)
        distractor = int(np.flatnonzero(mask)[0])
        self.assertNotEqual(distractor, self.repair_action())
        _, reward, terminated, truncated, info = env.step(distractor)
        self.assertEqual((reward, terminated, truncated), (0., True, False))
        self.assertEqual((info['seconds'], info['trips'], info['new_connections']), (0., 0, 1))
        self.assertEqual(env.raw['inventory'][0], 0)
        with self.assertRaises(RuntimeError):
            env.step(distractor)

    def test_repair_earns_one_on_all_heldout_layouts_and_replays(self):
        env = self.env
        for seed in range(20000, 20100):
            env.reset(seed=seed)
            self.assertEqual(env.raw['inventory'][0], 1)
            self.assertGreater(env.action_masks().sum(), 400)
            _, reward, terminated, truncated, info = env.step(self.repair_action())
            self.assertEqual((reward, terminated, truncated), (1., True, False))
            self.assertEqual((info['seconds'], info['trips'], info['road_units_spent']), (0., 0, 1))
            self.assertEqual(env.expected_training_return(), 1.)
        recorder = PracticeRecorder(env, seed=20000)
        recorder.step(self.repair_action())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'single-build.json'
            recorder.save(path)
            self.assertEqual(verify(path, host_dll=DLL)['result'], 'PASS')

    def test_fast_collection_matches_regular_steps_across_worker_resets(self):
        torch.set_num_threads(2)
        envs = [self.env, ConnectionPractice(host_dll=DLL, stage=SINGLE_BUILD_STAGE, split='validation')]
        self.addCleanup(envs[1].close)
        policy = practice_policy(envs[0], lambda _: 0.)
        events = []
        collector = ParallelCollector(envs, policy, seeds=[20000, 20001],
                                      on_transition=lambda i, t, info: events.append((i, t, info)))
        self.addCleanup(collector.close)
        fingerprint = policy_fingerprint(policy)

        # Script one correct move and one legal distractor per wave.
        for worker, env in enumerate(envs):
            original_mask = env.action_masks

            def force_one(env=env, original_mask=original_mask, repair=worker == 0):
                legal = original_mask()
                repair_edge = set(gap(env))
                chosen = next(int(i) for i in np.flatnonzero(legal)
                              if (set(env.direct_endpoints(i)) == repair_edge) == repair)
                legal[:] = False
                legal[chosen] = True
                return legal

            env.action_masks = force_one

        reference = collector.collect(target_tokens=2, hard_limit=2, deadline=monotonic()+30, policy_version='v0')
        collector.reset_many([(0, 20000), (1, 20001)])

        def reset_completed():
            collector.reset_many([(0, 20002), (1, 20003)])

        fast = collector.collect_single_builds(target_tokens=3, deadline=monotonic()+30,
                                               policy_version='v0', reset_completed=reset_completed)
        self.assertEqual([i for i, _ in fast], [0, 1, 0])
        for (_, expected), (_, actual) in zip(reference, fast):
            t, u = expected.transitions[0], actual.transitions[0]
            self.assertEqual((t.action, t.reward, t.log_probability, t.value),
                             (u.action, u.reward, u.log_probability, u.value))
            np.testing.assert_array_equal(t.mask, u.mask)
            for name in t.observation:
                np.testing.assert_array_equal(t.observation[name], u.observation[name])
            self.assertIsNone(actual.final_observation)
            self.assertEqual(actual.bootstrap_value, 0.)
        batches = parallel_batches(fast, device='cpu', minibatch_size=3, direct=True, single_build=True)
        self.assertEqual(batches[0]['returns'].tolist(), [1., 0., 1.])
        self.assertEqual(len(events), 5)
        self.assertTrue(all(info['seconds'] == 0 for _, _, info in events))
        self.assertEqual(policy_fingerprint(policy), fingerprint)

    def test_frozen_comparison_measures_binary_reward_separately_from_trips(self):
        env = self.env
        original = env.action_masks

        def scripted_mask(repair):
            mask = np.zeros(env.action_space.n, dtype=bool)
            repair_edge = set(gap(env))
            legal = np.flatnonzero(original())
            action = next(i for i in legal if (set(env.direct_endpoints(i)) == repair_edge) == repair)
            mask[action] = True
            return mask

        def evaluate_build(repair):
            with patch.object(env, 'action_masks', side_effect=lambda: scripted_mask(repair)):
                return evaluate(None, [env], [20000], deadline=monotonic()+30, max_decisions=1)

        misses = evaluate_build(False)
        repairs = evaluate_build(True)
        self.assertEqual(repairs[0]['score'], 0)
        self.assertEqual(repairs[0]['task_score'], 1)
        self.assertTrue(repairs[0]['natural'])
        self.assertEqual(summarize(repairs)['repair_rate'], 1.)
        self.assertEqual(paired(misses, repairs, metric='task_score')['trained_higher_score'], 1)


if __name__ == '__main__':
    unittest.main()

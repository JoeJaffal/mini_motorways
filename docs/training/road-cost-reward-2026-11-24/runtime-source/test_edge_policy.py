"""Shared edge policy parity and masked inference, without updates."""
import os
import unittest

import numpy as np
import torch

from connection_practice import ARENA_SIZE, ConnectionPractice, SINGLE_BUILD_STAGE
from edge_policy import EDGE_POLICY, stage1_policy
from hierarchy_rollout import policy_fingerprint
from test_one_gap import gap


DLL = os.environ.get('STAGE1_SINGLE_BUILD_DLL', 'simulation/Headless/bin/Release/net8.0/TrafficHost.dll')


class SharedEdgeChecks(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        self.env = ConnectionPractice(host_dll=DLL, stage=SINGLE_BUILD_STAGE, split='validation')
        self.addCleanup(self.env.close)
        self.policy = stage1_policy(self.env, lambda _: 0., name=EDGE_POLICY)
        self.obs, _ = self.env.reset(seed=20000)

    def logits(self, observation):
        with torch.inference_mode():
            inputs, _ = self.policy.obs_to_tensor(observation)
            features = self.policy.extract_features(inputs)
            return self.policy.action_net(self.policy.mlp_extractor.forward_actor(features))[0].numpy()

    def test_equivariant_to_translation_and_quarter_turn(self):
        xmin, xmax, ymin, ymax = self.env.practice_bounds
        size = ARENA_SIZE
        board = self.obs['grid']
        arena = board[:, ymin:ymax, xmin:xmax]
        old = self.logits(self.obs)
        relocated = np.zeros_like(board)
        relocated[:, 3:3+size, 2:2+size] = arena
        np.testing.assert_allclose(self.logits(dict(self.obs, grid=relocated)), old, atol=1e-7)

        turned = np.rot90(arena, k=-1, axes=(1, 2)).copy()
        for start in (9, 30):
            turned[start:start+8] = np.roll(turned[start:start+8], 2, axis=0)
        rotated = np.zeros_like(board)
        rotated[:, ymin:ymax, xmin:xmax] = turned
        new = self.logits(dict(self.obs, grid=rotated))

        edges = {}
        for action in range(1, self.env.action_space.n):
            endpoints = self.env.direct_endpoints(action)
            if all(xmin <= x < xmax and ymin <= y < ymax for x, y in endpoints):
                edges[frozenset(endpoints)] = action
        for endpoints, action in edges.items():
            transformed = frozenset((xmin + size - 1 - (y - ymin), ymin + x - xmin)
                                    for x, y in endpoints)
            self.assertAlmostEqual(float(old[action]), float(new[edges[transformed]]), places=7)
        self.assertGreater(float(np.ptp(old)), 0.)

    def test_masked_policy_and_binary_reward(self):
        before = policy_fingerprint(self.policy)
        mask = self.env.action_masks()
        edge = set(gap(self.env))
        correct, = [int(i) for i in np.flatnonzero(mask) if set(self.env.direct_endpoints(i)) == edge]
        with torch.inference_mode():
            tensor, _ = self.policy.obs_to_tensor(self.obs)
            distribution = self.policy.get_distribution(tensor, action_masks=mask)
            probabilities = distribution.distribution.probs.numpy()[0]
            self.assertTrue(np.all(probabilities[mask] > 0))
            self.assertTrue(np.all(probabilities[~mask] == 0))
            action = torch.tensor([correct])
            value, logp, entropy = self.policy.evaluate_actions(tensor, action, action_masks=mask)
            self.assertTrue(torch.isfinite(torch.cat((value.flatten(), logp, entropy))).all())
        _, reward, terminated, truncated, _ = self.env.step(correct)
        self.assertEqual((reward, terminated, truncated), (1., True, False))
        self.assertEqual(policy_fingerprint(self.policy), before)


if __name__ == '__main__':
    unittest.main()

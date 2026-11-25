import math
import unittest

import gymnasium as gym
import numpy as np
import torch

from city_bridge_strategy_policy import (
    BridgeStrategyDistribution, CityBridgeStrategyFeatures, CityBridgeStrategyPolicy,
)
from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS
from city_route_repair_policy import ProgressDistribution
from city_wide_strategy_policy import CityWideStrategyFeatures, WideStrategyHead
from visible_observation import observation_space


class BridgeDistributionTests(unittest.TestCase):
    def make_logits(self):
        base = torch.zeros((1, 2*ROAD_SLOTS+2))
        base[0, 1:5] = torch.tensor([3., 1., -50., -51.])
        water = torch.zeros((1, ROAD_SLOTS))
        water[0, 2:4] = 1
        gate = torch.tensor([[math.log(.2/.8)]], requires_grad=True)
        return base, water, gate

    def test_joint_probability_entropy_and_policy_gradient(self):
        base, water, gate = self.make_logits()
        mask = np.zeros((1, ROAD_SLOTS+1), dtype=bool)
        mask[:, :5] = True
        d = BridgeStrategyDistribution(ROAD_SLOTS+1)
        d.proba_distribution(torch.cat((base, water, gate), 1)).apply_masking(mask)
        p = d.distribution.probs
        torch.testing.assert_close(p[0, 0], torch.tensor(.5))
        torch.testing.assert_close(p[0, 1:3].sum(), torch.tensor(.4))
        torch.testing.assert_close(p[0, 3:5].sum(), torch.tensor(.1))
        torch.testing.assert_close(p[0, 3]/p[0, 4], torch.tensor(math.e))
        self.assertFalse(bool(p[~torch.as_tensor(mask)].any()))
        positive = p[p > 0]
        torch.testing.assert_close(d.entropy()[0], -(positive*positive.log()).sum())
        d.log_prob(torch.tensor([3])).backward()
        torch.testing.assert_close(gate.grad, torch.tensor([[.8]]))
        original = p.detach().clone()
        d.apply_masking(mask)
        torch.testing.assert_close(d.distribution.probs, original, rtol=0, atol=0)

    def test_missing_categories_and_forced_wait_are_finite(self):
        for allowed in ([0], [0, 1, 2], [0, 3, 4]):
            base, water, gate = self.make_logits()
            mask = np.zeros((1, ROAD_SLOTS+1), dtype=bool)
            mask[:, allowed] = True
            old = ProgressDistribution(ROAD_SLOTS+1).proba_distribution(base)
            old.apply_masking(mask)
            new = BridgeStrategyDistribution(ROAD_SLOTS+1).proba_distribution(torch.cat((base, water, gate), 1))
            new.apply_masking(mask)
            torch.testing.assert_close(new.distribution.probs, old.distribution.probs, rtol=0, atol=0)
            loss = new.log_prob(torch.tensor([allowed[-1]])).sum()+new.entropy().sum()
            loss.backward()
            self.assertTrue(torch.isfinite(gate.grad).all())
            self.assertEqual(float(gate.grad.abs().sum()), 0.)

    def test_frozen_dry_actor_after_arbitrary_new_parameter_changes(self):
        torch.set_num_threads(1)
        space = observation_space()
        policy = CityBridgeStrategyPolicy(space, gym.spaces.Discrete(ROAD_SLOTS+1), lambda _: .0001,
            features_extractor_class=CityBridgeStrategyFeatures, optimizer_class=RelativeRateAdam,
            normalize_images=False)
        names = [n for n, p in policy.named_parameters() if p.requires_grad]
        self.assertTrue(all(n.startswith('value_net.') or n.startswith('features_extractor.bridge_strategy_') for n in names))
        obs = {k: torch.zeros((1, *v.shape)) for k, v in space.spaces.items()}
        obs['grid'][:, 0:2] = 1
        obs['grid'][0, 1, 10, 10] = 0
        obs['grid'][0, 2, 10, 10] = 1
        f = policy.features_extractor
        with torch.no_grad():
            for name, parameter in f.named_parameters():
                if name.startswith('bridge_strategy_'):
                    parameter.add_(torch.randn_like(parameter)*.1)
            base = CityWideStrategyFeatures.forward(f, obs)
            logits = WideStrategyHead(f.context_width)(base)
        mask = np.zeros((1, ROAD_SLOTS+1), dtype=bool)
        mask[:, :20] = True  # These edges are far from the water cell.
        old = ProgressDistribution(ROAD_SLOTS+1).proba_distribution(logits)
        old.apply_masking(mask)
        actual = policy.get_distribution(obs, action_masks=mask)
        torch.testing.assert_close(actual.distribution.probs, old.distribution.probs, rtol=0, atol=0)
        self.assertTrue(torch.isfinite(policy.predict_values(obs)).all())


if __name__ == '__main__':
    unittest.main()

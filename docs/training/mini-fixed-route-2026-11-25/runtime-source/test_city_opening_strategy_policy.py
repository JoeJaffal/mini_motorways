import unittest
from unittest.mock import patch

import gymnasium as gym
import torch

from city_opening_strategy_policy import CityOpeningStrategyFeatures, CityOpeningStrategyPolicy
from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS
from city_strategy_policy import STRATEGY_CONTEXT
from city_wide_strategy_policy import CityWideStrategyFeatures
from visible_observation import observation_space


class OpeningStrategyTests(unittest.TestCase):
    def test_initial_parity_freezing_and_gate(self):
        torch.set_num_threads(1)
        space = observation_space()
        policy = CityOpeningStrategyPolicy(space, gym.spaces.Discrete(ROAD_SLOTS+1), lambda _: .0001,
            features_extractor_class=CityOpeningStrategyFeatures,
            optimizer_class=RelativeRateAdam, normalize_images=False)
        names = [n for n, p in policy.named_parameters() if p.requires_grad]
        self.assertTrue(names)
        self.assertTrue(all(n.startswith('features_extractor.opening_strategy_') or n.startswith('value_net.') for n in names))
        f = policy.features_extractor
        obs = {k: torch.zeros((1, *v.shape)) for k, v in space.spaces.items()}
        torch.testing.assert_close(f(obs), CityWideStrategyFeatures.forward(f, obs), rtol=0, atol=0)
        self.assertTrue(torch.isfinite(f(obs)).all())
        with torch.no_grad():
            f.opening_strategy_roads.bias.fill_(.75)
            f.opening_strategy_wait[-1].bias.fill_(.5)
        for established in (False, True):
            context = torch.zeros((1, STRATEGY_CONTEXT))
            context[:, 57] = int(established)
            gate = torch.tensor([[established]])
            with patch.object(f, 'strategy_context', return_value=(context, gate)):
                base = CityWideStrategyFeatures.forward(f, obs)
                actual = f(obs)
            if established:
                torch.testing.assert_close(actual, base, rtol=0, atol=0)
            else:
                torch.testing.assert_close(actual[:, :ROAD_SLOTS]-base[:, :ROAD_SLOTS], torch.full((1, ROAD_SLOTS), .75))
                index = ROAD_SLOTS+f.context_width
                self.assertAlmostEqual(float((actual[0, index]-base[0, index]).detach()), .5)
            policy.zero_grad()
            actual.sum().backward()
            gradient = f.opening_strategy_roads.bias.grad
            self.assertIsNotNone(gradient)
            self.assertEqual(bool(gradient.abs().sum() > 0), not established)
            self.assertTrue(all(p.grad is None for n, p in f.named_parameters() if not n.startswith('opening_strategy_')))


if __name__ == '__main__':
    unittest.main()

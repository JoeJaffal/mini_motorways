"""Retention and learning checks for mixed opening/established PPO batches."""
import unittest

import torch

from city_established_policy import CityEstablishedFeatures
from city_network_service_policy import CityNetworkServiceFeatures
import test_city_network_service as fixtures
from visible_observation import observation_space


class CityEstablishedTests(unittest.TestCase):
    def test_opening_is_exact_while_established_actor_can_change(self):
        torch.set_num_threads(1)
        space = observation_space()
        model = CityEstablishedFeatures(space)
        source = CityNetworkServiceFeatures(space)
        model.load_state_dict(source.state_dict(), strict=False)
        model.opening_reference.load_state_dict(source.state_dict())
        grid = torch.zeros((1, *space['grid'].shape))
        grid[:, (0, 1, 18)] = 1
        for x, y, kind, direction in [(5, 5, 19, 0), (7, 5, 20, 4), (10, 10, 20, 4)]:
            fixtures.CityNetworkServiceTests.building(grid, x, y, kind, 0, direction)
        attached = grid.clone()
        fixtures.CityNetworkServiceTests.draw_east(attached, 5, 5)
        fixtures.CityNetworkServiceTests.draw_east(attached, 6, 5)
        obs = {'grid': torch.cat((grid, attached)),
               'global': torch.zeros((2, *space['global'].shape))}
        self.assertEqual(model.service_features(obs['grid'])[-2].flatten().tolist(), [False, True])
        with torch.no_grad():
            expected = source(obs)
            torch.testing.assert_close(model(obs), expected, atol=0, rtol=0)
            model.growth_roads.bias.add_(1)
        actual = model(obs)
        torch.testing.assert_close(actual[0], expected[0], atol=0, rtol=0)
        self.assertFalse(torch.equal(actual[1], expected[1]))
        actual.sum().backward()
        self.assertTrue(all(p.grad is None for p in model.opening_reference.parameters()))
        self.assertGreater(model.growth_roads.bias.grad.abs().sum().item(), 0)


if __name__ == '__main__':
    unittest.main()

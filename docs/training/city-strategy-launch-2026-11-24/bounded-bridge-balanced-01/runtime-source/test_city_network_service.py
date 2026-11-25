import unittest

import torch

from city_network_service_policy import CityNetworkServiceFeatures
from city_road_pilot import edge_action
from visible_observation import WIDTH, observation_space


class CityNetworkServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.space = observation_space()
        cls.features = CityNetworkServiceFeatures(cls.space)

    def board(self):
        grid = torch.zeros((1, *self.space['grid'].shape))
        grid[:, (0, 1, 18)] = 1
        return grid

    @staticmethod
    def building(grid, x, y, kind, color, direction):
        grid[0, 18, y, x] = 0
        grid[0, (kind, 21+color, 29, 30+direction), y, x] = 1

    @staticmethod
    def draw_east(grid, x, y):
        grid[0, 9, y, x] = grid[0, 13, y, x+1] = 1

    @torch.no_grad()
    def test_complete_visible_component_excludes_one_way_markers(self):
        grid = self.board()
        for x in range(4, 24):
            self.draw_east(grid, x, 9)
        grid[0, 9, 9, 24] = 1
        board = grid.flatten(2)
        directions = board[:, 30:38].argmax(dim=1)
        approaches = self.features.neighbors[self.features.service_cells, directions]
        labels, *_ = self.features.visible_components(board, directions, approaches)
        row = labels[0, 9*WIDTH:10*WIDTH]
        self.assertTrue(torch.equal(row[4:25], row[4].expand(21)))
        self.assertNotEqual(row[24].item(), row[25].item())

    @torch.no_grad()
    def test_bare_approach_does_not_count_as_service(self):
        grid = self.board()
        self.building(grid, 5, 5, 19, 0, 0)
        self.building(grid, 7, 5, 20, 0, 4)
        self.building(grid, 10, 10, 20, 0, 4)
        self.assertFalse(self.features.service_features(grid)[-2].item())
        self.draw_east(grid, 5, 5)
        self.assertFalse(self.features.service_features(grid)[-2].item())
        self.draw_east(grid, 6, 5)
        self.assertTrue(self.features.service_features(grid)[-2].item())

    @torch.no_grad()
    def test_farther_same_color_destination_retains_progress_and_urgency(self):
        grid = self.board()
        self.building(grid, 10, 10, 19, 0, 0)
        self.building(grid, 13, 10, 20, 0, 4)
        self.building(grid, 15, 13, 20, 0, 4)
        grid[0, 41, 13, 15] = .75
        action = edge_action((11, 10), (12, 11))-1
        advance, joins, urgency, active, _, _ = self.features.service_features(grid)
        self.assertTrue(active.item())
        self.assertEqual(advance[0, action].item(), 1.)
        self.assertEqual(joins[0, action].item(), 0.)
        self.assertEqual(urgency[0, action].item(), .75)
        grid[0, 21, 13, 15] = 0
        grid[0, 23, 13, 15] = 1
        advance, _, urgency, *_ = self.features.service_features(grid)
        self.assertEqual(advance[0, action].item(), 0.)
        self.assertEqual(urgency[0, action].item(), 0.)


if __name__ == '__main__':
    unittest.main()

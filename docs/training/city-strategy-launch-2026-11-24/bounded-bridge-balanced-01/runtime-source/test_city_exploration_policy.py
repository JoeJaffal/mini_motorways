import unittest
import gymnasium as gym
import numpy as np
import torch
from city_learning_policy import CityLearningPolicy
from city_exploration_policy import CityResidualExplorationFeatures
from city_road_policy import ROAD_SLOTS
from city_road_pilot import edge_action
import test_city_network_service as fixtures
from visible_observation import observation_space


class CityExplorationTests(unittest.TestCase):
    def test_mask_wait_mass_and_opening_survive_temperature(self):
        torch.set_num_threads(1)
        space=observation_space()
        policy=CityLearningPolicy(space,gym.spaces.Discrete(1+ROAD_SLOTS),lambda _:1e-4,
            features_extractor_class=CityResidualExplorationFeatures,normalize_images=False)
        grid=torch.zeros((1,*space['grid'].shape));grid[:,(0,1,18)]=1
        for x,y,kind,direction in [(5,5,19,0),(7,5,20,4),(10,10,20,4)]:
            fixtures.CityNetworkServiceTests.building(grid,x,y,kind,0,direction)
        attached=grid.clone()
        for x in (5,6):fixtures.CityNetworkServiceTests.draw_east(attached,x,5)
        obs={'grid':torch.cat((grid,attached)),'global':torch.zeros((2,*space['global'].shape)),
             'motorways':torch.zeros((2,*space['motorways'].shape))}
        mask=np.zeros((2,1+ROAD_SLOTS),bool);mask[:,[0,edge_action((5,5),(6,5)),edge_action((6,5),(7,5)),edge_action((20,20),(21,20))]]=True
        feature=policy.features_extractor
        with torch.no_grad():
            feature.growth_road_temperature.fill_(1.)
            p=policy.get_distribution(obs,action_masks=mask).distribution.probs.clone()
            feature.growth_road_temperature.fill_(20.)
            q=policy.get_distribution(obs,action_masks=mask).distribution.probs.clone()
        torch.testing.assert_close(p[0],q[0],atol=0,rtol=0)
        torch.testing.assert_close(p[:,0],q[:,0],atol=1e-6,rtol=0)
        self.assertTrue(torch.equal(q[~torch.as_tensor(mask)],torch.zeros_like(q[~torch.as_tensor(mask)])))
        self.assertFalse(torch.equal(p[1,1:],q[1,1:]))
        mask[:,1:]=False
        dist=policy.get_distribution(obs,action_masks=mask)
        self.assertTrue(torch.isfinite(dist.distribution.probs).all())
        torch.testing.assert_close(dist.distribution.probs[:,0],torch.ones(2))

if __name__=='__main__':unittest.main()

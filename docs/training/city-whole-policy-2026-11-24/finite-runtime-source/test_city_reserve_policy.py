import unittest
import gymnasium as gym
import torch
from city_reserve_policy import CityReservePolicy,CityReserveFeatures,CityVisibleReserveFeatures
from unittest.mock import patch
from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS
from visible_observation import observation_space

class ReservePolicyTests(unittest.TestCase):
    def test_trainable_set_and_stock_decode(self):
        torch.set_num_threads(1)
        p=CityReservePolicy(observation_space(),gym.spaces.Discrete(ROAD_SLOTS+1),lambda _: .03,
            features_extractor_class=CityReserveFeatures,optimizer_class=RelativeRateAdam,normalize_images=False)
        self.assertEqual([n for n,v in p.named_parameters() if v.requires_grad],
            ['features_extractor.growth_reserve_wait.weight','value_net.0.weight','value_net.0.bias','value_net.2.weight','value_net.2.bias'])
        f=p.features_extractor
        def context(grid):
            yes=torch.ones((len(grid),1),dtype=torch.bool);no=~yes
            return None,None,None,no,yes,yes
        f.service_features=context
        obs={'grid':torch.zeros((2,*observation_space()['grid'].shape)),
             'global':torch.zeros((2,*observation_space()['global'].shape))}
        obs['global'][:,0]=torch.tensor([2/102,8/108])
        ev=f.reserve_evidence(obs)
        torch.testing.assert_close(ev[:,1],torch.tensor([.25,1.]))
        self.assertEqual(f.growth_reserve_wait.weight.count_nonzero(),0)

    def test_missing_progress_is_not_a_visible_blocker(self):
        torch.set_num_threads(1)
        f=CityVisibleReserveFeatures(observation_space())
        def pending_without_local_progress(grid):
            yes=torch.ones((len(grid),1),dtype=torch.bool);no=~yes
            return None,None,None,no,yes,no
        f.service_features=pending_without_local_progress
        obs={'grid':torch.zeros((1,*observation_space()['grid'].shape)),
             'global':torch.zeros((1,*observation_space()['global'].shape))}
        obs['global'][0,0]=2/102
        with patch('city_reserve_policy.MidgameTimingFeatures.waiting_context',return_value=torch.tensor([[False]])):
            self.assertEqual(f.reserve_evidence(obs).count_nonzero(),0)
        with patch('city_reserve_policy.MidgameTimingFeatures.waiting_context',return_value=torch.tensor([[True]])):
            torch.testing.assert_close(f.reserve_evidence(obs)[0,4:],torch.tensor([1.,.25]))

if __name__=='__main__':unittest.main()

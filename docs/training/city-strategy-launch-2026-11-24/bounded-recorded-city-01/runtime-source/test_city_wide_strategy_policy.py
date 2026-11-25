import unittest
import gymnasium as gym
import torch
from torch import nn
from city_wide_strategy_policy import CityWideStrategyFeatures,CityWideStrategyPolicy
from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS
from visible_observation import observation_space

class WideStrategyTests(unittest.TestCase):
    def test_shapes_freezing_and_long_range_gradient(self):
        torch.set_num_threads(1);space=observation_space()
        p=CityWideStrategyPolicy(space,gym.spaces.Discrete(ROAD_SLOTS+1),lambda _: .003,
            features_extractor_class=CityWideStrategyFeatures,optimizer_class=RelativeRateAdam,normalize_images=False)
        names=[n for n,v in p.named_parameters() if v.requires_grad]
        self.assertEqual(len(names),30)
        self.assertTrue(all(n.startswith('value_net.') or n.startswith('features_extractor.growth_strategy_') for n in names))
        obs={k:torch.zeros((1,*v.shape)) for k,v in space.spaces.items()}
        f=p.features_extractor(obs)
        self.assertEqual(f.shape,(1,p.features_extractor.features_dim))
        self.assertTrue(torch.isfinite(f).all())
        self.assertEqual(p.value_net(p.mlp_extractor.forward_critic(f)).shape,(1,1))
        self.assertEqual(p.action_net(f).shape,(1,2*ROAD_SLOTS+2))
        convs=[layer for layer in p.features_extractor.growth_strategy_spatial if isinstance(layer,nn.Conv2d)]
        with torch.no_grad():
            for layer in convs:layer.weight.zero_();layer.bias.zero_()
            convs[0].weight[0,19,0,0]=1
            for layer in convs[1:]:layer.weight[0,0,1,2 if layer.dilation==(8,8) else 1]=1
        grid=torch.zeros((1,*space['grid'].shape));grid[0,19,10,18]=1;grid.requires_grad_()
        value=p.features_extractor.growth_strategy_spatial(grid)[0,0,10,10]
        self.assertGreater(value.item(),0);value.backward()
        self.assertGreater(grid.grad[0,19,10,18].item(),0)

if __name__=='__main__':unittest.main()

import unittest
import gymnasium as gym
import torch
from city_strategy_policy import CityStrategyFeatures,CityStrategyPolicy,STRATEGY_CONTEXT
from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS
from visible_observation import observation_space

class CityStrategyTests(unittest.TestCase):
    def test_trainable_set_and_head_shapes(self):
        torch.set_num_threads(1)
        space=observation_space()
        policy=CityStrategyPolicy(space,gym.spaces.Discrete(ROAD_SLOTS+1),lambda _: .003,
            features_extractor_class=CityStrategyFeatures,optimizer_class=RelativeRateAdam,normalize_images=False)
        names=[n for n,p in policy.named_parameters() if p.requires_grad]
        self.assertTrue(names)
        self.assertTrue(all(n.startswith('value_net.') or n.startswith('features_extractor.growth_strategy_') for n in names))
        self.assertEqual(len(names),12)
        self.assertEqual([g['lr_scale'] for g in policy.optimizer.param_groups],[1.,.3,.1])
        for layer in (policy.features_extractor.growth_strategy_wait[-1],policy.features_extractor.growth_strategy_roads[-1]):
            self.assertEqual(layer.weight.count_nonzero(),0);self.assertEqual(layer.bias.count_nonzero(),0)
        obs={k:torch.zeros((1,*v.shape)) for k,v in space.spaces.items()}
        features=policy.features_extractor(obs)
        self.assertEqual(features.shape,(1,policy.features_extractor.features_dim))
        self.assertEqual(policy.value_net(policy.mlp_extractor.forward_critic(features)).shape,(1,1))
        logits=policy.action_net(features)
        self.assertEqual(logits.shape,(1,2*ROAD_SLOTS+2))
        self.assertTrue(torch.isfinite(logits).all())

if __name__=='__main__':unittest.main()

import unittest
import gymnasium as gym
import torch
from city_relational_policy import CityDemandRelationsFeatures,CityRelationalPolicy,RelativeRateAdam
from city_road_pilot import edge_action
from city_road_policy import ROAD_SLOTS
from visible_observation import observation_space
import test_city_network_service as fixtures


class CityRelationTests(unittest.TestCase):
    def test_supply_is_color_matched_and_pressure_is_visible(self):
        torch.set_num_threads(1)
        space=observation_space();f=CityDemandRelationsFeatures(space)
        grid=torch.zeros((1,*space['grid'].shape));grid[:,(0,1,18)]=1
        b=fixtures.CityNetworkServiceTests.building;east=fixtures.CityNetworkServiceTests.draw_east
        b(grid,5,5,19,0,0);b(grid,5,6,19,0,0);b(grid,10,5,20,0,4)
        for x,y in [(5,5),(6,5),(5,6),(8,5),(9,5)]:east(grid,x,y)
        grid[0,11,5,6]=grid[0,15,6,6]=1
        grid[0,57,5,9]=.5;grid[0,41,5,10]=.5
        slot=edge_action((7,5),(8,5))-1
        with torch.no_grad():v=f.relation_evidence(grid)[0,slot]
        self.assertEqual(v[0].item(),2.)
        self.assertEqual(v[2].item(),0.)
        self.assertEqual(v[4].item(),.25)
        self.assertEqual(v[8].item(),1.)
        grid[0,21,5,10]=0;grid[0,22,5,10]=1
        with torch.no_grad():v=f.relation_evidence(grid)[0,slot]
        self.assertEqual(v[0].item(),0.)

    def test_only_relation_actor_learns_and_optimizer_scales_critic(self):
        torch.set_num_threads(1)
        p=CityRelationalPolicy(observation_space(),gym.spaces.Discrete(ROAD_SLOTS+1),lambda _: .01,
            features_extractor_class=CityDemandRelationsFeatures,normalize_images=False,
            optimizer_class=RelativeRateAdam)
        self.assertEqual([n for n,v in p.features_extractor.named_parameters() if v.requires_grad],['growth_relations.weight'])
        self.assertEqual(p.features_extractor.growth_relations.weight.count_nonzero().item(),0)
        x=torch.nn.Parameter(torch.tensor(0.));y=torch.nn.Parameter(torch.tensor(0.))
        opt=RelativeRateAdam([dict(params=[x],lr_scale=1),dict(params=[y],lr_scale=.01)],lr=.01)
        x.grad=torch.ones_like(x);y.grad=torch.ones_like(y);opt.step()
        self.assertAlmostEqual((x/y).detach().item(),100.,places=4)
        self.assertEqual([g['lr'] for g in opt.param_groups],[.01,.01])

if __name__=='__main__':unittest.main()

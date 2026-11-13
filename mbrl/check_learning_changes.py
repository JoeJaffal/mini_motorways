"""Regression checks for risk inputs, return-sign search and checkpoint migration."""
from __future__ import annotations
import copy
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torch import nn

from actions import Candidate, _features, candidates, candidate_matrix
from alphazero import Edge, Network, Node, ReplayMixture, Sample, search, search_value, train_batch
from environment import GRID_CHANNELS, visible_grid, visible_scalar, TrafficEnv
from check_requested_changes import OutcomeHost
from smoke import observation


class LearningChanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_search_is_independent_of_common_value_offset(self):
        requests = [{"command":"wait"}] + [
            {"command":"build","tool":"Road","x":i,"y":0} for i in range(1,12)]
        items = [Candidate(r,str(i),_features(0)) for i,r in enumerate(requests)]
        priors = [.4] + [.6/11]*11
        class Branch:
            env = SimpleNamespace(host=None)
            def restore(self, *args): pass
            def transition(self, request, seed):
                i=request.get("x",0)
                reward=100.0 if useful_build and i==1 else -.1*i
                return SimpleNamespace(observation={},reward=reward,terminated=False,
                                       truncated=False,accepted=True)
        class Pool(Branch):
            def __init__(self, workers):
                self.workers=workers
                self.branches=[Branch() for _ in range(workers)]
            def run(self,jobs): return [fn(*args) for fn,args in jobs]
        for useful_build in (False,True):
            for workers in (1,2,3):
                policies=[]
                for offset in (-100.,0.,100.):
                    def node(*args,**kwargs):
                        return Node({},items,offset,[Edge(p) for p in priors])
                    with patch("alphazero.make_node",side_effect=node):
                        _,visits,stats=search(SimpleNamespace(value_scale=100,eval=lambda:None),
                            SimpleNamespace(observation={},host=None),Pool(workers),[],8,1,
                            random.Random(4),discount=1.0)
                    self.assertEqual(visits.sum(),8)
                    self.assertTrue(np.isfinite(stats["rootPolicy"]).all())
                    self.assertEqual(int(np.argmax(stats["rootPolicy"])),1 if useful_build else 0)
                    policies.append(stats["rootPolicy"])
                self.assertTrue(all(np.allclose(policies[0],p) for p in policies[1:]))

    def test_pending_work_uses_the_same_baseline(self):
        edge=Edge(.5)
        self.assertEqual(search_value(edge,-100),-100)
        edge.in_flight=2
        self.assertEqual(search_value(edge,-100),-100)
        edge.visits=1;edge.total=-70
        self.assertEqual(search_value(edge,-100),-90)
        edge.in_flight=0
        self.assertEqual(search_value(edge,-100),-70)

    def test_risk_inputs_distinguish_capacity_load_and_timer(self):
        obs=observation()
        shop=obs["buildings"][1]
        shop.update(width=2,height=2,demand=6,demandCapacity=6,overcrowdedFor=25)
        original=visible_grid(obs)
        self.assertEqual(original.shape,(42,30,50))
        self.assertTrue(np.allclose(original[39:,5:7,12:14],np.array([.6,1.,.5])[:,None,None]))
        self.assertFalse(original[39:,:5,:].any())
        changed=copy.deepcopy(obs)
        changed["buildings"][1].update(demandCapacity=9,overcrowdedFor=49)
        encoded=visible_grid(changed)
        self.assertTrue(np.array_equal(original[:39],encoded[:39]))
        self.assertFalse(np.array_equal(original[39:],encoded[39:]))
        self.assertTrue(np.array_equal(visible_scalar(obs),visible_scalar(changed)))
        obs["playableXMax"]=12
        self.assertFalse(visible_grid(obs)[39:].any())

    def test_legacy_weights_preserve_predictions_and_new_inputs_can_learn(self):
        torch.manual_seed(8)
        old=Network(value_scale=100)
        old.grid[0]=nn.Conv2d(39,32,5,stride=2,padding=2)
        new=Network(value_scale=100)
        new.load_compatible_state_dict(old.state_dict())
        grid=torch.tensor(visible_grid(observation())[None])
        scalar=torch.tensor(visible_scalar(observation())[None])
        options,mask=candidate_matrix(candidates(observation()))
        options=torch.tensor(options[None]);mask=torch.tensor(mask[None])
        with torch.no_grad():
            expected=old(grid[:,:39],scalar,options,mask)
            actual=new(grid,scalar,options,mask)
        self.assertTrue(all(torch.allclose(a,b,atol=2e-5) for a,b in zip(expected,actual)))
        self.assertFalse(new.grid[0].weight[:,39:].any())
        new(grid,scalar,options,mask)[0].sum().backward()
        self.assertGreater(new.grid[0].weight.grad[:,39:].abs().sum(),0)

    def test_trip_multiplier_preserves_raw_components(self):
        for multiplier in (1.,10.):
            env=TrafficEnv(OutcomeHost(demand=4,trips=2),trip_reward=multiplier)
            env.reset("LosAngeles",42)
            step=env.step({"command":"wait"})
            self.assertEqual(step.components["trips"],2)
            self.assertAlmostEqual(step.reward,2*multiplier+.2-.04)

    def test_full_replay_and_optimizer_resume_matches_next_update(self):
        torch.manual_seed(3)
        obs=observation()
        options,mask=candidate_matrix(candidates(obs))
        policy=np.zeros(len(mask),dtype=np.float32);policy[0]=1
        sample=Sample(visible_grid(obs),visible_scalar(obs),options,mask,policy,10,50)
        replay=ReplayMixture(6000)
        for city in ("Tokyo","Beijing","LosAngeles"):
            replay.add([copy.deepcopy(sample)],{"map":city,"trips":10})
        model=Network(value_scale=100)
        optimizer=torch.optim.Adam(model.parameters(),lr=3e-4,weight_decay=1e-5)
        rng=random.Random(6)
        train_batch(model,optimizer,replay,batch_size=2,rng=rng)
        state=copy.deepcopy({"model":model.state_dict(),"optimizer":optimizer.state_dict(),
                             "replay":replay.state_dict(),"rng":rng.getstate()})
        train_batch(model,optimizer,replay,batch_size=2,rng=rng)
        restored=Network(value_scale=100);restored.load_state_dict(state["model"])
        opt=torch.optim.Adam(restored.parameters(),lr=3e-4,weight_decay=1e-5)
        opt.load_state_dict(state["optimizer"])
        memory=ReplayMixture();memory.load_state_dict(state["replay"])
        rng2=random.Random();rng2.setstate(state["rng"])
        train_batch(restored,opt,memory,batch_size=2,rng=rng2)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(model.parameters(),restored.parameters())))
        self.assertEqual(rng.getstate(),rng2.getstate())


if __name__=="__main__":
    unittest.main()

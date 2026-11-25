"""Forward-only integration/checkpoint tests. Never calls update()."""
from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
import numpy as np
import torch
import gymnasium as gym
from visible_observation import observation_space
from hierarchy_policy import HierarchyPolicy
from hierarchy_rollout import TokenTransition,InferenceBatch,policy_fingerprint
from hierarchy_batches import prepare_batches
from hierarchy_updater import HierarchyUpdater
from hierarchy_checkpoint import save_checkpoint,load_checkpoint

class IntegrationChecks(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(61)
        space=observation_space();space.spaces['focus']=gym.spaces.Box(0,1,(2,30,50),np.float32);space.spaces['context']=gym.spaces.Box(0,1,(8,),np.float32)
        self.policy=HierarchyPolicy(space,gym.spaces.Discrete(1501),lambda _:3e-4)
        self.obs={k:np.zeros(v.shape,np.float32) for k,v in space.spaces.items()}
    def token(self,role,next_role,reward=0,terminated=False):
        obs={k:v.copy() for k,v in self.obs.items()};obs['context'][['primary','secondary','executor'].index(role)]=1
        return TokenTransition(obs,np.ones(1501,bool),0,-1.,1.,role,next_role,reward,0,0,terminated,False,None,'v1',(None,None))
    def collection(self):
        records=(self.token('primary','secondary'),self.token('secondary','executor'),self.token('executor','primary',3,True))
        return InferenceBatch(records,self.obs,0.,'v1',policy_fingerprint(self.policy),3.)
    def test_returns_and_joint_probabilities_reach_both_losses_without_updates(self):
        before=policy_fingerprint(self.policy);batches=prepare_batches(self.collection(),device='cpu')
        self.assertEqual({b['role'] for b in batches},{'manager','executor'})
        self.assertAlmostEqual(sum(b['level_weight'] for b in batches),1)
        for b in batches:
            self.assertEqual(b['returns'].item(),3)
            if b['role']=='manager':self.assertEqual(b['old_log_probability'].item(),-2)
            with torch.inference_mode():loss,_=HierarchyUpdater(self.policy).loss(b)
            self.assertTrue(torch.isfinite(loss))
        self.assertEqual(before,policy_fingerprint(self.policy));self.assertFalse(self.policy.optimizer.state)
    def test_partial_focus_cannot_be_updated(self):
        batch=self.collection()
        with self.assertRaisesRegex(ValueError,'unfinished focus'):
            prepare_batches(replace(batch,transitions=batch.transitions[:2]),device='cpu')
    def test_trusted_checkpoint_roundtrip_and_config_rejection(self):
        before=policy_fingerprint(self.policy);config={'fixture':'untrained'}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'checkpoint.pt'
            save_checkpoint(path,self.policy,config=config,counters={'updates':0})
            self.assertEqual(load_checkpoint(path,self.policy,expected_config=config),{'updates':0})
            with self.assertRaises(ValueError):load_checkpoint(path,self.policy,expected_config={'different':True})
            self.assertFalse(path.with_name(path.name+'.tmp').exists())
        self.assertEqual(before,policy_fingerprint(self.policy));self.assertFalse(self.policy.optimizer.state)
if __name__=='__main__':unittest.main()

"""Bounded inference/collection checks. No learning or optimizer steps."""
import argparse
import math
import sys
import unittest

import numpy as np
import torch
from connection_practice import ConnectionPractice,WAIT,HANDOFF,NONE
from hierarchy_policy import HierarchyPolicy
from hierarchy_rollout import FrozenInferenceCollector,FocusAssembler,policy_fingerprint

DOTNET='dotnet';DLL=None


class ScriptPolicy:
    """A deterministic test double, not a trainable model."""
    def __init__(self,executor=WAIT):self.executor=executor;self.fixture_version=1
    def state_dict(self):return {'fixture_version':torch.tensor(float(self.fixture_version))}
    def set_training_mode(self,_):pass
    def obs_to_tensor(self,obs):return {k:torch.as_tensor(v[None]) for k,v in obs.items()},False
    def forward(self,obs,deterministic=False,action_masks=None):
        role=int(obs['context'][0,:3].argmax())
        action=(0,NONE,self.executor)[role]
        assert action_masks[action]
        return torch.tensor([action]),torch.tensor([[1.]]),torch.tensor([-math.log(np.count_nonzero(action_masks))])
    def predict_values(self,_):return torch.tensor([[7.]])


class CollectorChecks(unittest.TestCase):
    def setUp(self):self.env=ConnectionPractice(dotnet=DOTNET,host_dll=DLL)
    def tearDown(self):self.env.close()

    def test_actual_untrained_policy_records_its_own_masked_probabilities(self):
        torch.set_num_threads(1);torch.manual_seed(103)
        policy=HierarchyPolicy(self.env.observation_space,self.env.action_space,lambda _:0.)
        before=policy_fingerprint(policy)
        collector=FrozenInferenceCollector(self.env,policy,seed=42)
        batch=collector.collect(max_tokens=6,policy_version='untrained-fixture',deterministic=True)
        self.assertEqual(len(batch.transitions),6)
        self.assertEqual(policy_fingerprint(policy),before)
        self.assertEqual(batch.score_delta,sum(t.reward for t in batch.transitions))
        self.assertFalse(policy.optimizer.state)
        for t in batch.transitions:
            self.assertTrue(t.mask[t.action])
            with torch.inference_mode():
                obs,_=policy.obs_to_tensor(t.observation)
                value,logp,_=policy.evaluate_actions(obs,torch.tensor([t.action]),action_masks=t.mask)
            self.assertAlmostEqual(logp.item(),t.log_probability,places=6)
            self.assertAlmostEqual(value.item(),t.value,places=6)

    def test_true_task_end_has_zero_bootstrap(self):
        self.env.seconds=1
        collector=FrozenInferenceCollector(self.env,ScriptPolicy(),seed=1)
        batch=collector.collect(max_tokens=10,policy_version='script-fixture')
        self.assertEqual(len(batch.transitions),3)
        self.assertTrue(batch.transitions[-1].terminated)
        self.assertFalse(batch.transitions[-1].truncated)
        self.assertEqual(batch.bootstrap_value,0)
        assembler=FocusAssembler();assembler.append(batch.transitions)
        self.assertTrue(assembler.completed[0].terminated)

    def test_operational_interruption_retains_live_state_bootstrap(self):
        self.env.max_paused_tokens=3
        collector=FrozenInferenceCollector(self.env,ScriptPolicy(HANDOFF),seed=2)
        batch=collector.collect(max_tokens=10,policy_version='script-fixture')
        self.assertFalse(batch.transitions[-1].terminated)
        self.assertTrue(batch.transitions[-1].truncated)
        self.assertEqual(batch.bootstrap_value,7)

    def test_behavior_version_guard_and_option_boundary(self):
        policy=ScriptPolicy(HANDOFF)
        collector=FrozenInferenceCollector(self.env,policy,seed=3)
        collector.collect(max_tokens=1,policy_version='v1')
        policy.fixture_version=2
        with self.assertRaisesRegex(RuntimeError,'without a new policy version'):
            collector.collect(max_tokens=1,policy_version='v1')
        with self.assertRaisesRegex(RuntimeError,'within a focus'):
            collector.collect(max_tokens=1,policy_version='v2')
        policy.fixture_version=1
        collector.collect(max_tokens=2,policy_version='v1')
        self.assertEqual(self.env.role,'primary')
        policy.fixture_version=2
        batch=collector.collect(max_tokens=1,policy_version='v2')
        self.assertEqual(batch.policy_version,'v2')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dotnet',default='dotnet');p.add_argument('--dll')
    args,rest=p.parse_known_args();DOTNET,DLL=args.dotnet,args.dll
    unittest.main(argv=[sys.argv[0]]+rest)

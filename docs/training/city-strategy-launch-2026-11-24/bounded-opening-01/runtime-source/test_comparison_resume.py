"""Frozen comparison and state restoration; never calls backward or optimizer.step."""
import copy,hashlib,os,random,tempfile,unittest
from pathlib import Path
from time import monotonic
import numpy as np
import torch
from connection_practice import ConnectionPractice
from hierarchy_policy import HierarchyPolicy
from hierarchy_checkpoint import save_checkpoint
from hierarchy_rollout import policy_fingerprint
from checkpoint_tools import LEGACY_RUNNER,read_checkpoint,load_frozen,resume_checkpoint
from compare_stage1 import evaluate,paired
from practice_replay import identity
DOTNET=os.environ.get('STAGE1_DOTNET','dotnet');DLL='simulation/Headless/bin/Release/net8.0/TrafficHost.dll'
class Checks(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.env=ConnectionPractice(dotnet=DOTNET,host_dll=DLL,stage='one-gap-compact',split='validation')
        self.policy=HierarchyPolicy(self.env.observation_space,self.env.action_space,lambda _:3e-4)
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'fixture.pt'
        self.config=dict(stage='one-gap-compact',environment=identity(self.env),source_hashes={
            name:hashlib.sha256(Path('training',name).read_bytes()).hexdigest() for name in ('train_parallel_stage1.py','hierarchy_policy.py','checkpoint_tools.py')})
    def tearDown(self):self.env.close();self.directory.cleanup()
    def save(self,config=None):
        save_checkpoint(self.path,self.policy,config=config or self.config,counters=dict(tokens=4096,updates=8,version=2,episodes=3,worker_episodes=[3]))
    def test_restore_parameters_adam_counters_rng_and_legacy_migration(self):
        # Synthetic optimizer history tests restoration without performing learning.
        param=next(self.policy.parameters())
        self.policy.optimizer.state[param]=dict(step=torch.tensor(8.),exp_avg=torch.full_like(param,.125),exp_avg_sq=torch.full_like(param,.25))
        self.save();expected=torch.rand(5);expected_numpy=np.random.rand(3);expected_python=random.random()
        other=HierarchyPolicy(self.env.observation_space,self.env.action_space,lambda _:3e-4)
        payload,counters=resume_checkpoint(self.path,other,self.config)
        self.assertEqual(counters['updates'],8);self.assertEqual(policy_fingerprint(other),payload['policy_sha256'])
        state=other.optimizer.state[next(other.parameters())]
        self.assertEqual(state['step'].item(),8);self.assertTrue(torch.all(state['exp_avg']==.125))
        torch.testing.assert_close(torch.rand(5),expected)
        np.testing.assert_equal(np.random.rand(3),expected_numpy);self.assertEqual(random.random(),expected_python)
        legacy=copy.deepcopy(self.config);legacy['source_hashes']['train_parallel_stage1.py']=LEGACY_RUNNER
        del legacy['source_hashes']['checkpoint_tools.py'];self.save(legacy)
        resume_checkpoint(self.path,other,self.config)
    def test_reject_incompatible_stage_and_corrupt_weights(self):
        self.save()
        config=copy.deepcopy(self.config);config['stage']='clear'
        with self.assertRaisesRegex(ValueError,'configuration'):resume_checkpoint(self.path,self.policy,config)
        payload=read_checkpoint(self.path);next(iter(payload['parameters'].values())).add_(1)
        torch.save(payload,self.path)
        with self.assertRaisesRegex(ValueError,'hash'):read_checkpoint(self.path)
    def test_frozen_paired_sampling_matches_identical_models(self):
        self.save();before=policy_fingerprint(self.policy);self.env.seconds=1
        rows=evaluate(self.policy,[self.env],[20000,20001],deadline=monotonic()+60,max_decisions=300)
        second=HierarchyPolicy(self.env.observation_space,self.env.action_space,lambda _:0.)
        load_frozen(self.path,second,identity(self.env))
        other=evaluate(second,[self.env],[20000,20001],deadline=monotonic()+60,max_decisions=300)
        self.assertEqual(rows,other);self.assertEqual(paired(rows,other)['ties'],2)
        self.assertEqual(policy_fingerprint(self.policy),before);self.assertFalse(self.policy.optimizer.state)
        self.assertFalse(second.optimizer.state)
    def test_external_caps_are_not_natural_completions(self):
        self.env.seconds=180
        rows=evaluate(self.policy,[self.env],[20000],deadline=monotonic()+60,max_decisions=1)
        self.assertFalse(rows[0]['natural']);self.assertEqual(rows[0]['ending'],'external_decision_limit')
        with self.assertRaises(TimeoutError):evaluate(self.policy,[self.env],[20000],deadline=monotonic()-1,max_decisions=1)
if __name__=='__main__':unittest.main(verbosity=2)

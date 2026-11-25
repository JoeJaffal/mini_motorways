"""Independent credit streams and parallel real-host inference, no updates."""
import os,unittest
from dataclasses import replace
from time import monotonic
import numpy as np
import torch
from connection_practice import ConnectionPractice
from hierarchy_rollout import TokenTransition,InferenceBatch,policy_fingerprint
from parallel_stage1 import ParallelCollector,parallel_batches

class ScriptPolicy:
    def state_dict(self):return {'fixture':torch.tensor(1.)}
    def set_training_mode(self,_):pass
    def obs_to_tensor(self,obs):
        batched=obs['context'].ndim==2
        return {k:torch.as_tensor(v if batched else v[None]) for k,v in obs.items()},batched
    def forward(self,obs,deterministic=False,action_masks=None):
        role=obs['context'][:,:3].argmax(1)
        actions=torch.where(role==1,1500,0)
        return actions,torch.ones((len(role),1)),torch.as_tensor(-np.log(np.count_nonzero(action_masks,axis=1)),dtype=torch.float32)
    def predict_values(self,obs):return torch.full((len(obs['context']),1),7.)


def stream(score):
    def t(role,nxt,reward=0,done=False):
        return TokenTransition({'x':np.zeros(1,np.float32)},np.ones(1501,bool),0,-1.,1.,role,nxt,reward,0,0,done,False,None,'v1',(None,None))
    return InferenceBatch((t('primary','secondary'),t('secondary','executor'),t('executor','primary',score,True)),{},0.,'v1','same',score)

class ParallelChecks(unittest.TestCase):
    def test_returns_do_not_cross_workers(self):
        batches=parallel_batches([(0,stream(3)),(1,stream(10))],device='cpu',minibatch_size=128)
        self.assertEqual({b['role'] for b in batches},{'manager','executor'})
        self.assertAlmostEqual(sum(b['level_weight'] for b in batches),1)
        for b in batches:
            np.testing.assert_array_equal(b['returns'].numpy(),[3,10])
            self.assertAlmostEqual(b['advantages'].mean().item(),0,places=6)
            self.assertEqual(b['returns'].device.type,'cpu')
    def test_mixed_versions_or_duplicate_workers_fail(self):
        with self.assertRaises(ValueError):parallel_batches([(0,stream(1)),(1,replace(stream(2),policy_version='v2'))],device='cpu',minibatch_size=2)
        with self.assertRaises(ValueError):parallel_batches([(0,stream(1)),(0,stream(2))],device='cpu',minibatch_size=2)
    def make(self):
        envs=[]
        try:
            for _ in range(2):
                env=ConnectionPractice(dotnet=os.environ.get('STAGE1_DOTNET','dotnet'),host_dll='simulation/Headless/bin/Release/net8.0/TrafficHost.dll')
                env.seconds=1;envs.append(env)
            policy=ScriptPolicy();events=[]
            collector=ParallelCollector(envs,policy,seeds=[42,43],on_transition=lambda i,t,info:events.append((i,t)))
            return envs,policy,collector,events
        except BaseException:
            for e in envs:e.close()
            raise
    def test_real_hosts_batched_roles_end_independently(self):
        envs,policy,collector,events=self.make()
        try:
            before=policy_fingerprint(policy)
            records=collector.collect(target_tokens=32,hard_limit=64,deadline=monotonic()+30,policy_version='v1')
            self.assertEqual([i for i,_ in records],[0,1])
            self.assertEqual(len(events),6)
            for i,b in records:
                self.assertEqual([t.role for t in b.transitions],['primary','secondary','executor'])
                self.assertTrue(b.transitions[-1].terminated);self.assertEqual(b.bootstrap_value,0)
                self.assertEqual(envs[i].raw['time'],1)
            self.assertEqual(policy_fingerprint(policy),before)
        finally:
            collector.close()
            for e in envs:e.close()
    def test_global_cap_cannot_overrun_by_vector_width(self):
        envs,_,collector,events=self.make()
        try:
            with self.assertRaises(TimeoutError):collector.collect(target_tokens=32,hard_limit=1,deadline=monotonic()+30,policy_version='v1')
            self.assertEqual(len(events),1)
        finally:
            collector.close()
            for e in envs:e.close()

if __name__=='__main__':unittest.main()

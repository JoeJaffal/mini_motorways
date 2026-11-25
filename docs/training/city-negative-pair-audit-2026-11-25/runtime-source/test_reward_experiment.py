"""Reward algebra, visible connectivity and learner integration; no learning."""
import copy,os,tempfile,unittest
from pathlib import Path
from time import monotonic
import numpy as np
import torch
from connection_practice import ConnectionPractice,DRAW,WAIT,NONE
from environment import DIRS
from test_one_gap import gap
from test_connection_practice import enter_executor
from hierarchy_policy import HierarchyPolicy
from hierarchy_rollout import FrozenInferenceCollector,FocusAssembler,TokenTransition,InferenceBatch
from hierarchy_batches import prepare_batches
from hierarchy_updater import HierarchyUpdater
from practice_replay import PracticeRecorder,verify
from practice_reward import reward_parts,connection_potential
DOTNET=os.environ.get('STAGE1_DOTNET','dotnet');DLL='simulation/Headless/bin/Release/net8.0/TrafficHost.dll'
def edit(env,a,b):
    enter_executor(env,primary=a[1]*50+a[0])
    env.step(DRAW);env.step(a[1]*50+a[0])
    result=env.step(DIRS.index((b[0]-a[0],b[1]-a[1])))
    assert result[4]['accepted'] and env.raw['time']==0
    return result

class RewardChecks(unittest.TestCase):
    def make(self,mode='connection-economy',split='train'):
        return ConnectionPractice(dotnet=DOTNET,host_dll=DLL,stage='one-gap-compact',reward_mode=mode,split=split)
    def test_algebra_terminal_and_no_refund(self):
        self.assertAlmostEqual(reward_parts('connection-economy',trips=0,before=0,after=1,spent=1,terminated=False)[0],.24)
        self.assertEqual(reward_parts('connection-economy',trips=0,before=1,after=1,spent=0,terminated=False)[0],0)
        self.assertEqual(reward_parts('connection-economy',trips=0,before=1,after=1,spent=0,terminated=True)[0],-.25)
        self.assertEqual(reward_parts('score',trips=1,before=0,after=1,spent=20,terminated=True)[0],1)
        with self.assertRaises(ValueError):reward_parts('connection-economy',trips=0,before=0,after=0,spent=-1,terminated=False)
    def test_visible_reachability_and_repair_reward_varied_layouts(self):
        for split,seeds in [('train',range(42,52)),('validation',range(20000,20010))]:
            env=self.make(split=split)
            try:
                for seed in seeds:
                    env.reset(seed=seed);self.assertEqual(env.potential(),0)
                    a,b=gap(env);enter_executor(env,primary=a[1]*50+a[0])
                    result=edit(env,a,b)
                    self.assertAlmostEqual(result[1],.24);self.assertEqual(env.potential(),1)
                    self.assertEqual(result[4]['trip_reward'],0);self.assertAlmostEqual(result[4]['road_cost'],.01)
                    self.assertEqual(edit(env,a,b)[1],0)
                    changed=copy.deepcopy(env.raw);shop=next(x for x in changed['buildings'] if not x['isHouse'])
                    shop['color']=(shop['color']+1)%3
                    self.assertEqual(connection_potential(changed,env.practice_area),0)
                    changed=copy.deepcopy(env.raw);home=next(x for x in changed['buildings'] if x['isHouse'])
                    home['drivewayDirection']=(home['drivewayDirection']+1)%8
                    self.assertEqual(connection_potential(changed,env.practice_area),0)
            finally:env.close()
    def test_full_episode_terminal_correction_and_strict_replay(self):
        env=self.make()
        try:
            recorder=PracticeRecorder(env,seed=42);a,b=gap(env)
            for action in [a[1]*50+a[0],NONE,DRAW,a[1]*50+a[0],DIRS.index((b[0]-a[0],b[1]-a[1]))]:recorder.step(action)
            self.assertAlmostEqual(env.training_reward_total,.24)
            while not env.done:
                action=NONE if env.role=='secondary' else (a[1]*50+a[0] if env.role=='primary' else WAIT)
                result=recorder.step(action)
            self.assertGreaterEqual(env.raw['tripsCompleted'],3)
            self.assertEqual(env.potential(),0)
            self.assertAlmostEqual(env.shaping_total,0)
            self.assertAlmostEqual(env.training_reward_total,env.raw['tripsCompleted']-.01)
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/'trace.json';recorder.save(p);self.assertEqual(verify(p,DOTNET,DLL)['result'],'PASS')
        finally:env.close()
    def test_no_terminal_correction_on_operational_cut(self):
        env=self.make()
        try:
            env.reset(seed=42);a,b=gap(env);enter_executor(env,primary=a[1]*50+a[0]);edit(env,a,b)
            env.max_paused_tokens=env.paused_tokens+1
            _,reward,terminated,truncated,info=env.step(10)
            self.assertFalse(terminated);self.assertTrue(truncated)
            self.assertEqual(reward,0);self.assertEqual(env.potential(),1)
            self.assertAlmostEqual(env.training_reward_total,.24)
        finally:env.close()
    def test_negative_returns_prepare_finite_losses_and_collector_ledger(self):
        torch.set_num_threads(1);env=self.make()
        try:
            policy=HierarchyPolicy(env.observation_space,env.action_space,lambda _:3e-4)
            collector=FrozenInferenceCollector(env,policy,seed=42)
            batch=collector.collect(max_tokens=128,policy_version='v1')
            self.assertAlmostEqual(sum(t.reward for t in batch.transitions),env.expected_training_return())
            # A complete negative executor interval must survive assembly and both heads.
            obs=env.encode();mask=np.ones(1501,bool)
            def t(role,nxt,r=0):return TokenTransition(obs,mask,0,-1.,0.,role,nxt,r,0,0,False,False,None,'v1',(None,None))
            records=(t('primary','secondary'),t('secondary','executor'),t('executor','primary',-.01))
            f=InferenceBatch(records,obs,0.,'v1','fixture',0.)
            parts=prepare_batches(f,device='cpu',minibatch_size=16)
            self.assertEqual({b['role'] for b in parts},{'manager','executor'})
            updater=HierarchyUpdater(policy)
            for b in parts:
                self.assertLess(float(b['returns'][0]),0)
                with torch.inference_mode():self.assertTrue(torch.isfinite(updater.loss(b)[0]))
            self.assertFalse(policy.optimizer.state)
        finally:env.close()
    def test_score_mode_unchanged(self):
        env=self.make('score')
        try:
            env.reset(seed=42);a,b=gap(env);enter_executor(env,primary=a[1]*50+a[0])
            self.assertEqual(edit(env,a,b)[1],0)
            self.assertEqual(env.training_reward_total,0)
        finally:env.close()
if __name__=='__main__':unittest.main(verbosity=2)

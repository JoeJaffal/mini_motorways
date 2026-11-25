"""Compact curriculum/mask/counter/replay checks, no optimizer updates."""
import os,tempfile,unittest
from pathlib import Path
import numpy as np
from connection_practice import ConnectionPractice,DRAW,WAIT,NONE,CANCEL
from test_connection_practice import enter_executor,edit
from test_one_gap import gap
from practice_replay import PracticeRecorder,verify
from environment import DIRS
DOTNET=os.environ.get('STAGE1_DOTNET','dotnet')
DLL='simulation/Headless/bin/Release/net8.0/TrafficHost.dll'
class CompactChecks(unittest.TestCase):
    def make(self,split='train'):
        return ConnectionPractice(dotnet=DOTNET,host_dll=DLL,stage='one-gap-compact',split=split)
    def test_layouts_contained_and_repair_possible(self):
        for split,seeds in [('train',range(42,62)),('validation',range(20000,20020))]:
            env=self.make(split)
            try:
                for seed in seeds:
                    obs,_=env.reset(seed=seed);x0,x1,y0,y1=env.practice_bounds
                    self.assertEqual((x1-x0,y1-y0),(12,12))
                    self.assertEqual(env.practice_area.sum(),144)
                    np.testing.assert_array_equal(obs['grid'][0].ravel().astype(bool),env.practice_area)
                    self.assertEqual(env.action_masks()[:1500].sum(),144)
                    self.assertFalse(np.any(obs['grid'][:,~env.practice_area.reshape(30,50)]))
                    for i,b in enumerate(env.raw['connections']):
                        if b:self.assertTrue(env.practice_area[i])
                    a,b=gap(env);self.assertTrue(env.practice_area[a[1]*50+a[0]])
                    self.assertTrue(env.practice_area[b[1]*50+b[0]])
                    enter_executor(env,primary=a[1]*50+a[0])
                    result=edit(env,a,b)
                    self.assertEqual(result[4]['draw_commands'],1)
                    self.assertEqual(result[4]['changed_draws'],1)
                    self.assertEqual(result[4]['new_connections'],1)
                    enter_executor(env,primary=a[1]*50+a[0])
                    repeated=edit(env,a,b)
                    self.assertEqual(repeated[4]['no_change_draws'],1)
                    self.assertEqual(repeated[4]['road_units_spent'],0)
                    env._call(command='step',ticks=3600)
                    self.assertGreaterEqual(env.info()['trips'],3)
            finally:env.close()
    def test_random_actions_never_leave_arena_or_delete(self):
        env=self.make();rng=np.random.default_rng(52)
        try:
            env.reset(seed=42);initial=np.array(env.raw['connections'])
            with self.assertRaises(ValueError):env.step(int(np.flatnonzero(~env.practice_area)[0]))
            for _ in range(600):
                mask=env.action_masks()
                if env.role!='executor' or env.phase==1:
                    self.assertFalse(np.any(mask[:1500]&~env.practice_area))
                if env.role=='executor' and env.phase==2:
                    for d in np.flatnonzero(mask[:8]):
                        dx,dy=DIRS[d];x,y=env.first[0]+dx,env.first[1]+dy
                        self.assertTrue(env.practice_area[y*50+x])
                env.step(int(rng.choice(np.flatnonzero(mask))))
                now=np.array(env.raw['connections']);np.testing.assert_array_equal(now&initial,initial)
                for i,b in enumerate(now):
                    if b:self.assertTrue(env.practice_area[i])
                if env.done:break
        finally:env.close()
    def test_native_rewards_and_replay_with_compact_observation(self):
        env=self.make()
        try:
            recorder=PracticeRecorder(env,seed=42);a,b=gap(env)
            for action in [a[1]*50+a[0],NONE,DRAW,a[1]*50+a[0],DIRS.index((b[0]-a[0],b[1]-a[1]))]:recorder.step(action)
            rewards=0
            while not env.done:
                action=NONE if env.role=='secondary' else (a[1]*50+a[0] if env.role=='primary' else WAIT)
                rewards+=recorder.step(action)[1]
            self.assertGreaterEqual(rewards,3);self.assertEqual(rewards,env.raw['tripsCompleted'])
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/'trace.json';recorder.save(p);self.assertEqual(verify(p,DOTNET,DLL)['result'],'PASS')
        finally:env.close()
if __name__=='__main__':unittest.main(verbosity=2)

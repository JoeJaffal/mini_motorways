"""Draw-only curriculum checks; no learner or weight updates."""
import os,tempfile,unittest
from pathlib import Path
import numpy as np
from connection_practice import ConnectionPractice,DRAW,WAIT,HANDOFF,ERASE,REMOVE,NONE,CANCEL
from environment import DIRS
from test_one_gap import gap
from test_connection_practice import enter_executor,edit
from practice_replay import PracticeRecorder,verify
DOTNET=os.environ.get('STAGE1_DOTNET','dotnet')
DLL='simulation/Headless/bin/Release/net8.0/TrafficHost.dll'

class DrawOnlyChecks(unittest.TestCase):
    def make(self,stage='one-gap-draw-only'):
        return ConnectionPractice(dotnet=DOTNET,host_dll=DLL,stage=stage)
    def test_no_delete_and_no_driveway_rotation(self):
        env=self.make()
        try:
            env.reset(seed=42);enter_executor(env)
            mask=env.action_masks()
            self.assertEqual(set(np.flatnonzero(mask)),{WAIT,DRAW,HANDOFF})
            for action in (ERASE,REMOVE):
                with self.assertRaises(ValueError):env.step(action)
            home=next(b for b in env.raw['buildings'] if b['isHouse'])
            h=(home['cell']['x'],home['cell']['y']);direction=home['drivewayDirection']
            env.step(DRAW);env.step(h[1]*50+h[0])
            self.assertEqual(set(np.flatnonzero(env.action_masks())),{direction,CANCEL})
        finally:env.close()
    def test_random_drawing_preserves_every_initial_edge(self):
        env=self.make();rng=np.random.default_rng(71)
        try:
            for seed in (42,43,44,45):
                env.reset(seed=seed);initial=np.array(env.raw['connections'])
                for _ in range(250):
                    mask=env.action_masks();action=int(rng.choice(np.flatnonzero(mask)))
                    env.step(action)
                    current=np.array(env.raw['connections'])
                    np.testing.assert_array_equal(current&initial,initial)
                    if env.done:break
        finally:env.close()
    def test_completion_reward_and_stage_replay(self):
        env=self.make()
        try:
            recorder=PracticeRecorder(env,seed=42);a,b=gap(env)
            for action in [0,NONE,DRAW,a[1]*50+a[0],DIRS.index((b[0]-a[0],b[1]-a[1]))]:
                self.assertEqual(recorder.step(action)[1],0)
            reward=0
            while not env.done:
                action=NONE if env.role=='secondary' else 0
                reward+=recorder.step(action)[1]
            self.assertGreaterEqual(reward,3);self.assertEqual(reward,env.raw['tripsCompleted'])
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'trace.json';recorder.save(path)
                self.assertEqual(verify(path,DOTNET,DLL)['result'],'PASS')
        finally:env.close()
    def test_original_one_gap_retains_deletion(self):
        env=self.make('one-gap')
        try:
            env.reset(seed=42);enter_executor(env);mask=env.action_masks()
            self.assertTrue(mask[ERASE]);self.assertTrue(mask[REMOVE])
        finally:env.close()

if __name__=='__main__':unittest.main(verbosity=2)

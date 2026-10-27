"""Workflow validation only: scripted games and test doubles, no learner updates."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from environment import TrafficEnv, ROOT, CELLS
from progress import BudgetCallback

DOTNET='dotnet'


class WorkflowChecks(unittest.TestCase):
    def test_seed_blocks_and_explicit_eval(self):
        env=TrafficEnv(dotnet=DOTNET,seeds=[1000,1001],episodes_per_seed=2)
        try:
            seeds=[];attempts=[];cycles=[]
            for i in range(6):
                _,info=env.reset(seed=42 if i==0 else None)
                seeds.append(info['scenario_seed']);attempts.append(info['seed_attempt']);cycles.append(info['seed_cycle'])
            self.assertEqual(seeds,[1000,1000,1001,1001,1000,1000])
            self.assertEqual(attempts,[1,2,1,2,1,2]);self.assertEqual(cycles,[1,1,1,1,2,2])
            counter=env.episodes_started
            _,info=env.reset(options={'scenario_seed':2000})
            self.assertEqual(info['scenario_seed'],2000)
            self.assertEqual(env.episodes_started,counter)
            env.reset(seed=42)
            self.assertEqual(env.scenario_seed,1000)
        finally:env.close()

    def test_recording_cross_runtime_and_tamper_detection(self):
        env=TrafficEnv(dotnet=DOTNET,record_replays=True,seconds=3)
        try:
            env.reset(options={'scenario_seed':1000})
            env.step(CELLS+2)
            env.step(int(np.flatnonzero(env.action_masks())[0]))
            env.step(-1)
            _,_,_,done,info=env.step(CELLS)
            self.assertTrue(done)
            recording=info['episode_replay']
            self.assertEqual(len(recording['actions']),3)
            self.assertEqual(recording['actions'][0]['command'],'build')
            self.assertTrue(recording['truncated'])
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
                path=Path(directory)/'replay.json'
                path.write_text(json.dumps(recording))
                args=[DOTNET,str(ROOT/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'),'--verify-replay',str(path)]
                result=subprocess.run(args,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout)['commands'],3)
                recording['actions'][0]['afterTrips']+=1
                path.write_text(json.dumps(recording))
                result=subprocess.run(args,capture_output=True,text=True,timeout=30)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('diverged',result.stderr)
        finally:env.close()

    def test_progress_and_best_files_without_training(self):
        class FakeModel:
            num_timesteps=0
            def get_env(self):return None
            def save(self,path):Path(str(path)+'.zip').write_text('UNIT TEST DOUBLE - NOT A MODEL')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory, redirect_stdout(io.StringIO()) as printed:
            output=Path(directory)
            callback=BudgetCallback(output,1,100,2,0.000001,{'schema':'test'})
            model=FakeModel();callback.init_callback(model);callback.on_training_start({}, {})
            for i,(seed,score) in enumerate([(1000,2),(1000,1),(1001,0)],1):
                info=dict(trips=score,seconds=3,rejected_actions=0,commands=3,scenario_seed=seed,
                          seed_attempt=2 if i==2 else 1,seed_cycle=1,mean_car_wait=.5,max_car_wait=2,
                          action_counts={'wait':3},command_completed=True,
                          episode_replay={'seed':seed,'score':score,'duration':3,'actions':[]})
                model.num_timesteps=i
                callback.update_locals({'infos':[info],'dones':[True]})
                self.assertTrue(callback.on_step())
            callback.on_training_end()
            self.assertEqual(json.loads((output/'best-game.json').read_text())['score'],2)
            self.assertEqual(json.loads((output/'seeds/seed-1001/best-game.json').read_text())['score'],0)
            status=json.loads((output/'status.json').read_text())
            self.assertEqual(status['episodes'],3);self.assertTrue(status['finished'])
            self.assertEqual(json.loads((output/'seed-summary.json').read_text())['1000']['mean_score'],1.5)
            text=printed.getvalue()
            for expected in ['SEED 1000','SEED 1001','NEW BEST','ETA','car wait mean/max','recent20']:
                self.assertIn(expected,text)

    def test_stop_saves_partial_game_without_a_finished_episode(self):
        env=TrafficEnv(dotnet=DOTNET,record_replays=True,seconds=10)
        try:
            env.reset(options={'scenario_seed':1000})
            *_,info=env.step(CELLS)
            class FakeModel:
                num_timesteps=1
                def get_env(self):return SimpleNamespace(envs=[SimpleNamespace(unwrapped=env)])
                def save(self,path):Path(str(path)+'.zip').write_text('UNIT TEST DOUBLE - NOT A MODEL')
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory,redirect_stdout(io.StringIO()):
                callback=BudgetCallback(Path(directory),1,100)
                callback.init_callback(FakeModel());callback.on_training_start({}, {})
                callback.update_locals({'infos':[info],'dones':[False]})
                callback.on_step();callback.on_training_end()
                recording=json.loads((Path(directory)/'best-game.json').read_text())
                self.assertTrue(recording['partial'])
                self.assertEqual(recording['duration'],1)
                self.assertEqual(recording['episode'],1)
                self.assertEqual(json.loads((Path(directory)/'seed-summary.json').read_text()),{})
        finally:env.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dotnet',default='dotnet')
    args,rest=parser.parse_known_args();DOTNET=args.dotnet
    unittest.main(argv=[sys.argv[0]]+rest)

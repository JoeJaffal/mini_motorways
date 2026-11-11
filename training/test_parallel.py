"""Parallel integration checks without optimizer updates."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from environment import ROOT,CELLS
from parallel import make_vector
from progress import BudgetCallback

DOTNET='dotnet'


class ParallelChecks(unittest.TestCase):
    def test_four_shaped_workers_autoreset_and_legacy_checkpoint_inputs(self):
        torch.set_num_threads(2)
        env=make_vector(4,dotnet=DOTNET,seeds=[1000],seconds=1,reward_mode='connectivity')
        try:
            model=MaskablePPO.load(ROOT/'output/training/seed-1000-parallel-02/final.zip',env=env,
                                   device='cpu',n_steps=64)
            obs=env.reset();masks=np.asarray(env.env_method('action_masks'))
            actions,_=model.predict(obs,action_masks=masks)
            self.assertTrue(all(masks[i,a] for i,a in enumerate(actions)))
            self.assertEqual(len({e.unwrapped.host.process.pid for e in env.envs}),4)
            _,rewards,dones,infos=env.step(np.full(4,CELLS))
            self.assertTrue(dones.all())
            self.assertTrue((rewards==0).all())
            for i,info in enumerate(infos):
                self.assertEqual(info['reward_mode'],'connectivity')
                self.assertEqual(info['connected_houses'],0)
                self.assertTrue(info['TimeLimit.truncated'])
                self.assertEqual(env.envs[i].unwrapped.training_reward_total,0)
        finally:env.close()

    def test_independent_hosts_masks_and_terminal_replays(self):
        env=make_vector(2,dotnet=DOTNET,seeds=[1000],seconds=2,record_replays=True)
        try:
            env.seed(42);obs=env.reset()
            self.assertEqual(obs['grid'].shape,(2,50,30,50))
            self.assertNotEqual(env.envs[0].unwrapped.host.process.pid,env.envs[1].unwrapped.host.process.pid)
            masks=env.env_method('action_masks')
            self.assertEqual(np.asarray(masks).shape,(2,1513))
            _,_,done,info=env.step(np.array([CELLS,CELLS+2]))
            self.assertFalse(done.any())
            self.assertEqual(info[0]['seconds'],1)
            self.assertEqual(info[1]['seconds'],0)
            self.assertEqual(info[1]['worker'],1)
            obs,_,done,info=env.step(np.array([CELLS,CELLS]))
            self.assertTrue(done[0]);self.assertFalse(done[1])
            self.assertTrue(info[0]['TimeLimit.truncated'])
            self.assertIn('terminal_observation',info[0])
            self.assertEqual(len(info[0]['episode_replay']['actions']),2)
            self.assertEqual(env.envs[0].unwrapped.commands,0)
            self.assertEqual(env.envs[1].unwrapped.commands,1)
        finally:env.close()

    def test_existing_checkpoint_batched_prediction_and_new_rollout_shape(self):
        torch.set_num_threads(2)
        env=make_vector(2,dotnet=DOTNET,seeds=[1000])
        try:
            model=MaskablePPO.load(ROOT/'output/training/first-full-tools/final.zip',env=env,
                                   device='cpu',n_steps=128)
            self.assertEqual(model.n_envs,2)
            self.assertEqual(model.rollout_buffer.buffer_size,128)
            obs=env.reset()
            masks=np.asarray(env.env_method('action_masks'))
            actions,_=model.predict(obs,action_masks=masks)
            self.assertEqual(actions.shape,(2,))
            self.assertTrue(all(masks[i,a] for i,a in enumerate(actions)))
            env.step_async(actions);env.wait_pending()
        finally:env.close()

    def test_callback_keeps_worker_identity_and_best_replay(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory,redirect_stdout(io.StringIO()):
            env=make_vector(2,dotnet=DOTNET,seeds=[1000],seconds=1,record_replays=True)
            class FakeModel:
                num_timesteps=2
                def get_env(self):return env
                def save(self,path):Path(str(path)+'.zip').write_text('UNIT TEST DOUBLE')
            try:
                env.reset()
                _,_,dones,infos=env.step(np.array([CELLS,CELLS]))
                cb=BudgetCallback(Path(directory),1,100)
                cb.init_callback(FakeModel());cb.on_training_start({}, {})
                cb.update_locals({'infos':infos,'dones':dones});cb.on_step();cb.on_training_end()
                self.assertEqual(cb.episodes,2)
                self.assertEqual([r['worker'] for r in cb.episode_results],[0,1])
                status=json.loads((Path(directory)/'status.json').read_text())
                self.assertEqual(len(status['workers']),2)
                replay=json.loads((Path(directory)/'best-game.json').read_text())
                self.assertEqual(replay['score'],0)
                self.assertIn(replay['worker'],[0,1])
            finally:env.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dotnet',default='dotnet')
    args,rest=parser.parse_known_args();DOTNET=args.dotnet
    unittest.main(argv=[sys.argv[0]]+rest)

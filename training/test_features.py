"""Connectivity inputs and explicit checkpoint adaptation, without learning."""
import argparse
import sys
import unittest
import json
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from environment import TrafficEnv,ROOT,CELLS
from parallel import make_vector
from migration import warm_start

DOTNET='dotnet'


class FeatureChecks(unittest.TestCase):
    def test_spatial_residual_preserves_policy_then_trains_and_reloads(self):
        import tempfile
        from pathlib import Path
        torch.set_num_threads(2)
        env=make_vector(1,dotnet=DOTNET,observation_mode='connectivity',reward_mode='connectivity',seconds=3)
        legacy=TrafficEnv(dotnet=DOTNET)
        try:
            path=ROOT/'output/training/multi-seed-shaped-01/final.zip'
            source=MaskablePPO.load(path,device='cpu')
            model=warm_start(path,env,dict(n_steps=16,batch_size=8,n_epochs=1,gamma=.999,learning_rate=.0003,ent_coef=.01),42,True,'spatial-residual')
            a,_=legacy.reset(seed=42,options={'scenario_seed':1000})
            b,_=env.envs[0].unwrapped.reset(seed=42,options={'scenario_seed':1000})
            with torch.no_grad():
                pa=source.policy.get_distribution(source.policy.obs_to_tensor(a)[0],action_masks=legacy.action_masks()).distribution.probs
                pb=model.policy.get_distribution(model.policy.obs_to_tensor(b)[0],action_masks=env.envs[0].unwrapped.action_masks()).distribution.probs
            np.testing.assert_allclose(pa.numpy(),pb.numpy(),atol=1e-7,rtol=1e-6)
            head=model.policy.features_extractor.spatial_head[-1]
            before=head.weight.detach().clone()
            model.learn(total_timesteps=32)
            self.assertFalse(torch.equal(before,head.weight))
            obs=env.reset();mask=env.env_method('action_masks')[0]
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
                model.save(Path(directory)/'spatial')
                restored=MaskablePPO.load(Path(directory)/'spatial',device='cpu')
                x,_=model.predict(obs,deterministic=True,action_masks=mask)
                y,_=restored.predict(obs,deterministic=True,action_masks=mask)
                np.testing.assert_array_equal(x,y)
        finally:legacy.close();env.close()

    def test_inputs_match_current_connectivity_and_hide_future(self):
        env=TrafficEnv(dotnet=DOTNET,observation_mode='connectivity',reward_mode='connectivity')
        try:
            obs,_=env.reset(seed=42,options={'scenario_seed':1000})
            self.assertEqual(obs['grid'].shape,(52,30,50))
            self.assertTrue(env.observation_space.contains(obs))
            self.assertGreater(obs['grid'][50].sum(),0);self.assertGreater(obs['grid'][51].sum(),0)
            path=ROOT/'docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/best-game.json'
            for event in json.loads(path.read_text())['actions']:
                req={k:v for k,v in event.items() if k in ['command','tool','x','y','toX','toY','id','choice']}
                obs,_,_,_,_=env._advance(None if req['command']=='wait' else req)
                if env.connected_houses:break
            self.assertGreater(env.connected_houses,0)
            for p,b in env.parcels.items():
                if not env.is_visible(p):continue
                expected=b['id'] not in env.connectivity['connectedHouseIds' if b['isHouse'] else 'suppliedDestinationIds']
                self.assertEqual(obs['grid'][50 if b['isHouse'] else 51,p[1],p[0]],expected)
            env.raw['scheduledSpawns']=[{'time':0,'color':7}];env.raw['randomDraws']=999999
            for key in obs:np.testing.assert_array_equal(obs[key],env.encode()[key])
            self.assertEqual(obs['grid'][:,~env.visible.reshape(30,50)].sum(),0)
        finally:env.close()

    def test_zero_channel_migration_preserves_action_probabilities(self):
        torch.set_num_threads(2)
        oldenv=TrafficEnv(dotnet=DOTNET);newenv=make_vector(1,dotnet=DOTNET,observation_mode='connectivity')
        try:
            a,_=oldenv.reset(seed=42,options={'scenario_seed':1000});b=newenv.reset()
            # Match the new vector's default seed explicitly.
            b0,_=newenv.envs[0].unwrapped.reset(seed=42,options={'scenario_seed':1000})
            path=ROOT/'output/training/multi-seed-shaped-01/final.zip'
            source=MaskablePPO.load(path,device='cpu')
            target=warm_start(path,newenv,dict(n_steps=256,batch_size=64,n_epochs=4,gamma=.999,learning_rate=.0003,ent_coef=.01),42,True)
            with torch.no_grad():
                pa=source.policy.get_distribution(source.policy.obs_to_tensor(a)[0],action_masks=oldenv.action_masks()).distribution.probs
                pb=target.policy.get_distribution(target.policy.obs_to_tensor(b0)[0],action_masks=newenv.envs[0].unwrapped.action_masks()).distribution.probs
            np.testing.assert_allclose(pa.numpy(),pb.numpy(),atol=1e-7,rtol=1e-6)
            self.assertEqual(len(target.policy.optimizer.state),0)
            self.assertEqual(sum(p.numel() for p in target.policy.parameters()),450898)
            self.assertTrue(torch.all(target.policy.features_extractor.grid[0].weight[:,50:]==0))
            with self.assertRaises(ValueError):warm_start(path,newenv,dict(n_steps=256,batch_size=64),42,False)
        finally:oldenv.close();newenv.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dotnet',default='dotnet')
    args,rest=parser.parse_known_args();DOTNET=args.dotnet
    unittest.main(argv=[sys.argv[0]]+rest)

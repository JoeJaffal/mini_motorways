"""Planner-aided adapter checks with ordinary finite-stock gameplay."""
import argparse
from pathlib import Path
import tempfile
import unittest
import sys
import json
import subprocess
import numpy as np
import torch
from gymnasium.utils.env_checker import check_env
from sb3_contrib import MaskablePPO
from goal_agent import GoalEnv,GoalPolicy,vector
from environment import ROOT

DOTNET='dotnet';DLL=None


class GoalChecks(unittest.TestCase):
    def test_contract_and_actual_finite_connection_replay(self):
        env=GoalEnv(dotnet=DOTNET,host_dll=DLL,seconds=200)
        try:
            check_env(env,skip_render_check=True)
            obs,_=env.reset(seed=42,options={'scenario_seed':2000})
            self.assertTrue(env.observation_space.contains(obs))
            self.assertTrue(env.action_masks()[3:].any())
            initial=env.base.raw['inventory'][0]
            env.step(int(np.flatnonzero(env.action_masks()[3:])[0])+3)
            self.assertGreater(env.base.connected_houses,0)
            self.assertLess(env.base.raw['inventory'][0],initial)
            for _ in range(20):
                _,_,term,trunc,info=env.step(0)
                if info['trips']>0 or term or trunc:break
            self.assertGreater(info['trips'],0)
            self.assertFalse(env.base.raw['unlimitedConstruction'])
            replay=env.export_replay()
            self.assertTrue(all(e['command'] in ['draw','upgrade','wait'] for e in replay['actions']))
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
                path=Path(directory)/'goal.json';path.write_text(json.dumps(replay))
                dll=DLL or ROOT/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'
                result=subprocess.run([DOTNET,str(dll),'--verify-replay',str(path)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
        finally:env.close()

    def test_goal_policy_updates_and_reload(self):
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            env=vector(1,directory,dotnet=DOTNET,host_dll=DLL,seconds=30,seeds=[1000])
            try:
                model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=8,batch_size=8,n_epochs=1,gamma=.99,gae_lambda=.99)
                before=torch.cat([x.detach().flatten() for x in model.policy.parameters()]).clone()
                model.learn(total_timesteps=16)
                after=torch.cat([x.detach().flatten() for x in model.policy.parameters()])
                self.assertFalse(torch.equal(before,after))
                model.save(Path(directory)/'model')
                restored=MaskablePPO.load(Path(directory)/'model',device='cpu')
                obs=env.reset();mask=np.asarray(env.env_method('action_masks'))
                a,_=model.predict(obs,deterministic=True,action_masks=mask)
                b,_=restored.predict(obs,deterministic=True,action_masks=mask)
                np.testing.assert_array_equal(a,b)
            finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dotnet',default='dotnet');p.add_argument('--host-dll')
    a,rest=p.parse_known_args();DOTNET=a.dotnet;DLL=a.host_dll
    unittest.main(argv=[sys.argv[0]]+rest)

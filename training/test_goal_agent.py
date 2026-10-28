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
    def test_congestion_grid_contract_and_live_values(self):
        env=GoalEnv(dotnet=DOTNET,host_dll=DLL,seconds=100,congestion_aware=True)
        try:
            obs,_=env.reset(seed=42,options={'scenario_seed':2000})
            self.assertTrue(env.observation_space.contains(obs))
            self.assertEqual(obs['candidates'].shape,(512,32))
            p=env.plans[0][0];k=env.base.index(p)
            env.base.raw['vehicles']=[{'x':p[0],'y':p[1],'waiting':30.,'stage':'Driving','speed':0.}]*2
            env._refresh();obs=env.encode()
            self.assertAlmostEqual(float(obs['traffic'].reshape(4,1500)[0,k]),.2,places=7)
            self.assertEqual(float(obs['traffic'].reshape(4,1500)[1,k]),.5)
            self.assertTrue(env.observation_space.contains(obs))
            env.base.raw['vehicles']=[];env._refresh()
            self.assertEqual(float(env.encode()['traffic'][:2].sum()),0.)
        finally:env.close()

    def test_congestion_policy_save_reload(self):
        torch.set_num_threads(2)
        env=GoalEnv(dotnet=DOTNET,host_dll=DLL,seconds=30,congestion_aware=True)
        try:
            model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=8,batch_size=8,n_epochs=1)
            before=model.policy.features_extractor.prior.weight.detach().clone()
            traffic_before=model.policy.features_extractor.traffic_encoder[0].weight.detach().clone()
            model.learn(total_timesteps=16)
            self.assertFalse(torch.equal(before,model.policy.features_extractor.prior.weight))
            self.assertFalse(torch.equal(traffic_before,model.policy.features_extractor.traffic_encoder[0].weight))
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
                model.save(Path(directory)/'model')
                restored=MaskablePPO.load(Path(directory)/'model',device='cpu')
                obs,_=env.reset(seed=42,options={'scenario_seed':2000})
                a,_=model.predict(obs,deterministic=True,action_masks=env.action_masks())
                b,_=restored.predict(obs,deterministic=True,action_masks=env.action_masks())
                np.testing.assert_array_equal(a,b)
        finally:env.close()

    def test_existing_connection_can_offer_physical_bypass(self):
        from environment import DIRS,cell
        from planner_diagnostic import path_to
        env=GoalEnv(dotnet=DOTNET,host_dll=DLL,seconds=200,congestion_aware=True)
        try:
            env.reset(seed=42,options={'scenario_seed':2000})
            env.step(3)
            e=env.base;found=False
            for h,home in e.houses.items():
                for shop in e.buildings:
                    if shop['isHouse'] or shop['color']!=home['color']:continue
                    d=DIRS[home['drivewayDirection']];start=h[0]+d[0],h[1]+d[1]
                    for entry,direction in zip(shop['entrances'],shop['entranceDirections']):
                        p=cell(entry);d=DIRS[direction];goal=p[0]+d[0],p[1]+d[1]
                        route=path_to(e,start,goal,np.where(np.asarray(e.arrays['infrastructure'])==0,1e6,0.))
                        if route and len(route)>4 and all(e.arrays['infrastructure'][e.index(p)]!=0 for p in route):
                            p=route[len(route)//2]
                            e.raw['vehicles']=[{'x':p[0],'y':p[1],'waiting':60.,'stage':'Driving'}]*5
                            env.cache_key=None;env._refresh()
                            if env.bypass_baselines:found=True;break
                    if found:break
                if found:break
            self.assertTrue(found,'Congested connected pair should permit a finite physical bypass')
            index=next(iter(env.bypass_baselines));route=env.plans[index]
            self.assertEqual(float(env.features[index,25]),1.)
            self.assertGreater(sum(e.arrays['infrastructure'][e.index(p)]==0 for p in route),0)
            # Restore simulator vehicles before executing: synthetic data tests
            # only observation/proposal logic, never simulator performance.
            e.raw['vehicles']=[]
            env.step(index+3)
            replay=env.export_replay()
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
                path=Path(directory)/'bypass.json';path.write_text(json.dumps(replay))
                dll=DLL or ROOT/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'
                result=subprocess.run([DOTNET,str(dll),'--verify-replay',str(path)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
        finally:env.close()

    def test_cached_routes_refresh_live_traffic_without_topology_change(self):
        env=GoalEnv(dotnet=DOTNET,host_dll=DLL,seconds=100)
        try:
            env.reset(seed=42,options={'scenario_seed':2000})
            self.assertTrue(env.plans)
            routes=[list(route) for route in env.plans];key=env.cache_key
            p=routes[0][0]
            env.base.raw['vehicles']=[{'x':p[0],'y':p[1],'waiting':30.}]*2
            shop=next(b for b in env.base.buildings if b['id']==env.plan_shops[0])
            shop['demand']=7;shop['overcrowdedFor']=10
            env._refresh()
            self.assertEqual(env.cache_key,key)
            self.assertEqual(env.plans,routes)
            self.assertAlmostEqual(float(env.features[0,20]),.2/len(routes[0]),places=7)
            self.assertAlmostEqual(float(env.features[0,21]),.5)
            self.assertAlmostEqual(float(env.features[0,16]),.35,places=7)
            self.assertAlmostEqual(float(env.features[0,22]),.2,places=7)
            env.base.raw['vehicles']=[]
            env._refresh()
            self.assertEqual(float(env.features[0,20]),0.)
            self.assertEqual(float(env.features[0,21]),0.)
        finally:env.close()

    def test_collapsing_forced_wait_preserves_frozen_ordinary_game(self):
        torch.set_num_threads(2)
        envs=[GoalEnv(dotnet=DOTNET,host_dll=DLL,seconds=180,skip_forced_wait=s) for s in [False,True]]
        try:
            model=MaskablePPO(GoalPolicy,envs[0],device='cpu',seed=42,n_steps=8,batch_size=8)
            for env in envs:
                obs,_=env.reset(seed=42,options={'scenario_seed':2000})
                while True:
                    a,_=model.predict(obs,deterministic=True,action_masks=env.action_masks())
                    obs,_,t,c,_=env.step(a)
                    if t or c:break
            self.assertEqual(envs[0].export_replay()['actions'],envs[1].export_replay()['actions'])
            self.assertEqual(envs[0].base.raw['tripsCompleted'],envs[1].base.raw['tripsCompleted'])
            self.assertGreater(envs[1].forced_wait_commands,0)
            self.assertLess(envs[1].decisions,envs[0].decisions)
        finally:
            for env in envs:env.close()

    def test_reward_scaling_keeps_game_and_score_identical(self):
        envs=[GoalEnv(dotnet=DOTNET,host_dll=DLL,seconds=100,reward_scale=s) for s in [1.,.01]]
        try:
            for e in envs:e.reset(seed=42,options={'scenario_seed':2000})
            action=int(np.flatnonzero(envs[0].action_masks()[3:])[0])+3
            positive=False
            for step in range(20):
                a=action if step==0 else 0
                x,y=[e.step(a) for e in envs]
                self.assertAlmostEqual(x[1]*.01,y[1],places=9)
                self.assertEqual(x[4]['trips'],y[4]['trips'])
                for key in x[0]:np.testing.assert_array_equal(x[0][key],y[0][key])
                positive|=x[4]['trips']>0
                if x[2] or x[3]:break
            self.assertTrue(positive)
        finally:
            for e in envs:e.close()

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
            env=vector(1,directory,dotnet=DOTNET,host_dll=DLL,seconds=30,seeds=[1000],skip_forced_wait=True)
            try:
                model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=8,batch_size=8,n_epochs=1,gamma=.99,gae_lambda=.99)
                model.skip_forced_wait=True
                before=torch.cat([x.detach().flatten() for x in model.policy.parameters()]).clone()
                actor_before=model.policy.features_extractor.prior.weight.detach().clone()
                model.learn(total_timesteps=16)
                after=torch.cat([x.detach().flatten() for x in model.policy.parameters()])
                self.assertFalse(torch.equal(before,after))
                self.assertFalse(torch.equal(actor_before,model.policy.features_extractor.prior.weight))
                model.save(Path(directory)/'model')
                restored=MaskablePPO.load(Path(directory)/'model',device='cpu')
                self.assertTrue(restored.skip_forced_wait)
                obs=env.reset();mask=np.asarray(env.env_method('action_masks'))
                a,_=model.predict(obs,deterministic=True,action_masks=mask)
                b,_=restored.predict(obs,deterministic=True,action_masks=mask)
                np.testing.assert_array_equal(a,b)
            finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dotnet',default='dotnet');p.add_argument('--host-dll')
    a,rest=p.parse_known_args();DOTNET=a.dotnet;DLL=a.host_dll
    unittest.main(argv=[sys.argv[0]]+rest)

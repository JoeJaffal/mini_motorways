"""Normal-stock traffic-light actions, observation contract and PPO updates."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
import torch
from gymnasium.utils.env_checker import check_env
from sb3_contrib import MaskablePPO
from environment import ROOT,DIRS
from goal_agent import GoalPolicy
from signal_agent import SignalEnv,SIGNAL_START

DOTNET=str(ROOT/'tmp/dotnet/dotnet.exe')


class SignalChecks(unittest.TestCase):
    def test_contract_stock_mask_and_global_equivalence(self):
        env=SignalEnv(dotnet=DOTNET,seconds=30)
        try:
            check_env(env,skip_render_check=True)
            obs,_=env.reset(seed=42,options={'scenario_seed':2000})
            self.assertTrue(env.observation_space.contains(obs))
            self.assertEqual(obs['traffic'].shape,(5,30,50))
            self.assertEqual(env.base.raw['inventory'][3],0)
            self.assertFalse(env.action_masks()[SIGNAL_START:].any())
            np.testing.assert_array_equal(np.clip(env.base.encode_global(),0,1),env.base.encode()['global'])
            _,reward,_,_,info=env.step(SIGNAL_START)
            self.assertEqual(info['rejected_actions'],1)
        finally:env.close()

    def test_signal_actor_and_context_update_and_reload(self):
        torch.set_num_threads(2)
        env=SignalEnv(dotnet=DOTNET,seconds=40)
        try:
            model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=8,batch_size=8,n_epochs=2,
                policy_kwargs=dict(features_extractor_kwargs=dict(prior_temperature=2.)))
            before=model.policy.features_extractor.route_context.weight.detach().clone()
            model.learn(total_timesteps=16)
            self.assertFalse(torch.equal(before,model.policy.features_extractor.route_context.weight))
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
                model.save(Path(folder)/'policy')
                restored=MaskablePPO.load(Path(folder)/'policy',device='cpu')
                self.assertEqual(restored.policy.features_extractor.prior_temperature,2.)
                obs,_=env.reset(seed=42,options={'scenario_seed':2000})
                a,_=model.predict(obs,deterministic=True,action_masks=env.action_masks())
                b,_=restored.predict(obs,deterministic=True,action_masks=env.action_masks())
                np.testing.assert_array_equal(a,b)
        finally:env.close()

    def test_normal_upgrade_signal_consumption_and_exact_replay(self):
        torch.set_num_threads(2)
        env=SignalEnv(dotnet=DOTNET,seconds=1000,enable_signals=False)
        try:
            model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=8,batch_size=8)
            acquired=False
            for seed in [2000,2001,2002]:
                obs,_=env.reset(seed=42,options={'scenario_seed':seed})
                while not env.base.done:
                    offers=env.base.raw['upgradeChoices']
                    lights=next((i for i,o in enumerate(offers) if o['type']==3),None)
                    action=1+lights if lights is not None else int(model.predict(obs,deterministic=True,action_masks=env.action_masks())[0])
                    obs,_,_,_,_=env.step(action)
                    if env.base.raw['inventory'][3]>0:acquired=True;break
                if acquired:break
            self.assertTrue(acquired,'Normal weekly offer must supply lights in fixture seeds')
            e=env.base
            # If necessary build a disconnected cross using normal road stock.
            if not any(e._legal[4][k] and int(e.arrays['connections'][k]).bit_count()>=3 for k in range(1500)):
                p=next((x,y) for y in range(1,29) for x in range(1,49)
                    if all(e.is_visible(q) and e.land[e.index(q)] and e.arrays['infrastructure'][e.index(q)]==0
                           for q in [(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)]))
                e._advance(dict(command='draw',x=p[0]-1,y=p[1],toX=p[0]+1,toY=p[1]))
                e._advance(dict(command='draw',x=p[0],y=p[1]-1,toX=p[0],toY=p[1]+1))
            env.enable_signals=True;env._refresh()
            self.assertTrue(env.signal_cells)
            # Verify the light head can learn when a real legal action is present.
            tensor=model.policy.obs_to_tensor(env.encode())[0]
            before=model.policy.features_extractor.signal_row[-1].weight.detach().clone()
            _,logp,_=model.policy.evaluate_actions(tensor,torch.tensor([SIGNAL_START]),action_masks=env.action_masks()[None,:])
            model.policy.optimizer.zero_grad();(-logp.mean()).backward();model.policy.optimizer.step()
            self.assertFalse(torch.equal(before,model.policy.features_extractor.signal_row[-1].weight))
            p=env.signal_cells[0];old=e.raw['inventory'][3];roads=e.raw['inventory'][0];rejects=e.rejected
            _,reward,_,_,info=env.step(SIGNAL_START)
            self.assertEqual(e.raw['inventory'][3],old-1)
            self.assertEqual(e.raw['inventory'][0],roads)
            self.assertEqual(e.arrays['infrastructure'][e.index(p)],4)
            self.assertNotIn(p,env.signal_cells)
            self.assertEqual(e.rejected,rejects)
            self.assertEqual(info['signals_placed'],1)
            self.assertAlmostEqual(reward,env.reward_scale*(info['trip_reward']+info['shaping_reward']))
            self.assertEqual(float(env.encode()['traffic'][4,p[1],p[0]]),1.)
            replay=env.export_replay()
            self.assertFalse(e.raw['unlimitedConstruction'])
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
                path=Path(folder)/'signal.json';path.write_text(json.dumps(replay))
                result=subprocess.run([DOTNET,str(ROOT/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'),
                    '--verify-replay',str(path)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
        finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dotnet',default=DOTNET)
    a,rest=p.parse_known_args();DOTNET=a.dotnet
    unittest.main(argv=[__file__]+rest)

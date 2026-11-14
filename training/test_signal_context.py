"""Cheap v4 observation/transfer checks; no training run or full-game evaluation."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from environment import ROOT
from goal_agent import GoalPolicy
from signal_agent import SignalEnv,SIGNAL_START,transfer_signal_context
from train_goal import model_environment


class ContextChecks(unittest.TestCase):
    def test_features_preserving_transfer_gradients_and_reload(self):
        torch.set_num_threads(2)
        env=SignalEnv(signal_context=True,dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'))
        try:
            env.reset(seed=42,options={'scenario_seed':2000});e=env.base
            p=next((x,y) for y in range(1,29) for x in range(1,49) if all(e.is_visible(q) and e.land[e.index(q)]
                and e.arrays['infrastructure'][e.index(q)]==0 for q in [(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)]))
            e._advance(dict(command='draw',x=p[0]-1,y=p[1],toX=p[0]+1,toY=p[1]))
            e._advance(dict(command='draw',x=p[0],y=p[1]-1,toX=p[0],toY=p[1]+1))
            # Synthetic observation fixture only: no simulator command follows
            # this stock/queue injection and no gameplay score is measured.
            e.raw['inventory'][3]=1
            shop=next(b for b in e.buildings if not b['isHouse'])
            shop.update(demand=9,reserved=3,demandCapacity=6,overcrowdedFor=25)
            e.raw['vehicles']=[dict(x=p[0],y=p[1],speed=0.,waiting=12.,obstacle='Carpark access occupied',stage='Outbound',shopId=shop['id'])]
            e._refresh();env._refresh();obs=env.encode()
            self.assertTrue(env.observation_space.contains(obs))
            i=env.signal_cells.index(p);row=obs['signals'][i]
            self.assertEqual(row[12],1.);self.assertEqual(row[13],0.)
            self.assertAlmostEqual(float(row[16]),.2,places=7)
            self.assertEqual(row[18],.5);self.assertEqual(row[19],1.);self.assertEqual(row[20],.5)
            e.raw['vehicles'][0]['obstacle']='Crossing vehicle';env._refresh();cross=env.encode()['signals'][i]
            self.assertEqual(cross[12],0.);self.assertEqual(cross[13],1.)
            for k in range(12):self.assertEqual(row[k],cross[k])
            source=MaskablePPO.load(ROOT/'output/training/signals-night-01/validation-best.zip',device='cpu')
            target=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=8,batch_size=8,
                policy_kwargs=dict(features_extractor_kwargs=dict(prior_temperature=source.policy.features_extractor.prior_temperature)))
            transfer_signal_context(target,source)
            old_obs=dict(obs,signals=obs['signals'][:,:12].copy());mask=env.action_masks()
            with torch.no_grad():
                a=source.policy.get_distribution(source.policy.obs_to_tensor(old_obs)[0],action_masks=mask).distribution.probs
                b=target.policy.get_distribution(target.policy.obs_to_tensor(obs)[0],action_masks=mask).distribution.probs
            torch.testing.assert_close(a,b,atol=1e-6,rtol=1e-6)
            self.assertFalse(target.policy.optimizer.state)
            self.assertTrue(torch.all(target.policy.features_extractor.signal_row[0].weight[:,12:]==0))
            _,logp,_=target.policy.evaluate_actions(target.policy.obs_to_tensor(obs)[0],torch.tensor([SIGNAL_START+i]),action_masks=mask[None,:])
            target.policy.optimizer.zero_grad();(-logp.mean()).backward()
            self.assertGreater(float(target.policy.features_extractor.signal_row[0].weight.grad[:,12:].abs().sum()),0)
            with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
                path=Path(folder)/'model';target.save(path)
                restored=MaskablePPO.load(path,device='cpu')
                check=model_environment(restored,dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'))
                try:self.assertTrue(check.signal_context)
                finally:check.close()
        finally:env.close()


if __name__=='__main__':unittest.main()

from pathlib import Path
import json,numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,RESERVE
from prepare_city_policy import masked_probs
root=Path.cwd();torch.set_num_threads(1)
m=MaskablePPO.load('output/training/city-strategy-balanced-extension-01/segment-001/midpoint.zip',device='cpu')
e=CityCurriculumEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',collapse_forced_wait=True,reserve_warmup_seconds=6)
samples=[]
try:
 for index in range(16):
  obs,_=e.reset(options=dict(scenario_seed=157100000+index,exercise=RESERVE));rng=np.random.default_rng(18411+index);episode=[]
  while not e.done:
   mask=e.action_masks();p=masked_probs(m,obs,mask).astype(float);p/=p.sum();a=int(rng.choice(len(p),p=p))
   next_obs,r,_,_,info=e.step(a);episode.append(dict(obs=obs,mask=mask,action=a,reward=r));obs=next_obs
  total=0
  for row in reversed(episode):total+=row['reward'];row['return']=total
  samples.extend(episode)
finally:e.close()
selected=np.random.default_rng(42517).choice(len(samples),32,replace=False);batch=[samples[i] for i in selected]
obs={key:torch.as_tensor(np.stack([r['obs'][key] for r in batch])) for key in batch[0]['obs']}
actions=torch.tensor([r['action'] for r in batch]);masks=np.stack([r['mask'] for r in batch]);returns=torch.tensor([r['return'] for r in batch],dtype=torch.float32)
values,logp,entropy=m.policy.evaluate_actions(obs,actions,action_masks=masks);values=values.flatten()
params=[p for p in m.policy.parameters() if p.requires_grad]
def norm(gs):return float(torch.sqrt(sum((g.detach()**2).sum() for g in gs if g is not None)))
result=[]
for use_returns in (False,True):
 advantages=(returns if use_returns else returns-values.detach());advantages=(advantages-advantages.mean())/(advantages.std()+1e-8)
 actor_loss=-(advantages*logp).mean()-m.ent_coef*entropy.mean();critic_loss=((returns-values)**2).mean()
 ag=torch.autograd.grad(actor_loss,params,retain_graph=True,allow_unused=True)
 cg=torch.autograd.grad(critic_loss,params,retain_graph=True,allow_unused=True)
 for vf in (m.vf_coef,.001):
  combined=[(torch.zeros_like(p) if a is None else a)+(torch.zeros_like(p) if c is None else vf*c) for p,a,c in zip(params,ag,cg)]
  gn=norm(combined);result.append(dict(return_advantages=use_returns,vf_coef=vf,actor_gradient_norm=norm(ag),weighted_critic_gradient_norm=vf*norm(cg),combined_gradient_norm=gn,global_clip_scale=min(1,m.max_grad_norm/(gn+1e-6))))
p=root/'docs/training/city-strategy-launch-2026-11-24/gradient-balance-diagnostic.json';p.write_text(json.dumps(dict(note='Frozen on-policy reserve trajectories;32 sampled transitions, finite-window Monte Carlo returns. Actor score-function gradient equals first PPO update at ratio1. This diagnoses gradient scaling, not a measured benefit from changing vf_coef. No updates applied.',samples=len(samples),batch_size=len(batch),mean_return=float(returns.mean()),mean_value=float(values.detach().mean()),rows=result),indent=2)+'\n');print(result)

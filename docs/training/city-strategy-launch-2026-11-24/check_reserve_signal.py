from pathlib import Path
import json,numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,RESERVE
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();torch.set_num_threads(1)
path=root/'output/training/city-strategy-balanced-extension-01/segment-001/midpoint.zip'
m=MaskablePPO.load(path,device='cpu');rows=[]
for name,options in [('original',{}),('warmup6',dict(reserve_warmup_seconds=6)),('delay2',dict(reserve_delay_seconds=2))]:
 e=CityCurriculumEnv('output/city-strategy-short-delay-build-01/bin/TrafficHost/release/TrafficHost.dll',collapse_forced_wait=True,**options)
 try:
  for index in range(16):
   obs,_=e.reset(options=dict(scenario_seed=157100000+index,exercise=RESERVE));rng=np.random.default_rng(18411+index);steps=[]
   while not e.done:
    mask=e.action_masks();p=masked_probs(m,obs,mask).astype(float);p/=p.sum()
    with torch.no_grad():
     tensor,_=m.policy.obs_to_tensor(obs);_,gate=m.policy.features_extractor.strategy_context(tensor)
    a=int(rng.choice(len(p),p=p));obs,r,_,_,info=e.step(a)
    steps.append(dict(action=a,pwait=float(p[0]),reward=r,gate=float(gate.item())))
   total=0
   for step in reversed(steps):total+=step['reward'];step['return_to_go']=total
   rows.append(dict(case=name,seed=157100000+index,action_seed=18411+index,score=total,new_deliveries=info['new_deliveries'],stock_at_arrival=info['future_stock'],steps=steps))
   print(name,index,total,info['new_deliveries'],flush=True)
 finally:e.close()
summary={}
for name in ('original','warmup6','delay2'):
 games=[r for r in rows if r['case']==name];steps=[s for r in games for s in r['steps']]
 returns=np.array([s['return_to_go'] for s in steps]);scores=np.array([s['gate']*((s['action']==0)-s['pwait']) for s in steps])
 summary[name]=dict(games=len(games),successes=sum(r['new_deliveries']>0 for r in games),decisions=len(steps),return_mean=float(returns.mean()),return_std=float(returns.std()),mean_initial_wait=float(np.mean([r['steps'][0]['pwait'] for r in games])),zero_baseline_wait_score_gradient=float(np.mean(returns*scores)),centered_scaled_wait_score_gradient=float(np.mean((returns-returns.mean())/max(returns.std(),1e-8)*scores)))
result=dict(checkpoint=str(path),sha256=sha256(path),note='Frozen Monte Carlo diagnostic; positive score-function gradient favors increasing additive Wait bias. Full-cohort centered estimate approximates, but is not identical to, task minibatch PPO updates. No gradient applied, no teacher actions, no fresh-city readiness evidence.',summary=summary,rows=rows)
p=root/'docs/training/city-strategy-launch-2026-11-24/reserve-signal-diagnostic.json';p.write_text(json.dumps(result,indent=2)+'\n');print(summary)

from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs
r=Path('docs/training/city-whole-policy-2026-11-24');a=json.loads((r/'watched-reference/trace.json').read_text())['actions'];b=json.loads((r/'watched-whole/trace.json').read_text())['actions'];i=next(i for i,(x,y) in enumerate(zip(a,b)) if x['action']!=y['action'])
torch.set_num_threads(1);parent=MaskablePPO.load('output/training/city-strategy-wide-initial-01/start.zip',device='cpu');candidate=MaskablePPO.load('output/training/city-whole-fit-01/whole/final.zip',device='cpu');env=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=600,allow_bridges=True)
try:
 obs,_=env.reset(options=dict(scenario_seed=184000000));rng=np.random.default_rng(193251)
 for x in a[:i]:
  p=masked_probs(parent,obs,env.action_masks()).astype(float);assert int(rng.choice(len(p),p=p/p.sum()))==x['action'];obs,*_=env.step(x['action'])
 mask=env.action_masks();p=masked_probs(parent,obs,mask).astype(float);q=masked_probs(candidate,obs,mask).astype(float);p/=p.sum();q/=q.sum();u=rng.random()
 choose=lambda probs:int(np.searchsorted(np.cumsum(probs),u,side='right'))
 assert choose(p)==a[i]['action'] and choose(q)==b[i]['action']
 only_wait=np.r_[q[0],p[1:]/p[1:].sum()*(1-q[0])];only_roads=np.r_[p[0],q[1:]/q[1:].sum()*(1-p[0])]
 report=dict(decision=i+1,native_seconds=env.raw['time'],reference_action=choose(p),candidate_action=choose(q),reference_wait=float(p[0]),candidate_wait=float(q[0]),conditional_road_tv=float(np.abs(p[1:]/p[1:].sum()-q[1:]/q[1:].sum()).sum()/2),same_random_uniform=float(u),action_with_only_wait_changed=choose(only_wait),action_with_only_road_preferences_changed=choose(only_roads),limit='One shared pre-divergence state. Joint categorical sampling can change which road is sampled when Wait mass changes. This does not estimate population score effects or guide training actions.')
finally:env.close()
(r/'first-divergence.json').write_text(json.dumps(report,indent=2)+'\n');print(report)

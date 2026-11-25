from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();rec=root/'docs/training/city-road-choice-2026-11-24';torch.set_num_threads(1)
base=MaskablePPO.load(root/'output/training/city-road-choice-initial-01/start.zip',device='cpu')
paths=dict(roads=root/'output/training/city-road-choice-fit-02/roads/final.zip',joint=root/'output/training/city-whole-fit-01/whole/final.zip')
models={k:MaskablePPO.load(v,device='cpu') for k,v in paths.items()};reports={}
for arm,m in models.items():
 changes={k:float((v-base.policy.state_dict()[k]).abs().max()) for k,v in m.policy.state_dict().items() if not torch.equal(v,base.policy.state_dict()[k])}
 assert changes and all('growth_strategy_' in k or k.startswith('value_net.') for k in changes)
 assert all(torch.isfinite(v).all() for v in m.policy.state_dict().values())
 if arm=='roads':assert not any('wait' in k for k in changes)
 reports[arm]=dict(checkpoint=str(paths[arm]),sha256=sha256(paths[arm]),changed_tensors=changes,optimizer_steps=int(next(iter(m.policy.optimizer.state.values()))['step']),states=[])
e=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=600,allow_bridges=True)
try:
 for seed,action_seed in [(184000000,193251),(184000003,193254)]:
  obs,_=e.reset(options=dict(scenario_seed=seed));rng=np.random.default_rng(action_seed);decision=0
  while not e.done:
   mask=e.action_masks();a=masked_probs(base,obs,mask)
   if decision%10==0:
    for arm,m in models.items():
     b=masked_probs(m,obs,mask)
     assert not b[~mask].any()
     if arm=='roads':assert abs(float(a[0]-b[0]))<1e-6
     road_tv=float(np.abs(a[1:]/a[1:].sum()-b[1:]/b[1:].sum()).sum()/2) if a[1:].sum()>0 else None
     reports[arm]['states'].append(dict(seed=seed,decision=decision,seconds=e.raw['time'],wait_before=float(a[0]),wait_after=float(b[0]),conditional_road_tv=road_tv))
   action=int(rng.choice(len(a),p=a.astype(float)/a.sum(dtype=float)));obs,*_=e.step(action);decision+=1
finally:e.close()
for arm,r in reports.items():
 r['max_wait_probability_error']=max(abs(x['wait_after']-x['wait_before']) for x in r['states'])
 r['mean_conditional_road_tv']=float(np.mean([x['conditional_road_tv'] for x in r['states'] if x['conditional_road_tv'] is not None]))
(rec/'trained-policy-audit.json').write_text(json.dumps(reports,indent=2)+'\n')
print({k:{n:v for n,v in r.items() if n not in ('states','changed_tensors')} for k,r in reports.items()})

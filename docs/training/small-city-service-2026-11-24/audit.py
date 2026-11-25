from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import masked_probs,sha256
r=Path('docs/training/small-city-service-2026-11-24');torch.set_num_threads(1)
p=Path('output/training/city-whole-initial-01/start.zip');q=Path('output/training/small-city-offset-fit-01/ppo/final.zip');a=MaskablePPO.load(p,device='cpu');b=MaskablePPO.load(q,device='cpu')
changes={k:float((v-a.policy.state_dict()[k]).abs().max()) for k,v in b.policy.state_dict().items() if not torch.equal(v,a.policy.state_dict()[k])}
assert changes and all('growth_strategy_' in k or k.startswith('value_net.') for k in changes);assert all(torch.isfinite(v).all() for v in b.policy.state_dict().values())
e=CityCurriculumEnv('output/small-city-offset-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True);rows=[]
try:
 for seed,action_seed in [(191000100,214000),(191000108,214008)]:
  obs,_=e.reset(options=dict(scenario_seed=seed,exercise='small-city-offset-pairs'));rng=np.random.default_rng(action_seed);i=0
  while not e.done:
   mask=e.action_masks();x=masked_probs(a,obs,mask)
   if i%5==0:
    y=masked_probs(b,obs,mask);assert not y[~mask].any();rows.append(dict(seed=seed,decision=i,time=e.raw['time'],wait_before=float(x[0]),wait_after=float(y[0]),conditional_road_tv=float(np.abs(x[1:]/x[1:].sum()-y[1:]/y[1:].sum()).sum()/2) if x[1:].sum() else None))
   action=int(rng.choice(len(x),p=x.astype(float)/x.sum(dtype=float)));obs,*_=e.step(action);i+=1
finally:e.close()
report=dict(parent_sha256=sha256(p),final_sha256=sha256(q),optimizer_steps=int(next(iter(b.policy.optimizer.state.values()))['step']),changed_tensors=changes,states=rows,mean_conditional_road_tv=float(np.mean([x['conditional_road_tv'] for x in rows if x['conditional_road_tv'] is not None])),mean_wait_change=float(np.mean([x['wait_after']-x['wait_before'] for x in rows])))
(r/'policy-audit.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ['changed_tensors','states']})

import json
from pathlib import Path
import numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import masked_probs
from export_city_replays import action_endpoints
r=Path('docs/training/mini-task-repair-2026-11-25');torch.set_num_threads(1)
models={name:MaskablePPO.load(path,device='cpu') for name,path in [('original','output/training/city-whole-initial-01/start.zip'),('expansion','output/training/expansion-comparison-01/expansion/final.zip')]}
e=CityCurriculumEnv('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',validation=True);rows=[]
try:
 for seed in range(231000000,231000016):
  obs,_=e.reset(options=dict(exercise='small-city-offset-single',scenario_seed=seed));mask=e.action_masks();prob={}
  for name,m in models.items():
   p=masked_probs(m,obs,mask).astype(float);q=p[1:]/p[1:].sum();prob[name]=q
   h=-float((q[q>0]*np.log(q[q>0])).sum());top=np.argsort(q)[-8:][::-1]
   rows.append(dict(seed=seed,model=name,wait=float(p[0]),legal_roads=int(mask[1:].sum()),conditional_entropy=h,effective_choices=float(np.exp(h)),top=[dict(edge=action_endpoints(int(i)+1),probability=float(q[i])) for i in top]))
  rows[-1]['conditional_road_tv_vs_original']=float(abs(prob['original']-prob['expansion']).sum()/2)
finally:e.close()
(r/'road-distributions.json').write_text(json.dumps(rows,indent=2))
print('Mean conditional road TV',np.mean([x['conditional_road_tv_vs_original'] for x in rows if 'conditional_road_tv_vs_original' in x]))
for x in rows[:2]:print(x)

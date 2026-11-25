from pathlib import Path
import json,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,LOW,HIGH,PRIORITY,SWAP
from city_road_pilot import edge_action
from prepare_city_policy import masked_probs

torch.set_num_threads(1)
paths=['output/training/city-five-stage-traffic-initial-01/start.zip','output/training/city-five-stage-traffic-01/midpoint.zip']
models=[MaskablePPO.load(p,device='cpu') for p in paths]
e=CityCurriculumEnv('output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True)
rows=[]
try:
 for ex in [PRIORITY,SWAP,LOW,HIGH]:
  for seed in range(118200000,118200004):
   obs,_=e.reset(options=dict(exercise=ex,scenario_seed=seed));mask=e.action_masks()
   refs=e.host.call(command='curriculumReference')['edits']
   actions={r['kind']:edge_action((r['x'],r['y']),(r['toX'],r['toY'])) for r in refs}
   probs=[]
   for model in models:
    p=masked_probs(model,obs,mask)
    probs.append({'wait':float(p[0]),**{k:float(p[a]) for k,a in actions.items()}})
   rows.append(dict(exercise=ex,seed=seed,probabilities=probs))
finally:e.close()
with Path('docs/training/five-stage-city-learning-2026-11-23/traffic-update-probe.json').open('x') as f:json.dump(dict(models=paths,rows=rows),f,indent=2)
for ex in [LOW,HIGH]:
 values=[r for r in rows if r['exercise']==ex]
 print(ex,[(round(r['probabilities'][0]['feeder'],4),round(r['probabilities'][1]['feeder'],4)) for r in values])

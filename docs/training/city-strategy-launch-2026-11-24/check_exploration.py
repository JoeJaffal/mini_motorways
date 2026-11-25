from pathlib import Path
import sys,json,argparse
sys.path.insert(0,str(Path.cwd()/'training'))
import numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,LESSONS
from prepare_city_policy import masked_probs,sha256
p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();torch.set_num_threads(1)
m=MaskablePPO.load(a.checkpoint,device='cpu');e=CityCurriculumEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True);rows=[]
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=141000000,exercise=lesson));mask=e.action_masks();v=masked_probs(m,obs,mask).astype(float);q=v[1:]/v[1:].sum();q=q[mask[1:]];positive=q[q>0]
  entropy=float(-(positive*np.log(positive)).sum())
  rows.append(dict(lesson=lesson,legal_roads=len(q),wait=float(v[0]),conditional_top_road=float(q.max()),conditional_entropy=entropy,effective_roads=float(np.exp(entropy)),roads_below_one_in_million=int((q<1e-6).sum())))
finally:e.close()
a.output.write_text(json.dumps(dict(checkpoint=str(a.checkpoint),sha256=sha256(a.checkpoint),note='Initial native lesson probes only; not a full-city distribution or evidence of successful strategy.',rows=rows),indent=2)+'\n');print(json.dumps(rows,indent=2))

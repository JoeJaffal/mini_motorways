from pathlib import Path
import argparse,json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,LESSONS
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--parent',default='output/training/city-strategy-initial-01/start.zip');p.add_argument('--output',type=Path,required=True);a=p.parse_args();torch.set_num_threads(1)
parent=MaskablePPO.load(a.parent,device='cpu');m=MaskablePPO.load(a.candidate,device='cpu')
changes={k:float((v-parent.policy.state_dict()[k]).abs().max()) for k,v in m.policy.state_dict().items() if not torch.equal(v,parent.policy.state_dict()[k])}
assert all('growth_strategy_' in k or k.startswith('value_net.') for k in changes),changes
assert any('growth_strategy_wait' in k for k in changes)
assert any('growth_strategy_roads' in k for k in changes)
assert all(torch.isfinite(v).all() for v in m.policy.state_dict().values())
e=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll')
try:
 for seed in [2004,99161630,99312933,99324387]:
  obs,_=e.reset(options=dict(scenario_seed=seed));mask=e.action_masks()
  np.testing.assert_array_equal(masked_probs(parent,obs,mask),masked_probs(m,obs,mask))
finally:e.close()
e=CityCurriculumEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True);rows=[]
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=141000000,exercise=lesson));mask=e.action_masks()
  b,c=masked_probs(parent,obs,mask),masked_probs(m,obs,mask)
  assert (c[~mask]==0).all()
  roads0=b[1:]/b[1:].sum();roads1=c[1:]/c[1:].sum()
  rows.append(dict(lesson=lesson,wait_before=float(b[0]),wait_after=float(c[0]),conditional_road_total_variation=float(np.abs(roads0-roads1).sum()/2)))
finally:e.close()
a.output.write_text(json.dumps(dict(candidate=a.candidate,sha256=sha256(Path(a.candidate)),changed_parameters=changes,opening_exact_cases=4,probes=rows),indent=2)+'\n');print(rows)

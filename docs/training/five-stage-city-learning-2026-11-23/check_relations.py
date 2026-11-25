from pathlib import Path
import argparse,json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,LOW,HIGH,PRIORITY,SWAP,JOIN
from city_road_pilot import CityRoadEnv,edge_action
from prepare_city_policy import masked_probs

p=argparse.ArgumentParser();p.add_argument("--checkpoint",default="output/training/city-five-stage-relations-initial-01/start.zip");p.add_argument("--output",type=Path,default=Path("docs/training/five-stage-city-learning-2026-11-23/relations-checks.json"));args=p.parse_args()
torch.set_num_threads(1)
dll='output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll'
m=MaskablePPO.load(args.checkpoint,device='cpu')
old=MaskablePPO.load('output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip',device='cpu')
e=CityCurriculumEnv(dll,validation=True);rows=[]
try:
 for ex in [LOW,HIGH,PRIORITY,SWAP,JOIN]:
  obs,_=e.reset(options=dict(exercise=ex,scenario_seed=118200000));tensor,_=m.policy.obs_to_tensor(obs);mask=e.action_masks()
  with torch.no_grad():v=m.policy.features_extractor.relation_evidence(tensor['grid'])
  refs=e.host.call(command='curriculumReference')['edits'];features={r['kind']:v[0,edge_action((r['x'],r['y']),(r['toX'],r['toY']))-1].tolist() for r in refs}
  m.policy.features_extractor.growth_road_temperature.fill_(1.)
  np.testing.assert_allclose(masked_probs(m,obs,mask),masked_probs(old,obs,mask),atol=1e-6,rtol=1e-5)
  m.policy.features_extractor.growth_road_temperature.fill_(20.)
  if ex in (LOW,HIGH):
   assert features['feeder'][0]==3 and features['separate-exit'][2]==1
   assert features['feeder'][2]==0 and features['separate-exit'][0]==0
  rows.append(dict(exercise=ex,features=features))
finally:e.close()
e=CityRoadEnv(dll)
try:
 obs,_=e.reset(options=dict(scenario_seed=2004));mask=e.action_masks()
 np.testing.assert_array_equal(masked_probs(m,obs,mask),masked_probs(old,obs,mask))
finally:e.close()
# The optimizer applies the critic multiplier and restores the scheduled base LR.
from city_relational_policy import RelativeRateAdam
x=torch.nn.Parameter(torch.tensor(0.));y=torch.nn.Parameter(torch.tensor(0.))
o=RelativeRateAdam([dict(params=[x],lr_scale=1.),dict(params=[y],lr_scale=.01)],lr=.01)
x.grad=torch.ones_like(x);y.grad=torch.ones_like(y);o.step()
assert np.isclose(float((x/y).detach()),100,rtol=1e-5) and all(g['lr']==.01 for g in o.param_groups)
with args.output.open('x') as f:json.dump(dict(rows=rows,opening_parity=True,temperature_one_parity=True,optimizer_ratio=100),f,indent=2)
print(rows)

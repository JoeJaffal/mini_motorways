from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_reserve_policy import CityReservePolicy,CityReserveFeatures
from city_relational_policy import RelativeRateAdam
from city_road_pilot import CityRoadEnv
from city_curriculum import CityCurriculumEnv,LESSONS
from prepare_city_policy import sha256,masked_probs

torch.set_num_threads(1)
parent=Path('output/training/city-five-stage-cold-initial-01/candidate.zip')
out=Path('output/training/city-road-reserve-initial-01');out.mkdir(exist_ok=False)
dll='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll'
e=CityRoadEnv(dll)
try:
 old=MaskablePPO.load(parent,device='cpu')
 m=MaskablePPO(CityReservePolicy,e,device='cpu',n_steps=128,batch_size=64,n_epochs=4,learning_rate=.03,gamma=1.,gae_lambda=.95,ent_coef=.01,target_kl=.03,
 policy_kwargs=dict(features_extractor_class=CityReserveFeatures,features_extractor_kwargs=dict(conservative=True,temperature=20.,road_scale=20.),optimizer_class=RelativeRateAdam,normalize_images=False))
 missing,extra=m.policy.load_state_dict(old.policy.state_dict(),strict=False)
 assert not extra and len(missing)==3 and all(k.endswith('growth_reserve_wait.weight') for k in missing),(missing,extra)
 obs,_=e.reset(options=dict(scenario_seed=2004));mask=e.action_masks()
 np.testing.assert_array_equal(masked_probs(m,obs,mask),masked_probs(old,obs,mask))
finally:e.close()
e=CityCurriculumEnv(dll,validation=True);checks=[]
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=131000000,exercise=lesson));mask=e.action_masks()
  a,b=masked_probs(m,obs,mask),masked_probs(old,obs,mask)
  np.testing.assert_array_equal(a,b)
  checks.append(dict(lesson=lesson,initial_wait=float(a[0]),zero_init_exact=True))
finally:e.close()
m.num_timesteps=old.num_timesteps;m._n_updates=old._n_updates;m.save(out/'start.zip')
(out/'config.json').write_text(json.dumps(dict(parent=str(parent),parent_sha256=sha256(parent),start_sha256=sha256(out/'start.zip'),optimizer='fresh; changed parameter set',checks=checks),indent=2)+'\n')
print(checks)

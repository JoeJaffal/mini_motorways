from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_reserve_policy import CityReservePolicy,CityVisibleReserveFeatures
from city_relational_policy import RelativeRateAdam
from city_curriculum import CityCurriculumEnv,LESSONS
from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256,masked_probs

torch.set_num_threads(1)
parent=Path('output/training/city-road-reserve-pilot-01/final.zip');out=Path('output/training/city-road-reserve-repaired-01');out.mkdir(exist_ok=False)
dll='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll';e=CityRoadEnv(dll)
try:
 old=MaskablePPO.load(parent,device='cpu')
 m=MaskablePPO(CityReservePolicy,e,device='cpu',n_steps=128,batch_size=64,n_epochs=4,learning_rate=.03,gamma=1.,gae_lambda=.95,ent_coef=.01,target_kl=.03,
  policy_kwargs=dict(features_extractor_class=CityVisibleReserveFeatures,features_extractor_kwargs=dict(conservative=True,temperature=20.,road_scale=20.),optimizer_class=RelativeRateAdam,normalize_images=False))
 m.policy.load_state_dict(old.policy.state_dict(),strict=True)
 # No further training is scheduled. Copy moments, recording changed semantics.
 m.policy.optimizer.load_state_dict(old.policy.optimizer.state_dict())
 m.num_timesteps=old.num_timesteps;m._n_updates=old._n_updates
 obs,_=e.reset(options=dict(scenario_seed=2004));mask=e.action_masks()
 np.testing.assert_array_equal(masked_probs(m,obs,mask),masked_probs(old,obs,mask))
finally:e.close()
e=CityCurriculumEnv(dll,validation=True);checks=[]
try:
 for ex in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=131000000,exercise=ex));mask=e.action_masks()
  a,b=masked_probs(old,obs,mask),masked_probs(m,obs,mask)
  np.testing.assert_allclose(a[1:]/a[1:].sum(),b[1:]/b[1:].sum(),atol=2e-6,rtol=2e-5)
  checks.append(dict(exercise=ex,wait_before=float(a[0]),wait_after=float(b[0])))
finally:e.close()
m.save(out/'candidate.zip')
(out/'config.json').write_text(json.dumps(dict(source=str(parent),source_sha256=sha256(parent),candidate_sha256=sha256(out/'candidate.zip'),note='Feature repair only; identical trained weights, copied optimizer, no additional PPO. Resume needs bounded validation.',checks=checks),indent=2)+'\n')
print(checks)

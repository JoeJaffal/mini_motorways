from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_strategy_policy import CityStrategyFeatures,CityStrategyPolicy,STRATEGY_CONTEXT
from city_relational_policy import RelativeRateAdam
from city_road_pilot import CityRoadEnv
from city_curriculum import CityCurriculumEnv,LESSONS
from prepare_city_policy import sha256,masked_probs

torch.set_num_threads(1)
parent=Path('output/training/city-five-stage-cold-initial-01/candidate.zip');out=Path('output/training/city-strategy-initial-01');out.mkdir(exist_ok=False)
dll='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll';e=CityRoadEnv(dll)
old=MaskablePPO.load(parent,device='cpu')
try:
 m=MaskablePPO(CityStrategyPolicy,e,device='cpu',n_steps=512,batch_size=128,n_epochs=4,learning_rate=.003,gamma=1.,gae_lambda=1.,ent_coef=.01,target_kl=.03,
  policy_kwargs=dict(features_extractor_class=CityStrategyFeatures,features_extractor_kwargs=dict(conservative=True,temperature=20.,road_scale=20.),optimizer_class=RelativeRateAdam,normalize_images=False))
 state=old.policy.state_dict();weight=state['value_net.0.weight']
 state['value_net.0.weight']=torch.cat((weight,weight.new_zeros((len(weight),STRATEGY_CONTEXT))),dim=1)
 missing,extra=m.policy.load_state_dict(state,strict=False)
 assert not extra and len(missing)==24 and all('growth_strategy_' in k for k in missing),(missing,extra)
 obs,_=e.reset(options=dict(scenario_seed=2004));mask=e.action_masks()
 np.testing.assert_array_equal(masked_probs(m,obs,mask),masked_probs(old,obs,mask))
finally:e.close()
e=CityCurriculumEnv(dll,validation=True);checks=[]
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=141000000,exercise=lesson));mask=e.action_masks()
  np.testing.assert_array_equal(masked_probs(m,obs,mask),masked_probs(old,obs,mask))
  tensor,_=m.policy.obs_to_tensor(obs)
  with torch.no_grad():
   a,b=m.policy.predict_values(tensor),old.policy.predict_values(tensor)
  torch.testing.assert_close(a,b,rtol=1e-5,atol=1e-5)
  checks.append(dict(lesson=lesson,actor_exact=True,critic_max_difference=float((a-b).abs().max())))
finally:e.close()
m.num_timesteps=old.num_timesteps;m._n_updates=old._n_updates;m.save(out/'start.zip')
(out/'config.json').write_text(json.dumps(dict(parent=str(parent),parent_sha256=sha256(parent),initial_sha256=sha256(out/'start.zip'),optimizer='fresh: new residual modules and expanded critic',checks=checks),indent=2)+'\n')
print(checks)

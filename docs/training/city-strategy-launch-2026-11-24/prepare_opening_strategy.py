from pathlib import Path
from copy import deepcopy
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_opening_strategy_policy import CityOpeningStrategyFeatures,CityOpeningStrategyPolicy
from city_curriculum import CityCurriculumEnv,LESSONS
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();rec=root/'docs/training/city-strategy-launch-2026-11-24';out=root/'output/training/city-strategy-opening-initial-02';out.mkdir(exist_ok=False)
parent=root/'output/training/city-strategy-original-delay-01/segment-001/final.zip';dll='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll';torch.set_num_threads(1);torch.manual_seed(114241)
old=MaskablePPO.load(parent,device='cpu');e=CityRoadEnv(dll)
kwargs=deepcopy(old.policy_kwargs);kwargs['features_extractor_class']=CityOpeningStrategyFeatures
try:
 m=MaskablePPO(CityOpeningStrategyPolicy,e,device='cpu',seed=114241,n_steps=512,batch_size=128,n_epochs=old.n_epochs,learning_rate=.0001,gamma=old.gamma,gae_lambda=1.,ent_coef=old.ent_coef,target_kl=old.target_kl,vf_coef=1e-5,max_grad_norm=old.max_grad_norm,policy_kwargs=kwargs)
 missing,extra=m.policy.load_state_dict(old.policy.state_dict(),strict=False)
 assert missing and not extra and all('opening_strategy_' in k for k in missing),(missing,extra)
 f=m.policy.features_extractor;f.opening_strategy_spatial.load_state_dict(old.policy.features_extractor.growth_strategy_spatial.state_dict(),strict=True)
 # New actor parameters have no prior moments; retain critic Adam state by name.
 previous=dict(old.policy.named_parameters());transferred=[]
 for name,parameter in m.policy.named_parameters():
  if name.startswith('value_net.') and previous[name] in old.policy.optimizer.state:
   m.policy.optimizer.state[parameter]=deepcopy(old.policy.optimizer.state[previous[name]]);transferred.append(name)
 assert len(transferred)==4
 checks=[]
 for seed in [2004,99161630,99312933,99324387,99123141,99433969]:
  obs,_=e.reset(options=dict(scenario_seed=seed));rng=np.random.default_rng(331)
  for step in range(20):
   mask=e.action_masks();a,b=masked_probs(old,obs,mask),masked_probs(m,obs,mask);np.testing.assert_array_equal(a,b)
   tensor,_=m.policy.obs_to_tensor(obs)
   with torch.no_grad():torch.testing.assert_close(old.policy.predict_values(tensor),m.policy.predict_values(tensor),rtol=0,atol=0)
   checks.append(dict(seed=seed,step=step,actor_exact=True,value_exact=True))
   obs,_,terminated,truncated,_=e.step(int(rng.choice(len(a),p=a.astype(float)/a.astype(float).sum())))
   if terminated or truncated:break
finally:e.close()
e=CityCurriculumEnv(dll,validation=True);native=[]
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=141000000,exercise=lesson));mask=e.action_masks();np.testing.assert_array_equal(masked_probs(old,obs,mask),masked_probs(m,obs,mask));native.append(lesson)
finally:e.close()
m.num_timesteps=old.num_timesteps;m._n_updates=old._n_updates;m.save(out/'start.zip')
loaded=MaskablePPO.load(out/'start.zip',device='cpu')
for name,parameter in loaded.policy.named_parameters():
 if name in transferred:
  for key,value in old.policy.optimizer.state[previous[name]].items():
   actual=loaded.policy.optimizer.state[parameter][key]
   if torch.is_tensor(value):torch.testing.assert_close(value,actual,rtol=0,atol=0)
   else:assert value==actual
# Arbitrary opening parameter updates must not alter an established observation.
with torch.no_grad():
 for name,parameter in loaded.policy.features_extractor.named_parameters():
  if name.startswith('opening_strategy_'):parameter.add_(torch.randn_like(parameter)*.1)
e=CityCurriculumEnv(dll,validation=True)
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=141000000,exercise=lesson));tensor,_=loaded.policy.obs_to_tensor(obs)
  with torch.no_grad():_,gate=loaded.policy.features_extractor.strategy_context(tensor)
  assert gate.item(),lesson
  np.testing.assert_array_equal(masked_probs(old,obs,e.action_masks()),masked_probs(loaded,obs,e.action_masks()))
finally:e.close()
record=dict(parent=str(parent),parent_sha256=sha256(parent),initial=str(out/'start.zip'),initial_sha256=sha256(out/'start.zip'),opening_state_checks=checks,native_initial_exact=native,established_actor_exact_after_arbitrary_opening_changes=native,critic_optimizer_state_exact=transferred,new_actor_optimizer='fresh moments for new parameters only',note='Existing learned parameters copied exactly. New spatial opening encoder copies learned growth encoder; zero output heads preserve initial actor and value. Established actor is fixed for the same visible state; changed openings can still change subsequent city states.')
(out/'config.json').write_text(json.dumps(record,indent=2)+'\n');(rec/'opening-initial-checks.json').write_text(json.dumps(record,indent=2)+'\n');print(dict(opening_states=len(checks),native_exact=len(native),critic_moments=len(transferred),sha256=record['initial_sha256']))

from pathlib import Path
from copy import deepcopy
import json, torch, numpy as np, sys
from sb3_contrib import MaskablePPO
from city_road_choice_policy import CityRoadChoicePolicy
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs, sha256

torch.set_num_threads(1)
root=Path.cwd(); rec=root/'docs/training/city-road-choice-2026-11-24'
parent=root/'output/training/city-whole-initial-01/start.zip'
out=root/'output/training/city-road-choice-initial-01';out.mkdir(exist_ok='--validate-existing' in sys.argv)
a=MaskablePPO.load(parent,device='cpu')
e=CityRoadEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=600,allow_bridges=True)
b=MaskablePPO(CityRoadChoicePolicy,e,device='cpu',seed=11424,n_steps=512,batch_size=128,n_epochs=4,learning_rate=.0001,gamma=1.,gae_lambda=1.,ent_coef=a.ent_coef,target_kl=a.target_kl,policy_kwargs=deepcopy(a.policy_kwargs))
b.policy.load_state_dict(a.policy.state_dict(),strict=True)
b.num_timesteps=a.num_timesteps;b._n_updates=a._n_updates
f=b.policy.features_extractor
for module in (f.growth_strategy_wait,f.growth_strategy_visual_wait):
 assert all(torch.count_nonzero(p)==0 for p in module[-1].parameters())
 assert not any(p.requires_grad for p in module.parameters())
assert not a.policy.optimizer.state
states=[];rng=np.random.default_rng(31124)
try:
 for seed in range(184000000,184000008):
  obs,_=e.reset(options=dict(scenario_seed=seed))
  for i in range(16):
   mask=e.action_masks();pa=masked_probs(a,obs,mask);pb=masked_probs(b,obs,mask)
   np.testing.assert_array_equal(pa,pb)
   inputs,_=b.policy.obs_to_tensor(obs)
   with torch.no_grad():torch.testing.assert_close(a.policy.predict_values(inputs),b.policy.predict_values(inputs),rtol=0,atol=0)
   if i%8==0:states.append((deepcopy(obs),mask.copy()))
   action=int(rng.choice(len(pa),p=pa.astype(float)/pa.sum(dtype=float)));obs,*_=e.step(action)
   if e.done:break
 if '--validate-existing' not in sys.argv:b.save(out/'start.zip')
 c=MaskablePPO.load(out/'start.zip',device='cpu')
 before={k:v.clone() for k,v in c.policy.state_dict().items()}
 obs,mask=states[0];inputs,_=c.policy.obs_to_tensor(obs)
 road=int(np.argmax(masked_probs(c,obs,mask)[1:]))+1;dist=c.policy.get_distribution(inputs,mask)
 c.policy.optimizer.zero_grad();(-dist.log_prob(torch.tensor([road])).mean()).backward();c.policy.optimizer.step()
 changed=[k for k,v in c.policy.state_dict().items() if not torch.equal(v,before[k])]
 assert changed and all('growth_strategy_roads' in k or 'growth_strategy_spatial_roads' in k for k in changed)
 errors=[];tvs=[]
 for obs,mask in states:
  pa=masked_probs(b,obs,mask);pc=masked_probs(c,obs,mask)
  errors.append(float(abs(pa[0]-pc[0])))
  if pa[1:].sum()>0:tvs.append(float(np.abs(pa[1:]/pa[1:].sum()-pc[1:]/pc[1:].sum()).sum()/2))
 assert max(errors)<1e-6 and max(tvs)>0
 assert int(next(iter(c.policy.optimizer.state.values()))['step'])==1
 # Saved initialization remains untouched; optimizer test uses a disposable copy.
 d=MaskablePPO.load(out/'start.zip',device='cpu');assert not d.policy.optimizer.state
 assert all(torch.equal(v,d.policy.state_dict()[k]) for k,v in a.policy.state_dict().items())
 report=dict(parent=str(parent),parent_sha256=sha256(parent),checkpoint=str(out/'start.zip'),sha256=sha256(out/'start.zip'),exact_shared_states=len(states),disposable_optimizer_step=1,max_wait_probability_error=max(errors),max_conditional_road_tv=max(tvs),changed_test_tensors=changed,optimizer_groups=3)
 (rec/'initial-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:e.close()

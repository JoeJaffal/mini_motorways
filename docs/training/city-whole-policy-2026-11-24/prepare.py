from pathlib import Path
from copy import deepcopy
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_whole_strategy_policy import CityWholeStrategyPolicy,CityWholeStrategyFeatures
from city_road_pilot import CityRoadEnv
from city_repeated_seeds import CityRepeatedSeedsEnv
from prepare_city_policy import masked_probs,sha256
root=Path.cwd();r=root/'docs/training/city-whole-policy-2026-11-24';out=root/'output/training/city-whole-initial-01';out.mkdir(exist_ok=False)
torch.set_num_threads(1)
parent=root/'output/training/city-strategy-wide-initial-01/start.zip';original=sha256(parent)
a=MaskablePPO.load(parent,device='cpu');kwargs=deepcopy(a.policy_kwargs);kwargs['features_extractor_class']=CityWholeStrategyFeatures
b=MaskablePPO.load(parent,device='cpu',custom_objects=dict(policy_class=CityWholeStrategyPolicy,policy_kwargs=kwargs))
assert all(torch.equal(v,b.policy.state_dict()[k]) for k,v in a.policy.state_dict().items())
dll='output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll';env=CityRoadEnv(dll,horizon=600,allow_bridges=True);rng=np.random.default_rng(31124);checks=0
try:
 for seed in range(184000000,184000008):
  obs,_=env.reset(options=dict(scenario_seed=seed))
  for i in range(32):
   mask=env.action_masks();pa=masked_probs(a,obs,mask);pb=masked_probs(b,obs,mask);np.testing.assert_array_equal(pa,pb)
   inputs,_=b.policy.obs_to_tensor(obs)
   with torch.no_grad():torch.testing.assert_close(a.policy.predict_values(inputs),b.policy.predict_values(inputs),rtol=0,atol=0)
   checks+=1
   action=int(rng.choice(len(pa),p=pa.astype(float)/pa.sum(dtype=float)));obs,*_=env.step(action)
   if env.done:break
 obs,_=env.reset(options=dict(scenario_seed=184000000));mask=env.action_masks();gradients={}
 for name,m in [('gated',a),('whole',b)]:
  m.policy.zero_grad();inputs,_=m.policy.obs_to_tensor(obs)
  gate=m.policy.features_extractor.strategy_context(inputs)[1];assert not gate.any()
  dist=m.policy.get_distribution(inputs,mask);loss=-dist.log_prob(torch.tensor([0])).mean();loss.backward()
  gradients[name]=sum(float(p.grad.abs().sum()) for n,p in m.policy.named_parameters() if 'growth_strategy_' in n and p.grad is not None)
 assert gradients['gated']==0 and gradients['whole']>0
 b.policy.zero_grad();b.save(out/'start.zip');loaded=MaskablePPO.load(out/'start.zip',device='cpu');np.testing.assert_array_equal(masked_probs(b,obs,mask),masked_probs(loaded,obs,mask))
finally:env.close()
e=CityRepeatedSeedsEnv(dll,stage='city',worker=2,workers=16,seed_start=184000000,repeat_city_count=8,allow_bridges=True)
try:
 seeds=[]
 for _ in range(10):seeds.append(e.reset()[1]['seed'])
 assert seeds==[184000000+(2+i)%8 for i in range(10)]
 obs,info=e.reset(options=dict(scenario_seed=185000000,exercise='city'));assert info['seed']==185000000
finally:e.close()
assert sha256(parent)==original
report=dict(parent=str(parent),parent_sha256=original,checkpoint=str(out/'start.zip'),sha256=sha256(out/'start.zip'),exact_actor_value_states=checks,opening_actor_gradient_l1=gradients,repeated_reset_seeds=seeds,explicit_reset_bypass=True,weights_initially_exact=True)
(r/'initial-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report)

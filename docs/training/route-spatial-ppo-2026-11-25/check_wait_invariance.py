"""Probe Wait invariance after actual road-encoder PPO updates."""
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_route_outcome import CityRouteOutcomeEnv
from city_curriculum import SMALL_TIGHT,SMALL_STOCK
from prepare_city_policy import masked_probs,sha256
from prepare_city_wait_repair import optimizer_by_name,assert_state_equal

torch.set_num_threads(1)
parent=Path('output/training/route-spatial-smoke-initial-01/start.zip')
final=Path('output/training/route-spatial-trainer-smoke-01/final.zip')
a=MaskablePPO.load(parent,device='cpu');b=MaskablePPO.load(final,device='cpu')
old=optimizer_by_name(a.policy);new=optimizer_by_name(b.policy)
trainable={n for n,p in b.policy.named_parameters() if p.requires_grad}
assert len(trainable)==22
assert_state_equal({n:s for n,s in old.items() if n not in trainable},{n:s for n,s in new.items() if n not in trainable})
for n in trainable:assert int(new[n]['step'])==int(old[n]['step'])+4
for n,p in a.policy.named_parameters():
 if n not in trainable:torch.testing.assert_close(p,dict(b.policy.named_parameters())[n],rtol=0,atol=0)
f=b.policy.features_extractor
assert not ({p.data_ptr() for p in f.growth_strategy_spatial.parameters()} & {p.data_ptr() for p in f.growth_wait_spatial.parameters()})
encoder_change=max(float((p-dict(a.policy.named_parameters())[n]).abs().max().detach()) for n,p in b.policy.named_parameters() if n.startswith('features_extractor.growth_strategy_spatial.'))
assert encoder_change>0
rows=[];env=CityRouteOutcomeEnv('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',fast_small_city_tail=True)
try:
 for i in range(16):
  obs,_=env.reset(options=dict(exercise=SMALL_TIGHT if i<12 else SMALL_STOCK,scenario_seed=244014000+i))
  rng=np.random.default_rng(720000+i)
  for step in range(4):
   mask=env.action_masks();x=masked_probs(a,obs,mask).astype(float);y=masked_probs(b,obs,mask).astype(float)
   x/=x.sum();y/=y.sum()
   error=abs(x[0]-y[0]);assert error<1e-6
   road_error=0.
   if x[1:].sum()>0 and y[1:].sum()>0:road_error=float(abs(x[1:]/x[1:].sum()-y[1:]/y[1:].sum()).max())
   rows.append(dict(seed=244014000+i,step=step,wait_error=float(error),conditional_road_change=road_error))
   if i==0 and step==0:
    tensor,_=b.policy.obs_to_tensor(obs)
    b.policy.zero_grad(set_to_none=True)
    b.policy.predict_values(tensor).sum().backward()
    assert all(p.grad is None for n,p in b.policy.named_parameters() if n.startswith('features_extractor.'))
   action=int(rng.choice(len(x),p=x));obs,_,_,_,_=env.step(action)
   if env.done:break
finally:env.close()
report=dict(parent_sha256=sha256(parent),final_sha256=sha256(final),states=len(rows),wait_max_error=max(r['wait_error'] for r in rows),conditional_road_max_change=max(r['conditional_road_change'] for r in rows),road_encoder_weight_max_change=encoder_change,frozen_wait_encoder_weights_and_adam_exact=True,all22_trainable_adam_advanced4=True,critic_gradient_does_not_train_encoder=True,copy_storage_independent=True,limits='Disposable128-decision integration check; no performance claim.')
r=Path(__file__).parent
(r/'wait-invariance.json').open('x').write(json.dumps(dict(summary=report,states=rows),indent=2)+'\n')
print(json.dumps(report,indent=2))

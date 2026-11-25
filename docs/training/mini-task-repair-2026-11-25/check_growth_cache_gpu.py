from pathlib import Path
import json,time
import numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import sha256
r=Path('docs/training/mini-task-repair-2026-11-25');torch.set_num_threads(1)
parent=Path('output/training/city-whole-initial-01/start.zip');before=sha256(parent);model=MaskablePPO.load(parent,device='cuda');p=model.policy;p.set_training_mode(False);f=p.features_extractor
samples=[];masks=[];env=CityCurriculumEnv('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll')
try:
 for ex,seed in [('small-city-offset-single',231000000),('small-city-offset-pairs',231000001),('city',184000002),('city',185000007)]:
  obs,_=env.reset(options=dict(exercise=ex,scenario_seed=seed));samples.append(obs);masks.append(env.action_masks())
  for i in range(8):
   if env.done:break
   choices=np.flatnonzero(env.action_masks());obs,*_=env.step(int(choices[min(len(choices)-1,1)]) if i%2 else 0)
  samples.append(obs);masks.append(env.action_masks())
finally:env.close()
from visible_observation import VisibleObservation
for case in ('best','typical','worst'):
 raw=json.loads((r/'long-replays'/case/'final-state.json').read_text())
 samples.append(VisibleObservation().encode(raw,horizon=600))
 terminal_mask=np.zeros_like(masks[0]);terminal_mask[0]=True;masks.append(terminal_mask)
inputs={k:torch.as_tensor(np.stack([x[k] for x in samples]),device='cuda') for k in samples[0]};mask=np.stack(masks);actions=torch.zeros(len(samples),dtype=torch.long,device='cuda')
results=[];grads=[]
for enabled in (False,True):
 f.growth_cache_enabled=enabled;p.optimizer.zero_grad(set_to_none=True)
 values,logp,entropy=p.evaluate_actions(inputs,actions,action_masks=mask)
 results.append(tuple(x.detach().clone() for x in (values,logp,entropy)))
 (-logp.mean()-.01*entropy.mean()+1e-5*values.square().mean()).backward()
 grads.append({n:v.grad.detach().clone() if v.grad is not None else None for n,v in p.named_parameters() if v.requires_grad})
 assert getattr(f.opening_reference,'_growth_features_cache',None) is None
for a,b in zip(*results):torch.testing.assert_close(a,b,rtol=1e-6,atol=1e-6)
for name,a in grads[0].items():
 b=grads[1][name]
 if a is None:assert b is None
 else:torch.testing.assert_close(a,b,rtol=1e-6,atol=1e-6)
# A parameter update must not reuse a previous call's frozen feature values.
p.optimizer.step()
with torch.no_grad():
 f.growth_cache_enabled=False;a=p.evaluate_actions(inputs,actions,action_masks=mask)
 f.growth_cache_enabled=True;b=p.evaluate_actions(inputs,actions,action_masks=mask)
 for x,y in zip(a,b):torch.testing.assert_close(x,y,rtol=1e-6,atol=1e-6)
 timings={}
 for batch in (1,16):
  x={k:v[:1].expand(batch,*v.shape[1:]) for k,v in inputs.items()};ms=np.repeat(mask[:1],batch,axis=0);act=torch.zeros(batch,dtype=torch.long,device='cuda')
  timings[str(batch)]={}
  for enabled in (False,True):
   f.growth_cache_enabled=enabled
   for _ in range(2):p.evaluate_actions(x,act,action_masks=ms)
   times=[]
   for _ in range(12):
    torch.cuda.synchronize();start=time.perf_counter();p.evaluate_actions(x,act,action_masks=ms);torch.cuda.synchronize();times.append(time.perf_counter()-start)
   timings[str(batch)][str(enabled)]=dict(median_seconds=float(np.median(times)),samples=times)
assert sha256(parent)==before
report=dict(observations=len(samples),live_native_observations=8,terminal_encodings_with_wait_only_test_mask=3,values_logprobs_entropies_within_1e6=True,trainable_gradients_within_1e6=True,cache_cleared_each_call=True,post_update_parity=True,gpu_timings=timings,concurrent_training_active=True,checkpoint_unchanged=True)
(r/'growth-cache-gpu-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

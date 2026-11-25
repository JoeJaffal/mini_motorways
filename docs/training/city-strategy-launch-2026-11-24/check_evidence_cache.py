"""Exact forward/gradient/Adam parity and timing for per-call visible evidence reuse."""
from pathlib import Path
from time import perf_counter
from unittest.mock import patch
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_recorded_starts import CityRecordedStartEnv
from city_network_service_policy import CityNetworkServiceFeatures
from prepare_city_policy import sha256

torch.set_num_threads(1);root=Path.cwd();out=root/'docs/training/city-strategy-launch-2026-11-24/evidence-cache-check.json';assert not out.exists()
path=Path('output/training/city-strategy-bridge-reference-city-01/segment-001/final.zip');identity=sha256(path)
env=CityRecordedStartEnv('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',stage='city',worker=1,workers=4,seed_start=174000000,city_horizon=1200,allow_bridges=True,city_starts='output/training/city-strategy-recorded-starts-01/starts.json')
observations=[];masks=[]
try:
 for _ in range(8):
  obs,_=env.reset();observations.append(obs);masks.append(env.action_masks())
finally:env.close()
models=[MaskablePPO.load(path,device='cuda') for _ in range(2)]
for m,enabled in zip(models,[False,True]):m.policy.features_extractor.evidence_cache_enabled=enabled
obs={k:torch.as_tensor(np.stack([o[k] for o in observations]),device='cuda') for k in observations[0]};mask=np.stack(masks)
with torch.no_grad():
 f=[m.policy.features_extractor(obs) for m in models];assert torch.equal(*f)
 probs=[m.policy.get_distribution(obs,action_masks=mask).distribution.probs.clone() for m in models];assert torch.equal(*probs)
 values=[m.policy.predict_values(obs) for m in models];assert torch.equal(*values)
 actions=probs[0].argmax(1)
original=CityNetworkServiceFeatures.service_features;counts=[]
for m in models:
 calls=[0]
 def count(self,grid):calls[0]+=1;return original(self,grid)
 with patch.object(CityNetworkServiceFeatures,'service_features',count),torch.no_grad():m.policy.get_distribution(obs,action_masks=mask)
 counts.append(calls[0])
timings=[]
for m in models:
 times=[]
 with torch.no_grad():
  for _ in range(3):
   torch.cuda.synchronize();start=perf_counter()
   for _ in range(8):m.policy.get_distribution(obs,action_masks=mask)
   torch.cuda.synchronize();times.append((perf_counter()-start)/8)
 timings.append(times)
for m in models:
 m.policy.optimizer.zero_grad()
 value,logp,entropy=m.policy.evaluate_actions(obs,actions,action_masks=mask)
 loss=-(logp*torch.linspace(-1,1,8,device='cuda')).mean()-.01*entropy.mean()+1e-5*(value.flatten()-torch.linspace(20,200,8,device='cuda')).square().mean()
 loss.backward()
for (name,a),(other,b) in zip(models[0].policy.named_parameters(),models[1].policy.named_parameters()):
 assert name==other and ((a.grad is None and b.grad is None) or torch.equal(a.grad,b.grad)),name
for m in models:
 torch.nn.utils.clip_grad_norm_(m.policy.parameters(),.5);m.policy.optimizer.step()
a=models[0].policy.state_dict();b=models[1].policy.state_dict();assert all(torch.equal(v,b[k]) for k,v in a.items())
assert all(m.policy.features_extractor._evidence_cache is None for m in models)
assert sha256(path)==identity
r=dict(checkpoint=str(path),sha256=identity,cases=8,feature_probability_value_gradient_and_adam_exact=True,cache_cleared=True,service_body_calls=counts,gpu_batch8_seconds=timings,speedup=float(np.median(timings[0])/np.median(timings[1])),default_enabled=False,note='One test Adam step only on in-memory copies; no saved checkpoint modified. Timing is this batch/model/device, not an end-to-end throughput guarantee.')
out.write_text(json.dumps(r,indent=2)+'\n');print(out.read_text())

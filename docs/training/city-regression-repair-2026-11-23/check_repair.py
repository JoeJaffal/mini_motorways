from pathlib import Path
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
torch.set_num_threads(1)
root=Path('output/training/city-established-pilot-01')
s=json.loads((root/'state.json').read_text())
path=root/s['checkpoints'][-1]['path']
new=MaskablePPO.load(path,device='cpu')
old=MaskablePPO.load('output/training/city-learning-long-01/segment-01/checkpoints/city-000413696-e191fc32.zip',device='cpu')
for k,v in old.policy.features_extractor.state_dict().items():
 torch.testing.assert_close(v,new.policy.features_extractor.opening_reference.state_dict()[k],atol=0,rtol=0)
assert any(not torch.equal(v,old.policy.state_dict()[k]) for k,v in new.policy.state_dict().items() if '.growth_roads.' in k and 'opening_reference' not in k)
cases=json.loads(Path('docs/training/city-regression-repair-2026-11-23/replays.json').read_text())
review=json.loads(Path('output/training/city-learning-long-01/segment-02/review.json').read_text())
orig=[json.loads(s) for s in (Path(review['folder'])/'games.jsonl').read_text().splitlines()]
env=CityRoadEnv('output/city-network-service-build.NdaqGi/bin/TrafficHost/release/TrafficHost.dll')
results=[]
try:
 for case in cases:
  seed=case['seed'];r=next(g for g in orig if g['model']==1 and g['seed']==seed)
  obs,info=env.reset(options={'scenario_seed':seed});rng=np.random.default_rng(r['action_seed'])
  count=0;first=None
  while not env.done:
   mask=env.action_masks()
   with torch.no_grad():
    tensor,_=new.policy.obs_to_tensor(obs)
    established=bool(new.policy.features_extractor.service_features(tensor['grid'])[-2])
   p=masked_probs(new,obs,mask)
   if not established:
    np.testing.assert_array_equal(p,masked_probs(old,obs,mask));count+=1
   p=p.astype(float);p/=p.sum()
   action=int(rng.choice(len(p),p=p))
   obs,reward,_,_,info=env.step(action)
   if reward and first is None:first=info['seconds']
  results.append(dict(seed=seed,prior_score=r['trips'],score=info['trips'],first_delivery=first,protected_states=count))
finally:env.close()
Path('docs/training/city-regression-repair-2026-11-23/repair-checks.json').write_text(json.dumps(dict(checkpoint=str(path),sha256=sha256(path),cases=results,opening_weights_exact=True,spatial_weights_updated=True),indent=2)+'\n')
print(results)

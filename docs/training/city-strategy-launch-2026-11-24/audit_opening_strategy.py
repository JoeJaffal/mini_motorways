from pathlib import Path
import argparse,json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,LESSONS
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--parent');p.add_argument('--output',type=Path,required=True);args=p.parse_args();torch.set_num_threads(1)
initial=MaskablePPO.load('output/training/city-strategy-opening-initial-02/start.zip',device='cpu');m=MaskablePPO.load(args.candidate,device='cpu');old=MaskablePPO.load('output/training/city-strategy-original-delay-01/segment-001/final.zip',device='cpu')
changes={k:float((v-initial.policy.state_dict()[k]).abs().max()) for k,v in m.policy.state_dict().items() if not torch.equal(v,initial.policy.state_dict()[k])}
assert changes and all('opening_strategy_' in k or k.startswith('value_net.') for k in changes)
assert any('opening_strategy_wait' in k for k in changes) and any('opening_strategy_roads' in k for k in changes)
assert all(torch.isfinite(v).all() for v in m.policy.state_dict().values())
for k,v in old.policy.state_dict().items():
 if not k.startswith('value_net.'):assert torch.equal(v,m.policy.state_dict()[k]),k
native=[];e=CityCurriculumEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True)
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=141000000,exercise=lesson));mask=e.action_masks();np.testing.assert_array_equal(masked_probs(old,obs,mask),masked_probs(m,obs,mask));native.append(lesson)
finally:e.close()
probes=[];e=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll')
try:
 for seed in [2004,99161630,99312933,99324387,99123141,99433969]:
  obs,_=e.reset(options=dict(scenario_seed=seed));mask=e.action_masks();a,b=masked_probs(old,obs,mask),masked_probs(m,obs,mask);probes.append(dict(seed=seed,wait_before=float(a[0]),wait_after=float(b[0]),total_variation=float(np.abs(a-b).sum()/2)))
finally:e.close()
args.output.write_text(json.dumps(dict(candidate=args.candidate,sha256=sha256(Path(args.candidate)),changed_parameters=changes,established_initial_exact=native,opening_probes=probes),indent=2)+'\n');print(probes)

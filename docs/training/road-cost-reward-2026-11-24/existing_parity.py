from pathlib import Path
import json,numpy as np
from city_curriculum import CityCurriculumEnv
hosts=['output/small-city-offset-build-01/bin/TrafficHost/release/TrafficHost.dll','output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'];envs=[CityCurriculumEnv(h) for h in hosts];count=0
try:
 for seed in range(198800000,198800004):
  for e in envs:e.reset(options=dict(scenario_seed=seed,exercise='small-city-offset-pairs'))
  rng=np.random.default_rng(seed)
  while not envs[0].done:
   a,b=envs;assert a.raw==b.raw;np.testing.assert_array_equal(a.action_masks(),b.action_masks());action=int(rng.choice(np.flatnonzero(a.action_masks())))
   x,rx,tx,ux,ix=a.step(action);y,ry,ty,uy,iy=b.step(action);assert (rx,tx,ux,ix)==(ry,ty,uy,iy)
   for k in x:np.testing.assert_array_equal(x[k],y[k])
   count+=1
 assert a.raw==b.raw
finally:
 for e in envs:e.close()
Path('docs/training/road-cost-reward-2026-11-24/existing-fixture-parity.json').write_text(json.dumps(dict(exact_transitions=count,hosts=hosts))+'\n');print(count)

from pathlib import Path
import sys,json,torch,numpy as np
sys.path.insert(0,str(Path.cwd()/'training'))
from sb3_contrib import MaskablePPO
from city_task_rollout_buffer import CityTaskRolloutBuffer
from city_curriculum import CityCurriculumEnv,LESSONS
from prepare_city_policy import masked_probs,sha256
p=Path('output/training/city-strategy-balanced-extension-01/segment-001/midpoint.zip');torch.set_num_threads(1)
a=MaskablePPO.load(p,device='cpu');b=MaskablePPO.load(p,device='cpu',rollout_buffer_class=CityTaskRolloutBuffer,rollout_buffer_kwargs=dict(worker_tasks=['city']*8+['reserve']*4+['priority']*4,return_advantage_tasks=('reserve',)))
def exact(x,y):
 if isinstance(x,torch.Tensor):assert torch.equal(x,y)
 elif isinstance(x,dict):
  assert x.keys()==y.keys()
  for k in x:exact(x[k],y[k])
 elif isinstance(x,(tuple,list)):
  assert len(x)==len(y)
  for v,w in zip(x,y):exact(v,w)
 else:assert x==y,(x,y)
exact(a.get_parameters(),b.get_parameters());assert a.num_timesteps==b.num_timesteps and a._n_updates==b._n_updates and b.normalize_advantage
e=CityCurriculumEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',validation=True)
try:
 for lesson in LESSONS:
  obs,_=e.reset(options=dict(scenario_seed=141000000,exercise=lesson));mask=e.action_masks();np.testing.assert_array_equal(masked_probs(a,obs,mask),masked_probs(b,obs,mask))
finally:e.close()
Path('docs/training/city-strategy-launch-2026-11-24/return-advantage-load-check.json').write_text(json.dumps(dict(parent=str(p),sha256=sha256(p),parameters_and_optimizer_exact=True,actor_exact_lessons=len(LESSONS),num_timesteps=b.num_timesteps,n_updates=b._n_updates),indent=2)+'\n');print('Exact weights, optimizer and nine actor probes')

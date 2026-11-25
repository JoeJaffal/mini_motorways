import importlib.util,json
from pathlib import Path
import numpy as np
import city_curriculum as current
r=Path('docs/training/mini-task-repair-2026-11-25');spec=importlib.util.spec_from_file_location('prior_curriculum',r/'runtime-source/city_curriculum.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
dll='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll';a=current.CityCurriculumEnv(dll,allow_bridges=True);b=prior.CityCurriculumEnv(dll,allow_bridges=True);count=0
try:
 for ex in ('city',*current.SMALL_LESSONS,*current.LESSONS):
  options=dict(exercise=ex,scenario_seed=235000010);x,ix=a.reset(options=options);y,iy=b.reset(options=options)
  assert ix==iy and a.raw==b.raw and a.horizon==b.horizon
  for _ in range(8):
   for k in x:np.testing.assert_array_equal(x[k],y[k])
   np.testing.assert_array_equal(a.action_masks(),b.action_masks())
   if a.done:break
   action=int(np.flatnonzero(a.action_masks())[-1]) if count%3 else 0
   x,ra,ta,ua,ia=a.step(action);y,rb,tb,ub,ib=b.step(action);assert (ra,ta,ua,ia)==(rb,tb,ub,ib) and a.raw==b.raw;count+=1
finally:a.close();b.close()
for invalid in (0,59,601):
 try:current.CityCurriculumEnv('does-not-exist',small_city_horizon=invalid)
 except ValueError:pass
 else:raise AssertionError('Invalid horizon accepted')
(r/'default-horizon-check.json').write_text(json.dumps(dict(exact_transitions=count,default_behavior_unchanged=True,invalid_rejected_before_host=True),indent=2));print('PASS',count)

from pathlib import Path
import json,numpy as np
from city_curriculum import CityCurriculumEnv,LESSONS,RESERVE
from prepare_city_policy import sha256
old='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll'
new='output/city-strategy-short-delay-build-01/bin/TrafficHost/release/TrafficHost.dll'
rows=[];transitions=0

def same(a,b):
 assert a.raw==b.raw
 for key in a.observation():np.testing.assert_array_equal(a.observation()[key],b.observation()[key])
 np.testing.assert_array_equal(a.action_masks(),b.action_masks())

a=CityCurriculumEnv(old,validation=True);b=CityCurriculumEnv(new,validation=True)
try:
 for exercise in (*LESSONS,'city'):
  for index in range(4):
   options=dict(scenario_seed=154000000+index,exercise=exercise)
   a.reset(options=options);b.reset(options=options);same(a,b)
   rng=np.random.default_rng(index)
   for step in range(40):
    if a.done:break
    mask=a.action_masks();choices=np.flatnonzero(mask)
    action=int(rng.choice(choices)) if step%3==0 else 0
    ra=a.step(action);rb=b.step(action);assert ra[1:]==rb[1:];same(a,b);transitions+=1
finally:a.close();b.close()
for validation in (False,True):
 a=CityCurriculumEnv(new,validation=validation);b=CityCurriculumEnv(new,validation=validation,reserve_delay_seconds=2)
 try:
  for index in range(8):
   options=dict(scenario_seed=154100000+index,exercise=RESERVE)
   a.reset(options=options);b.reset(options=options);same(a,b)
   start=b.raw['time'];assert b.info()['future_targets']==0
   a.step(0);b.step(0);same(a,b)
   while not b.info()['future_targets'] and b.raw['time']-start<4:b.step(0)
   assert b.info()['future_targets']==1 and 2<=b.raw['time']-start<=3
   rows.append(dict(validation=validation,seed=options['scenario_seed'],initial_exact=True,first_second_exact=True,appearance_delay=b.raw['time']-start))
   # Explicit-delay configuration cannot leak into ordinary reset.
   city=dict(scenario_seed=154200000+index,exercise='city');a.reset(options=city);b.reset(options=city)
   for _ in range(10):a.step(0);b.step(0);same(a,b)
 finally:a.close();b.close()
# Old binary must reject the new protocol, rather than silently ignore an option.
a=CityCurriculumEnv(old,reserve_delay_seconds=2)
try:
 try:a.reset(options=dict(scenario_seed=154100000,exercise=RESERVE))
 except RuntimeError:pass
 else:raise AssertionError('Old host silently accepted new practice option')
finally:a.close()
result=dict(default_transitions_exact=transitions,rows=rows,old_host_rejects=True,old_sha256=sha256(Path(old)),new_sha256=sha256(Path(new)))
Path('docs/training/city-strategy-launch-2026-11-24/short-delay-parity.json').write_text(json.dumps(result,indent=2)+'\n');print(result)

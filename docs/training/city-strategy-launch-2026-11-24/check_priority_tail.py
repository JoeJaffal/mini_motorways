from pathlib import Path
import sys,json,time,numpy as np
sys.path.insert(0,str(Path.cwd()/'training'))
from city_curriculum import CityCurriculumEnv,PRIORITY,SWAP
host='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll';old=CityCurriculumEnv(host,validation=True,collapse_forced_wait=True);fast=CityCurriculumEnv(host,validation=True,collapse_forced_wait=True,fast_priority_tail=True);rows=[]
try:
 for ex in (PRIORITY,SWAP):
  for index in range(16):
   seed=147000000+index;options=dict(scenario_seed=seed,exercise=ex)
   a,_=old.reset(options=options);b,_=fast.reset(options=options)
   for k in a:np.testing.assert_array_equal(a[k],b[k])
   for _ in range(index%4):
    a=old.step(0);b=fast.step(0)
    for k in a[0]:np.testing.assert_array_equal(a[0][k],b[0][k])
    assert a[1:]==b[1:]
   mask=old.action_masks();np.testing.assert_array_equal(mask,fast.action_masks());legal=np.flatnonzero(mask[1:])+1
   action=int(legal[0 if index%2 else -1])
   start=time.monotonic();a=old.step(action);old_seconds=time.monotonic()-start
   start=time.monotonic();b=fast.step(action);fast_seconds=time.monotonic()-start
   assert a[1:]==b[1:],(ex,seed,a[1:],b[1:])
   assert old.raw==fast.raw,(ex,seed,'native final mismatch')
   assert a[2] and not a[3] and b[2] and not b[3]
   assert fast.observation_space.contains(b[0])
   # Terminal motion history is unused by PPO. The next episode starts with
   # identical observations, so no learning-visible state is skipped.
   motion_diff=bool(np.any(a[0]['grid'][57:]!=b[0]['grid'][57:]))
   a,_=old.reset(options=options);b,_=fast.reset(options=options)
   for k in a:np.testing.assert_array_equal(a[k],b[k])
   rows.append(dict(exercise=ex,seed=seed,action=action,old_seconds=old_seconds,fast_seconds=fast_seconds,terminal_motion_differs=motion_diff))
finally:old.close();fast.close()
p=Path('docs/training/city-strategy-launch-2026-11-24/priority-tail-check.json');p.write_text(json.dumps(dict(cases=rows,exact_native_final_reward_flags_info_and_next_reset=True,speedup=sum(r['old_seconds'] for r in rows)/sum(r['fast_seconds'] for r in rows)),indent=2)+'\n');print(json.loads(p.read_text())['speedup'])

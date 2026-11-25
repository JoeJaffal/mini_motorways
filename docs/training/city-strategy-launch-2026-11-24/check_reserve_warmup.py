from pathlib import Path
import sys,json,numpy as np
sys.path.insert(0,str(Path.cwd()/'training'))
from city_curriculum import CityCurriculumEnv,RESERVE
host='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll';rows=[]
for validation in (False,True):
 old=CityCurriculumEnv(host,validation=validation);warm=CityCurriculumEnv(host,validation=validation,reserve_warmup_seconds=6)
 try:
  for i in range(8):
   seed=149000000+i;options=dict(scenario_seed=seed,exercise=RESERVE)
   old.reset(options=options);b,info=warm.reset(options=options)
   for _ in range(6):a=old.step(0)[0]
   assert old.raw==warm.raw
   for k in a:np.testing.assert_array_equal(a[k],b[k])
   np.testing.assert_array_equal(old.action_masks(),warm.action_masks())
   assert info['trips']==0 and info['seconds']==0 and info['future_targets']==0
   before=warm.raw['tripsCompleted'];left=old.step(0);right=warm.step(0)
   assert left[1]==right[1]==warm.raw['tripsCompleted']-before
   for k in left[0]:np.testing.assert_array_equal(left[0][k],right[0][k])
   rows.append(dict(seed=seed,validation=validation,physical_state_and_actor_input_exact=True,warmup_rewards_excluded=True))
 finally:old.close();warm.close()
p=Path('docs/training/city-strategy-launch-2026-11-24/reserve-warmup-check.json');p.write_text(json.dumps(dict(cases=rows,warmup_seconds=6,note='Fixed warmup before rated episode; original evaluation remains zero warmup.'),indent=2)+'\n');print(len(rows),'cases pass')

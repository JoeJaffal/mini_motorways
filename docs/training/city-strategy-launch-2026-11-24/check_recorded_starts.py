from pathlib import Path
import json,tempfile,numpy as np
from city_recorded_starts import CityRecordedStartEnv,raw_digest,observation_digest
from city_curriculum import CityCurriculumEnv
DLL='output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll'
MANIFEST=Path('output/training/city-strategy-recorded-start-smoke-01/starts.json')
def make(rank,path=MANIFEST):return CityRecordedStartEnv(DLL,stage='city',worker=rank,workers=4,seed_start=172000000,city_horizon=1200,allow_bridges=True,city_starts=path)
checks=[];manifest=json.loads(MANIFEST.read_text());prefix=manifest['starts'][0]
e=make(1)
try:
 obs,info=e.reset();assert raw_digest(e.raw)==prefix['raw_sha256'] and observation_digest(obs)==prefix['observation_sha256']
 assert info['trips']==0 and info['initial_trips']==prefix['trips']>0 and info['road_actions']==info['wait_actions']==0
 checks.append('Exact native world and motion-history observation replay; prefix score/actions excluded')
 total=0
 for _ in range(12):
  _,r,_,_,info=e.step(0);total+=r
  assert total==e.raw['tripsCompleted']-prefix['trips']==info['trips']
 checks.append('Only subsequent native deliveries counted as reward and episode trips')
 obs,info=e.reset(options=dict(exercise='city',scenario_seed=2004));assert info['initial_trips']==0 and info['seconds']==0 and info['prefix_id'] is None
 checks.append('Explicit evaluation reset bypasses recorded start')
finally:e.close()
e=make(0);old=CityCurriculumEnv(DLL,stage='city',worker=0,workers=4,seed_start=172000000,city_horizon=1200,allow_bridges=True)
try:
 a,ia=e.reset();b,ib=old.reset()
 for i in range(32):
  assert all(np.array_equal(a[k],b[k]) for k in a) and raw_digest(e.raw)==raw_digest(old.raw)
  mask=e.action_masks();assert np.array_equal(mask,old.action_masks())
  action=0 if i%3==0 else int(np.flatnonzero(mask)[-1])
  a,ra,ta,xa,ia=e.step(action);b,rb,tb,xb,ib=old.step(action)
  assert (ra,ta,xa)==(rb,tb,xb) and all(ia[k]==v for k,v in ib.items())
 checks.append('Cold worker:32 exact legacy transitions, masks, observations and common info')
finally:e.close();old.close()
with tempfile.TemporaryDirectory() as folder:
 bad=Path(folder)/'bad.json';changed=json.loads(MANIFEST.read_text());changed['starts'][0]['raw_sha256']='bad';bad.write_text(json.dumps(changed));e=make(1,bad)
 try:
  try:e.reset()
  except RuntimeError:checks.append('Corrupted native-state digest rejected')
  else:raise AssertionError('Corrupted replay accepted')
 finally:e.close()
 changed=json.loads(MANIFEST.read_text());changed['host_sha256']='bad';bad.write_text(json.dumps(changed))
 try:make(1,bad)
 except ValueError:checks.append('Different native host rejected before launch')
 else:raise AssertionError('Wrong host accepted')
out=Path('docs/training/city-strategy-launch-2026-11-24/recorded-start-native-checks.json');assert not out.exists();out.write_text(json.dumps(dict(passed=len(checks),checks=checks,test_only_seed=prefix['seed'],note='This development-seed prefix is only a replay test, never part of training data.'),indent=2)+'\n');print(out.read_text())

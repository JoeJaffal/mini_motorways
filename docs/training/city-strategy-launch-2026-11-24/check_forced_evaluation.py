from pathlib import Path
import sys,json,time,torch
sys.path.insert(0,str(Path.cwd()/'training'))
from sb3_contrib import MaskablePPO
from audit_city_service import trace
from evaluate_city_curriculum import play
from city_curriculum import CityCurriculumEnv,PRIORITY,SWAP,RESERVE,ROUTE
from prepare_city_policy import sha256
host='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll';path=Path('output/training/city-strategy-balanced-fast-01/final.zip');torch.set_num_threads(1);m=MaskablePPO.load(path,device='cpu');identity=sha256(path);rows=[]
for lesson in (PRIORITY,SWAP,RESERVE,ROUTE):
 e=CityCurriculumEnv(host,validation=True)
 try:
  start=time.monotonic();a=play(e,lesson,141000000,74111,m,skip_forced_inference=False);old=time.monotonic()-start
  start=time.monotonic();b=play(e,lesson,141000000,74111,m,skip_forced_inference=True);new=time.monotonic()-start
  assert a==b,(lesson,a,b)
  rows.append(dict(case=lesson,old_seconds=old,new_seconds=new,exact=True))
 finally:e.close()
for seed,action_seed in [(99005063,1419396886),(99265995,13757151)]:
 start=time.monotonic();a=trace(host,m,seed,action_seed,estimate=False,skip_forced_inference=False);old=time.monotonic()-start
 start=time.monotonic();b=trace(host,m,seed,action_seed,estimate=False,skip_forced_inference=True);new=time.monotonic()-start
 assert a==b,(seed,a,b)
 rows.append(dict(case='city',seed=seed,action_seed=action_seed,old_seconds=old,new_seconds=new,exact=True))
assert sha256(path)==identity
p=Path('docs/training/city-strategy-launch-2026-11-24/forced-evaluation-check.json');p.write_text(json.dumps(dict(rows=rows,checkpoint_sha256=identity,note='Only singleton-mask neural inference skipped. All native steps, observation histories and action RNG draws remain unchanged.'),indent=2)+'\n');print(rows)

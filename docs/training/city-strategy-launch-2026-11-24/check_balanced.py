from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()/'training'))
from city_curriculum import CityCurriculumEnv
rows=[];seeds=[]
for rank in range(16):
 e=CityCurriculumEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',stage='strategy-balanced',worker=rank,workers=16,seed_start=145000000,collapse_forced_wait=True)
 try:
  tasks=[]
  for _ in range(2):
   obs,info=e.reset();assert e.observation_space.contains(obs) and e.action_masks().any();tasks.append(info['exercise']);seeds.append(info['seed'])
  assert tasks[0]==tasks[1]
  rows.append(dict(worker=rank,exercise=tasks[0]))
 finally:e.close()
assert len(set(seeds))==len(seeds)
from collections import Counter
counts=Counter(r['exercise'] for r in rows)
assert counts=={'city':8,'midgame-network-reserve':4,'traffic-priority-established':2,'traffic-priority-established-swap':2}
p=Path('docs/training/city-strategy-launch-2026-11-24/balanced-check.json');p.write_text(json.dumps(dict(assignments=rows,counts=counts,unique_reset_seeds=len(seeds),native_observation_and_masks_valid=True),indent=2)+'\n');print(counts)

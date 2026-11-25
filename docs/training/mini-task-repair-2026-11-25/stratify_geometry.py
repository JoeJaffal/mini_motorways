import json
from pathlib import Path
from city_curriculum import CityCurriculumEnv
from environment import DIRS
r=Path('docs/training/mini-task-repair-2026-11-25/audit');rows=[json.loads(l) for l in (r/'games.jsonl').read_text().splitlines()];geometry=[]
e=CityCurriculumEnv('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',validation=True)
try:
 for ex in ['small-city-offset-single','small-city-offset-stock','small-city-offset-pairs']:
  for seed in range(231000000,231000016):
   e.reset(options=dict(exercise=ex,scenario_seed=seed));pts=[]
   for b in e.raw['buildings']:
    c=b['entrance'];d=DIRS[b['drivewayDirection']];pts.append((c['x']+d[0],c['y']+d[1]))
   dist=max(abs(a-b) for a,b in zip(*pts));geometry.append(dict(exercise=ex,seed=seed,approach_distance=dist,opening_gate=dist<=6))
finally:e.close()
(r/'geometry.json').write_text(json.dumps(geometry,indent=2))
summary=[]
for m in ('original','expansion'):
 for ex in ['small-city-offset-single','small-city-offset-stock','small-city-offset-pairs']:
  for gate in (True,False):
   group=[x for x in rows if x['model']==m and x['exercise']==ex and next(g['opening_gate'] for g in geometry if g['exercise']==ex and g['seed']==x['seed'])==gate]
   summary.append(dict(model=m,exercise=ex,opening_gate=gate,games=len(group),successes=sum(x['success'] for x in group)))
(r/'geometry-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

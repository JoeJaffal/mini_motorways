from pathlib import Path
import json
from city_curriculum import CityCurriculumEnv,LESSONS,JOIN,ROUTE,DELAY,PRIORITY,SWAP,QUIET
from city_road_pilot import edge_action

dll='output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll'
rows=[]
for ex in LESSONS:
 outcomes=[]
 for collapse in [False,True]:
  env=CityCurriculumEnv(dll,validation=True,collapse_forced_wait=collapse)
  try:
   obs,_=env.reset(options=dict(exercise=ex,scenario_seed=118100001))
   refs=env.host.call(command='curriculumReference')['edits']
   if ex in (PRIORITY,SWAP):refs=[r for r in refs if r['kind']=='upper']
   elif ex not in (JOIN,ROUTE,DELAY,QUIET):refs=[r for r in refs if r['kind']=='feeder']
   actions=[edge_action((r['x'],r['y']),(r['toX'],r['toY'])) for r in refs]
   total=0;calls=0;forced=0
   while not env.done:
    a=actions.pop(0) if actions and env.action_masks()[actions[0]] else 0
    obs,r,term,trunc,info=env.step(a);total+=r;calls+=1;forced+=info['forced_waits']
   assert total==info['trips']
   if collapse:assert term and not trunc
   outcomes.append(dict(raw=env.raw,reward=total,calls=calls,forced=forced))
  finally:env.close()
 assert outcomes[0]['raw']==outcomes[1]['raw'] and outcomes[0]['reward']==outcomes[1]['reward']
 rows.append(dict(exercise=ex,reward=outcomes[0]['reward'],ordinary_calls=outcomes[0]['calls'],collapsed_calls=outcomes[1]['calls'],forced=outcomes[1]['forced']))
print(rows)
with Path('docs/training/five-stage-city-learning-2026-11-23/forced-wait-checks.json').open('x') as f:json.dump(rows,f,indent=2)

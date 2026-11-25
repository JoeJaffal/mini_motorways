from pathlib import Path
import json
from city_curriculum import CityCurriculumEnv,RESERVE
from city_road_pilot import edge_action
DLL='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll'
rows=[]
for seed in [131000000,131000001,131000002,131000003]:
 states=[]
 for collapse in [False,True]:
  env=CityCurriculumEnv(DLL,validation=True,collapse_forced_wait=collapse)
  try:
   obs,info=env.reset(options=dict(exercise=RESERVE,scenario_seed=seed))
   assert info['future_targets']==0 and len(env.raw['buildings'])==3
   refs=env.host.call(command='curriculumReference')['edits']
   actions=[edge_action((r['x'],r['y']),(r['toX'],r['toY'])) for r in refs]
   reward=0;steps=0
   while not env.done:
    mask=env.action_masks()
    a=actions.pop(0) if info['future_targets'] and actions and mask[actions[0]] else 0
    obs,r,term,trunc,info=env.step(a);reward+=r;steps+=1
   assert reward==info['trips']==sum(info['served'].values())
   assert info['new_deliveries']>0
   if collapse:assert term and not trunc
   states.append((env.raw,reward))
   rows.append(dict(seed=seed,collapsed=collapse,steps=steps,reward=reward,future_stock=info['future_stock']))
   # Reset cancels a pending future spawn and does not leak into ordinary city.
   env.reset(options=dict(exercise=RESERVE,scenario_seed=seed))
   env.reset(options=dict(exercise='city',scenario_seed=2004))
   ordinary=CityCurriculumEnv(DLL)
   try:
    ordinary.reset(options=dict(exercise='city',scenario_seed=2004))
    for _ in range(25):
     env.step(0);ordinary.step(0);assert env.raw==ordinary.raw
   finally:ordinary.close()
  finally:env.close()
 assert states[0]==states[1]
assert any(rows[i+1]['steps']<rows[i]['steps'] for i in range(0,len(rows),2))
Path('docs/training/road-reserve-learning-2026-11-23/native-reserve-checks.json').write_text(json.dumps(rows,indent=2)+'\n')
print(rows)

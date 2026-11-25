"""Validate task labels through native Wait-only continuation, not a planner."""
from pathlib import Path
import json
from city_wait_decision import CityWaitDecisionEnv,SCHEDULE,NEEDS_BUILD
r=Path('docs/training/build-wait-ppo-2026-11-25');rows=[]
env=CityWaitDecisionEnv('output/wait-decision-build-02/artifacts/bin/TrafficHost/release/TrafficHost.dll',validation=True,bandit=False)
try:
 for case in sorted(set(SCHEDULE)):
  for seed in range(244020000,244020008):
   obs,info=env.reset(options=dict(case=case,scenario_seed=seed))
   initial={b['id']:b['served'] for b in env.raw['buildings'] if not b['isHouse']}
   before_time=env.raw['time'];stock=info['road_stock']
   while not env.done:obs,reward,t,tr,info=env.step(0)
   final={b['id']:b['served'] for b in env.raw['buildings'] if not b['isHouse']}
   pending=[k for k,v in initial.items() if v==0]
   if case in NEEDS_BUILD:
    assert pending and all(final[k]==0 for k in pending),(case,seed,initial,final)
   elif case=='quiet':assert final and all(v>0 for v in final.values()),(case,seed,final)
   else:assert all(final[k]==initial[k] for k in initial)
   assert info['road_stock']==stock and info['road_actions']==0
   rows.append(dict(case=case,seed=seed,initial_time=before_time,final_time=env.raw['time'],initial_served=initial,final_served=final,stock=stock))
finally:env.close()
(r/'task-meaning-checks.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',len(rows),'native Wait-only label checks; no reference actions queried')

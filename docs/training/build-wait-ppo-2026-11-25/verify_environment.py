from pathlib import Path
import json
import numpy as np
import city_curriculum as cc
from city_wait_decision import CityWaitDecisionEnv,SCHEDULE,NEEDS_BUILD
from prepare_city_policy import sha256
r=Path('docs/training/build-wait-ppo-2026-11-25')
old=Path('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll')
new=Path('output/wait-decision-build-02/artifacts/bin/TrafficHost/release/TrafficHost.dll')
cc.LESSONS+=('adjacent','bend','clear','obstacle')
exercises=('city','adjacent','bend','clear','obstacle',cc.SMALL_TIGHT,cc.SMALL_STOCK,cc.SMALL_OFFSET,cc.QUIET)
a=cc.CityCurriculumEnv(str(old),validation=True,allow_bridges=True,small_city_horizon=300)
b=cc.CityCurriculumEnv(str(new),validation=True,allow_bridges=True,small_city_horizon=300);transitions=0
try:
 for i,ex in enumerate(exercises):
  x,_=a.reset(options=dict(exercise=ex,scenario_seed=244003000+i));y,_=b.reset(options=dict(exercise=ex,scenario_seed=244003000+i))
  for k in range(20):
   assert a.raw==b.raw and all(np.array_equal(x[n],y[n]) for n in x)
   m=a.action_masks();assert np.array_equal(m,b.action_masks());choices=np.flatnonzero(m)
   action=int(choices[(k*17+i)%len(choices)]) if k%2==0 else 0
   x,ar,at,ac,ai=a.step(action);y,br,bt,bc,bi=b.step(action)
   assert (ar,at,ac,ai)==(br,bt,bc,bi) and a.raw==b.raw;transitions+=1
   if a.done:break
finally:a.close();b.close()
rows=[];colors=set();resets=0
for validation in (False,True):
 env=CityWaitDecisionEnv(str(new),validation=validation)
 try:
  for case in ('match','mismatch','homes','destinations'):
   for seed in range(244004000,244004128):
    obs,info=env.reset(options=dict(case=case,scenario_seed=seed,warmup_seconds=0));resets+=1
    colors.update(x['color'] for x in env.raw['buildings'])
    assert all(np.isfinite(x).all() for x in obs.values())
  for i,case in enumerate(SCHEDULE):
   for build in (False,True):
    obs,info=env.reset(options=dict(case=case,scenario_seed=244001000+i));mask=env.action_masks()
    action=int(np.flatnonzero(mask[1:])[0]+1) if build else 0
    _,reward,t,tr,end=env.step(action)
    assert t and not tr and reward==float(build==(case in NEEDS_BUILD))
    rows.append(dict(validation=validation,case=case,build=build,reward=reward,native_reward=end['native_reward'],warmup=end['warmup_seconds']))
 finally:env.close()
assert colors==set(range(5))
report=dict(production_sha256=sha256(old),diagnostic_sha256=sha256(new),ordinary_exact_transitions=transitions,ordinary_families=list(exercises),pair_reset_checks=resets,native_colors=sorted(colors),binary_native_transitions=rows,limits='Initial-state and one-step contracts; no learning or promotion. Binary task rewards are separate from native trips. Failed v1 retained.')
(r/'environment-checks.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',transitions,'ordinary transitions',resets,'pair resets',len(rows),'binary decisions')

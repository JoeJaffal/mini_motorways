import json,copy
from pathlib import Path
import numpy as np
import city_curriculum as cc
from pair_audit_env import CityPairAuditEnv,CASES
from prepare_city_policy import sha256
r=Path('docs/training/city-negative-pair-audit-2026-11-25')
old=Path('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll')
new=Path('output/pair-city-audit-build-01/artifacts/bin/TrafficHost/release/TrafficHost.dll')
cc.LESSONS+=('adjacent','bend','clear','obstacle')
exercises=('city','adjacent','bend','clear','obstacle',cc.SMALL_TIGHT,cc.SMALL_STOCK,cc.SMALL_OFFSET,cc.QUIET)
a=cc.CityCurriculumEnv(str(old),validation=True,allow_bridges=True,small_city_horizon=300)
b=cc.CityCurriculumEnv(str(new),validation=True,allow_bridges=True,small_city_horizon=300)
transitions=0
try:
 for i,ex in enumerate(exercises):
  x,_=a.reset(options=dict(exercise=ex,scenario_seed=244000000+i));y,_=b.reset(options=dict(exercise=ex,scenario_seed=244000000+i))
  for k in range(20):
   assert a.raw==b.raw and all(np.array_equal(x[n],y[n]) for n in x)
   m=a.action_masks();assert np.array_equal(m,b.action_masks())
   choices=np.flatnonzero(m);action=int(choices[(k*17+i)%len(choices)]) if k%2==0 else 0
   x,ar,at,ac,ai=a.step(action);y,br,bt,bc,bi=b.step(action)
   assert (ar,at,ac,ai)==(br,bt,bc,bi) and a.raw==b.raw
   transitions+=1
   if a.done:break
finally:a.close();b.close()
env=CityPairAuditEnv(str(new),horizon=60,observation_horizon=600,allow_bridges=True);cases=[]
try:
 for seed in range(244000100,244000104):
  saved={}
  for case in CASES:
   obs,info=env.reset(options=dict(case=case,scenario_seed=seed))
   saved[case]=(copy.deepcopy(env.raw),{k:v.copy() for k,v in obs.items()},env.action_masks().copy())
   cases.append(dict(seed=seed,case=case,stock=info['road_stock']))
  match,mismatch=saved['match'],saved['mismatch']
  assert np.array_equal(match[2],mismatch[2])
  assert any(not np.array_equal(match[1][k],mismatch[1][k]) for k in match[1])
  # Building IDs/positions/access geometry and inventory must match; only shop color changes.
  assert all(a==b or (a,b)==(1,0) for a,b in zip(match[0]['buildingColors'],mismatch[0]['buildingColors']))
  for raw in (match[0],mismatch[0]):
   raw['buildingColors']=[0 if c>=0 else c for c in raw['buildingColors']]
   for building in raw['buildings']:building['color']=0
  assert match[0]==mismatch[0]
finally:env.close()
report=dict(production_sha256=sha256(old),diagnostic_sha256=sha256(new),parity_exercises=list(exercises),exact_native_transitions=transitions,pair_fixture_checks=cases,matching_mismatched_geometry_and_masks_exact=True,current_input_distinguishes_colors=True,limits='Diagnostic host only; no learner/environment change. Smoke seeds244M are separate from audit243M and reserved236M/237M.')
(r/'host-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

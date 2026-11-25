from pathlib import Path
import json,numpy as np
from environment import Host,DIRS
from city_road_pilot import CityRoadEnv,edge_action
from prepare_city_policy import sha256
root=Path.cwd();rec=root/'docs/training/city-strategy-launch-2026-11-24';old='output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll';new='output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll'
a,b=Host('dotnet',old),Host('dotnet',new);transitions=0;seeds=[99005063,99008267,99096723,99265651,99323274,99480639,*range(164100000,164100010)]
try:
 for seed in seeds:
  x=a.call(command='reset',version='OriginalReference',scenario='LosAngeles',seed=seed);y=b.call(command='reset',version='OriginalReference',scenario='LosAngeles',seed=seed);assert x==y,(seed,'reset');rng=np.random.default_rng(seed)
  for step in range(100):
   ma=a.call(command='cityRoadMask');mb=b.call(command='cityRoadMask');assert ma==mb
   bridge=b.call(command='cityConnectionMask')['connections'];assert all(not v or bridge[i] for i,v in enumerate(ma['connections']))
   choices=np.flatnonzero(ma['connections'])
   if len(choices) and rng.random()<.4:
    index=int(rng.choice(choices));cell,d=divmod(index,4);px,py=cell%50,cell//50;dx,dy=DIRS[d];request=dict(command='cityRoad',x=px,y=py,toX=px+dx,toY=py+dy)
   else:request=dict(command='wait',horizonSeconds=600)
   x=a.call(**request);y=b.call(**request);assert x==y,(seed,step);transitions+=1
   if x['terminated']:break
finally:a.close();b.close()
assert transitions==1600
# Same discrete action encodes the bridge edge; raw native rewards remain exact.
e=CityRoadEnv(new,allow_bridges=True);route=[(23,15),(23,16),(22,16),(21,16),(20,17),(19,17),(18,17),(17,17),(16,17),(15,17)];reward=0
try:
 obs,info=e.reset(options=dict(scenario_seed=99005063));assert e.observation_space.contains(obs)
 for start,end in zip(route,route[1:]):
  action=edge_action(start,end);assert e.action_masks()[action];obs,r,terminal,truncated,info=e.step(action);reward+=r;assert not terminal and not truncated and e.observation_space.contains(obs)
 assert info['bridge_stock']==0 and info['bridge_tiles']==1 and info['road_stock']==18
 while info['seconds']<60:
  obs,r,terminal,truncated,info=e.step(0);reward+=r;assert reward==info['trips'] and not terminal
 assert info['trips']==3
finally:e.close()
# Unsupported host must fail explicitly, not silently fall back to dry roads.
e=CityRoadEnv(old,allow_bridges=True);rejected=False
try:
 e.reset(options=dict(scenario_seed=99005063))
 try:e.action_masks()
 except RuntimeError:rejected=True
finally:e.close()
assert rejected
record=dict(old_host_sha256=sha256(Path(old)),new_host_sha256=sha256(Path(new)),default_exact_transitions=transitions,default_seeds=seeds,legacy_masks_preserved=True,bridge_mode_fixed_control=info,control_native_reward=reward,old_host_explicitly_rejects_new_mode=rejected,note='Fixed manual route is an engineering test only,never a policy performance result or learner input.')
(rec/'bridge-protocol-check.json').write_text(json.dumps(record,indent=2)+'\n');print(record)

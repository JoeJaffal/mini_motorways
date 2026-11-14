"""Bounded current-rule correctness recording; no model or optimizer."""
from pathlib import Path
from collections import deque
import sys,json,time
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'training'))
import numpy as np
from environment import TrafficEnv,DIRS
out=Path(__file__).with_name('reward-fixture-v2.json')
if out.exists():raise SystemExit('Refuse to overwrite completed fixture')
starttime=time.perf_counter();env=TrafficEnv(dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),seeds=[1000],seconds=400,record_replays=True,reward_mode="connectivity")
try:
 env.reset(seed=42);free={(int(k%50),int(k//50)) for k in np.flatnonzero(env.land)};best=None
 for h,home in env.houses.items():
  dx,dy=DIRS[home['drivewayDirection']];start=(h[0]+dx,h[1]+dy);q=deque([start]);parent={start:None}
  while q:
   p=q.popleft()
   for dx,dy in DIRS[::2]:
    point=(p[0]+dx,p[1]+dy)
    if point in free and point not in parent:parent[point]=p;q.append(point)
  for shop in env.buildings:
   if shop['isHouse'] or shop['color']!=home['color']:continue
   end=tuple(shop['entrance'][k] for k in ('x','y'));dx,dy=DIRS[shop['drivewayDirection']];target=(end[0]+dx,end[1]+dy)
   if target not in parent:continue
   path=[target]
   while parent[path[-1]] is not None:path.append(parent[path[-1]])
   path=[h]+list(reversed(path))+[end]
   if best is None or len(path)<len(best):best=path
 assert best
 for a,b in zip(best,best[1:]):
  result=env._advance(dict(command='draw',x=a[0],y=a[1],toX=b[0],toY=b[1]));assert result[4]['accepted']
 assert env.connected_houses>0
 while not env.done:
  if time.perf_counter()-starttime>120:raise RuntimeError('120s wall limit')
  result=env._advance(None)
 recording=env.export_replay();assert recording['terminated'] and recording['score']>0
 recording['source']='Scripted ordinary-road correctness fixture for fidelity repairs 2026-11-08; not policy performance.'
 out.write_text(json.dumps(recording,indent=2)+'\n');print(json.dumps(dict(score=recording['score'],duration=recording['duration'],actions=len(recording['actions']),wallSeconds=time.perf_counter()-starttime)))
finally:env.close()

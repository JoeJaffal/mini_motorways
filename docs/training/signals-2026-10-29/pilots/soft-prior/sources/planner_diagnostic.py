"""Separate visible-state greedy routing baseline, NOT a learned policy.

Tests whether ordinary road construction can serve these scenarios before
attributing every failure to compute. Uses no reference command or stock grants.
"""
import argparse
import heapq
import json
from pathlib import Path
from environment import TrafficEnv,ROOT,DIRS,cell


def path_to(env,start,goal,cell_penalty=None):
    def allowed(p):
        if not env.is_visible(p):return False
        k=env.index(p)
        return env.arrays['terrain'][k]!=2 and env.arrays['buildingKinds'][k]==0 and not env.arrays['pendingRemovals'][k] and p not in env.roundabouts
    if not allowed(start) or not allowed(goal):return None
    queue=[(0,start)];cost={start:0};parent={start:None}
    while queue:
        old,p=heapq.heappop(queue)
        if old!=cost[p]:continue
        if p==goal:
            path=[p]
            while parent[path[-1]] is not None:path.append(parent[path[-1]])
            return list(reversed(path))
        for d,(dx,dy) in enumerate(DIRS):
            q=p[0]+dx,p[1]+dy
            if not allowed(q):continue
            i,j=env.index(p),env.index(q)
            water=env.arrays['terrain'][j]==1
            if dx and dy and (water or env.arrays['terrain'][i]==1):continue
            if water and env.arrays['infrastructure'][j]==0 and env.raw['inventory'][1]<=0:continue
            if dx and dy:
                x,y=(p[0],q[1]),(q[0],p[1]);cross=DIRS.index((dx,-dy))
                if env.arrays['connections'][env.index(x)]&(1<<cross):continue
            new=old+.04+(1 if env.arrays['infrastructure'][j]==0 else 0)
            if cell_penalty is not None:new+=float(cell_penalty[j])
            if new<cost.get(q,float('inf')):
                cost[q]=new;parent[q]=p;heapq.heappush(queue,(new,q))
    return None


def reachable(env,start,goal):
    seen={start};todo=[start]
    while todo:
        p=todo.pop()
        if p==goal and env.arrays['infrastructure'][env.index(p)]!=0:return True
        bits=env.arrays['connections'][env.index(p)]
        for d,(dx,dy) in enumerate(DIRS):
            q=p[0]+dx,p[1]+dy
            if bits&(1<<d) and env.is_visible(q) and q not in seen and env.arrays['buildingKinds'][env.index(q)]==0 and not env.arrays['pendingRemovals'][env.index(q)]:
                seen.add(q);todo.append(q)
    return False


def proposal(env):
    best=None;rank=None
    supplied=set(env.connectivity['suppliedDestinationIds'])
    for h,home in env.houses.items():
        d=DIRS[home['drivewayDirection']];start=h[0]+d[0],h[1]+d[1]
        for shop in env.buildings:
            if shop['isHouse'] or shop['color']!=home['color']:continue
            for entry,direction in zip(shop['entrances'],shop['entranceDirections']):
                p=cell(entry);d=DIRS[direction];goal=p[0]+d[0],p[1]+d[1]
                if reachable(env,start,goal):continue
                path=path_to(env,start,goal)
                if not path:continue
                missing=sum(env.arrays['infrastructure'][env.index(p)]==0 for p in path)
                if missing>env.raw['inventory'][0]:continue
                candidate=(int(shop['id'] in supplied),missing,len(path))
                if rank is None or candidate<rank:best=path;rank=candidate
    return best


def strokes(path):
    if len(path)==1:return [(path[0],path[0])]
    result=[];start=path[0];previous=path[0];direction=None
    for p in path[1:]:
        new=(p[0]-previous[0],p[1]-previous[1])
        if direction is not None and new!=direction:result.append((start,previous));start=previous
        direction=new;previous=p
    result.append((start,previous));return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--count',type=int,default=3)
    p.add_argument('--seed-start',type=int,default=2000);p.add_argument('--seconds',type=int,default=1200)
    p.add_argument('--host-dll',type=Path);p.add_argument('--dotnet',default=str(ROOT/'tmp/dotnet/dotnet.exe'))
    a=p.parse_args()
    if a.output.exists():p.error('Fresh output folder required')
    a.output.mkdir(parents=True);results=[]
    env=TrafficEnv(dotnet=a.dotnet,seconds=a.seconds,observation_mode='connectivity',record_replays=True,host_dll=a.host_dll)
    try:
        for seed in range(a.seed_start,a.seed_start+a.count):
            env.reset(seed=seed,options={'scenario_seed':seed});pending=[];cached=None
            while not env.done:
                offers=env.raw['upgradeChoices']
                if offers:
                    choice=max(range(len(offers)),key=lambda i:offers[i]['roads']+(offers[i]['amount'] if offers[i]['type']==0 else 0))
                    env._advance(dict(command='upgrade',choice=choice));cached=None;continue
                stamp=(env.network_version,tuple(env.raw['inventory']))
                if not pending and stamp!=cached:
                    plan=proposal(env);pending=strokes(plan) if plan else [];cached=stamp
                if pending:
                    start,end=pending.pop(0)
                    env._advance(dict(command='draw',x=start[0],y=start[1],toX=end[0],toY=end[1]))
                else:env._advance()
            info=env.info();results.append(info)
            replay=env.export_replay();replay.update(source='heuristic-diagnostic',policySchema='visible-greedy-router-v1')
            (a.output/f'seed-{seed}.json').write_text(json.dumps(replay,indent=2)+'\n')
            print(f"PLANNER DIAGNOSTIC | {seed} | {info['trips']} trips | {info['seconds']:.1f}s",flush=True)
        (a.output/'results.json').write_text(json.dumps(dict(protocol='Visible-state greedy routing, not learned; finite normal stock, upgrades, no debug actions',cap=a.seconds,results=results),indent=2)+'\n')
    finally:env.close()


if __name__=='__main__':main()

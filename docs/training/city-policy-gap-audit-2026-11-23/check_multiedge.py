"""Find and verify affordable short routes for archived unserved city targets."""

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from heapq import heappop, heappush
from itertools import permutations
import json
from pathlib import Path

from audit_city_service import tile
from city_road_pilot import CityRoadEnv
from export_city_replays import action_endpoints
from prepare_city_policy import sha256
from visible_observation import WIDTH


def shortest_candidate(raw, mask, target):
    graph = defaultdict(dict)
    for i,bits in enumerate(raw['connections']):
        for direction in range(4):
            if bits & (1 << direction):
                a,b = action_endpoints(1 + 4*i + direction)
                graph[a][b] = graph[b][a] = (0,0)
    kinds = raw['buildingKinds']
    for slot,legal in enumerate(mask[1:],start=1):
        if legal:
            a,b = action_endpoints(slot)
            paid = int(not kinds[a[1]*WIDTH+a[0]] and not kinds[b[1]*WIDTH+b[0]])
            graph[a][b] = graph[b][a] = (paid,slot)
    starts = [tile(b['cell']) for b in raw['buildings'] if b['isHouse'] and b['color']==target['color']]
    goals = set(map(tile,target['entrances'] or [target['entrance']]))
    heap = [(0,0,home,()) for home in starts]
    visited = set()
    while heap:
        cost,count,cell,edits = heappop(heap)
        if cell in visited:
            continue
        visited.add(cell)
        if cell in goals:
            return cost,edits
        for neighbor,(units,action) in graph[cell].items():
            if neighbor not in visited and cost+units<=min(3,raw['inventory'][0]) and count+bool(action)<=4:
                heappush(heap,(cost+units,count+bool(action),neighbor,edits+(action,) if action else edits))
    return None


def replay_prefix(env, game, count):
    env.reset(options={'scenario_seed':game['seed']})
    for action in game['actions'][:count]:
        env.step(action)


def verify(env, game, target_id, decision, time, edits):
    for order in permutations(edits):
        replay_prefix(env, game, decision)
        if env.raw['time']!=time:
            raise RuntimeError('Original prefix did not reproduce')
        start=env.raw['inventory'][0]
        for action in order:
            if not env.action_masks()[action]:
                break
            env.step(action)
        else:
            paid=start-env.raw['inventory'][0]
            while not env.done and env.raw['time']<time+90:
                env.step(0)
                target=next(b for b in env.raw['buildings'] if b['id']==target_id)
                if target['served']:
                    return dict(actions=order, cost=paid, delivery=env.raw['time'])
            # Every accepted order ends with the same roads at the same native time.
            return dict(actions=order, cost=paid, delivery=None)
    return None


def inspect(dll, game, original):
    env=CityRoadEnv(dll)
    try:
        env.reset(options={'scenario_seed':game['seed']})
        targets={t['id']:t for t in original['targets'] if t['id'] in game['focus']}
        candidates=defaultdict(dict)
        last=None
        for decision,action in enumerate(game['actions']):
            info=env.info()
            time,stock=info['seconds'],info['road_stock']
            sample=(int(time//5),info['road_actions'],stock)
            if stock and sample!=last and time<=original['seconds']-90:
                for b in env.raw['buildings']:
                    target=targets.get(b['id'])
                    if target is not None and time>=target['first_seen'] and len(candidates[b['id']])<5:
                        candidate=shortest_candidate(env.raw,env.action_masks(),b)
                        if candidate is not None and len(candidate[1])>1:
                            cost,edits=candidate
                            candidates[b['id']].setdefault(tuple(sorted(edits)),(decision,time,stock,cost,edits))
            last=sample
            env.step(action)
        if any(env.info()[k]!=original[k] for k in env.info()):
            raise RuntimeError('Original city result did not reproduce')
        result=[]
        for target,paths in candidates.items():
            tested=[]
            for decision,time,stock,cost,edits in paths.values():
                observed=verify(env,game,target,decision,time,edits)
                tested.append(dict(decision=decision, second=time, stock=stock, estimated_cost=cost,
                                   estimated_edits=edits, native=observed))
                if observed and observed['delivery'] is not None:
                    break
            result.append(dict(target_id=target,tested=tested))
        return dict(seed=game['seed'], targets=game['focus'], result=result)
    finally:
        env.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--witness',type=Path,required=True)
    parser.add_argument('--games',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    witness=json.loads(args.witness.read_text())
    rows=[json.loads(s) for s in args.games.read_text().splitlines()]
    final_model=max(row['model'] for row in rows)
    originals={r['seed']:r for r in rows if r['model']==final_model}
    if sha256(args.dll)!=witness['host_sha256']:
        raise RuntimeError('Wrong native host')
    with ProcessPoolExecutor(max_workers=6) as pool:
        tasks=[pool.submit(inspect,args.dll,g,originals[g['seed']]) for g in witness['games']]
        result=[task.result() for task in tasks]
    with args.output.open('x') as stream:
        json.dump(dict(host_sha256=witness['host_sha256'], games=result),stream,indent=2)
        stream.write('\n')


if __name__=='__main__':
    main()

"""Offline bend feasibility check. Its route enumeration is never imported by PPO."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np

from construction_practice import EDGE_END, ConstructionPractice, endpoints, tile
from environment import DIRS
from visible_observation import WIDTH


def component(env, initial):
    reached = {initial}
    stack = [initial]
    while stack:
        x,y = stack.pop()
        mask = env.raw['connections'][y*WIDTH+x]
        for d,(dx,dy) in enumerate(DIRS):
            if mask & (1 << d):
                nxt = (x+dx,y+dy)
                if nxt not in reached:
                    reached.add(nxt)
                    stack.append(nxt)
    return reached


def solution_candidates(env):
    origins = component(env, tile(env.house['cell']))
    targets = component(env, tile(env.shop['entrance']))
    candidates = defaultdict(list)
    for action in np.flatnonzero(env.legal[:EDGE_END]):
        a,b = [env.world(p) for p in endpoints(action)]
        candidates[a].append((b,int(action)))
        candidates[b].append((a,int(action)))

    def grow(current, visited, path):
        if current in targets:
            yield tuple(path)
            return
        left = env.edit_limit-len(path)
        distance = min(max(abs(current[0]-x), abs(current[1]-y)) for x,y in targets)
        if left < distance:
            return
        for nxt,action in candidates[current]:
            if nxt not in visited and nxt not in origins:
                yield from grow(nxt, visited|{nxt}, path+[action])

    seen = set()
    for point in sorted(origins):
        for path in grow(point,{point},[]):
            signature = frozenset(path)
            if signature not in seen:
                seen.add(signature)
                yield path


def verify(env, split, seed):
    env.reset('bend',split,seed)
    reference = env.reference()
    plans = [tuple(reference)]
    alternate = next((plan for plan in solution_candidates(env) if set(plan)!=set(reference)), None)
    if alternate is not None:
        plans.append(alternate)
    outcomes = []
    for sequence in plans:
        env.reset('bend',split,seed)
        played = []
        for action in sequence:
            finished = env.step(action)
            played.append(action)
            if finished:
                break
            env.mask()
        if not env.connected():
            raise RuntimeError(f'{split} layout {seed} did not connect via {sequence}')
        trips, seconds = env.deliveries()
        if trips<3 or seconds!=180:
            raise RuntimeError(f'{split} layout {seed} did not deliver via {sequence}')
        outcomes.append(dict(actions=played,trips=trips))
    if len(outcomes)>1 and set(outcomes[0]['actions'])==set(outcomes[1]['actions']):
        raise RuntimeError(f'{split} layout {seed} has no distinct alternative')
    return dict(split=split,seed=seed,edit_limit=env.edit_limit,routes=outcomes)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    with Path(args.output).open('x') as out:
        env=ConstructionPractice(args.dll)
        try:
            rows=[]
            for split,base in [('train',64000),('validation',32000)]:
                results=[verify(env,split,seed) for seed in range(base,base+100)]
                print(split,sum(len(row['routes'])==2 for row in results),'/100 with alternatives',flush=True)
                rows.extend(results)
        finally:
            env.close()
        json.dump(rows,out,indent=2)
        out.write('\n')

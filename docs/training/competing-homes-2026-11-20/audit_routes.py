"""Replay archived actions and bound the paid stock still needed at each move."""

import argparse
from collections import Counter, deque
from pathlib import Path

import json

from bend_ppo import digest, write
from construction_practice import advance, endpoints, tile
from environment import DIRS
from evaluate_triad_ppo import TriadEnvironment
from visible_observation import WIDTH


def optimistic_cost(world):
    """Lower bound. Keep parcel approaches, but ignore crossings and edit caps."""
    raw = world.raw
    start, goal = tile(world.match['cell']), tile(world.shop['entrance'])
    approaches = {
        tile(b['cell'] if b['isHouse'] else b['entrance']): b['drivewayDirection']
        for b in raw['buildings']
    }
    distances = {start: 0}
    queue = deque([(start, 0)])
    while queue:
        point, cost = queue.popleft()
        if distances[point] != cost:
            continue
        if point == goal:
            return cost
        index = point[1] * WIDTH + point[0]
        for d in range(8):
            other = advance(point, d)
            if not all(0 <= p < len(world.cells) for p in world.local(other)):
                continue
            k = other[1] * WIDTH + other[0]
            if raw['terrain'][k] or raw['buildingKinds'][k] and other not in approaches:
                continue
            if point in approaches and approaches[point] != d:
                continue
            if other in approaches and approaches[other] != (d + 4) % 8:
                continue
            free = point in approaches or other in approaches or raw['connections'][index] & (1 << d)
            new_cost = cost + int(not free)
            if new_cost >= distances.get(other, float('inf')):
                continue
            distances[other] = new_cost
            (queue.appendleft if free else queue.append)((other, new_cost))
    raise RuntimeError('The optimistic graph has no possible connection')


def replay(env, stage, row):
    env.reset(options=dict(stage=stage, split='validation', layout_seed=row['seed']))
    world = env.env
    cost = optimistic_cost(world)
    stock = world.inventory
    heading = DIRS[world.shop['drivewayDirection']]
    buildings = [dict(role='home' if b['isHouse'] else 'destination', color=b['color'],
                      location=tile(b['cell']), access=tile(b['entrance']), width=b['width'], height=b['height'])
                 for b in world.raw['buildings']]
    if cost > stock:
        raise RuntimeError('Fixture starts over its stock budget')
    trace = []
    first = None
    for step, action in enumerate(row['actions'], 1):
        cells = [world.world(p) for p in endpoints(action)] if action else []
        _, _, done, truncated, info = env.step(action)
        if truncated:
            raise RuntimeError('Unexpected truncation')
        remaining = world.raw['inventory'][0]
        lower_bound = optimistic_cost(world)
        if first is None and lower_bound > remaining:
            first = step
        trace.append(dict(step=step, action=action, cells=cells, paid=stock-remaining,
                          bound_before=cost, bound_after=lower_bound, remaining=remaining))
        cost, stock = lower_bound, remaining
    if not done or bool(info['connected']) != row['connected']:
        raise RuntimeError('Native replay diverged from the frozen archive')
    return dict(seed=row['seed'], connected=info['connected'], first_deficit=first,
                destination_heading=heading, buildings=buildings, trace=trace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.source.read_text())
    if digest(args.dll) != report['native_sha256']:
        raise RuntimeError('Replay requires the exact original native host')
    env = TriadEnvironment(args.dll)
    try:
        arms = report['results']
        if 'results' in arms:
            arms = arms['results']
        results = {key: [replay(env, key.split('/')[0], row) for row in rows]
                   for key, rows in arms.items()}
    finally:
        env.close()
    summary = {key: dict(Counter(str(r['first_deficit']) for r in rows)) for key, rows in results.items()}
    parallel = {}
    for key, rows in results.items():
        invalid = [r for r in rows if r['first_deficit']]
        edges = [(r['trace'][r['first_deficit']-1]['cells'], r['destination_heading']) for r in invalid]
        parallel[key] = sum(
            (b[0]-a[0])*heading[1] == (b[1]-a[1])*heading[0]
            for (a, b), heading in edges
        )
    print(summary)
    print('First deficient edge parallel to destination axis:', parallel)
    write(args.output, dict(source_sha256=digest(args.source), native_sha256=digest(args.dll),
                            first_deficit=summary, parallel_first_deficit=parallel, results=results))


if __name__ == '__main__':
    main()

"""Measure native new-destination service and the cost of available road paths."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import heapq
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from audit_city_roads import assigned_edges
from city_road_pilot import CityRoadEnv
from export_city_replays import action_endpoints
from prepare_city_policy import masked_probs, sha256
from visible_observation import WIDTH


def tile(point):
    return point['x'], point['y']


def native_edge_graph(raw, mask):
    """Combine built links and individually legal edges as a feasibility estimate."""
    graph = defaultdict(list)
    kinds = raw['buildingKinds']
    for i, bits in enumerate(raw['connections']):
        for direction in range(4):
            if bits & (1 << direction):
                a, b = action_endpoints(1 + 4*i + direction)
                graph[a].append((b, 0))
                graph[b].append((a, 0))
    for slot in np.flatnonzero(mask[1:]):
        a, b = action_endpoints(1+int(slot))
        cost = int(not kinds[a[1]*WIDTH+a[0]] and not kinds[b[1]*WIDTH+b[0]])
        graph[a].append((b, cost))
        graph[b].append((a, cost))
    return graph


def estimated_cost(graph, homes, entrances):
    if not homes:
        return None
    distances = {cell: 0 for cell in homes}
    queue = [(0, cell) for cell in homes]
    heapq.heapify(queue)
    while queue:
        cost, cell = heapq.heappop(queue)
        if cost != distances[cell]:
            continue
        if cell in entrances:
            return cost
        for neighbor, units in graph[cell]:
            score = cost+units
            if score < distances.get(neighbor, np.inf):
                distances[neighbor] = score
                heapq.heappush(queue, (score, neighbor))
    return None


def inspect_destinations(graph, buildings, time, stock, targets):
    homes = defaultdict(set)
    for building in buildings:
        if building['isHouse']:
            homes[building['color']].add(tile(building['cell']))
    for building in buildings:
        if building['id'] not in targets or building['served']:
            continue
        row = targets[building['id']]
        sources = homes[building['color']]
        if sources and row['first_matching_home'] is None:
            row['first_matching_home'] = time
        entrances = {tile(point) for point in building['entrances']}
        cost = estimated_cost(graph, sources, entrances)
        if time == row['first_seen']:
            row['arrival_cost'] = cost
        if cost is not None and cost <= stock and row['first_affordable_path'] is None:
            row.update(first_affordable_path=time, affordable_cost=cost, stock_at_opportunity=stock)


def trace(dll, model, seed, action_seed, *, estimate=True, horizon=600, skip_forced_inference=True, allow_bridges=False):
    env = CityRoadEnv(dll,horizon=horizon,observation_horizon=600,allow_bridges=allow_bridges)
    try:
        obs, info = env.reset(options={'scenario_seed': seed})
        rng = np.random.default_rng(action_seed)
        known = {b['id'] for b in env.raw['buildings']}
        targets = {}
        paid_edges, used_edges = Counter(), set()
        previous = None
        while not env.done:
            mask = env.action_masks()
            time, stock = info['seconds'], info['road_stock']
            buildings = env.raw['buildings']
            spawned = False
            for building in buildings:
                key = building['id']
                if key in known:
                    continue
                known.add(key)
                spawned = True
                if not building['isHouse'] and info['trips']:
                    targets[key] = dict(id=key, color=building['color'], first_seen=time,
                                        arrival_stock=stock, arrival_paid=sum(paid_edges.values()),
                                        first_matching_home=None, arrival_cost=None,
                                        first_affordable_path=None, first_delivery=None, served=0)
            for building in buildings:
                if building['id'] in targets and building['served']:
                    row = targets[building['id']]
                    if row['first_delivery'] is None:
                        row['first_delivery'] = time
                        row['paid_after_arrival_to_first_delivery'] = sum(paid_edges.values())-row['arrival_paid']
                    row['served'] = building['served']
            snapshot = (int(time//5), info['road_actions'])
            if estimate and targets and (spawned or snapshot != previous) and any(not t['served'] for t in targets.values()):
                inspect_destinations(native_edge_graph(env.raw, mask), buildings, time, stock, targets)
            previous = snapshot
            # A singleton legal mask fixes the categorical distribution exactly.
            # Still sample it below to preserve the action RNG stream, and still
            # step/encode every native observation for the traffic history.
            p = (mask.astype(np.float64) if skip_forced_inference and mask.sum()==1
                 else masked_probs(model, obs, mask).astype(np.float64))
            if not np.isfinite(p).all() or p[~mask].any():
                raise RuntimeError('Invalid policy mask or probability')
            action = int(rng.choice(len(p), p=p/p.sum()))
            obs, _, terminal, truncated, info = env.step(action)
            if action and stock > info['road_stock']:
                paid_edges[tuple(sorted(action_endpoints(action)))] += stock-info['road_stock']
            used_edges.update(assigned_edges(env.raw))
        for building in env.raw['buildings']:
            if building['id'] in targets and building['served']:
                row = targets[building['id']]
                row['served'] = building['served']
                if row['first_delivery'] is None:
                    row['first_delivery'] = info['seconds']
                    row['paid_after_arrival_to_first_delivery'] = sum(paid_edges.values())-row['arrival_paid']
        return dict(info, targets=list(targets.values()), action_seed=action_seed,
                    native_game_over=terminal, truncated=truncated,
                    paid_units=sum(paid_edges.values()),
                    outside_routes=sum(cost for edge, cost in paid_edges.items() if edge not in used_edges))
    finally:
        env.close()


def worker(dll, checkpoint, jobs):
    torch.set_num_threads(1)
    model = MaskablePPO.load(checkpoint, device='cpu')
    results = []
    for seed, action_seed in jobs:
        row = trace(dll, model, seed, action_seed)
        results.append(row)
        print(f'CITY | {seed} | {row["trips"]} deliveries | {len(row["targets"])} new targets', flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll','checkpoint','output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    args = parser.parse_args()
    rng = np.random.default_rng(436246)
    jobs = [(96_000_000+int(seed), int(rng.integers(100_000_000,2**31)))
            for seed in rng.choice(100000, 24, replace=False)]
    args.output.mkdir(parents=True, exist_ok=False)
    with ProcessPoolExecutor(max_workers=8, mp_context=mp.get_context('spawn')) as pool:
        tasks = [pool.submit(worker, args.dll, args.checkpoint, jobs[i::8]) for i in range(8)]
        rows = [row for task in tasks for row in task.result()]
    if len({row['seed'] for row in rows}) != len(jobs):
        raise RuntimeError('Incomplete city audit')
    summary = dict(games=rows, host_sha256=sha256(args.dll), checkpoint_sha256=sha256(args.checkpoint))
    (args.output/'audit.json').write_text(json.dumps(summary, indent=2)+'\n')


if __name__ == '__main__':
    main()

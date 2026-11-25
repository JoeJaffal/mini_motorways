"""Audit road spending and test a frozen change to Build-or-Wait odds."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import CityRoadEnv
from diagnose_city_policy import routes
from export_city_replays import action_endpoints
from prepare_city_policy import masked_probs, sha256
from train_city_opening_pilot import opening_has_route


def assigned_edges(raw):
    for car in raw['vehicles']:
        if car['stage'] == 'Home':
            continue
        for key in ('route', 'returnRoute'):
            cells = [(point['x'], point['y']) for point in car[key]]
            for a, b in zip(cells, cells[1:]):
                if a != b:
                    yield tuple(sorted((a, b)))


def audit(env, seed, action_seed, *, model=None, actions=None, wait_odds=1):
    obs, info = env.reset(options={'scenario_seed': seed})
    open_mask = opening_has_route(env.raw, env.action_masks())
    rng = np.random.default_rng(action_seed)
    spent, dispatched = Counter(), set()
    first_route = first_delivery = first_stockout = None
    before_route = before_delivery = longest_build_streak = build_streak = 0
    initial_wait_probability = None
    for decision in range(10000):
        stock = info['road_stock']
        buildings = info['buildings']
        mask = env.action_masks()
        if actions is None:
            p = masked_probs(model, obs, mask).astype(np.float64)
            p[0] *= wait_odds
            p /= p.sum()
            if decision == 0:
                initial_wait_probability = float(p[0])
            action = int(rng.choice(len(p), p=p))
        else:
            action = actions[decision]
        if not mask[action]:
            raise RuntimeError(f'Illegal action in seed {seed} at decision {decision}')
        obs, reward, terminal, truncated, info = env.step(action)
        now = info['seconds']
        if action:
            build_streak += 1
            longest_build_streak = max(longest_build_streak, build_streak)
            units = stock - info['road_stock']
            if units < 0:
                raise RuntimeError('Unexpected road stock increase during a draw')
            if units:
                spent[tuple(sorted(action_endpoints(action)))] += units
                if first_route is None:
                    before_route += units
                if first_delivery is None:
                    before_delivery += units
        else:
            build_streak = 0
        if first_stockout is None and info['road_stock'] == 0:
            first_stockout = now
        if first_route is None and (action or buildings != info['buildings']):
            if routes(env)['connectedHouseIds']:
                first_route = now
        if reward and first_delivery is None:
            first_delivery = now
        dispatched.update(assigned_edges(env.raw))
        if terminal or truncated:
            if actions is not None and decision + 1 != len(actions):
                raise RuntimeError(f'Archived replay length differs for seed {seed}')
            break
    else:
        raise RuntimeError(f'No game ending for seed {seed}')
    return dict(**info, action_seed=action_seed, open_mask=open_mask, wait_odds=wait_odds,
                initial_wait_probability=initial_wait_probability, first_route=first_route,
                first_delivery=first_delivery, first_stockout=first_stockout,
                paid_road_units=sum(spent.values()), paid_units_through_first_route=before_route,
                paid_units_before_first_delivery=before_delivery,
                paid_units_in_any_observed_trip_route=sum(units for edge, units in spent.items() if edge in dispatched),
                paid_units_outside_observed_trip_routes=sum(units for edge, units in spent.items() if edge not in dispatched),
                longest_build_streak=longest_build_streak, native_game_over=terminal, truncated=truncated)


def fresh_suite(dll):
    env = CityRoadEnv(dll)
    rng = np.random.default_rng(313881)
    groups = {True: 0, False: 0}
    jobs = []
    try:
        for value in rng.choice(100000, 400, replace=False):
            seed = int(value) + 83_100_000
            env.reset(options={'scenario_seed': seed})
            open_mask = opening_has_route(env.raw, env.action_masks())
            if groups[open_mask] == 8:
                continue
            groups[open_mask] += 1
            jobs.append(dict(seed=seed, action_seed=int(rng.integers(100_000_000, 2**31)),
                             open_mask=open_mask))
            if len(jobs) == 16:
                return jobs
    finally:
        env.close()
    raise RuntimeError('Could not make the fresh audit suite')


def compare_worker(dll, checkpoint, jobs):
    torch.set_num_threads(1)
    model = MaskablePPO.load(checkpoint, device='cpu')
    env = CityRoadEnv(dll, include_connectivity=True)
    try:
        rows = []
        for job in jobs:
            pair = [audit(env, job['seed'], job['action_seed'], model=model, wait_odds=odds)
                    for odds in (1, 4)]
            if any(row['open_mask'] != job['open_mask'] for row in pair):
                raise RuntimeError('Opening class changed')
            rows.extend(pair)
            print(f'{job["seed"]} | deliveries {[row["trips"] for row in pair]}', flush=True)
        return rows
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll', 'checkpoint', 'selection', 'output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text())
    identities = dict(checkpoint_sha256=sha256(args.checkpoint), host_sha256=sha256(args.dll))
    if any(selection[key] != value for key, value in identities.items()):
        raise RuntimeError('Use the checkpoint and host recorded in the replays')
    args.output.mkdir(parents=True, exist_ok=False)
    env = CityRoadEnv(args.dll, include_connectivity=True)
    traces = {}
    try:
        for label, trace in selection['traces'].items():
            expected = trace['episode']
            result = audit(env, expected['seed'], expected['action_seed'], actions=trace['actions'])
            if any(result[key] != expected[key] for key in
                   ('trips', 'seconds', 'road_actions', 'wait_actions', 'road_stock', 'native_game_over', 'truncated')):
                raise RuntimeError(f'Archived episode {label} did not reproduce')
            traces[label] = result
            print(f'REPLAY {label} | {result["trips"]} deliveries | {result["paid_road_units"]} units', flush=True)
    finally:
        env.close()
    (args.output/'replays.json').write_text(json.dumps(traces, indent=2)+'\n')
    jobs = fresh_suite(args.dll)
    (args.output/'suite.json').write_text(json.dumps(jobs, indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=8, mp_context=mp.get_context('spawn')) as pool:
        futures = [pool.submit(compare_worker, args.dll, args.checkpoint, jobs[i::8]) for i in range(8)]
        rows = [row for future in futures for row in future.result()]
    if len(rows) != len({(r['seed'],r['wait_odds']) for r in rows}) or len(rows) != 2 * len(jobs):
        raise RuntimeError('Incomplete matched comparison')
    rows.sort(key=lambda r:(r['seed'], r['wait_odds']))
    (args.output/'comparison.json').write_text(json.dumps(rows, indent=2)+'\n')
    (args.output/'identity.json').write_text(json.dumps(identities, indent=2)+'\n')


if __name__ == '__main__':
    main()

"""Trace native route availability and delivery stalls in frozen city games."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs, sha256


def traffic(raw):
    cars = [car for car in raw['vehicles'] if car['visible']]
    return {
        'visible_vehicles': len(cars),
        'waiting_ge_10s': sum(car['waiting'] >= 10 for car in cars),
        'max_vehicle_wait_seconds': max((car['waiting'] for car in cars), default=0),
    }


def routes(env):
    result = env.host.call(command='observe')
    if result['observation']['time'] != env.raw['time']:
        raise RuntimeError('Connectivity query changed the simulation clock')
    return result['usefulConnectivity']


def play(env, model, job):
    seed, action_seed = job['seed'], job['action_seed']
    rng = np.random.default_rng(action_seed)
    obs, info = env.reset(options={'scenario_seed': seed})
    first_route = first_stockout = first_score = None
    checkpoints, deliveries, road_edits = [], [], []
    prior_time, reward_sum = -1, 0
    previous_buildings = 0
    peak_waiting = 0
    while not env.done:
        mask = env.action_masks()
        p = masked_probs(model, obs, mask).astype(np.float64)
        if not np.isfinite(p).all() or p[~mask].any():
            raise RuntimeError('Invalid native masked probabilities')
        action = int(rng.choice(len(p), p=p / p.sum()))
        before = info['seconds']
        obs, reward, terminal, truncated, info = env.step(action)
        now = info['seconds']
        if action and job['cohort'] == 'opening':
            road_edits.append([now, action])
        if info['road_stock'] == 0 and first_stockout is None:
            first_stockout = now
        if reward:
            deliveries.append([now, int(reward)])
            if first_score is None:
                first_score = now
        reward_sum += reward
        if first_route is None and (action or len(env.raw['buildings']) != previous_buildings):
            if routes(env)['connectedHouseIds']:
                first_route = now
        previous_buildings = len(env.raw['buildings'])
        congestion = traffic(env.raw)
        peak_waiting = max(peak_waiting, congestion['waiting_ge_10s'])
        crossed_minute = int(now // 60) > int(prior_time // 60)
        if crossed_minute or env.done:
            checkpoints.append(dict(seconds=now, score=info['trips'], stock=info['road_stock'],
                                    road_actions=info['road_actions'], buildings=info['buildings'],
                                    **routes(env), **congestion))
        if before > now:
            raise RuntimeError('Native clock went backwards')
        prior_time = now
    if reward_sum != info['trips'] or env.action_masks().any():
        raise RuntimeError('Frozen evaluation disagreed with the native score or terminal mask')
    final_routes = checkpoints[-1]['suppliedDestinationIds']
    worst = max((b for b in env.raw['buildings'] if not b['isHouse']),
                key=lambda b: (b['overcrowdedFor'], b['demand']))
    return dict(
        **job, seconds=info['seconds'], trips=info['trips'], road_stock=info['road_stock'],
        buildings=info['buildings'], roads=info['road_actions'], native_game_over=terminal,
        truncated=truncated, first_route=first_route, first_stockout=first_stockout,
        first_score=first_score, last_score=deliveries[-1][0] if deliveries else None,
        score_by_600=sum(n for t, n in deliveries if t <= 600 + 1e-9),
        peak_vehicles_waiting_ge_10s=peak_waiting,
        worst_destination={**{k: worst[k] for k in ('id', 'color', 'demand', 'reserved', 'overcrowdedFor')},
                           'supplied': worst['id'] in final_routes},
        samples=checkpoints, road_edits=road_edits,
    )


def shard(dll, checkpoint, jobs):
    torch.set_num_threads(1)
    model = MaskablePPO.load(checkpoint, device='cpu')
    envs = {}
    try:
        results = []
        for job in jobs:
            horizon = job['horizon']
            if horizon not in envs:
                envs[horizon] = CityRoadEnv(dll, horizon=horizon, observation_horizon=600,
                                           include_connectivity=True)
            result = play(envs[horizon], model, job)
            results.append(result)
            print(f'{job["cohort"]} | {job["seed"]} / {job["action_seed"]} | '
                  f'{result["trips"]} trips | {result["seconds"]:.2f}s', flush=True)
        return results
    finally:
        for env in envs.values():
            env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    suite = json.loads(args.suite.read_text())
    jobs = suite['jobs']
    if not 1 <= args.workers <= len(jobs):
        parser.error('Use at least one worker and no more than the number of jobs')
    identity = sha256(args.checkpoint)
    args.output.mkdir(parents=True, exist_ok=False)
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context('spawn')) as pool:
        partitions = [jobs[i::args.workers] for i in range(args.workers)]
        futures = [pool.submit(shard, args.dll, args.checkpoint, part) for part in partitions]
        results = [row for future in futures for row in future.result()]
    results.sort(key=lambda row: row['index'])
    if [row['index'] for row in results] != list(range(len(jobs))) or sha256(args.checkpoint) != identity:
        raise RuntimeError('Incomplete trial set or changed checkpoint')
    (args.output/'games.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in results))
    (args.output/'identity.json').write_text(json.dumps(dict(
        checkpoint=str(args.checkpoint), checkpoint_sha256=identity, suite_sha256=sha256(args.suite),
        dll=str(args.dll), host_sha256=sha256(args.dll), games=len(results),
    ), indent=2) + '\n')


if __name__ == '__main__':
    main()

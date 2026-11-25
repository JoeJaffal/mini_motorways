"""Evaluate the exact city road actors in existing native demand and congestion fixtures."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import edge_action
from construction_practice import endpoints
from prepare_city_policy import masked_probs, sha256
from score_wait_ppo import native_build_or_wait
from traffic_practice import TrafficPractice, visible_traffic
from visible_observation import CELLS, VisibleObservation

CASES = (
    ('traffic-priority', 76530, 0, 100, ('upper', 'lower')),
    ('traffic-priority-swap', 76530, 0, 100, ('upper', 'lower')),
    ('traffic-junction-low-live', 78930, 36, 120, ('feeder', 'separate-exit')),
    ('traffic-junction-high-live', 78930, 36, 120, ('feeder', 'separate-exit')),
)


def play(practice, stage, seed, warm_seconds, horizon, model, control):
    practice.start(stage, 'validation', seed)
    encoder = VisibleObservation()
    obs = encoder.encode(practice.raw, horizon=600)
    for _ in range(warm_seconds):
        practice.mask()
        native_build_or_wait(practice, 0, 20)
        obs = encoder.encode(practice.raw, horizon=600)
    if practice.raw['time'] != warm_seconds:
        raise RuntimeError('Traffic fixture ended before the first decision')
    controls = practice.controls()
    shops = [b for b in practice.raw['buildings'] if not b['isHouse']]
    urgent = max(shops, key=lambda b: b['demand'])['id']
    initial = {b['id']: b['served'] for b in shops}
    first = None
    first_probs = None
    rng = np.random.default_rng(seed + 147521)
    queues = []
    for decision in range(200):
        legal = practice.mask()
        local = np.flatnonzero(legal)
        global_slots = np.array([0, *(edge_action(*(practice.world(cell) for cell in endpoints(a))) for a in local[1:])])
        mask = np.zeros(1+4*CELLS, dtype=bool)
        mask[global_slots] = True
        if model is None:
            action = controls[control] if decision == 0 else 0
        else:
            probs = masked_probs(model, obs, mask).astype(np.float64)[global_slots]
            probs /= probs.sum()
            if first_probs is None:
                by_local = dict(zip(local.tolist(), probs.tolist()))
                first_probs = {'wait': by_local[0], **{key:by_local.get(slot,0.0) for key,slot in controls.items()}}
            action = int(rng.choice(local, p=probs))
        outcome = native_build_or_wait(practice, action, 20)
        if action and first is None:
            first = next((key for key,slot in controls.items() if slot==action), 'other road')
        if action == 0:
            queues.append(sum(car['speed'] < .22 for car in visible_traffic(practice.raw)))
        if outcome['terminated'] or practice.raw['time'] >= horizon:
            served={b['id']: b['served']-initial[b['id']] for b in practice.raw['buildings'] if b['id'] in initial}
            return dict(first_road=first, first_probability=first_probs, total_deliveries=sum(served.values()),
                        urgent_deliveries=served[urgent], served=served,
                        mean_stopped_cars=float(np.mean(queues)), ended_at=practice.raw['time'],
                        native_game_over=outcome['terminated'])
        obs = encoder.encode(practice.raw, horizon=600)
    raise RuntimeError('Unexpected traffic decision cap')


def worker(dll, paths, job):
    torch.set_num_threads(1)
    stage, seed, warm, horizon, controls = job
    practice = TrafficPractice(dll)
    try:
        models = [MaskablePPO.load(path, device='cpu') for path in paths]
        results = {str(i): play(practice, stage, seed, warm, horizon, model, None) for i,model in enumerate(models)}
        for control in controls:
            results[control] = play(practice, stage, seed, warm, horizon, None, control)
        return dict(stage=stage, seed=seed, results=results)
    finally:
        practice.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--checkpoints', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=6)
    args = parser.parse_args()
    hashes = {str(path): sha256(path) for path in args.checkpoints}
    host_hash = sha256(args.dll)
    jobs = [(stage,seed,warm,horizon,controls) for stage, first, warm, horizon, controls in CASES
            for seed in range(first,first+args.count)]
    with ProcessPoolExecutor(max_workers=6, mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks = [pool.submit(worker,args.dll,args.checkpoints,job) for job in jobs]
        rows = [task.result() for task in tasks]
    if any(sha256(Path(path))!=value for path,value in hashes.items()) or sha256(args.dll)!=host_hash:
        raise RuntimeError('Frozen fixtures or checkpoints changed')
    with args.output.open('x') as stream:
        json.dump(dict(models=list(hashes), checkpoints_sha256=hashes, host_sha256=host_hash, games=rows),stream,indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()

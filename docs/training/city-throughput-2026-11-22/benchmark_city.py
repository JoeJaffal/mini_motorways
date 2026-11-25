"""Measure native city collection through SB3 subprocesses without learning."""

import argparse
from functools import partial
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from stable_baselines3.common.vec_env import SubprocVecEnv

from city_road_pilot import CityRoadEnv


def available_mib():
    with Path('/proc/meminfo').open() as stream:
        return next(int(line.split()[1]) / 1024 for line in stream if line.startswith('MemAvailable:'))


def trial(dll, workers, seconds, seed):
    available_before = available_mib()
    rng = np.random.default_rng(seed)
    env = SubprocVecEnv([partial(CityRoadEnv, dll) for _ in range(workers)],
                       start_method='forkserver')
    masks_time = 0.
    steps_time = 0.
    batches = 0
    endings = 0
    edits = 0
    try:
        env.seed(seed)
        env.reset()
        empty = np.zeros(workers, dtype=np.int64)
        for _ in range(4):
            env.env_method('action_masks')
            env.step(empty)
        start = perf_counter()
        minimum_available = available_mib()
        next_sample = start + 1
        while batches < 8 or perf_counter() - start < seconds:
            now = perf_counter()
            if now >= next_sample:
                minimum_available = min(minimum_available, available_mib())
                next_sample = now + 1
            tick = perf_counter()
            masks = env.env_method('action_masks')
            masks_time += perf_counter() - tick
            actions = empty.copy()
            if batches % 12 == 0:
                for i, mask in enumerate(masks):
                    legal = np.flatnonzero(mask[1:]) + 1
                    if len(legal):
                        actions[i] = rng.choice(legal)
            tick = perf_counter()
            _, _, finished, _ = env.step(actions)
            steps_time += perf_counter() - tick
            edits += int(np.count_nonzero(actions))
            endings += int(np.count_nonzero(finished))
            batches += 1
        elapsed = perf_counter() - start
    finally:
        env.close()
    return dict(workers=workers, seed=seed, seconds=elapsed, batches=batches,
                decisions=batches*workers, decisions_per_second=batches*workers/elapsed,
                mask_seconds=masks_time, step_seconds=steps_time, edits=edits, endings=endings,
                available_before_mib=available_before, minimum_available_mib=minimum_available)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--workers', type=int, nargs='+', default=[4, 8, 12, 16, 24, 32])
    parser.add_argument('--seed', type=int, default=171020)
    args = parser.parse_args()
    if args.output.exists() or args.seconds <= 0 or min(args.workers) <= 0:
        parser.error('Use a fresh output and positive durations and worker counts')
    rows = []
    for workers in args.workers:
        row = trial(args.dll, workers, args.seconds, args.seed)
        rows.append(row)
        print(json.dumps(row), flush=True)
    with args.output.open('x') as stream:
        json.dump(rows, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()

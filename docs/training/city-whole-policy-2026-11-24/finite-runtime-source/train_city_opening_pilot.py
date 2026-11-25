"""Continue score-only city PPO on a mix of closed openings and ordinary cities."""

import argparse
from collections import defaultdict, deque
from functools import partial
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv

from city_road_pilot import FORWARD, CityRoadEnv
from prepare_city_policy import sha256
from train_city_score_pilot import EPISODE_FIELDS, RecordEpisodes
from visible_observation import WIDTH

TRAIN_START, TRAIN_END = 79_100_000, 79_500_000
DEV_START, DEV_END = 81_100_000, 81_500_000
HORIZON = 1200
OBSERVATION_HORIZON = 600


def opening_has_route(raw, mask):
    """Check reachability in the initial legal-edge mask before making any edits."""
    home, = [b for b in raw['buildings'] if b['isHouse']]
    shop, = [b for b in raw['buildings'] if not b['isHouse']]
    if shop['color'] != home['color']:
        raise RuntimeError('Unexpected unmatched starting parcels')
    graph = defaultdict(list)
    for slot in np.flatnonzero(mask[1:]):
        cell, direction = divmod(int(slot), 4)
        x, y = cell % WIDTH, cell // WIDTH
        dx, dy = FORWARD[direction]
        a, b = (x, y), (x+dx, y+dy)
        graph[a].append(b)
        graph[b].append(a)
    start = home['cell']['x'], home['cell']['y']
    entrances = {(p['x'], p['y']) for p in shop['entrances']}
    queue = deque([start])
    visited = {start}
    while queue:
        cell = queue.popleft()
        if cell in entrances:
            return True
        for neighbor in graph[cell]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return False


class OpeningCity(CityRoadEnv):
    def __init__(self, dll, rank, workers):
        super().__init__(dll, horizon=HORIZON, observation_horizon=OBSERVATION_HORIZON)
        self.scenario_cursor = TRAIN_START + rank
        self.workers = workers
        self.cohort = 'closed' if rank % 2 == 0 else 'ordinary'

    def reset(self, *, seed=None, options=None):
        while self.scenario_cursor < TRAIN_END:
            scenario_seed = self.scenario_cursor
            self.scenario_cursor += self.workers
            obs, info = super().reset(seed=seed, options={'scenario_seed': scenario_seed})
            if self.cohort == 'ordinary' or not opening_has_route(self.raw, self.action_masks()):
                return obs, info
        raise RuntimeError('Ran out of training-only scenario seeds')

    def info(self):
        return dict(**super().info(), cohort=self.cohort)


def make_env(dll, rank, workers):
    return Monitor(OpeningCity(dll, rank, workers), info_keywords=(*EPISODE_FIELDS, 'cohort'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--rollouts-per-save', type=int, default=8)
    args = parser.parse_args()
    if args.workers < 2 or args.workers % 2 or args.rollouts_per_save < 1:
        parser.error('Choose an even worker count with at least two workers and a positive save interval')
    if not torch.cuda.is_available():
        parser.error('CUDA is required')
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    parent_hash, host_hash = sha256(args.parent), sha256(args.dll)
    env = SubprocVecEnv([partial(make_env, args.dll, rank, args.workers) for rank in range(args.workers)],
                        start_method='forkserver')
    try:
        model = MaskablePPO.load(args.parent, env=env, device='cuda', force_reset=True,
                                 seed=682979, learning_rate=5e-5)
        original = model.num_timesteps
        original_epochs = model._n_updates
        optimizer_entries = len(model.policy.optimizer.state)
        if not original or not optimizer_entries:
            raise RuntimeError('Use a trained overnight checkpoint with its optimizer state')
        per_save = args.workers * model.n_steps * args.rollouts_per_save
        config = dict(
            parent=str(args.parent), parent_sha256=parent_hash, host=str(args.dll), host_sha256=host_hash,
            workers=args.workers, rollouts_per_save=args.rollouts_per_save, total_added_decisions=2*per_save,
            initial_decisions=original, optimizer_entries=optimizer_entries, initial_epochs=original_epochs,
            lr=5e-5, seed=682979, rollout_steps=model.n_steps, batch_size=model.batch_size,
            epochs=model.n_epochs, gamma=model.gamma, gae_lambda=model.gae_lambda, target_kl=model.target_kl,
            entropy_coefficient=model.ent_coef, horizons=dict(native=HORIZON, observation=OBSERVATION_HORIZON),
            training_seed_range=[TRAIN_START, TRAIN_END],
        )
        (args.output/'config.json').write_text(json.dumps(config, indent=2)+'\n')
        model.set_logger(configure(str(args.output), ['stdout', 'csv']))
        start = perf_counter()
        saves = []
        with (args.output/'episodes.jsonl').open('x') as file:
            callback = RecordEpisodes(file)
            for _ in range(2):
                model.learn(total_timesteps=per_save, reset_num_timesteps=False, callback=callback)
                model.logger.dump(step=model.num_timesteps)
                added = model.num_timesteps - original
                target = args.output/f'city-added-{added:07d}.zip'
                model.save(target, exclude=['_last_obs', '_last_episode_starts', 'ep_info_buffer', 'ep_success_buffer'])
                saves.append(dict(path=target.name, added_decisions=added, decisions=model.num_timesteps,
                                  sha256=sha256(target), elapsed_seconds=perf_counter()-start,
                                  episodes=callback.completed))
                print(f'SAVED | {target} | {added} added decisions | {callback.completed} games', flush=True)
        if model.num_timesteps != original+2*per_save or sha256(args.parent)!=parent_hash:
            raise RuntimeError('Unexpected pilot budget or parent change')
        (args.output/'status.json').write_text(json.dumps(dict(
            result='COMPLETE', saved=saves, added_ppo_epochs=model._n_updates-original_epochs,
            elapsed_seconds=perf_counter()-start,
            peak_cuda_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
        ), indent=2)+'\n')
    finally:
        env.close()


if __name__ == '__main__':
    main()

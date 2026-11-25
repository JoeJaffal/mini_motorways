"""Run a bounded score-only Maskable PPO pilot in the native growing city."""

import argparse
from functools import partial
import json
from pathlib import Path
from time import perf_counter

from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import configure
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256

TRAINING_SEED_START = 78_000_000
TRAINING_SEED_END = 79_000_000
EPISODE_FIELDS = ('seed', 'seconds', 'trips', 'road_stock', 'buildings', 'weekly_awards',
                  'road_actions', 'wait_actions')


class TrainingCity(CityRoadEnv):
    def __init__(self, dll, worker, workers, *, seed_start=TRAINING_SEED_START, seed_end=TRAINING_SEED_END):
        super().__init__(dll)
        self.next_seed = seed_start + worker
        self.seed_end = seed_end
        self.workers = workers

    def reset(self, *, seed=None, options=None):
        if self.next_seed >= self.seed_end:
            raise RuntimeError('The pilot exhausted the training-only scenario seed range')
        scenario_seed = self.next_seed
        self.next_seed += self.workers
        return super().reset(seed=seed, options={'scenario_seed': scenario_seed})


def make_env(dll, worker, workers):
    return Monitor(TrainingCity(dll, worker, workers), info_keywords=EPISODE_FIELDS)


class RecordEpisodes(BaseCallback):
    def __init__(self, output):
        super().__init__()
        self.output = output
        self.completed = 0

    def _on_step(self):
        for info in self.locals['infos']:
            if 'episode' not in info:
                continue
            episode = info['episode']
            if episode['r'] != episode['trips']:
                raise RuntimeError('Episode return must equal native deliveries')
            row = dict(decisions=self.num_timesteps, truncated=info['TimeLimit.truncated'], **episode)
            self.output.write(json.dumps(row) + '\n')
            self.completed += 1
        return True

    def _on_rollout_end(self):
        self.output.flush()
        self.logger.record('pilot/completed_games', self.completed)
        if torch.cuda.is_available():
            self.logger.record('pilot/peak_allocated_mib', torch.cuda.max_memory_allocated() / 2**20)
            self.logger.record('pilot/peak_reserved_mib', torch.cuda.max_memory_reserved() / 2**20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--rollouts-per-save', type=int, default=6)
    parser.add_argument('--saves', type=int, default=2)
    args = parser.parse_args()
    rollout_steps, batch_size, epochs, seed = 128, 64, 4, 837111
    if min(args.workers, args.rollouts_per_save, args.saves) <= 0:
        parser.error('Worker count, rollouts per save, and save count must be positive')
    if not torch.cuda.is_available():
        parser.error('The pilot requires CUDA')
    torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=False)
    original_hash = sha256(args.checkpoint)
    per_save = args.workers * rollout_steps * args.rollouts_per_save
    config = dict(workers=args.workers, rollout_steps=rollout_steps, batch_size=batch_size,
                  epochs=epochs, seed=seed, rollouts_per_save=args.rollouts_per_save,
                  saves=args.saves, requested_decisions=per_save * args.saves, learning_rate=1e-4,
                  scenario_seed_range=[TRAINING_SEED_START, TRAINING_SEED_END],
                  parent=str(args.checkpoint), parent_sha256=original_hash,
                  host=str(args.dll), host_sha256=sha256(args.dll), device='cuda',
                  gamma=1.0, gae_lambda=.95, entropy_coefficient=.01, target_kl=.03)
    (args.output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    env = SubprocVecEnv([partial(make_env, args.dll, i, args.workers) for i in range(args.workers)],
                        start_method='forkserver')
    try:
        model = MaskablePPO.load(
            args.checkpoint, env=env, device='cuda', seed=seed, n_steps=rollout_steps,
            batch_size=batch_size, n_epochs=epochs, learning_rate=config['learning_rate'],
            gamma=config['gamma'], gae_lambda=config['gae_lambda'],
            ent_coef=config['entropy_coefficient'], target_kl=config['target_kl'],
        )
        if model.num_timesteps or model.policy.optimizer.state:
            raise RuntimeError('Use the frozen city starting checkpoint for this pilot')
        model.set_logger(configure(str(args.output), ['stdout', 'csv']))
        checkpoints = []
        start = perf_counter()
        with (args.output / 'episodes.jsonl').open('x') as episode_output:
            callback = RecordEpisodes(episode_output)
            for _ in range(args.saves):
                model.learn(total_timesteps=per_save, reset_num_timesteps=False, callback=callback)
                model.logger.dump(step=model.num_timesteps)
                path = args.output / f'city-{model.num_timesteps:07d}.zip'
                model.save(path)
                checkpoints.append(dict(path=path.name, sha256=sha256(path), decisions=model.num_timesteps,
                                        elapsed_seconds=perf_counter() - start))
                print(f'SAVED | {path} | {callback.completed} completed games', flush=True)
        if sha256(args.checkpoint) != original_hash or model.num_timesteps != config['requested_decisions']:
            raise RuntimeError('Pilot changed the parent or exceeded its requested decision budget')
        status = dict(result='COMPLETE', checkpoints=checkpoints, completed_games=callback.completed,
                      elapsed_seconds=perf_counter()-start, policy_update_passes=model._n_updates,
                      peak_cuda_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                      peak_cuda_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
        (args.output / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    finally:
        env.close()


if __name__ == '__main__':
    main()

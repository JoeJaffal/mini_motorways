"""Check and train city service ranking with native one-edge actions and score reward."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import json
import multiprocessing
from pathlib import Path
from time import monotonic

import numpy as np
from sb3_contrib import MaskablePPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

from city_network_service_policy import CityNetworkServiceFeatures, CityNetworkServicePolicy
from city_road_pilot import edge_action
from city_service_policy import CityServiceFeatures
from evaluate_midgame_service import exercise_game
from prepare_city_policy import sha256
from run_city_overnight import publish_json
from train_city_score_pilot import EPISODE_FIELDS, RecordEpisodes
from train_midgame_service import MidgameServiceEnv, NETWORK_LESSONS, SERVICE_FIELDS

TRAIN_START, TRAIN_END = 108_000_000, 108_100_000
VALIDATION_START = 108_200_000
LESSON_CYCLE = (NETWORK_LESSONS[0], NETWORK_LESSONS[1], NETWORK_LESSONS[1], NETWORK_LESSONS[2])
INITIAL_PRIOR = dict(progress=1.5, join=5., coupling=1.)


class CityNetworkPracticeEnv(MidgameServiceEnv):
    def __init__(self, dll, worker=0, workers=1, *, validation=False):
        super().__init__(dll, worker, workers, validation=validation)
        self.cursor = TRAIN_START + worker
        self.episode = 0

    def reset(self, *, seed=None, options=None):
        if options is None:
            if not TRAIN_START <= self.cursor < TRAIN_END:
                raise RuntimeError('Exhausted network practice training seeds')
            exercise = LESSON_CYCLE[(self.episode+self.worker) % len(LESSON_CYCLE)]
            options = dict(scenario_seed=self.cursor, exercise=exercise)
            self.cursor += self.workers
            self.episode += 1
        return super().reset(seed=seed, options=options)


def verify(dll):
    rows = []
    for validation in (False, True):
        env = CityNetworkPracticeEnv(dll, validation=validation)
        try:
            base = VALIDATION_START if validation else TRAIN_END - 1_000
            for index, exercise in enumerate(NETWORK_LESSONS):
                for seed in range(base+100*index, base+100*index+16):
                    obs, initial = env.reset(options=dict(scenario_seed=seed, exercise=exercise))
                    assert env.observation_space.contains(obs)
                    edits = env.host.call(command='curriculumReference')['edits']
                    actions = [edge_action((e['x'], e['y']), (e['toX'], e['toY'])) for e in edits]
                    assert bool(all(env.action_masks()[a] for a in actions)) == (exercise != NETWORK_LESSONS[-1])
                    for action in actions:
                        while not env.action_masks()[action] and not env.done:
                            env.step(0)
                        env.step(action)
                    while not env.done:
                        env.step(0)
                    row = env.info()
                    if not row['new_deliveries'] or not row['existing_deliveries']:
                        raise RuntimeError(f'Native scoring witness failed: {row}')
                    if initial['road_stock']-row['road_stock'] != len(actions):
                        raise RuntimeError(f'Witness did not use the expected paid road units: {row}')
                    row.update(split=env.split, witness_actions=actions)
                    rows.append(row)
        finally:
            env.close()
    return rows


def make_worker(dll, worker, workers):
    return Monitor(CityNetworkPracticeEnv(dll, worker, workers),
                   info_keywords=(*EPISODE_FIELDS, *SERVICE_FIELDS))


def transfer(parent, env, settings):
    if type(parent.policy.features_extractor) is not CityServiceFeatures:
        raise ValueError('Use the narrow city service checkpoint as the source')
    conservative = parent.policy.features_extractor.conservative
    model = MaskablePPO(
        CityNetworkServicePolicy, env, **settings,
        policy_kwargs=dict(features_extractor_class=CityNetworkServiceFeatures,
                           features_extractor_kwargs=dict(conservative=conservative),
                           normalize_images=False),
    )
    missing, unexpected = model.policy.load_state_dict(parent.policy.state_dict(), strict=False)
    expected = {f'{prefix}.growth_service_urgency' for prefix in
                ('features_extractor', 'pi_features_extractor', 'vf_features_extractor')}
    if set(missing) != expected or unexpected:
        raise RuntimeError(f'Unexpected network service transfer: {missing}, {unexpected}')
    model.num_timesteps = parent.num_timesteps
    model._n_updates = parent._n_updates
    return model


def train(args):
    if not torch.cuda.is_available():
        raise RuntimeError('Use CUDA for the bounded pilot')
    args.output.mkdir(parents=True, exist_ok=False)
    source_hash, host_hash = sha256(args.parent), sha256(args.dll)
    parent = MaskablePPO.load(args.parent, device='cpu')
    settings = dict(device='cuda', seed=641997, n_steps=128, batch_size=64, n_epochs=4,
                    learning_rate=3e-4, gamma=1., gae_lambda=.95, ent_coef=.01, target_kl=.03)
    per_stage = args.rollouts_per_save * args.workers * settings['n_steps']
    config = dict(parent=str(args.parent), parent_sha256=source_hash, host=str(args.dll), host_sha256=host_hash,
                  settings=settings, workers=args.workers, training_range=[TRAIN_START, TRAIN_END],
                  decisions_requested=per_stage*2, initial_prior=INITIAL_PRIOR)
    publish_json(args.output/'config.json', config)
    env = SubprocVecEnv([partial(make_worker, args.dll, worker, args.workers) for worker in range(args.workers)],
                       start_method='forkserver')
    start = monotonic()
    try:
        model = transfer(parent, env, settings)
        model.save(args.output/'network-only.zip')
        with torch.no_grad():
            for name, delta in INITIAL_PRIOR.items():
                getattr(model.policy.features_extractor, f'growth_service_{name}').add_(delta)
        model.save(args.output/'initial.zip')
        model.set_logger(configure(str(args.output), ['csv']))
        rows = []
        with (args.output/'training-episodes.jsonl').open('x') as stream:
            callback = RecordEpisodes(stream)
            for stage in ('midpoint', 'final'):
                for _ in range(args.rollouts_per_save):
                    model.learn(total_timesteps=args.workers*settings['n_steps'],
                                reset_num_timesteps=False, callback=callback)
                    metrics = model.logger.name_to_value
                    if not all(np.isfinite(metrics[key]) for key in ('train/loss', 'train/approx_kl', 'train/value_loss')):
                        raise RuntimeError('Nonfinite learner metrics')
                    model.logger.dump(step=model.num_timesteps)
                    print(f'PPO | {model.num_timesteps-parent.num_timesteps} added decisions | '
                          f'{callback.completed} episodes', flush=True)
                path = args.output/f'{stage}.zip'
                model.save(path, exclude=['_last_obs', '_last_episode_starts', 'ep_info_buffer', 'ep_success_buffer'])
                rows.append(dict(path=path.name, sha256=sha256(path),
                                 decisions_added=model.num_timesteps-parent.num_timesteps,
                                 episodes=callback.completed, elapsed_seconds=monotonic()-start))
                publish_json(args.output/'checkpoints.json', rows)
        if rows[-1]['decisions_added'] != config['decisions_requested']:
            raise RuntimeError('The actual PPO decision count differs from the configured budget')
        if sha256(args.parent) != source_hash or sha256(args.dll) != host_hash:
            raise RuntimeError('The parent checkpoint or native host changed during the pilot')
    finally:
        env.close()


def evaluate_batch(dll, paths, jobs):
    torch.set_num_threads(1)
    models = [MaskablePPO.load(path, device='cpu') for path in paths]
    env = CityNetworkPracticeEnv(dll, validation=True)
    try:
        rows = []
        for job in jobs:
            scores = []
            for index, model in enumerate(models):
                row = exercise_game(env, model, job)
                rows.append(dict(row, model=index, action_seed=job['action_seed']))
                scores.append(row['new_deliveries'])
            print(f'EVAL | {job["cohort"]} {job["seed"]} | {scores}', flush=True)
        return rows
    finally:
        env.close()


def evaluate(args):
    args.output.mkdir(parents=True, exist_ok=False)
    hashes = {str(path): sha256(path) for path in args.checkpoints}
    host_hash = sha256(args.dll)
    rng = np.random.default_rng(args.seed)
    jobs = [
        dict(cohort=exercise, seed=VALIDATION_START+1_000+index*20_000+int(offset),
             action_seed=int(rng.integers(100_000_000, 2**31)))
        for index, exercise in enumerate(NETWORK_LESSONS)
        for offset in rng.choice(20_000, args.games, replace=False)
    ]
    publish_json(args.output/'suite.json', jobs)
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks = [pool.submit(evaluate_batch, args.dll, args.checkpoints, jobs[i::args.workers])
                 for i in range(args.workers)]
        rows = [row for task in tasks for row in task.result()]
    if len(rows) != len(jobs)*len(args.checkpoints) or any(sha256(Path(p)) != h for p, h in hashes.items()):
        raise RuntimeError('Incomplete data or changed checkpoints')
    if sha256(args.dll) != host_hash:
        raise RuntimeError('The native host changed during frozen review')
    rows.sort(key=lambda row: (row['model'], row['exercise'], row['seed']))
    (args.output/'games.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    results = {}
    for index in range(len(args.checkpoints)):
        results[index] = {}
        for exercise in NETWORK_LESSONS:
            group = [row for row in rows if row['model'] == index and row['exercise'] == exercise]
            results[index][exercise] = dict(
                games=len(group), served=sum(row['new_deliveries'] > 0 for row in group),
                mean_new=float(np.mean([row['new_deliveries'] for row in group])),
                mean_existing=float(np.mean([row['existing_deliveries'] for row in group])),
                mean_score=float(np.mean([row['trips'] for row in group])),
                stock_at_gate=sum((row['stock_at_gate'] or 0) > 0 for row in group),
            )
    publish_json(args.output/'summary.json', dict(models=list(hashes), sha256=hashes,
                                                host_sha256=host_hash, results=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('verify', 'train', 'evaluate'))
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--rollouts-per-save', type=int, default=8)
    parser.add_argument('--checkpoints', type=Path, nargs='+')
    parser.add_argument('--games', type=int, default=16)
    parser.add_argument('--seed', type=int, default=516231)
    args = parser.parse_args()
    if (args.workers < 1 or args.rollouts_per_save < 1 or not 1 <= args.games <= 20_000
            or (args.mode == 'train' and not args.parent) or (args.mode == 'evaluate' and not args.checkpoints)):
        parser.error('Supply positive counts and the checkpoints for this mode')
    torch.set_num_threads(1)
    if args.mode == 'verify':
        args.output.mkdir(parents=True, exist_ok=False)
        rows = verify(args.dll)
        publish_json(args.output/'witnesses.json', rows)
        print(f'PREFLIGHT | {len(rows)} native scoring witnesses', flush=True)
    elif args.mode == 'train':
        train(args)
    else:
        evaluate(args)


if __name__ == '__main__':
    main()

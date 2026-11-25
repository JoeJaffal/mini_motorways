"""Run the resumable native-score full-city pilot from the repaired opening policy."""

import argparse
import fcntl
from functools import partial
import json
from math import isfinite
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor
import torch

from city_growth_policy import CityGrowthFeatures, CityGrowthPolicy
from prepare_city_policy import sha256
from run_city_overnight import ARCHIVE, DEFAULT_HOST, PILOT_CONFIG, ROOT, publish_json, read_json, train
from train_city_score_pilot import EPISODE_FIELDS, TrainingCity

PARENT_RECORD = ARCHIVE / 'city-route-repair-2026-11-22/selected-checkpoint.json'
CITY_CRITIC = ROOT / 'output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip'
CITY_CRITIC_SHA256 = 'a65357dea3e889525bfdc18743dbbeb02141ad244934b270217afad7a472df29'
SEED_START, SEED_END = 92_000_000, 92_500_000


def make_worker(dll, scenario_seed, workers):
    os.setsid()
    native = TrainingCity(dll, 0, workers, seed_start=scenario_seed, seed_end=SEED_END)
    return Monitor(native, info_keywords=EPISODE_FIELDS)


def load_initial(path, env, settings, *, critic, policy_class=CityGrowthPolicy, features_class=CityGrowthFeatures, feature_options=None):
    parent = MaskablePPO.load(path, device='cpu')
    city = MaskablePPO.load(critic, device='cpu')
    model = MaskablePPO(
        policy_class, env, **settings,
        policy_kwargs=dict(features_extractor_class=features_class, normalize_images=False,
                           features_extractor_kwargs=feature_options),
    )
    missing, extra = model.policy.load_state_dict(parent.policy.state_dict(), strict=False)
    prefixes = ('features_extractor.growth_', 'pi_features_extractor.growth_', 'vf_features_extractor.growth_')
    if extra or not missing or any(not name.startswith(prefixes) for name in missing):
        raise RuntimeError(f'Unexpected policy transfer: {missing}, {extra}')
    model.policy.value_net.load_state_dict(city.policy.value_net.state_dict())
    model.num_timesteps = parent.num_timesteps
    model._n_updates = parent._n_updates
    return model


def review(root, config, state):
    if (root/'review.json').exists():
        return
    checkpoints = [config['start']]
    for row in state['checkpoints']:
        path = root/row['path']
        if sha256(path) != row['sha256']:
            raise RuntimeError(f'Checkpoint changed: {path}')
        checkpoints.append(str(path))
    if sha256(Path(checkpoints[0])) != config['start_sha256']:
        raise RuntimeError('The repaired baseline changed')
    destination = root/f'evaluation-{uuid4().hex[:8]}'
    subprocess.run([
        sys.executable, '-u', str(ROOT/'training/evaluate_city_route_repair.py'),
        '--dll', config['dll'], '--city-dll', config['dll'],
        '--checkpoints', *checkpoints, '--cohorts', 'city',
        '--zone-offset', '5000000', '--seed', str(config['review_seed']),
        '--city-games', str(config['review_games']), '--workers', str(min(8, config['review_games'])),
        '--output', str(destination),
    ], check=True)
    results = read_json(destination/'summary.json')
    publish_json(root/'review.json', dict(folder=str(destination),
                                        models=results['models'], measurements=results['results']))
    print(f'REVIEW COMPLETE | {root / "review.json"}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--hours', type=float, default=1.)
    parser.add_argument('--save-minutes', type=float, default=30.)
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--review-games', type=int, default=24)
    parser.add_argument('--review-seed', type=int, default=661207)
    parser.add_argument('--training-seed-start', type=int, default=SEED_START)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if (not isfinite(args.hours) or not isfinite(args.save_minutes) or min(args.hours, args.save_minutes) <= 0
            or min(args.workers, args.review_games) < 1
            or not SEED_START <= args.training_seed_start < SEED_END - args.workers):
        parser.error('Use positive settings and a start inside the growth training seed range')
    if not torch.cuda.is_available():
        parser.error('CUDA is required')
    torch.set_num_threads(1)
    parent_record = read_json(PARENT_RECORD)
    start = ROOT / parent_record['policy_checkpoint']
    pilot = read_json(PILOT_CONFIG)
    parent_hash, host_hash, critic_hash = sha256(start), sha256(DEFAULT_HOST), sha256(CITY_CRITIC)
    if (parent_hash, host_hash, critic_hash) != (parent_record['sha256'], pilot['host_sha256'], CITY_CRITIC_SHA256):
        parser.error('The repaired checkpoint, native host, or city critic differs from the verified artifact')
    parent = MaskablePPO.load(start, device='cpu')
    config = dict(
        hours=args.hours, save_minutes=args.save_minutes, workers=args.workers,
        dll=str(DEFAULT_HOST), start=str(start), start_sha256=parent_hash, host_sha256=host_hash,
        critic=str(CITY_CRITIC), critic_sha256=critic_hash,
        initial_model_state=[parent.num_timesteps, 0, parent._n_updates],
        pilot=dict(pilot, learning_rate=5e-5, seed=946753),
        training_seed_start=args.training_seed_start, training_seed_end=SEED_END,
        review_seed=args.review_seed, review_games=args.review_games,
    )
    root = args.output.resolve()
    if not args.resume:
        root.mkdir(parents=True, exist_ok=False)
    with (root/'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.resume:
            if config != read_json(root/'config.json'):
                parser.error('Resume requires the original settings and checkpoints')
            state = read_json(root/'state.json')
        else:
            (root/'checkpoints').mkdir()
            (root/'sessions').mkdir()
            state = dict(training_complete=False, checkpoints=[])
            publish_json(root/'config.json', config)
            publish_json(root/'state.json', state)
        initializer = partial(load_initial, critic=CITY_CRITIC)
        if not state['training_complete'] and not train(
            root, config, state, worker_factory=make_worker, load_initial=initializer,
        ):
            print('STOPPED | use the same command with --resume', flush=True)
            return
        review(root, config, state)


if __name__ == '__main__':
    main()

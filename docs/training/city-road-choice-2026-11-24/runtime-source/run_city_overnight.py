"""Run resumable, time-bounded city PPO and compare saved checkpoints."""

import argparse
import fcntl
from functools import partial
import json
from math import isfinite
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import monotonic
from uuid import uuid4

from sb3_contrib import MaskablePPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

from prepare_city_policy import sha256
from train_city_score_pilot import RecordEpisodes, TRAINING_SEED_START, make_env

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'docs/training'
DEFAULT_HOST = ROOT / 'output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll'
DEFAULT_START = ROOT / 'output/training/city-road-start-01/city-start.zip'
PILOT_CONFIG = ARCHIVE / 'city-score-pilot-2026-11-22/config.json'
DEV = ARCHIVE / 'city-score-pilot-2026-11-22/development-seeds.json'
TEST = ARCHIVE / 'city-frozen-baseline-2026-11-22/seed-suite.json'
OVERNIGHT_SEED_START = 78_100_000


def read_json(path):
    return json.loads(path.read_text())


def publish_json(path, content):
    temporary = path.with_name(f'.{path.name}-{uuid4().hex}.tmp')
    with temporary.open('x') as output:
        json.dump(content, output, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def save_state(root, model, env, state, elapsed, finished, completed_games):
    token = f'city-{model.num_timesteps:09d}-{uuid4().hex[:8]}'
    path = root / 'checkpoints' / f'{token}.zip'
    temporary = path.with_name(f'.{token}.tmp.zip')
    model.save(temporary, exclude=['_last_obs', '_last_episode_starts', 'ep_info_buffer', 'ep_success_buffer'])
    with temporary.open('rb') as output:
        os.fsync(output.fileno())
    temporary.replace(path)
    checkpoint = dict(
        path=str(path.relative_to(root)), sha256=sha256(path), decisions=model.num_timesteps,
        training_seconds=elapsed, next_seeds=env.get_attr('next_seed'),
        optimizer_entries=len(model.policy.optimizer.state), epochs=model._n_updates,
        completed_games=completed_games,
    )
    state['checkpoints'].append(checkpoint)
    state['training_complete'] = finished
    publish_json(root / 'state.json', state)
    print(f'SAVED | {path.name} | {elapsed/3600:.3f}h trained | '
          f'{completed_games} completed games | complete={finished}', flush=True)


def make_overnight_worker(dll, scenario_seed, workers):
    # Keep terminal Ctrl+C in the parent so workers can finish their current rollout.
    os.setsid()
    return make_env(dll, scenario_seed - TRAINING_SEED_START, workers)


def train(root, config, state, *, worker_factory=make_overnight_worker, load_initial=None):
    previous = state['checkpoints'][-1] if state['checkpoints'] else None
    path = Path(config['start']) if previous is None else root / previous['path']
    if sha256(path) != (config['start_sha256'] if previous is None else previous['sha256']):
        raise RuntimeError(f'Checkpoint does not match its recorded hash: {path}')
    workers = config['workers']
    settings = config['pilot']
    rollout = workers * settings['rollout_steps']
    first_seed = config.get('training_seed_start', OVERNIGHT_SEED_START)
    next_seeds = (list(range(first_seed, first_seed + workers)) if previous is None else previous['next_seeds'])
    env = SubprocVecEnv([partial(worker_factory, config['dll'], seed, workers) for seed in next_seeds],
                       start_method='forkserver')
    old_handlers = {}
    stop_signal = None

    def request_stop(signum, _frame):
        nonlocal stop_signal
        stop_signal = signum

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            old_handlers[signum] = signal.signal(signum, request_stop)
        seed = settings['seed'] + (0 if previous is None else previous['decisions'] // rollout)
        ppo_settings = dict(
            device='cuda', seed=seed, n_steps=settings['rollout_steps'],
            batch_size=settings['batch_size'], n_epochs=settings['epochs'],
            learning_rate=settings['learning_rate'], gamma=settings['gamma'],
            gae_lambda=settings['gae_lambda'], ent_coef=settings['entropy_coefficient'],
            target_kl=settings['target_kl'],
        )
        if previous is None and load_initial is not None:
            model = load_initial(path, env, ppo_settings)
        else:
            model = MaskablePPO.load(path, env=env, force_reset=True, **ppo_settings)
        expected = tuple(config.get('initial_model_state', (0, 0, 0))) if previous is None else (
            previous['decisions'], previous['optimizer_entries'], previous['epochs'])
        loaded = model.num_timesteps, len(model.policy.optimizer.state), model._n_updates
        if loaded != expected:
            raise RuntimeError(f'Restored decisions, optimizer state or PPO epochs differ: {loaded} vs {expected}')
        session = root / 'sessions' / uuid4().hex[:12]
        session.mkdir()
        publish_json(session / 'start.json', dict(decisions=loaded[0], optimizer_entries=loaded[1],
                                                epochs=loaded[2], next_scenario_seeds=next_seeds))
        model.set_logger(configure(str(session), ['csv']))
        prior_seconds = 0 if previous is None else previous['training_seconds']
        previous_games = 0 if previous is None else previous['completed_games']
        last_save = prior_seconds
        print(f'START | {workers} workers | {loaded[0]} saved decisions | '
              f'{prior_seconds/3600:.3f}h already trained | optimizer tensors {loaded[1]}', flush=True)
        with (session/'episodes.jsonl').open('x') as output:
            callback = RecordEpisodes(output)
            start = monotonic()
            while stop_signal is None:
                model.learn(total_timesteps=rollout, reset_num_timesteps=False, callback=callback)
                elapsed = prior_seconds + monotonic() - start
                completed_games = previous_games + callback.completed
                metrics = model.logger.name_to_value
                for metric in ('train/loss', 'train/approx_kl', 'train/value_loss'):
                    if not isfinite(metrics[metric]):
                        raise RuntimeError(f'Nonfinite PPO metric: {metric}')
                model.logger.dump(step=model.num_timesteps)
                recent = model.ep_info_buffer
                score = f' | mean score {sum(row["trips"] for row in recent)/len(recent):.1f}' if recent else ''
                print(f'PPO | {model.num_timesteps} decisions | {completed_games} completed games{score} | '
                      f'{elapsed/3600:.3f}/{config["hours"]:g}h', flush=True)
                finished = elapsed >= config['hours'] * 3600
                if finished or stop_signal or elapsed - last_save >= config['save_minutes'] * 60:
                    save_state(root, model, env, state, elapsed, finished, completed_games)
                    last_save = elapsed
                if finished:
                    break
            if stop_signal and model.num_timesteps > loaded[0]:
                saved_decisions = state['checkpoints'][-1]['decisions'] if state['checkpoints'] else 0
                if model.num_timesteps > saved_decisions:
                    save_state(root, model, env, state, prior_seconds + monotonic() - start, False,
                               previous_games + callback.completed)
        return stop_signal is None and state['training_complete']
    finally:
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        env.close()


def development_candidates(root, checkpoints, interval_seconds=3600):
    candidates = []
    next_review = interval_seconds
    for checkpoint in checkpoints:
        if checkpoint['training_seconds'] >= next_review:
            candidates.append(root / checkpoint['path'])
            next_review = (int(checkpoint['training_seconds'] // interval_seconds) + 1) * interval_seconds
    final = root / checkpoints[-1]['path']
    if final not in candidates:
        candidates.append(final)
    return candidates


def choose_development_checkpoint(measurements):
    sampled = [row for row in measurements if row['mode'] == 'sampled']
    baseline = next(row for row in sampled if row['checkpoint_decisions'] == 0)
    eligible = [row for row in sampled if row['scoring_games'] >= baseline['scoring_games']]
    return max(eligible, key=lambda row: (row['mean_score'], -row['checkpoint_decisions']))


def review(root, config, state, development=DEV, test=TEST, workers=8):
    if development == DEV and sha256(development) != config['development_sha256']:
        raise RuntimeError('The development suite changed since run preparation')
    if test == TEST and sha256(test) != config['test_sha256']:
        raise RuntimeError('The reserved suite changed since run preparation')
    if (root/'review.json').exists():
        print(f'REVIEW | already complete | {root / "review.json"}', flush=True)
        return
    attempt = root / f'review-{uuid4().hex[:8]}'
    attempt.mkdir()
    start = Path(config['start'])
    candidates = development_candidates(root, state['checkpoints'])
    checksums = {root / row['path']: row['sha256'] for row in state['checkpoints']}
    if sha256(start) != config['start_sha256'] or any(sha256(path) != checksums[path] for path in candidates):
        raise RuntimeError('A review checkpoint differs from its recorded hash')

    def evaluate(label, suite, checkpoints):
        destination = attempt / label
        count = len(read_json(suite)['games'])
        subprocess.run([
            sys.executable, '-u', str(ROOT/'training/evaluate_city_checkpoints.py'),
            '--dll', config['dll'], '--checkpoints', *map(str, checkpoints),
            '--seed-suite', str(suite), '--output', str(destination), '--workers', str(min(workers, count)),
        ], check=True)
        return read_json(destination/'summary.json')

    print(f'REVIEW | {len(candidates)} training checkpoints and the starting reference', flush=True)
    dev = evaluate('development', development, [start, *candidates])
    selection = choose_development_checkpoint(dev['measurements'])
    decision = selection['checkpoint_decisions']
    chosen = next((root / row['path'] for row in state['checkpoints'] if row['decisions'] == decision), start)
    publish_json(attempt/'selection.json', dict(checkpoint=str(chosen), development=selection))
    test_checkpoints = [start] if chosen == start else [start, chosen]
    reserved = evaluate('reserved', test, test_checkpoints)
    publish_json(root/'review.json', dict(folder=str(attempt), checkpoint=str(chosen),
                                        selection=selection, reserved=reserved['measurements']))
    print(f'REVIEW COMPLETE | {root / "review.json"} | selected {chosen}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hours', type=float, default=8)
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--save-minutes', type=float, default=15)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dll', type=Path, default=DEFAULT_HOST)
    parser.add_argument('--start', type=Path, default=DEFAULT_START)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--train-only', action='store_true', help='Skip post-run evaluation')
    args = parser.parse_args()
    if not (isfinite(args.hours) and args.hours > 0 and isfinite(args.save_minutes)
            and args.save_minutes > 0 and args.workers > 0):
        parser.error('Use a positive run budget, checkpoint interval, and worker count')
    if not torch.cuda.is_available():
        parser.error('CUDA is required for training')
    torch.set_num_threads(1)
    pilot = read_json(PILOT_CONFIG)
    root = args.output.resolve()
    config = dict(hours=args.hours, workers=args.workers, save_minutes=args.save_minutes,
                  dll=str(args.dll.resolve()), start=str(args.start.resolve()),
                  host_sha256=sha256(args.dll), start_sha256=sha256(args.start), pilot=pilot,
                  development_sha256=sha256(DEV), test_sha256=sha256(TEST))
    if (config['host_sha256'], config['start_sha256']) != (pilot['host_sha256'], pilot['parent_sha256']):
        parser.error('Use the verified city host and frozen starting checkpoint from the score pilot')
    if not args.resume:
        root.mkdir(parents=True, exist_ok=False)
    with (root/'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.resume:
            if config != read_json(root/'config.json'):
                parser.error('Resume requires the original run settings and input hashes')
            state = read_json(root/'state.json')
        else:
            (root/'checkpoints').mkdir()
            (root/'sessions').mkdir()
            state = dict(training_complete=False, checkpoints=[])
            publish_json(root/'config.json', config)
            publish_json(root/'state.json', state)
        if not state['training_complete'] and not train(root, config, state):
            print('STOPPED | resume with the same command and --resume', flush=True)
            return
        if not args.train_only:
            review(root, config, state)


if __name__ == '__main__':
    main()

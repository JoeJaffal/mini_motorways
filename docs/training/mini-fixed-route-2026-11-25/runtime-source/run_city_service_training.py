"""Run a time-bounded score-only PPO continuation for native city service."""

import argparse
import fcntl
from functools import partial
from math import isfinite
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from sb3_contrib import MaskablePPO
import torch

from city_service_policy import CityServiceFeatures
from prepare_city_policy import sha256
from run_city_growth_pilot import CITY_CRITIC, CITY_CRITIC_SHA256, PARENT_RECORD, load_initial
from run_city_overnight import PILOT_CONFIG, ROOT, development_candidates, publish_json, read_json, train
from train_city_score_pilot import EPISODE_FIELDS, TrainingCity
from stable_baselines3.common.monitor import Monitor
import os

SEED_START, SEED_END = 97_000_000, 99_000_000
BASELINE = ROOT / read_json(PARENT_RECORD)['policy_checkpoint']


def make_worker(dll, seed, workers):
    os.setsid()
    native = TrainingCity(dll, 0, workers, seed_start=seed, seed_end=SEED_END)
    return Monitor(native, info_keywords=EPISODE_FIELDS)


def review(root, config, state):
    if (root/'review.json').exists():
        return
    candidates = development_candidates(root, state['checkpoints'], config['review_interval_minutes']*60)
    if sha256(Path(config['baseline'])) != config['baseline_sha256']:
        raise RuntimeError('The repaired reference changed before review')
    start = [] if config['start'] == config['baseline'] else [config['start']]
    review_paths = [config['baseline'], *start, *map(str, candidates)]
    for path in candidates:
        item = next(c for c in state['checkpoints'] if path == root/c['path'])
        if sha256(path) != item['sha256']:
            raise RuntimeError(f'A saved checkpoint changed: {path}')
    reference = str(root/'initial.zip')
    if (root/'initial.zip').exists():
        review_paths.insert(1, reference)
    destination = root/f'review-{uuid4().hex[:8]}'
    subprocess.run([
        sys.executable, '-u', str(ROOT/'training/evaluate_city_service.py'),
        '--dll', config['dll'], '--checkpoints', *review_paths, '--output', str(destination),
        '--games', str(config['review_games']), '--seed', str(config['review_seed']),
    ], check=True)
    publish_json(root/'review.json', dict(folder=str(destination),**read_json(destination/'summary.json')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True,type=Path)
    parser.add_argument('--dll', required=True,type=Path)
    parser.add_argument('--start', default=BASELINE,type=Path)
    parser.add_argument('--hours', required=True,type=float)
    parser.add_argument('--save-minutes', default=15.,type=float)
    parser.add_argument('--seed-start', default=SEED_START,type=int)
    parser.add_argument('--workers', default=32,type=int)
    parser.add_argument('--review-games', default=24,type=int)
    parser.add_argument('--review-seed', default=274698,type=int)
    parser.add_argument('--review-interval-minutes',default=60.,type=float)
    parser.add_argument('--reserve',action='store_true',help='Conserve scarce stock only on quiet, supplied networks')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--learning-rate',type=float,help='Override the continuation learning rate')
    args=parser.parse_args()
    if args.learning_rate is not None and (not isfinite(args.learning_rate) or args.learning_rate <= 0):
        parser.error('Learning rate must be finite and positive')
    if (not all(isfinite(n) and n>0 for n in (args.hours,args.save_minutes,args.review_interval_minutes))
            or min(args.workers,args.review_games)<1 or not SEED_START<=args.seed_start<SEED_END-args.workers
            or not torch.cuda.is_available()):
        parser.error('Use positive counts and durations, CUDA, and a training-only seed start')
    torch.set_num_threads(1)
    root=args.output.resolve()
    source=args.start.resolve()
    host=args.dll.resolve()
    parent=MaskablePPO.load(source,device='cpu')
    starting_model=parent.policy.features_extractor
    transfer=source==BASELINE
    if not transfer and not isinstance(starting_model,CityServiceFeatures):
        parser.error('Start from the selected repaired policy or a trained city service checkpoint')
    baseline_hash=sha256(BASELINE)
    if baseline_hash!=read_json(PARENT_RECORD)['sha256'] or sha256(CITY_CRITIC)!=CITY_CRITIC_SHA256:
        raise RuntimeError('The repaired base or city critic hash differs')
    critic = CITY_CRITIC
    pilot=dict(read_json(PILOT_CONFIG),learning_rate=8e-5 if transfer else 5e-5,seed=641516)
    if args.learning_rate is not None:
        pilot['learning_rate'] = args.learning_rate
    cfg=dict(hours=args.hours,save_minutes=args.save_minutes,workers=args.workers,
             training_seed_start=args.seed_start,training_seed_end=SEED_END,
             start=str(source),start_sha256=sha256(source),dll=str(host),host_sha256=sha256(host),
             baseline=str(BASELINE),baseline_sha256=baseline_hash,
             initial_model_state=[parent.num_timesteps,len(parent.policy.optimizer.state),parent._n_updates],
             review_games=args.review_games,review_seed=args.review_seed,
             review_interval_minutes=args.review_interval_minutes,pilot=pilot,reserve=args.reserve)
    if not args.resume:
        root.mkdir(parents=True,exist_ok=False)

    def initialize(path, env, settings):
        model=load_initial(path,env,settings,critic=critic,features_class=CityServiceFeatures,
                           feature_options=dict(conservative=args.reserve))
        initial=root/'initial.zip'
        if not initial.exists():
            model.save(initial)
        return model

    with (root/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.resume:
            if cfg!=read_json(root/'config.json'):
                parser.error('Use the original run settings and checkpoint for resume')
            state=read_json(root/'state.json')
        else:
            (root/'checkpoints').mkdir()
            (root/'sessions').mkdir()
            state=dict(training_complete=False,checkpoints=[])
            publish_json(root/'config.json',cfg)
            publish_json(root/'state.json',state)
        if not state['training_complete'] and not train(
                root,cfg,state,worker_factory=make_worker,load_initial=initialize if transfer else None):
            print('STOPPED | resume with the same command and --resume',flush=True)
            return
        review(root,cfg,state)


if __name__=='__main__':
    main()

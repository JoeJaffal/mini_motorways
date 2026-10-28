"""CPU MaskablePPO runner. Run from the repository root; see training/README.md."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import torch
from torch import nn
from sb3_contrib import MaskablePPO
from progress import BudgetCallback
from parallel import make_vector
from shutdown import save_checkpoint,stop_and_save
from rewards import GAMMA,WEIGHT,HOUSE_CAP,REWARD_SCHEMAS
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.logger import configure

from environment import TrafficEnv, ROOT, SCHEMA, CONNECTIVITY_SCHEMA, TOOLS, CHANNELS, GLOBALS


class GridEncoder(BaseFeaturesExtractor):
    def __init__(self, observation_space):
        super().__init__(observation_space, features_dim=128)
        channels=observation_space['grid'].shape[0]
        self.grid = nn.Sequential(nn.Conv2d(channels, 16, 3, stride=2, padding=1), nn.ReLU(),
                                  nn.Conv2d(16, 24, 3, stride=2, padding=1), nn.ReLU(), nn.Flatten())
        with torch.no_grad():
            size = self.grid(torch.zeros(1, channels, 30, 50)).shape[1]
        self.combine = nn.Sequential(nn.Linear(size+GLOBALS, 128), nn.ReLU())

    def forward(self, observations):
        return self.combine(torch.cat([self.grid(observations['grid']), observations['global']], dim=1))


def evaluate(model, dotnet, seconds, seeds, deterministic=False,host_dll=None):
    observation_mode='connectivity' if model.observation_space['grid'].shape[0]==52 else 'legacy'
    env = TrafficEnv(dotnet=dotnet, seconds=seconds, seeds=seeds,observation_mode=observation_mode,
                     draw_mask=getattr(model,'draw_mask','all'),host_dll=host_dll)
    runs = []
    try:
        for seed in seeds:
            obs, _ = env.reset(seed=seed, options={'scenario_seed': seed})
            while True:
                action, _ = model.predict(obs, deterministic=deterministic, action_masks=env.action_masks())
                obs, reward, terminated, truncated, info = env.step(action)
                if terminated or truncated:
                    result = {**info, 'terminated': terminated, 'truncated': truncated,
                              'deterministic': deterministic}
                    runs.append(result)
                    print(f'EVAL | seed {seed} | score {info["trips"]} | survived {info["seconds"]:.1f}s | '
                          f'car wait mean/max {info["mean_car_wait"]:.2f}/{info["max_car_wait"]:.2f}s | '
                          f'{"highest-probability" if deterministic else "sampled"} | '
                          f'{"game failure" if terminated else "time cap"}',flush=True)
                    break
    finally:
        env.close()
    return runs



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', default='dotnet')
    parser.add_argument('--host-dll',type=Path)
    parser.add_argument('--minutes', type=float, default=30)
    parser.add_argument('--steps', type=int, default=10_000_000)
    parser.add_argument('--episode-seconds', type=int, default=3600)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--workers', type=int, choices=[1,2,4], default=1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--eval-episodes', type=int, default=3)
    parser.add_argument('--episodes-per-seed', type=int, default=100)
    parser.add_argument('--train-seed-start', type=int, default=1000)
    parser.add_argument('--train-seed-count', type=int, default=100)
    parser.add_argument('--seed-schedule', choices=['blocks','random'], default='blocks')
    parser.add_argument('--print-seconds', type=float, default=5)
    parser.add_argument('--reward-mode',choices=['trips','connectivity'],default='connectivity')
    parser.add_argument('--observation-mode',choices=['legacy','connectivity'],default='legacy')
    parser.add_argument('--adapt-inputs',action='store_true')
    parser.add_argument('--reset-optimizer',action='store_true')
    parser.add_argument('--validation-minutes',type=float,default=0)
    parser.add_argument('--architecture',choices=['legacy','spatial-residual'],default='legacy')
    parser.add_argument('--draw-mask',choices=['all','productive'],default='all')
    args = parser.parse_args()
    if args.validation_minutes<0:parser.error('Validation interval must be nonnegative')
    if args.minutes <= 0 or args.steps < 1 or args.threads < 1 or not 1 <= args.eval_episodes <= 20:
        parser.error('Positive budgets required; evaluation episodes must be 1..20')
    if args.episodes_per_seed < 1 or args.train_seed_count < 1 or args.print_seconds <= 0:
        parser.error('Seed-block size, seed count and print interval must be positive')
    training_seeds = range(args.train_seed_start,args.train_seed_start+args.train_seed_count)
    if set(training_seeds).intersection(range(2000,2000+args.eval_episodes)):
        parser.error('Training seeds must not overlap reserved evaluation seeds')
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    output = args.output or ROOT/'output/training'/datetime.now().strftime('%Y%m%d-%H%M%S')
    output = output.resolve()
    if output.exists():parser.error(f'Run folder already exists: {output}. Choose a NEW --output / -RunName; use --resume to continue weights.')
    output.mkdir(parents=True, exist_ok=False)
    schema=CONNECTIVITY_SCHEMA if args.observation_mode=='connectivity' else SCHEMA
    config = dict(schema=schema, simulator_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
                  dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
                  version='OriginalReference', city='LosAngeles', device='cpu', algorithm='MaskablePPO',
                  reward=('trip delta' if args.reward_mode=='trips' else 'trip delta + gamma*Phi(next)-Phi(current), per selection'),
                  reward_schema=REWARD_SCHEMAS[args.reward_mode],
                  reward_parameters=dict(gamma=GAMMA,connection_weight=WEIGHT,house_cap=HOUSE_CAP,
                                         terminal_potential=0,external_time_limit='bootstrap live potential') if args.reward_mode=='connectivity' else {},
                  tools=TOOLS, tick_interval=20, maximum_selection_decisions=4,
                  training_seeds=[training_seeds.start, training_seeds.stop-1],
                  seed_schedule=args.seed_schedule, episodes_per_seed=args.episodes_per_seed,
                  evaluation_seeds=[2000, 1999+args.eval_episodes],
                  created_utc=datetime.now(timezone.utc).isoformat(), arguments={k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()},
                  packages={name: importlib.metadata.version(name) for name in
                            ['torch', 'numpy', 'gymnasium', 'stable-baselines3', 'sb3-contrib']},
                  workers=args.workers, aggregate_rollout_size=256,
                  hyperparameters=dict(n_steps=256//args.workers, batch_size=64, n_epochs=4, gamma=GAMMA,
                                       learning_rate=.0003, ent_coef=.01, net_arch=[64]))
    (output/'config.json').write_text(json.dumps(config, indent=2)+'\n')
    # Preserve exact source even before a commit, alongside the revision metadata.
    for name in ['environment.py', 'train.py', 'progress.py','parallel.py','shutdown.py','rewards.py','migration.py','spatial_policy.py']:
        (output/name).write_text((Path(__file__).parent/name).read_text())
    env = make_vector(args.workers, output=output, dotnet=args.dotnet, seconds=args.episode_seconds,
                            seeds=training_seeds, episodes_per_seed=args.episodes_per_seed,
                            seed_schedule=args.seed_schedule, record_replays=True,
                            reward_mode=args.reward_mode,reward_gamma=GAMMA,observation_mode=args.observation_mode,draw_mask=args.draw_mask,host_dll=args.host_dll)
    try:
        if args.resume:
            previous_config = json.loads((args.resume.parent/'config.json').read_text())
            compatible=previous_config['schema']==schema or (args.adapt_inputs and previous_config['schema']==SCHEMA and schema==CONNECTIVITY_SCHEMA)
            if not compatible or previous_config['arguments']['episode_seconds'] != args.episode_seconds:
                raise RuntimeError('Resume schema or episode duration mismatch')
            prior_architecture=previous_config['arguments'].get('architecture','legacy')
            if prior_architecture!=args.architecture and not (args.adapt_inputs or args.reset_optimizer):
                raise RuntimeError('Architecture change requires explicit warm start')
            if args.adapt_inputs or args.reset_optimizer:
                from migration import warm_start
                model=warm_start(args.resume,env,config['hyperparameters'],args.seed,args.adapt_inputs,args.architecture)
            else:model = MaskablePPO.load(args.resume, env=env, device='cpu',n_steps=256//args.workers)
            if args.reward_mode=='connectivity' and model.gamma!=GAMMA:
                raise RuntimeError('Checkpoint discount must match connectivity-shaping gamma')
        else:
            policy='MultiInputPolicy'
            if args.architecture=='spatial-residual':
                from spatial_policy import SpatialResidualPolicy
                policy=SpatialResidualPolicy
            model = MaskablePPO(policy, env, device='cpu', seed=args.seed, verbose=0,
                                policy_kwargs=dict(features_extractor_class=GridEncoder, net_arch=[64], normalize_images=False),
                                **{k:v for k,v in config['hyperparameters'].items() if k != 'net_arch'})
        model.draw_mask=args.draw_mask
        model.set_logger(configure(str(output), ['csv']))
        model.save(output/'initial')
        initial_parameters = torch.cat([p.detach().flatten().cpu() for p in model.policy.parameters()]).clone()
        print(f'RUN DIRECTORY | {output}',flush=True)
        print(f'REWARD | {REWARD_SCHEMAS[args.reward_mode]} | score/best/evaluation remain actual trips',flush=True)
        print(f'WORKERS | {args.workers} simultaneous games | shared model | 256 aggregate selections per rollout',flush=True)
        print(f'SCHEDULE | {args.episodes_per_seed} consecutive games per seed | '
              f'{training_seeds.start} through {training_seeds.stop-1} | {args.seed_schedule}',flush=True)
        print('EVALUATION | checking starting policy on reserved seeds before learner timer starts',flush=True)
        torch.manual_seed(args.seed+1)
        before = evaluate(model, args.dotnet, args.episode_seconds, range(2000, 2000+args.eval_episodes),host_dll=args.host_dll)
        def validation_fn(policy):
            training=policy.policy.training
            try:
                with torch.random.fork_rng(devices=[]):
                    torch.manual_seed(43)
                    return evaluate(policy,args.dotnet,args.episode_seconds,range(2000,2000+args.eval_episodes),deterministic=True,host_dll=args.host_dll)
            finally:policy.policy.set_training_mode(training)
        callback = BudgetCallback(output, args.minutes, args.steps, args.episodes_per_seed,
                                  args.print_seconds, config,validation_fn,args.validation_minutes)
        started = time.perf_counter()
        interrupted = False
        try:
            model.learn(total_timesteps=args.steps, callback=callback, reset_num_timesteps=True)
        except KeyboardInterrupt:
            interrupted = True
            print('STOP REQUESTED | saving current policy; skipping final evaluation',flush=True)
            stop_and_save(model,env,callback,output)
        elapsed = time.perf_counter()-started
        if not interrupted:save_checkpoint(model,output/'final.zip')
        final_parameters = torch.cat([p.detach().flatten().cpu() for p in model.policy.parameters()])
        changed = bool(not torch.equal(initial_parameters, final_parameters))
        # Reload for evaluation: exercises checkpoint serialization, not only RAM state.
        restored = MaskablePPO.load(output/'final', device='cpu')
        after, greedy = [], []
        if not interrupted:
            print('EVALUATION | final checkpoint on reserved seeds; learner has stopped',flush=True)
            torch.manual_seed(args.seed+1)
            after = evaluate(restored, args.dotnet, args.episode_seconds, range(2000, 2000+args.eval_episodes),host_dll=args.host_dll)
            torch.manual_seed(args.seed+1)
            greedy = evaluate(restored, args.dotnet, args.episode_seconds, range(2000, 2000+args.eval_episodes), deterministic=True,host_dll=args.host_dll)
        summary = dict(training_wall_seconds=elapsed, policy_steps=model.num_timesteps,
                       completed_commands=callback.commands, episodes=callback.episodes,
                       parameter_update_confirmed=changed, interrupted=interrupted,
                       policy_steps_per_second=model.num_timesteps/elapsed,
                       commands_per_second=callback.commands/elapsed,
                       best_training_score=callback.best, before=before, after=after, deterministic_after=greedy,
                       workers=args.workers,reward_mode=args.reward_mode,reward_schema=REWARD_SCHEMAS[args.reward_mode],
                       seed_schedule=args.seed_schedule, episodes_per_seed=args.episodes_per_seed,
                       best_replay=str(output/'best-game.json') if (output/'best-game.json').exists() else None,
                       evaluation_skipped=interrupted, target_score=1000,
                       target_met=any(r['trips'] >= 1000 for r in after+greedy))
        (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print('RESULT ' + json.dumps(summary), flush=True)
        print(f'Artifacts: {output}', flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()

"""CPU MaskablePPO runner. Run from the repository root; see training/README.md."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import torch
from torch import nn
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.logger import configure

from environment import TrafficEnv, ROOT, SCHEMA, TOOLS, CHANNELS, GLOBALS


class GridEncoder(BaseFeaturesExtractor):
    def __init__(self, observation_space):
        super().__init__(observation_space, features_dim=128)
        self.grid = nn.Sequential(nn.Conv2d(CHANNELS, 16, 3, stride=2, padding=1), nn.ReLU(),
                                  nn.Conv2d(16, 24, 3, stride=2, padding=1), nn.ReLU(), nn.Flatten())
        with torch.no_grad():
            size = self.grid(torch.zeros(1, CHANNELS, 30, 50)).shape[1]
        self.combine = nn.Sequential(nn.Linear(size+GLOBALS, 128), nn.ReLU())

    def forward(self, observations):
        return self.combine(torch.cat([self.grid(observations['grid']), observations['global']], dim=1))


def evaluate(model, dotnet, seconds, seeds, deterministic=False):
    env = TrafficEnv(dotnet=dotnet, seconds=seconds, seeds=seeds)
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
                    print('EVAL ' + json.dumps(result), flush=True)
                    break
    finally:
        env.close()
    return runs


class BudgetCallback(BaseCallback):
    def __init__(self, output, minutes):
        super().__init__()
        self.output, self.seconds = output, minutes*60
        self.started = self.last_print = self.last_save = time.perf_counter()
        self.commands = self.episodes = self.best = self.rejects = 0
        self.episode_results = []

    def _on_step(self):
        now = time.perf_counter()
        for info, done in zip(self.locals['infos'], self.locals['dones']):
            self.commands += int(info.get('command_completed', False))
            if done:
                self.episodes += 1
                self.best = max(self.best, info['trips'])
                self.rejects += info['rejected_actions']
                result = {k: info[k] for k in ['trips', 'seconds', 'rejected_actions', 'commands', 'scenario_seed']}
                result['terminated'] = not info.get('TimeLimit.truncated', False)
                result['truncated'] = bool(info.get('TimeLimit.truncated', False))
                self.episode_results.append(result)
                with (self.output / 'episodes.jsonl').open('a') as f:
                    f.write(json.dumps(result)+'\n')
        if now-self.last_print >= 30:
            status = dict(wall_seconds=round(now-self.started, 1), policy_steps=self.num_timesteps,
                          completed_commands=self.commands, episodes=self.episodes, best_training_score=self.best,
                          policy_steps_per_second=round(self.num_timesteps/(now-self.started), 1),
                          commands_per_second=round(self.commands/(now-self.started), 1))
            (self.output/'status.json').write_text(json.dumps(status, indent=2)+'\n')
            print('PROGRESS ' + json.dumps(status), flush=True)
            self.last_print = now
        if now-self.last_save >= 120:
            self.model.save(self.output/'latest')
            self.last_save = now
        return now-self.started < self.seconds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', default='dotnet')
    parser.add_argument('--minutes', type=float, default=30)
    parser.add_argument('--steps', type=int, default=10_000_000)
    parser.add_argument('--episode-seconds', type=int, default=3600)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--eval-episodes', type=int, default=3)
    args = parser.parse_args()
    if args.minutes <= 0 or args.steps < 1 or args.threads < 1 or not 1 <= args.eval_episodes <= 20:
        parser.error('Positive budgets required; evaluation episodes must be 1..20')
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    output = args.output or ROOT/'output/training'/datetime.now().strftime('%Y%m%d-%H%M%S')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = dict(schema=SCHEMA, simulator_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
                  dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
                  version='OriginalReference', city='LosAngeles', device='cpu', algorithm='MaskablePPO',
                  reward='tripsCompleted_after - tripsCompleted_before; no shaping',
                  tools=TOOLS, tick_interval=20, maximum_selection_decisions=4,
                  training_seeds=[1000, 1099], evaluation_seeds=[2000, 1999+args.eval_episodes],
                  created_utc=datetime.now(timezone.utc).isoformat(), arguments={k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()},
                  packages={name: importlib.metadata.version(name) for name in
                            ['torch', 'numpy', 'gymnasium', 'stable-baselines3', 'sb3-contrib']},
                  hyperparameters=dict(n_steps=256, batch_size=64, n_epochs=4, gamma=.999,
                                       learning_rate=.0003, ent_coef=.01, net_arch=[64]))
    (output/'config.json').write_text(json.dumps(config, indent=2)+'\n')
    # Preserve exact source even before a commit, alongside the revision metadata.
    for name in ['environment.py', 'train.py']:
        (output/name).write_text((Path(__file__).parent/name).read_text())
    env = Monitor(TrafficEnv(dotnet=args.dotnet, seconds=args.episode_seconds), str(output/'monitor.csv'),
                  info_keywords=('trips', 'seconds', 'rejected_actions'))
    try:
        if args.resume:
            previous_config = json.loads((args.resume.parent/'config.json').read_text())
            if previous_config['schema'] != SCHEMA or previous_config['arguments']['episode_seconds'] != args.episode_seconds:
                raise RuntimeError('Resume schema or episode duration mismatch')
            model = MaskablePPO.load(args.resume, env=env, device='cpu')
        else:
            model = MaskablePPO('MultiInputPolicy', env, device='cpu', seed=args.seed, verbose=0,
                                policy_kwargs=dict(features_extractor_class=GridEncoder, net_arch=[64], normalize_images=False),
                                **{k:v for k,v in config['hyperparameters'].items() if k != 'net_arch'})
        model.set_logger(configure(str(output), ['csv']))
        model.save(output/'initial')
        initial_parameters = torch.cat([p.detach().flatten().cpu() for p in model.policy.parameters()]).clone()
        torch.manual_seed(args.seed+1)
        before = evaluate(model, args.dotnet, args.episode_seconds, range(2000, 2000+args.eval_episodes))
        callback = BudgetCallback(output, args.minutes)
        started = time.perf_counter()
        interrupted = False
        try:
            model.learn(total_timesteps=args.steps, callback=callback, reset_num_timesteps=True)
        except KeyboardInterrupt:
            interrupted = True
        elapsed = time.perf_counter()-started
        model.save(output/'final')
        final_parameters = torch.cat([p.detach().flatten().cpu() for p in model.policy.parameters()])
        changed = bool(not torch.equal(initial_parameters, final_parameters))
        # Reload for evaluation: exercises checkpoint serialization, not only RAM state.
        restored = MaskablePPO.load(output/'final', device='cpu')
        torch.manual_seed(args.seed+1)
        after = evaluate(restored, args.dotnet, args.episode_seconds, range(2000, 2000+args.eval_episodes))
        torch.manual_seed(args.seed+1)
        greedy = evaluate(restored, args.dotnet, args.episode_seconds, range(2000, 2000+args.eval_episodes), deterministic=True)
        summary = dict(training_wall_seconds=elapsed, policy_steps=model.num_timesteps,
                       completed_commands=callback.commands, episodes=callback.episodes,
                       parameter_update_confirmed=changed, interrupted=interrupted,
                       policy_steps_per_second=model.num_timesteps/elapsed,
                       commands_per_second=callback.commands/elapsed,
                       best_training_score=callback.best, before=before, after=after, deterministic_after=greedy,
                       target_score=1000, target_met=any(r['trips'] >= 1000 for r in after+greedy))
        (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print('RESULT ' + json.dumps(summary), flush=True)
        print(f'Artifacts: {output}', flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()

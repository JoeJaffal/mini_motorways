"""Add driveway rotation and Finish to the reward-trained construction policy."""

import argparse
from functools import partial
import json
from pathlib import Path
from time import monotonic

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from torch import nn

import spare_road_ppo
from bend_ppo import Monitor, digest, write
from construction_practice import ACTIONS, EDGE_END, tile
from environment import DIRS
from hierarchy_rollout import policy_fingerprint
from spare_road_ppo import ExplorationFeatures, SpareRoadEnvironment, SpareRoadPolicy, TemperedHead
from visible_observation import WIDTH

OFFSETS = np.asarray(DIRS)
ROTATED = (np.arange(8)[:, None] + np.arange(8)) % 8
REMOVAL = np.arange(8)[None, :] == 4
DRIVEWAY_WIDTH = 20


class DrivewayEnvironment(SpareRoadEnvironment):
    def __init__(self, dll, worker=0, workers=1, exercise='driveway', seed_start=660000):
        super().__init__(dll, worker, workers, exercise)
        self.seed_start = seed_start
        self.observation_space.spaces['driveway'] = gym.spaces.Box(
            -2, 2, (8, DRIVEWAY_WIDTH), np.float32)
        self.action_space = gym.spaces.Discrete(ACTIONS)

    def _seed(self):
        return super()._seed() - 450000 + self.seed_start

    def reset(self, *, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)
        self.started_connected = self.env.connected()
        return obs, info

    def action_masks(self):
        return self.env.legal.copy()

    def _observation(self, observation):
        obs = super()._observation(observation)
        practice = self.env
        house = next(b for b in practice.raw['buildings'] if b['isHouse'])
        home = np.asarray(tile(house['cell']))
        targets = home + OFFSETS
        cells = targets[:, 1] * WIDTH + targets[:, 0]
        road = np.asarray(practice.raw['infrastructure']) == 1
        links = np.asarray(practice.raw['connections'])[cells]
        neighbors = targets[:, None] + OFFSETS[ROTATED]
        neighbor_cells = neighbors[..., 1] * WIDTH + neighbors[..., 0]
        delta = obs['anchors'][1] - np.asarray(practice.local(home)) - OFFSETS
        features = np.column_stack((
            np.arange(8) == house['drivewayDirection'], road[cells],
            ((links[:, None] >> ROTATED) & 1) * ~REMOVAL,
            road[neighbor_cells] * ~REMOVAL,
            (delta * OFFSETS).sum(axis=1) / 12,
            (delta * OFFSETS[:, ::-1] * [-1, 1]).sum(axis=1) / 12,
        )).astype(np.float32)
        return dict(obs, driveway=features)

    def step(self, action):
        obs, reward, done, truncated, info = super().step(action)
        return obs, reward, done, truncated, dict(
            info, started_connected=self.started_connected, action=int(action))


class DrivewayFeatures(ExplorationFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += 8 * DRIVEWAY_WIDTH

    def forward(self, observations):
        return torch.cat((super().forward(observations), observations['driveway'].flatten(1)), dim=1)


class DrivewayLatents(nn.Module):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def forward_actor(self, features):
        board, driveway = features.split((features.shape[1] - 8 * DRIVEWAY_WIDTH, 8 * DRIVEWAY_WIDTH), dim=1)
        return self.parent.forward_actor(board), driveway.reshape(-1, 8, DRIVEWAY_WIDTH)

    def forward_critic(self, features):
        return self.parent.forward_critic(features[:, :-8 * DRIVEWAY_WIDTH])

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class DrivewayHead(TemperedHead):
    def __init__(self):
        super().__init__()
        self.driveway = nn.Sequential(nn.Linear(DRIVEWAY_WIDTH, 32), nn.SiLU(), nn.Linear(32, 1))

    def forward(self, latent):
        board, driveway = latent
        roads = super().forward(board)
        rotations = self.driveway(driveway).squeeze(-1)
        finish = (rotations * driveway[..., 0]).sum(dim=1, keepdim=True)
        return torch.cat((finish, roads[:, 1:], rotations), dim=1)


class DrivewayPolicy(SpareRoadPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = DrivewayLatents(self.mlp_extractor)
        self.action_net = DrivewayHead()
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class DrivewayMonitor(Monitor):
    def _on_rollout_start(self):
        super()._on_rollout_start()
        self.cases = {'needs_rotation': [0, 0], 'already_connected': [0, 0]}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done:
                case = self.cases['already_connected' if info['started_connected'] else 'needs_rotation']
                case[0] += int(info['connected'])
                case[1] += 1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending.update(cases=self.cases)
        print(f'DRIVEWAY | rotate {self.cases["needs_rotation"]} | finish {self.cases["already_connected"]}', flush=True)


def verify(parent, policy, dll):
    env = DrivewayEnvironment(dll)
    try:
        for stage, seed in [('adjacent', 30000), ('bend', 32000), ('clear', 36200), ('obstacle', 38000)]:
            observation, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
            mask = env.action_masks()
            prior_obs = {key: observation[key] for key in parent.observation_space.spaces}
            with torch.inference_mode():
                prior = parent.get_distribution(parent.obs_to_tensor(prior_obs)[0], action_masks=mask[:EDGE_END])
                current = policy.get_distribution(policy.obs_to_tensor(observation)[0], action_masks=mask)
                torch.testing.assert_close(prior.distribution.probs, current.distribution.probs[:, :EDGE_END].cpu())
        for seed in (34000, 34001):
            env.reset(options=dict(stage='driveway', split='validation', layout_seed=seed))
            mask = env.action_masks()
            if not mask[0] or mask[1:EDGE_END].any() or not mask[EDGE_END:].any():
                raise RuntimeError('Unexpected native driveway mask')
            _, reward, done, truncated, info = env.step(0)
            if not done or truncated or reward != float(info['started_connected']):
                raise RuntimeError('Finish did not preserve the existing service state')
    finally:
        env.close()


def train(args):
    config = json.loads(args.checkpoint.with_name('config.json').read_text())
    if config['native_sha256'] != digest(args.dll) or config['source_sha256'] != digest(spare_road_ppo.__file__):
        raise ValueError('Parent host or source changed')
    parent = MaskablePPO.load(args.checkpoint, device='cpu')
    env = SubprocVecEnv([
        partial(DrivewayEnvironment, args.dll, i, args.workers, seed_start=args.seed_start)
        for i in range(args.workers)
    ], start_method='forkserver')
    try:
        model = MaskablePPO(
            DrivewayPolicy, env, learning_rate=args.learning_rate, n_steps=128, batch_size=128,
            n_epochs=4, gamma=1., gae_lambda=1., ent_coef=args.entropy, target_kl=.02,
            device=args.device, seed=args.seed,
            policy_kwargs=dict(features_extractor_class=DrivewayFeatures, normalize_images=False,
                               optimizer_kwargs={'eps': 1e-5}))
        missing, unexpected = model.policy.load_state_dict(parent.policy.state_dict(), strict=False)
        if unexpected or set(missing) != {f'action_net.driveway.{i}.{part}' for i in (0, 2)
                                          for part in ('weight', 'bias')}:
            raise RuntimeError('Unexpected difference from the PPO parent')
        for name, parameter in model.policy.named_parameters():
            parameter.requires_grad_(name.startswith(('action_net.driveway.', 'value_net.')))
        verify(parent.policy, model.policy, args.dll)
        args.output.mkdir(parents=True)
        write(args.output/'config.json', dict(
            kind='driveway-ppo', native_sha256=digest(args.dll), source_sha256=digest(__file__),
            parent=str(args.checkpoint), parent_sha256=digest(args.checkpoint),
            parent_fingerprint=policy_fingerprint(parent.policy), seed=args.seed,
            seed_start=args.seed_start, workers=args.workers, decisions=args.decisions,
            learning_rate=args.learning_rate, entropy=args.entropy, wall_seconds=args.wall_seconds,
            teacher_actions=False, optimizer='fresh Adam; train rotation/Finish and critic only'))
        model.save(args.output/'initial.zip')
        monitor = DrivewayMonitor(args.output, args.wall_seconds)
        try:
            model.learn(total_timesteps=args.decisions, callback=monitor, progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        verify(parent.policy, model.policy, args.dll)
        write(args.output/'status.json', dict(
            result=result, saved_decisions=monitor.completed_update_decisions,
            collected_decisions=model.num_timesteps, elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decisions', type=int, default=65536)
    parser.add_argument('--wall-seconds', type=int, default=480)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--seed-start', type=int, default=660000)
    parser.add_argument('--learning-rate', type=float, default=.0004)
    parser.add_argument('--entropy', type=float, default=.005)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    args = parser.parse_args()
    if min(args.decisions, args.workers, args.wall_seconds) < 1 or args.decisions % (128 * args.workers):
        parser.error('Use a positive whole-rollout decision budget')
    if args.output.exists():
        parser.error('Use a new output directory')
    torch.set_num_threads(2)
    train(args)


if __name__ == '__main__':
    main()

"""Terrain-conditioned Maskable PPO for longer obstruction detours."""

import argparse
from collections import deque
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

from bend_ppo import Monitor, digest, write
from clear_road_ppo import GEOMETRY_CHANNELS
from construction_practice import EDGE_END, endpoints
from driveway_ppo import DrivewayEnvironment, DrivewayFeatures, DrivewayPolicy
from edge_policy import EDGE_WIDTH
from environment import DIRS
from hierarchy_rollout import policy_fingerprint
from offset_ppo import layout_geometry
from pair_ppo import CommitmentPolicy, PairEnvironment, PairFeatures

BLOCKS = 3
TERRAIN_WIDTH = BLOCKS * 3 + 2
TERRAIN_INPUT = BLOCKS * 3 + 2
PHASES = ('-warm-spare', '-warm', '-spare', '')
TARGETS = ('obstacle-wide', 'obstacle-offset')


class TerrainEnvironmentMixin:
    def __init__(self, dll, worker=0, workers=1, target=None, seed_start=880000, temperature=2.,
                 phase=0, target_offset=0):
        super().__init__(dll, worker, workers, seed_start=seed_start)
        self.target = target
        self.phase = phase
        self.target_temperature = temperature
        self.target_offset = target_offset
        self.observation_space.spaces['terrain'] = gym.spaces.Box(-1, 12, (TERRAIN_INPUT,), np.float32)

    def set_phase(self, phase):
        self.phase = phase

    def _terrain_seed(self, stage):
        if not self.target_offset:
            return self._seed()
        for _ in range(128):
            seed = self._seed()
            observation = self.env.host.call(command='reset', version='OriginalReference', practice=True,
                                             practiceStage='curriculum-' + stage,
                                             practiceSplit='train', seed=seed)['observation']
            if layout_geometry(observation)[1] == self.target_offset:
                return seed
        raise RuntimeError('Could not sample a layout with the requested lateral offset')

    def reset(self, *, seed=None, options=None):
        training = options is None
        self.episode_phase = self.phase if training else -1
        if training:
            stage = self.target + PHASES[self.phase] if self.target in TARGETS else self.target
            options = dict(stage=stage, split='train', layout_seed=self._terrain_seed(stage))
        obs, info = super().reset(seed=seed, options=options)
        if training and self.target in TARGETS:
            self.episode_temperature = 1. + (self.target_temperature - 1.) * (1. - self.phase / 4)
            obs = self._with_temperature(obs)
            self.env.edit_limit += 1
        elif training and self.target == 'obstacle':
            self.env.edit_limit += 1
        return obs, info

    def _observation(self, observation):
        obs = super()._observation(observation)
        practice = self.env
        y, x = np.where(np.asarray(practice.raw['terrain'])[practice.cells] == 2)
        if len(x) > BLOCKS:
            raise RuntimeError('Terrain pilot supports at most three visible blocked tiles')
        terrain = np.zeros((BLOCKS, 3), dtype=np.float32)
        terrain[:len(x)] = np.column_stack((x, y, np.ones(len(x))))
        heading = DIRS[practice.shop['drivewayDirection']] if practice.shop is not None else (0, 0)
        return dict(obs, terrain=np.concatenate((terrain.ravel(), np.asarray(heading, dtype=np.float32))))

    def step(self, action):
        obs, reward, ended, truncated, info = super().step(action)
        return obs, reward, ended, truncated, dict(
            info, target=self.target, terrain_phase=self.episode_phase, native_stage=self.env.stage)


class TerrainDriveEnvironment(TerrainEnvironmentMixin, DrivewayEnvironment):
    pass


class TerrainPairEnvironment(TerrainEnvironmentMixin, PairEnvironment):
    pass


class TerrainFeatureMixin:
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += TERRAIN_INPUT

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['terrain']), dim=1)


class TerrainDriveFeatures(TerrainFeatureMixin, DrivewayFeatures):
    pass


class TerrainPairFeatures(TerrainFeatureMixin, PairFeatures):
    pass


class TerrainLatents(nn.Module):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def forward_actor(self, features):
        return self.parent.forward_actor(features[:, :-TERRAIN_INPUT]), features[:, -TERRAIN_INPUT:]

    def forward_critic(self, features):
        return self.parent.forward_critic(features[:, :-TERRAIN_INPUT])

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class TerrainHead(nn.Module):
    def __init__(self, base, paired, minimum_blocked_tiles):
        super().__init__()
        self.base = base
        self.paired = paired
        self.minimum_blocked_tiles = minimum_blocked_tiles
        pairs = torch.tensor([endpoints(action) for action in range(1, EDGE_END)], dtype=torch.float32)
        self.register_buffer('midpoint', pairs.mean(dim=1), persistent=False)
        self.register_buffer('edge_direction', pairs[:, 1] - pairs[:, 0], persistent=False)
        self.residual = nn.Sequential(
            nn.Linear(EDGE_WIDTH + GEOMETRY_CHANNELS + TERRAIN_WIDTH, 48), nn.SiLU(),
            nn.Linear(48, 1))
        nn.init.zeros_(self.residual[-1].weight)
        nn.init.zeros_(self.residual[-1].bias)

    def forward(self, latent):
        board, terrain = latent
        prior = self.base(board)
        road_and_driveway = board[0] if self.paired else board
        edges, temperature = road_and_driveway[0]
        blocks = terrain[:, :-2].reshape(-1, BLOCKS, 3)
        heading = terrain[:, -2:]
        side = heading.flip(dims=(1,)) * heading.new_tensor([-1, 1])
        delta = blocks[:, None, :, :2] - self.midpoint[None, :, None]
        visible = blocks[:, :, 2]
        coordinates = torch.stack((
            (delta * heading[:, None, None]).sum(-1) / 4,
            (delta * side[:, None, None]).sum(-1) / 4,
            torch.ones_like(delta[..., 0])),
            dim=-1) * visible[:, None, :, None]
        axis = torch.stack(((self.edge_direction * heading[:, None]).sum(-1),
                            (self.edge_direction * side[:, None]).sum(-1)), dim=-1)
        features = torch.cat((edges, coordinates.flatten(2), axis), dim=-1)
        supported = visible.sum(dim=1, keepdim=True) >= self.minimum_blocked_tiles
        residual = self.residual(features).squeeze(-1) * supported / temperature
        return torch.cat((prior[:, :1], prior[:, 1:EDGE_END] + residual, prior[:, EDGE_END:]), dim=1)


class TerrainPolicyMixin:
    paired = False

    def __init__(self, *args, minimum_blocked_tiles=1, **kwargs):
        self.minimum_blocked_tiles = minimum_blocked_tiles
        super().__init__(*args, **kwargs)

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = TerrainLatents(self.mlp_extractor)
        self.action_net = TerrainHead(self.action_net, self.paired, self.minimum_blocked_tiles)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class TerrainDrivePolicy(TerrainPolicyMixin, DrivewayPolicy):
    pass


class TerrainPairPolicy(TerrainPolicyMixin, CommitmentPolicy):
    paired = True


class TerrainMonitor(Monitor):
    def __init__(self, output, seconds, phase=0, previous_steps=0):
        super().__init__(output, seconds)
        self.phase = phase
        self.completed_update_decisions = previous_steps
        self.window = deque(maxlen=4)

    def _on_rollout_start(self):
        prior = self.pending
        super()._on_rollout_start()
        if prior is not None:
            self.window.append(prior['by_target'])
        if self.phase < len(PHASES) - 1 and len(self.window) == self.window.maxlen:
            totals = [tuple(sum(entry[k][i] for entry in self.window) for i in (0, 1)) for k in TARGETS]
            if all(games >= 40 and wins / games >= .85 for wins, games in totals):
                self.model.save(self.output/f'passed-phase-{self.phase}.zip')
                self.phase += 1
                self.window.clear()
                self.training_env.env_method('set_phase', self.phase)
                print(f'CURRICULUM | phase {self.phase} | modifiers {PHASES[self.phase]!r}', flush=True)
        self.by_target = {stage: [0, 0] for stage in (*TARGETS, 'obstacle')}
        self.hard = {'-2': [0, 0], '2': [0, 0]}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done and info['terrain_phase'] == self.phase:
                counts = self.by_target[info['target']]
                counts[0] += int(info['connected'])
                counts[1] += 1
                if info['target'] == TARGETS[1] and abs(info['offset']) == 2:
                    counts = self.hard[str(info['offset'])]
                    counts[0] += int(info['connected'])
                    counts[1] += 1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending.update(phase=self.phase, by_target=self.by_target, hard_offsets=self.hard)
        print('TERRAIN | ' + ' | '.join(f'{key} {a}/{b}' for key, (a, b) in self.by_target.items()), flush=True)
        if any(games for _, games in self.hard.values()):
            print(f'HARD OFFSETS | {self.hard}', flush=True)


def feasibility(dll, count=8, full_only=False):
    env = TerrainDriveEnvironment(dll)
    records = []
    try:
        for target, first in zip(TARGETS, (50000, 51000)):
            for phase in ('',) if full_only else PHASES:
                for seed in range(first, first + count):
                    stage = target + phase
                    env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
                    practice = env.env
                    practice.edit_limit += 1
                    stock = practice.inventory
                    for action in practice.reference():
                        if not env.action_masks()[action]:
                            raise RuntimeError(f'Illegal feasibility witness in {stage}, seed {seed}')
                        _, reward, done, truncated, info = env.step(action)
                        if done:
                            break
                    trips, _ = practice.deliveries()
                    if truncated or reward != 1 or trips < 3 or info['road_units_spent'] > stock:
                        raise RuntimeError(f'Unsolved feasibility witness in {stage}, seed {seed}')
                    records.append(dict(stage=stage, seed=seed, stock=stock,
                                        spent=info['road_units_spent'], trips=trips))
    finally:
        env.close()
    return records


def verify(dll, parent, policy, env_factory):
    env = env_factory(dll)
    try:
        for stage, seed in [('adjacent', 30000), ('driveway', 34000), ('clear', 36200),
                            ('obstacle', 38000), ('obstacle-wide', 50000), ('obstacle-offset', 51000)]:
            obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
            mask = env.action_masks()
            with torch.inference_mode():
                a = parent.obs_to_tensor({key: obs[key] for key in parent.observation_space.spaces})[0]
                b = policy.obs_to_tensor(obs)[0]
                previous = parent.get_distribution(a, action_masks=mask).distribution.probs
                current = policy.get_distribution(b, action_masks=mask).distribution.probs.cpu()
                torch.testing.assert_close(previous, current)
    finally:
        env.close()


def train(args):
    if args.resume:
        prior_config = json.loads(args.checkpoint.with_name('config.json').read_text())
        if prior_config['native_sha256'] != digest(args.dll):
            raise ValueError('Resume requires the previous native host')
    else:
        feasibility_results = feasibility(args.dll)
    parent = MaskablePPO.load(args.checkpoint, device='cpu')
    paired = 'parcel_colors' in parent.observation_space.spaces
    policy_class, feature_class, env_class = (TerrainPairPolicy, TerrainPairFeatures, TerrainPairEnvironment) if paired else (
        TerrainDrivePolicy, TerrainDriveFeatures, TerrainDriveEnvironment)
    if args.hard_offsets:
        assignments = [(TARGETS[0], 0)] * 2 + [(TARGETS[1], 0)] * 4
        assignments += [(TARGETS[1], -2), (TARGETS[1], 2)] * 5
    else:
        assignments = ([(TARGETS[0], 0)] * (4 if args.resume else 7)
                       + [(TARGETS[1], 0)] * (10 if args.resume else 7) + [('obstacle', 0)] * 2)
    phase = 3 if args.resume else 0
    seed_start = 1180000 if args.hard_offsets else 980000 if args.resume else 880000
    env = SubprocVecEnv([partial(env_class, args.dll, i, len(assignments), stage, seed_start=seed_start,
                                 temperature=args.temperature, phase=phase, target_offset=offset)
                        for i, (stage, offset) in enumerate(assignments)], start_method='forkserver')
    try:
        if args.resume:
            model = MaskablePPO.load(args.checkpoint, env=env, device=args.device)
            if (policy_fingerprint(model.policy) != policy_fingerprint(parent.policy)
                    or model.num_timesteps != parent.num_timesteps
                    or not model.policy.optimizer.state_dict()['state']):
                raise RuntimeError('Resume failed to restore weights, counters or Adam state')
        else:
            model = MaskablePPO(
                policy_class, env, learning_rate=.0004, n_steps=128, batch_size=128, n_epochs=4,
                gamma=1., gae_lambda=1., ent_coef=.008, target_kl=.03, device=args.device, seed=42,
                policy_kwargs=dict(features_extractor_class=feature_class, normalize_images=False,
                                   optimizer_kwargs={'eps': 1e-5}))
            parent_weights = {
                key.replace('action_net.', 'action_net.base.', 1) if key.startswith('action_net.') else key: val
                for key, val in parent.policy.state_dict().items()}
            missing, unexpected = model.policy.load_state_dict(parent_weights, strict=False)
            if unexpected or not missing or any(not name.startswith('action_net.residual.') for name in missing):
                raise RuntimeError('Unexpected warm-start weight difference')
        for name, parameter in model.policy.named_parameters():
            parameter.requires_grad_(name.startswith(('action_net.residual.', 'value_net.')))
        verify(args.dll, parent.policy, model.policy, env_class)
        args.output.mkdir(parents=True)
        if not args.resume:
            write(args.output/'feasibility.json', feasibility_results)
        write(args.output/'config.json', dict(
            kind='terrain-ppo', native_sha256=digest(args.dll), source_sha256=digest(__file__),
            parent=str(args.checkpoint), parent_sha256=digest(args.checkpoint),
            parent_fingerprint=policy_fingerprint(parent.policy), seed=42, workers=assignments,
            decisions=args.decisions, wall_seconds=args.wall_seconds, teacher_actions=False,
            starting_phase=phase, starting_decisions=model.num_timesteps, seed_start=seed_start,
            training_only_modifiers=PHASES, temperature=args.temperature, resumed_adam=args.resume))
        model.save(args.output/'initial.zip')
        monitor = TerrainMonitor(args.output, args.wall_seconds, phase, model.num_timesteps)
        try:
            model.learn(total_timesteps=args.decisions, reset_num_timesteps=not args.resume,
                        callback=monitor, progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        write(args.output/'status.json', dict(result=result, phase=monitor.phase,
            saved_decisions=monitor.completed_update_decisions, collected_decisions=model.num_timesteps,
            elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


def save_three_block_variant(args):
    trained = MaskablePPO.load(args.checkpoint, device='cpu')
    if 'terrain' not in trained.observation_space.spaces:
        raise ValueError('The branch guard requires a terrain checkpoint')
    kwargs = dict(trained.policy_kwargs, minimum_blocked_tiles=3)
    policy_class = TerrainPairPolicy if 'parcel_colors' in trained.observation_space.spaces else TerrainDrivePolicy
    guarded = MaskablePPO.load(args.checkpoint, device='cpu',
                               custom_objects=dict(policy_class=policy_class, policy_kwargs=kwargs))
    before = policy_fingerprint(trained.policy)
    if policy_fingerprint(guarded.policy) != before or guarded.num_timesteps != trained.num_timesteps:
        raise RuntimeError('The branch guard changed learned parameters or counters')
    guarded.save(args.output)
    write(args.output.with_suffix('.json'), dict(
        source_checkpoint=str(args.checkpoint), source_sha256=digest(args.checkpoint),
        output_sha256=digest(args.output), parameter_fingerprint=before, minimum_blocked_tiles=3,
        saved_decisions=guarded.num_timesteps, trained=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decisions', type=int, default=262144)
    parser.add_argument('--wall-seconds', type=int, default=900)
    parser.add_argument('--temperature', type=float, default=2.)
    parser.add_argument('--resume', action='store_true', help='Continue on full original-stock layouts')
    parser.add_argument('--hard-offsets', action='store_true', help='Rebalance full-stock continuation toward offsets ±2')
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--save-three-block-variant', action='store_true')
    parser.add_argument('--verify-count', type=int, default=8)
    parser.add_argument('--verify-full-only', action='store_true')
    args = parser.parse_args()
    if min(args.decisions, args.wall_seconds, args.verify_count) < 1 or args.decisions % 2048 or args.output.exists():
        parser.error('Use a fresh output and a whole-rollout budget')
    if not 1 <= args.temperature <= 6:
        parser.error('Temperature must be between 1 and 6')
    if args.hard_offsets and not args.resume:
        parser.error('Hard-offset balancing requires a trained terrain checkpoint')
    torch.set_num_threads(2)
    if args.save_three_block_variant:
        if args.output.suffix != '.zip' or args.output.with_suffix('.json').exists():
            parser.error('Use a fresh .zip path and evidence filename')
        save_three_block_variant(args)
    elif args.verify_only:
        records = feasibility(args.dll, args.verify_count, args.verify_full_only)
        write(args.output, records)
        print(f'{len(records)} legal native witness routes delivered at least three trips')
    else:
        train(args)


if __name__ == '__main__':
    main()

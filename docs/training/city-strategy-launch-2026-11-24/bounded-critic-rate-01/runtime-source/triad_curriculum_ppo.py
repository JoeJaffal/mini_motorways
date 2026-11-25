"""Reward-only PPO from short road stubs to empty competing-home boards."""

import argparse
from collections import deque
from functools import partial
from pathlib import Path
from time import monotonic

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from torch import nn

from bend_ppo import Monitor, digest, write
from construction_practice import EDGE_END, advance, endpoints, inside
from environment import DIRS
from evaluate_construction_ppo import SEEDS, evaluate
from evaluate_triad_ppo import MULTIPLE_STAGES, STAGES, feasibility
from hierarchy_rollout import policy_fingerprint
from pair_ppo import COLORS
from triad_ppo import SelectionEnvironment, SelectionFeatures, SelectionHead, SelectionPolicy
from visible_observation import WIDTH

STUBS = {
    count: tuple(f'{stage}-stub{count}' for stage in STAGES)
    for count in (1, 2)
}
PHASES = {2: STUBS[2], 1: STUBS[1], 0: STAGES}
UNEVEN = tuple(f'{stage}-uneven' for stage in STAGES)
SEEDS.update({stage: 64000 + 1000 * count for count, pair in STUBS.items() for stage in pair})
SEEDS.update({stage: 68000 for stage in UNEVEN})
FRAME_INPUT = 11  # destination heading, stock, and the two sets of outside-approach positions
NETWORK_INPUT = 3 * 12 * 12 + 6


def existing_network(practice, anchors, heading):
    """Mark current links attached to each approach and measure their extent."""
    road = practice.raw['connections']
    rooted = np.zeros((3, 12, 12), dtype=np.float32)
    fronts = anchors.copy()
    h = np.asarray(heading)
    for index, anchor in enumerate(anchors):
        root = tuple(map(int, anchor))
        if not inside(root):
            continue
        seen = {root}
        pending = [root]
        while pending:
            x, y = pending.pop()
            rooted[index, y, x] = 1
            gx, gy = practice.world((x, y))
            mask = road[gy * WIDTH + gx]
            for direction in range(8):
                if not mask & (1 << direction):
                    continue
                neighbor = advance((x, y), direction)
                if inside(neighbor) and neighbor not in seen:
                    bx, by = practice.world(neighbor)
                    if road[by * WIDTH + bx] & (1 << ((direction + 4) % 8)):
                        seen.add(neighbor)
                        pending.append(neighbor)
        cells = np.array(sorted(seen), dtype=np.float32)
        progress = (cells @ h) * (1 if index == 2 else -1)
        fronts[index] = cells[progress == progress.max()].mean(axis=0)
    return np.concatenate((rooted.ravel(), fronts.ravel()))


class CurriculumEnvironment(SelectionEnvironment):
    def __init__(self, dll, worker=0, workers=1, role='target', phase=2, seed_start=1350000,
                 use_frame=False, use_network=False):
        super().__init__(dll, worker, workers, seed_start=seed_start)
        self.role = role
        self.side = worker % 2
        self.phase = phase
        self.use_frame = use_frame
        self.use_network = use_network
        if use_frame:
            self.observation_space.spaces['route_frame'] = gym.spaces.Box(-2, 13, (FRAME_INPUT,), np.float32)
        if use_network:
            self.observation_space.spaces['route_network'] = gym.spaces.Box(-2, 13, (NETWORK_INPUT,), np.float32)

    def set_phase(self, phase):
        self.phase = phase

    def reset(self, *, seed=None, options=None):
        self.episode_phase = self.phase
        if options is None:
            stages = {'target': PHASES[self.phase], 'empty': STAGES, 'rehearsal': MULTIPLE_STAGES[3]}
            options = dict(stage=stages[self.role][self.side], split='train', layout_seed=self._seed())
        return super().reset(seed=seed, options=options)

    def _observation(self, observation):
        obs = super()._observation(observation)
        if not self.use_frame:
            return obs
        practice = self.env
        heading = DIRS[practice.shop['drivewayDirection']] if practice.shop is not None else (0, 0)
        result = dict(obs, route_frame=np.array([
            *heading, practice.raw['inventory'][0] / 8.,
            *obs['anchors'].ravel(), *obs['alternate_anchors'].ravel(),
        ], dtype=np.float32))
        if self.use_network:
            anchors = np.stack((obs['anchors'][0], obs['alternate_anchors'][0], obs['anchors'][1]))
            result['route_network'] = existing_network(practice, anchors, heading)
        return result

    def step(self, action):
        obs, reward, done, truncated, info = super().step(action)
        return obs, reward, done, truncated, dict(
            info, curriculum_role=self.role, curriculum_phase=self.episode_phase, curriculum_side=self.side)


class FrameFeatures(SelectionFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += FRAME_INPUT

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['route_frame']), dim=1)


class NetworkFeatures(FrameFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += NETWORK_INPUT

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['route_network']), dim=1)


class FrameLatents(nn.Module):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def forward_actor(self, features):
        return self.parent.forward_actor(features[:, :-FRAME_INPUT]), features[:, -FRAME_INPUT:]

    def forward_critic(self, features):
        return self.parent.forward_critic(features[:, :-FRAME_INPUT])

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class NetworkLatents(nn.Module):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def forward_actor(self, features):
        old, frame = self.parent.forward_actor(features[:, :-NETWORK_INPUT])
        return old, frame, features[:, -NETWORK_INPUT:]

    def forward_critic(self, features):
        return self.parent.forward_critic(features[:, :-NETWORK_INPUT])

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class FrameHead(SelectionHead):
    def __init__(self, base):
        super().__init__(base)
        pairs = torch.tensor([endpoints(a) for a in range(1, EDGE_END)], dtype=torch.float32)
        self.register_buffer('pairs', pairs, persistent=False)
        self.frame = nn.Sequential(nn.Linear(10, 48), nn.SiLU(), nn.Linear(48, 32), nn.SiLU(), nn.Linear(32, 1))
        nn.init.zeros_(self.frame[-1].weight)
        nn.init.zeros_(self.frame[-1].bias)

    def forward(self, latent):
        old, frame = latent
        features, _, _ = self.geometry(old, frame)
        return self.score(old, self.frame(features).squeeze(-1))

    def geometry(self, old, frame):
        heading = frame[:, :2]
        side = heading.flip(dims=(1,)) * heading.new_tensor([-1, 1])
        anchors = frame[:, 3:].reshape(-1, 2, 2, 2)
        home, shop = anchors.unbind(dim=2)
        lateral_sign = torch.where(((home-shop)*side[:, None]).sum(dim=-1) < 0., -1., 1.)
        lateral = side[:, None] * lateral_sign[..., None]
        axis = torch.stack((heading[:, None].expand_as(lateral), lateral), dim=-1)
        relative = self.pairs[None, None] - shop[:, :, None, None]
        projected = torch.einsum('btepc,btcd->btepd', relative, axis) / 6.
        first, second = projected.unbind(3)
        delta = second - first
        reverse = (delta[..., 0] < 0) | ((delta[..., 0] == 0) & (delta[..., 1] < 0))
        delta = torch.where(reverse[..., None], -delta, delta) * 6.
        target = torch.einsum('btc,btcd->btd', home-shop, axis) / 6.
        midpoint = (first + second) * .5
        home_delta = target[:, :, None] - midpoint
        role = old[2][:, 1:].reshape(-1, 2, 2, COLORS).prod(dim=2).sum(dim=-1)
        stock = frame[:, None, None, 2].expand_as(midpoint[..., 0])
        extra = torch.cat((midpoint, home_delta, delta,
                           target[:, :, None].expand_as(midpoint),
                           stock[..., None], role[:, :, None, None].expand_as(stock[..., None])), dim=-1)
        return extra, axis, self.pairs.mean(dim=1)


class NetworkHead(FrameHead):
    def __init__(self, base):
        super().__init__(base)
        coordinates = self.pairs.long()
        flat = coordinates[..., 1] * 12 + coordinates[..., 0]
        valid = ((coordinates >= 0) & (coordinates < 12)).all(dim=-1)
        self.register_buffer('cell_indices', torch.where(valid, flat, 144), persistent=False)
        self.network = nn.Sequential(nn.Linear(20, 64), nn.SiLU(), nn.Linear(64, 48), nn.SiLU(), nn.Linear(48, 1))
        nn.init.zeros_(self.network[-1].weight)
        nn.init.zeros_(self.network[-1].bias)

    def forward(self, latent):
        old, frame, network = latent
        geometry, axis, midpoint = self.geometry(old, frame)
        grids = torch.nn.functional.pad(network[:, :-6].reshape(-1, 3, 144), (0, 1))
        fronts = network[:, -6:].reshape(-1, 3, 2)
        homes = fronts[:, :2]
        shop = fronts[:, 2:]
        relative = torch.stack((homes[:, :, None] - midpoint,
                                shop.expand_as(homes)[:, :, None] - midpoint), dim=3)
        displacement = torch.einsum('btepc,btcd->btepd', relative, axis).flatten(3) / 6.
        occupancy = grids[:, :, self.cell_indices]
        home = occupancy[:, :2]
        destination = occupancy[:, 2:3].expand_as(home)
        other = home.flip(dims=(1,))
        marks = torch.cat((home, destination, other), dim=-1)
        features = torch.cat((geometry, displacement, marks), dim=-1)
        return self.score(old, self.frame(geometry).squeeze(-1) + self.network(features).squeeze(-1))


class FramePolicy(SelectionPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = FrameLatents(self.mlp_extractor)
        self.action_net = FrameHead(self.action_net.base)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class NetworkPolicy(FramePolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = NetworkLatents(self.mlp_extractor)
        self.action_net = NetworkHead(self.action_net.base)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class CurriculumMonitor(Monitor):
    def __init__(self, output, seconds, previous, phase):
        super().__init__(output, seconds)
        self.completed_update_decisions = previous
        self.phase = phase
        self.rollouts = deque(maxlen=3)
        self.phase_rollouts = 0
        self.total_rollouts = 0

    def _on_rollout_start(self):
        previous = self.pending
        super()._on_rollout_start()
        if previous is not None:
            self.rollouts.append(previous['target_sides'])
            self.phase_rollouts += 1
            self.total_rollouts += 1
            if self.total_rollouts % 16 == 0:
                self.model.save(self.output/f'rollout-{self.total_rollouts}.zip')
            if self.phase > 0 and self.phase_rollouts >= 6:
                sides = [[sum(row[str(s)][i] for row in self.rollouts) for i in (0, 1)] for s in (0, 1)]
                passed = all(n >= 25 and wins/n >= .85 for wins, n in sides)
                if passed or self.phase_rollouts >= 20:
                    self.model.save(self.output/f'phase-{self.phase}-boundary.zip')
                    self.phase -= 1
                    self.rollouts.clear()
                    self.phase_rollouts = 0
                    self.training_env.env_method('set_phase', self.phase)
                    print(f'CURRICULUM | phase {self.phase} | {"gate passed" if passed else "advance at rollout cap"}',
                          flush=True)
        self.sides = {str(side): [0, 0] for side in (0, 1)}
        self.counts = {}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if not done:
                continue
            case = self.counts.setdefault(info['case'], [0, 0])
            case[0] += int(info['connected'])
            case[1] += 1
            if info['curriculum_role'] == 'target' and info['curriculum_phase'] == self.phase:
                group = self.sides[str(info['curriculum_side'])]
                group[0] += int(info['connected'])
                group[1] += 1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending.update(phase=self.phase, target_sides=self.sides, cases=self.counts)
        print(f'PHASE {self.phase} | ' + ' | '.join(
            f'{case} {wins}/{n}' for case, (wins, n) in sorted(self.counts.items())), flush=True)


def verify_policy(parent, child, dll):
    spaces = child.observation_space.spaces
    env = CurriculumEnvironment(dll, use_frame='route_frame' in spaces, use_network='route_network' in spaces)
    try:
        for stage, seed in [('pair-triad-left', 54200), ('pair-triad-right-stub1', 65000),
                            ('pair-triad-left-stub2', 66000), ('pair-triad-right-triple', 58000),
                            ('driveway', 34001), ('clear', 36200), ('pair-homes', 42000)]:
            obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
            mask = env.action_masks()
            with torch.inference_mode():
                a = parent.obs_to_tensor({k: obs[k] for k in parent.observation_space.spaces})[0]
                b = child.obs_to_tensor(obs)[0]
                p = parent.get_distribution(a, action_masks=mask).distribution.probs
                q = child.get_distribution(b, action_masks=mask).distribution.probs.cpu()
                torch.testing.assert_close(p, q, atol=2e-6, rtol=2e-5)
    finally:
        env.close()


def train(args):
    parent = MaskablePPO.load(args.checkpoint, device='cpu')
    parent_frame = 'route_frame' in parent.observation_space.spaces
    parent_network = 'route_network' in parent.observation_space.spaces
    network = parent_network or args.network
    frame = parent_frame or args.frame or network
    adding_features = (frame and not parent_frame) or (network and not parent_network)
    roles = ['target'] * 10 + ['empty'] * 2 + ['rehearsal'] * 4
    env = SubprocVecEnv([partial(CurriculumEnvironment, args.dll, i, len(roles), role, args.phase,
                                 args.seed_start, frame, network)
                        for i, role in enumerate(roles)], start_method='forkserver')
    try:
        if adding_features:
            actor, encoder = (NetworkPolicy, NetworkFeatures) if network else (FramePolicy, FrameFeatures)
            model = MaskablePPO(
                actor, env, learning_rate=args.learning_rate, n_steps=128, batch_size=128, n_epochs=4,
                gamma=1., gae_lambda=1., ent_coef=args.entropy, target_kl=.02, device=args.device, seed=args.seed,
                policy_kwargs=dict(features_extractor_class=encoder, normalize_images=False,
                                   optimizer_kwargs={'eps': 1e-5}))
            missing, unexpected = model.policy.load_state_dict(parent.policy.state_dict(), strict=False)
            if unexpected or not missing or any(not k.startswith(('action_net.frame.', 'action_net.network.'))
                                                for k in missing):
                raise RuntimeError('Unexpected weights changed in frame adaptation')
            model.num_timesteps = parent.num_timesteps
            model._n_updates = parent._n_updates
        else:
            model = MaskablePPO.load(args.checkpoint, env=env, device=args.device,
                                     custom_objects=dict(learning_rate=args.learning_rate, ent_coef=args.entropy))
            if (policy_fingerprint(model.policy) != policy_fingerprint(parent.policy)
                    or model.num_timesteps != parent.num_timesteps
                    or not model.policy.optimizer.state_dict()['state']):
                raise RuntimeError('Checkpoint state was not restored')
        verify_policy(parent.policy, model.policy, args.dll)
        spatial = ('action_net.frame.', 'action_net.network.')
        trainable = ('action_net.residual.', 'action_net.affinity.', 'value_net.', *spatial)
        if args.frame_only:
            trainable = ('value_net.', *spatial)
        for key, parameter in model.policy.named_parameters():
            parameter.requires_grad_(key.startswith(trainable))
        args.output.mkdir(parents=True)
        write(args.output/'config.json', dict(
            native_sha256=digest(args.dll), parent=str(args.checkpoint), parent_sha256=digest(args.checkpoint),
            source_sha256=digest(__file__), teacher_actions=False, initial_phase=args.phase,
            starting_decisions=model.num_timesteps, roles=roles, planned_decisions=args.decisions,
            seed_start=args.seed_start, seed=args.seed, learning_rate=args.learning_rate, entropy=args.entropy,
            frame=frame, network=network, frame_only=args.frame_only, restored_adam=not adding_features,
            reward='1 for connecting the matching home within original native road stock, otherwise 0'))
        model.save(args.output/'initial.zip')
        monitor = CurriculumMonitor(args.output, args.wall_seconds, model.num_timesteps, args.phase)
        try:
            model.learn(total_timesteps=args.decisions, reset_num_timesteps=False,
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('train', 'evaluate', 'verify'))
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', type=int, choices=(0, 1, 2, 3, 4), default=2,
                        help='2 or 1 stubs, 0 empty, 3 earlier three-gap repairs, 4 unequal home distances')
    parser.add_argument('--decisions', type=int, default=131072)
    parser.add_argument('--wall-seconds', type=int, default=900)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--device', default='cuda', choices=('cuda', 'cpu'))
    parser.add_argument('--frame', action='store_true')
    parser.add_argument('--network', action='store_true', help='Add features about the visible built network')
    parser.add_argument('--frame-only', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--seed-start', type=int, default=1350000)
    parser.add_argument('--learning-rate', type=float, default=.0007)
    parser.add_argument('--entropy', type=float, default=.002)
    args = parser.parse_args()
    if (min(args.count, args.workers, args.decisions, args.wall_seconds) < 1
            or args.offset < 0 or args.decisions % 2048 or args.output.exists()):
        parser.error('Use positive counts, whole rollouts, and a new output path')
    if args.mode != 'verify' and args.checkpoint is None:
        parser.error('A saved checkpoint is required')
    torch.set_num_threads(2)
    if args.mode == 'train':
        if args.phase not in PHASES or args.frame_only and not (args.frame or args.network):
            parser.error('Invalid training options')
        train(args)
    elif args.mode == 'verify':
        rows = (feasibility(args.dll, UNEVEN, args.count, empty_stages=UNEVEN) if args.phase == 4
                else feasibility(args.dll, STUBS[2] + STUBS[1], args.count))
        write(args.output, dict(native_sha256=digest(args.dll), rows=rows))
        print(f'{len(rows)} fixtures passed the native delivery gate', flush=True)
    else:
        model = MaskablePPO.load(args.checkpoint, device='cpu')
        use_frame = 'route_frame' in model.observation_space.spaces
        stages = UNEVEN if args.phase == 4 else MULTIPLE_STAGES[3] if args.phase == 3 else PHASES[args.phase]
        use_network = 'route_network' in model.observation_space.spaces
        report = evaluate(model, lambda: CurriculumEnvironment(args.dll, use_frame=use_frame,
                                                                  use_network=use_network),
                          stages, args.count, args.offset, args.workers)
        write(args.output, dict(report, checkpoint_sha256=digest(args.checkpoint),
                                native_sha256=digest(args.dll), runner_sha256=digest(__file__)))


if __name__ == '__main__':
    main()

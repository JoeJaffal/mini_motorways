"""Reward-only Finish versus Build on isolated native building pairs."""

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

import driveway_ppo
from bend_ppo import Monitor, compact_observation, digest, write
from connection_practice import ARENA_SIZE
from construction_practice import ACTIONS, EDGE_END, ConstructionPractice, advance, tile
from driveway_ppo import DrivewayEnvironment, DrivewayFeatures, DrivewayHead, DrivewayPolicy
from edge_policy import EDGE_SLOTS
from environment import CELLS, DIRS
from hierarchy_rollout import policy_fingerprint
from visible_observation import HEIGHT, WIDTH

CASES = ('match', 'mismatch', 'homes', 'destinations', 'blue-red')
COLORS = 5
PAIR_FEATURES = COLORS * 2 + EDGE_SLOTS
local_y, local_x = np.mgrid[:ARENA_SIZE, :ARENA_SIZE]
PAIR_INSIDE = np.stack([(local_x + dx >= 0) & (local_x + dx < ARENA_SIZE)
                        & (local_y + dy >= 0) & (local_y + dy < ARENA_SIZE)
                        for dx, dy in DIRS[:4]], axis=-1)


class PairPractice(ConstructionPractice):
    commit_after_build = False

    def reset_pair(self, case, split, seed):
        self.stage, self.case, self.seed = 'pair-' + case, case, seed
        self.edits = 0
        result = self.call(command='reset', version='OriginalReference', practice=True,
                           practiceStage='curriculum-' + self.stage, practiceSplit=split, seed=seed)
        if not result['accepted'] or result['terminated'] or self.raw['time'] != 0:
            raise RuntimeError('Expected a fresh native pair layout')
        buildings = self.raw['buildings']
        if len(buildings) != 2:
            raise RuntimeError('Pair curriculum requires two real parcels')
        self.house = next((b for b in buildings if b['isHouse']), None)
        self.shop = next((b for b in buildings if not b['isHouse']), None)
        self.compatible = bool(self.house and self.shop and self.house['color'] == self.shop['color'])
        if self.compatible != (case == 'match'):
            raise RuntimeError('Unexpected pair compatibility')
        self.prepare_arena(buildings)

    def prepare_arena(self, buildings):
        x_min = min(b['cell']['x'] for b in buildings)
        x_max = max(b['cell']['x'] + b['width'] - 1 for b in buildings)
        y_min = min(b['cell']['y'] for b in buildings)
        y_max = max(b['cell']['y'] + b['height'] - 1 for b in buildings)
        if max(x_max - x_min, y_max - y_min) >= ARENA_SIZE:
            raise RuntimeError('Pair exceeds the practice arena')
        self.x0 = max(0, min(WIDTH - ARENA_SIZE, (x_min + x_max - ARENA_SIZE + 1) // 2))
        self.y0 = max(0, min(HEIGHT - ARENA_SIZE, (y_min + y_max - ARENA_SIZE + 1) // 2))
        y, x = np.mgrid[:ARENA_SIZE, :ARENA_SIZE]
        self.cells = (y + self.y0) * WIDTH + x + self.x0
        self.area = np.zeros(CELLS, dtype=bool)
        self.area[self.cells] = True
        self.mask()
        self.inventory = self.raw['inventory'][0]
        self.edit_limit = self.native_mask['editLimit'] + 1

    def mask(self):
        if not self.stage.startswith('pair-'):
            return super().mask()
        self.native_mask = self.host.call(command='curriculumMask')
        native = np.asarray(self.native_mask['connections'], dtype=bool).reshape(CELLS, 4)
        self.legal = np.zeros(ACTIONS, dtype=bool)
        self.legal[0] = not self.commit_after_build or self.edits == 0
        self.legal[1:EDGE_END] = native[self.cells.ravel()].ravel()
        # The native canvas is larger than the policy's local action arena.
        self.legal[1:EDGE_END] &= PAIR_INSIDE.ravel()
        return self.legal

    def connected(self):
        if self.stage.startswith('pair-') and not self.compatible:
            return False
        return super().connected()


class PairEnvironment(DrivewayEnvironment):
    def __init__(self, dll, worker=0, workers=1, case='match', seed_start=760000, commit=False):
        super().__init__(dll, worker, workers, seed_start=seed_start)
        self.env.close()
        self.env = PairPractice(dll)
        self.case = case
        self.commit = commit
        self.observation_space.spaces['parcel_colors'] = gym.spaces.Box(0, 2, (COLORS, 2), np.float32)
        self.observation_space.spaces['legal_draw'] = gym.spaces.Box(0, 1, (EDGE_SLOTS,), np.float32)

    def reset(self, *, seed=None, options=None):
        if options is not None and not options['stage'].startswith('pair-'):
            return super().reset(seed=seed, options=options)
        gym.Env.reset(self, seed=seed)
        if options is None:
            case, split, layout_seed = self.case, 'train', self._seed()
        else:
            case, split, layout_seed = options['stage'][5:], options['split'], options['layout_seed']
        self.env.commit_after_build = self.commit and options is None
        self.env.reset_pair(case, split, layout_seed)
        self.distance, self.offset, self.surplus = 0, 0, 0
        self.episode_temperature = 1.
        self.started_connected = False
        return self._with_temperature(self._observation(compact_observation(self.env))), {}

    def _observation(self, observation):
        practice = self.env
        if practice.stage.startswith('pair-'):
            anchors = []
            for building in (practice.house, practice.shop):
                if building is None:
                    anchors.append((-2, -2))
                else:
                    access = tile(building['cell'] if building['isHouse'] else building['entrance'])
                    anchors.append(practice.local(advance(access, building['drivewayDirection'])))
            obs = dict(observation, anchors=np.asarray(anchors, dtype=np.float32),
                       driveway=np.zeros(self.observation_space.spaces['driveway'].shape, dtype=np.float32))
        else:
            obs = super()._observation(observation)
        colors = np.zeros((COLORS, 2), dtype=np.float32)
        for building in practice.raw['buildings']:
            colors[building['color'], int(not building['isHouse'])] += 1
        return dict(obs, parcel_colors=colors, legal_draw=practice.legal[1:EDGE_END].astype(np.float32))

    def step(self, action):
        obs, reward, ended, truncated, info = super().step(action)
        practice = self.env
        if practice.stage.startswith('pair-'):
            success = info['connected'] if practice.compatible else action == 0 and practice.edits == 1
            ended = ended or not practice.compatible
            reward = float(ended and success)
            info.update(case=practice.case, success=bool(success))
        return obs, reward, ended, truncated, info


class PairFeatures(DrivewayFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += PAIR_FEATURES

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['parcel_colors'].flatten(1),
                          observation['legal_draw']), dim=1)


class PairLatents(nn.Module):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def forward_actor(self, features):
        board, colors, legal = features.split((features.shape[1] - PAIR_FEATURES, COLORS * 2, EDGE_SLOTS), dim=1)
        return self.parent.forward_actor(board), colors.reshape(-1, COLORS, 2), legal.bool()

    def forward_critic(self, features):
        return self.parent.forward_critic(features[:, :-PAIR_FEATURES])

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class PairHead(DrivewayHead):
    def __init__(self):
        super().__init__()
        self.color_roles = nn.Sequential(nn.Linear(2, 16), nn.SiLU(), nn.Linear(16, 16), nn.SiLU())
        self.finish = nn.Sequential(nn.Linear(16, 24), nn.SiLU(), nn.Linear(24, 1))
        nn.init.zeros_(self.finish[-1].weight)
        nn.init.constant_(self.finish[-1].bias, -2.)

    def forward(self, latent):
        board, colors, legal = latent
        prior = super().forward(board)
        relative_finish = self.finish_score(colors)
        draws = prior[:, 1:EDGE_END].masked_fill(~legal, -1e8)
        finish = torch.where(legal.any(dim=1, keepdim=True),
                             relative_finish + draws.logsumexp(dim=1, keepdim=True), prior[:, :1])
        return torch.cat((finish, prior[:, 1:]), dim=1)

    def finish_score(self, colors):
        return self.finish(self.color_roles(colors).sum(dim=1))


class InteractionHead(PairHead):
    def __init__(self):
        super().__init__()
        self.interaction = nn.Linear(3, 1, bias=False)
        nn.init.zeros_(self.interaction.weight)
        nn.init.constant_(self.finish[-1].bias, -4.)

    def finish_score(self, colors):
        # Visible role counts and local color co-occurrence give the optimizer
        # a short gradient path. The signs and action preference are learned.
        both = colors.prod(dim=2).sum(dim=1, keepdim=True)
        return super().finish_score(colors) + self.interaction(torch.cat((colors.sum(dim=1), both), dim=1))


class PairPolicy(DrivewayPolicy):
    head_class = PairHead

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = PairLatents(self.mlp_extractor)
        self.action_net = self.head_class()
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class InteractionPolicy(PairPolicy):
    head_class = InteractionHead


class CommitmentHead(InteractionHead):
    def __init__(self):
        super().__init__()
        nn.init.constant_(self.finish[-1].bias, -.5)


class CommitmentPolicy(InteractionPolicy):
    head_class = CommitmentHead


class PairMonitor(Monitor):
    def _on_rollout_start(self):
        super()._on_rollout_start()
        self.counts = {case: [0, 0] for case in CASES if case != 'blue-red'}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done:
                row = self.counts[info['case']]
                row[0] += int(info['success'])
                row[1] += 1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending.update(cases=self.counts)
        print('PAIR | ' + ' | '.join(f'{k} {a}/{b}' for k, (a, b) in self.counts.items()), flush=True)


def verify(parent, policy, dll):
    env = PairEnvironment(dll)
    try:
        for stage, seed in [('adjacent', 30000), ('driveway', 34000), ('driveway', 34001),
                            ('bend', 32000), ('clear', 36200), ('obstacle', 38000)]:
            obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
            mask = env.action_masks()
            with torch.inference_mode():
                a = parent.obs_to_tensor({k: obs[k] for k in parent.observation_space.spaces})[0]
                b = policy.obs_to_tensor(obs)[0]
                prior = parent.get_distribution(a, action_masks=mask).distribution.probs
                actual = policy.get_distribution(b, action_masks=mask).distribution.probs.cpu()
                torch.testing.assert_close(prior, actual)
        match_obs, _ = env.reset(options=dict(stage='pair-match', split='validation', layout_seed=42000))
        match_mask = env.action_masks()
        mismatch_obs, _ = env.reset(options=dict(stage='pair-mismatch', split='validation', layout_seed=42000))
        if not np.array_equal(match_mask, env.action_masks()) or not match_mask[0] or not match_mask[1:EDGE_END].any():
            raise RuntimeError('Pair mask leaked compatibility')
        for key in match_obs:
            if np.array_equal(match_obs[key], mismatch_obs[key]) == (key == 'parcel_colors'):
                raise RuntimeError('Paired boards should disagree only in visible color roles')
        _, reward, ended, truncated, info = env.step(0)
        if not ended or truncated or reward != 1 or not info['success']:
            raise RuntimeError('No-build outcome did not receive its terminal reward')
    finally:
        env.close()


def train(args):
    config = json.loads(args.checkpoint.with_name('config.json').read_text())
    if config['native_sha256'] != digest(args.parent_dll) or config['source_sha256'] != digest(args.parent_source):
        raise ValueError('Parent host or source changed')
    parent = MaskablePPO.load(args.checkpoint, device='cpu')
    if args.commit:
        assignments = ['match'] * 8 + ['mismatch'] * 4 + ['homes'] * 2 + ['destinations'] * 2
        policy_class = CommitmentPolicy
    elif args.interaction:
        assignments = ['match'] * 11 + ['mismatch'] * 3 + ['homes', 'destinations']
        policy_class = InteractionPolicy
    else:
        assignments = ['match'] * 7 + ['mismatch'] * 5 + ['homes'] * 2 + ['destinations'] * 2
        policy_class = PairPolicy
    env = SubprocVecEnv([partial(PairEnvironment, args.dll, i, len(assignments), case, commit=args.commit)
                        for i, case in enumerate(assignments)], start_method='forkserver')
    try:
        model = MaskablePPO(
            policy_class, env, learning_rate=.0007,
            n_steps=128, batch_size=128, n_epochs=4, gamma=1., gae_lambda=1., ent_coef=.002,
            target_kl=.02, device=args.device, seed=42,
            policy_kwargs=dict(features_extractor_class=PairFeatures, normalize_images=False,
                               optimizer_kwargs={'eps': 1e-5}))
        missing, unexpected = model.policy.load_state_dict(parent.policy.state_dict(), strict=False)
        prefixes = ('action_net.color_roles.', 'action_net.finish.', 'action_net.interaction.')
        if unexpected or not missing or any(not name.startswith(prefixes) for name in missing):
            raise RuntimeError('Unexpected difference from the driveway PPO parent')
        for name, parameter in model.policy.named_parameters():
            parameter.requires_grad_(name.startswith(prefixes + ('value_net.',)))
        verify(parent.policy, model.policy, args.dll)
        args.output.mkdir(parents=True)
        write(args.output/'config.json', dict(
            kind='pair-ppo', native_sha256=digest(args.dll), source_sha256=digest(__file__),
            parent=str(args.checkpoint), parent_native_sha256=digest(args.parent_dll),
            parent_sha256=digest(args.checkpoint), seed=42, workers=assignments,
            decisions=args.decisions, wall_seconds=args.wall_seconds, teacher_actions=False,
            commit_training_only=args.commit, color_interaction=args.interaction or args.commit,
            initial_finish_log_odds=-.5 if args.commit else -4. if args.interaction else -2.,
            reward='1 for a connected matching pair or immediate Finish on an unserviceable pair'))
        model.save(args.output/'initial.zip')
        monitor = PairMonitor(args.output, args.wall_seconds)
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
    parser.add_argument('--parent-dll', required=True)
    parser.add_argument('--parent-source', type=Path, default=Path(driveway_ppo.__file__))
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decisions', type=int, default=98304)
    parser.add_argument('--wall-seconds', type=int, default=720)
    parser.add_argument('--interaction', action='store_true')
    parser.add_argument('--commit', action='store_true')
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    args = parser.parse_args()
    if min(args.decisions, args.wall_seconds) < 1 or args.decisions % 2048 or args.output.exists():
        parser.error('Use a new output directory and a positive whole-rollout budget')
    torch.set_num_threads(2)
    train(args)


if __name__ == '__main__':
    main()

"""Learn which visible house to serve while still choosing one road edge at a time."""

import argparse
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
from clear_road_ppo import GEOMETRY_CHANNELS
from construction_practice import EDGE_END, advance, tile
from edge_policy import EDGE_WIDTH
from evaluate_triad_ppo import GAP_STAGES, MULTIPLE_STAGES, STAGES, TriadEnvironment
from hierarchy_rollout import policy_fingerprint
from pair_ppo import COLORS, CommitmentPolicy, PairFeatures

TARGET_INPUT = 1 + 2 * COLORS * 2


class SelectionEnvironment(TriadEnvironment):
    def __init__(self, dll, worker=0, workers=1, stage='pair-triad-left', seed_start=940000):
        super().__init__(dll)
        self.worker, self.workers = worker, workers
        self.training_stage = stage
        self.seed_start = seed_start
        self.observation_space.spaces['alternate_anchors'] = gym.spaces.Box(-2, 13, (2, 2), np.float32)
        self.observation_space.spaces['target_roles'] = gym.spaces.Box(0, 1, (TARGET_INPUT,), np.float32)

    def reset(self, *, seed=None, options=None):
        if options is None:
            options = dict(stage=self.training_stage, split='train',
                           layout_seed=self.seed_start + self.worker + self.workers * self.candidate)
            self.candidate += 1
        return super().reset(seed=seed, options=options)

    def _observation(self, observation):
        obs = super()._observation(observation)
        practice = self.env
        roles = np.zeros((2, 2, COLORS), dtype=np.float32)
        alternate = obs['anchors'].copy()
        active = practice.stage.startswith('pair-triad-')
        if active:
            first, second = practice.homes
            alternate[0] = practice.local(advance(tile(second['cell']), second['drivewayDirection']))
            roles[0, 0, first['color']] = 1.
            roles[1, 0, second['color']] = 1.
            roles[:, 1, practice.shop['color']] = 1.
        return dict(obs, alternate_anchors=alternate,
                    target_roles=np.concatenate((np.array([active], dtype=np.float32), roles.ravel())))


class SelectionFeatures(PairFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self.base_features = self._features_dim
        self._features_dim = 2 * self.base_features + TARGET_INPUT

    def forward(self, observation):
        first = super().forward(observation)
        second = super().forward(dict(observation, anchors=observation['alternate_anchors']))
        return torch.cat((first, second, observation['target_roles']), dim=1)


class SelectionLatents(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base

    def forward_actor(self, features):
        first, second = features[:, :-TARGET_INPUT].chunk(2, dim=1)
        return self.base.forward_actor(first), self.base.forward_actor(second), features[:, -TARGET_INPUT:]

    def forward_critic(self, features):
        first, _ = features[:, :-TARGET_INPUT].chunk(2, dim=1)
        return self.base.forward_critic(first)

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class SelectionHead(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.affinity = nn.Linear(1, 1, bias=False)
        nn.init.zeros_(self.affinity.weight)
        self.residual = nn.Sequential(nn.Linear(EDGE_WIDTH + GEOMETRY_CHANNELS + 1, 40),
                                      nn.SiLU(), nn.Linear(40, 1))
        nn.init.zeros_(self.residual[-1].weight)
        nn.init.zeros_(self.residual[-1].bias)
        self.select_component = False

    def forward(self, latent):
        return self.score(latent)

    def score(self, latent, additional_bonus=0.):
        first, second, inputs = latent
        primary = self.base(first)
        alternate = self.base(second)
        active = inputs[:, :1].bool()
        colors = inputs[:, 1:].reshape(-1, 2, 2, COLORS)
        # Each target gets the same trainable score on its visible color overlap.
        overlap = colors.prod(dim=2).sum(dim=-1, keepdim=True)
        affinity = self.affinity(overlap).squeeze(-1)
        weights = affinity.log_softmax(dim=1)
        legal = first[2]
        road_logits = torch.stack((primary[:, 1:EDGE_END], alternate[:, 1:EDGE_END]), dim=1)
        edges = torch.stack((first[0][0][0], second[0][0][0]), dim=1)
        adjusted = torch.cat((edges, overlap[:, :, None].expand(-1, -1, edges.shape[2], -1)), dim=-1)
        bonus = self.residual(adjusted).squeeze(-1) + additional_bonus
        masked = (road_logits + bonus).masked_fill(~legal[:, None], -1e8)
        normalized = masked.log_softmax(dim=2)
        if self.select_component:
            selected = weights.argmax(dim=1)
            mixed = normalized[torch.arange(len(selected), device=selected.device), selected]
        else:
            mixed = (normalized + weights[:, :, None]).logsumexp(dim=1)
        # Preserve the previous comparison of Finish versus all drawing actions.
        mixed = mixed + road_logits[:, 0].masked_fill(~legal, -1e8).logsumexp(dim=1, keepdim=True)
        roads = torch.where(active, mixed, primary[:, 1:EDGE_END])
        return torch.cat((primary[:, :1], roads, primary[:, EDGE_END:]), dim=1)


class SelectionPolicy(CommitmentPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = SelectionLatents(self.mlp_extractor)
        self.action_net = SelectionHead(self.action_net)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class SelectionMonitor(Monitor):
    def _on_rollout_start(self):
        super()._on_rollout_start()
        self.cases = {}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done:
                row = self.cases.setdefault(info['case'], [0, 0])
                row[0] += int(info['connected'])
                row[1] += 1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending['affinity_weight'] = float(self.model.policy.action_net.affinity.weight.detach().cpu().item())
        self.pending['cases'] = self.cases
        print('TRIAD | ' + ' | '.join(f'{case} {wins}/{games}' for case, (wins, games) in sorted(self.cases.items())),
              flush=True)


def verify(parent, policy, dll):
    env = SelectionEnvironment(dll)
    try:
        for stage, seed in [('adjacent', 30000), ('driveway', 34001), ('clear', 36200),
                            ('obstacle', 38000), ('pair-match', 42000), ('pair-homes', 42000)]:
            obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
            mask = env.action_masks()
            with torch.inference_mode():
                a = parent.obs_to_tensor({key: obs[key] for key in parent.observation_space.spaces})[0]
                b = policy.obs_to_tensor(obs)[0]
                prior = parent.get_distribution(a, action_masks=mask).distribution.probs
                actual = policy.get_distribution(b, action_masks=mask).distribution.probs.cpu()
                torch.testing.assert_close(prior, actual)
    finally:
        env.close()


def train(args):
    parent = MaskablePPO.load(args.checkpoint, device='cpu')
    stages = GAP_STAGES if args.gaps else STAGES
    if args.resume and args.full:
        assignments = list(STAGES) * 6 + list(MULTIPLE_STAGES[3]) + list(GAP_STAGES)
        seed_start = 1240000
    elif args.resume:
        assignments = list(MULTIPLE_STAGES[3]) * 5 + list(MULTIPLE_STAGES[2]) + list(GAP_STAGES) * 2
        seed_start = 1040000
    else:
        assignments = list(stages) * 8
        seed_start = 940000
    env = SubprocVecEnv([partial(SelectionEnvironment, args.dll, i, len(assignments), stage, seed_start)
                        for i, stage in enumerate(assignments)], start_method='forkserver')
    try:
        prefixes = ('action_net.affinity.', 'action_net.residual.')
        if args.resume:
            model = MaskablePPO.load(args.checkpoint, env=env, device=args.device)
            if (policy_fingerprint(model.policy) != policy_fingerprint(parent.policy)
                    or model.num_timesteps != parent.num_timesteps
                    or not model.policy.optimizer.state_dict()['state']):
                raise RuntimeError('Resume failed to restore weights, counters or Adam state')
        else:
            model = MaskablePPO(
                SelectionPolicy, env, learning_rate=args.learning_rate, n_steps=128, batch_size=128, n_epochs=4,
                gamma=1., gae_lambda=1., ent_coef=.002, target_kl=.02, device=args.device, seed=42,
                policy_kwargs=dict(features_extractor_class=SelectionFeatures, normalize_images=False,
                                   optimizer_kwargs={'eps': 1e-5}))
            weights = {key.replace('action_net.', 'action_net.base.', 1) if key.startswith('action_net.') else key: val
                       for key, val in parent.policy.state_dict().items()}
            missing, unexpected = model.policy.load_state_dict(weights, strict=False)
            if unexpected or not missing or any(not name.startswith(prefixes) for name in missing):
                raise RuntimeError('Unexpected warm-start difference')
        for name, parameter in model.policy.named_parameters():
            parameter.requires_grad_(name.startswith(prefixes + ('value_net.',)))
        baseline = MaskablePPO.load(args.original_checkpoint, device='cpu') if args.resume else parent
        verify(baseline.policy, model.policy, args.dll)
        args.output.mkdir(parents=True)
        write(args.output/'config.json', dict(
            kind='triad-ppo', native_sha256=digest(args.dll), source_sha256=digest(__file__),
            parent=str(args.checkpoint), parent_sha256=digest(args.checkpoint),
            parent_fingerprint=policy_fingerprint(parent.policy), seed=42,
            decisions=args.decisions, wall_seconds=args.wall_seconds, teacher_actions=False,
            stages=assignments, learning_rate=model.learning_rate, starting_decisions=model.num_timesteps,
            resumed_adam=args.resume, seed_start=seed_start,
            reward='1 for legally connecting the serviceable home by the edit limit, otherwise 0'))
        model.save(args.output/'initial.zip')
        monitor = SelectionMonitor(args.output, args.wall_seconds)
        monitor.completed_update_decisions = model.num_timesteps
        try:
            model.learn(total_timesteps=args.decisions, reset_num_timesteps=not args.resume,
                        callback=monitor, progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        verify(baseline.policy, model.policy, args.dll)
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
    parser.add_argument('--decisions', type=int, default=98304)
    parser.add_argument('--wall-seconds', type=int, default=720)
    parser.add_argument('--learning-rate', type=float, default=.001)
    parser.add_argument('--gaps', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Continue with two- and three-gap branches')
    parser.add_argument('--full', action='store_true', help='Resume on empty-board branches with rehearsal')
    parser.add_argument('--original-checkpoint', type=Path, help='Pair-only parent for parity on prior skills')
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    args = parser.parse_args()
    if min(args.decisions, args.wall_seconds) < 1 or args.decisions % 2048 or args.output.exists():
        parser.error('Use a fresh output and a whole-rollout budget')
    if args.resume and not args.original_checkpoint:
        parser.error('The previous pair-only parent is required for parity checks')
    if args.full and not args.resume:
        parser.error('Empty-board continuation requires --resume')
    torch.set_num_threads(2)
    train(args)


if __name__ == '__main__':
    main()

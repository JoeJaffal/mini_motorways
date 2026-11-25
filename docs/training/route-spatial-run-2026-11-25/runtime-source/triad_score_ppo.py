"""Score-only timed play on empty boards with competing homes."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from math import log
from pathlib import Path
from threading import Lock
from time import monotonic

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from torch import nn

from bend_ppo import Monitor, compact_observation, digest, write
from connection_practice import ARENA_SIZE
from construction_practice import EDGE_END, endpoints
from evaluate_triad_ppo import STAGES, witness
from hierarchy_rollout import policy_fingerprint
from score_wait_ppo import CLOCK_WIDTH, WAIT_TICKS, native_build_or_wait, play
from triad_curriculum_ppo import (
    UNEVEN, CurriculumEnvironment, FrameFeatures, FramePolicy, NetworkFeatures, NetworkPolicy,
)
from triad_ppo import SelectionFeatures, SelectionPolicy

DECISIONS = 18
EXTRA = CLOCK_WIDTH + 2
LEGAL_DRAWS = EDGE_END - 1
TOTAL_EXTRA = EXTRA + LEGAL_DRAWS


class ScoreTriadEnvironment(CurriculumEnvironment):
    def __init__(self, dll, worker=0, workers=1, use_frame=False, use_network=False,
                 uneven=False, seed_start=1580000, decision_limit=DECISIONS, wait_ticks=WAIT_TICKS):
        super().__init__(dll, worker, workers, phase=0, seed_start=seed_start,
                         use_frame=use_frame, use_network=use_network)
        self.uneven = uneven
        self.decision_limit = decision_limit
        self.wait_ticks = wait_ticks
        self.observation_space.spaces['score_clock'] = gym.spaces.Box(0, 12, (EXTRA,), np.float32)

    def reset(self, *, seed=None, options=None):
        self.wait_decisions = 0
        self.waits = 0
        self.first_wait_move = None
        self.first_connection = None
        self.builds_after_connection = 0
        if options is None and self.uneven:
            options = dict(stage=UNEVEN[self.side], split='train', layout_seed=self._seed())
        return super().reset(seed=seed, options=options)

    def _observation(self, observation):
        obs = super()._observation(observation)
        raw = self.env.raw
        road = obs['grid'][1].astype(bool)
        degree = obs['grid'][5:13].sum(axis=0)
        clock = np.array([
            1., raw['time'] / 100., self.wait_decisions / self.decision_limit,
            raw['tripsCompleted'] / 10., raw['inventory'][0] / 2.,
            road.sum() / 12., obs['grid'][5:13].sum() / 24.,
            np.abs(obs['anchors'][0] - obs['anchors'][1]).max() / 12.,
            np.count_nonzero(road & (degree == 1)) / 2.,
            np.count_nonzero(road & (degree == 0)) / 2.,
        ], dtype=np.float32)
        return dict(obs, score_clock=clock)

    def step(self, action):
        action = int(action)
        if self.wait_decisions >= self.decision_limit:
            raise RuntimeError('No timed choices remain')
        practice = self.env
        result = native_build_or_wait(practice, action, self.wait_ticks)
        self.waits += int(action == 0)
        self.wait_decisions += 1
        if action == 0 and self.first_wait_move is None:
            self.first_wait_move = self.wait_decisions
        if action != 0 and self.first_connection is not None:
            self.builds_after_connection += 1
        ended = result['terminated'] or self.wait_decisions == self.decision_limit
        if not ended:
            practice.mask()
        obs = self._with_temperature(self._observation(compact_observation(practice)))
        trips = practice.raw['tripsCompleted']
        connected = practice.connected()
        if connected and self.first_connection is None:
            self.first_connection = dict(move=self.wait_decisions, seconds=practice.raw['time'],
                                         builds=practice.edits)
        return obs, float(result['tripsDelta']), ended, False, dict(
            stage=practice.stage, connected=connected, trips=trips,
            seconds=practice.raw['time'], waits=self.waits, builds=practice.edits,
            spent=practice.inventory-practice.raw['inventory'][0],
            first_wait_move=self.first_wait_move, first_connection=self.first_connection,
            builds_after_connection=self.builds_after_connection,
            native_failure=result['terminated'], success=trips >= 3)


class ScoreFeaturesMixin:
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += TOTAL_EXTRA

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['score_clock'], observation['legal_draw']), dim=1)


class ScoreFeatures(ScoreFeaturesMixin, SelectionFeatures):
    pass


class ScoreFrameFeatures(ScoreFeaturesMixin, FrameFeatures):
    pass


class ScoreNetworkFeatures(ScoreFeaturesMixin, NetworkFeatures):
    pass


class ScoreLatents(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base

    def forward_actor(self, features):
        before, clock, legal = features.split((features.shape[1]-TOTAL_EXTRA, EXTRA, LEGAL_DRAWS), dim=1)
        return self.base.forward_actor(before), clock, legal.bool()

    def forward_critic(self, features):
        base = self.base.forward_critic(features[:, :-TOTAL_EXTRA])
        return torch.cat((base, features[:, -TOTAL_EXTRA:-LEGAL_DRAWS]), dim=1)

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class ScoreHead(nn.Module):
    def __init__(self, draw):
        super().__init__()
        self.draw = draw
        self.wait = nn.Sequential(nn.Linear(CLOCK_WIDTH + 2, 48), nn.SiLU(), nn.Linear(48, 1))
        self.correction = nn.Linear(2, 1, bias=False)

    def forward(self, latent):
        return self.score(latent)

    def score(self, latent, draw_bonus=0.):
        board, context, legal = latent
        prior = self.draw(board)
        clock, loose = context.split((CLOCK_WIDTH, 2), dim=1)
        draw = prior[:, 1:EDGE_END] + draw_bonus
        masked = draw.masked_fill(~legal, -1e8)
        mass = masked.logsumexp(dim=1, keepdim=True)
        peak = masked.amax(dim=1, keepdim=True)
        summary = torch.where(legal.any(dim=1, keepdim=True),
                              torch.cat((mass, peak), dim=1) / 10., torch.zeros_like(loose))
        wait = self.wait(torch.cat((clock, summary), dim=1)) + self.correction(loose) + mass
        wait = torch.where(legal.any(dim=1, keepdim=True), wait, torch.zeros_like(wait))
        return torch.cat((wait, draw, prior[:, EDGE_END:]), dim=1)


class ScorePolicyMixin:
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = ScoreLatents(self.mlp_extractor)
        self.action_net = ScoreHead(self.action_net)
        first = self.value_net[0]
        self.value_net[0] = nn.Linear(first.in_features + EXTRA, first.out_features)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class ScorePolicy(ScorePolicyMixin, SelectionPolicy):
    pass


class ScoreFramePolicy(ScorePolicyMixin, FramePolicy):
    pass


class ScoreNetworkPolicy(ScorePolicyMixin, NetworkPolicy):
    pass


class AttachmentFeatures(ScoreFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += LEGAL_DRAWS
        points = torch.tensor([endpoints(a) for a in range(1, EDGE_END)])
        indices = points[..., 1] * ARENA_SIZE + points[..., 0]
        valid = ((points >= 0) & (points < ARENA_SIZE)).all(dim=-1)
        self.register_buffer('attachment_cells', torch.where(valid, indices, ARENA_SIZE**2), persistent=False)

    def forward(self, observation):
        parcels = observation['grid'][:, [2, 3]].amax(dim=1).flatten(1)
        parcels = torch.nn.functional.pad(parcels, (0, 1))
        reaches_parcel = parcels[:, self.attachment_cells].amax(dim=-1)
        return torch.cat((super().forward(observation), reaches_parcel), dim=1)


class AttachmentLatents(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base

    def forward_actor(self, features):
        return self.base.forward_actor(features[:, :-LEGAL_DRAWS]), features[:, -LEGAL_DRAWS:]

    def forward_critic(self, features):
        return self.base.forward_critic(features[:, :-LEGAL_DRAWS])

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class AttachmentHead(ScoreHead):
    def __init__(self, draw):
        super().__init__(draw)
        self.attachment_odds = nn.Parameter(torch.zeros(()))

    def forward(self, latent):
        score, reaches_parcel = latent
        return self.score(score, reaches_parcel * self.attachment_odds)


class AttachmentScorePolicy(ScorePolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = AttachmentLatents(self.mlp_extractor)
        self.action_net = AttachmentHead(self.action_net.draw)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class ScoreMonitor(Monitor):
    def __init__(self, output, seconds, stages):
        super().__init__(output, seconds)
        self.stages = stages

    def _on_rollout_start(self):
        super()._on_rollout_start()
        self.sides = {stage: [0, 0, 0] for stage in self.stages}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done:
                row = self.sides[info['stage']]
                row[0] += int(info['success'])
                row[1] += 1
                row[2] += info['trips']
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending['native_score'] = self.sides
        odds = getattr(self.model.policy.action_net, 'attachment_odds', None)
        if odds is not None:
            self.pending['attachment_logit'] = float(odds.detach().cpu())
        print('TIMED | ' + ' | '.join(
            f'{stage}: {wins}/{n} pass, {trips} trips' for stage, (wins, n, trips) in self.sides.items()),
            flush=True)


def check_native(factory, stages):
    env = factory()
    rows = []
    try:
        for stage in stages:
            for build in (False, True):
                env.reset(options=dict(stage=stage, split='validation', layout_seed=56500))
                actions = witness(env.env) if build else []
                reward_sum = 0.
                for action in actions + [0] * (env.decision_limit-len(actions)):
                    _, reward, ended, truncated, info = env.step(action)
                    reward_sum += reward
                    if ended:
                        break
                if truncated or reward_sum != info['trips'] or info['success'] != build:
                    raise RuntimeError('Native score-only control diverged')
                rows.append(dict(stage=stage, witness=build, total_reward=reward_sum, **{
                    'elapsed': info['seconds'], 'spent': info['spent']}))
    finally:
        env.close()
    return rows


def new_timed_model(args, env, route, policy_class, feature_class):
    previous_wait = MaskablePPO.load(args.wait_checkpoint, device='cpu')
    timed_parent = 'score_clock' in previous_wait.observation_space.spaces
    wait_prefix = 'action_net.wait.' if timed_parent else 'action_net.base.wait.'
    model = MaskablePPO(
        policy_class, env, learning_rate=args.learning_rate, n_steps=128, batch_size=128, n_epochs=4,
        gamma=1., gae_lambda=1., ent_coef=.004, target_kl=.025, device=args.device, seed=42,
        policy_kwargs=dict(features_extractor_class=feature_class, normalize_images=False,
                           optimizer_kwargs={'eps': 1e-5}))
    original = route.policy.state_dict()
    weights = {k.replace('action_net.', 'action_net.draw.', 1) if k.startswith('action_net.') else k: v
               for k, v in original.items()}
    weights['value_net.0.weight'] = torch.nn.functional.pad(original['value_net.0.weight'], (0, EXTRA))
    for key, value in previous_wait.policy.state_dict().items():
        if key.startswith(wait_prefix):
            weights[key.replace(wait_prefix, 'action_net.wait.', 1)] = value
        elif key.startswith('action_net.correction.'):
            weights[key] = value
    model.policy.load_state_dict(weights, strict=True)
    bias_adjustment = 0. if timed_parent else -1.
    with torch.no_grad():
        wait_head = model.policy.action_net
        if args.initial_wait_prob is None:
            wait_head.wait[-1].bias.add_(bias_adjustment)
        else:
            p = args.initial_wait_prob
            wait_head.wait[-1].weight.zero_()
            wait_head.wait[-1].bias.fill_(log(p / (1-p)))
            wait_head.correction.weight.zero_()
    return model, bias_adjustment if args.initial_wait_prob is None else None


def train(args, factory, route, policy_class, feature_class):
    stages = STAGES + UNEVEN if args.mix_uneven else STAGES
    controls = check_native(factory, stages)
    env = SubprocVecEnv([
        partial(factory, worker=i, workers=16, uneven=args.mix_uneven and i >= 12, seed_start=args.seed_start)
        for i in range(16)
    ], start_method='forkserver')
    try:
        bias_adjustment = None
        if args.learn_attachment_odds:
            model = MaskablePPO(
                AttachmentScorePolicy, env, learning_rate=args.learning_rate, n_steps=128, batch_size=128,
                n_epochs=4, gamma=1., gae_lambda=1., ent_coef=.004, target_kl=.025, device=args.device, seed=42,
                policy_kwargs=dict(features_extractor_class=AttachmentFeatures, normalize_images=False,
                                   optimizer_kwargs={'eps': 1e-5}))
            missing, unexpected = model.policy.load_state_dict(route.policy.state_dict(), strict=False)
            if unexpected or missing != ['action_net.attachment_odds']:
                raise RuntimeError('The attachment experiment changed the existing model parameters')
            model.num_timesteps = route.num_timesteps
            model._n_updates = route._n_updates
            verify_action_parity(factory, route.policy, model.policy)
        elif args.resume:
            model = MaskablePPO.load(args.checkpoint, env=env, device=args.device,
                                     custom_objects=dict(learning_rate=args.learning_rate))
            if (policy_fingerprint(model.policy) != policy_fingerprint(route.policy)
                    or model.num_timesteps != route.num_timesteps
                    or not model.policy.optimizer.state_dict()['state']):
                raise RuntimeError('Timed continuation did not restore checkpoint state')
        else:
            model, bias_adjustment = new_timed_model(args, env, route, policy_class, feature_class)
        route_before = policy_fingerprint(model.policy.action_net.draw)
        prefixes = ('action_net.wait.', 'action_net.correction.', 'value_net.')
        if args.learn_attachment_odds:
            prefixes += ('action_net.attachment_odds',)
        if args.train_draw:
            prefixes += ('action_net.draw.affinity.', 'action_net.draw.residual.',
                         'action_net.draw.frame.', 'action_net.draw.network.')
        for key, parameter in model.policy.named_parameters():
            parameter.requires_grad_(key.startswith(prefixes))
        args.output.mkdir(parents=True)
        write(args.output/'config.json', dict(
            native_sha256=digest(args.dll), source_sha256=digest(__file__), checkpoint_sha256=digest(args.checkpoint),
            wait_checkpoint_sha256=digest(args.wait_checkpoint) if args.wait_checkpoint else None,
            seed=42, seed_start=args.seed_start, decisions=args.decisions, learning_rate=args.learning_rate,
            decision_limit=args.decision_limit, wait_ticks=args.wait_ticks, reward='native tripsDelta only',
            teacher_actions=False,
            route_frozen=not args.train_draw, initial_wait_prob=args.initial_wait_prob,
            starting_decisions=model.num_timesteps, restored_adam=args.resume and not args.learn_attachment_odds,
            learn_attachment_odds=args.learn_attachment_odds, training_stages=stages,
            transferred_wait_initial_bias_adjustment=bias_adjustment))
        write(args.output/'native-controls.json', controls)
        model.save(args.output/'initial.zip')
        monitor = ScoreMonitor(args.output, args.wall_seconds, stages)
        monitor.completed_update_decisions = model.num_timesteps
        try:
            model.learn(total_timesteps=args.decisions, reset_num_timesteps=not args.resume,
                        callback=monitor, progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        if not args.train_draw and policy_fingerprint(model.policy.action_net.draw) != route_before:
            raise RuntimeError('Frozen draw actor changed during timed training')
        write(args.output/'status.json', dict(result=result, saved_decisions=monitor.completed_update_decisions,
              collected_decisions=model.num_timesteps, elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


def verify_action_parity(factory, parent, added_feature):
    env = factory()
    try:
        for stage in STAGES:
            for seed in (62000, 62001, 62002):
                obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
                mask = env.action_masks()
                with torch.inference_mode():
                    a = parent.obs_to_tensor(obs)[0]
                    b = added_feature.obs_to_tensor(obs)[0]
                    p = parent.get_distribution(a, action_masks=mask).distribution.probs
                    q = added_feature.get_distribution(b, action_masks=mask).distribution.probs.cpu()
                    torch.testing.assert_close(p, q, atol=2e-6, rtol=2e-5)
    finally:
        env.close()


def evaluate(args, factory, model):
    policy = model.policy
    if args.diagnostic_attachment_logit is not None:
        odds = getattr(policy.action_net, 'attachment_odds', None)
        if odds is None:
            raise ValueError('The attachment probe needs a checkpoint with the visible parcel feature')
        with torch.no_grad():
            odds.fill_(args.diagnostic_attachment_logit)
    policy.set_training_mode(False)
    fingerprint = policy_fingerprint(policy)
    envs = []
    lock = Lock()
    results = {}
    try:
        for _ in range(8):
            envs.append(factory())
        with ThreadPoolExecutor(max_workers=8) as pool:
            for stage in UNEVEN if args.uneven else STAGES:
                for mode in ('greedy', 'sampled'):
                    first = (68000 if args.uneven else 62000) + args.offset
                    rows = []
                    for start in range(first, first+args.count, len(envs)):
                        seeds = range(start, min(first+args.count, start+len(envs)))
                        rows.extend(pool.map(lambda pair: play(pair[0], policy, lock, stage, pair[1], mode),
                                             zip(envs, seeds)))
                    results[f'{stage}/{mode}'] = rows
                    print(f'{stage}/{mode}: {sum(r["success"] for r in rows)}/{len(rows)} passed, '
                          f'{np.mean([r["trips"] for r in rows]):.2f} mean trips', flush=True)
    finally:
        for env in envs:
            env.close()
    if policy_fingerprint(policy) != fingerprint:
        raise RuntimeError('Frozen timed evaluation changed weights')
    write(args.output, dict(native_sha256=digest(args.dll), checkpoint_sha256=digest(args.checkpoint),
                            fingerprint=fingerprint, diagnostic_attachment_logit=args.diagnostic_attachment_logit,
                            decision_limit=args.decision_limit, wait_ticks=args.wait_ticks,
                            results=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('train', 'evaluate'))
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--wait-checkpoint', type=Path)
    parser.add_argument('--initial-wait-prob', type=float, help='Initialize Wait odds without the old output layer')
    parser.add_argument('--resume', action='store_true', help='Restore weights and Adam from a timed checkpoint')
    parser.add_argument('--train-draw', action='store_true', help='Fine-tune the competing-home draw scorer')
    parser.add_argument('--mix-uneven', action='store_true', help='Use four workers on unequal home distances')
    parser.add_argument('--learn-attachment-odds', action='store_true',
                        help='Learn a logit adjustment for visible parcel attachment draws')
    parser.add_argument('--diagnostic-attachment-logit', type=float,
                        help='Frozen diagnostic adjustment to attachment odds')
    parser.add_argument('--learning-rate', type=float, default=.0006)
    parser.add_argument('--seed-start', type=int, default=1580000)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decisions', type=int, default=98304)
    parser.add_argument('--wall-seconds', type=int, default=900)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--decision-limit', type=int, default=DECISIONS)
    parser.add_argument('--wait-ticks', type=int, default=WAIT_TICKS)
    parser.add_argument('--uneven', action='store_true', help='Frozen stress test with different home distances')
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    args = parser.parse_args()
    if (args.output.exists() or min(args.count, args.decisions, args.wall_seconds,
                                    args.decision_limit, args.wait_ticks) < 1
            or args.offset < 0 or args.decisions % 2048):
        parser.error('Use a fresh output path, a whole rollout budget and positive bounds')
    if args.mode == 'train' and not args.resume and args.wait_checkpoint is None:
        parser.error('Training requires a verified score-only Wait parent')
    if args.mode == 'train' and args.uneven:
        parser.error('Unequal home distances are an evaluation-only test')
    if args.train_draw and not args.resume:
        parser.error('Fine-tuning the draw scorer starts from a trained timed policy')
    if args.learn_attachment_odds and not args.resume:
        parser.error('Start the attachment experiment from a trained timed policy')
    if args.resume and args.initial_wait_prob is not None:
        parser.error('A resumed actor keeps its saved Wait odds')
    if args.mode == 'train' and args.diagnostic_attachment_logit is not None:
        parser.error('The diagnostic logit is an evaluation control')
    if args.initial_wait_prob is not None and not 0 < args.initial_wait_prob < 1:
        parser.error('Initial Wait probability must be between zero and one')
    torch.set_num_threads(2)
    model = MaskablePPO.load(args.checkpoint, device='cpu')
    spaces = model.observation_space.spaces
    network, frame = 'route_network' in spaces, 'route_frame' in spaces
    factory = partial(ScoreTriadEnvironment, args.dll, use_frame=frame, use_network=network,
                      decision_limit=args.decision_limit, wait_ticks=args.wait_ticks)
    if args.mode == 'train':
        if args.resume != ('score_clock' in spaces):
            parser.error('Match --resume to the checkpoint type')
        if args.learn_attachment_odds and frame:
            parser.error('The attachment experiment uses the base timed actor')
        actor, encoder = ((ScoreNetworkPolicy, ScoreNetworkFeatures) if network
                          else (ScoreFramePolicy, ScoreFrameFeatures) if frame else (ScorePolicy, ScoreFeatures))
        train(args, factory, model, actor, encoder)
    else:
        evaluate(args, factory, model)


if __name__ == '__main__':
    main()

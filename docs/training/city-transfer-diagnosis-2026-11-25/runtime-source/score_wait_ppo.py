"""Train an explicit Build-or-Wait decision using native scored trips only."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
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
from construction_practice import EDGE_END, endpoints
from hierarchy_rollout import policy_fingerprint
from pair_ppo import CommitmentPolicy, PairEnvironment
from pair_ppo import PairFeatures

STAGES = ('wait-zero', 'wait-one', 'wait-two')
DECISION_LIMIT = 10
WAIT_TICKS = 200
CLOCK_WIDTH = 8


def native_build_or_wait(practice, action, wait_ticks=WAIT_TICKS):
    if not 0 <= action < EDGE_END or not practice.legal[action]:
        raise RuntimeError(f'Illegal Build-or-Wait action {action}')
    time_before = practice.raw['time']
    stock_before = practice.raw['inventory'][0]
    if action == 0:
        result = practice.call(command='step', ticks=wait_ticks)
        if not result['terminated'] and not np.isclose(practice.raw['time'] - time_before, wait_ticks / 20.):
            raise RuntimeError('Wait did not advance the expected native interval')
    else:
        first, second = (practice.world(pos) for pos in endpoints(action))
        result = practice.call(command='draw', x=first[0], y=first[1], toX=second[0], toY=second[1])
        practice.edits += 1
        if practice.raw['time'] != time_before:
            raise RuntimeError('Road edit advanced time')
    if not result['accepted'] or result['truncated'] or result['tripsDelta'] < 0:
        raise RuntimeError('Unexpected native response')
    if not 0 <= practice.raw['inventory'][0] <= stock_before:
        raise RuntimeError('Build-or-Wait exceeded native stock')
    return result


class ScoreWaitEnvironment(PairEnvironment):
    def __init__(self, dll, worker=0, workers=1, exercise='wait-zero'):
        super().__init__(dll, worker, workers, seed_start=1100000)
        self.wait_exercise = exercise
        self.wait_active = False
        self.observation_space.spaces['clock'] = gym.spaces.Box(0, 2, (CLOCK_WIDTH,), np.float32)

    def reset(self, *, seed=None, options=None):
        if options is None:
            options = dict(stage=self.wait_exercise, split='train', layout_seed=self._seed())
        stage = options['stage']
        self.wait_active = stage in STAGES
        if not self.wait_active:
            return super().reset(seed=seed, options=options)
        gym.Env.reset(self, seed=seed)
        practice = self.env
        practice.stage, practice.seed = 'pair-' + stage, options['layout_seed']
        practice.edits = 0
        practice.commit_after_build = False
        response = practice.call(command='reset', version='OriginalReference', practice=True,
                                 practiceStage='curriculum-' + stage, practiceSplit=options['split'],
                                 seed=practice.seed)
        if not response['accepted'] or response['terminated'] or response['truncated']:
            raise RuntimeError('Cannot reset native Build-or-Wait fixture')
        buildings = practice.raw['buildings']
        practice.house, = (b for b in buildings if b['isHouse'])
        practice.shop, = (b for b in buildings if not b['isHouse'])
        practice.compatible = True
        practice.prepare_arena(buildings)
        self.wait_decisions = 0
        self.waits = 0
        self.initial_connected = practice.connected()
        self.episode_temperature = 1.
        if self.initial_connected != (stage == 'wait-zero') or not self.action_masks()[1:EDGE_END].any():
            raise RuntimeError('Expected a visible board with legal competing build choices')
        return self._next_observation(), {}

    def _next_observation(self):
        return self._with_temperature(self._observation(compact_observation(self.env)))

    def _observation(self, observation):
        obs = super()._observation(observation)
        clock = np.zeros(CLOCK_WIDTH, dtype=np.float32)
        if self.wait_active:
            raw = self.env.raw
            clock[:] = [1., raw['time'] / 100., self.wait_decisions / DECISION_LIMIT,
                        raw['tripsCompleted'] / 10., raw['inventory'][0] / 2.,
                        obs['grid'][1].sum() / 12., obs['grid'][5:13].sum() / 24.,
                        np.abs(obs['anchors'][0] - obs['anchors'][1]).max() / 12.]
        return dict(obs, clock=clock)

    def step(self, action):
        if not self.wait_active:
            return super().step(action)
        practice = self.env
        action = int(action)
        if self.wait_decisions >= DECISION_LIMIT:
            raise RuntimeError('No Build-or-Wait decisions remain')
        result = native_build_or_wait(practice, action)
        self.waits += int(action == 0)
        self.wait_decisions += 1
        ended = result['terminated'] or self.wait_decisions == DECISION_LIMIT
        if not ended:
            practice.mask()
        trips = practice.raw['tripsCompleted']
        return self._next_observation(), float(result['tripsDelta']), ended, False, dict(
            stage=practice.stage[5:], started_connected=self.initial_connected, connected=practice.connected(),
            trips=trips, seconds=practice.raw['time'], waits=self.waits, builds=practice.edits,
            spent=practice.inventory-practice.raw['inventory'][0],
            native_failure=result['terminated'], success=trips >= 3)


class WaitFeatures(PairFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += CLOCK_WIDTH

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['clock']), dim=1)


class TopologyWaitEnvironment(ScoreWaitEnvironment):
    def __init__(self, dll, worker=0, workers=1, exercise='wait-zero'):
        super().__init__(dll, worker, workers, exercise)
        self.observation_space.spaces['loose_ends'] = gym.spaces.Box(0, 72, (2,), np.float32)

    def _observation(self, observation):
        obs = super()._observation(observation)
        roads = obs['grid'][1].astype(bool)
        degree = obs['grid'][5:13].sum(axis=0)
        endpoints = np.array([np.count_nonzero(roads & (degree == d)) for d in (1, 0)], dtype=np.float32)
        return dict(obs, loose_ends=endpoints / 2)


class TopologyFeatures(WaitFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += 2

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['loose_ends']), dim=1)


class WaitLatents(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base

    def forward_actor(self, features):
        return self.base.forward_actor(features[:, :-CLOCK_WIDTH]), features[:, -CLOCK_WIDTH:]

    def forward_critic(self, features):
        return torch.cat((self.base.forward_critic(features[:, :-CLOCK_WIDTH]), features[:, -CLOCK_WIDTH:]), dim=1)

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class WaitHead(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.wait = nn.Sequential(nn.Linear(CLOCK_WIDTH + 2, 48), nn.SiLU(), nn.Linear(48, 1))
        nn.init.zeros_(self.wait[-1].weight)
        nn.init.constant_(self.wait[-1].bias, .8)

    def forward(self, latent):
        board, clock = latent
        prior = self.base(board)
        legal = board[2]
        draws = prior[:, 1:EDGE_END].masked_fill(~legal, -1e8)
        can_draw = legal.any(dim=1, keepdim=True)
        mass = draws.logsumexp(dim=1, keepdim=True)
        peak = draws.amax(dim=1, keepdim=True)
        summary = torch.where(can_draw, torch.cat((mass / 10, peak / 10), dim=1), torch.zeros_like(clock[:, :2]))
        wait = self.wait(torch.cat((clock, summary), dim=1)) + mass
        action_zero = torch.where(clock[:, :1].bool() & can_draw, wait, prior[:, :1])
        return torch.cat((action_zero, prior[:, 1:]), dim=1)


class WaitPolicy(CommitmentPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = WaitLatents(self.mlp_extractor)
        self.action_net = WaitHead(self.action_net)
        first = self.value_net[0]
        self.value_net[0] = nn.Linear(first.in_features + CLOCK_WIDTH, first.out_features)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class TopologyLatents(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base

    def forward_actor(self, features):
        return self.base.forward_actor(features[:, :-2]), features[:, -2:]

    def forward_critic(self, features):
        return self.base.forward_critic(features[:, :-2])

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class TopologyHead(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.correction = nn.Linear(2, 1, bias=False)
        nn.init.zeros_(self.correction.weight)

    def forward(self, latent):
        board, loose_ends = latent
        prior = self.base(board)
        clock = board[1]
        wait = prior[:, :1] + self.correction(loose_ends) * clock[:, :1]
        return torch.cat((wait, prior[:, 1:]), dim=1)


class TopologyWaitPolicy(WaitPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = TopologyLatents(self.mlp_extractor)
        self.action_net = TopologyHead(self.action_net)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class WaitMonitor(Monitor):
    def _on_rollout_start(self):
        super()._on_rollout_start()
        self.cases = {k: dict(played=0, trips=0, passed=0, builds=0) for k in STAGES}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done:
                case = self.cases[info['stage']]
                case['played'] += 1
                case['trips'] += info['trips']
                case['passed'] += int(info['success'])
                case['builds'] += info['builds']
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending['score_cases'] = self.cases
        print('WAIT | ' + ' | '.join(
            f'{key} {row["trips"]} trips/{row["played"]} games, {row["builds"]} builds'
            for key, row in self.cases.items()), flush=True)


def verify_reward(dll):
    env = ScoreWaitEnvironment(dll)
    results = []
    try:
        for stage in STAGES:
            env.reset(options=dict(stage=stage, split='validation', layout_seed=61000))
            total = 0
            for _ in range(DECISION_LIMIT):
                _, reward, ended, truncated, info = env.step(0)
                total += reward
                if ended:
                    break
            if truncated or total != info['trips'] or bool(total) != (stage == 'wait-zero'):
                raise RuntimeError('Only native trips may receive reward')
            results.append(dict(stage=stage, fixed_wait_only_trips=total, seconds=info['seconds']))
    finally:
        env.close()
    return results


def train(args):
    verification = verify_reward(args.dll)
    parent = MaskablePPO.load(args.checkpoint, device='cpu')
    if args.topology:
        env_class, policy_class, feature_class = TopologyWaitEnvironment, TopologyWaitPolicy, TopologyFeatures
        assignments = ['wait-zero'] * 4 + ['wait-one'] * 4 + ['wait-two'] * 8
    else:
        env_class, policy_class, feature_class = ScoreWaitEnvironment, WaitPolicy, WaitFeatures
        assignments = ['wait-zero'] * 6 + ['wait-one'] * 5 + ['wait-two'] * 5
    env = SubprocVecEnv([partial(env_class, args.dll, i, len(assignments), stage)
                        for i, stage in enumerate(assignments)], start_method='forkserver')
    try:
        model = MaskablePPO(
            policy_class, env, learning_rate=.004 if args.topology else .0007,
            n_steps=128, batch_size=128, n_epochs=4,
            gamma=1., gae_lambda=1., ent_coef=.01, target_kl=.025, device=args.device, seed=42,
            policy_kwargs=dict(features_extractor_class=feature_class, normalize_images=False,
                               optimizer_kwargs={'eps': 1e-5}))
        original = parent.policy.state_dict()
        weights = {key.replace('action_net.', 'action_net.base.', 1) if key.startswith('action_net.') else key: val
                   for key, val in original.items()}
        prefix = 'action_net.correction.' if args.topology else 'action_net.wait.'
        if not args.topology:
            weights['value_net.0.weight'] = torch.nn.functional.pad(original['value_net.0.weight'], (0, CLOCK_WIDTH))
        missing, unexpected = model.policy.load_state_dict(weights, strict=False)
        if unexpected or not missing or any(not name.startswith(prefix) for name in missing):
            raise RuntimeError('Unexpected difference from the paired parent')
        for name, parameter in model.policy.named_parameters():
            parameter.requires_grad_(name.startswith((prefix, 'value_net.')))
        args.output.mkdir(parents=True)
        write(args.output/'verification.json', verification)
        write(args.output/'config.json', dict(
            kind='score-wait-ppo', native_sha256=digest(args.dll), source_sha256=digest(__file__),
            parent=str(args.checkpoint), parent_sha256=digest(args.checkpoint),
            parent_fingerprint=policy_fingerprint(parent.policy), seed=42,
            decisions=args.decisions, wall_seconds=args.wall_seconds, assignments=assignments,
            teacher_actions=False, decision_limit=DECISION_LIMIT, wait_ticks=WAIT_TICKS,
            topology_correction=args.topology,
            reward='native tripsDelta only'))
        model.save(args.output/'initial.zip')
        monitor = WaitMonitor(args.output, args.wall_seconds)
        try:
            model.learn(total_timesteps=args.decisions, callback=monitor, progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        write(args.output/'status.json', dict(result=result, saved_decisions=monitor.completed_update_decisions,
            collected_decisions=model.num_timesteps, elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


def play(env, policy, lock, stage, seed, mode):
    obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
    generator = torch.Generator().manual_seed(100000 + seed)
    decisions = []
    reward_sum = 0.
    while True:
        mask = env.action_masks()
        if mode == 'always-wait':
            action = 0
        else:
            with lock, torch.inference_mode():
                tensor, _ = policy.obs_to_tensor(obs)
                probs = policy.get_distribution(tensor, action_masks=mask).distribution.probs[0]
                actions = np.flatnonzero(mask)
                legal = probs[actions]
                if mode == 'grouped-greedy':
                    pick = 0 if len(legal) == 1 or legal[0] >= legal[1:].sum() else 1 + int(legal[1:].argmax())
                elif mode == 'greedy':
                    pick = int(legal.argmax())
                else:
                    pick = int(torch.multinomial(legal, 1, generator=generator))
                action = int(actions[pick])
        obs, reward, ended, truncated, info = env.step(action)
        decisions.append(action)
        reward_sum += reward
        if ended or truncated:
            break
    if truncated or reward_sum != info['trips']:
        raise RuntimeError('Evaluation reward diverged from native score')
    return dict(info, seed=seed, actions=decisions)


def evaluate(args):
    model = MaskablePPO.load(args.checkpoint, device='cpu')
    policy = model.policy
    policy.set_training_mode(False)
    fingerprint = policy_fingerprint(policy)
    envs = []
    lock = Lock()
    results = {}
    env_class = TopologyWaitEnvironment if 'loose_ends' in model.observation_space.spaces else ScoreWaitEnvironment
    try:
        for _ in range(8):
            envs.append(env_class(args.dll))
        with ThreadPoolExecutor(max_workers=len(envs)) as pool:
            for mode in args.modes:
                for stage in STAGES:
                    rows = []
                    first = 61000 + args.offset
                    for start in range(first, first + args.count, len(envs)):
                        seeds = range(start, min(start + len(envs), first + args.count))
                        rows.extend(pool.map(lambda pair: play(pair[0], policy, lock, stage, pair[1], mode),
                                             zip(envs, seeds)))
                    results[f'{stage}/{mode}'] = rows
                    print(f'{stage}/{mode}: {sum(r["success"] for r in rows)}/{len(rows)} at three trips; '
                          f'{sum(r["trips"] for r in rows) / len(rows):.2f} mean trips', flush=True)
    finally:
        for env in envs:
            env.close()
    if policy_fingerprint(policy) != fingerprint:
        raise RuntimeError('Frozen policy was modified')
    write(args.output, dict(fingerprint=fingerprint, native_sha256=digest(args.dll),
                            checkpoint_sha256=digest(args.checkpoint), results=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('train', 'evaluate'))
    parser.add_argument('--dll', required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decisions', type=int, default=65536)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--topology', action='store_true')
    parser.add_argument('--modes', nargs='+', choices=('greedy', 'grouped-greedy', 'sampled', 'always-wait'),
                        default=['greedy', 'sampled'])
    parser.add_argument('--wall-seconds', type=int, default=720)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    args = parser.parse_args()
    if (min(args.decisions, args.wall_seconds, args.count) < 1 or args.decisions % 2048
            or args.offset < 0 or args.output.exists()):
        parser.error('Use a fresh output and a positive whole-rollout budget')
    torch.set_num_threads(2)
    if args.mode == 'train':
        train(args)
    else:
        evaluate(args)


if __name__ == '__main__':
    main()

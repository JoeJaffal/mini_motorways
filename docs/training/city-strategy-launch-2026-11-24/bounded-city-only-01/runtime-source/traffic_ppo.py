"""Reward-only Maskable PPO for choosing between native construction choices."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from math import isfinite
from pathlib import Path
from threading import Lock
from time import monotonic

import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.vec_env import SubprocVecEnv
from torch import nn

from bend_ppo import Monitor, digest, write
from connection_practice import ARENA_SIZE
from construction_practice import EDGE_END, endpoints
from hierarchy_rollout import policy_fingerprint
from traffic_practice import CHANNELS, JUNCTION, PRIORITY, PRIORITY_THREE, TrafficEnvironment, visible_traffic

N_EDGE = EDGE_END - 1
LOCAL_WIDTH = 32
EXERCISES = {'priority': PRIORITY, 'priority-three': PRIORITY_THREE, 'junction': JUNCTION}
SEEDS = {'priority': 76000, 'priority-three': 84000, 'junction': 78000}


class TrafficFeatures(BaseFeaturesExtractor):
    def __init__(self, observation_space):
        self.shop_count = observation_space['shops'].shape[0]
        self.edge_width = 2*LOCAL_WIDTH + 2 + 6*self.shop_count
        self.context_width = 2*LOCAL_WIDTH + 4 + 5*self.shop_count
        super().__init__(observation_space, features_dim=N_EDGE*self.edge_width + self.context_width)
        self.vision = nn.Sequential(nn.Conv2d(CHANNELS, LOCAL_WIDTH, 3, padding=1), nn.SiLU(),
                                    nn.Conv2d(LOCAL_WIDTH, LOCAL_WIDTH, 3, padding=1), nn.SiLU())
        ends = torch.tensor([endpoints(a) for a in range(1, EDGE_END)])
        valid = ((ends >= 0) & (ends < ARENA_SIZE)).all(dim=-1)
        ids = ends[..., 1]*ARENA_SIZE + ends[..., 0]
        self.register_buffer('indices', torch.where(valid, ids, ARENA_SIZE**2), persistent=False)
        self.register_buffer('midpoints', ends.float().mean(dim=1), persistent=False)
        self.register_buffer('directions', (ends[:, 1]-ends[:, 0]).float(), persistent=False)

    def forward(self, obs):
        vision = self.vision(obs['grid']).flatten(2).transpose(1, 2)
        extended = torch.nn.functional.pad(vision, (0, 0, 0, 1))
        one, two = extended[:, self.indices].unbind(dim=2)
        shops = obs['shops']
        delta = (shops[:, None, :, :2] - self.midpoints[None, :, None])/ARENA_SIZE
        demand = shops[:, None, :, 2:].expand(-1, N_EDGE, -1, -1)
        context = torch.cat((shops[..., :2]/ARENA_SIZE, shops[..., 2:]), dim=-1)
        context = torch.cat((vision.mean(dim=1), vision.amax(dim=1), obs['clock'], context.flatten(1)), dim=-1)
        axes = self.directions[None].expand(len(vision), -1, -1)
        alignment = (delta * axes[:, :, None]).sum(dim=-1).abs()
        edge = torch.cat((one+two, (one-two).abs(), delta.flatten(2), demand.flatten(2), axes, alignment), dim=-1)
        return torch.cat((edge.flatten(1), context), dim=-1)


class TrafficLatents(nn.Module):
    def __init__(self, features):
        super().__init__()
        self.edge_width = features.edge_width
        self.context_width = features.context_width

    def forward_actor(self, features):
        edges, context = features.split((N_EDGE*self.edge_width, self.context_width), dim=1)
        return edges.reshape(-1, N_EDGE, self.edge_width), context

    def forward_critic(self, features):
        return features[:, -self.context_width:]

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class TrafficHead(nn.Module):
    def __init__(self, features):
        super().__init__()
        self.context = nn.Sequential(nn.Linear(features.context_width, 24), nn.SiLU())
        self.edge = nn.Sequential(nn.Linear(features.edge_width+24, 48), nn.SiLU(), nn.Linear(48, 1))
        self.wait = nn.Sequential(nn.Linear(features.context_width, 24), nn.SiLU(), nn.Linear(24, 1))

    def forward(self, latent):
        edges, context = latent
        global_context = self.context(context)[:, None].expand(-1, N_EDGE, -1)
        road = self.edge(torch.cat((edges, global_context), dim=-1)).squeeze(-1)
        return torch.cat((self.wait(context), road), dim=-1)


class TrafficPolicy(MaskableActorCriticPolicy):
    def _build(self, lr_schedule):
        features = self.features_extractor
        self.mlp_extractor = TrafficLatents(features)
        self.action_net = TrafficHead(features)
        self.value_net = nn.Sequential(nn.Linear(features.context_width, 48), nn.SiLU(), nn.Linear(48, 1))
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


ROOT_WIDTH = 6


class RootFeatures(TrafficFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += N_EDGE * self.shop_count * ROOT_WIDTH

    def forward(self, obs):
        base = super().forward(obs)
        shops = obs['shops']
        root = torch.nn.functional.pad(obs['roots'].flatten(2), (0, 1))
        membership = root[:, :, self.indices].transpose(1, 2)
        relative = (shops[:, None, :, :2]-self.midpoints[None, :, None])/ARENA_SIZE
        demand = shops[:, None, :, 2:4].expand(-1, N_EDGE, -1, -1)
        features = torch.cat((membership.amax(dim=-1, keepdim=True), membership.amin(dim=-1, keepdim=True),
                              relative, demand), dim=-1)
        return torch.cat((base, features.flatten(1)), dim=1)


class RootLatents(TrafficLatents):
    def __init__(self, features):
        super().__init__(features)
        self.shop_count = features.shop_count
        self.base_width = N_EDGE*self.edge_width + self.context_width

    def forward_actor(self, features):
        base, relations = features.split((self.base_width, N_EDGE*self.shop_count*ROOT_WIDTH), dim=1)
        return super().forward_actor(base), relations.reshape(-1, N_EDGE, self.shop_count, ROOT_WIDTH)

    def forward_critic(self, features):
        return super().forward_critic(features[:, :self.base_width])


class RootHead(TrafficHead):
    def __init__(self, features):
        super().__init__(features)
        self.shop = nn.Sequential(nn.Linear(ROOT_WIDTH, 24), nn.SiLU(), nn.Linear(24, 1))

    def forward(self, latent):
        base, relations = latent
        logits = super().forward(base)
        residual = self.shop(relations).sum(dim=2).squeeze(-1)
        return torch.cat((logits[:, :1], logits[:, 1:]+residual), dim=1)


class RootPolicy(TrafficPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = RootLatents(self.features_extractor)
        self.action_net = RootHead(self.features_extractor)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class DemandHead(RootHead):
    def __init__(self, features):
        super().__init__(features)
        self.demand_weight = nn.Parameter(torch.zeros(()))

    def forward(self, latent):
        logits = super().forward(latent)
        relations = latent[1]
        # Combine visible pins with the existing component at each edge endpoint.
        # The initialized adjustment is zero. PPO learns its direction and size.
        demand = (relations[..., 0] * relations[..., 4]).sum(dim=-1)
        return torch.cat((logits[:, :1], logits[:, 1:]+6*self.demand_weight*demand), dim=1)


class DemandPolicy(RootPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.action_net = DemandHead(self.features_extractor)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


FLOW_WIDTH = 18


class FlowFeatures(RootFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += N_EDGE * FLOW_WIDTH
        xy = torch.arange(ARENA_SIZE**2)
        locations = torch.stack((xy % ARENA_SIZE, xy // ARENA_SIZE), dim=1).float()
        delta = self.midpoints[:, None] - locations
        distance = delta.square().sum(dim=-1).sqrt()
        self.register_buffer('locality', torch.exp(-distance/2), persistent=False)

    def forward(self, obs):
        base = super().forward(obs)
        traffic = obs['grid'][:, [19, 20, 21, 23]].flatten(2)
        close = torch.einsum('et,bct->bec', self.locality, traffic)
        total = traffic.sum(dim=-1)/3
        midpoint = (self.midpoints[None] - obs['shops'][:, :, :2].mean(dim=1, keepdim=True))/ARENA_SIZE
        total_per_edge = total[:, None].expand(-1, N_EDGE, -1)
        interactions = (midpoint[..., None] * total_per_edge[:, :, None]).flatten(2)
        features = torch.cat((close, total_per_edge, midpoint, interactions), dim=-1)
        return torch.cat((base, features.flatten(1)), dim=1)


class FlowLatents(RootLatents):
    def forward_actor(self, features):
        return super().forward_actor(features[:, :-N_EDGE*FLOW_WIDTH]), features[:, -N_EDGE*FLOW_WIDTH:].reshape(
            -1, N_EDGE, FLOW_WIDTH)

    def forward_critic(self, features):
        return super().forward_critic(features[:, :-N_EDGE*FLOW_WIDTH])


class FlowHead(RootHead):
    def __init__(self, features):
        super().__init__(features)
        self.flow = nn.Sequential(nn.Linear(FLOW_WIDTH, 32), nn.SiLU(), nn.Linear(32, 1))
        nn.init.zeros_(self.flow[-1].weight)
        nn.init.zeros_(self.flow[-1].bias)

    def forward(self, latent):
        prior, context = latent
        logits = super().forward(prior)
        adjustment = self.flow(context).squeeze(-1)
        return torch.cat((logits[:, :1], logits[:, 1:]+adjustment), dim=1)


class FlowPolicy(RootPolicy):
    head_class = FlowHead
    latents_class = FlowLatents

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = self.latents_class(self.features_extractor)
        self.action_net = self.head_class(self.features_extractor)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class FlowRelationHead(FlowHead):
    def __init__(self, features):
        super().__init__(features)
        self.link_context = nn.Linear(10, 1, bias=False)
        nn.init.zeros_(self.link_context.weight)

    def forward(self, latent):
        prior, context = latent
        logits = super().forward(latent)
        membership = prior[1][..., :2].amax(dim=-2)
        connected, same_network = membership.unbind(dim=-1)
        # A candidate can attach one free endpoint or close a loop within
        # an existing shop component. Traffic changes the learned value of either.
        link_kind = torch.stack((connected - same_network, same_network), dim=-1)
        car_counts = context[..., 4:8]
        signals = torch.cat((torch.ones_like(car_counts[..., :1]), car_counts), dim=-1)
        adjustment = self.link_context((link_kind[..., None] * signals[..., None, :]).flatten(2)).squeeze(-1)
        return torch.cat((logits[:, :1], logits[:, 1:] + adjustment), dim=1)


class FlowRelationPolicy(FlowPolicy):
    head_class = FlowRelationHead


ENDPOINT_WIDTH = 2


class EndpointFeatures(FlowFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += N_EDGE * ENDPOINT_WIDTH

    def forward(self, obs):
        base = super().forward(obs)
        degree = obs['grid'][:, 8:16].sum(dim=1).flatten(1)
        degree = torch.nn.functional.pad(degree, (0, 1))
        terminal_count = (degree[:, self.indices] == 1).sum(dim=-1)
        terminals = torch.stack((terminal_count == 1, terminal_count == 2), dim=-1)
        return torch.cat((base, terminals.to(base.dtype).flatten(1)), dim=1)


class EndpointLatents(FlowLatents):
    def forward_actor(self, features):
        split = N_EDGE * ENDPOINT_WIDTH
        prior, flow = super().forward_actor(features[:, :-split])
        return prior, flow, features[:, -split:].reshape(-1, N_EDGE, ENDPOINT_WIDTH)

    def forward_critic(self, features):
        return super().forward_critic(features[:, :-N_EDGE*ENDPOINT_WIDTH])


class EndpointHead(FlowHead):
    def __init__(self, features):
        super().__init__(features)
        self.endpoint_context = nn.Linear(10, 1, bias=False)
        nn.init.zeros_(self.endpoint_context.weight)

    def forward(self, latent):
        prior, flow, terminals = latent
        logits = super().forward((prior, flow))
        # Score one or two visible road ends in a current shop component.
        # PPO learns what the local degree means under the observed car load.
        connected = prior[1][..., 0].amax(dim=-1, keepdim=True)
        counts = flow[..., 4:8]
        context = torch.cat((torch.ones_like(counts[..., :1]), counts), dim=-1)
        inputs = (connected[..., None] * terminals[..., None] * context[..., None, :]).flatten(2)
        adjustment = self.endpoint_context(inputs).squeeze(-1)
        return torch.cat((logits[:, :1], logits[:, 1:] + adjustment), dim=1)


class EndpointPolicy(FlowPolicy):
    head_class = EndpointHead
    latents_class = EndpointLatents


class TopologyEndpointHead(nn.Module):
    """Score road ends and traffic with the same actor at every location."""

    def __init__(self, features):
        super().__init__()
        self.wait = nn.Sequential(nn.Linear(10, 24), nn.SiLU(), nn.Linear(24, 1))
        self.edge = nn.Sequential(nn.Linear(18, 48), nn.SiLU(), nn.Linear(48, 1))

    def forward(self, latent):
        prior, flow, terminals = latent
        (_, board_context), relations = prior
        # The actor uses visible clock, demand and car totals across the board.
        # Existing shop components and local traffic are evaluated per edge.
        clock = board_context[:, 2*LOCAL_WIDTH:2*LOCAL_WIDTH+4]
        demand = relations[:, 0, :, 4:6].mean(dim=1)
        context = torch.cat((clock, demand, flow[:, 0, 4:8]), dim=-1)
        reach = relations[..., :2].mean(dim=-2)
        shared_context = context[:, None].expand(-1, N_EDGE, -1)
        edge = torch.cat((terminals, reach, flow[..., :4], shared_context), dim=-1)
        return torch.cat((self.wait_score(context), self.edge(edge).squeeze(-1)), dim=1)

    def wait_score(self, context):
        return self.wait(context)


class TopologyEndpointPolicy(EndpointPolicy):
    head_class = TopologyEndpointHead


class ClockTopologyEndpointHead(TopologyEndpointHead):
    def __init__(self, features):
        super().__init__(features)
        self.wait_clock = nn.Parameter(torch.zeros(2))

    def wait_score(self, context):
        # The early and later preferences are trainable. Time is observable.
        early = ((.35 - context[:, :1]) / .20).clamp(0., 1.)
        return self.wait(context) + early*self.wait_clock[0] + (1-early)*self.wait_clock[1]


class ClockTopologyEndpointPolicy(TopologyEndpointPolicy):
    head_class = ClockTopologyEndpointHead


class TrainingTraffic(TrafficEnvironment):
    """Collapse a sequence of forced Waits into one native advance."""

    def __init__(self, *args, warm_min=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.warm_min = warm_min
        self.warm_max = self.warm_seconds

    def reset(self, *, seed=None, options=None):
        if self.warm_min is not None and options is None:
            layout_seed = self.seed_start + self.worker + self.workers*self.episode
            generator = np.random.default_rng([layout_seed, 7951])
            self.warm_seconds = int(generator.integers(self.warm_min, self.warm_max + 1))
        return super().reset(seed=seed, options=options)

    def step(self, action):
        if action != 0 or self.env.legal[1:].any():
            return super().step(action)
        previous = self.wait_ticks
        self.wait_ticks = round(self.horizon*20)
        try:
            return super().step(0)
        finally:
            self.wait_ticks = previous


class TrafficMonitor(Monitor):
    def _on_rollout_start(self):
        super()._on_rollout_start()
        self.by_stage = {}

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if not done:
                continue
            row = self.by_stage.setdefault(info['stage'], dict(games=0, trips=0, native_failures=0))
            row['games'] += 1
            row['trips'] += info['trips']
            row['native_failures'] += int(info['native_failure'])
            time = info['first_build_time']
            row['games_built'] = row.get('games_built', 0) + int(time is not None)
            row['games_built_before_20'] = row.get('games_built_before_20', 0) + int(time is not None and time < 20)
            row['games_built_immediately'] = row.get('games_built_immediately', 0) + int(time == info['started_at'])
            row['build_seconds'] = row.get('build_seconds', 0.) + (time if time is not None else 0.)
            self.games += 1
            self.successes += int(info['trips'] > 0)
        self.stopped_by_wall = monotonic() >= self.deadline
        return not self.stopped_by_wall

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending['stages'] = self.by_stage
        weight = getattr(self.model.policy.action_net, 'demand_weight', None)
        if weight is not None:
            self.pending['demand_weight'] = float(weight.detach().cpu())
        print('TRAFFIC | ' + ' | '.join(f'{s}: {v["trips"]/v["games"]:.2f} trips / {v["games"]} games'
                                       for s, v in self.by_stage.items()), flush=True)

    def _record_update(self):
        if self.pending is not None:
            metrics = self.model.logger.name_to_value
            self.pending['optimizer'] = {name: float(value) for name, value in metrics.items()
                                         if name.startswith('train/') and isfinite(value)}
        super()._record_update()


def run_layout(env, policy, mutex, stage, seed, mode):
    obs, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
    raw = env.env.raw
    before_pins = [int(b['demand']) for b in raw['buildings'] if not b['isHouse']]
    before_cars = len(visible_traffic(raw))
    labels = env.env.controls() if mode not in ('greedy', 'sampled') else {}
    control, _, suffix = mode.partition('@')
    scheduled_time = int(suffix) if suffix else 0
    sequence = [labels[name] for name in control.split('+')] if policy is None and control != 'wait' else []
    used_edits = 0
    generator = torch.Generator().manual_seed(280000+seed)
    total = 0.
    while True:
        mask = env.action_masks()
        if policy is None:
            should_build = env.env.raw['time'] >= scheduled_time - 1e-6 and used_edits < len(sequence)
            action = sequence[used_edits] if should_build else 0
            used_edits += int(should_build)
        elif not mask[1:].any():
            # Keep the sampled random stream identical to masked inference.
            if mode == 'sampled':
                torch.multinomial(torch.ones(1), 1, generator=generator)
            action = 0
        else:
            with mutex, torch.inference_mode():
                values = policy.obs_to_tensor(obs)[0]
                probs = policy.get_distribution(values, action_masks=mask).distribution.probs[0]
                actions = np.flatnonzero(mask)
                legal = probs[actions]
                selected = int(legal.argmax()) if mode == 'greedy' else int(torch.multinomial(legal, 1, generator=generator))
                action = int(actions[selected])
        obs, reward, done, truncated, info = env.step(action)
        total += reward
        if done or truncated:
            break
    if truncated or total != info['trips'] or info['spent'] > env.env.inventory:
        raise RuntimeError('Frozen play diverged from native stock or score')
    return dict(info, initial_pins=before_pins, initial_visible_cars=before_cars)


def evaluate(args, stages, environment_class=TrafficEnvironment):
    model = MaskablePPO.load(args.checkpoint, device='cpu') if args.mode == 'evaluate' else None
    policy = model.policy if model else None
    initial = policy_fingerprint(policy) if policy else None
    if policy:
        policy.set_training_mode(False)
    results = {}
    mutex = Lock()
    envs = []
    shop_count = 3 if args.exercise == 'priority-three' else 2
    try:
        for _ in range(args.workers):
            envs.append(environment_class(args.dll, horizon=args.horizon, wait_ticks=args.wait_ticks,
                                          warm_seconds=args.warm_seconds, use_roots=bool(
                                              model and 'roots' in model.observation_space.spaces),
                                          shop_count=shop_count))
        with ThreadPoolExecutor(max_workers=len(envs)) as pool:
            for stage in stages:
                if policy is not None:
                    modes = ('greedy', 'sampled')
                else:
                    if '-stock' in stage:
                        modes = ('share+feeder', 'separate-entry+separate-exit', 'share', 'wait')
                    elif '-live' in stage:
                        modes = ('feeder', 'separate-exit', 'wait')
                    elif stage in PRIORITY_THREE:
                        modes = ('upper+center', 'upper+lower', 'center+lower', 'wait')
                    else:
                        modes = ('upper', 'lower', 'wait') if stage in PRIORITY else ('share', 'separate', 'wait')
                    if args.control_delays:
                        modes = tuple(f'{mode}@{seconds}' for mode in modes if mode != 'wait'
                                      for seconds in args.control_delays) + ('wait',)
                for mode in modes:
                    first = SEEDS[args.exercise]+args.offset
                    rows = []
                    for start in range(first, first+args.count, len(envs)):
                        seeds = range(start, min(first+args.count, start+len(envs)))
                        rows.extend(pool.map(lambda pair: run_layout(pair[0], policy, mutex, stage, pair[1], mode),
                                             zip(envs, seeds)))
                    results[f'{stage}/{mode}'] = rows
                    print(f'{stage}/{mode} | {np.mean([r["trips"] for r in rows]):.2f} trips | '
                          f'{np.mean([r["stopped_cars_mean"] for r in rows]):.2f} stopped cars | '
                          f'{sum(r["native_failure"] for r in rows)} failures', flush=True)
    finally:
        for env in envs:
            env.close()
    if policy is not None and policy_fingerprint(policy) != initial:
        raise RuntimeError('Frozen evaluation changed weights')
    write(args.output, dict(results=results, native_sha256=digest(args.dll), horizon=args.horizon,
                            warm_seconds=args.warm_seconds, wait_ticks=args.wait_ticks, fingerprint=initial,
                            checkpoint_sha256=digest(args.checkpoint) if policy else None))


def train(args, stages):
    shop_count = 3 if args.exercise == 'priority-three' else 2
    env = SubprocVecEnv([partial(TrainingTraffic, args.dll, stages[i % len(stages)], i, args.workers,
                                 horizon=args.horizon, wait_ticks=args.wait_ticks, warm_seconds=args.warm_seconds,
                                 warm_min=args.warm_min,
                                 seed_start=args.seed_start, use_roots=args.roots, shop_count=shop_count)
                        for i in range(args.workers)], start_method='forkserver')
    try:
        if args.checkpoint is None or args.clock_wait_init is not None:
            if args.clock_wait_init is not None:
                actor = ClockTopologyEndpointPolicy
            elif args.endpoint_relation:
                actor = TopologyEndpointPolicy if args.endpoint_topology else EndpointPolicy
            else:
                actor = FlowRelationPolicy if args.flow_relation else (
                    FlowPolicy if args.flow else DemandPolicy if args.demand_relation else (
                        RootPolicy if args.roots else TrafficPolicy))
            encoder = EndpointFeatures if args.endpoint_relation else (
                FlowFeatures if args.flow else RootFeatures if args.roots else TrafficFeatures)
            model = MaskablePPO(
                actor, env, learning_rate=args.learning_rate,
                n_steps=128, batch_size=128, n_epochs=4,
                gamma=1., gae_lambda=1., ent_coef=args.entropy, target_kl=.025, device=args.device, seed=args.seed,
                policy_kwargs=dict(features_extractor_class=encoder, normalize_images=False,
                                   optimizer_kwargs={'eps': 1e-5}))
            if args.clock_wait_init is not None:
                parent = MaskablePPO.load(args.checkpoint, device=args.device)
                missing, unexpected = model.policy.load_state_dict(parent.policy.state_dict(), strict=False)
                if missing != ['action_net.wait_clock'] or unexpected:
                    raise ValueError('Clock exploration requires an unmodified topology checkpoint')
                with torch.no_grad():
                    model.policy.action_net.wait_clock[0] = args.clock_wait_init
                model.num_timesteps = parent.num_timesteps
        else:
            model = MaskablePPO.load(args.checkpoint, env=env, device=args.device,
                                     custom_objects=dict(learning_rate=args.learning_rate, ent_coef=args.entropy))
        if args.wait_logit_offset:
            with torch.no_grad():
                model.policy.action_net.wait[-1].bias.add_(args.wait_logit_offset)
        if args.train_wait_only or args.train_roads_only:
            # This actor's road scores depend on fixed observation transforms.
            # The learned convolution remains in the critic path.
            # SB3 can reconstruct the saved __main__ class by value.
            if type(model.policy.action_net).__name__ not in (
                TopologyEndpointHead.__name__, ClockTopologyEndpointHead.__name__,
            ):
                raise ValueError('Head-specific training requires the coordinate-independent topology actor')
            if args.train_wait_only:
                model.policy.action_net.edge.requires_grad_(False)
            else:
                head = model.policy.action_net
                head.wait.requires_grad_(False)
                if hasattr(head, 'wait_clock'):
                    head.wait_clock.requires_grad_(False)
        args.output.mkdir(parents=True)
        start = model.num_timesteps
        write(args.output/'config.json', dict(
            source_sha256=digest(__file__), observation_sha256=digest(Path(__file__).with_name('traffic_practice.py')),
            native_sha256=digest(args.dll),
            checkpoint=str(args.checkpoint) if args.checkpoint else None, stages=stages,
            start=start, horizon=args.horizon, wait_ticks=args.wait_ticks, warm_seconds=args.warm_seconds,
            warm_min=args.warm_min,
            decisions=args.decisions, wall_seconds=args.wall_seconds, device=args.device,
            workers=args.workers, seed=args.seed, seed_start=args.seed_start,
            learning_rate=args.learning_rate, entropy=args.entropy, wait_logit_offset=args.wait_logit_offset,
            train_wait_only=args.train_wait_only, train_roads_only=args.train_roads_only,
            clock_wait_init=args.clock_wait_init,
            fresh_optimizer=args.checkpoint is None or args.clock_wait_init is not None,
            roots=args.roots,
            flow=args.flow, flow_relation=args.flow_relation, endpoint_relation=args.endpoint_relation,
            endpoint_topology=args.endpoint_topology,
            demand_relation=args.demand_relation,
            reward='native tripsDelta only',
            teacher_actions=False, forced_wait_compaction=True))
        model.save(args.output/'initial.zip')
        monitor = TrafficMonitor(args.output, args.wall_seconds)
        monitor.completed_update_decisions = start
        try:
            model.learn(total_timesteps=args.decisions, callback=monitor, reset_num_timesteps=False,
                        progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        write(args.output/'status.json', dict(result=result, saved_decisions=monitor.completed_update_decisions,
              collected_decisions=model.num_timesteps, elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('train', 'evaluate', 'controls'))
    parser.add_argument('--exercise', choices=tuple(SEEDS), required=True)
    parser.add_argument('--stages', nargs='+', help='Explicit native stages within this exercise')
    parser.add_argument('--dll', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--horizon', type=int, default=100)
    parser.add_argument('--wait-ticks', type=int, default=200)
    parser.add_argument('--warm-seconds', type=int, default=18)
    parser.add_argument('--warm-min', type=int, help='Earliest training start when sampling a warmup range')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--control-delays', nargs='+', type=int, help='Absolute seconds before the scripted control edit')
    parser.add_argument('--decisions', type=int, default=65536)
    parser.add_argument('--wall-seconds', type=int, default=1200)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--seed-start', type=int, default=2370000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--learning-rate', type=float, default=.0006)
    parser.add_argument('--entropy', type=float, default=.015)
    parser.add_argument('--wait-logit-offset', type=float, default=0.,
                        help='Optional initial Wait bias for prior-to-surge exploration')
    head_training = parser.add_mutually_exclusive_group()
    head_training.add_argument('--train-wait-only', action='store_true',
                               help='Hold the topology actor’s road scores fixed while learning Wait')
    head_training.add_argument('--train-roads-only', action='store_true',
                               help='Hold the topology actor’s Wait score fixed while learning road choices')
    parser.add_argument('--clock-wait-init', type=float,
                        help='Warm-start a trainable clock-dependent Wait preference with fresh Adam')
    parser.add_argument('--roots', action='store_true', help='Expose only components of currently constructed edges')
    parser.add_argument('--demand-relation', action='store_true', help='Learn a preference from current pins and components')
    parser.add_argument('--flow', action='store_true', help='Use visible car density and speed around candidate edits')
    parser.add_argument('--flow-relation', action='store_true',
                        help='Learn how visible traffic changes the value of links within or onto existing roads')
    parser.add_argument('--endpoint-relation', action='store_true',
                        help='Learn how traffic changes the value of joining visible road ends')
    parser.add_argument('--endpoint-topology', action='store_true',
                        help='Score visible road ends and traffic without coordinate inputs to the actor')
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    args = parser.parse_args()
    args.endpoint_topology = args.endpoint_topology or args.clock_wait_init is not None
    args.endpoint_relation = args.endpoint_relation or args.endpoint_topology
    args.flow = args.flow or args.flow_relation or args.endpoint_relation
    args.roots = args.roots or args.demand_relation or args.flow
    if args.output.exists() or min(args.workers, args.count, args.wait_ticks, args.horizon) < 1:
        parser.error('Use new output and positive dimensions')
    if args.mode == 'evaluate' and args.checkpoint is None:
        parser.error('Frozen evaluation requires a checkpoint')
    if not isfinite(args.wait_logit_offset):
        parser.error('Wait initialization must be finite')
    if args.clock_wait_init is not None and (args.checkpoint is None or not isfinite(args.clock_wait_init)):
        parser.error('Clock exploration needs a topology checkpoint and a finite initial preference')
    if args.warm_min is not None and (args.mode != 'train' or not 0 <= args.warm_min <= args.warm_seconds):
        parser.error('The training warmup range must be nonnegative and end at the configured warmup')
    if args.mode == 'train' and (args.decisions < 1 or args.decisions % (128*args.workers)):
        parser.error('Training requires a positive whole-rollout decision budget')
    torch.set_num_threads(2)
    stages = tuple(args.stages) if args.stages else EXERCISES[args.exercise]
    if any(stage.startswith('traffic-junction') for stage in stages) and not 0 <= args.warm_seconds < args.horizon:
        parser.error('Junction warmup must finish before the episode horizon')
    if args.mode == 'train':
        train(args, stages)
    else:
        evaluate(args, stages)


if __name__ == '__main__':
    main()

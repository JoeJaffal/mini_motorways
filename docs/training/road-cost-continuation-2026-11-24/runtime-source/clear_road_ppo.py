"""Frozen evaluation and reward-only PPO on clear-land roads."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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

import bend_ppo
from bend_ppo import BendEnvironment, CompactEdgeFeatures, Monitor, digest, write
from construction_practice import EDGE_END, advance, endpoints, tile
from edge_policy import EDGE_SLOTS, EDGE_WIDTH, EdgeActionHead, SharedEdgePolicy
from environment import DIRS
from hierarchy_rollout import policy_fingerprint

EVAL_SEEDS = {'adjacent': 30000, 'bend': 32000, 'clear': 36000}
GEOMETRY_CHANNELS = 12


class ClearRoadEnvironment(BendEnvironment):
    def __init__(self, dll, worker=0, workers=1, exercise='clear', *, parent_inputs=False):
        super().__init__(dll, worker=worker, workers=workers)
        self.exercise = exercise
        self.parent_inputs = parent_inputs
        if not parent_inputs:
            self.observation_space.spaces['anchors'] = gym.spaces.Box(-2, 13, (2, 2), np.float32)

    def _observation(self, observation):
        if self.parent_inputs:
            return observation
        home, = (b for b in self.env.raw['buildings'] if b['isHouse'])
        shop = self.env.shop
        anchors = np.array([
            self.env.local(advance(tile(home['cell']), home['drivewayDirection'])),
            self.env.local(advance(tile(shop['entrance']), shop['drivewayDirection'])),
        ], dtype=np.float32)
        return dict(observation, anchors=anchors)

    def reset(self, *, seed=None, options=None):
        if options is None:
            layout_seed = 90000 + self.worker + self.workers*self.episode
            self.episode += 1
            options = dict(stage=self.exercise, split='train', layout_seed=layout_seed)
        observation, info = super().reset(seed=seed, options=options)
        return self._observation(observation), info

    def step(self, action):
        observation, reward, terminated, truncated, info = super().step(action)
        return self._observation(observation), reward, terminated, truncated, {
            **info, 'stage': self.env.stage,
        }


class GoalAwareFeatures(CompactEdgeFeatures):
    """Augment local edge features with displacements to visible driveway approaches."""

    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim = EDGE_SLOTS * (EDGE_WIDTH + GEOMETRY_CHANNELS)
        pairs = torch.tensor([endpoints(a) for a in range(1, EDGE_END)], dtype=torch.float32)
        self.register_buffer('midpoints', pairs.mean(dim=1), persistent=False)
        self.register_buffer('half_edges', (pairs[:, 1]-pairs[:, 0])/2, persistent=False)
        self.register_buffer('pairs', pairs, persistent=False)

    def forward(self, observations):
        features = super().forward(observations).reshape(-1, EDGE_SLOTS, EDGE_WIDTH)
        anchors = observations['anchors']
        midpoint_delta = (anchors[:,None] - self.midpoints[None,:,None])/12
        delta = (anchors[:,None,:,None] - self.pairs[None,:,None])/12
        distances = delta.abs().amax(dim=-1)
        geometry = torch.cat((midpoint_delta.flatten(2), distances.amin(dim=-1), distances.amax(dim=-1),
                              self.half_edges[None].expand(len(anchors),-1,-1),
                              (midpoint_delta * self.half_edges[None,:,None]).sum(dim=-1).abs()), dim=-1)
        return torch.cat((features, geometry), dim=-1).flatten(1)


class GoalLatents(nn.Module):
    def forward_actor(self, features):
        return features.reshape(-1, EDGE_SLOTS, EDGE_WIDTH + GEOMETRY_CHANNELS)

    def forward_critic(self, features):
        local = self.forward_actor(features)[..., :EDGE_WIDTH]
        return torch.cat((local.mean(dim=1), local.amax(dim=1)), dim=-1)

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class GoalAwareHead(EdgeActionHead):
    def __init__(self):
        super().__init__()
        self.context = nn.Sequential(
            nn.Linear(EDGE_WIDTH + GEOMETRY_CHANNELS, 48), nn.SiLU(), nn.Linear(48, 1)
        )
        nn.init.zeros_(self.context[-1].weight)
        nn.init.zeros_(self.context[-1].bias)

    def forward(self, edges):
        base = super().forward(edges[..., :EDGE_WIDTH])
        bonus = self.context(edges).squeeze(-1)
        return base + torch.cat((bonus.new_zeros((len(bonus), 1)), bonus), dim=1)


class GoalAwarePolicy(SharedEdgePolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = GoalLatents()
        self.action_net = GoalAwareHead()
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


def checked_checkpoint(path, dll):
    config = json.loads(Path(path).with_name('config.json').read_text())
    source = __file__ if config.get('kind') == 'clear-road-ppo' else bend_ppo.__file__
    if config['native_sha256'] != digest(dll) or config['source_sha256'] != digest(source):
        raise ValueError('Checkpoint host binary or runner source differs')
    return MaskablePPO.load(path, device='cpu')


def geometry(env):
    shop = env.shop
    home = env.house
    dx,dy = DIRS[shop['drivewayDirection']]
    x,y = advance(tile(shop['entrance']), shop['drivewayDirection'])
    hx,hy = tile(home['cell'])
    return dict(distance=(hx-x)*dx+(hy-y)*dy, offset=(hx-x)*-dy+(hy-y)*dx)


def evaluate(args, model, output):
    policy = model.policy
    before = policy_fingerprint(policy)
    parent_inputs = 'anchors' not in policy.observation_space.spaces
    envs = []
    rows = []
    try:
        for _ in range(args.eval_workers):
            envs.append(ClearRoadEnvironment(args.dll, parent_inputs=parent_inputs))
        with ThreadPoolExecutor(max_workers=len(envs)) as pool:
            for stage in args.stages:
                start = EVAL_SEEDS[stage] + args.eval_offset
                for offset in range(0, 100, len(envs)):
                    active_count = min(100-offset, len(envs))
                    group = envs[:active_count]
                    seeds = [start+offset+i for i in range(active_count)]
                    records = [dict(stage=stage, seed=seed, actions=[]) for seed in seeds]
                    observations = [
                        o for o,_ in pool.map(lambda pair: pair[0].reset(options=dict(
                            stage=stage, split='validation', layout_seed=pair[1])), zip(group,seeds))
                    ]
                    for env,row in zip(group,records):
                        row.update(geometry(env.env))
                    active = list(range(active_count))
                    rngs = [torch.Generator().manual_seed(100000+seed) for seed in seeds]
                    while active:
                        merged = {k:np.stack([observations[i][k] for i in active])
                                  for k in observations[active[0]]}
                        masks = np.stack([group[i].action_masks() for i in active])
                        with torch.inference_mode():
                            tensor,_ = policy.obs_to_tensor(merged)
                            probs = policy.get_distribution(tensor, action_masks=masks).distribution.probs
                            actions = (probs.argmax(dim=1).tolist() if not args.sample else
                                [int(torch.multinomial(row, 1, generator=rngs[i]))
                                 for i,row in zip(active,probs)])
                        results = list(pool.map(lambda pair: pair[0].step(pair[1]),
                                                zip((group[i] for i in active), actions)))
                        remaining = []
                        for i, action, (obs, _, done, truncated, info) in zip(active, actions, results):
                            if truncated:
                                raise RuntimeError('Construction evaluation truncated')
                            observations[i] = obs
                            records[i]['actions'].append(action)
                            if not done:
                                remaining.append(i)
                            else:
                                records[i].update(connected=info['connected'], used=info['road_units_spent'])
                        active = remaining
                    outcomes = pool.map(lambda env: env.env.deliveries(), group)
                    for row,(trips, seconds) in zip(records,outcomes):
                        rows.append(dict(row, trips=trips, seconds=seconds))
                print('Evaluated',stage,flush=True)
    finally:
        for env in envs:
            env.close()
    if policy_fingerprint(policy) != before:
        raise RuntimeError('Frozen evaluation changed model weights')
    summary = {}
    for stage in args.stages:
        matching = [r for r in rows if r['stage']==stage]
        summary[stage] = dict(delivered=sum(r['trips']>=3 for r in matching), layouts=len(matching),
            mean_trips=float(np.mean([r['trips'] for r in matching])),
            mean_road_units=float(np.mean([r['used'] for r in matching])))
    write(output/'results.json',dict(fingerprint=before,sampled=args.sample,optimizer_updates=0,
                                    summary=summary,layouts=rows))
    print(json.dumps(summary),flush=True)


def preflight(parent, child, dll):
    env = ClearRoadEnvironment(dll)
    try:
        for stage,seed in [('clear',36000),('bend',32000),('adjacent',30000)]:
            observation,_ = env.reset(options=dict(stage=stage,split='validation',layout_seed=seed))
            mask = env.action_masks()
            with torch.inference_mode():
                prior,_ = parent.obs_to_tensor({'grid':observation['grid']})
                current,_ = child.obs_to_tensor(observation)
                old = parent.get_distribution(prior,action_masks=mask).distribution.logits
                new = child.get_distribution(current,action_masks=mask).distribution.logits.cpu()
                torch.testing.assert_close(old,new,atol=2e-5,rtol=2e-5)
    finally:
        env.close()


def train(args, output):
    parent = checked_checkpoint(args.checkpoint,args.dll)
    exercises = ['clear']*(args.workers-4) + ['bend']*2 + ['adjacent']*2
    env = SubprocVecEnv(
        [partial(ClearRoadEnvironment, args.dll, i, args.workers, exercise)
         for i,exercise in enumerate(exercises)], start_method='forkserver')
    try:
        model = MaskablePPO(GoalAwarePolicy, env, learning_rate=1e-4, n_steps=128,
            batch_size=128, n_epochs=4, gamma=1., gae_lambda=1., ent_coef=.01, target_kl=.02,
            seed=42, device=args.device, verbose=0,
            policy_kwargs=dict(features_extractor_class=GoalAwareFeatures, normalize_images=False,
                               optimizer_kwargs={'eps':1e-5}))
        incompatible = model.policy.load_state_dict(parent.policy.state_dict(), strict=False)
        if (incompatible.unexpected_keys or set(incompatible.missing_keys) !=
                {f'action_net.context.{i}.{k}' for i in (0,2) for k in ('bias','weight')}):
            raise RuntimeError('Unexpected weights differ from the reward-trained parent')
        preflight(parent.policy,model.policy,args.dll)
        write(output/'config.json',dict(kind='clear-road-ppo',parent=str(args.checkpoint),
            parent_fingerprint=policy_fingerprint(parent.policy),initial_fingerprint=policy_fingerprint(model.policy),
            native_sha256=digest(args.dll),source_sha256=digest(__file__),seed=42,worker_exercises=exercises,
            optimizer='fresh Adam',learning_rate=1e-4,ent_coef=.01,gamma=1.,gae_lambda=1.,
            rollout_steps_per_worker=128,batch_size=128,epochs=4,target_kl=.02,
            teacher_actions=False,visibility='relative positions of visible approaches, no routes',
            decision_budget=args.decisions,wall_seconds=args.wall_seconds))
        model.save(output/'initial.zip')
        monitor = ClearMonitor(output,args.wall_seconds)
        try:
            model.learn(total_timesteps=args.decisions, callback=monitor, progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        write(output/'status.json',dict(result=result,
            saved_decisions=monitor.completed_update_decisions,collected_decisions=model.num_timesteps,
            elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


class ClearMonitor(Monitor):
    def _on_rollout_start(self):
        super()._on_rollout_start()
        self.by_exercise = {stage:[0,0] for stage in EVAL_SEEDS}

    def _on_step(self):
        for done,info in zip(self.locals['dones'],self.locals['infos']):
            if done:
                counts = self.by_exercise[info['stage']]
                counts[0] += int(info['connected'])
                counts[1] += 1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending['exercises'] = self.by_exercise
        solved,total = self.by_exercise['clear']
        print(f'CLEAR | {solved}/{total} connected | {self.num_timesteps} build decisions collected',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('evaluate','train'))
    p.add_argument('--dll',required=True)
    p.add_argument('--checkpoint',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--sample',action='store_true')
    p.add_argument('--stages',nargs='+',choices=tuple(EVAL_SEEDS),default=['clear'])
    p.add_argument('--eval-workers',type=int,default=10)
    p.add_argument('--eval-offset',type=int,default=0)
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--decisions',type=int,default=131072)
    p.add_argument('--wall-seconds',type=int,default=1800)
    p.add_argument('--device',choices=('cuda','cpu'),default='cuda')
    args=p.parse_args()
    if args.eval_workers<1 or args.eval_offset<0:
        p.error('Invalid evaluation bounds')
    if args.mode=='train' and (args.workers < 5 or min(args.decisions,args.wall_seconds)<1
                               or args.decisions % (args.workers*128)):
        p.error('Need at least five workers and a positive whole-rollout budget')
    torch.set_num_threads(2)
    output=Path(args.output)
    output.mkdir(parents=True)
    if args.mode=='train':
        train(args,output)
    else:
        evaluate(args,checked_checkpoint(args.checkpoint,args.dll),output)


if __name__=='__main__':
    main()

"""Reward-only, distance-staged PPO for two-tile lateral offsets."""
import argparse
from collections import deque
from functools import partial
import json
from pathlib import Path
from time import monotonic

import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import SubprocVecEnv

from bend_ppo import Monitor, digest, write
from clear_road_ppo import ClearRoadEnvironment, GoalAwarePolicy, checked_checkpoint, evaluate, geometry
from construction_practice import advance, tile
from environment import DIRS
from hierarchy_rollout import policy_fingerprint

TEMPERATURES = {2:4., 3:4., 4:3.5, 5:3., 6:2.5, 7:2.}


class ExplorationPolicy(GoalAwarePolicy):
    temperature = 1.

    def _get_action_dist_from_latent(self, latent_pi):
        logits = self.action_net(latent_pi) / self.temperature
        return self.action_dist.proba_distribution(action_logits=logits)


def layout_geometry(raw):
    home, = (b for b in raw['buildings'] if b['isHouse'])
    shop, = (b for b in raw['buildings'] if not b['isHouse'])
    direction = shop['drivewayDirection']
    dx, dy = DIRS[direction]
    hx, hy = tile(home['cell'])
    sx, sy = advance(tile(shop['entrance']), direction)
    return (hx-sx)*dx+(hy-sy)*dy, (hy-sy)*dx-(hx-sx)*dy


class OffsetEnvironment(ClearRoadEnvironment):
    def __init__(self, dll, worker, workers, exercise, sign):
        super().__init__(dll, worker, workers, exercise)
        self.sign = sign
        self.candidate = 0
        self.admitted = 0
        self.max_span = 2

    def set_max_span(self, span):
        if not 2 <= span <= 7:
            raise ValueError('Unsupported distance')
        self.max_span = span

    def _seed(self):
        value = 250000 + self.worker + self.workers*self.candidate
        self.candidate += 1
        return value

    def _sample_layout(self):
        if self.exercise != 'clear':
            return self.exercise, self._seed()
        newest = self.admitted % 4 != 0
        shortest = self.sign and (self.max_span==2 or not newest and self.max_span==3)
        stage = 'clear-offset-short' if shortest else 'clear'
        for _ in range(512):
            seed = self._seed()
            raw = self.env.host.call(command='reset', version='OriginalReference', practice=True,
                practiceStage='curriculum-'+stage, practiceSplit='train', seed=seed)['observation']
            distance, offset = layout_geometry(raw)
            if not self.sign:
                if abs(offset)<=1:
                    return stage, seed
            elif offset == 2*self.sign:
                admissible = distance == (2 if shortest else self.max_span) if newest or shortest else distance < self.max_span
                if admissible:
                    return stage,seed
        raise RuntimeError('Unable to find a layout in the requested training family')

    def reset(self, *, seed=None, options=None):
        if options is not None:
            return super().reset(seed=seed, options=options)
        stage, layout_seed = self._sample_layout()
        result = super().reset(seed=seed, options=dict(stage=stage, split='train', layout_seed=layout_seed))
        self.distance, self.offset = layout_geometry(self.env.raw)
        self.admitted += 1
        if self.sign and (self.offset != 2*self.sign or self.distance > self.max_span):
            raise RuntimeError('Unexpected native layout after selecting an offset seed')
        return result

    def step(self, action):
        observation, reward, terminated, truncated, info = super().step(action)
        return observation,reward,terminated,truncated,dict(info, stage=self.exercise,
            distance=self.distance, offset=self.offset, targeted=bool(self.sign))


class OffsetMonitor(Monitor):
    def __init__(self, output, seconds, previous_steps):
        super().__init__(output,seconds)
        self.completed_update_decisions = previous_steps
        self.max_span = 2
        self.windows = deque(maxlen=3)

    def _on_rollout_start(self):
        if self.pending is not None:
            self.windows.append(self.pending['targeted'])
        super()._on_rollout_start()
        if len(self.windows)==3 and self.max_span<7:
            sign_totals = [tuple(sum(batch[str(sign)][i] for batch in self.windows) for i in range(2))
                           for sign in (-2,2)]
            if all(games>=30 and hits/games>=.85 for hits,games in sign_totals):
                self.max_span += 1
                self.windows.clear()
                self.training_env.env_method('set_max_span',self.max_span)
                print(f'CURRICULUM | advanced to {self.max_span}-tile routes',flush=True)
        self.model.policy.temperature = TEMPERATURES[self.max_span]
        self.targeted = {str(sign):[0,0] for sign in (-2,2)}
        self.rehearsal = {stage:[0,0] for stage in ('clear','bend','adjacent')}

    def _on_step(self):
        for done,info in zip(self.locals['dones'],self.locals['infos']):
            if not done:
                continue
            if info['targeted']:
                if info['distance']==self.max_span:
                    counts = self.targeted[str(info['offset'])]
                else:
                    continue
            else:
                counts = self.rehearsal[info['stage']]
            counts[0] += int(info['connected'])
            counts[1] += 1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending.update(max_span=self.max_span,temperature=self.model.policy.temperature,
                            targeted=self.targeted,rehearsal=self.rehearsal)
        left,right = self.targeted['-2'],self.targeted['2']
        print(f'OFFSET | {self.max_span} tiles | left {left[0]}/{left[1]} | right {right[0]}/{right[1]} | '
              f'{self.num_timesteps} cumulative build decisions',flush=True)


def check_fixture(dll, original):
    for standard_stage, seed in [('clear',36022),('bend',32000),('adjacent',30000)]:
        envs = [ClearRoadEnvironment(x) for x in (dll,original)]
        try:
            reset = [e.reset(options=dict(stage=standard_stage, split='validation', layout_seed=seed))[0]
                     for e in envs]
            import numpy as np
            for k in reset[0]:
                np.testing.assert_array_equal(reset[0][k],reset[1][k])
            np.testing.assert_array_equal(envs[0].action_masks(),envs[1].action_masks())
        finally:
            for env in envs:env.close()
    env = ClearRoadEnvironment(dll)
    try:
        for seed in range(63000,63008):
            env.reset(options=dict(stage='clear-offset-short',split='validation',layout_seed=seed))
            assert geometry(env.env)['distance']==2 and abs(geometry(env.env)['offset'])==2
            assert env.env.inventory==1
            action, = env.env.reference()
            _,reward,done,truncated,_=env.step(action)
            assert done and not truncated and reward==1
            assert env.env.deliveries()[0]>=3
    finally:
        env.close()


def train(args,output):
    parent = checked_checkpoint(args.checkpoint,args.original_dll)
    before = policy_fingerprint(parent.policy)
    assignments = [('clear',-1)]*6+[('clear',1)]*6+[('clear',0)]*2+[('bend',0),('adjacent',0)]
    env = SubprocVecEnv([partial(OffsetEnvironment,args.dll,i,len(assignments),stage,sign)
                         for i,(stage,sign) in enumerate(assignments)],start_method='forkserver')
    try:
        model = MaskablePPO.load(args.checkpoint, env=env, device=args.device,
                                 custom_objects={'policy_class':ExplorationPolicy})
        if policy_fingerprint(model.policy)!=before or model.num_timesteps!=parent.num_timesteps:
            raise RuntimeError('Resume did not preserve policy weights and counters')
        if not model.policy.optimizer.state_dict()['state']:
            raise RuntimeError('Resume did not restore the PPO optimizer state')
        write(output/'config.json',dict(kind='offset-ppo',parent=str(args.checkpoint),
            parent_fingerprint=before,parent_decisions=model.num_timesteps,native_sha256=digest(args.dll),
            source_sha256=digest(__file__),workers=assignments,temperatures=TEMPERATURES,
            teacher_actions=False,decision_budget=args.decisions,wall_seconds=args.wall_seconds,
            advance_rule='Both offset directions at least 85% over 3 rollouts at the current distance',
            terminal_reward='1 for any legal route that connects, otherwise 0'))
        model.save(output/'initial.zip')
        monitor = OffsetMonitor(output,args.wall_seconds,model.num_timesteps)
        started_at = model.num_timesteps
        print(f'RESUMED | {started_at} saved build decisions | short two-tile offsets',flush=True)
        try:
            model.learn(total_timesteps=args.decisions,reset_num_timesteps=False,
                        callback=monitor,progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET'
        write(output/'status.json',dict(result=result,saved_decisions=monitor.completed_update_decisions,
            collected_decisions=model.num_timesteps,additional_saved=monitor.completed_update_decisions-started_at,
            last_span=monitor.max_span,elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('verify','train','evaluate'))
    p.add_argument('--dll',required=True)
    p.add_argument('--original-dll')
    p.add_argument('--checkpoint')
    p.add_argument('--output',required=True)
    p.add_argument('--device',choices=('cpu','cuda'),default='cuda')
    p.add_argument('--decisions',type=int,default=131072)
    p.add_argument('--wall-seconds',type=int,default=1800)
    p.add_argument('--eval-workers',type=int,default=10)
    p.add_argument('--sample',action='store_true')
    args=p.parse_args()
    if args.mode in ('train','verify') and not args.original_dll:
        p.error('Original host required')
    if args.mode != 'verify' and not args.checkpoint:
        p.error('Trusted checkpoint required')
    if min(args.eval_workers,args.decisions,args.wall_seconds)<1 or args.decisions%2048:
        p.error('Invalid positive budget or worker count')
    output=Path(args.output)
    output.mkdir(parents=True)
    torch.set_num_threads(2)
    if args.mode=='verify':
        check_fixture(args.dll,args.original_dll)
        write(output/'verification.json',dict(ordinary_fixture_parity=True,short_offset_deliveries=8))
    elif args.mode=='train':
        train(args,output)
    else:
        config=json.loads(Path(args.checkpoint).with_name('config.json').read_text())
        if config['native_sha256']!=digest(args.dll) or config['source_sha256']!=digest(__file__):
            raise ValueError('Runner or native host differs from training identity')
        model=MaskablePPO.load(args.checkpoint,device='cpu')
        model.policy.temperature=1.
        args.stages=['clear','bend','adjacent']
        args.eval_offset=0
        evaluate(args,model,output)


if __name__ == '__main__':
    main()

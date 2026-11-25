"""Exploration-only surplus stock, with original-budget frozen evaluation."""
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

from bend_ppo import Monitor, digest, write
from clear_road_ppo import (
    ClearRoadEnvironment, GoalAwareFeatures, GoalAwareHead, GoalAwarePolicy, GoalLatents,
    checked_checkpoint, geometry,
)
from edge_policy import EDGE_WIDTH
from hierarchy_rollout import policy_fingerprint
from offset_ppo import layout_geometry

STOCK_STAGES = {2:'clear-spare-two', 1:'clear-spare-one', 0:'clear'}


class ExplorationFeatures(GoalAwareFeatures):
    """Carry rollout temperature separately from visible neural features."""
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self._features_dim += 1

    def forward(self, observation):
        return torch.cat((super().forward(observation), observation['temperature']), dim=1)


class TemperedLatents(GoalLatents):
    def forward_actor(self, features):
        return super().forward_actor(features[:, :-1]), features[:, -1:]

    def forward_critic(self, features):
        local = super().forward_actor(features[:, :-1])[..., :EDGE_WIDTH]
        return torch.cat((local.mean(dim=1), local.amax(dim=1)), dim=-1)


class TemperedHead(GoalAwareHead):
    def forward(self, latent):
        edges, temperature = latent
        return super().forward(edges) / temperature


class SpareRoadPolicy(GoalAwarePolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = TemperedLatents()
        self.action_net = TemperedHead()
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


class SpareRoadEnvironment(ClearRoadEnvironment):
    def __init__(self, dll, worker=0, workers=1, exercise='clear', sign=0, temperature=1.):
        super().__init__(dll, worker, workers, exercise)
        self.sign = sign
        self.exploration_temperature = temperature
        self.pending_surplus = 2
        self.widen = False
        self.candidate = 0
        self.admitted = 0
        self.observation_space.spaces['temperature'] = gym.spaces.Box(1, 12, (1,), np.float32)

    def set_phase(self, surplus, widen):
        self.pending_surplus = surplus
        self.widen = widen

    def _seed(self):
        seed = 450000+self.worker+self.workers*self.candidate
        self.candidate += 1
        return seed

    def _training_layout(self):
        if self.exercise!='clear':
            return self.exercise,self._seed()
        stage = STOCK_STAGES[self.pending_surplus] if self.sign else 'clear'
        for _ in range(512):
            seed=self._seed()
            raw=self.env.host.call(command='reset',version='OriginalReference',practice=True,
                practiceStage='curriculum-'+stage,practiceSplit='train',seed=seed)['observation']
            distance,offset=layout_geometry(raw)
            if self.sign:
                if offset==2*self.sign and (self.widen or distance==3):
                    return stage,seed
            elif abs(offset)==(0 if self.admitted%4==0 else 1):
                return stage,seed
        raise RuntimeError('Unable to find a requested native layout')

    def _with_temperature(self, observation):
        return dict(observation, temperature=np.array([self.episode_temperature],dtype=np.float32))

    def reset(self, *, seed=None, options=None):
        if options is None:
            stage,layout_seed=self._training_layout()
            options=dict(stage=stage,split='train',layout_seed=layout_seed)
            self.surplus=self.pending_surplus if self.sign else 0
            self.episode_temperature=(max(1.,1.+(self.exploration_temperature-1.)*(self.surplus+.5)/2.5)
                                      if self.sign else 1.)
        else:
            self.surplus=0
            self.episode_temperature=1.
        obs,info=super().reset(seed=seed,options=options)
        self.distance,self.offset=layout_geometry(self.env.raw)
        self.admitted+=1
        if self.sign and (self.offset!=self.sign*2 or not self.widen and self.distance!=3):
            raise RuntimeError('Unexpected targeted layout')
        return self._with_temperature(obs),info

    def step(self, action):
        obs,reward,terminated,truncated,info=super().step(action)
        return self._with_temperature(obs),reward,terminated,truncated,dict(
            info,stage=self.exercise,distance=self.distance,offset=self.offset,spare=self.surplus,targeted=bool(self.sign))


class SpareMonitor(Monitor):
    def __init__(self, output, seconds, previous_steps):
        super().__init__(output,seconds)
        self.completed_update_decisions=previous_steps
        self.surplus=2
        self.widen=False
        self.window=deque(maxlen=3)
        self.initial_targeted=[0,0]
        self.insufficient_signal=False

    def _on_rollout_start(self):
        if self.pending is not None:
            targeted = self.pending['targeted']
            self.window.append(targeted)
            if self.pending['surplus'] == 2:
                for k in range(2):
                    self.initial_targeted[k] += sum(v[k] for v in targeted.values())
        super()._on_rollout_start()
        if self.surplus==2 and self.initial_targeted[1]>=6000 and self.initial_targeted[0]<=2:
            self.insufficient_signal=True
            print(f'STOP | {self.initial_targeted[0]}/{self.initial_targeted[1]} targeted games connected',flush=True)
        if len(self.window)==3 and not self.widen:
            totals=[[sum(batch[str(sign)][i] for batch in self.window) for i in range(2)] for sign in (-2,2)]
            if all(games>=30 and wins/games>=.85 for wins,games in totals):
                if self.surplus:
                    self.surplus-=1
                else:
                    self.widen=True
                self.window.clear()
                self.training_env.env_method('set_phase',self.surplus,self.widen)
                print(f'CURRICULUM | spare stock {self.surplus} | expand distances {self.widen}',flush=True)
        self.targeted={str(side):[0,0] for side in (-2,2)}
        self.rehearsal={name:[0,0] for name in ('clear','bend','adjacent')}

    def _on_step(self):
        if self.insufficient_signal:
            return False
        for done,info in zip(self.locals['dones'],self.locals['infos']):
            if done and info['targeted'] and info['spare']==self.surplus:
                count=self.targeted[str(info['offset'])]
            elif done and not info['targeted']:
                count=self.rehearsal[info['stage']]
            else:
                continue
            count[0]+=int(info['connected'])
            count[1]+=1
        return super()._on_step()

    def _on_rollout_end(self):
        super()._on_rollout_end()
        self.pending.update(surplus=self.surplus,widen=self.widen,targeted=self.targeted,rehearsal=self.rehearsal)
        left,right=self.targeted['-2'],self.targeted['2']
        print(f'SPARE +{self.surplus} | left {left[0]}/{left[1]} | right {right[0]}/{right[1]} | '
              f'{self.num_timesteps} cumulative decisions',flush=True)


def verify(args, output):
    hosts = [ClearRoadEnvironment(path) for path in (args.original_dll,args.dll)]
    controls = 0
    fixtures = []
    try:
        for stage,seed in [('clear',36022),('bend',32000),('adjacent',30000)]:
            obs=[host.reset(options=dict(stage=stage,split='validation',layout_seed=seed))[0] for host in hosts]
            assert all(np.array_equal(obs[0][k],obs[1][k]) for k in obs[0])
            assert np.array_equal(hosts[0].action_masks(),hosts[1].action_masks())
            controls+=1
        for seed in (36022,36053):
            for surplus,stage in STOCK_STAGES.items():
                env=hosts[1]
                env.reset(options=dict(stage=stage,split='validation',layout_seed=seed))
                assert geometry(env.env)['distance']==3 and abs(geometry(env.env)['offset'])==2
                assert env.env.inventory==2+surplus and env.env.edit_limit==3+surplus
                for action in env.env.reference():
                    _,reward,done,truncated,_=env.step(action)
                    if done:
                        break
                assert done and not truncated and reward==1
                trips,_=env.env.deliveries()
                assert trips>=3
                fixtures.append(dict(seed=seed,spare=surplus,trips=trips))
    finally:
        for env in hosts:env.close()
    write(output/'verification.json',dict(ordinary_host_parity=controls,scripted_fixtures=fixtures))


def train(args,output):
    parent=checked_checkpoint(args.checkpoint,args.original_dll)
    before=policy_fingerprint(parent.policy)
    assignments=[('clear',-1)]*4+[('clear',1)]*4+[('clear',0)]*6+[('bend',0),('adjacent',0)]
    env=SubprocVecEnv([partial(SpareRoadEnvironment,args.dll,i,len(assignments),stage,sign,args.temperature)
        for i,(stage,sign) in enumerate(assignments)],start_method='forkserver')
    try:
        kwargs=dict(parent.policy_kwargs,features_extractor_class=ExplorationFeatures)
        model=MaskablePPO.load(args.checkpoint,env=env,device=args.device,custom_objects=dict(
            policy_class=SpareRoadPolicy,policy_kwargs=kwargs,observation_space=env.observation_space))
        if policy_fingerprint(model.policy)!=before or model.num_timesteps!=parent.num_timesteps:
            raise RuntimeError('Warm start changed weights or decision counters')
        if not model.policy.optimizer.state_dict()['state']:
            raise RuntimeError('Optimizer state not restored')
        write(output/'config.json',dict(kind='spare-road-ppo',parent=str(args.checkpoint),parent_fingerprint=before,
            parent_decisions=model.num_timesteps,source_sha256=digest(__file__),native_sha256=digest(args.dll),
            workers=assignments,targeted_temperature=args.temperature,targeted_start_span=3,start_spare=2,
            reward='1 for connecting with any legal route, otherwise 0',teacher_actions=False,
            decisions=args.decisions,wall_seconds=args.wall_seconds,advance_rule='both signs 85% over 3 rollouts',
            early_stop='at least 6000 initial targeted episodes with no more than 2 successes'))
        model.save(output/'initial.zip')
        start=model.num_timesteps
        monitor=SpareMonitor(output,args.wall_seconds,start)
        print(f'RESUMED | {start} saved decisions | two spare road units only in targeted training',flush=True)
        try:
            model.learn(total_timesteps=args.decisions,reset_num_timesteps=False,callback=monitor,progress_bar=False)
        except KeyboardInterrupt:
            result='INTERRUPTED'
        else:
            result=('INSUFFICIENT_SIGNAL' if monitor.insufficient_signal else
                    'WALL_BUDGET' if monitor.stopped_by_wall else 'DECISION_BUDGET')
        write(output/'status.json',dict(result=result,saved_decisions=monitor.completed_update_decisions,
            collected_decisions=model.num_timesteps,saved_additional=monitor.completed_update_decisions-start,
            spare=monitor.surplus,widen=monitor.widen,elapsed_seconds=monotonic()-monitor.started))
    finally:
        env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('verify','train'))
    p.add_argument('--dll',required=True)
    p.add_argument('--original-dll',required=True)
    p.add_argument('--checkpoint')
    p.add_argument('--output',required=True)
    p.add_argument('--device',choices=('cpu','cuda'),default='cuda')
    p.add_argument('--decisions',type=int,default=131072)
    p.add_argument('--wall-seconds',type=int,default=1800)
    p.add_argument('--temperature',type=float,default=4.)
    args=p.parse_args()
    if min(args.decisions,args.wall_seconds)<1 or args.decisions%2048 or not 1<=args.temperature<=12:
        p.error('Invalid static budget or exploration temperature')
    if args.mode=='train' and not args.checkpoint:
        p.error('Trusted checkpoint required for training')
    torch.set_num_threads(2)
    output=Path(args.output);output.mkdir(parents=True)
    if args.mode=='verify':
        verify(args,output)
    else:
        train(args,output)


if __name__=='__main__':
    main()

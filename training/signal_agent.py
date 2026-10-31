"""Opt-in traffic-light goal schema; normal stock, legal ordinary junctions."""
from functools import partial
import gymnasium as gym
import numpy as np
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
from parallel import ParallelHostVecEnv
from goal_agent import GoalEnv,GOALS
from environment import DIRS
from upgrade_rules import supported_mask

SIGNALS=32
SIGNAL_START=GOALS+3
SIGNAL_SCHEMA='visible-route-signals-policy-v3'
CONTEXT_SCHEMA='visible-route-signal-context-v4'


class SignalEnv(GoalEnv):
    def __init__(self,enable_signals=True,disable_light_actions=False,signal_context=False,supported_upgrades=False,**kwargs):
        self.supported_upgrades=bool(supported_upgrades)
        self.signal_context=bool(signal_context)
        self.enable_signals=bool(enable_signals)
        self.disable_light_actions=bool(disable_light_actions)
        self.signals_placed_count=0
        self.signal_cells=[];self.signal_features=np.zeros((SIGNALS,24 if self.signal_context else 12),np.float32)
        kwargs['congestion_aware']=True
        super().__init__(**kwargs)
        self.schema=CONTEXT_SCHEMA if self.signal_context else SIGNAL_SCHEMA
        self.action_space=gym.spaces.Discrete(SIGNAL_START+SIGNALS)
        spaces=dict(self.observation_space.spaces)
        spaces['signals']=gym.spaces.Box(0,1,self.signal_features.shape,np.float32)
        spaces['traffic']=gym.spaces.Box(0,1,(5,30,50),np.float32)
        self.observation_space=gym.spaces.Dict(spaces)

    def reset(self,*,seed=None,options=None):
        self.signals_placed_count=0
        return super().reset(seed=seed,options=options)

    def _refresh(self):
        super()._refresh()
        e=self.base;self.signal_cells=[];self.signal_features.fill(0)
        if not self.enable_signals or e.raw['inventory'][3]<=0:return
        counts=np.zeros(1500);wait=np.zeros(1500)
        for v in e.raw['vehicles']:
            p=int(v['x']),int(v['y'])
            if e.is_visible(p):
                k=e.index(p);counts[k]+=1;wait[k]=max(wait[k],v['waiting'])
        candidates=[]
        shops={b['id']:b for b in e.buildings if not b['isHouse']}
        for k in np.flatnonzero(e._legal[4]):
            degree=int(e.arrays['connections'][k]).bit_count()
            if degree<3:continue
            p=int(k%50),int(k//50)
            near=[int(k)]+[e.index((p[0]+dx,p[1]+dy)) for dx,dy in DIRS if e.is_visible((p[0]+dx,p[1]+dy))]
            values=[p[0]/50,p[1]/30,degree/8,counts[k]/10,wait[k]/60,
                    counts[near].sum()/20,wait[near].max()/60,np.mean(wait[near]>=3),
                    e.raw['inventory'][3]/10,e.raw['inventory'][0]/100,(e.raw['time']%140)/140,1]
            if self.signal_context:
                nearby=[v for v in e.raw['vehicles'] if e.is_visible((int(v['x']),int(v['y']))) and e.index((int(v['x']),int(v['y']))) in near]
                stopped=[v for v in nearby if v['waiting']>=3]
                parking=[v for v in stopped if v['obstacle']=='Carpark access occupied']
                crossing=[v for v in stopped if v['obstacle'] in ['Crossing vehicle','Approaching vehicle priority']]
                related={v['shopId'] for v in nearby if v['stage'] in ['Outbound','EnteringParking'] and v['shopId'] in shops}
                pressure=[shops[i] for i in related]
                entrance_road=any((b['entrances'][j]['x']+DIRS[d][0],b['entrances'][j]['y']+DIRS[d][1])==p
                    for b in shops.values() for j,d in enumerate(b['entranceDirections']))
                denom=max(1,len(stopped))
                values += [len(parking)/denom,len(crossing)/denom,
                    sum(v['obstacle']=='Traffic light' for v in stopped)/denom,
                    sum(v['obstacle']=='Queue ahead' for v in stopped)/denom,
                    max((v['waiting'] for v in parking),default=0)/60,
                    max((v['waiting'] for v in crossing),default=0)/60,
                    max((b['overcrowdedFor'] for b in pressure),default=0)/50,
                    max((max(0,b['demand']-b['reserved'])/max(1,b['demandCapacity']) for b in pressure),default=0),
                    max((b['overcrowdedFor'] for b in shops.values()),default=0)/50,
                    sum(b['overcrowdedFor']>0 for b in pressure)/max(1,len(pressure)),
                    float(entrance_road),sum(e.arrays['infrastructure'][i]==4 for i in near)/len(near)]
            candidates.append(((-wait[near].max(),-counts[near].sum(),int(k)),p,values))
        for i,(_,p,values) in enumerate(sorted(candidates)[:SIGNALS]):
            self.signal_cells.append(p);self.signal_features[i]=np.clip(values,0,1)

    def encode(self):
        obs=super().encode();obs['signals']=self.signal_features.copy()
        light=np.zeros(1500,np.float32)
        light[self.base.visible]=np.asarray(self.base.arrays['infrastructure'])[self.base.visible]==4
        obs['traffic']=np.concatenate([obs['traffic'],light.reshape(1,30,50)],axis=0)
        return obs

    def action_masks(self):
        mask=np.zeros(self.action_space.n,bool)
        mask[:SIGNAL_START]=super().action_masks()
        if not self.disable_light_actions:mask[SIGNAL_START:SIGNAL_START+len(self.signal_cells)]=True
        if self.supported_upgrades:mask=supported_mask(mask,self.base.raw['upgradeChoices'])
        return mask

    def _execute_extra(self,action):
        p=self.signal_cells[action-SIGNAL_START]
        result=self.base._advance(dict(command='build',tool='TrafficLight',x=p[0],y=p[1]))
        if result[-1]['accepted']:self.signals_placed_count+=1

    def info(self):
        return dict(super().info(),traffic_lights_enabled=self.enable_signals,
                    signal_candidates=len(self.signal_cells),signals_placed=self.signals_placed_count,
                    observation_schema=self.schema,signal_context=self.signal_context,
                    supported_upgrades=self.supported_upgrades)


def transfer_signal_context(target,source):
    """V3->v4 warm start: preserve weights, zero added inputs, fresh optimizer."""
    import torch
    if source.observation_space['signals'].shape[1]!=12 or target.observation_space['signals'].shape[1]!=24:
        raise ValueError('Expected v3 source and v4 target')
    if target.policy.optimizer.state:raise ValueError('Warm start requires a fresh optimizer')
    old=dict(source.policy.named_parameters())
    with torch.no_grad():
        for name,value in target.policy.named_parameters():
            original=old[name]
            if value.shape==original.shape:value.copy_(original)
            elif name in ['features_extractor.signal_row.0.weight','features_extractor.signal_prior.weight']:
                value.zero_();value[:,:original.shape[1]].copy_(original)
            else:raise ValueError(f'Unsupported parameter shape: {name}')


def worker(index,output,kwargs):
    from pathlib import Path
    return Monitor(SignalEnv(**kwargs),str(Path(output)/f'worker-{index:02d}.monitor.csv'),info_keywords=('trips','seconds','rejected_actions'))


def signal_vector(workers,output,**kwargs):
    factories=[partial(worker,i,output,kwargs) for i in range(workers)]
    return ParallelHostVecEnv(factories) if workers>1 else DummyVecEnv(factories)

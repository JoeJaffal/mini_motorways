"""Opt-in traffic-light goal schema; normal stock, legal ordinary junctions."""
from functools import partial
import gymnasium as gym
import numpy as np
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
from parallel import ParallelHostVecEnv
from goal_agent import GoalEnv,GOALS
from environment import DIRS

SIGNALS=32
SIGNAL_START=GOALS+3
SIGNAL_SCHEMA='visible-route-signals-policy-v3'


class SignalEnv(GoalEnv):
    def __init__(self,enable_signals=True,disable_light_actions=False,**kwargs):
        self.enable_signals=bool(enable_signals)
        self.disable_light_actions=bool(disable_light_actions)
        self.signals_placed_count=0
        self.signal_cells=[];self.signal_features=np.zeros((SIGNALS,12),np.float32)
        kwargs['congestion_aware']=True
        super().__init__(**kwargs)
        self.schema=SIGNAL_SCHEMA
        self.action_space=gym.spaces.Discrete(SIGNAL_START+SIGNALS)
        spaces=dict(self.observation_space.spaces)
        spaces['signals']=gym.spaces.Box(0,1,(SIGNALS,12),np.float32)
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
        for k in np.flatnonzero(e._legal[4]):
            degree=int(e.arrays['connections'][k]).bit_count()
            if degree<3:continue
            p=int(k%50),int(k//50)
            near=[int(k)]+[e.index((p[0]+dx,p[1]+dy)) for dx,dy in DIRS if e.is_visible((p[0]+dx,p[1]+dy))]
            values=[p[0]/50,p[1]/30,degree/8,counts[k]/10,wait[k]/60,
                    counts[near].sum()/20,wait[near].max()/60,np.mean(wait[near]>=3),
                    e.raw['inventory'][3]/10,e.raw['inventory'][0]/100,(e.raw['time']%140)/140,1]
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
        return mask

    def _execute_extra(self,action):
        p=self.signal_cells[action-SIGNAL_START]
        result=self.base._advance(dict(command='build',tool='TrafficLight',x=p[0],y=p[1]))
        if result[-1]['accepted']:self.signals_placed_count+=1

    def info(self):
        return dict(super().info(),traffic_lights_enabled=self.enable_signals,
                    signal_candidates=len(self.signal_cells),signals_placed=self.signals_placed_count,
                    observation_schema=SIGNAL_SCHEMA)


def worker(index,output,kwargs):
    from pathlib import Path
    return Monitor(SignalEnv(**kwargs),str(Path(output)/f'worker-{index:02d}.monitor.csv'),info_keywords=('trips','seconds','rejected_actions'))


def signal_vector(workers,output,**kwargs):
    factories=[partial(worker,i,output,kwargs) for i in range(workers)]
    return ParallelHostVecEnv(factories) if workers>1 else DummyVecEnv(factories)

"""Experimental hierarchical PPO: choose connections; visible router draws them.

Different action abstraction from the primitive all-tools agent. No stock grants,
future state, debug construction or teacher trajectories. Candidate paths are
computed by a visible-state router, so scores must be labeled hybrid/planner-aided.
"""
from functools import partial
import numpy as np
import gymnasium as gym
import torch
from torch import nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from environment import TrafficEnv,DIRS,cell
from planner_diagnostic import path_to,reachable,strokes
from parallel import ParallelHostVecEnv
from rewards import ConnectionPotential

GOALS=512
GOAL_SCHEMA='visible-route-goal-policy-v1'


class GoalEnv(gym.Env):
    metadata={'render_modes':[]}
    schema=GOAL_SCHEMA
    def __init__(self,**kwargs):
        super().__init__()
        self.base=TrafficEnv(observation_mode='connectivity',reward_mode='trips',record_replays=True,**kwargs)
        self.action_space=gym.spaces.Discrete(GOALS+3)
        self.observation_space=gym.spaces.Dict({'candidates':gym.spaces.Box(-1,1,(GOALS,25),np.float32),
                                               'global':gym.spaces.Box(0,1,(42,),np.float32)})
        self.potential=ConnectionPotential(gamma=.99)

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed);self.base.reset(seed=seed,options=options)
        self.potential.reset(self.base.connected_houses);self.shaping_total=0.;self.reward_total=0.;self.decisions=0
        self.cache_key=None;self._refresh()
        return self.encode(),self.info()

    def _refresh(self):
        e=self.base
        key=(e.network_version,tuple(e.raw['inventory']),tuple(e.raw[k] for k in ['playableXMin','playableXMax','playableYMin','playableYMax']))
        if self.cache_key==key:
            by_id={b['id']:b for b in e.buildings}
            for i,shop_id in enumerate(self.plan_shops):
                self.features[i,16]=min(1,by_id[shop_id]['demand']/20)
                self.features[i,22]=min(1,by_id[shop_id]['overcrowdedFor']/50)
            return
        self.cache_key=key;self.plans=[];self.plan_shops=[];self.features=np.zeros((GOALS,25),np.float32)
        supplied=set(e.connectivity['suppliedDestinationIds']);connected=set(e.connectivity['connectedHouseIds'])
        traffic=np.zeros(1500);wait=np.zeros(1500)
        for v in e.raw['vehicles']:
            p=int(v['x']),int(v['y'])
            if e.is_visible(p):traffic[e.index(p)]+=1;wait[e.index(p)]=max(wait[e.index(p)],v['waiting'])
        for h,home in e.houses.items():
            d=DIRS[home['drivewayDirection']];start=h[0]+d[0],h[1]+d[1]
            for shop in e.buildings:
                if shop['isHouse'] or shop['color']!=home['color']:continue
                best=None;rank=None
                for entry,direction in zip(shop['entrances'],shop['entranceDirections']):
                    p=cell(entry);d=DIRS[direction];goal=p[0]+d[0],p[1]+d[1]
                    if reachable(e,start,goal):best=None;rank=None;break
                    route=path_to(e,start,goal)
                    if not route:continue
                    missing=sum(e.arrays['infrastructure'][e.index(p)]==0 for p in route)
                    if missing>e.raw['inventory'][0]:continue
                    score=missing+len(route)*.04
                    if rank is None or score<rank:best=route;rank=score
                if best is None:continue
                if len(self.plans)>=GOALS:raise RuntimeError('Goal schema overflow: candidates must not be silently truncated')
                indices=[e.index(p) for p in best];new=sum(e.arrays['infrastructure'][k]==0 for k in indices)
                color=[int(i==home['color']) for i in range(8)];s=cell(shop['cell'])
                values=[h[0]/50,h[1]/30,s[0]/50,s[1]/30,(s[0]-h[0])/50,(s[1]-h[1])/30]+color+[
                    new/100,len(best)/100,shop['demand']/20,int(home['id'] not in connected),int(shop['id'] not in supplied),
                    1-new/len(best),float(traffic[indices].mean())/10,float(wait[indices].max())/60,shop['overcrowdedFor']/50,
                    sum(e.arrays['terrain'][k]==1 and e.arrays['infrastructure'][k]==0 for k in indices)/10,1]
                self.features[len(self.plans)]=np.clip(values,-1,1);self.plans.append(best);self.plan_shops.append(shop['id'])

    def encode(self):
        e=self.base;global_state=e.encode()['global'].copy();houses=sum(b['isHouse'] for b in e.buildings)
        shops=[b for b in e.buildings if not b['isHouse']];cars=e.raw['vehicles']
        global_state[25:]=0
        global_state[25:37]=[(e.raw['time']%140)/140,e.connected_houses/max(1,houses),
            1-len(e.connectivity['suppliedDestinationIds'])/max(1,len(shops)),len(self.plans)/GOALS,
            houses/100,len(shops)/20,sum(v.get('stage')!='Home' for v in cars)/200,
            sum(b['demand'] for b in shops)/100,max((b['overcrowdedFor'] for b in shops),default=0)/50,
            sum(v['waiting'] for v in cars)/max(1,len(cars))/60,max((v['waiting'] for v in cars),default=0)/60,
            np.count_nonzero(e.arrays['infrastructure'])/1500]
        return {'candidates':self.features.copy(),'global':np.clip(global_state,0,1)}

    def action_masks(self):
        mask=np.zeros(GOALS+3,bool);mask[0]=True
        for i in range(min(2,len(self.base.raw['upgradeChoices']))):mask[1+i]=True
        mask[3:3+len(self.plans)]=True
        return mask

    def step(self,action):
        e=self.base
        if e.done:raise RuntimeError('Reset required')
        action=int(action);before=e.raw['tripsCompleted'];commands=e.commands
        if not 0<=action<GOALS+3 or not self.action_masks()[action]:
            e.rejected+=1;e._advance()
        elif action==0:
            # Up to five ordinary one-second waits, checking game end and growth.
            version=e.network_version
            for _ in range(5):
                e._advance()
                if e.done or e.network_version!=version or e.raw['upgradeChoices']:break
        elif action<3:e._advance(dict(command='upgrade',choice=action-1))
        else:
            for a,b in strokes(self.plans[action-3]):
                e._advance(dict(command='draw',x=a[0],y=a[1],toX=b[0],toY=b[1]))
                if e.done:break
        terminated=bool(e.raw['failed']);truncated=e.done and not terminated
        shaping=self.potential.step(e.connected_houses,terminated)
        trips=e.raw['tripsCompleted']-before;self.shaping_total+=shaping;self.reward_total+=trips+shaping;self.decisions+=1
        self._refresh();info=self.info()
        info.update(command_completed=True,commands_delta=e.commands-commands,trip_reward=trips,shaping_reward=shaping)
        if e.done:info['episode_replay']=self.export_replay()
        return self.encode(),float(trips+shaping),terminated,truncated,info

    def info(self):
        return dict(self.base.info(),reward_mode='goal-connectivity',reward_schema='goal-trip-potential-gamma099-v1',
                    observation_mode='goal-candidates',planner_aided=True,
                    shaping_reward_total=self.shaping_total,training_reward_total=self.reward_total,
                    trip_reward_total=self.base.raw['tripsCompleted'],connection_potential=self.potential.previous,
                    macro_decisions=self.decisions,available_goals=len(getattr(self,'plans',[])))

    def export_replay(self):
        replay=self.base.export_replay()
        if replay:replay.update(source='hybrid-training',policySchema=GOAL_SCHEMA,plannerAided=True)
        return replay

    def close(self):self.base.close()


def worker(index,output,kwargs):
    from pathlib import Path
    return Monitor(GoalEnv(**kwargs),str(Path(output)/f'worker-{index:02d}.monitor.csv'),info_keywords=('trips','seconds','rejected_actions'))


def vector(workers,output,**kwargs):
    factories=[partial(worker,i,output,kwargs) for i in range(workers)]
    return ParallelHostVecEnv(factories) if workers>1 else DummyVecEnv(factories)


class GoalFeatures(BaseFeaturesExtractor):
    def __init__(self,space):
        super().__init__(space,features_dim=GOALS+3+64)
        self.row=nn.Sequential(nn.Linear(25,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU())
        self.residual=nn.Linear(32,1);nn.init.zeros_(self.residual.weight);nn.init.zeros_(self.residual.bias)
        self.prior=nn.Linear(25,1,bias=False)
        with torch.no_grad():
            self.prior.weight.zero_();self.prior.weight[0,14]=-30;self.prior.weight[0,15]=-1
            self.prior.weight[0,16]=2;self.prior.weight[0,17]=2;self.prior.weight[0,18]=12
        self.tools=nn.Sequential(nn.Linear(42,32),nn.Tanh(),nn.Linear(32,3))
        nn.init.zeros_(self.tools[-1].weight)
        with torch.no_grad():self.tools[-1].bias.zero_()
        self.context=nn.Sequential(nn.Linear(106,64),nn.Tanh())

    def forward(self,obs):
        candidates=obs['candidates'];valid=candidates[:,:,24:25];rows=self.row(candidates)
        mean=(rows*valid).sum(1)/valid.sum(1).clamp(min=1)
        maximum=(rows*valid).max(1).values
        values=self.context(torch.cat([mean,maximum,obs['global']],dim=1))
        tools=self.tools(obs['global'])
        offers=torch.stack([torch.zeros_like(tools[:,0]),obs['global'][:,9:15].sum(1)*20,obs['global'][:,17:23].sum(1)*20],dim=1)
        logits=torch.cat([tools+offers,(self.residual(rows)+self.prior(candidates)).squeeze(-1)],dim=1)
        return torch.cat([logits,values],dim=1)


class GoalHeads(nn.Module):
    latent_dim_pi=GOALS+3;latent_dim_vf=64
    def forward(self,x):return self.forward_actor(x),self.forward_critic(x)
    def forward_actor(self,x):return x[:,:GOALS+3]
    def forward_critic(self,x):return x[:,GOALS+3:]


class GoalPolicy(MaskableActorCriticPolicy):
    def __init__(self,*args,**kwargs):
        kwargs['features_extractor_class']=GoalFeatures;kwargs['normalize_images']=False
        super().__init__(*args,**kwargs)
    def _build(self,lr_schedule):
        self.mlp_extractor=GoalHeads();self.action_net=nn.Identity();self.value_net=nn.Linear(64,1)
        nn.init.zeros_(self.value_net.weight);nn.init.zeros_(self.value_net.bias)
        self.optimizer=self.optimizer_class(self.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)

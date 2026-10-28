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
CONGESTION_SCHEMA='visible-route-congestion-policy-v2'


class GoalEnv(gym.Env):
    metadata={'render_modes':[]}
    schema=GOAL_SCHEMA
    def __init__(self,reward_scale=1.,skip_forced_wait=False,congestion_aware=False,allow_alternatives=True,**kwargs):
        super().__init__()
        if not np.isfinite(reward_scale) or reward_scale<=0:raise ValueError('Positive finite reward scale required')
        self.reward_scale=float(reward_scale)
        self.skip_forced_wait=bool(skip_forced_wait)
        self.congestion_aware=bool(congestion_aware)
        self.allow_alternatives=bool(allow_alternatives)
        self.schema=CONGESTION_SCHEMA if self.congestion_aware else GOAL_SCHEMA
        self.base=TrafficEnv(observation_mode='connectivity',reward_mode='trips',record_replays=True,**kwargs)
        self.action_space=gym.spaces.Discrete(GOALS+3)
        spaces={'candidates':gym.spaces.Box(-1,1,(GOALS,32 if self.congestion_aware else 25),np.float32),
                'global':gym.spaces.Box(0,1,(42,),np.float32)}
        if self.congestion_aware:spaces['traffic']=gym.spaces.Box(0,1,(4,30,50),np.float32)
        self.observation_space=gym.spaces.Dict(spaces)
        self.potential=ConnectionPotential(gamma=.99)

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed);self.base.reset(seed=seed,options=options)
        self.potential.reset(self.base.connected_houses);self.shaping_total=0.;self.reward_total=0.;self.decisions=0;self.forced_wait_commands=0
        self.cache_key=None;self._refresh()
        return self.encode(),self.info()

    def _refresh(self):
        e=self.base
        key=(e.network_version,tuple(e.raw['inventory']),tuple(e.raw[k] for k in ['playableXMin','playableXMax','playableYMin','playableYMax']))
        # Only the optional bypass search is time dependent. Live observations
        # below still refresh every decision; route searches run at most per 15s.
        if self.congestion_aware:key+=(int(e.raw['time']//15),)
        if self.cache_key==key:
            self._refresh_dynamic_features()
            return
        self.cache_key=key;self.plans=[];self.plan_shops=[];self.features=np.zeros(self.observation_space['candidates'].shape,np.float32)
        self.bypass_baselines={}
        supplied=set(e.connectivity['suppliedDestinationIds']);connected=set(e.connectivity['connectedHouseIds'])
        traffic=np.zeros(1500);wait=np.zeros(1500)
        for v in e.raw['vehicles']:
            p=int(v['x']),int(v['y'])
            if e.is_visible(p):traffic[e.index(p)]+=1;wait[e.index(p)]=max(wait[e.index(p)],v['waiting'])
        alternatives=[]
        for h,home in e.houses.items():
            d=DIRS[home['drivewayDirection']];start=h[0]+d[0],h[1]+d[1]
            for shop in e.buildings:
                if shop['isHouse'] or shop['color']!=home['color']:continue
                best=None;rank=None;connected_route=False
                for entry,direction in zip(shop['entrances'],shop['entranceDirections']):
                    p=cell(entry);d=DIRS[direction];goal=p[0]+d[0],p[1]+d[1]
                    if reachable(e,start,goal):
                        best=None;rank=None;connected_route=True;break
                    route=path_to(e,start,goal)
                    if not route:continue
                    missing=sum(e.arrays['infrastructure'][e.index(p)]==0 for p in route)
                    if missing>e.raw['inventory'][0]:continue
                    score=missing+len(route)*.04
                    if rank is None or score<rank:best=route;rank=score
                if connected_route and self.congestion_aware and self.allow_alternatives and len(alternatives)<64:
                    # Find an actual existing route first (new cells prohibitively
                    # expensive), then seek a lower-load physical bypass.
                    penalty=np.where(np.asarray(e.arrays['infrastructure'])==0,1e6,0.)
                    baseline=path_to(e,start,goal,penalty)
                    if baseline and all(e.arrays['connections'][e.index(a)]&(1<<DIRS.index((b[0]-a[0],b[1]-a[1]))) for a,b in zip(baseline,baseline[1:])):
                        ids=[e.index(p) for p in baseline]
                        if wait[ids].max()>=3:
                            load=np.minimum(traffic,10)*.3+np.minimum(wait,60)/15
                            bypass=path_to(e,start,goal,load)
                            if bypass:
                                missing=sum(e.arrays['infrastructure'][e.index(p)]==0 for p in bypass)
                                new_load=sum(load[e.index(p)] for p in bypass)
                                if 0<missing<=e.raw['inventory'][0] and new_load<sum(load[ids])*.8:
                                    alternatives.append((h,home,shop,bypass,baseline))
                    continue
                if best is None:continue
                if len(self.plans)>=GOALS:raise RuntimeError('Goal schema overflow: candidates must not be silently truncated')
                indices=[e.index(p) for p in best];new=sum(e.arrays['infrastructure'][k]==0 for k in indices)
                color=[int(i==home['color']) for i in range(8)];s=cell(shop['cell'])
                values=[h[0]/50,h[1]/30,s[0]/50,s[1]/30,(s[0]-h[0])/50,(s[1]-h[1])/30]+color+[
                    new/100,len(best)/100,shop['demand']/20,int(home['id'] not in connected),int(shop['id'] not in supplied),
                    1-new/len(best),float(traffic[indices].mean())/10,float(wait[indices].max())/60,shop['overcrowdedFor']/50,
                    sum(e.arrays['terrain'][k]==1 and e.arrays['infrastructure'][k]==0 for k in indices)/10,1]
                self.features[len(self.plans),:25]=np.clip(values,-1,1);self.plans.append(best);self.plan_shops.append(shop['id'])
        for h,home,shop,route,baseline in alternatives[:max(0,GOALS-len(self.plans))]:
            i=len(self.plans);s=cell(shop['cell']);ids=[e.index(p) for p in route]
            new=sum(e.arrays['infrastructure'][k]==0 for k in ids)
            self.features[i,:25]=np.clip([h[0]/50,h[1]/30,s[0]/50,s[1]/30,(s[0]-h[0])/50,(s[1]-h[1])/30]+
                [int(c==home['color']) for c in range(8)]+[new/100,len(route)/100,shop['demand']/20,0,0,
                1-new/len(route),traffic[ids].mean()/10,wait[ids].max()/60,shop['overcrowdedFor']/50,
                sum(e.arrays['terrain'][k]==1 and e.arrays['infrastructure'][k]==0 for k in ids)/10,1],-1,1)
            self.plans.append(route);self.plan_shops.append(shop['id']);self.bypass_baselines[i]=baseline
        if self.congestion_aware:self._refresh_dynamic_features()

    def _refresh_dynamic_features(self):
        """Refresh live vehicle/demand summaries without recomputing cached paths."""
        e=self.base
        traffic=np.zeros(1500);wait=np.zeros(1500)
        for v in e.raw['vehicles']:
            p=int(v['x']),int(v['y'])
            if e.is_visible(p):
                k=e.index(p);traffic[k]+=1;wait[k]=max(wait[k],v['waiting'])
        by_id={b['id']:b for b in e.buildings}
        for i,(route,shop_id) in enumerate(zip(self.plans,self.plan_shops)):
            indices=[e.index(p) for p in route];shop=by_id[shop_id]
            self.features[i,[16,20,21,22]]=np.clip([
                shop['demand']/20,traffic[indices].mean()/10,
                wait[indices].max()/60,shop['overcrowdedFor']/50],-1,1)
            if self.congestion_aware:
                base=[e.index(p) for p in self.bypass_baselines.get(i,route)]
                junctions=[k for k in indices if int(e.arrays['connections'][k]).bit_count()>=3]
                self.features[i,25:]=np.clip([float(i in self.bypass_baselines),traffic[base].mean()/10,
                    wait[base].max()/60,np.mean(wait[indices]>=3),max(traffic[indices])/10,
                    max((wait[k] for k in junctions),default=0)/60,len(junctions)/max(1,len(indices))],0,1)

    def encode(self):
        e=self.base;global_state=np.clip(e.encode_global(),0,1);houses=sum(b['isHouse'] for b in e.buildings)
        shops=[b for b in e.buildings if not b['isHouse']];cars=e.raw['vehicles']
        global_state[25:]=0
        global_state[25:37]=[(e.raw['time']%140)/140,e.connected_houses/max(1,houses),
            1-len(e.connectivity['suppliedDestinationIds'])/max(1,len(shops)),len(self.plans)/GOALS,
            houses/100,len(shops)/20,sum(v.get('stage')!='Home' for v in cars)/200,
            sum(b['demand'] for b in shops)/100,max((b['overcrowdedFor'] for b in shops),default=0)/50,
            sum(v['waiting'] for v in cars)/max(1,len(cars))/60,max((v['waiting'] for v in cars),default=0)/60,
            np.count_nonzero(e.arrays['infrastructure'])/1500]
        result={'candidates':self.features.copy(),'global':np.clip(global_state,0,1)}
        if self.congestion_aware:
            grid=np.zeros((4,1500),np.float32)
            for y in range(30):
                for x in range(50):
                    if e.is_visible((x,y)):
                        k=e.index((x,y));grid[2,k]=e.arrays['infrastructure'][k]!=0
                        grid[3,k]=int(e.arrays['connections'][k]).bit_count()/8
            for v in cars:
                p=int(v['x']),int(v['y'])
                if e.is_visible(p):
                    k=e.index(p);grid[0,k]+=.1;grid[1,k]=max(grid[1,k],v['waiting']/60)
            result['traffic']=np.clip(grid.reshape(4,30,50),0,1)
        return result

    def action_masks(self):
        mask=np.zeros(GOALS+3,bool);mask[0]=True
        for i in range(min(2,len(self.base.raw['upgradeChoices']))):mask[1+i]=True
        mask[3:3+len(self.plans)]=True
        return mask

    def step(self,action):
        e=self.base
        if e.done:raise RuntimeError('Reset required')
        action=int(action);before=e.raw['tripsCompleted'];commands=e.commands
        if not 0<=action<self.action_space.n or not self.action_masks()[action]:
            e.rejected+=1;e._advance()
        elif action==0:
            # Up to five ordinary one-second waits, checking game end and growth.
            version=e.network_version
            for _ in range(5):
                e._advance()
                if e.done or e.network_version!=version or e.raw['upgradeChoices']:break
        elif action<3:e._advance(dict(command='upgrade',choice=action-1))
        elif action<GOALS+3:
            for a,b in strokes(self.plans[action-3]):
                e._advance(dict(command='draw',x=a[0],y=a[1],toX=b[0],toY=b[1]))
                if e.done:break
        else:self._execute_extra(action)
        self._refresh()
        # Only collapse states with no alternative action. Inspect after every
        # normal one-second command so no newly available choice is skipped.
        while self.skip_forced_wait and not e.done and not self.action_masks()[1:].any():
            e._advance();self.forced_wait_commands+=1;self._refresh()
        terminated=bool(e.raw['failed']);truncated=e.done and not terminated
        shaping=self.potential.step(e.connected_houses,terminated)
        trips=e.raw['tripsCompleted']-before;self.shaping_total+=shaping;self.reward_total+=trips+shaping;self.decisions+=1
        info=self.info()
        info.update(command_completed=True,commands_delta=e.commands-commands,trip_reward=trips,shaping_reward=shaping)
        if e.done:info['episode_replay']=self.export_replay()
        return self.encode(),float((trips+shaping)*self.reward_scale),terminated,truncated,info

    def _execute_extra(self,action):
        raise RuntimeError('No extra actions in this goal schema')

    def info(self):
        return dict(self.base.info(),reward_mode='goal-connectivity',reward_schema='goal-trip-potential-gamma099-choice-v1' if self.skip_forced_wait else 'goal-trip-potential-gamma099-v1',
                    observation_mode='goal-candidates',planner_aided=True,
                    shaping_reward_total=self.shaping_total,training_reward_total=self.reward_total*self.reward_scale,
                    unscaled_training_reward_total=self.reward_total,reward_scale=self.reward_scale,
                    skip_forced_wait=self.skip_forced_wait,forced_wait_commands=self.forced_wait_commands,
                    congestion_aware=self.congestion_aware,bypass_candidates=len(self.bypass_baselines),
                    trip_reward_total=self.base.raw['tripsCompleted'],connection_potential=self.potential.previous,
                    macro_decisions=self.decisions,available_goals=len(getattr(self,'plans',[])))

    def export_replay(self):
        replay=self.base.export_replay()
        if replay:replay.update(source='hybrid-training',policySchema=self.schema,plannerAided=True,skipForcedWait=self.skip_forced_wait)
        return replay

    def close(self):self.base.close()


def worker(index,output,kwargs):
    from pathlib import Path
    return Monitor(GoalEnv(**kwargs),str(Path(output)/f'worker-{index:02d}.monitor.csv'),info_keywords=('trips','seconds','rejected_actions'))


def vector(workers,output,**kwargs):
    factories=[partial(worker,i,output,kwargs) for i in range(workers)]
    return ParallelHostVecEnv(factories) if workers>1 else DummyVecEnv(factories)


class GoalFeatures(BaseFeaturesExtractor):
    def __init__(self,space,prior_temperature=1.):
        if not np.isfinite(prior_temperature) or prior_temperature<=0:raise ValueError('Positive prior temperature required')
        self.signal_count=space['signals'].shape[0] if 'signals' in space.spaces else 0
        super().__init__(space,features_dim=GOALS+3+self.signal_count+64)
        self.prior_temperature=float(prior_temperature)
        width=space['candidates'].shape[1];self.has_traffic='traffic' in space.spaces
        self.row=nn.Sequential(nn.Linear(width,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU())
        self.residual=nn.Linear(32,1);nn.init.zeros_(self.residual.weight);nn.init.zeros_(self.residual.bias)
        self.prior=nn.Linear(width,1,bias=False)
        with torch.no_grad():
            self.prior.weight.zero_();self.prior.weight[0,14]=-30;self.prior.weight[0,15]=-1
            self.prior.weight[0,16]=2;self.prior.weight[0,17]=2;self.prior.weight[0,18]=12
        if self.has_traffic:
            self.traffic_encoder=nn.Sequential(nn.Conv2d(space['traffic'].shape[0],8,3,stride=2,padding=1),nn.ReLU(),
                nn.Conv2d(8,16,3,stride=2,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((2,3)),nn.Flatten(),nn.Linear(96,32),nn.Tanh())
        self.tools=nn.Sequential(nn.Linear(74 if self.has_traffic else 42,32),nn.Tanh(),nn.Linear(32,3))
        nn.init.zeros_(self.tools[-1].weight)
        with torch.no_grad():self.tools[-1].bias.zero_()
        self.context=nn.Sequential(nn.Linear(138 if self.has_traffic else 106,64),nn.Tanh())
        if self.signal_count:
            self.signal_row=nn.Sequential(nn.Linear(12,32),nn.ReLU(),nn.Linear(32,1))
            nn.init.zeros_(self.signal_row[-1].weight);nn.init.zeros_(self.signal_row[-1].bias)
            self.signal_prior=nn.Linear(12,1)
            with torch.no_grad():
                self.signal_prior.weight.zero_();self.signal_prior.bias.fill_(-1)
                self.signal_prior.weight[0,4]=2;self.signal_prior.weight[0,6]=2
            self.route_context=nn.Linear(74,32,bias=False);nn.init.zeros_(self.route_context.weight)

    def forward(self,obs):
        candidates=obs['candidates'];valid=candidates[:,:,24:25];rows=self.row(candidates)
        mean=(rows*valid).sum(1)/valid.sum(1).clamp(min=1)
        maximum=(rows*valid).max(1).values
        global_features=obs['global']
        if self.has_traffic:global_features=torch.cat([global_features,self.traffic_encoder(obs['traffic'])],dim=1)
        values=self.context(torch.cat([mean,maximum,global_features],dim=1))
        tools=self.tools(global_features)
        offers=torch.stack([torch.zeros_like(tools[:,0]),obs['global'][:,9:15].sum(1)*20,obs['global'][:,17:23].sum(1)*20],dim=1)
        route_logits=self.residual(rows).squeeze(-1)+self.prior(candidates).squeeze(-1)/self.prior_temperature
        if self.signal_count:
            route_logits+=(rows*torch.tanh(self.route_context(global_features))[:,None,:]).sum(-1)/(32**.5)
        logits=torch.cat([tools+offers/self.prior_temperature,route_logits],dim=1)
        if self.signal_count:
            signals=obs['signals'];signal_logits=(self.signal_row(signals)+self.signal_prior(signals)/self.prior_temperature).squeeze(-1)
            logits=torch.cat([logits,signal_logits],dim=1)
        return torch.cat([logits,values],dim=1)


class GoalHeads(nn.Module):
    latent_dim_pi=GOALS+3;latent_dim_vf=64
    def __init__(self,actions=GOALS+3):
        super().__init__();self.latent_dim_pi=actions
    def forward(self,x):return self.forward_actor(x),self.forward_critic(x)
    def forward_actor(self,x):return x[:,:self.latent_dim_pi]
    def forward_critic(self,x):return x[:,self.latent_dim_pi:]


class GoalPolicy(MaskableActorCriticPolicy):
    def __init__(self,*args,**kwargs):
        kwargs['features_extractor_class']=GoalFeatures;kwargs['normalize_images']=False
        super().__init__(*args,**kwargs)
    def _build(self,lr_schedule):
        self.mlp_extractor=GoalHeads(self.action_space.n);self.action_net=nn.Identity();self.value_net=nn.Linear(64,1)
        nn.init.zeros_(self.value_net.weight);nn.init.zeros_(self.value_net.bias)
        self.optimizer=self.optimizer_class(self.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)

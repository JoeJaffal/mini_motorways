"""Stage 1 direct-control focus hierarchy. No training entry point.

1501 context-dependent tokens; native pure Stage 1 masks; published visible
observations plus focus/role context. Full-game tools/credit/replay are separate
readiness gates, never delegated to the legacy trainer.
"""
from collections import defaultdict
from time import perf_counter

import gymnasium as gym
import numpy as np
from environment import Host, CELLS, DIRS
from practice_reward import specification,connection_potential,reward_parts,BETA,ROAD_COST
from visible_observation import VisibleObservation, observation_space

# Published root-control order. Handoff is the hierarchy's extra root context.
WAIT,DRAW,ROUNDABOUT,MOTORWAY,EDIT_MOTORWAY,ERASE,REMOVE,REMOVE_ROUNDABOUT,REMOVE_MOTORWAY,WEEKLY,HANDOFF=range(11)
CANCEL=NONE=1500
DIRECT_STAGE = "one-gap-direct"
SINGLE_BUILD_STAGE = "one-gap-single-build"
DIRECT_STAGES = (DIRECT_STAGE, SINGLE_BUILD_STAGE)
ARENA_SIZE = 12


class ConnectionPractice(gym.Env):
    schema='connection-practice-hierarchy-v4'
    metadata={'render_modes':[]}

    def __init__(self,dotnet='dotnet',host_dll=None,max_paused_tokens=4096,split='train',stage='clear',reward_mode=None):
        if split not in ('train','validation') or not 1<=max_paused_tokens<=4096:
            raise ValueError('Invalid split or pause limit')
        if stage not in ('clear','one-gap','one-gap-draw-only','one-gap-compact',*DIRECT_STAGES):raise ValueError('Unknown practice stage')
        self.single_build = stage == SINGLE_BUILD_STAGE
        default_reward = 'single-build' if self.single_build else 'score'
        self.reward_mode = default_reward if reward_mode is None else reward_mode
        specification(self.reward_mode)
        if self.single_build and self.reward_mode != default_reward:
            raise ValueError('Single-build stage requires its binary connection reward')
        if not self.single_build and self.reward_mode != 'score' and (
                stage != 'one-gap-compact' or self.reward_mode != 'connection-economy'):
            raise ValueError('Experimental reward requires its matching practice stage')
        self.stage=stage
        self.direct = stage in DIRECT_STAGES
        if self.single_build:
            self.schema = 'connection-practice-single-build-v1'
        elif self.direct:
            self.schema = 'connection-practice-direct-v1'
        self.practice_bounds=None
        self.practice_area=np.ones(1500,bool)
        self.host=Host(dotnet,host_dll)
        self.seconds=180
        self.visible_encoder=VisibleObservation()
        self.action_space=gym.spaces.Discrete(1 + ARENA_SIZE ** 2 * 4 if self.direct else 1501)
        self.observation_space=observation_space()
        self.observation_space.spaces['focus']=gym.spaces.Box(0,1,(2,30,50),np.float32)
        self.observation_space.spaces['context']=gym.spaces.Box(0,1,(8,),np.float32)
        self.max_paused_tokens=max_paused_tokens
        self.split=split
        self.timings=defaultdict(float)
        self.done=True
        self.record_actions=False
        self._generation=0
        self._mask_stamp=None
        try:
            hello=self._request(command='hello')
            self.protocol_version=hello.get('protocolVersion')
            self.simulator_version=hello.get('simulatorVersion')
            self._practice_capabilities=hello.get('capabilities',[])
            required={'connection-practice-v1','practice-pure-mask-v1','displayed-state-flags-v1','bounded-native-wait-v1'}
            if self.direct:
                required.add('practice-new-connections-v1')
            if self.single_build:
                required.add('practice-single-build-v1')
            if not hello.get('accepted') or hello.get('terminated') or hello.get('truncated') or self.protocol_version!='maskable-direct-hierarchy-v1' or self.simulator_version!='2026-11-10.f34' or not required<=set(hello.get('capabilities',[])):
                raise RuntimeError('Simulator/protocol handshake mismatch')
        except BaseException:
            self.host.close()
            raise

    def _request(self,**request):
        start=perf_counter()
        try:result=self.host.call(**request)
        except Exception:
            self.done=True
            raise
        self.timings['host_seconds']+=perf_counter()-start
        self.timings['host_calls']+=1
        return result

    def _call(self,**request):
        result=self._request(**request)
        self.raw=result['observation']
        self.network_version=result.get('networkVersion')
        try:self.visible=self.visible_encoder.visibility(self.raw).ravel()&self.practice_area
        except Exception:
            self.done=True
            raise
        stamp=(self._generation,self.network_version,tuple(self.raw['inventory']),
               tuple((o['type'],o['amount'],o['roads']) for o in self.raw['upgradeChoices']),
               bool(result['terminated']),bool(result['truncated']))
        if stamp!=self._mask_stamp:
            self._mask_cache=None
            self._direct_mask_cache = None
            self._direction_cache={}
            self._mask_stamp=stamp
        return result

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed)
        layout_seed=(options or {}).get('scenario_seed')
        if layout_seed is None:
            layout_seed=seed if seed is not None else self.np_random.integers(0,2**31-1)
        if self.stage!='clear' and 'practice-one-gap-v1' not in self._practice_capabilities:
            raise RuntimeError('Rebuild host: one-gap capability missing')
        self.scenario_seed=int(layout_seed)
        self.phase,self.tool,self.first,self.old=0,None,None,None
        self.focus=[None,None]
        self.role,self.edit_count,self.decisions=('executor' if self.direct else 'primary'),0,0
        self.paused_tokens=0
        self.actions=[]
        self._generation+=1
        self.visible_encoder.reset()
        self.practice_bounds=None
        self.practice_area[:]=True
        self._potential_stamp=None
        self.training_reward_total=0.
        self.reward_road_units=0
        self.shaping_total=0.
        self.road_cost_total=0.
        self.done=False
        self.timings.clear()
        native_stage = self.stage if self.stage in ('clear', SINGLE_BUILD_STAGE) else 'one-gap'
        starting_stock = 1 if self.single_build else 20
        result=self._call(command='reset',version='OriginalReference',practice=True,
                   practiceSplit=self.split,practiceStage=native_stage,seed=self.scenario_seed)
        buildings=self.raw['buildings']
        houses=[b for b in buildings if b['isHouse']]
        shops=[b for b in buildings if not b['isHouse']]
        valid=(result.get('simulatorVersion')==self.simulator_version and
            self.raw['version']=='OriginalReference' and not self.raw['unlimitedConstruction'] and
            self.raw['time']==0 and self.raw['tripsCompleted']==0 and not self.raw['failed'] and
            not result['terminated'] and len(houses)==1 and len(shops)==1 and
            houses[0]['color']==shops[0]['color'] and self.raw['inventory']==[starting_stock,0,0,0,0,0] and
            not self.raw['upgradeChoices'] and not any(self.raw['terrain']) and
            (not any(self.raw['infrastructure']) and not any(self.raw['connections']) if self.stage=='clear' else any(self.raw['connections'])))
        if not valid:
            self.done=True
            raise RuntimeError('Unexpected Stage 1 reset/rules/distribution; do not collect')
        if self.direct or self.stage == 'one-gap-compact':self._set_practice_area()
        self.initial_potential=self.potential()
        if self.single_build and (self.initial_potential or not self.action_masks().any()):
            self.done = True
            raise RuntimeError('Single-build layout must start disconnected with legal builds')
        return self.encode(),self.info()

    def potential(self):
        if self.reward_mode=='score':return 0.
        if self.raw['failed'] or self.raw['time']>=self.seconds-1e-7:return 0.
        if self._potential_stamp!=self.network_version:
            self._potential=connection_potential(self.raw,self.practice_area)
            self._potential_stamp=self.network_version
        return self._potential

    def expected_training_return(self):
        if self.single_build:
            return self.potential()
        if self.reward_mode=='score':return float(self.raw['tripsCompleted'])
        return self.raw['tripsCompleted']+BETA*(self.potential()-self.initial_potential)-ROAD_COST*self.reward_road_units

    def _set_practice_area(self):
        # Fixed-size arena enclosing visible starting buildings/roads, not the missing edge.
        cells=[(i%50,i//50) for i,bits in enumerate(self.raw['connections']) if bits]
        for b in self.raw['buildings']:
            cells.extend((x,y) for x in range(b['cell']['x'],b['cell']['x']+b['width'])
                         for y in range(b['cell']['y'],b['cell']['y']+b['height']))
        xs,ys=zip(*cells)
        if max(xs)-min(xs)>=12 or max(ys)-min(ys)>=12:
            raise RuntimeError('Initial layout does not fit compact arena')
        x0=max(0,min(38,(min(xs)+max(xs)-11)//2))
        y0=max(0,min(18,(min(ys)+max(ys)-11)//2))
        self.practice_bounds=(x0,x0+12,y0,y0+12)
        yy,xx=np.mgrid[:30,:50]
        self.practice_area=((xx>=x0)&(xx<x0+12)&(yy>=y0)&(yy<y0+12)).ravel()
        self.visible=self.visible_encoder.visibility(self.raw).ravel()&self.practice_area

    def encode(self):
        try:return self._encode()
        except Exception:
            self.done=True
            raise

    def _encode(self):
        start=perf_counter()
        visible_raw=self.raw
        if self.practice_bounds is not None:
            visible_raw=dict(self.raw,**dict(zip(('playableXMin','playableXMax','playableYMin','playableYMax'),self.practice_bounds)))
        obs=self.visible_encoder.encode(visible_raw,horizon=self.seconds,
            stage=self.phase,control=self.tool,paused_tokens=self.paused_tokens,
            operands=(self.first,None,self.old,None))
        focus=np.zeros((2,30,50),np.float32)
        for i,p in enumerate(self.focus):
            if p is not None and self.visible[p[1]*50+p[0]]:focus[i,p[1],p[0]]=1
        context=np.zeros(8,np.float32)
        context[['primary','secondary','executor'].index(self.role)]=1
        context[3+self.phase]=1
        context[6]=self.edit_count/8
        context[7]=min(self.paused_tokens/self.max_paused_tokens,1)
        obs.update(focus=focus,context=context)
        self.timings['encode_seconds']+=perf_counter()-start
        return obs

    def info(self):
        return dict(schema=self.schema,scenario_seed=self.scenario_seed,split=self.split,stage=self.stage,practice_bounds=self.practice_bounds,
            role=self.role,edits_in_option=self.edit_count,paused_tokens=self.paused_tokens,
            trips=self.raw['tripsCompleted'],seconds=self.raw['time'],timings=dict(self.timings),
            pass_candidate=(bool(self.raw['failed']) or self.raw['time']>=self.seconds) and self.raw['tripsCompleted']>=3)

    def _sources(self):
        if self._mask_cache is None:
            result=self._request(command='practiceMask',tool='sources')
            self._mask_cache={DRAW:self._boolean_mask(result['drawSources'],1500),
                ERASE:self._boolean_mask(result['eraseSources'],1500),REMOVE:self._boolean_mask(result['removeCells'],1500)}
        return self._mask_cache

    def _boolean_mask(self,values,count):
        mask=np.asarray(values)
        if mask.shape!=(count,) or mask.dtype!=np.bool_:
            self.done=True
            raise RuntimeError('Native boolean mask schema mismatch')
        return mask

    def _house_neighbors(self):
        cells=set()
        for b in self.raw['buildings']:
            if not b['isHouse']:continue
            x,y=b['cell']['x'],b['cell']['y']
            for dx,dy in [(0,0)]+DIRS:
                if 0<=x+dx<50 and 0<=y+dy<30:cells.add((y+dy)*50+x+dx)
        return cells

    def _draw_only_directions(self,first):
        key=(DRAW,first)
        if key not in self._direction_cache:
            result=self._request(command='practiceMask',tool='draw',x=first[0],y=first[1])
            self._direction_cache[key]=self._boolean_mask(result['directions'],8)
        directions=self._direction_cache[key].copy()
        for b in self.raw['buildings']:
            if not b['isHouse']:continue
            home=(b['cell']['x'],b['cell']['y'])
            dx,dy=DIRS[b['drivewayDirection']];outside=(home[0]+dx,home[1]+dy)
            for d,(dx,dy) in enumerate(DIRS):
                target=(first[0]+dx,first[1]+dy)
                if (first==home and target!=outside) or (target==home and first!=outside):directions[d]=False
        if self.stage=='one-gap-compact':
            for d,(dx,dy) in enumerate(DIRS):
                x,y=first[0]+dx,first[1]+dy
                if not (0<=x<50 and 0<=y<30) or not self.practice_area[y*50+x]:directions[d]=False
        return directions

    def direct_endpoints(self, action):
        slot, direction = divmod(action - 1, 4)
        y, x = divmod(slot, ARENA_SIZE)
        x += self.practice_bounds[0]
        y += self.practice_bounds[2]
        dx, dy = DIRS[direction]
        return (x, y), (x + dx, y + dy)

    def _direct_mask(self):
        if self._direct_mask_cache is None:
            result = self._request(command='practiceMask', tool='newConnections')
            native = self._boolean_mask(result['connections'], CELLS * 4).reshape(CELLS, 4)
            mask = np.zeros(self.action_space.n, dtype=bool)
            mask[WAIT] = not self.single_build
            xmin, xmax, ymin, ymax = self.practice_bounds
            for action in range(1, len(mask)):
                (x, y), (tx, ty) = self.direct_endpoints(action)
                if xmin <= tx < xmax and ymin <= ty < ymax:
                    mask[action] = native[y * 50 + x, (action - 1) % 4]
            self._direct_mask_cache = mask
        return self._direct_mask_cache.copy()

    def action_masks(self):
        if self.done:raise RuntimeError('Reset required after episode end')
        if self.direct:
            return self._direct_mask()
        mask=np.zeros(1501,bool)
        if self.role!='executor':
            mask[:1500]=self.visible
            if self.role=='secondary':mask[NONE]=True
        elif self.phase==0:
            mask[[WAIT,HANDOFF]]=True
            for tool,sources in self._sources().items():
                if self.stage in ('one-gap-draw-only','one-gap-compact') and tool!=DRAW:continue
                mask[tool]=sources.any()
        elif self.phase==1:
            mask[:1500]=self._sources()[self.tool]&self.visible
            if self.stage in ('one-gap-draw-only','one-gap-compact') and self.tool==DRAW:
                # Drawing can rotate a house driveway, implicitly removing its old edge.
                for cell in self._house_neighbors():
                    if mask[cell]:mask[cell]=self._draw_only_directions((cell%50,cell//50)).any()
            mask[CANCEL]=True
        elif self.phase==2:
            key=(self.tool,self.first)
            if key not in self._direction_cache:
                result=self._request(command='practiceMask',tool='draw' if self.tool==DRAW else 'erase',
                                     x=self.first[0],y=self.first[1])
                self._direction_cache[key]=self._boolean_mask(result['directions'],8)
            directions=self._direction_cache[key]
            if self.stage in ('one-gap-draw-only','one-gap-compact'):directions=self._draw_only_directions(self.first)
            if directions.shape!=(8,):raise RuntimeError('Native direction mask schema mismatch')
            mask[:8]=directions
            mask[CANCEL]=True
        return mask

    def _clear_operands(self):
        self.phase,self.tool,self.first,self.old=0,None,None,None

    def _review(self):
        self.role,self.edit_count='primary',0
        self._clear_operands()

    def step(self, action):
        return self._step(action, encode_after=True)

    def step_single_build(self, action):
        """Collect a terminal training transition without encoding its ending board."""
        if not self.single_build:
            raise ValueError('Single-build step requires the single-build stage')
        return self._step(action, encode_after=False)

    def _step(self, action, *, encode_after):
        if self.done:raise RuntimeError('Reset required after episode end')
        action=int(action)
        if not 0<=action<self.action_space.n or not self.action_masks()[action]:
            raise ValueError('Action outside stage interface mask')
        before,before_time=self.raw['tripsCompleted'],self.raw['time']
        before_potential=self.potential()
        before_role,before_phase=self.role,self.phase
        before_connections=self.raw['connections']
        before_stock=self.raw['inventory'][0]
        draw_metrics=dict(draw_commands=0,changed_draws=0,no_change_draws=0,new_connections=0,road_units_spent=0,road_units_refunded=0)
        self.decisions+=1
        accepted,completed=True,False
        request=None
        if self.direct:
            if action == WAIT:
                request = dict(command='wait', horizonSeconds=self.seconds)
                self._call(**request)
                completed = True
            else:
                (x, y), (tx, ty) = self.direct_endpoints(action)
                request = dict(command='draw', x=x, y=y, toX=tx, toY=ty)
        elif self.role in ('primary','secondary'):
            i=int(self.role=='secondary')
            self.focus[i]=None if action==NONE else (action%50,action//50)
            if not i:self.focus[1]=None
            self.role='executor' if i else 'secondary'
        elif self.phase and action==CANCEL:
            self._clear_operands()  # Cancellation is not a focus handoff.
        elif self.phase==0:
            if action==HANDOFF:self._review()
            elif action==WAIT:
                request=dict(command='wait',horizonSeconds=self.seconds)
                self._call(**request)
                completed=True
                self._review()
            else:
                self.tool,self.phase=action,1
        elif self.phase==1:
            self.first=(action%50,action//50)
            if self.tool==REMOVE:
                request=dict(command='build',tool='Remove',x=self.first[0],y=self.first[1])
            else:self.phase=2
        else:
            dx,dy=DIRS[action]
            request=dict(command='draw' if self.tool==DRAW else 'erase',x=self.first[0],y=self.first[1],
                         toX=self.first[0]+dx,toY=self.first[1]+dy)
        if request is not None and request['command']!='wait':
            result=self._call(**request)
            accepted=bool(result['accepted'])
            if not accepted:
                self.done=True
                raise RuntimeError('Native rejected a masked-valid action; integration defect')
            if request['command']=='draw':
                added=sum((int(b)&~int(a)).bit_count() for a,b in zip(before_connections,self.raw['connections']))//2
                changed=before_connections!=self.raw['connections']
                draw_metrics.update(draw_commands=1,changed_draws=int(changed),no_change_draws=int(not changed),new_connections=added,
                    road_units_spent=max(0,before_stock-self.raw['inventory'][0]),road_units_refunded=max(0,self.raw['inventory'][0]-before_stock))
            completed=True
            self.edit_count+=1
            self._clear_operands()
            if self.direct:
                self.edit_count = 0
                direction = (action - 1) % 4
                links = self.raw['connections']
                selected = links[y * 50 + x] & (1 << direction)
                reverse = links[ty * 50 + tx] & (1 << ((direction + 4) % 8))
                removed = any(a & ~b for a, b in zip(before_connections, links))
                if added != 1 or not selected or not reverse or removed:
                    self.done = True
                    raise RuntimeError('Native draw must add exactly the selected connection')
            elif self.edit_count>=8:self._review()
        self.paused_tokens=0 if self.raw['time']>before_time else self.paused_tokens+1
        horizon=self.raw['time']>=self.seconds-1e-7
        terminated=self.single_build or bool(self.raw['failed']) or horizon
        operational=self.paused_tokens>=self.max_paused_tokens and not terminated
        truncated=operational
        self.done=terminated or truncated
        reward,shaping,cost=reward_parts(self.reward_mode,trips=self.raw['tripsCompleted']-before,before=before_potential,after=self.potential(),spent=draw_metrics['road_units_spent'],terminated=terminated)
        self.reward_road_units+=draw_metrics['road_units_spent']
        self.training_reward_total+=reward;self.shaping_total+=shaping;self.road_cost_total+=cost
        if not np.isclose(self.training_reward_total,self.expected_training_return(),atol=1e-8,rtol=1e-8):raise RuntimeError('Reward ledger mismatch')
        info=self.info()
        info.update(training_reward=reward,trip_reward=self.raw['tripsCompleted']-before,connection_shaping=shaping,road_cost=cost,potential=self.potential(),**draw_metrics,accepted=accepted,command_completed=completed,operational_truncation=operational,
            ending_reason='single_build' if self.single_build else 'game_over' if self.raw['failed'] else 'task_horizon' if horizon else
                'paused_policy_stall' if operational else None)
        if operational:info['pass_candidate']=False
        if self.record_actions:
            self.actions.append(dict(action=action,role=before_role,phase=before_phase,
                after_role=self.role,after_phase=self.phase,focus=list(self.focus),
                request=request,seconds=self.raw['time'],trips=self.raw['tripsCompleted']))
        observation = self.encode() if encode_after else None
        return observation,reward,terminated,truncated,info

    def close(self):self.host.close()

"""One city observation/action interface for service, waiting and traffic practice.

The native reference edits are never read by this environment or its learner.
Rewards are native completed trips, with warmup deliveries excluded.
"""
import gymnasium as gym
import numpy as np
from city_road_pilot import CityRoadEnv, FORWARD
from visible_observation import WIDTH

JOIN = 'midgame-network-join'
ROUTE = 'midgame-network-route'
DELAY = 'midgame-network-delay'
QUIET = 'midgame-network-quiet'
PRIORITY = 'traffic-priority-established'
SWAP = 'traffic-priority-established-swap'
LOW = 'traffic-junction-low-live'
HIGH = 'traffic-junction-high-live'
RESERVE = 'midgame-network-reserve'
LESSONS = (JOIN, ROUTE, DELAY, QUIET, PRIORITY, SWAP, LOW, HIGH, RESERVE)
STAGES = {'city': ('city',),
          'strategy-balanced': ('city',)*8 + (RESERVE,)*4 + (PRIORITY, SWAP, PRIORITY, SWAP),
          'strategy-mixed': ('city', 'city', 'city', 'city', RESERVE, RESERVE, RESERVE, RESERVE,
                             PRIORITY, SWAP, JOIN, ROUTE, DELAY, QUIET),
          'connections': (JOIN, ROUTE, ROUTE),
          'waiting': (DELAY, DELAY, QUIET, JOIN),
          'traffic': (PRIORITY, SWAP, LOW, HIGH),
          'reserve': (RESERVE, RESERVE, RESERVE, JOIN, ROUTE, DELAY),
          'reserve-mixed': ('city', 'city', RESERVE, RESERVE, JOIN, ROUTE, DELAY),
          'mixed': ('city', 'city', 'city', 'city', JOIN, ROUTE, DELAY, QUIET, PRIORITY, SWAP, LOW, HIGH)}


class CityCurriculumEnv(CityRoadEnv):
    def __init__(self, dll, stage='mixed', worker=0, workers=1, seed_start=110_000_000, validation=False, collapse_forced_wait=False, city_horizon=600, fast_priority_tail=False, reserve_warmup_seconds=0, reserve_delay_seconds=None, allow_bridges=False):
        super().__init__(dll, horizon=city_horizon, observation_horizon=600, allow_bridges=allow_bridges)
        self.city_horizon = city_horizon
        self.stage, self.worker, self.workers = stage, worker, workers
        self.collapse_forced_wait = collapse_forced_wait
        self.fast_priority_tail = fast_priority_tail
        if not 0<=reserve_warmup_seconds<=6:raise ValueError('Reserve warmup must be 0..6 seconds')
        self.reserve_warmup_seconds=reserve_warmup_seconds
        if reserve_delay_seconds is not None and (not 1<=reserve_delay_seconds<=16 or reserve_warmup_seconds):
            raise ValueError('Explicit reserve delay must be 1..16 with no warmup')
        self.reserve_delay_seconds=reserve_delay_seconds
        if fast_priority_tail and not collapse_forced_wait:
            raise ValueError('Fast terminal priority tail requires forced-Wait compression')
        self.cursor, self.episode = seed_start+worker, worker
        self.split = 'validation' if validation else 'train'

    def reset(self, *, seed=None, options=None):
        gym.Env.reset(self, seed=seed)
        if options is None:
            # Fixed worker tasks balance rollout decisions. Cycling episodes
            # would nearly erase one-decision lessons beside long cities.
            index = self.worker if self.stage == 'strategy-balanced' else self.episode
            options = dict(scenario_seed=self.cursor, exercise=STAGES[self.stage][index % len(STAGES[self.stage])])
            self.cursor += self.workers
            self.episode += 1
        self.exercise = options['exercise']
        self.scenario_seed = options['scenario_seed']
        self.horizon = self.city_horizon
        if self.exercise == 'city':
            obs, info = super().reset(seed=seed, options=options)
            return obs, dict(info, exercise='city')
        if self.exercise not in LESSONS:
            raise ValueError('Unknown curriculum exercise')
        delay = self.reserve_delay_seconds if self.exercise==RESERVE else None
        extra = {} if delay is None else dict(reserveDelaySeconds=delay)
        result = self.host.call(command='reset' if delay is None else 'resetReserveDelay', version='OriginalReference', practice=True,
                                practiceStage='curriculum-'+self.exercise, practiceSplit=self.split,
                                seed=self.scenario_seed, **extra)
        if not result.get('accepted') or result['terminated'] or result['truncated']:
            raise RuntimeError('Native fixture reset failed')
        self.raw = result['observation']
        self.encoder.reset()
        self.observation()
        # Preserve visible movement history during the live traffic warmup.
        if self.exercise in (LOW, HIGH):
            while self.raw['time'] < 36-1e-8:
                result = self.host.call(command='wait', horizonSeconds=36)
                if result['terminated'] or result['truncated']:
                    raise RuntimeError('Traffic warmup ended early')
                self.raw = result['observation']
                self.observation()
        if self.exercise==RESERVE and self.reserve_warmup_seconds:
            # Easier initial states, not teacher actions in the rollout. This
            # fixed warmup never reads the hidden future spawn time. Evaluation
            # defaults to the original full-delay exercise.
            until=self.raw['time']+self.reserve_warmup_seconds
            buildings=len(self.raw['buildings'])
            while self.raw['time']<until-1e-8:
                result=self.host.call(command='wait',horizonSeconds=until)
                if result['terminated'] or result['truncated']:
                    raise RuntimeError('Reserve warmup ended early')
                self.raw=result['observation'];self.observation()
            if len(self.raw['buildings'])!=buildings:
                raise RuntimeError('Reserve warmup must finish before new buildings appear')
        self.start_time = self.raw['time']
        self.horizon = 120 if self.exercise.startswith('traffic-') else self.start_time+60
        self.start_score = self.raw['tripsCompleted']
        self.initial_served = {b['id']: b['served'] for b in self.raw['buildings'] if not b['isHouse']}
        self.initial_pending = [k for k,v in self.initial_served.items() if v == 0]
        shops = [b for b in self.raw['buildings'] if not b['isHouse']]
        self.urgent_id = max(shops, key=lambda b:b['demand'])['id']
        self.stock_initial = self.raw['inventory'][0]
        self.future_stock = None
        self.weekly_awards = self.road_actions = self.wait_actions = 0
        self.first_action = None
        self.done = False
        self.cached_mask = None
        return self.observation(), self.info()

    def info(self):
        row = super().info()
        if self.exercise == 'city':
            return dict(row, exercise='city')
        delivered = {b['id']: b['served']-self.initial_served[b['id']]
                     for b in self.raw['buildings'] if b['id'] in self.initial_served}
        future = {b['id']: b['served'] for b in self.raw['buildings']
                  if not b['isHouse'] and b['id'] not in self.initial_served}
        if future and self.future_stock is None:
            self.future_stock = self.raw['inventory'][0]
        delivered.update(future)
        row.update(exercise=self.exercise, seconds=row['seconds']-self.start_time,
                   trips=row['trips']-self.start_score, stock_initial=self.stock_initial,
                   new_deliveries=sum(delivered[k] for k in self.initial_pending)+sum(future.values()),
                   future_stock=self.future_stock, future_targets=len(future),
                   urgent_deliveries=delivered[self.urgent_id], served=delivered,
                   first_action=self.first_action)
        return row

    def action_masks(self):
        if self.exercise == 'city':
            return super().action_masks()
        if self.done:
            return np.zeros(self.action_space.n, dtype=bool)
        if self.cached_mask is None:
            result = self.host.call(command='curriculumMask')
            self.cached_mask = np.array([True, *result['connections']], dtype=bool)
        return self.cached_mask

    def _step_once(self, action):
        if self.exercise == 'city':
            return super().step(action)
        action = int(action)
        if self.done or not self.action_space.contains(action) or not self.action_masks()[action]:
            raise ValueError('Unavailable curriculum action')
        before = self.raw
        if action:
            cell,d = divmod(action-1,4)
            x,y = cell%WIDTH, cell//WIDTH
            dx,dy = FORWARD[d]
            result = self.host.call(command='draw', x=x, y=y, toX=x+dx, toY=y+dy)
            self.road_actions += 1
            if self.first_action is None: self.first_action = action
        else:
            result = self.host.call(command='wait', horizonSeconds=self.horizon)
            self.wait_actions += 1
        self.raw = result['observation']
        self.cached_mask = None
        reward = result['tripsDelta']
        if not result['accepted'] or result['truncated'] or reward != self.raw['tripsCompleted']-before['tripsCompleted']:
            raise RuntimeError('Invalid native reward transition')
        if action and self.raw['time'] != before['time']:
            raise RuntimeError('Construction advanced time')
        terminated = bool(result['terminated'])
        truncated = not terminated and self.raw['time']+.05 > self.horizon+1e-9
        self.done = terminated or truncated
        return self.observation(), float(reward), terminated, truncated, self.info()

    def step(self, action):
        obs,reward,terminated,truncated,info=self._step_once(action)
        forced=0
        if (self.fast_priority_tail and self.exercise in (PRIORITY, SWAP)
                and not self.done and self.raw['inventory'][0] == 0
                and not self.action_masks()[1:].any()):
            # These fixed priority fixtures have no spawns, stock awards or
            # removals. After spending their sole road, no choice can return.
            # Run the same native ticks, avoiding IPC/encoding at each second.
            # Only terminal motion history differs; this finite lesson ends
            # with terminated=True and never bootstraps that observation.
            before=self.raw
            ticks=int(round((self.horizon-before['time'])/.05))
            result=self.host.call(command='step',ticks=ticks)
            self.raw=result['observation'];self.cached_mask=None
            if (not result['accepted'] or result['truncated'] or self.raw['upgradeChoices']
                    or self.raw['inventory'] != before['inventory']
                    or len(self.raw['buildings']) != len(before['buildings'])
                    or result['tripsDelta'] != self.raw['tripsCompleted']-before['tripsCompleted']):
                raise RuntimeError('Priority terminal-tail contract changed')
            terminated=bool(result['terminated'])
            truncated=not terminated and self.raw['time']+.05>self.horizon+1e-9
            if not (terminated or truncated):raise RuntimeError('Priority tail did not end')
            self.done=True
            forced=int(np.ceil(self.raw['time']-before['time']-1e-9))
            self.wait_actions+=forced
            reward+=result['tripsDelta']
            obs,info=self.observation(),self.info()
        # With gamma=1, combining forced Wait transitions preserves total native
        # reward. Stop immediately when a legal build returns (e.g. weekly stock).
        while self.collapse_forced_wait and not self.done and not self.action_masks()[1:].any():
            obs,extra,terminated,truncated,info=self._step_once(0)
            reward+=extra
            forced+=1
        if self.collapse_forced_wait and self.exercise != 'city' and truncated:
            # These lessons optimize the finite measured window, with no unknown
            # post-lesson value bootstrapped from a different city task.
            terminated,truncated=True,False
        return obs,reward,terminated,truncated,dict(info,forced_waits=forced)

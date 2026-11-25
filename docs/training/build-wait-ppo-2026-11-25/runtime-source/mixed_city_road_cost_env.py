"""Fixed worker mix: native city score plus bounded road-cost practice."""
import math
import gymnasium as gym
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT, SMALL_STOCK


class AccountedCityCurriculumEnv(CityCurriculumEnv):
    def _step_once(self,action):
        before=self.raw['inventory'][0]
        result=super()._step_once(action)
        # Account at each primitive transition, before a compressed forced Wait
        # can replenish stock. Road actions consume no simulation time.
        if action:self.step_paid_units+=max(0,before-self.raw['inventory'][0])
        return result


class MixedCityRoadCostEnv(gym.Wrapper):
    def __init__(self,dll,*,road_cost=.04,worker=0,workers=16,seed_start=210000000):
        if not math.isfinite(road_cost) or not 0<=road_cost<=.04:raise ValueError('Invalid road cost')
        super().__init__(AccountedCityCurriculumEnv(dll,stage='city',worker=worker,workers=workers,
                         seed_start=seed_start,collapse_forced_wait=True,city_horizon=600,allow_bridges=True))
        self.configured_cost=road_cost
        self.fixed_exercise=('city','city',SMALL_TIGHT,SMALL_STOCK)[worker%4]
        self.effective_cost=0.
        self.paid_units=0
        self.native_return=0.
        self.initial_stock=0

    def reset(self,*,seed=None,options=None):
        if options is None:
            options=dict(scenario_seed=self.env.cursor,exercise=self.fixed_exercise)
            self.env.cursor+=self.env.workers;self.env.episode+=1
        if options['exercise'] not in ('city',SMALL_TIGHT,SMALL_STOCK):raise ValueError('Unsupported task')
        self.effective_cost=0. if options['exercise']=='city' else self.configured_cost
        obs,info=self.env.reset(seed=seed,options=options)
        self.initial_stock=self.env.raw['inventory'][0]
        if options['exercise']!='city' and not 0<=info['stock_initial']<=18:raise RuntimeError('Practice stock bound')
        self.paid_units=0;self.native_return=0.
        return obs,self._info(info)

    def action_masks(self):return self.env.action_masks()

    def _info(self,info):
        return dict(info,stock_initial=self.initial_stock,native_return=self.native_return,paid_units=self.paid_units,road_cost=self.effective_cost,
                    shaped_return=self.native_return-self.effective_cost*self.paid_units)

    def step(self,action):
        before=self.env.raw['inventory'][0]
        self.env.step_paid_units=0
        obs,reward,terminated,truncated,info=self.env.step(action)
        after=self.env.raw['inventory'][0]
        if self.env.exercise!='city' and (info['weekly_awards'] or after>before):raise RuntimeError('Practice replenishment')
        spent=self.env.step_paid_units
        self.paid_units+=spent
        self.native_return+=reward
        if not math.isclose(self.native_return,info['trips']):raise RuntimeError('Native ledger mismatch')
        return obs,float(reward-self.effective_cost*spent),terminated,truncated,self._info(info)

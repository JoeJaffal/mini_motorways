"""Opt-in road-unit cost for finite, single-connection practice only."""
import math
import gymnasium as gym
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT, SMALL_STOCK


class CityRoadCostEnv(gym.Wrapper):
    def __init__(self, dll, *, road_cost=0., **kwargs):
        if not math.isfinite(road_cost) or not 0 <= road_cost <= .04:
            raise ValueError('Road cost must be finite and between0 and.04')
        super().__init__(CityCurriculumEnv(dll, stage='road-cost', **kwargs))
        self.road_cost = float(road_cost)
        self.paid_units = 0
        self.native_return = 0.

    def reset(self, **kwargs):
        options = kwargs.get('options')
        if options and options.get('exercise') not in (SMALL_TIGHT, SMALL_STOCK):
            raise ValueError('Road cost is restricted to single-connection practice')
        obs, info = self.env.reset(**kwargs)
        if not 0 <= info['stock_initial'] <= 18:
            raise RuntimeError('Reward-ordering stock bound changed')
        self.paid_units = 0
        self.native_return = 0.
        return obs, self._info(info)

    def _info(self, info):
        return dict(info, native_return=self.native_return, paid_units=self.paid_units,
                    road_cost=self.road_cost,
                    shaped_return=self.native_return-self.road_cost*self.paid_units)

    def action_masks(self):
        return self.env.action_masks()

    def step(self, action):
        before = self.env.raw['inventory'][0]
        obs, reward, terminated, truncated, info = self.env.step(action)
        spent = max(0, before-self.env.raw['inventory'][0])
        if info['weekly_awards'] or self.env.raw['inventory'][0] > before:
            raise RuntimeError('Unexpected stock replenishment in finite cost lesson')
        self.paid_units += spent
        self.native_return += reward
        if not math.isclose(self.native_return, info['trips']):
            raise RuntimeError('Native reward ledger mismatch')
        return obs, float(reward-self.road_cost*spent), terminated, truncated, self._info(info)

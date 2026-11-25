"""Opt-in first-delivery practice; native city rewards and rules are unchanged."""
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT, SMALL_STOCK


class CityRouteOutcomeEnv(CityCurriculumEnv):
    def __init__(self, dll, *, worker=0, workers=1, seed_start=248000000,
                 validation=False, collapse_forced_wait=True, fast_small_city_tail=False):
        self.zero_cost_builds = 0
        self.outcome_return = 0.
        super().__init__(dll, stage='single-connection', worker=worker, workers=workers,
                         seed_start=seed_start, validation=validation, allow_bridges=True,
                         collapse_forced_wait=collapse_forced_wait,
                         fast_small_city_tail=fast_small_city_tail, small_city_horizon=300)

    def reset(self, *, seed=None, options=None):
        if options is None:
            options = dict(exercise=SMALL_TIGHT if self.worker % 16 < 12 else SMALL_STOCK,
                           scenario_seed=self.cursor)
            self.cursor += self.workers
        if options['exercise'] not in (SMALL_TIGHT, SMALL_STOCK):
            raise ValueError('Route outcome practice requires a single native target')
        self.zero_cost_builds = 0
        self.outcome_return = 0.
        obs, info = super().reset(seed=seed, options=options)
        assert len(self.initial_pending) == 1 and len(self.raw['buildings']) == 2
        assert self.start_score == 0 and self.stock_initial > 0
        return obs, info

    def step(self, action):
        before_stock = self.raw['inventory'][0]
        obs, native_reward, base_terminal, base_truncated, info = super().step(action)
        assert info['weekly_awards'] == 0 and len(self.raw['buildings']) == 2
        if action and info['road_stock'] == before_stock:
            self.zero_cost_builds += 1
        success = info['new_deliveries'] > 0
        reward = 0.
        bonus = 0.
        if success:
            remaining = info['road_stock']/self.stock_initial
            assert 0 <= remaining <= 1
            # All edits count, including zero-cost extra edges. No shortest-path
            # target, negative failure reward, or prescribed construction action.
            bonus = .20*remaining + .05/(1+info['road_actions'])
            reward = 1.+bonus
        done = success or base_terminal or base_truncated
        self.done = done
        self.outcome_return += reward
        assert 0 <= self.outcome_return <= 1.25
        return obs, reward, done, False, dict(info,
            task_success=success, task_return=self.outcome_return, efficiency_bonus=bonus,
            paid_units=self.stock_initial-info['road_stock'], zero_cost_builds=self.zero_cost_builds,
            native_reward=native_reward, underlying_terminated=base_terminal,
            underlying_truncated=base_truncated,
            task_end='first_delivery' if success else ('underlying_end' if done else None),
            reward_source='First actual delivery plus bounded success-only road-economy bonus; not native city score',
            terminal_observation_may_follow_forced_tail=bool(info.get('forced_waits', 0)))

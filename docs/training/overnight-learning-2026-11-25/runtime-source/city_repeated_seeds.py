"""Repeated native cities for a fitting diagnostic, without action guidance."""
from city_curriculum import CityCurriculumEnv

class CityRepeatedSeedsEnv(CityCurriculumEnv):
    def __init__(self, *args, repeat_city_count, finite_city_horizon=False, **kwargs):
        super().__init__(*args, **kwargs)
        if self.stage != 'city' or repeat_city_count < 1:
            self.close()
            raise ValueError('Repeated seeds require city stage and positive count')
        self.finite_city_horizon=finite_city_horizon
        self.repeat_city_count=repeat_city_count
        self.repeat_seed_start=self.cursor-self.worker
        self.repeat_episode=0

    def reset(self, *, seed=None, options=None):
        if options is None:
            options=dict(exercise='city',scenario_seed=self.repeat_seed_start+(self.worker+self.repeat_episode)%self.repeat_city_count)
            self.repeat_episode+=1
        return super().reset(seed=seed,options=options)

    def step(self, action):
        obs,reward,terminated,truncated,info=super().step(action)
        info=dict(info,native_game_over=terminated,finite_horizon_end=bool(self.finite_city_horizon and truncated))
        if self.finite_city_horizon and truncated:
            terminated,truncated=True,False
        return obs,reward,terminated,truncated,info

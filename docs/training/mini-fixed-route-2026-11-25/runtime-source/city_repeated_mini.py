"""Repeat a native training fixture for a bounded learnability diagnostic."""
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT


class CityRepeatedMiniEnv(CityCurriculumEnv):
    def __init__(self, dll, *, repeat_mini_seed, **kwargs):
        self.repeat_mini_seed = int(repeat_mini_seed)
        super().__init__(dll, **kwargs)

    def reset(self, *, seed=None, options=None):
        if options is None:
            options = dict(exercise=SMALL_TIGHT, scenario_seed=self.repeat_mini_seed)
        return super().reset(seed=seed, options=options)

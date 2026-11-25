"""Native midgame starts replayed from an older policy; never action targets.

The recorded prefix is consumed only during reset. PPO sees and controls every
subsequent decision and receives only subsequent native delivery rewards.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from city_curriculum import CityCurriculumEnv
from city_road_pilot import CityRoadEnv


def raw_digest(raw):
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def observation_digest(observation):
    h = hashlib.sha256()
    for key, value in sorted(observation.items()):
        a = np.ascontiguousarray(value)
        h.update(key.encode()); h.update(a.dtype.str.encode())
        h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


class CityRecordedStartEnv(CityCurriculumEnv):
    """Three workers out of four use recorded starts; one keeps cold cities."""
    def __init__(self, dll, *, city_starts, **kwargs):
        manifest = json.loads(Path(city_starts).read_text())
        if manifest.get('schema') != 'native-city-starts-v1' or not manifest.get('starts'):
            raise ValueError('Expected a nonempty native city-start manifest')
        if hashlib.sha256(Path(dll).read_bytes()).hexdigest() != manifest['host_sha256']:
            raise ValueError('Recorded city starts require the exact native host')
        if kwargs.get('stage', 'mixed') != 'city' or not kwargs.get('allow_bridges', False):
            raise ValueError('Recorded starts currently require bridge-enabled city training')
        self.starts = manifest['starts']
        rank = kwargs.get('worker', 0)
        count = kwargs.get('workers', 1)
        self.start_cursor = rank-rank//4-1
        self.start_stride = count-(count+3)//4
        if count < 4 or count % 4:
            raise ValueError('Recorded-start mixtures require a multiple of four workers')
        if any(p['seconds'] >= kwargs.get('city_horizon', 600) for p in self.starts):
            raise ValueError('City horizon must extend beyond recorded starts')
        self.initial_seconds = self.initial_trips = 0
        self.prefix_id = None
        super().__init__(dll, **kwargs)

    def reset(self, *, seed=None, options=None):
        self.initial_seconds = self.initial_trips = 0
        self.prefix_id = None
        if options is not None or self.worker % 4 == 0:
            return super().reset(seed=seed, options=options)
        # Rotate all starts independently of their scores. No future information
        # enters the observation or selects actions after reset.
        prefix = self.starts[self.start_cursor % len(self.starts)]
        self.start_cursor += self.start_stride
        obs, _ = super().reset(seed=seed, options=dict(exercise='city', scenario_seed=prefix['seed']))
        for action in prefix['actions']:
            if self.done or not self.action_masks()[action]:
                raise RuntimeError('Recorded prefix contains an unavailable action')
            obs, _, _, _, _ = CityRoadEnv.step(self, action)
        if self.done or raw_digest(self.raw) != prefix['raw_sha256'] or observation_digest(obs) != prefix['observation_sha256']:
            raise RuntimeError('Recorded city start did not replay exactly')
        self.initial_seconds = self.raw['time']
        self.initial_trips = self.raw['tripsCompleted']
        self.prefix_id = prefix['seed']
        self.road_actions = self.wait_actions = self.weekly_awards = 0
        return obs, self.info()

    def info(self):
        row = super().info()
        row.update(initial_seconds=self.initial_seconds, initial_trips=self.initial_trips, prefix_id=self.prefix_id)
        if self.prefix_id is not None:
            row.update(exercise='city-recorded-start', trips=row['trips']-self.initial_trips)
        return row

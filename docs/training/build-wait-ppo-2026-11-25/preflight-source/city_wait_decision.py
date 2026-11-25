"""Explicit one-decision practice reward; native city rewards are unchanged."""
import gymnasium as gym
from city_road_pilot import CityRoadEnv
from city_curriculum import CityCurriculumEnv, JOIN, ROUTE, QUIET


SCHEDULE = ('match', 'join', 'match', 'route', 'match', 'join', 'match', 'route',
            'mismatch', 'mismatch', 'homes', 'destinations', 'quiet', 'quiet', 'quiet', 'quiet')
NEEDS_BUILD = frozenset(('match', 'join', 'route'))


class CityWaitDecisionEnv(CityCurriculumEnv):
    def __init__(self, dll, *, worker=0, workers=1, seed_start=245000000,
                 validation=False, bandit=True):
        CityRoadEnv.__init__(self, dll, horizon=600, observation_horizon=600, allow_bridges=True)
        self.worker, self.workers = worker, workers
        self.cursor = seed_start + worker
        self.case_cursor = worker
        self.split = 'validation' if validation else 'train'
        self.bandit = bandit

    def reset(self, *, seed=None, options=None):
        gym.Env.reset(self, seed=seed)
        if options is None:
            options = dict(case=SCHEDULE[self.case_cursor % len(SCHEDULE)], scenario_seed=self.cursor)
            self.cursor += self.workers
            self.case_cursor += self.workers
        self.case = options['case']
        if self.case not in SCHEDULE:
            raise ValueError('Unknown build-or-Wait lesson')
        self.scenario_seed = int(options['scenario_seed'])
        self.exercise = {'join': JOIN, 'route': ROUTE, 'quiet': QUIET}.get(
            self.case, 'wait-decision-' + self.case)
        result = self.host.call(command='reset', version='OriginalReference', practice=True,
            practiceStage='curriculum-' + self.exercise, practiceSplit=self.split, seed=self.scenario_seed)
        if not result['accepted'] or result['terminated'] or result['truncated']:
            raise RuntimeError('Native decision fixture reset failed')
        self.raw = result['observation']
        homes = [b for b in self.raw['buildings'] if b['isHouse']]
        shops = [b for b in self.raw['buildings'] if not b['isHouse']]
        if self.case in ('match', 'mismatch', 'homes', 'destinations'):
            expected = {'match': (1, 1), 'mismatch': (1, 1), 'homes': (2, 0), 'destinations': (0, 2)}
            assert (len(homes), len(shops)) == expected[self.case]
            compatible = any(h['color'] == d['color'] for h in homes for d in shops)
            assert compatible == (self.case == 'match')
        self.encoder.reset()
        self.observation()
        self.warmup = int(options.get('warmup_seconds', self.scenario_seed % 31))
        if not 0 <= self.warmup <= 30:
            raise ValueError('Warmup must be 0..30 seconds')
        # Initial-state variation, not actions in the learning episode. Keep a
        # final visible frame interval for motion features; never expose velocities.
        for seconds in (max(0, self.warmup - 1), min(1, self.warmup)):
            if not seconds:
                continue
            before = self.raw
            result = self.host.call(command='step', ticks=20 * seconds)
            self.raw = result['observation']
            if (not result['accepted'] or result['terminated'] or result['truncated']
                    or self.raw['inventory'] != before['inventory']
                    or len(self.raw['buildings']) != len(before['buildings'])
                    or self.raw['upgradeChoices']):
                raise RuntimeError('Initial waiting prefix changed fixture contract')
            self.observation()
        self.horizon = self.raw['time'] + 60
        self.start_score = self.raw['tripsCompleted']
        self.weekly_awards = self.road_actions = self.wait_actions = 0
        self.first_action = None
        self.cached_mask = None
        self.done = False
        if not self.action_masks()[1:].any():
            raise RuntimeError('Decision lesson must offer both Wait and construction')
        return self.observation(), self.info()

    def info(self):
        info = CityRoadEnv.info(self)
        return dict(info, exercise='build-wait-' + self.case, case=self.case,
                    warmup_seconds=self.warmup, native_trips_since_reset=info['trips'] - self.start_score)

    def step(self, action):
        obs, native_reward, terminated, truncated, info = self._step_once(action)
        if not self.bandit:
            return obs, native_reward, terminated, truncated, info
        correct = (int(action) != 0) == (self.case in NEEDS_BUILD)
        self.done = True
        return obs, float(correct), True, False, dict(info, task_success=correct,
            native_reward=native_reward, native_terminated=terminated, native_truncated=truncated,
            reward_source='Explicit one-decision build-or-Wait task; not native city score')

"""Native priority and shared-junction exercises with visible traffic."""

from collections import Counter

import gymnasium as gym
import numpy as np

from connection_practice import ARENA_SIZE
from construction_practice import EDGE_END, ConstructionPractice, advance, edge_id, endpoints, inside, tile
from environment import CELLS, DIRS
from score_wait_ppo import native_build_or_wait
from visible_observation import HEIGHT, WIDTH

PRIORITY = ('traffic-priority', 'traffic-priority-swap')
PRIORITY_THREE = ('traffic-priority-three', 'traffic-priority-three-shift')
JUNCTION = ('traffic-junction-low', 'traffic-junction-high')
CHANNELS = 24
LOCAL_ACTIONS = np.array([inside(endpoints(a)[1]) for a in range(1, EDGE_END)])


class TrafficPractice(ConstructionPractice):
    def start(self, stage, split, seed):
        self.stage, self.seed, self.edits = stage, seed, 0
        outcome = self.call(command='reset', version='OriginalReference', practice=True,
                            practiceStage='curriculum-'+stage, practiceSplit=split, seed=seed)
        if not outcome['accepted'] or outcome['terminated'] or outcome['truncated']:
            raise RuntimeError(f'Native reset failed: {outcome.get("message")}')
        xs, ys = np.nonzero(np.asarray(self.raw['terrain']).reshape(HEIGHT, WIDTH).T != 2)
        if max(xs.max()-xs.min(), ys.max()-ys.min()) >= ARENA_SIZE:
            raise RuntimeError('Traffic fixture exceeds the local board')
        self.x0 = int(np.clip((xs.min()+xs.max()-ARENA_SIZE+1)//2, 0, WIDTH-ARENA_SIZE))
        self.y0 = int(np.clip((ys.min()+ys.max()-ARENA_SIZE+1)//2, 0, HEIGHT-ARENA_SIZE))
        y, x = np.mgrid[:ARENA_SIZE, :ARENA_SIZE]
        self.cells = (y+self.y0)*WIDTH+x+self.x0
        self.inventory = self.raw['inventory'][0]

    def mask(self):
        response = self.host.call(command='curriculumMask')
        candidates = np.asarray(response['connections']).reshape(CELLS, 4)[self.cells.ravel()].ravel()
        self.legal = np.r_[True, candidates & LOCAL_ACTIONS]
        return self.legal

    def controls(self):
        rows = self.host.call(command='curriculumReference')['edits']
        return {r['kind']: edge_id(self.local((r['x'], r['y'])), self.local((r['toX'], r['toY'])))
                for r in rows}


def visible_traffic(raw):
    return [v for v in raw['vehicles'] if v['visible'] and str(v['stage']).lower() in
            ('1', '5', 'outbound', 'returning')]


def movement_density(practice):
    values = np.zeros((ARENA_SIZE, ARENA_SIZE), dtype=np.float32)
    for car in visible_traffic(practice.raw):
        x, y = practice.local((round(car['x']), round(car['y'])))
        if inside((x, y)):
            values[y, x] += .25
    return values


def rooted_tiles(links, origin):
    """Follow existing visible links from a parcel entrance."""
    roots = np.zeros_like(links, dtype=np.float32)
    pending = [origin]
    roots[origin[1], origin[0]] = 1
    while pending:
        x, y = pending.pop()
        for d in range(len(DIRS)):
            if not (links[y, x] & (1 << d)):
                continue
            a, b = advance((x, y), d)
            if inside((a, b)) and roots[b, a] == 0 and links[b, a] & (1 << ((d+4) % 8)):
                roots[b, a] = 1
                pending.append((a, b))
    return roots


class TrafficEnvironment(gym.Env):
    metadata = {'render_modes': []}

    def __init__(self, dll, stage=PRIORITY[0], worker=0, workers=1, horizon=100, wait_ticks=200,
                 warm_seconds=18, seed_start=2370000, use_roots=False, shop_count=2):
        self.env = TrafficPractice(dll)
        self.stage, self.worker, self.workers, self.episode = stage, worker, workers, 0
        self.horizon, self.wait_ticks, self.warm_seconds = horizon, wait_ticks, warm_seconds
        self.seed_start = seed_start
        self.use_roots = use_roots
        self.action_space = gym.spaces.Discrete(EDGE_END)
        self.observation_space = gym.spaces.Dict({
            'grid': gym.spaces.Box(0, 8, (CHANNELS, ARENA_SIZE, ARENA_SIZE), np.float32),
            'shops': gym.spaces.Box(-1, 12, (shop_count, 5), np.float32),
            'clock': gym.spaces.Box(0, 8, (4,), np.float32),
        })
        if use_roots:
            self.observation_space.spaces['roots'] = gym.spaces.Box(
                0, 1, (shop_count, ARENA_SIZE, ARENA_SIZE), np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if options is None:
            options = dict(stage=self.stage, split='train',
                           layout_seed=self.seed_start+self.worker+self.workers*self.episode)
            self.episode += 1
        w = self.env
        w.start(options['stage'], options['split'], options['layout_seed'])
        if len(self.served()) != self.observation_space.spaces['shops'].shape[0]:
            raise RuntimeError(f'Shop count does not match the observation space for {w.stage}')
        self.actions = []
        self.queue_sum = 0
        self.queue_peak = 0
        self.queue_samples = 0
        self.previous_movement = np.zeros((ARENA_SIZE, ARENA_SIZE), dtype=np.float32)
        if w.stage.startswith('traffic-junction') and self.warm_seconds:
            recent_ticks = min(round(self.warm_seconds*20), 100)
            history_ticks = round(self.warm_seconds*20)-recent_ticks
            for capture_previous, ticks in ((False, history_ticks), (True, recent_ticks)):
                if capture_previous:
                    self.previous_movement = movement_density(w)
                if ticks > 0:
                    event = w.call(command='step', ticks=ticks)
                    if event['terminated'] or event['truncated']:
                        raise RuntimeError(f'Warmup failed on {w.stage}, seed {w.seed}')
        self.initial_trips = w.raw['tripsCompleted']
        self.initial_served = self.served()
        self.started_at = w.raw['time']
        self.first_build_time = None
        w.mask()
        self.cached = self.observation()
        return self.cached, {}

    def served(self):
        return {str(b['id']): int(b['served']) for b in self.env.raw['buildings'] if not b['isHouse']}

    def observation(self):
        w = self.env
        raw = w.raw
        cells = w.cells
        kinds = np.asarray(raw['buildingKinds'])[cells]
        colors = np.asarray(raw['buildingColors'])[cells]
        links = np.asarray(raw['connections'])[cells]
        grid = np.stack([
            np.asarray(raw['terrain'])[cells] == 2, np.asarray(raw['infrastructure'])[cells] == 1,
            *[(kinds == 1) & (colors == c) for c in range(3)],
            *[(kinds == 2) & (colors == c) for c in range(3)],
            *[(links & (1 << d)) != 0 for d in range(8)],
            *[np.zeros_like(kinds) for _ in range(8)],
        ], dtype=np.float32)
        shops = []
        for shop in sorted((b for b in raw['buildings'] if not b['isHouse']), key=lambda b: b['color']):
            x, y = w.local(tile(shop['entrance']))
            pins = shop['demand']/max(1, shop['demandCapacity'])
            grid[16, y, x] = pins
            grid[17, y, x] = shop['warningVisible']
            grid[18, y, x] = 1
            # The visible pin fill and warning are the demand inputs.
            shops.append((x, y, pins, float(shop['warningVisible']), shop['color']/2.))
        for car in visible_traffic(raw):
            x, y = w.local((round(car['x']), round(car['y'])))
            if not inside((x, y)):
                continue
            grid[19, y, x] += .25
            grid[20, y, x] += .25 * float(car['speed'] < .22)
            grid[21, y, x] += .25 * np.clip(car['speed']/2, 0, 1)
            grid[22, y, x] += .25 * np.sign(car['headingX'])
        grid[22] = (grid[22]+4)/4
        grid[23] = self.previous_movement
        clock = np.array([raw['time']/100, raw['inventory'][0]/2,
                          (raw['tripsCompleted']-self.initial_trips)/30,
                          len(visible_traffic(raw))/12], dtype=np.float32)
        obs = dict(grid=grid, shops=np.asarray(shops, dtype=np.float32), clock=clock)
        if self.use_roots:
            obs['roots'] = np.stack([rooted_tiles(links, (x, y)) for x, y, *_ in shops])
        return obs

    def action_masks(self):
        return self.env.legal.copy()

    def step(self, action):
        action = int(action)
        w = self.env
        before = w.raw['time']
        previous = self.cached['grid'][19]
        ticks = min(self.wait_ticks, max(1, round((self.horizon-before)*20)))
        outcome = native_build_or_wait(w, action, ticks)
        self.actions.append(action)
        if action:
            if self.first_build_time is None:
                self.first_build_time = before
        else:
            self.previous_movement = previous
            slow = sum(v['speed'] < .22 for v in visible_traffic(w.raw))
            self.queue_sum += slow
            self.queue_peak = max(self.queue_peak, slow)
            self.queue_samples += 1
        ended = bool(outcome['terminated'] or w.raw['time'] >= self.horizon - 1e-6 or len(self.actions) == 32)
        if not ended:
            w.mask()
        trips = w.raw['tripsCompleted']-self.initial_trips
        served = {k: v-self.initial_served[k] for k, v in self.served().items()}
        self.cached = self.observation()
        return self.cached, float(outcome['tripsDelta']), ended, False, dict(
            stage=w.stage, seed=w.seed, trips=trips, served=served, spent=w.inventory-w.raw['inventory'][0],
            seconds=w.raw['time'], stopped_cars_mean=self.queue_sum/max(1,self.queue_samples),
            stopped_cars_peak=self.queue_peak, native_waiting=w.raw['meanWaiting'],
            native_failure=outcome['terminated'], actions=self.actions.copy(),
            first_build_time=self.first_build_time, started_at=self.started_at)

    def close(self):
        self.env.close()

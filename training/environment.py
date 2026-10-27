"""Visible structured observations and bounded selections for all gameplay tools."""
from __future__ import annotations

import json
from pathlib import Path
import queue
import subprocess
import threading

import gymnasium as gym
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAPS = ['LosAngeles', 'Beijing', 'Tokyo', 'DarEsSalaam', 'London']
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
CELLS, CHANNELS, GLOBALS = 1500, 50, 42
TOOLS = ['wait', 'draw', 'Road', 'Bridge', 'TrafficLight', 'Roundabout',
         'Remove', 'driveway', 'motorway', 'editMotorway', 'removeMotorway',
         'upgrade0', 'upgrade1']
SCHEMA = 'full-tools-staged-grid-v1'


class Host:
    def __init__(self, dotnet):
        dll = ROOT / 'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'
        self.process = subprocess.Popen([dotnet, str(dll)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.messages = queue.Queue()
        self.errors = []
        def read():
            for line in self.process.stdout:
                self.messages.put(line)
            self.messages.put(None)
        def errors():
            for line in self.process.stderr:
                self.errors.append(line)
                self.errors[:] = self.errors[-20:]
        threading.Thread(target=read, daemon=True).start()
        threading.Thread(target=errors, daemon=True).start()

    def call(self, **request):
        try:
            self.process.stdin.write(json.dumps(request) + '\n')
            self.process.stdin.flush()
            line = self.messages.get(timeout=30)
            if line is None:
                raise RuntimeError('Host exited: ' + ''.join(self.errors))
            result = json.loads(line)
            if 'error' in result:
                raise RuntimeError(result['error'])
            if result['truncated']:
                raise RuntimeError('Simulator rejected scenario; integration cannot score this as a loss')
            return result
        except (queue.Empty, BrokenPipeError, OSError) as error:
            raise RuntimeError('Simulator communication failed: ' + ''.join(self.errors)) from error

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.write('{"command":"quit"}\n')
                self.process.stdin.flush()
                self.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


def cell(value):
    return value['x'], value['y']


class TrafficEnv(gym.Env):
    """Choose tool, then up to three cells; completed commands advance 20 ticks.

    No routing helpers or diagnostic commands. Intermediate selections have no
    reward/time effect and form an acyclic sequence of at most four decisions.
    Conservative masks remove obvious invalid choices; the host remains the
    authority and rejected commands still advance time.
    """
    metadata = {'render_modes': []}

    def __init__(self, dotnet='dotnet', city='LosAngeles', seconds=3600,
                 seeds=range(1000, 1100), episodes_per_seed=100,
                 seed_schedule='blocks', record_replays=False):
        super().__init__()
        if city not in MAPS or seconds < 1 or not tuple(seeds):
            raise ValueError('Unknown city, empty seeds or nonpositive duration')
        self.host = Host(dotnet)
        self.city, self.seconds, self.seeds = city, seconds, tuple(seeds)
        if episodes_per_seed < 1 or seed_schedule not in ('blocks', 'random'):
            raise ValueError('Invalid seed schedule')
        self.episodes_per_seed, self.seed_schedule = episodes_per_seed, seed_schedule
        self.record_replays, self.episodes_started = record_replays, 0
        self.action_space = gym.spaces.Discrete(CELLS + len(TOOLS))
        self.observation_space = gym.spaces.Dict({
            'grid': gym.spaces.Box(0, 1, (CHANNELS, 30, 50), np.float32),
            'global': gym.spaces.Box(0, 1, (GLOBALS,), np.float32),
        })
        self.done = True

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.episodes_started = 0
        self.scenario_seed = (options or {}).get('scenario_seed')
        if self.scenario_seed is None:
            if self.seed_schedule == 'blocks':
                self.scenario_seed = self.seeds[(self.episodes_started // self.episodes_per_seed) % len(self.seeds)]
            else:
                self.scenario_seed = int(self.np_random.choice(self.seeds))
            self.seed_attempt = self.episodes_started % self.episodes_per_seed + 1
            self.seed_cycle = self.episodes_started // (self.episodes_per_seed * len(self.seeds)) + 1
            self.episodes_started += 1
        else:
            self.seed_attempt, self.seed_cycle = 1, 1
        result = self.host.call(command='reset', version='OriginalReference',
                                scenario=self.city, seed=self.scenario_seed)
        self.raw = result['observation']
        if result['terminated'] or self.raw['version'] != 'OriginalReference' or self.raw['unlimitedConstruction']:
            raise RuntimeError('Unexpected reset or rules')
        self.done, self.rejected, self.commands = False, 0, 0
        self.episode_actions, self.action_counts = [], {}
        self.wait_sum, self.wait_samples, self.max_wait = 0.0, 0, 0.0
        self.phase, self.tool, self.first, self.old = 0, 0, None, None
        self._refresh()
        return self.encode(), self.info()

    def _refresh(self):
        o = self.raw
        if o['width'] != 50 or o['height'] != 30:
            raise RuntimeError('Grid schema changed')
        x, y = np.meshgrid(np.arange(50), np.arange(30))
        self.visible = ((x >= o['playableXMin']) & (x < o['playableXMax']) &
                        (y >= o['playableYMin']) & (y < o['playableYMax'])).ravel()
        self.arrays = {name: np.asarray(o[name]) for name in
                       ['terrain', 'infrastructure', 'buildingKinds', 'buildingColors',
                        'connections', 'pendingRemovals', 'demand', 'reservations']}
        if any(a.shape != (CELLS,) for a in self.arrays.values()):
            raise RuntimeError('Unexpected grid shape')
        self.houses, self.accesses, self.parcels = {}, {}, {}
        self.roundabouts, self.endpoints, self.active_motorways = set(), set(), {}
        self.buildings = []
        for b in o['buildings']:
            p = cell(b['cell'])
            if not self.is_visible(p):
                continue
            if not 0 <= b['color'] < 8:
                raise RuntimeError('Color vocabulary overflow; encoder must be revised')
            self.buildings.append(b)
            for dy in range(b['height']):
                for dx in range(b['width']):
                    self.parcels[(p[0]+dx, p[1]+dy)] = b
            if b['isHouse']:
                self.houses[p] = b
                self.accesses[p] = b['drivewayDirection']
            else:
                for a, d in zip(b['entrances'] or [b['entrance']],
                                b['entranceDirections'] or [b['drivewayDirection']]):
                    self.accesses[cell(a)] = d
        for r in o['roundabouts']:
            c = cell(r['center'])
            self.roundabouts.update([c] + [(c[0]+dx, c[1]+dy) for dx, dy in DIRS[::2]])
        for m in o['motorways']:
            for p in (cell(m['start']), cell(m['end'])):
                self.endpoints.add(p)
                if not m['pendingRemoval']:
                    self.active_motorways[p] = m
        a = self.arrays
        self.land = (self.visible & (a['terrain'] == 0) & (a['buildingKinds'] == 0) &
                     (a['pendingRemovals'] == 0))
        self._legal = self._legal_cells()

    def is_visible(self, p):
        return 0 <= p[0] < 50 and 0 <= p[1] < 30 and bool(self.visible[p[1]*50+p[0]])

    @staticmethod
    def index(p):
        return p[1]*50+p[0]

    def _legal_cells(self):
        a, inv = self.arrays, self.raw['inventory']
        empty = self.visible & (a['terrain'] != 2) & (a['buildingKinds'] == 0) & (a['pendingRemovals'] == 0)
        for p in self.roundabouts:
            if self.is_visible(p):
                empty[self.index(p)] = False
        road = empty & (a['terrain'] == 0) & (a['infrastructure'] == 0) & (inv[0] > 0)
        bridge = empty & (a['terrain'] == 1) & (a['infrastructure'] == 0) & (inv[0] > 0)
        if inv[1] <= 0:
            existing = (a['infrastructure'] == 2).reshape(30, 50)
            adjacent = np.zeros((30, 50), bool)
            adjacent[1:] |= existing[:-1]
            adjacent[:-1] |= existing[1:]
            adjacent[:, 1:] |= existing[:, :-1]
            adjacent[:, :-1] |= existing[:, 1:]
            bridge &= adjacent.ravel()
        light = empty & (a['infrastructure'] == 1) & (inv[3] > 0)
        motorway = self.land & (a['infrastructure'] != 4)
        for p in self.endpoints | self.roundabouts:
            if self.is_visible(p):
                light[self.index(p)] = False
                motorway[self.index(p)] = False
        roundabout = np.zeros(CELLS, bool)
        if inv[4] > 0:
            clear = self.land & (a['infrastructure'] != 4)
            for p in self.endpoints | self.roundabouts:
                if self.is_visible(p):
                    clear[self.index(p)] = False
            for k in np.flatnonzero(clear):
                p = (int(k % 50), int(k // 50))
                ring = [(p[0]+dx, p[1]+dy) for dx, dy in DIRS[::2]]
                if all(self.is_visible(q) and clear[self.index(q)] for q in ring):
                    roundabout[k] = True
        remove = self.visible & (a['infrastructure'] != 0) & (a['buildingKinds'] == 0) & (a['pendingRemovals'] == 0)
        for p in self.active_motorways:
            if self.is_visible(p):
                remove[self.index(p)] = True
        driveway = np.zeros(CELLS, bool)
        for p in self.houses:
            driveway[self.index(p)] = any(self.is_visible((p[0]+dx, p[1]+dy)) and
                                         self.land[self.index((p[0]+dx, p[1]+dy))] and
                                         (p[0]+dx, p[1]+dy) not in self.roundabouts for dx, dy in DIRS)
        select_motorway = np.zeros(CELLS, bool)
        for p in self.active_motorways:
            if self.is_visible(p):
                select_motorway[self.index(p)] = True
        # Draw may build and connect a multi-tile stroke, including bridges.
        draw = empty & ((a['infrastructure'] != 0) | road | bridge)
        for p in self.accesses:
            if self.is_visible(p):
                draw[self.index(p)] = True
        return {1: draw, 2: road, 3: bridge, 4: light, 5: roundabout, 6: remove,
                7: driveway, 8: motorway, 9: select_motorway, 10: select_motorway,
                'motorway': motorway}

    def action_masks(self):
        mask = np.zeros(self.action_space.n, bool)
        if self.phase == 0:
            mask[CELLS] = True
            for tool in range(1, 11):
                available = bool(self._legal[tool].any())
                if tool == 8:
                    available &= self.raw['inventory'][2] > 0 and self._legal[tool].sum() >= 2
                mask[CELLS+tool] = available
            if len(self.raw['upgradeChoices']) > 2:
                raise RuntimeError('Upgrade offer overflow')
            for i in range(len(self.raw['upgradeChoices'])):
                mask[CELLS+11+i] = True
        elif self.phase == 1:
            mask[:CELLS] = self._legal[self.tool]
        elif self.tool == 7:
            for dx, dy in DIRS:
                p = self.first[0]+dx, self.first[1]+dy
                if self.is_visible(p) and self.land[self.index(p)] and p not in self.roundabouts:
                    mask[self.index(p)] = True
        elif self.tool in (8, 9):
            mask[:CELLS] = self._legal['motorway']
            # An edit is allowed to reuse its own endpoints, including its start.
            if self.tool == 9:
                m = self.active_motorways[self.old]
                for p in (cell(m['start']), cell(m['end'])):
                    if self.is_visible(p):
                        mask[self.index(p)] = True
            if self.phase != 2 or self.tool == 8:
                x, y = np.meshgrid(np.arange(50), np.arange(30))
                mask[:CELLS] &= ((x-self.first[0])**2+(y-self.first[1])**2 >= 4).ravel()
        else:
            mask[:CELLS] = self._legal[1]
            mask[self.index(self.first)] = False
        # No viable continuation completes a wait, rather than freezing time.
        if not mask.any():
            mask[CELLS] = True
        return mask

    def encode(self):
        o, a = self.raw, self.arrays
        grid = np.zeros((CHANNELS, CELLS), np.float32)
        grid[0] = self.visible
        for i in range(3):
            grid[1+i] = a['terrain'] == i
        for i in range(5):
            grid[4+i] = a['infrastructure'] == i
        for i in range(3):
            grid[9+i] = a['buildingKinds'] == i
        for i in range(8):
            grid[12+i] = a['buildingColors'] == i
            grid[20+i] = (a['connections'] & (1 << i)) != 0
        grid[28] = a['pendingRemovals']
        grid[29] = a['demand'] / 20
        grid[30] = a['reservations'] / 20
        for b in self.buildings:
            for p in self.parcels:
                if self.parcels[p]['id'] == b['id'] and self.is_visible(p):
                    grid[31, self.index(p)] = b['overcrowdedFor'] / 50
        for p, direction in self.accesses.items():
            if self.is_visible(p):
                grid[32+direction, self.index(p)] = 1
        for v in o['vehicles']:
            p = int(v['x']), int(v['y'])
            if self.is_visible(p):
                k = self.index(p)
                grid[40, k] += .1
                grid[41, k] = max(grid[41, k], v['speed']/2)
                grid[42, k] = max(grid[42, k], v['waiting']/60)
        for m in o['motorways']:
            for p, q in [(cell(m['start']), cell(m['end'])), (cell(m['end']), cell(m['start']))]:
                if self.is_visible(p):
                    k = self.index(p)
                    grid[43, k] = 1
                    grid[44, k] = m['pendingRemoval']
                    grid[45, k], grid[46, k] = q[0]/50, q[1]/30
                    grid[47, k] = m['number']/20
        for channel, p in [(48, self.first), (49, self.old)]:
            if p is not None:
                grid[channel, self.index(p)] = 1
        grid[:, ~self.visible] = 0
        global_state = np.zeros(GLOBALS, np.float32)
        global_state[:6] = np.asarray(o['inventory']) / np.array([100, 10, 10, 10, 10, 10])
        global_state[6:9] = [o['time']/self.seconds, o['week']/100, o['tripsCompleted']/1000]
        for i, offer in enumerate(o['upgradeChoices']):
            if i >= 2 or not 0 <= offer['type'] < 6:
                raise RuntimeError('Upgrade schema overflow')
            global_state[9+i*8+offer['type']] = 1
            global_state[15+i*8:17+i*8] = [offer['amount']/100, offer['roads']/100]
        global_state[25+self.phase] = 1
        global_state[29+self.tool] = 1
        obs = {'grid': np.clip(grid.reshape(CHANNELS, 30, 50), 0, 1),
               'global': np.clip(global_state, 0, 1)}
        if not all(np.isfinite(x).all() for x in obs.values()):
            raise RuntimeError('Nonfinite policy observation')
        return obs

    def info(self):
        return dict(trips=self.raw['tripsCompleted'], seconds=self.raw['time'],
                    rejected_actions=self.rejected, commands=self.commands,
                    scenario_seed=self.scenario_seed, city=self.city,
                    seed_attempt=self.seed_attempt, seed_cycle=self.seed_cycle,
                    mean_car_wait=self.wait_sum / max(1, self.wait_samples),
                    max_car_wait=self.max_wait, action_counts=dict(self.action_counts))

    def export_replay(self):
        if not self.record_replays or not self.episode_actions:
            return None
        return dict(schemaVersion=1, version='OriginalReference', scenario=self.city,
                    seed=self.scenario_seed, variation='SameMap', score=self.raw['tripsCompleted'],
                    duration=self.raw['time'], terminated=bool(self.raw['failed']),
                    truncated=not bool(self.raw['failed']), partial=not self.done,
                    actions=self.episode_actions)

    def _advance(self, request=None):
        accepted = True
        if request is not None:
            result = self.host.call(**request)
            accepted = bool(result['accepted'])
            self.rejected += int(not accepted)
        before = self.raw['tripsCompleted']
        result = self.host.call(command='step', ticks=20)
        self.raw = result['observation']
        self.commands += 1
        family = 'wait' if request is None else request.get('tool', request['command'])
        self.action_counts[family] = self.action_counts.get(family, 0) + 1
        waits = [v['waiting'] for v in self.raw['vehicles']]
        self.wait_sum += sum(waits)
        self.wait_samples += len(waits)
        self.max_wait = max([self.max_wait] + waits)
        if self.record_replays:
            event = dict(request or {'command': 'wait'})
            event.update(ticks=20, accepted=accepted, afterTrips=self.raw['tripsCompleted'],
                         afterTime=self.raw['time'])
            self.episode_actions.append(event)
        terminated = bool(result['terminated'])
        truncated = not terminated and self.raw['time'] >= self.seconds-1e-6
        self.done = terminated or truncated
        self.phase, self.tool, self.first, self.old = 0, 0, None, None
        self._refresh()
        info = self.info()
        info.update(command_completed=True, accepted=accepted, request=request)
        if self.done and self.record_replays:
            info['episode_replay'] = self.export_replay()
        return self.encode(), float(self.raw['tripsCompleted']-before), terminated, truncated, info

    def step(self, action):
        if self.done:
            raise RuntimeError('Reset required after episode end')
        action = int(action)
        if not 0 <= action < self.action_space.n or not self.action_masks()[action]:
            self.rejected += 1
            return self._advance()
        if action == CELLS:
            return self._advance()
        if self.phase == 0:
            self.tool = action-CELLS
            if self.tool >= 11:
                return self._advance(dict(command='upgrade', choice=self.tool-11))
            self.phase = 1
        else:
            p = action % 50, action // 50
            if self.phase == 1:
                if 2 <= self.tool <= 6:
                    return self._advance(dict(command='build', tool=TOOLS[self.tool], x=p[0], y=p[1]))
                if self.tool == 10:
                    return self._advance(dict(command='removeMotorway', id=self.active_motorways[p]['id']))
                if self.tool == 9:
                    self.old = p
                else:
                    self.first = p
                self.phase = 2
            elif self.tool == 9 and self.phase == 2:
                self.first, self.phase = p, 3
            else:
                request = dict(command=TOOLS[self.tool], x=self.first[0], y=self.first[1], toX=p[0], toY=p[1])
                if self.tool == 7:
                    request['id'] = self.houses[self.first]['id']
                elif self.tool == 9:
                    request['id'] = self.active_motorways[self.old]['id']
                return self._advance(request)
        info = self.info()
        info['command_completed'] = False
        return self.encode(), 0.0, False, False, info

    def close(self):
        self.host.close()

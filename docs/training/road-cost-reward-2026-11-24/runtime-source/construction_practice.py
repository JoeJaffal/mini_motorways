"""Native, bounded construction exercises. Reference edits are requested only by the teacher."""
from hashlib import sha256

import numpy as np

from connection_practice import ARENA_SIZE, SINGLE_BUILD_STAGE, ConnectionPractice
from environment import CELLS, DIRS, Host
from practice_replay import identity
from practice_reward import connection_potential
from visible_observation import WIDTH, HEIGHT, VisibleObservation

EXERCISES = ('adjacent', 'bend', 'driveway', 'clear', 'obstacle')
FINISH = 0
EDGE_END = 1 + ARENA_SIZE ** 2 * 4
ACTIONS = EDGE_END + 8
INPUT_CHANNELS = 27


def tile(point):
    return point['x'], point['y']


def advance(point, direction):
    return point[0] + DIRS[direction][0], point[1] + DIRS[direction][1]


def endpoints(action):
    cell, d = divmod(action - 1, 4)
    x, y = cell % ARENA_SIZE, cell // ARENA_SIZE
    return (x, y), advance((x, y), d)


def edge_id(start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    d = DIRS.index((dx, dy))
    if d >= 4:
        start, d = end, (d + 4) % 8
    return 1 + (start[1] * ARENA_SIZE + start[0]) * 4 + d


def inside(point):
    return all(0 <= p < ARENA_SIZE for p in point)


def turn(point, count):
    x, y = point
    for _ in range(count):
        x, y = y, ARENA_SIZE - 1 - x
    return x, y


def action_maps():
    maps = []
    for count in range(4):
        result = np.full(ACTIONS, -1, dtype=np.int32)
        result[FINISH] = FINISH
        for action in range(1, EDGE_END):
            a, b = endpoints(action)
            if inside(b):
                result[action] = edge_id(turn(a, count), turn(b, count))
        for d in range(8):
            result[EDGE_END + d] = EDGE_END + (d - 2*count) % 8
        maps.append(result)
    return maps


NATIVE_TO_ALIGNED = action_maps()


class ConstructionPractice:
    def __init__(self, dll):
        self.host = Host('dotnet', dll)
        self.visible_encoder = VisibleObservation()
        try:
            hello = self.host.call(command='hello')
            if 'construction-curriculum-v1' not in hello['capabilities']:
                raise RuntimeError('The curriculum needs its own Release host')
        except BaseException:
            self.close()
            raise

    def close(self):
        self.host.close()

    def call(self, **request):
        result = self.host.call(**request)
        self.raw = result['observation']
        return result

    def reset(self, stage, split, seed):
        self.stage, self.seed = stage, seed
        self.edits = 0
        self.visible_encoder.reset()
        result = self.call(command='reset', version='OriginalReference', practice=True,
                           practiceStage='curriculum-' + stage, practiceSplit=split, seed=seed)
        if not result['accepted'] or result['terminated'] or self.raw['time'] != 0:
            raise RuntimeError('Unexpected native reset')
        self.house, = (b for b in self.raw['buildings'] if b['isHouse'])
        self.shop, = (b for b in self.raw['buildings'] if not b['isHouse'])
        assets = [tile(self.house['cell'])]
        x, y = tile(self.shop['cell'])
        assets.extend((x+dx, y+dy) for dx in range(self.shop['width']) for dy in range(self.shop['height']))
        assets.extend((i % WIDTH, i // WIDTH) for i, (road, terrain) in
                      enumerate(zip(self.raw['infrastructure'], self.raw['terrain'])) if road or terrain)
        xs, ys = zip(*assets)
        if max(xs)-min(xs) >= ARENA_SIZE or max(ys)-min(ys) >= ARENA_SIZE:
            raise RuntimeError('Layout does not fit the practice arena')
        self.x0 = max(0, min(WIDTH-ARENA_SIZE, (min(xs)+max(xs)-ARENA_SIZE+1)//2))
        self.y0 = max(0, min(HEIGHT-ARENA_SIZE, (min(ys)+max(ys)-ARENA_SIZE+1)//2))
        y, x = np.mgrid[:ARENA_SIZE, :ARENA_SIZE]
        self.cells = (y+self.y0)*WIDTH + x+self.x0
        self.area = np.zeros(CELLS, dtype=bool)
        self.area[self.cells] = True
        self.turns = self.shop['drivewayDirection']//2
        self.to_aligned = NATIVE_TO_ALIGNED[self.turns]
        self.from_aligned = np.full(ACTIONS, -1, dtype=np.int32)
        valid = np.flatnonzero(self.to_aligned >= 0)
        self.from_aligned[self.to_aligned[valid]] = valid
        self.mask()
        self.edit_limit = self.native_mask['editLimit']
        self.inventory = self.raw['inventory'][0]
        if stage != 'driveway' and self.connected():
            raise RuntimeError('Construction exercise unexpectedly starts connected')

    def local(self, point):
        return point[0]-self.x0, point[1]-self.y0

    def world(self, point):
        return point[0]+self.x0, point[1]+self.y0

    def mask(self):
        result = self.host.call(command='curriculumMask')
        self.native_mask = result
        result_mask = np.zeros(ACTIONS, dtype=bool)
        if self.stage == 'driveway':
            result_mask[FINISH] = True
            result_mask[EDGE_END:] = result['rotations']
        else:
            native = np.asarray(result['connections'], dtype=bool).reshape(CELLS, 4)
            result_mask[1:EDGE_END] = native[self.cells.ravel()].ravel()
            result_mask[self.to_aligned < 0] = False
        self.legal = result_mask
        return result_mask

    def aligned_mask(self):
        result = np.zeros(ACTIONS, dtype=bool)
        result[self.to_aligned[self.legal]] = True
        return result

    def connected(self):
        return bool(connection_potential(self.raw, self.area))

    def full_observation(self):
        bounds = dict(playableXMin=self.x0, playableXMax=self.x0+ARENA_SIZE,
                      playableYMin=self.y0, playableYMax=self.y0+ARENA_SIZE)
        observation = self.visible_encoder.encode(dict(self.raw, **bounds), horizon=180)
        observation['focus'] = np.zeros((2, HEIGHT, WIDTH), dtype=np.float32)
        observation['context'] = np.array([0, 0, 1, 1, 0, 0, 0, 0], dtype=np.float32)
        return observation

    def observation(self):
        """Use only visible topology, parcel positions, inventory and exercise identity."""
        road = np.asarray(self.raw['infrastructure'])[self.cells] == 1
        blocked = np.asarray(self.raw['terrain'])[self.cells] == 2
        parcels = np.asarray(self.raw['buildingKinds'])[self.cells]
        links = np.asarray(self.raw['connections'])[self.cells]
        planes = [road, blocked, parcels == 1, parcels == 2]
        home, = (b for b in self.raw['buildings'] if b['isHouse'])
        house = tile(home['cell'])
        access = tile(self.shop['entrance'])
        starts = (self.local(advance(house, home['drivewayDirection'])),
                  self.local(advance(access, self.shop['drivewayDirection'])))
        for x, y in starts:
            plane = np.zeros_like(road)
            if inside((x, y)):
                plane[y,x] = True
            planes.append(plane)
        rotated = np.rot90(np.asarray(planes), self.turns, axes=(1, 2))
        links = np.rot90(np.stack([(links & (1 << d)) != 0 for d in range(8)]),
                         self.turns, axes=(1, 2))
        links = np.roll(links, -2*self.turns, axis=0)
        y, x = np.mgrid[:ARENA_SIZE, :ARENA_SIZE]
        geometry = []
        for start in starts:
            tx, ty = turn(start, self.turns)
            geometry.extend(((x-tx)/ARENA_SIZE, (y-ty)/ARENA_SIZE))
        geometry.extend(((x-(ARENA_SIZE-1)/2)/ARENA_SIZE, (y-(ARENA_SIZE-1)/2)/ARENA_SIZE))
        global_planes = np.broadcast_to(np.array([
            *[self.stage == stage for stage in EXERCISES], self.raw['inventory'][0]/8,
            (self.edit_limit-self.edits)/8,
        ], dtype=np.float32)[:, None, None], (7, ARENA_SIZE, ARENA_SIZE))
        return np.concatenate((rotated, links, geometry, global_planes)).astype(np.float32)

    def reference(self):
        rows = self.host.call(command='curriculumReference')['edits']
        result = []
        for r in rows:
            a, b = (r['x'], r['y']), (r['toX'], r['toY'])
            if r['kind'] == 'finish':
                result.append(FINISH)
            elif r['kind'] == 'rotate':
                result.append(EDGE_END + DIRS.index((b[0]-a[0], b[1]-a[1])))
            else:
                result.append(edge_id(self.local(a), self.local(b)))
        return result

    def step(self, action):
        if self.edits >= self.edit_limit or not self.legal[action]:
            raise ValueError(f'Action {action} is outside the native curriculum mask')
        self.edits += 1
        if action == FINISH:
            return True
        if action >= EDGE_END:
            a = tile(self.house['cell'])
            b = advance(a, action-EDGE_END)
            result = self.call(command='driveway', id=self.house['id'], x=a[0], y=a[1], toX=b[0], toY=b[1])
        else:
            a, b = (self.world(p) for p in endpoints(action))
            result = self.call(command='draw', x=a[0], y=a[1], toX=b[0], toY=b[1])
            d = DIRS.index((b[0]-a[0], b[1]-a[1]))
            if not self.raw['connections'][a[1]*WIDTH+a[0]] & (1 << d):
                raise RuntimeError('Native build did not create the selected edge')
        if not result['accepted'] or result['terminated'] or self.raw['time'] != 0:
            raise RuntimeError('Native rejected a masked construction action')
        return self.connected() or self.edits >= self.edit_limit

    def deliveries(self):
        result = self.call(command='step', ticks=3600)
        if result['truncated'] or not (self.raw['failed'] or np.isclose(self.raw['time'], 180.)):
            raise RuntimeError('Expected native game over or the 180-second delivery horizon')
        return self.raw['tripsCompleted'], self.raw['time']


def verified_original_identity(config, dll, archive):
    """Use the preserved one-build source identity when loading the historical baseline."""
    import tarfile

    reference = ConnectionPractice(host_dll=dll, stage=SINGLE_BUILD_STAGE)
    try:
        current = identity(reference)
    finally:
        reference.close()
    saved = config['environment']
    if {k: v for k, v in current.items() if k != 'source_hashes'} != {
            k: v for k, v in saved.items() if k != 'source_hashes'}:
        raise ValueError('Old host protocol or binary differs')
    with tarfile.open(archive) as src:
        for name, expected in saved['source_hashes'].items():
            stream = src.extractfile(name)
            if stream is None or sha256(stream.read()).hexdigest() != expected:
                raise ValueError(f'Old source archive differs for {name}')
    return saved

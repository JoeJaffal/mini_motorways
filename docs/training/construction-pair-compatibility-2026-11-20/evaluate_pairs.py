"""Frozen construction policy on matched and unserviceable native building pairs."""
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import torch

from connection_practice import ARENA_SIZE
from construction_curriculum import load_model
from construction_practice import ConstructionPractice, EXERCISES, FINISH, NATIVE_TO_ALIGNED, advance, inside, tile, turn
from environment import CELLS, DIRS
from hierarchy_rollout import policy_fingerprint
from visible_observation import HEIGHT, WIDTH


CASES = ('match', 'mismatch', 'homes', 'destinations')
MODES = ('default_greedy', 'default_sampled', 'finish_greedy')


class PairEnvironment(ConstructionPractice):
    def reset_case(self, case, seed, finish):
        self.stage, self.seed = 'clear', seed
        self.case, self.finish = case, finish
        self.edits = 0
        result = self.call(command='reset', version='OriginalReference', practice=True,
                           practiceStage='curriculum-pair-' + case, practiceSplit='validation', seed=seed)
        if not result['accepted'] or result['terminated'] or self.raw['time'] != 0:
            raise RuntimeError('Expected a fresh pair fixture')
        self.homes = [b for b in self.raw['buildings'] if b['isHouse']]
        self.destinations = [b for b in self.raw['buildings'] if not b['isHouse']]
        if (len(self.homes), len(self.destinations)) != {
                'match': (1,1), 'mismatch': (1,1), 'homes': (2,0), 'destinations': (0,2)}[case]:
            raise RuntimeError('Wrong parcel types in fixture')
        self.house = self.homes[0] if self.homes else None
        self.shop = self.destinations[0] if self.destinations else None
        self.match = (self.house is not None and self.shop is not None
                      and self.house['color'] == self.shop['color'])
        if self.match != (case == 'match'):
            raise RuntimeError('Wrong building compatibility')
        if case == 'mismatch' and (self.house['color'], self.shop['color']) != (1, 0):
            raise RuntimeError('Expected a blue house and red destination')
        assets = [(b['cell']['x']+dx, b['cell']['y']+dy) for b in self.raw['buildings']
                  for dx in range(b['width']) for dy in range(b['height'])]
        xs, ys = zip(*assets)
        if max(xs)-min(xs) >= ARENA_SIZE or max(ys)-min(ys) >= ARENA_SIZE:
            raise RuntimeError('Pair does not fit in the arena')
        self.x0 = max(0, min(WIDTH-ARENA_SIZE, (min(xs)+max(xs)-ARENA_SIZE+1)//2))
        self.y0 = max(0, min(HEIGHT-ARENA_SIZE, (min(ys)+max(ys)-ARENA_SIZE+1)//2))
        y,x = np.mgrid[:ARENA_SIZE, :ARENA_SIZE]
        self.cells = (y+self.y0)*WIDTH + x+self.x0
        self.area = np.zeros(CELLS, dtype=bool)
        self.area[self.cells] = True
        anchor = self.shop or self.house
        self.turns = anchor['drivewayDirection']//2
        self.to_aligned = NATIVE_TO_ALIGNED[self.turns]
        self.from_aligned = np.full(len(self.to_aligned), -1, dtype=np.int32)
        valid = np.flatnonzero(self.to_aligned >= 0)
        self.from_aligned[self.to_aligned[valid]] = valid
        self.mask()
        self.edit_limit = self.native_mask['editLimit']
        self.inventory = self.raw['inventory'][0]

    def mask(self):
        result = super().mask()
        result[FINISH] = self.finish
        return result

    def connected(self):
        return self.match and super().connected()

    def observation(self):
        if self.house is not None and self.shop is not None:
            return super().observation()
        # The training encoder requires one parcel of each type. Keep every
        # actual tile plane and use zero approach/geometry planes for the absent role.
        road = np.asarray(self.raw['infrastructure'])[self.cells] == 1
        blocked = np.asarray(self.raw['terrain'])[self.cells] == 2
        parcels = np.asarray(self.raw['buildingKinds'])[self.cells]
        links = np.asarray(self.raw['connections'])[self.cells]
        basics = [road, blocked, parcels == 1, parcels == 2]
        starts = []
        for b in (self.house, self.shop):
            if b is None:
                starts.append(None)
            else:
                point = tile(b['cell'] if b['isHouse'] else b['entrance'])
                starts.append(self.local(advance(point, b['drivewayDirection'])))
        for start in starts:
            plane = np.zeros_like(road)
            if start is not None and inside(start):
                x, y = start
                plane[y,x] = True
            basics.append(plane)
        rotated = np.rot90(np.asarray(basics), self.turns, axes=(1, 2))
        directional = np.rot90(np.stack([(links & (1 << d)) != 0 for d in range(8)]),
                               self.turns, axes=(1, 2))
        directional = np.roll(directional, -2*self.turns, axis=0)
        y,x = np.mgrid[:ARENA_SIZE, :ARENA_SIZE]
        geometry = []
        for start in starts:
            if start is None:
                geometry.extend((np.zeros_like(x), np.zeros_like(y)))
            else:
                tx, ty = turn(start, self.turns)
                geometry.extend(((x-tx)/ARENA_SIZE, (y-ty)/ARENA_SIZE))
        geometry.extend(((x-(ARENA_SIZE-1)/2)/ARENA_SIZE, (y-(ARENA_SIZE-1)/2)/ARENA_SIZE))
        global_planes = np.broadcast_to(np.array([*[self.stage == s for s in EXERCISES],
            self.raw['inventory'][0]/8, (self.edit_limit-self.edits)/8], dtype=np.float32)[:,None,None],
            (7, ARENA_SIZE, ARENA_SIZE))
        return np.concatenate((rotated, directional, geometry, global_planes)).astype(np.float32)

    def physical_link(self):
        """Measure a road between real access points regardless of role/color."""
        a,b = [tile(v['cell'] if v['isHouse'] else v['entrance']) for v in self.raw['buildings']]
        queue = deque([a])
        seen = {a}
        links = self.raw['connections']
        while queue:
            x,y = queue.popleft()
            if (x,y) == b:
                return True
            for d, (dx,dy) in enumerate(DIRS):
                if links[y*WIDTH+x] & (1 << d):
                    nxt = (x+dx, y+dy)
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
        return False


def evaluate_case(model, envs, pool, case, mode):
    finish = mode == 'finish_greedy'
    records = []
    for offset in range(0, 100, len(envs)):
        size = min(100-offset, len(envs))
        batch = envs[:size]
        seeds = list(range(42000+offset, 42000+offset+size))
        list(pool.map(lambda pair: pair[0].reset_case(case, pair[1], finish), zip(batch,seeds)))
        initial = [dict(seed=seed, observation_sha256=sha256(env.observation().tobytes()).hexdigest(),
                        mask_sha256=sha256(env.aligned_mask().tobytes()).hexdigest(), actions=[])
                   for env, seed in zip(batch, seeds)]
        rng = [torch.Generator().manual_seed(100000+seed) for seed in seeds]
        active = list(range(size))
        while active:
            active = [i for i in active if batch[i].legal.any()]
            if not active:
                break
            inputs = torch.as_tensor(np.stack([batch[i].observation() for i in active]))
            legal = torch.as_tensor(np.stack([batch[i].aligned_mask() for i in active]))
            with torch.inference_mode():
                logits = model(inputs).masked_fill(~legal, -torch.inf)
                if mode == 'default_sampled':
                    actions = [int(torch.multinomial(row.softmax(0), 1, generator=rng[i]).item())
                               for i, row in zip(active, logits)]
                else:
                    actions = logits.argmax(dim=1).tolist()
            choices = [(batch[i], int(batch[i].from_aligned[action])) for i, action in zip(active, actions)]
            for i,(_, action) in zip(active, choices):
                initial[i]['actions'].append(action)
            done = list(pool.map(lambda choice: choice[0].step(choice[1]), choices))
            active = [i for i, ended in zip(active, done) if not ended]
            list(pool.map(lambda i: batch[i].mask(), active))
        for env, row in zip(batch, initial):
            row.update(physical_link=env.physical_link(), service_link=env.connected(),
                       stock_used=env.inventory-env.raw['inventory'][0],
                       abstained=not any(a != FINISH for a in row['actions']))
        deliveries = list(pool.map(lambda env: env.deliveries(), batch))
        for row, (trips, seconds) in zip(initial, deliveries):
            row.update(trips=trips, seconds=seconds)
        records.extend(initial)
    return records


def main(args):
    torch.set_num_threads(2)
    model = load_model(args.checkpoint, args.native_host, torch.device('cpu'))
    before = policy_fingerprint(model)
    envs = []
    try:
        for _ in range(args.workers):
            envs.append(PairEnvironment(args.fixture_host))
        rows = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for case in CASES:
                rows[case] = {mode: evaluate_case(model, envs, pool, case, mode) for mode in MODES}
                print('Completed', case, flush=True)
    finally:
        for env in envs:
            env.close()
    if policy_fingerprint(model) != before:
        raise RuntimeError('Frozen evaluation changed weights')
    for mode in MODES:
        for a,b in zip(rows['match'][mode], rows['mismatch'][mode]):
            if (a['seed'],a['observation_sha256'],a['mask_sha256']) != (
                    b['seed'],b['observation_sha256'],b['mask_sha256']):
                raise RuntimeError('Color-only fixture pair did not preserve actor inputs')
    return dict(policy_sha256=before, fixture_host_sha256=sha256(Path(args.fixture_host).read_bytes()).hexdigest(),
                source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), changed_weights=False, cases=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--native-host', required=True)
    parser.add_argument('--fixture-host', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--workers', type=int, default=10)
    args = parser.parse_args()
    if args.workers < 1 or Path(args.output).exists():
        parser.error('Use a positive worker count and a fresh output path')
    results = main(args)
    with Path(args.output).open('x') as out:
        json.dump(results, out, separators=(',', ':'))
        out.write('\n')

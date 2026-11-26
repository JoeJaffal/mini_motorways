"""Model-independent KDD graph evaluation. Standard-library only; no training/SUMO."""
import argparse
import hashlib
import heapq
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

class Episode:
    def __init__(self, scenario):
        self.scenario = scenario
        self.nodes = {n['id']: n for n in scenario['nodes']}
        self.edges = {e['id']: e for e in scenario['edges']}
        self.places = {p['id']: set(p['nodes']) for p in scenario['places']}
        if len(self.nodes) != len(scenario['nodes']) or len(self.edges) != len(scenario['edges']) or len(self.places) != len(scenario['places']):
            raise ValueError('Duplicate IDs')
        for e in self.edges.values():
            if e['u'] not in self.nodes or e['v'] not in self.nodes or e['u'] == e['v'] or not math.isfinite(e['cost']) or e['cost'] <= 0:
                raise ValueError('Invalid edge')
        if any(not ns or not ns <= self.nodes.keys() for ns in self.places.values()):
            raise ValueError('Invalid place')
        self.initial = {e['id'] for e in self.edges.values() if e['existing']}
        self.roads = self.initial.copy()
        self.actions = []
        self.budget = scenario['protocol']['max_added_segments']
        self.nr = 0 if not self.unserved() else None
        self.trace = []

    def road_nodes(self):
        return {n for eid in self.roads for n in (self.edges[eid]['u'], self.edges[eid]['v'])}

    def unserved(self):
        nodes = self.road_nodes()
        return sorted(p for p, ns in self.places.items() if not nodes & ns)

    def legal_actions(self, enforce_budget=True):
        if enforce_budget and len(self.actions) >= self.budget:
            return []
        rn = self.road_nodes()
        choices = [eid for eid, e in self.edges.items() if eid not in self.roads and not e['barrier'] and {e['u'], e['v']} & rn]
        interior = set().union(*(self.places[p] for p in self.unserved()))
        priority = [eid for eid in choices if {self.edges[eid]['u'], self.edges[eid]['v']} & interior]
        return sorted(priority or choices)

    def step(self, edge_id):
        if edge_id not in self.legal_actions():
            raise ValueError(f'Illegal action {edge_id!r} at step {len(self.actions)+1}; duplicate, disconnected, masked, barrier or over budget')
        self.roads.add(edge_id)
        self.actions.append(edge_id)
        pending = self.unserved()
        if self.nr is None and not pending:
            self.nr = len(self.actions)
        self.trace.append({'step': len(self.actions), 'edge_id': edge_id, 'unserved_places': len(pending), 'SC': self.cost()})
        return self.observe()

    def cost(self):
        return sum(self.edges[e]['cost'] for e in self.actions)

    def observe(self):
        return {'schema_version': 1, 'scenario_id': self.scenario['id'], 'scenario_sha256': digest(self.scenario),
                'road_edge_ids': sorted(self.roads), 'unserved_place_ids': self.unserved(),
                'legal_edge_ids': self.legal_actions(), 'added_segments': len(self.actions),
                'remaining_segments': self.budget-len(self.actions), 'construction_cost': self.cost(),
                'stage': 'done' if len(self.actions) == self.budget else ('connecting' if self.unserved() else 'full_connected')}

    def metrics(self):
        adj = {n: [] for n in self.road_nodes()}
        for eid in self.roads:
            e = self.edges[eid]
            adj[e['u']].append((e['v'], e['cost']))
            adj[e['v']].append((e['u'], e['cost']))
        distances = {}
        for start in adj:
            dist, queue = {start: 0.0}, [(0.0, start)]
            while queue:
                d, n = heapq.heappop(queue)
                if d != dist[n]:
                    continue
                for nxt, w in adj[n]:
                    candidate = d+w
                    if candidate < dist.get(nxt, math.inf):
                        dist[nxt] = candidate
                        heapq.heappush(queue, (candidate, nxt))
            distances[start] = dist
        total, missing, pairs = 0.0, 0, 0
        ids = sorted(self.places)
        for i, a in enumerate(ids):
            for b in ids[i+1:]:
                d = min((distances[u].get(v, math.inf) for u in self.places[a] & adj.keys() for v in self.places[b] & adj.keys()), default=math.inf)
                pairs += 1
                if math.isinf(d):
                    missing += 1
                else:
                    total += d
        return {'NR': self.nr, 'AD': None if missing else total/pairs, 'SC': self.cost(),
                'unreachable_place_pairs': missing, 'unserved_places': len(self.unserved()),
                'added_segments': len(self.actions), 'budget_complete': len(self.actions) == self.budget}


def evaluate(scenario, design):
    if design.get('schema_version') != 1 or design.get('scenario_sha256') != digest(scenario):
        raise ValueError('Design schema or scenario hash mismatch')
    ep = Episode(scenario)
    for action in design['actions']:
        if not isinstance(action, str):
            raise ValueError('Actions must be ordered source edge IDs')
        ep.step(action)
    return {'schema_version': 1, 'scenario_sha256': digest(scenario), 'design_sha256': digest(design),
            'design_label': design['label'], 'metrics': ep.metrics(), 'trace': ep.trace,
            'published_comparison_status': 'released_code_protocol; published_values_are_external_point_estimates',
            'note': 'No GP inference, traffic simulation or KDD learned-model reproduction implied.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ['evaluate', 'observe', 'smoke-design']:
        p = sub.add_parser(command)
        p.add_argument('--scenario', type=Path, default=ROOT/'data/harare.json')
        p.add_argument('--output', type=Path, required=True)
        if command == 'evaluate': p.add_argument('--design', type=Path, required=True)
        if command == 'smoke-design': p.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    scenario = read(args.scenario)
    if args.command == 'evaluate':
        result = evaluate(scenario, read(args.design))
    else:
        ep = Episode(scenario)
        if args.command == 'observe':
            result = ep.observe()
        else:
            rng = random.Random(args.seed)
            while ep.legal_actions(): ep.step(rng.choice(ep.legal_actions()))
            result = {'schema_version': 1, 'scenario_sha256': digest(scenario), 'label': 'random legal engineering fixture; not GP', 'seed': args.seed, 'actions': ep.actions}
    write(args.output, result)

if __name__ == '__main__': main()


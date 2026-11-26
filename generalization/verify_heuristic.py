"""Run the published reblocking heuristic on pinned KDD Harare data.
This is a local heuristic run, not a reproduction of KDD Table 3.
Only load the pinned trusted upstream pickle (hash checked below).
"""
from pathlib import Path
import sys, pickle, random, time, json, hashlib, argparse, platform
ROOT = Path(__file__).resolve().parent
REVISION = '2232a3da3cfa7bbe3f4e5eb48049baac6e67f662'
sys.path.insert(0, str(ROOT / ('upstream/topology-' + REVISION)))
import networkx as nx
import numpy as np
# API-only compatibility with the original NetworkX 1.x implementation.
nx.connected_component_subgraphs = lambda g: (g.subgraph(c).copy() for c in nx.connected_components(g))
nx.Graph.nodes_iter = lambda g: iter(g.nodes())
_neighbors = nx.Graph.neighbors
nx.Graph.neighbors = lambda g, n: list(_neighbors(g, n))
import my_graph as mg
import my_graph_helpers as mgh
parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--output', type=Path, default=ROOT/'results/harare-seed0.json')
args = parser.parse_args()
source = ROOT / 'inputs/Epworth_Demo.mg'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '4145ba0189e9d99d5f973abf3b71ae15aeda4edb33b932683bff225cac5fdbbf'
with source.open('rb') as f:
    original = pickle.load(f)

def edge_key(edge):
    return tuple(sorted((tuple(float(x) for x in n.loc) for n in edge.nodes)))

original_edges = {edge_key(d['myedge']): d for _, _, d in original.G.edges(data=True)}
original_roads = {k for k, d in original_edges.items() if d['myedge'].road}
# Rebuild to discard serialized cached faces; retain exact node positions and weights.
g = mg.MyGraph(name='Harare_KDD')
nodes = {n: mg.MyNode(n.loc) for n in original.G.nodes()}
for u, v, data in original.G.edges(data=True):
    edge = mg.MyEdge((nodes[u], nodes[v]))
    edge.barrier = data['myedge'].barrier
    g.add_edge(edge, weight=data['weight'])
g.define_roads()
assert {edge_key(e) for e in g.road_edges} == original_roads, 'Boundary roads differ from KDD input'
g.define_interior_parcels()
initial_unserved = len(g.interior_parcels)
initial_faces = len(g.inner_facelist)
actions = []
add_segment = g.add_road_segment

def recorded_add(edge):
    assert edge_key(edge) in original_edges
    assert not edge.barrier
    actions.append(edge_key(edge))
    add_segment(edge)

g.add_road_segment = recorded_add
random.seed(args.seed)
np.random.seed(args.seed)
start = time.perf_counter()
length = mgh.build_all_roads(g, wholepath=True)
elapsed = time.perf_counter() - start
final_roads = {edge_key(e) for e in g.myedges() if e.road}
assert original_roads <= final_roads
assert len(g.interior_parcels) == 0
assert {edge_key(e) for e in g.myedges()} == set(original_edges)
added = final_roads - original_roads
road_graph = nx.Graph()
road_graph.add_edges_from(final_roads)
assert nx.is_connected(road_graph)
record = {
    'method': 'Brelsford published probabilistic reblocking; local run',
    'topology_revision': REVISION,
    'kdd_revision': 'a3d86fbb201545415ddc1e09ea997b20089effd1',
    'input_sha256': source_hash,
    'seed': args.seed,
    'parameters': {'alpha': 8, 'wholepath': True, 'strict_greedy': False, 'outsidein': False},
    'stop_rule': 'all parcels have road-node access; no budget cap',
    'nodes': g.G.number_of_nodes(), 'edges': g.G.number_of_edges(),
    'places': initial_faces, 'initial_road_edges': len(original_roads),
    'initial_inaccessible_places': initial_unserved, 'final_inaccessible_places': len(g.interior_parcels),
    'added_road_edges': len(added), 'added_geometric_length_source_units': sum(original_edges[e]['myedge'].length for e in added),
    'added_source_weight_cost': sum(original_edges[e]['weight'] for e in added),
    'algorithm_reported_length': length, 'runtime_seconds': elapsed,
    'checks': {'initial_roads_preserved': True, 'no_new_corridors': True, 'road_network_connected': True, 'all_places_accessible': True},
    'actions': actions, 'initial_roads': sorted(original_roads), 'final_roads': sorted(final_roads),
    'versions': {'python': platform.python_version(), 'networkx': nx.__version__, 'numpy': np.__version__},
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ['actions','initial_roads','final_roads']}, indent=2))

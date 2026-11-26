"""Extract a portable JSON scenario from hash-verified upstream data. No training."""
from pathlib import Path
import sys, pickle, hashlib
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'upstream/topology-2232a3da3cfa7bbe3f4e5eb48049baac6e67f662'))
import my_graph
from experiment import write, digest, Episode, evaluate
source = ROOT.parent/'inputs/Epworth_Demo.mg'
expected = '4145ba0189e9d99d5f973abf3b71ae15aeda4edb33b932683bff225cac5fdbbf'
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
with source.open('rb') as f: graph = pickle.load(f)
nodes = sorted(graph.G.nodes(), key=lambda n: tuple(n.loc))
node_ids = {n: f'n{i:03d}' for i,n in enumerate(nodes)}
source_edges = list(graph.G.edges(data=True))
ordered_edges = sorted(enumerate(source_edges), key=lambda x: tuple(sorted((node_ids[x[1][0]], node_ids[x[1][1]]))))
edges = []
coordinate_edges = {}
for i, (source_index, (u,v,d)) in enumerate(ordered_edges):
    e = d['myedge']
    row = {'id':f'e{i:03d}', 'u':node_ids[u], 'v':node_ids[v], 'cost':float(d['weight']), 'geometric_length':float(e.length), 'existing':bool(e.road), 'barrier':bool(e.barrier), 'source_edge_index':source_index}
    edges.append(row)
    coordinate_edges[tuple(sorted((tuple(u.loc),tuple(v.loc))))] = row['id']
faces = sorted(graph.inner_facelist, key=lambda f: tuple(sorted(node_ids[n] for n in f.nodes)))
places = [{'id':f'p{i:03d}', 'nodes':sorted(node_ids[n] for n in f.nodes), 'centroid':[float(f.centroid.x),float(f.centroid.y)]} for i,f in enumerate(faces)]
count = sum(not e['existing'] for e in edges)
scenario = {'schema_version':1, 'id':'kdd-harare-epworth-v1',
    'provenance':{'input_sha256':expected, 'kdd_revision':'a3d86fbb201545415ddc1e09ea997b20089effd1', 'source':'https://github.com/tsinghua-fib-lab/road-planning-for-slums', 'source_file':'data/Epworth_Demo.mg'},
    'protocol':{'name':'released-code-half-budget-v1', 'max_added_segments':int(count*0.5)+1, 'candidate_segments':count, 'build_ratio':0.5, 'cost_units':'source weights; not assumed meters', 'distance':'minimum weighted road distance between parcel boundary road nodes', 'action_mask':'connected-road endpoint; prioritize endpoints incident to inaccessible places when available', 'paper_equivalence':'unverified; compare anchor before making claims'},
    'nodes':[{'id':node_ids[n], 'xy':[float(n.x),float(n.y)]} for n in nodes], 'edges':edges, 'places':places}
assert len(nodes)==54 and len(edges)==85 and len(places)==32
assert len(Episode(scenario).unserved())==12
write(ROOT/'data/harare.json', scenario)
write(ROOT/'data/published_reference.json', {'source':'https://fi.ee.tsinghua.edu.cn/~dingjingtao/papers/RoadPlan-KDD23.pdf', 'table':3, 'layout':'Harare', 'origin':'published rounded values; not locally reproduced', 'rows':{'DRL-GNN':{'NR':9,'AD':0.50,'SC':4.60}, 'HS-MC':{'NR':13,'AD':0.62,'SC':5.31}, 'Build All Roads':{'NR':None,'AD':0.47,'SC':11.50}}})
from experiment import read
for seed in (0,1):
    result = read(ROOT.parent/f'results/harare-seed{seed}.json')
    actions = [coordinate_edges[tuple(sorted(tuple(p) for p in edge))] for edge in result['actions']]
    design = {'schema_version':1, 'scenario_sha256':digest(scenario), 'label':f'Brelsford heuristic seed {seed}; stops at access; not budget complete', 'actions':actions}
    write(ROOT/f'examples/heuristic-seed{seed}.json',design)
write(ROOT/'examples/initial-observation.json',Episode(scenario).observe())
print('Exported Harare: 54 nodes, 85 edges, 32 places, 65 candidates, 33-step released-code budget')

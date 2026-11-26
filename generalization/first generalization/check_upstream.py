"""Check local evaluator against unmodified KDD MyGraph methods, no training."""
import sys, pickle, hashlib, math, types
from pathlib import Path
ROOT=Path(__file__).resolve().parent
KDD=ROOT.parent.parent/'tmp/kdd-upstream'
sys.path.insert(0,str(KDD))
# Load the graph subpackage without envs/__init__.py importing RoadEnv/geopandas.
# No graph functions are replaced.
import road_planning
pkg=types.ModuleType('road_planning.envs')
pkg.__path__=[str(KDD/'road_planning/envs')]
sys.modules['road_planning.envs']=pkg
from road_planning.envs import my_graph as mg
from experiment import Episode, read, write
class Loader(pickle.Unpickler):
    def find_class(self,module,name):
        if module=='my_graph': return getattr(mg,name)
        return super().find_class(module,name)

def load():
    source=ROOT.parent/'inputs/Epworth_Demo.mg'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='4145ba0189e9d99d5f973abf3b71ae15aeda4edb33b932683bff225cac5fdbbf'
    with source.open('rb') as f: g=Loader(f).load()
    g.define_roads(); g.define_interior_parcels(); g.td_dict_init(); g._cal_node_degree_and_isroad()
    return g

def key(u,v): return tuple(sorted((tuple(u.loc),tuple(v.loc))))
s=read(ROOT/'data/harare.json')
coords={n['id']:n['xy'] for n in s['nodes']}
lookup={e['id']:tuple(sorted((tuple(coords[e['u']]),tuple(coords[e['v']]))) ) for e in s['edges']}
rows=[]
for filename in ['smoke-seed0.json','heuristic-seed0.json']:
    g=load(); ep=Episode(s)
    upstream={key(e.nodes[0],e.nodes[1]):e for e in g.edge_list}
    actions=read(ROOT/'examples'/filename)['actions']
    for action in actions:
        mask=g._get_edge_mask()
        theirs={key(e.nodes[0],e.nodes[1]) for e,m in zip(g.edge_list,mask) if m}
        ours={lookup[eid] for eid in ep.legal_actions()}
        assert theirs==ours, 'Action mask mismatch'
        g.add_road_segment(upstream[lookup[action]]); ep.step(action)
        assert len(g.interior_parcels)==len(ep.unserved())
        assert math.isclose(g.total_cost(),ep.cost(),abs_tol=1e-12)
        if not ep.unserved():
            assert math.isclose(g.face2face_avg(),ep.metrics()['AD'],abs_tol=1e-10), (g.face2face_avg(),ep.metrics())
    assert g.full_connected_road_num==ep.nr
    rows.append({'design':filename,'steps_checked':len(actions),'mask_access_cost_NR_AD_match':True,'metrics':ep.metrics()})
write(ROOT/'results/upstream-parity.json',{'kdd_revision':s['provenance']['kdd_revision'],'checks':rows,'note':'Unmodified graph methods; no training, model weights or RoadEnv save side effects.'})
print('PASS upstream parity',rows)


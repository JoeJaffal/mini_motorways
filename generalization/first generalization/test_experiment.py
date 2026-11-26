"""Numerical and protocol checks; no learned policy required."""
import unittest, copy, random
from pathlib import Path
from experiment import Episode, read, digest, evaluate
from grid_projection import project
ROOT=Path(__file__).resolve().parent

class Checks(unittest.TestCase):
    def setUp(self): self.s=read(ROOT/'data/harare.json')
    def test_initial(self):
        e=Episode(self.s)
        self.assertEqual(len(e.unserved()),12)
        self.assertEqual(e.budget,33)
        self.assertEqual(e.metrics()['unreachable_place_pairs'],306)
        self.assertIsNone(e.metrics()['AD'])
    def test_all_roads_anchor(self):
        e=Episode(self.s); e.roads=set(e.edges); e.actions=sorted(e.roads-e.initial)
        m=e.metrics()
        self.assertAlmostEqual(m['AD'],0.47,delta=0.005)
        self.assertAlmostEqual(m['SC'],11.50,delta=0.005)
    def test_repeatability_and_budget(self):
        designs=[]
        for _ in range(2):
            e=Episode(self.s); rng=random.Random(0)
            while e.legal_actions(): e.step(rng.choice(e.legal_actions()))
            self.assertEqual(len(e.actions),33)
            self.assertTrue(e.metrics()['budget_complete'])
            with self.assertRaises(ValueError): e.step(next(iter(e.edges)))
            designs.append(e.actions)
        self.assertEqual(*designs)
    def test_duplicates_and_disconnected(self):
        e=Episode(self.s)
        with self.assertRaises(ValueError): e.step(next(iter(e.initial)))
        far=next(eid for eid,edge in e.edges.items() if not {edge['u'],edge['v']}&e.road_nodes())
        with self.assertRaises(ValueError): e.step(far)
        action=e.legal_actions()[0]; e.step(action)
        with self.assertRaises(ValueError): e.step(action)
    def test_identity(self):
        d=read(ROOT/'examples/smoke-seed0.json'); d['scenario_sha256']='wrong'
        with self.assertRaises(ValueError): evaluate(self.s,d)
    def test_heuristic_access_not_full_budget(self):
        r=evaluate(self.s,read(ROOT/'examples/heuristic-seed0.json'))
        self.assertEqual(r['metrics']['NR'],11)
        self.assertEqual(r['metrics']['unserved_places'],0)
        self.assertFalse(r['metrics']['budget_complete'])
    def test_boundary_distance(self):
        s={'id':'toy','nodes':[{'id':x} for x in 'abcd'],
           'edges':[{'id':str(i),'u':u,'v':v,'cost':w,'existing':True,'barrier':False} for i,(u,v,w) in enumerate([('a','b',2),('b','c',3),('c','d',4)])],
           'places':[{'id':'A','nodes':['a','b']},{'id':'B','nodes':['c','d']}], 'protocol':{'max_added_segments':0}}
        self.assertEqual(Episode(s).metrics()['AD'],3)
        s['places'][1]['nodes']=['b','c']
        self.assertEqual(Episode(s).metrics()['AD'],0)
    def test_grid_fails_closed(self):
        g=project(self.s)
        self.assertFalse(g['runnable_in_game'])
        self.assertEqual(g['width'],50); self.assertEqual(g['height'],30)
        g2=project(self.s,6,6)
        self.assertTrue(g2['conflicts'])

    def test_saved_grid_and_source_distances(self):
        import heapq, math
        g=read(ROOT/'data/grid-draft.json')
        audited=project(self.s,margin=g['projection']['margin'],offset=g['projection']['offset'],paths_override=g['corridor_cells'])
        self.assertEqual(audited['conflicts'],[])
        source={n['id']:[] for n in self.s['nodes']}; grid={}
        for e in self.s['edges']:
            source[e['u']].append((e['v'],e['cost'])); source[e['v']].append((e['u'],e['cost']))
            cells=list(map(tuple,g['corridor_cells'][e['id']]))
            self.assertGreater(len(cells),1)
            w=e['cost']/(len(cells)-1)
            for a,b in zip(cells,cells[1:]):
                self.assertEqual(max(abs(a[0]-b[0]),abs(a[1]-b[1])),1)
                grid.setdefault(a,[]).append((b,w)); grid.setdefault(b,[]).append((a,w))
        def shortest(adj,start):
            ds={start:0}; q=[(0,start)]
            while q:
                d,n=heapq.heappop(q)
                if ds[n]!=d: continue
                for nxt,w in adj[n]:
                    if d+w<ds.get(nxt,math.inf): ds[nxt]=d+w; heapq.heappush(q,(d+w,nxt))
            return ds
        for nid,cell in g['source_node_cells'].items():
            a=shortest(source,nid); b=shortest(grid,tuple(cell))
            for target,pos in g['source_node_cells'].items(): self.assertAlmostEqual(a[target],b[tuple(pos)],places=10)

    def test_bridge_and_path_validation(self):
        from bridge import Bridge,construction_setup
        grid=read(ROOT/'data/grid-draft.json')
        setup=construction_setup(self.s)
        self.assertEqual(setup,construction_setup(self.s))
        self.assertEqual(sum(x['kind']=='destination' for x in setup['roles'].values()),8)
        bridge=Bridge(self.s,grid,setup)
        eid=bridge.episode.legal_actions()[0]
        bridge.apply_complete_corridor_path(grid['corridor_cells'][eid])
        self.assertEqual(bridge.design('test')['actions'],[eid])
        with self.assertRaises(ValueError): bridge.apply_complete_corridor_path([[0,0],[1,0]])
        replay=Bridge(self.s,grid,setup,bridge.design('test'))
        self.assertEqual(replay.observe(),bridge.observe())
if __name__=='__main__': unittest.main()


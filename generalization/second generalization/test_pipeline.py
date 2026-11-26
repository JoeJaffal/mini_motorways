import tempfile, unittest, copy
from pathlib import Path
from pipeline import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.s=read(ROOT/'data/scenario.json'); self.g=read(ROOT/'data/grid.json')
        self.c=read(ROOT/'data/protocol.json'); self.setup=read(ROOT/'data/construction-setup.json')
        self.reference=read(ROOT/'data/reference-design.json')
    def test_budget_and_baseline_identity(self):
        st=validate_design(self.s,self.reference,self.c['budget_source_cost'])
        self.assertAlmostEqual(st.cost,self.c['budget_source_cost'])
        self.assertEqual(st.legal(),[])
        self.assertEqual(st.unserved(),[])
        with self.assertRaises(ValueError): validate_design(self.s,self.reference,self.c['budget_source_cost']/2)
        d=copy.deepcopy(self.reference); d['actions'].append(d['actions'][0])
        with self.assertRaises(ValueError): validate_design(self.s,d,self.c['budget_source_cost']*2)
    def test_source_constraints(self):
        st=DesignState(self.s,self.c['budget_source_cost'])
        with self.assertRaises(ValueError): st.step(next(iter(st.initial)))
        eid=next(eid for eid,e in st.edges.items() if not st.nodes().intersection([e['u'],e['v']]))
        with self.assertRaises(ValueError): st.step(eid)
    def test_manifest_independence(self):
        a=generate_workload(self.s,self.setup,self.c,1001)
        b=generate_workload(self.s,self.setup,self.c,1001)
        self.assertEqual(a,b)
        self.assertNotEqual(a['requests'],generate_workload(self.s,self.setup,self.c,1002)['requests'])
        roles=copy.deepcopy(self.setup); roles['roles']=dict(reversed(list(roles['roles'].items())))
        self.assertEqual(a,generate_workload(self.s,roles,self.c,1001))
        self.assertTrue(all(self.setup['roles'][r['origin']]['kind']=='house' and self.setup['roles'][r['destination']]['kind']=='destination' for r in a['requests']))
    def test_no_leaked_seed_and_invalid_config(self):
        c=copy.deepcopy(self.c); c['evaluation_seeds']=[c['construction_seed']]
        with self.assertRaises(ValueError): validate_config(c)
        c=copy.deepcopy(self.c); c['end_s']=1
        with self.assertRaises(ValueError): validate_config(c)
    def test_complete_accounting(self):
        requests=[{'id':str(i),'origin':'a','destination':'b','depart':0} for i in range(5)]
        content='<tripinfos><tripinfo id="0" depart="2" arrival="12" duration="10" waitingTime="3"/><tripinfo id="1" depart="-1" arrival="-1" vaporized="end"/><tripinfo id="2" depart="0" arrival="-1" vaporized="end"/><tripinfo id="3" depart="0" arrival="5" duration="5" vaporized="collision"/></tripinfos>'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'trips.xml'; p.write_text(content)
            rows=account({'requests':requests},{'4':'no access'},p,20)
            self.assertEqual([r['status'] for r in rows],['completed','never_departed','unfinished','removed','unroutable'])
            self.assertEqual(rows[0]['requested_to_arrival_s'],12)
            self.assertEqual(rows[1]['departure_delay_s'],20)
            self.assertEqual(sum(summarize(rows)['counts'].values()),5)
            with self.assertRaises(ValueError): account({'requests':requests},{},p,20)
    def test_pairing_and_completion_conditioning(self):
        r={'id':'a','origin':'x','destination':'y','depart':0,'status':'completed','duration_s':10,'requested_to_arrival_s':12,'waiting_s':0,'departure_delay_s':2}
        p=pair([r],[r]); self.assertEqual(p['mean_paired_duration_difference_s'],0)
        bad=dict(r,origin='changed')
        with self.assertRaises(ValueError): pair([r],[bad])
        failed=dict(r,status='unroutable',duration_s=None,requested_to_arrival_s=None,departure_delay_s=None)
        self.assertIsNone(pair([r],[failed])['mean_paired_duration_difference_s'])
        self.assertEqual(pair([r],[failed])['candidate_minus_reference_completed'],-1)
    def test_grid_validation(self):
        check_grid(self.s,self.g)
        broken=copy.deepcopy(self.g); eid=self.s['edges'][0]['id']; broken['corridor_cells'][eid][0]=[0,0]
        with self.assertRaises(ValueError): check_grid(self.s,broken)
    def test_second_bridge(self):
        from bridge import Bridge
        b=Bridge(self.s,self.g,self.setup,self.c)
        eid=b.state.legal()[0]; b.apply_complete_corridor_path(self.g['corridor_cells'][eid])
        self.assertEqual(b.freeze('test')['actions'],[eid])
        with self.assertRaises(ValueError): b.apply(eid)

if __name__=='__main__': unittest.main()


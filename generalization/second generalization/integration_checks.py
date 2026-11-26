"""Real SUMO acceptance checks, separate from GP evaluation."""
import argparse
from pipeline import *
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--prefix',required=True); args=parser.parse_args()
    if not args.prefix.replace('-','').replace('_','').isalnum(): raise ValueError('Use a simple unique prefix')
    c=read(ROOT/'data/protocol.json'); s=read(ROOT/'data/scenario.json'); g=read(ROOT/'data/grid.json')
    cfg=ROOT/'runs'/(args.prefix+'-configs'); cfg.mkdir(parents=True,exist_ok=False)
    evidence={}
    self_run=run(ROOT/'data/reference-design.json',ROOT/'runs'/(args.prefix+'-self'))
    for r in self_run['seeds']:
        assert r['paired']['candidate_minus_reference_completed']==0
        assert r['paired']['mean_paired_duration_difference_s']==0
        folder=ROOT/'runs'/(args.prefix+'-self')
        assert read(folder/'reference'/f"seed-{r['seed']}"/'outcomes.json')==read(folder/'candidate'/f"seed-{r['seed']}"/'outcomes.json')
    evidence['identical_design_identical_outcomes']=True
    disconnected=run(ROOT/'examples/empty-design.json',ROOT/'runs'/(args.prefix+'-disconnected'))
    assert all(r['candidate']['counts']['unroutable']>0 for r in disconnected['seeds'])
    evidence['disconnected_counts']=[r['candidate']['counts'] for r in disconnected['seeds']]
    cutoff=dict(c,trip_count=120,departure_window_s=5,end_s=6,evaluation_seeds=[1001])
    write(cfg/'cutoff.json',cutoff)
    cut=run(ROOT/'data/reference-design.json',ROOT/'runs'/(args.prefix+'-cutoff'),config_path=cfg/'cutoff.json')
    counts=cut['seeds'][0]['candidate']['counts']
    assert counts['unfinished']>0 and counts['never_departed']>0
    assert sum(counts.values())==120
    evidence['cutoff_counts']=counts
    # Explicitly verify an all-unroutable workload does not disappear or crash.
    empty=validate_design(s,read(ROOT/'examples/empty-design.json'),c['budget_source_cost'])
    folder=ROOT/'runs'/(args.prefix+'-no-access'); folder.mkdir()
    bins={n:binary(n) for n in ['netconvert','duarouter','sumo']}
    network=export_network(s,g,empty,c,folder,bins)
    missing=next(p for p,e in network['endpoints'].items() if not e['source_edges'])
    destination=next(p for p,e in network['endpoints'].items() if e['sink_edges'])
    manifest={'requests':[{'id':'deliberate-no-access','origin':missing,'destination':destination,'depart':0}]}
    seed_folder=folder/'seed-1001'; seed_folder.mkdir()
    outcome=simulate(manifest,network,c,seed_folder,bins,1001)
    assert outcome['summary']['counts']['unroutable']==1
    evidence['all_unroutable_preserved']=True
    evidence['sumo_version']=self_run['versions']['sumo']
    evidence['no_GP_evaluated']=True
    write(ROOT/'results'/(args.prefix+'-validation.json'),evidence)
    print(json.dumps(evidence,indent=2))

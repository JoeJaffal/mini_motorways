"""Model-neutral integration boundary; no mbrl import or guessed GP tensors."""
from pathlib import Path
import argparse, random
from experiment import Episode, read, write, digest
ROOT=Path(__file__).resolve().parent

def construction_setup(scenario, seed=0, destination_count=8):
    ids=sorted(p['id'] for p in scenario['places'])
    if not 1<=destination_count<len(ids): raise ValueError('Need origins and destinations')
    destinations=set(random.Random(seed).sample(ids,destination_count))
    return {'schema_version':1,'scenario_sha256':digest(scenario),'seed':seed,
            'demand_generator':'native Mini Motorways destination demand; host binding pending',
            'assignment_rule':'uniform sample without replacement; one color for all places',
            'roles':{pid:{'kind':'destination' if pid in destinations else 'house','color':0} for pid in ids},
            'status':'configuration_only_not_a_spawn_fixture',
            'note':'Engineering default, configurable before evaluation. No traffic enters NR/AD/SC.'}

class Bridge:
    def __init__(self,scenario,grid,setup,design=None):
        if grid['scenario_sha256']!=digest(scenario) or setup['scenario_sha256']!=digest(scenario): raise ValueError('Scenario mismatch')
        if grid['conflicts']: raise ValueError('Grid topology conflicts')
        self.episode=Episode(scenario); self.grid=grid; self.setup=setup
        if design is not None:
            if design['scenario_sha256']!=digest(scenario): raise ValueError('Design mismatch')
            for action in design['actions']: self.episode.step(action)

    def observe(self):
        state=self.episode.observe()
        return {'schema_version':1,'state':state,'grid':{'width':self.grid['width'],'height':self.grid['height'],
                'source_node_cells':self.grid['source_node_cells'],
                'corridor_cells':self.grid['corridor_cells'],
                'built_corridor_ids':state['road_edge_ids'], 'legal_corridor_ids':state['legal_edge_ids']},
                'places':self.episode.scenario['places'],'construction_setup':self.setup,
                'host_status':'not connected; building footprints and access mapping pending',
                'required_host_observation':'GP branch-specific observation to be supplied later; not mbrl tensors'}

    def apply(self,edge_id):
        self.episode.step(edge_id)
        return self.observe()

    def apply_complete_corridor_path(self,cells):
        # No nearest-edge snapping or partial-road credit. Multi-corridor paths
        # must be split in order by the future host adapter.
        for eid,path in self.grid['corridor_cells'].items():
            if cells==path or cells==list(reversed(path)):
                return self.apply(eid)
        raise ValueError('Path is not one complete source corridor; partial/off-corridor strokes are not accepted')

    def design(self,label):
        return {'schema_version':1,'scenario_sha256':digest(self.episode.scenario),
                'label':label,'actions':list(self.episode.actions)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design',type=Path)
    parser.add_argument('--edge',help='Optional next source corridor ID')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'examples/bridge')
    args=parser.parse_args()
    s=read(ROOT/'data/harare.json'); g=read(ROOT/'data/grid-draft.json')
    setup=read(ROOT/'data/construction-setup.json')
    bridge=Bridge(s,g,setup,read(args.design) if args.design else None)
    if args.edge: bridge.apply(args.edge)
    write(args.output_dir/'observation.json',bridge.observe())
    write(args.output_dir/'design.json',bridge.design('supplied candidate; model identity not yet bound'))

"""GP-facing corridor interface for the second experiment's COST budget."""
from pipeline import DesignState, validate_design, check_grid, digest

class Bridge:
    def __init__(self,scenario,grid,setup,protocol,design=None):
        check_grid(scenario,grid)
        if setup['scenario_sha256']!=digest(scenario) or protocol['scenario_sha256']!=digest(scenario): raise ValueError('Mismatched inputs')
        self.state=validate_design(scenario,design,protocol['budget_source_cost']) if design else DesignState(scenario,protocol['budget_source_cost'])
        self.grid=grid; self.setup=setup; self.protocol=protocol
    def observe(self):
        return {'state':self.state.observe(),'grid':self.grid,'construction_setup':self.setup,
                'host_status':'GP/native-game binding pending; never use first-experiment 33-segment mask here'}
    def apply(self,source_edge_id):
        self.state.step(source_edge_id)
        return self.observe()
    def apply_complete_corridor_path(self,cells):
        for eid,path in self.grid['corridor_cells'].items():
            if cells==path or cells==list(reversed(path)): return self.apply(eid)
        raise ValueError('Expected exactly one complete permitted corridor')
    def freeze(self,label): return self.state.design(label)

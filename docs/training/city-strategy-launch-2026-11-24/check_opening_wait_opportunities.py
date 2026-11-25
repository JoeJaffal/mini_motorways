from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import json
from city_road_pilot import CityRoadEnv
from audit_city_service import native_edge_graph,estimated_cost,tile
ROOT=Path.cwd();REC=ROOT/'docs/training/city-strategy-launch-2026-11-24'
def run(seed):
 e=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',horizon=240,observation_horizon=600)
 try:
  _,info=e.reset(options=dict(scenario_seed=seed));houses=[b for b in e.raw['buildings'] if b['isHouse']];shops=[b for b in e.raw['buildings'] if not b['isHouse']];assert len(houses)==len(shops)==1
  home={tile(houses[0]['cell'])};entrances={tile(x) for x in shops[0]['entrances']};checks=[];previous=-1
  while not e.done:
   stamp=int(info['seconds']//5)
   if stamp!=previous:
    cost=estimated_cost(native_edge_graph(e.raw,e.action_masks()),home,entrances);checks.append(dict(time=info['seconds'],cost=cost,stock=info['road_stock'],affordable=cost is not None and cost<=info['road_stock']));previous=stamp
   _,_,_,_,info=e.step(0)
  affordable=[v for v in checks if v['affordable']];row=dict(seed=seed,end_seconds=info['seconds'],initial_estimate=checks[0],first_affordable=affordable[0] if affordable else None,checks=checks);print({k:v for k,v in row.items() if k!='checks'},flush=True);return row
 finally:e.close()
if __name__=='__main__':
 source=json.loads((REC/'opening-failures.json').read_text())['rows']
 with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('spawn')) as pool:rows=list(pool.map(run,[r['seed'] for r in source]))
 (REC/'opening-wait-opportunities.json').write_text(json.dumps(dict(note='Wait-only counterfactuals for10 consumed zero-score seeds. Diagnostic legal-edge cost estimates only; no routes/actions given to learner. Individually legal edges can overestimate joint feasibility. Waiting changes later spawns relative to the failed actor trajectory.',rows=rows),indent=2)+'\n')

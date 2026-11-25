from pathlib import Path
import json,torch,os
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from sb3_contrib import MaskablePPO
from audit_city_service import trace
ROOT=Path.cwd();REC=ROOT/'docs/training/city-strategy-launch-2026-11-24'
def worker(row):
 torch.set_num_threads(1)
 m=MaskablePPO.load(ROOT/'output/training/city-strategy-original-delay-01/segment-001/final.zip',device='cpu')
 result=trace('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll',m,row['seed'],row['action_seed'],estimate=True)
 assert result['trips']==row['after']
 print(json.dumps(dict(seed=row['seed'],score=result['trips'],stock=result['road_stock'],unserved=[t for t in result['targets'] if not t['served']])),flush=True)
 return result
if __name__=='__main__':
 shifts=json.loads((REC/'confirmation04-failure-shifts.json').read_text())['paired_changes']
 jobs=[r for r in shifts if r['delta']<0 and r['after_stock']>0][:4]
 with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('spawn')) as pool:rows=list(pool.map(worker,jobs))
 (REC/'reserve-loss-affordability.json').write_text(json.dumps(dict(note='Four selected consumed-confirmation regressions with stock remaining. Shortest-cost estimate is diagnostic only,never passed to actor or trainer; single-edge legality does not guarantee jointly feasible path.',selected=jobs,rows=rows),indent=2)+'\n')

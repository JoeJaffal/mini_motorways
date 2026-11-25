"""Explicit seed/horizon native city suite, without route estimation."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from audit_city_service import trace
from prepare_city_policy import sha256

def worker(dll,checkpoint,jobs,horizon):
    torch.set_num_threads(1);model=MaskablePPO.load(checkpoint,device='cpu');rows=[]
    for seed,action_seed in jobs:
        row=trace(dll,model,seed,action_seed,estimate=False,horizon=horizon,allow_bridges=True)
        rows.append(row);print('CITY',seed,action_seed,row['trips'],row['seconds'],flush=True)
    return rows

def main():
    p=argparse.ArgumentParser()
    for name in ('dll','checkpoint','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--seed-start',type=int,required=True);p.add_argument('--count',type=int,default=16);p.add_argument('--action-seed',type=int,default=421000);p.add_argument('--horizon',type=int,default=600);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    if a.count<1 or a.workers<1 or not 0<a.horizon<=3600:p.error('Positive count/workers; horizon1..3600')
    a.output.mkdir(parents=True,exist_ok=False);before=sha256(a.checkpoint)
    jobs=[(a.seed_start+i,a.action_seed+j*10000+i) for j in range(2) for i in range(a.count)]
    (a.output/'suite.json').write_text(json.dumps(dict(jobs=jobs,horizon=a.horizon,observation_horizon=600,route_estimation=False),indent=2))
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool:
        rows=[r for f in [pool.submit(worker,str(a.dll),str(a.checkpoint),jobs[k::a.workers],a.horizon) for k in range(a.workers)] for r in f.result()]
    assert len(rows)==2*a.count and sha256(a.checkpoint)==before
    (a.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary=dict(checkpoint=str(a.checkpoint),checkpoint_sha256=before,host_sha256=sha256(a.dll),horizon=a.horizon,games=len(rows),scoring=sum(r['trips']>0 for r in rows),**{k:float(np.mean([r[k] for r in rows])) for k in ('trips','seconds','paid_units','outside_routes')})
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)

if __name__=='__main__':main()

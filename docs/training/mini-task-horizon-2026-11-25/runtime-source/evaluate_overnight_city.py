"""Frozen native city retention; no path-estimation or teacher actions."""
import argparse
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from audit_city_service import trace
from prepare_city_policy import sha256


def worker(dll,checkpoint,jobs):
    torch.set_num_threads(1)
    model=MaskablePPO.load(checkpoint,device='cpu')
    rows=[]
    for seed,action_seed in jobs:
        row=trace(dll,model,seed,action_seed,estimate=False,horizon=600,allow_bridges=True)
        rows.append(row)
        print('CITY',seed,row['trips'],flush=True)
    return rows


def main():
    p=argparse.ArgumentParser()
    for name in ('dll','checkpoint','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--workers',type=int,default=2)
    a=p.parse_args()
    if a.workers<1:p.error('Workers must be positive')
    a.output.mkdir(exist_ok=False,parents=True)
    jobs=[(start+i,193251+j*100+i) for start in (184000000,185000000) for j in range(2) for i in range(8)]
    # Existing development layouts/action RNGs, not an untouched test suite.
    (a.output/'suite.json').write_text(json.dumps(jobs)+'\n')
    before=sha256(a.checkpoint)
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool:
        futures=[pool.submit(worker,str(a.dll),str(a.checkpoint),jobs[i::8]) for i in range(8)]
        rows=[row for future in futures for row in future.result()]
    assert len(rows)==32 and len({(x['seed'],x['action_seed']) for x in rows})==32
    assert sha256(a.checkpoint)==before
    (a.output/'games.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
    report=dict(checkpoint=str(a.checkpoint),sha256=before,host_sha256=sha256(a.dll),
                suite='Consumed development suite; sampled inference,600s,bridges enabled',
                games=len(rows),scoring=sum(x['trips']>0 for x in rows),
                **{key:float(np.mean([x[key] for x in rows])) for key in ('trips','paid_units','outside_routes')})
    (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()

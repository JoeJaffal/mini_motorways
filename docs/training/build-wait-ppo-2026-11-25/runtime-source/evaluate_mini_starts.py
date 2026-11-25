"""Development-only checks on the selected reset bank; not transfer evidence."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from mini_recorded_starts import MiniRecordedStartEnv
from prepare_city_policy import masked_probs, sha256
from city_curriculum import SMALL_TIGHT, SMALL_OFFSET

def worker(dll,bank,checkpoint,jobs):
    torch.set_num_threads(1);m=MaskablePPO.load(checkpoint,device='cpu')
    e=MiniRecordedStartEnv(dll,mini_starts=bank,stage='expansion-balanced',workers=16,worker=14,collapse_forced_wait=True);rows=[]
    try:
        for ex,index,repeat in jobs:
            e.worker=14 if ex==SMALL_TIGHT else 10;e.prefix_cursor=index
            obs,info=e.reset();rng=np.random.default_rng(411000+index+repeat*1000);total=0
            while not e.done:
                mask=e.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(m,obs,mask).astype(float)
                action=int(rng.choice(len(p),p=p/p.sum()));obs,reward,_,_,info=e.step(action);total+=reward
            rows.append(dict(exercise=ex,prefix_id=info['prefix_id'],repeat=repeat,score=total,success=info['new_deliveries']>0,paid=info['stock_initial']-info['road_stock']))
        return rows
    finally:e.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',required=True);p.add_argument('--bank',required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    if a.workers<1:p.error('Workers must be positive')
    a.output.mkdir(parents=True,exist_ok=False)
    starts=json.loads(Path(a.bank).read_text())['starts'];jobs=[(ex,i,j) for ex in (SMALL_TIGHT,SMALL_OFFSET) for i in range(sum(s['exercise']==ex for s in starts)) for j in range(2)]
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool:
        rows=[r for f in [pool.submit(worker,a.dll,a.bank,a.checkpoint,jobs[k::8]) for k in range(8)] for r in f.result()]
    (a.output/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary={ex:dict(games=sum(r['exercise']==ex for r in rows),successes=sum(r['success'] for r in rows if r['exercise']==ex)) for ex in (SMALL_TIGHT,SMALL_OFFSET)}
    (a.output/'summary.json').write_text(json.dumps(dict(checkpoint_sha256=sha256(Path(a.checkpoint)),bank_sha256=sha256(Path(a.bank)),results=summary),indent=2));print(summary)

if __name__=='__main__':main()

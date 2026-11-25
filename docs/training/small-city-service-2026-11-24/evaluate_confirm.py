from pathlib import Path
import argparse,json,os
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import torch,numpy as np
from sb3_contrib import MaskablePPO
from audit_city_service import trace
from prepare_city_policy import sha256

def worker(checkpoint,jobs):
 torch.set_num_threads(1);m=MaskablePPO.load(checkpoint,device='cpu');rows=[]
 for split,seed,action_seed in jobs:
  row=trace('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll',m,seed,action_seed,estimate=False,horizon=600,allow_bridges=True)
  row['split']=split;rows.append(row);print(f"EVAL | {split} | {seed} | {row['trips']}",flush=True)
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
 jobs=[(split,start+i,244001+offset+i) for split,start,offset in [('fresh_a',196000000,0),('fresh_b',196000016,16)] for i in range(16)]
 (a.output/'suite.json').write_text(json.dumps(jobs)+'\n')
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  futures=[pool.submit(worker,a.checkpoint,jobs[i::8]) for i in range(8)];rows=[row for f in futures for row in f.result()]
 (a.output/'games.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
 summary=dict(checkpoint=a.checkpoint,sha256=sha256(Path(a.checkpoint)),host_sha256=sha256(Path('output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll')),horizon=600,allow_bridges=True,results={})
 baseline={} if not a.baseline else {(x['seed'],x['action_seed']):x for x in map(json.loads,(a.baseline/'games.jsonl').read_text().splitlines())}
 for split in ('fresh_a','fresh_b'):
  group=[x for x in rows if x['split']==split];item=dict(games=len(group),mean=float(np.mean([x['trips'] for x in group])),scoring=sum(x['trips']>0 for x in group),new_targets_served=sum(t['served']>0 for x in group for t in x['targets']),stockouts=sum(t['arrival_stock']==0 for x in group for t in x['targets']))
  if baseline:
   # Resample cities, keeping both action RNG replicates together.
   deltas=np.array([np.mean([x['trips']-baseline[(x['seed'],x['action_seed'])]['trips'] for x in group if x['seed']==seed]) for seed in sorted({x['seed'] for x in group})]);rng=np.random.default_rng(142915);draw=rng.integers(len(deltas),size=(12000,len(deltas)));item.update(delta=float(deltas.mean()),interval95=np.quantile(deltas[draw].mean(1),[.025,.975]).tolist())
  summary['results'][split]=item
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()

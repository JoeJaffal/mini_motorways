from pathlib import Path
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import argparse,json,multiprocessing as mp,numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import masked_probs,sha256
from audit_city_roads import assigned_edges
from export_city_replays import action_endpoints,frame
DLL='/home/mohammadjaffal/mini_motorways/output/training/road-cost-continuation-01/runtime/host/TrafficHost.dll'

def play(model,split,exercise,seed,action_seed,capture=False):
 e=CityCurriculumEnv(DLL,validation=split=='validation');rng=np.random.default_rng(action_seed);paid=Counter();used=set();first={};arrivals={};frames=[];steps=0
 try:
  obs,info=e.reset(options=dict(exercise=exercise,scenario_seed=seed));initial_id=next(b['id'] for b in e.raw['buildings'] if not b['isHouse']);total=0
  if capture:frames.append(frame(e.raw,'Start'))
  while not e.done:
   mask=e.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float);action=int(rng.choice(len(p),p=p/p.sum()));stock=info['road_stock']
   obs,reward,_,_,info=e.step(action);total+=reward;steps+=1
   if action and stock>info['road_stock']:paid[tuple(sorted(action_endpoints(action)))]+=stock-info['road_stock']
   used.update(assigned_edges(e.raw))
   for b in e.raw['buildings']:
    if b['isHouse']:continue
    if b['id'] not in arrivals:arrivals[b['id']]=dict(time=e.raw['time'],stock=info['road_stock'])
    if b['served'] and b['id'] not in first:first[b['id']]=e.raw['time']
   if capture:frames.append(frame(e.raw,'Build' if action else 'Wait',action_endpoints(action) if action else None))
   if steps>2000:raise RuntimeError('Unexpected lesson nontermination')
  later=[b for b in e.raw['buildings'] if not b['isHouse'] and b['id']!=initial_id];later_served=any(b['served'] for b in later);initial_served=initial_id in first
  assert total==info['trips']==sum(info['served'].values())
  row=dict(split=split,exercise=exercise,seed=seed,action_seed=action_seed,score=total,first_served=initial_served,later_exists=bool(later),later_served=later_served,both_served=initial_served and later_served,first_delivery=first.get(initial_id),later_delivery=min((first[b['id']] for b in later if b['id'] in first),default=None),arrival_stock=arrivals[later[0]['id']]['stock'] if later else None,initial_stock=info['stock_initial'],remaining_stock=info['road_stock'],paid_units=sum(paid.values()),outside_routes=sum(v for k,v in paid.items() if k not in used),decisions=steps,no_build=info['road_actions']==0)
  return row,frames
 finally:e.close()

def worker(checkpoint,jobs):
 torch.set_num_threads(1);m=MaskablePPO.load(checkpoint,device='cpu');rows=[]
 for job in jobs:
  row,_=play(m,*job);rows.append(row);print('EVAL',row['split'],row['exercise'],row['seed'],row['score'],row['first_served'],row['later_served'],flush=True)
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
 jobs=[('validation',exercise,199000000+i,251000+j*100+i) for exercise in ['small-city-offset-single','small-city-offset-stock'] for j in range(2) for i in range(32)]
 (a.output/'suite.json').write_text(json.dumps(jobs)+'\n')
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  futures=[pool.submit(worker,a.checkpoint,jobs[i::8]) for i in range(8)];rows=[x for f in futures for x in f.result()]
 (a.output/'games.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
 summary={}
 for split in ['validation']:
  for exercise in ['small-city-offset-single','small-city-offset-stock']:
   group=[x for x in rows if x['split']==split and x['exercise']==exercise]
   summary[split+'/'+exercise]={k:float(np.mean([x[k] for x in group])) for k in ['score','first_served','later_exists','later_served','both_served','initial_stock','remaining_stock','paid_units','outside_routes','no_build']};summary[split+'/'+exercise]['games']=len(group)
 (a.output/'summary.json').write_text(json.dumps(dict(checkpoint=a.checkpoint,sha256=sha256(Path(a.checkpoint)),host_sha256=sha256(Path(DLL)),results=summary),indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()

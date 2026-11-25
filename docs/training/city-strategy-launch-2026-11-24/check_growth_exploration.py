from pathlib import Path
import json,torch,numpy as np
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
ROOT=Path.cwd();REC=ROOT/'docs/training/city-strategy-launch-2026-11-24';MODEL=ROOT/'output/training/city-strategy-original-delay-01/segment-001/final.zip'
def run(row):
 torch.set_num_threads(1);m=MaskablePPO.load(MODEL,device='cpu');e=CityRoadEnv('output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll');steps=[]
 try:
  obs,info=e.reset(options=dict(scenario_seed=row['seed']));rng=np.random.default_rng(row['action_seed'])
  while not e.done:
   mask=e.action_masks();p=masked_probs(m,obs,mask).astype(float);p/=p.sum()
   with torch.no_grad():tensor,_=m.policy.obs_to_tensor(obs);_,gate=m.policy.features_extractor.strategy_context(tensor)
   action=int(rng.choice(len(p),p=p));q=p[1:][mask[1:]];q=q/q.sum() if q.sum() else q;positive=q[q>0]
   if gate.item() and len(q):steps.append(dict(time=info['seconds'],stock=info['road_stock'],legal_roads=len(q),wait=float(p[0]),conditional_max=float(q.max()),entropy=float(-(positive*np.log(positive)).sum()),action=action))
   obs,_,_,_,info=e.step(action)
  assert info['trips']==row['after']
  result=dict(seed=row['seed'],score=info['trips'],states=len(steps),conditional_max_over_0999=sum(x['conditional_max']>.999 for x in steps),mean_conditional_entropy=float(np.mean([x['entropy'] for x in steps])) if steps else None,mean_wait=float(np.mean([x['wait'] for x in steps])) if steps else None,road_choices=sum(x['action']!=0 for x in steps),steps=steps)
  print({k:v for k,v in result.items() if k!='steps'},flush=True);return result
 finally:e.close()
if __name__=='__main__':
 shifts=json.loads((REC/'confirmation04-failure-shifts.json').read_text())['paired_changes'];jobs=[r for r in shifts if r['delta']<0 and r['after_stock']>0][:4]
 with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('spawn')) as pool:rows=list(pool.map(run,jobs))
 (REC/'growth-exploration-failures.json').write_text(json.dumps(dict(note='Four selected consumed-confirmation losses,post-gate legal-road states; diagnostic only.',model=str(MODEL),sha256=sha256(MODEL),rows=rows),indent=2)+'\n')

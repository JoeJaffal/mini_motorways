from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import multiprocessing as mp,json
import numpy as np,torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import masked_probs,sha256
R=Path('docs/training/mini-task-repair-2026-11-25')
DLL='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
MODELS={'original':'output/training/city-whole-initial-01/start.zip','reset65':'output/training/mini-reset-comparison-01/reset-curriculum/checkpoint-000065536.zip'}
def worker(label,jobs):
 torch.set_num_threads(1);m=MaskablePPO.load(MODELS[label],device='cpu');e=CityCurriculumEnv(DLL,validation=True);rows=[]
 try:
  for expected in jobs:
   ex=expected['exercise'];seed=expected['seed'];obs,info=e.reset(options=dict(exercise=ex,scenario_seed=seed));e.horizon=300;rng=np.random.default_rng(seed+103);moments={};reward_sum=0
   while not e.done:
    mask=e.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(m,obs,mask).astype(float);act=int(rng.choice(len(p),p=p/p.sum()));obs,reward,terminal,truncated,info=e.step(act);reward_sum+=reward
    for t in (60,120,180,300):
     if e.raw['time']>=t-1e-6 and str(t) not in moments:
      shops=[b for b in e.raw['buildings'] if not b['isHouse']];moments[str(t)]=dict(score=info['trips'],stock=info['road_stock'],served=sum(b['served']>0 for b in shops),shops=len(shops),warning=sum(b['warningVisible'] for b in shops))
   assert moments['60']['score']==expected['score'] and moments['60']['stock']==expected['remaining_stock'],(label,ex,seed,moments['60'],expected)
   assert reward_sum==info['trips']
   row=dict(model=label,exercise=ex,seed=seed,score=info['trips'],seconds=e.raw['time'],native_game_over=terminal,moments=moments,old_60_score=expected['score'],old_later_served=expected['later_served']);rows.append(row);print('HORIZON',label,ex,seed,expected['score'],info['trips'],terminal,flush=True)
  return rows
 finally:e.close()
def main():
 out=R/'horizon-diagnostic';out.mkdir(exist_ok=False)
 paths={'original':R/'audit/games.jsonl','reset65':R/'evaluation/practice-reset-curriculum-65536/games.jsonl'}
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  fs=[]
  for label,path in paths.items():
   jobs=[x for x in map(json.loads,path.read_text().splitlines()) if x['exercise'] in ('small-city-offset-single','small-city-offset-pairs') and (label!='original' or x['model']=='original')]
   fs.extend(pool.submit(worker,label,jobs[i::4]) for i in range(4))
  rows=[x for f in fs for x in f.result()]
 (out/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
 (out/'config.json').write_text(json.dumps(dict(models={k:dict(path=v,sha256=sha256(Path(v))) for k,v in MODELS.items()},host_sha256=sha256(Path(DLL)),horizon=300,observation_horizon=600,first60_matches_archived=True),indent=2))
 print('COMPLETE',len(rows),flush=True)
if __name__=='__main__':main()

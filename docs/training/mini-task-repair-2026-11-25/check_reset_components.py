"""Diagnostic inference ablation of Wait versus conditional road choice.

No training, labels, planning or checkpoint promotion. Uses consumed city seeds.
"""
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import frozen_game,masked_probs,sha256
from summarize_expansion_comparison import paired

ROOT=Path('docs/training/mini-task-repair-2026-11-25')
DLL=Path('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll')
MODELS=dict(original=Path('output/training/city-whole-initial-01/start.zip'),
            reset_final=Path('output/training/mini-reset-comparison-01/reset-curriculum/final.zip'))


def combine(wait,roads):
    wait=wait.astype(float);wait=wait/wait.sum()
    roads=roads.astype(float);out=np.zeros_like(roads);out[0]=wait[0]
    mass=roads[1:].sum()
    if mass:out[1:]=(1-out[0])*roads[1:]/mass
    elif out[0]!=1:raise RuntimeError('Conditional road distribution underflow')
    return out


def worker(mode,jobs):
    torch.set_num_threads(1)
    models={name:MaskablePPO.load(path,device='cpu') for name,path in MODELS.items()}
    wait_label,road_label=('original','reset_final') if mode=='old_wait_new_roads' else ('reset_final','original')
    def probabilities(model,obs,mask):
        if mask.sum()==1:return mask.astype(float)
        p={name:masked_probs(m,obs,mask) for name,m in models.items()}
        for value in p.values():np.testing.assert_allclose(combine(value,value),value/value.astype(float).sum(),rtol=1e-6,atol=1e-8)
        result=combine(p[wait_label],p[road_label]);assert not result[~mask].any()
        return result
    env=CityRoadEnv(str(DLL),horizon=600,observation_horizon=600,allow_bridges=True)
    rows=[]
    try:
        for seed,action_seed in jobs:
            row=frozen_game(env,models['original'],seed,probabilities=probabilities,action_seed=action_seed)
            rows.append(dict(mode=mode,action_seed=action_seed,**row))
            print('COMPONENT',mode,seed,action_seed,row['trips'],flush=True)
        return rows
    finally:env.close()


def main():
    out=ROOT/'reset-components';out.mkdir(exist_ok=False)
    read=lambda path:[json.loads(line) for line in path.read_text().splitlines()]
    original=read(ROOT/'evaluation/city-initial/games.jsonl')
    final=read(ROOT/'evaluation/city-reset-curriculum-262144/games.jsonl')
    jobs=[(x['seed'],x['action_seed']) for x in original]
    config=dict(models={k:dict(path=str(v),sha256=sha256(v)) for k,v in MODELS.items()},
        host_sha256=sha256(DLL),suite=jobs,
        limits='Diagnostic probability-component intervention on reused development cities. Neither hybrid is a trained checkpoint or eligible for automatic promotion.')
    (out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn')) as pool:
        futures=[pool.submit(worker,mode,jobs[k::2]) for mode in ('old_wait_new_roads','new_wait_old_roads') for k in range(2)]
        rows=[r for f in futures for r in f.result()]
    (out/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    result={}
    for mode in ('old_wait_new_roads','new_wait_old_roads'):
        group=[r for r in rows if r['mode']==mode]
        result[mode]=dict(mean_score=float(np.mean([r['trips'] for r in group])),scoring=sum(r['trips']>0 for r in group),
            versus_original=paired(group,original,('trips','road_actions','seconds')),
            versus_reset_final=paired(group,final,('trips','road_actions','seconds')))
    for label,path in MODELS.items():assert sha256(path)==config['models'][label]['sha256']
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()

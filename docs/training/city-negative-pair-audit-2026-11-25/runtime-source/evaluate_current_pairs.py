"""Frozen native pair audit; no optimizer, teacher actions or route oracle."""
import json,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from pair_audit_env import CityPairAuditEnv,CASES
from prepare_city_policy import masked_probs,sha256
from export_city_replays import frame,action_endpoints

def worker(dll,checkpoint,label,jobs,out):
    torch.set_num_threads(1);model=MaskablePPO.load(checkpoint,device='cpu')
    env=CityPairAuditEnv(dll,horizon=60,observation_horizon=600,allow_bridges=True);rows=[]
    try:
        for case,seed in jobs:
            obs,info=env.reset(options=dict(case=case,scenario_seed=seed));stock=info['road_stock'];rng=np.random.default_rng(seed+107)
            total=paid=0;first_action=None;frames=[frame(env.raw,'Start')]
            for step in range(1000):
                mask=env.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
                assert np.isfinite(p).all() and not p[~mask].any()
                action=int(rng.choice(len(p),p=p/p.sum()))
                if first_action is None:first_action=action
                before=env.raw['tripsCompleted'];old_stock=info['road_stock']
                obs,reward,terminal,truncated,info=env.step(action);total+=reward
                assert reward==env.raw['tripsCompleted']-before
                if action:paid+=old_stock-info['road_stock']
                if seed==243000000:frames.append(frame(env.raw,'Build' if action else 'Wait',action_endpoints(action) if action else None))
                if env.done:break
            else:raise RuntimeError('Pair audit decision bound exceeded')
            assert total==info['trips'] and stock-paid==info['road_stock'] and info['weekly_awards']==0
            if case!='match':assert total==0
            row=dict(model=label,case=case,seed=seed,action_seed=seed+107,initial_stock=stock,paid_units=paid,first_action=first_action,**{k:v for k,v in info.items() if k!='seed'},native_game_over=terminal,truncated=truncated)
            rows.append(row);print('PAIR',label,case,seed,'deliveries',total,'builds',info['road_actions'],'paid',paid,flush=True)
            if seed==243000000:
                data=dict(title=f'{label}: {case}',intro='Frozen current city policy on isolated native pair. Legal connections and Wait; no automatic Finish. No later arrivals in this diagnostic.',speed='8',ending='60-second audit or native game-over',frames=frames,terrain=[[i,t] for i,t in enumerate(env.raw['terrain']) if t])
                path=Path(out)/f'{label}-{case}'
                path.with_suffix('.json').write_text(json.dumps(dict(result=row,replay=data)))
                template=Path(__file__).with_name('stage1_replay.html').read_text()
                path.with_suffix('.html').write_text(template.replace('/*REPLAY_DATA*/',json.dumps(data).replace('<','\\u003c')))
        return rows
    finally:env.close()

def main():
    root=Path.cwd();arc=root/'docs/training/city-negative-pair-audit-2026-11-25';out=arc/'evaluation';out.mkdir(exist_ok=False)
    checks=json.loads((arc/'host-checks.json').read_text());dll=root/'output/pair-city-audit-build-01/artifacts/bin/TrafficHost/release/TrafficHost.dll'
    assert sha256(dll)==checks['diagnostic_sha256']
    models={'original':root/'output/training/city-whole-initial-01/start.zip','focused_final':root/'output/training/mini-fixed-route-01/training/final.zip'}
    hashes={k:sha256(p) for k,p in models.items()};jobs=[(case,seed) for case in CASES for seed in range(243000000,243000016)]
    config=dict(models={k:dict(path=str(p),sha256=hashes[k]) for k,p in models.items()},host_sha256=sha256(dll),jobs=jobs,workers=2,horizon=60,observation_horizon=600,selection='Development fixtures, first seed of each model/case replayed.',limits='Isolated no-future-arrival scenes. Zero negative-case deliveries expected; evaluate construction separately. Not a prohibition on shared roads in full cities.')
    (arc/'config.json').write_text(json.dumps(config,indent=2)+'\n');rows=[]
    with ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn')) as pool:
        for label,checkpoint in models.items():
            futures=[pool.submit(worker,str(dll),str(checkpoint),label,jobs[k::2],str(out)) for k in range(2)]
            rows += [r for f in futures for r in f.result()]
    assert len(rows)==128 and sha256(dll)==checks['diagnostic_sha256']
    assert all(sha256(p)==hashes[k] for k,p in models.items())
    (arc/'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary={}
    for label in models:
        summary[label]={}
        for case in CASES:
            g=[r for r in rows if r['model']==label and r['case']==case]
            summary[label][case]=dict(games=len(g),built=sum(r['road_actions']>0 for r in g),scoring=sum(r['trips']>0 for r in g),first_wait=sum(r['first_action']==0 for r in g),mean_paid=float(np.mean([r['paid_units'] for r in g])),mean_build_actions=float(np.mean([r['road_actions'] for r in g])))
    (arc/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

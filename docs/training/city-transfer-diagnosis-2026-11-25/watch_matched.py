from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import json
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs,sha256
from export_city_replays import frame,action_endpoints

ROOT=Path.cwd()
OUT=ROOT/'docs/training/city-transfer-diagnosis-2026-11-25'
OLD=ROOT/'docs/training/overnight-learning-2026-11-25/evaluation'
DLL=ROOT/'output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
MODELS={name:json.loads((OLD/f'city-{name}/summary.json').read_text())['checkpoint'] for name in ('original','lesson-only','mixed-city')}


def worker(case,seed,action_seed):
    torch.set_num_threads(1)
    models={k:MaskablePPO.load(v,device='cpu') for k,v in MODELS.items()}
    summaries=[]
    for name,model in models.items():
        env=CityRoadEnv(DLL,horizon=600,observation_horizon=600,allow_bridges=True)
        expected=next(json.loads(line) for line in (OLD/f'city-{name}/games.jsonl').read_text().splitlines()
                      if (json.loads(line)['seed'],json.loads(line)['action_seed'])==(seed,action_seed))
        dest=OUT/'replays'/f'{case}-{name}';dest.mkdir(parents=True,exist_ok=False)
        rng=np.random.default_rng(action_seed);steps=[];frames=[];events=[];shared=[];first_score=None
        paid=0;before_first=0;after_first_before_growth=0;native_total=0;growth_seen=False
        try:
            obs,info=env.reset(options=dict(scenario_seed=seed));known={b['id'] for b in env.raw['buildings']};terrain=[[i,k] for i,k in enumerate(env.raw['terrain']) if k]
            frames.append(frame(env.raw,'Start'));last_frame_time=0
            while not env.done:
                mask=env.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
                if mask.sum()>1 and len(steps)%8==0:
                    q=masked_probs(models['original'],obs,mask).astype(float)
                    p_cond=p[1:]/max(p[1:].sum(),1e-30);q_cond=q[1:]/max(q[1:].sum(),1e-30)
                    shared.append(dict(decision=len(steps),time=info['seconds'],score=info['trips'],stock=info['road_stock'],
                                       wait=float(p[0]),original_wait=float(q[0]),conditional_road_tv=float(np.abs(p_cond-q_cond).sum()/2)))
                action=int(rng.choice(len(p),p=p/p.sum()));before=dict(info);raw_score=env.raw['tripsCompleted']
                served_before={b['id']:b['served'] for b in env.raw['buildings'] if not b['isHouse']}
                obs,reward,t,u,info=env.step(action)
                assert reward==env.raw['tripsCompleted']-raw_score
                native_total+=reward;spent=max(0,before['road_stock']-info['road_stock']) if action else 0;paid+=spent
                if first_score is None:before_first+=spent
                elif not growth_seen:after_first_before_growth+=spent
                if reward and first_score is None:first_score=info['seconds'];events.append(dict(kind='first_delivery',time=first_score,stock=info['road_stock'],paid=paid))
                for b in env.raw['buildings']:
                    if b['id'] not in known:
                        known.add(b['id'])
                        if not b['isHouse']:
                            if first_score is not None:growth_seen=True
                            events.append(dict(kind='destination_arrival',time=info['seconds'],id=b['id'],stock=info['road_stock'],paid=paid))
                old_shop_delta=sum(max(0,b['served']-served_before.get(b['id'],0)) for b in env.raw['buildings']
                                   if not b['isHouse'] and served_before.get(b['id'],0)>0)
                steps.append(dict(action=action,time=before['seconds'],after_time=info['seconds'],reward=reward,
                                  already_served_shop_delta=old_shop_delta,score=info['trips'],stock=info['road_stock'],
                                  spent=spent,wait_probability=float(p[0]),legal_roads=int(mask[1:].sum())))
                if action or reward or info['seconds']-last_frame_time>=5 or t or u:
                    frames.append(frame(env.raw,'Build' if action else f'Wait; deliveries +{reward:g}',action_endpoints(action) if action else None));last_frame_time=info['seconds']
            for key in ('seed','seconds','trips','road_stock','road_actions','wait_actions','weekly_awards'):
                assert info[key]==expected[key],(name,key,info[key],expected[key])
            assert native_total==info['trips'] and paid==expected['paid_units']
            row=dict(case=case,model=name,seed=seed,action_seed=action_seed,score=info['trips'],first_delivery=first_score,
                     paid=paid,paid_before_first=before_first,paid_after_first_before_growth=after_first_before_growth,
                     native_reward_ledger_verified=True,exact_evaluation_replay=True,events=events,shared_states=shared)
            (dest/'steps.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in steps))
            (dest/'trace.json').write_text(json.dumps(dict(result=row,frames=frames,terrain=terrain))+'\n')
            page=dict(title=f'{case}: {name}',intro=f'Native city replay; seed{seed}, action RNG{action_seed}. Policy actions, no planner. Score{info["trips"]}.',frames=frames,terrain=terrain,speed='16',ending='City evaluation ended.')
            (dest/'replay.html').write_text((ROOT/'training/stage1_replay.html').read_text().replace('/*REPLAY_DATA*/',json.dumps(page).replace('<','\\u003c')))
            summaries.append(row);print(case,name,info['trips'],'before-first',before_first,'after-first-before-growth',after_first_before_growth,flush=True)
        finally:env.close()
    return summaries


if __name__=='__main__':
    base={};datasets={}
    for name in ('original','parent','lesson-only','mixed-city'):
        rows=[json.loads(x) for x in (OLD/f'city-{name}/games.jsonl').read_text().splitlines()];datasets[name]=rows
        if name=='original':base={(x['seed'],x['action_seed']):x for x in rows}
    ranked=sorted((x['trips']-base[(x['seed'],x['action_seed'])]['trips'],x['seed'],x['action_seed']) for x in datasets['mixed-city'])
    selected=[('largest-loss',*ranked[0][1:]),('middle',*ranked[len(ranked)//2][1:]),('largest-win',*ranked[-1][1:])]
    summary={}
    for name,rows in datasets.items():
        targets=[t for x in rows for t in x['targets']]
        summary[name]=dict(games=len(rows),zero_score=sum(x['trips']==0 for x in rows),arrivals=len(targets),
                           arrivals_with_no_stock=sum(t['arrival_stock']==0 for t in targets),served=sum(t['served']>0 for t in targets),
                           unserved_despite_arrival_stock=sum(t['served']==0 and t['arrival_stock']>0 for t in targets))
    (OUT/'selection.json').write_text(json.dumps(dict(rule='Extremes and median of mixed-city minus original score; selected before replay; illustrative, not representative estimates.',cases=selected,all_city_summary=summary,models={k:dict(path=v,sha256=sha256(Path(v))) for k,v in MODELS.items()},host_sha256=sha256(DLL)),indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=3,mp_context=mp.get_context('spawn')) as pool:
        futures=[pool.submit(worker,*job) for job in selected];results=[r for f in futures for r in f.result()]
    (OUT/'replay-summary.json').write_text(json.dumps(results,indent=2)+'\n')

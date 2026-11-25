"""Expand forced Wait ticks for exact native visual review of final successful and failed cases."""
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_repeated_mini import CityRepeatedMiniEnv
from city_recorded_starts import raw_digest
from prepare_city_policy import masked_probs,sha256
from export_city_replays import frame,action_endpoints

root=Path('docs/training/mini-fixed-route-2026-11-25');out=root/'final-replay';out.mkdir(exist_ok=False)
rows=[json.loads(s) for s in (root/'evaluation/fixed-65536/games.jsonl').read_text().splitlines()]
selected={label:min((r for r in rows if r['success']==success),key=lambda r:r['action_seed']) for label,success in [('success',True),('failure',False)]}
models={label:('output/training/mini-fixed-route-01/training/final.zip',row) for label,row in selected.items()}
(out/'selection.json').write_text(json.dumps(dict(selection='Lowest action RNG in each final success/failure group. Illustrative training-layout cases; different action draws, same checkpoint.',selected=selected),indent=2)+'\n')
torch.set_num_threads(1);checks=[]
for label,(path,expected) in models.items():
    model=MaskablePPO.load(path,device='cpu');digest=sha256(Path(path))
    dll='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
    compact=CityRepeatedMiniEnv(dll,repeat_mini_seed=expected['seed'],small_city_horizon=300,collapse_forced_wait=True,fast_small_city_tail=True)
    visual=CityRepeatedMiniEnv(dll,repeat_mini_seed=expected['seed'],small_city_horizon=300)
    try:
        obs,info=compact.reset();visual.reset();assert compact.raw==visual.raw
        frames=[frame(visual.raw,'Start')];actions=[];rng=np.random.default_rng(expected["action_seed"]);total=0;first=None;builds_after=0
        while not compact.done:
            mask=compact.action_masks();prob=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
            action=int(rng.choice(len(prob),p=prob/prob.sum()))
            if action and first is not None:builds_after+=1
            obs,reward,_,_,info=compact.step(action);total+=reward
            _,extra,_,_,_=visual.step(action)
            if extra and first is None:first=visual.raw['time']
            frames.append(frame(visual.raw,'Build' if action else 'Wait',action_endpoints(action) if action else None))
            while visual.raw['time']+1e-8<compact.raw['time']:
                assert not visual.done and visual.action_masks().sum()==1
                _,extra,_,_,_=visual.step(0)
                if extra and first is None:first=visual.raw['time']
                frames.append(frame(visual.raw,'Forced Wait'))
            assert visual.raw==compact.raw
            actions.append(dict(action=action,time=compact.raw['time'],reward=reward,raw_sha256=raw_digest(compact.raw)))
        for key,actual in [('score',total),('remaining_stock',info['road_stock']),('road_actions',info['road_actions']),('seconds',info['seconds'])]:assert expected[key]==actual,(label,key)
        assert sha256(Path(path))==digest
        data=dict(title=f'Fixed hard connection: {label}',intro='Actual sampled policy actions; forced Wait periods expanded into native ticks. Same training board; separately selected successful and failed action RNGs. No teacher actions.',speed='8',ending='Native review end',frames=frames,terrain=[[i,t] for i,t in enumerate(visual.raw['terrain']) if t])
        (out/(label+'.json')).write_text(json.dumps(dict(expected=expected,checkpoint_sha256=digest,actions=actions,replay=data)))
        template=Path('training/stage1_replay.html').read_text()
        (out/(label+'.html')).write_text(template.replace('/*REPLAY_DATA*/',json.dumps(data).replace('<','\\u003c')))
        checks.append(dict(label=label,checkpoint_sha256=digest,score=total,first_delivery=first,builds_after_first=builds_after,road_actions=info['road_actions'],all_native_boundaries_exact=True,final_metrics_exact=True))
    finally:compact.close();visual.close()
(out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2),flush=True)

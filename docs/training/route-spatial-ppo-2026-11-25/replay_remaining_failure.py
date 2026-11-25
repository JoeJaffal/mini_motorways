"""Replay declared success/failure examples from the completed outcome review."""
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_route_outcome import CityRouteOutcomeEnv
from export_city_replays import frame,action_endpoints
from prepare_city_policy import masked_probs,sha256

def read(path):return [json.loads(s) for s in path.read_text().splitlines()]

def main():
    torch.set_num_threads(1)
    r=Path('docs/training/route-spatial-run-2026-11-25')
    assert Path('output/training/route-spatial-01/training/complete.json').exists()
    assert (r/'evaluation/outcome-262144/games.jsonl').exists()
    old=read(r/'evaluation/outcome-initial/games.jsonl')
    new=read(r/'evaluation/outcome-262144/games.jsonl')
    key=lambda x:(x['exercise'],x['seed'],x['action_seed'])
    before={key(x):x for x in old}
    failures=[x for x in new if not x['task_success']]
    assert failures
    selected={'remaining-failure':min(failures,key=key)}
    out=r/'remaining-failure-replay';out.mkdir(exist_ok=False)
    paths={'parent':Path('output/training/route-spatial-01/initial/start.zip'),'candidate':Path('output/training/route-spatial-01/training/final.zip')}
    dll=Path('output/training/route-spatial-01/runtime/host/TrafficHost.dll')
    selection=dict(criterion='Lowest-key remaining final practice failure; paired parent replay. Post-result diagnostic selection, not an independent test or population estimate.',selected=selected,models={k:dict(path=str(p),sha256=sha256(p)) for k,p in paths.items()},host_sha256=sha256(dll))
    (out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    template=Path('training/stage1_replay.html').read_text()
    for label,row in selected.items():
        for name,path in paths.items():
            expected=before[key(row)] if name=='parent' else row
            model=MaskablePPO.load(path,device='cpu')
            env=CityRouteOutcomeEnv(str(dll),validation=True,fast_small_city_tail=True)
            target=out/label/name;target.mkdir(parents=True)
            try:
                obs,info=env.reset(options=dict(exercise=row['exercise'],scenario_seed=row['seed']))
                rng=np.random.default_rng(row['action_seed']);frames=[frame(env.raw,'Start')];steps=[];total=0.
                while not env.done:
                    mask=env.action_masks()
                    probs=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
                    probs=probs/probs.sum()
                    roads=probs[1:]/max(probs[1:].sum(),1e-30)
                    positive=roads[roads>0]
                    diagnostic=dict(wait_probability=float(probs[0]),conditional_road_top_probability=float(roads.max()),conditional_road_entropy=float(-(positive*np.log(positive)).sum()))
                    action=int(rng.choice(len(probs),p=probs))
                    obs,reward,terminal,truncated,info=env.step(action);total+=reward
                    frames.append(frame(env.raw,'Build' if action else 'Wait',action_endpoints(action) if action else None))
                    steps.append(dict(action=action,seconds=info['seconds'],stock=info['road_stock'],reward=reward,forced_tail=info['terminal_observation_may_follow_forced_tail'],**diagnostic))
                for field in ('task_success','task_return','paid_units','road_actions','zero_cost_builds','trips','road_stock','seconds'):
                    assert info[field]==expected[field],(label,name,field,info[field],expected[field])
                assert total==expected['task_return']
                data=dict(title=f'{label}: {name}',intro='First-delivery practice. Native forced-Wait tail may jump to a later observation; endpoint time need not be first-delivery time.',speed='8',ending='Practice success' if info['task_success'] else 'Practice failure',frames=frames,terrain=[[i,t] for i,t in enumerate(env.raw['terrain']) if t])
                (target/'trace.json').write_text(json.dumps(data))
                (target/'replay.html').write_text(template.replace('/*REPLAY_DATA*/',json.dumps(data).replace('<','\\u003c')))
                (target/'steps.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in steps))
                (target/'verification.json').write_text(json.dumps(dict(exact=True,**info),indent=2)+'\n')
            finally:env.close()
    assert all(sha256(p)==selection['models'][k]['sha256'] for k,p in paths.items())
    assert sha256(dll)==selection['host_sha256']
    print('Selected outcome replays exact; no learning.',flush=True)

if __name__=='__main__':main()

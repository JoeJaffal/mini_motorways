"""Replay preselected native evaluation games and verify final counters."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_pilot import CityRoadEnv
from export_city_replays import frame,action_endpoints
from prepare_city_policy import masked_probs,sha256

def replay(dll,checkpoint,output,label,expected,horizon,comparisons):
    torch.set_num_threads(1);model=MaskablePPO.load(checkpoint,device='cpu')
    others={k:MaskablePPO.load(v,device='cpu') for k,v in comparisons.items()}
    env=CityRoadEnv(dll,horizon=horizon,observation_horizon=600,allow_bridges=True)
    output.mkdir(exist_ok=False,parents=True);rng=np.random.default_rng(expected['action_seed'])
    try:
        obs,info=env.reset(options=dict(scenario_seed=expected['seed']));frames=[frame(env.raw,'Start')];steps=[];total=0;last=0
        while not env.done:
            mask=env.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
            wait_probs={k:float(masked_probs(m,obs,mask)[0]) for k,m in others.items()}
            before=dict(seconds=env.raw.get('elapsedSeconds'),stock=env.raw.get('roadStock'),trips=env.raw['tripsCompleted'])
            action=int(rng.choice(len(p),p=p/p.sum()));score=env.raw['tripsCompleted']
            obs,reward,terminal,truncated,info=env.step(action);total+=reward
            assert reward==env.raw['tripsCompleted']-score
            steps.append(dict(action=action,time=info['seconds'],reward=reward,stock=info['road_stock'],wait_probs=wait_probs,before=before))
            if action or reward or info['seconds']-last>=5 or env.done:
                frames.append(frame(env.raw,'Build' if action else 'Wait',action_endpoints(action) if action else None));last=info['seconds']
        assert total==info['trips']
        for key in ('seed','seconds','trips','road_stock','road_actions','wait_actions','weekly_awards','bridge_stock','bridge_tiles'):
            assert info[key]==expected[key],(key,info[key],expected[key])
        assert terminal==expected['native_game_over'] and truncated==expected['truncated']
        data=dict(title=f'{label}: {info["trips"]} native deliveries',intro=f'Seed {expected["seed"]}; frozen checkpoint {Path(checkpoint).name}, up to {horizon} seconds.',speed='16',ending='Native game-over' if terminal else 'Evaluation horizon',frames=frames,terrain=[[i,t] for i,t in enumerate(env.raw['terrain']) if t])
        (output/'trace.json').write_text(json.dumps(data));(output/'final-state.json').write_text(json.dumps(env.raw));(output/'steps.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in steps))
        template=(Path.cwd()/'training/stage1_replay.html').read_text()
        (output/'replay.html').write_text(template.replace('/*REPLAY_DATA*/',json.dumps(data).replace('<','\\u003c')))
        result=dict(label=label,exact=True,**info);(output/'verification.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
        return result
    finally:env.close()


if __name__=='__main__':
    root=Path('docs/training/build-wait-continuation-2026-11-25/city-regression-replay')
    config=json.loads((root/'selection.json').read_text())
    data=json.loads((root/'wait32k/trace.json').read_text())
    template=Path('training/stage1_replay.html').read_text()
    (root/'wait32k/replay.html').open('x').write(template.replace('/*REPLAY_DATA*/',json.dumps(data).replace('<','\\u003c')))
    (root/'wait32k/verification.json').open('x').write(json.dumps(dict(exact=True,**config['expected']['wait32k'],recovery='All native counter assertions passed before template path failure; recovered saved trace without rerunning.'),indent=2))
    paths={k:v['path'] for k,v in config['models'].items()}
    replay('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',paths['wait98k'],root/'wait98k','wait98k',config['expected']['wait98k'],600,paths)

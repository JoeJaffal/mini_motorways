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

def replay(dll,checkpoint,output,label,expected,horizon):
    torch.set_num_threads(1);model=MaskablePPO.load(checkpoint,device='cpu')
    env=CityRoadEnv(dll,horizon=horizon,observation_horizon=600,allow_bridges=True)
    output.mkdir(exist_ok=False,parents=True);rng=np.random.default_rng(expected['action_seed'])
    try:
        obs,info=env.reset(options=dict(scenario_seed=expected['seed']));frames=[frame(env.raw,'Start')];steps=[];total=0;last=0
        while not env.done:
            mask=env.action_masks();p=mask.astype(float) if mask.sum()==1 else masked_probs(model,obs,mask).astype(float)
            action=int(rng.choice(len(p),p=p/p.sum()));score=env.raw['tripsCompleted']
            obs,reward,terminal,truncated,info=env.step(action);total+=reward
            assert reward==env.raw['tripsCompleted']-score
            steps.append(dict(action=action,time=info['seconds'],reward=reward,stock=info['road_stock']))
            if action or reward or info['seconds']-last>=5 or env.done:
                frames.append(frame(env.raw,'Build' if action else 'Wait',action_endpoints(action) if action else None));last=info['seconds']
        assert total==info['trips']
        for key in ('seed','seconds','trips','road_stock','road_actions','wait_actions','weekly_awards','bridge_stock','bridge_tiles'):
            assert info[key]==expected[key],(key,info[key],expected[key])
        assert terminal==expected['native_game_over'] and truncated==expected['truncated']
        data=dict(title=f'{label}: {info["trips"]} native deliveries',intro=f'Seed {expected["seed"]}; frozen original, up to {horizon} seconds.',speed='16',ending='Native game-over' if terminal else 'Evaluation horizon',frames=frames,terrain=[[i,t] for i,t in enumerate(env.raw['terrain']) if t])
        (output/'trace.json').write_text(json.dumps(data));(output/'final-state.json').write_text(json.dumps(env.raw));(output/'steps.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in steps))
        template=(Path(__file__).resolve().parent/'stage1_replay.html').read_text()
        (output/'replay.html').write_text(template.replace('/*REPLAY_DATA*/',json.dumps(data).replace('<','\\u003c')))
        result=dict(label=label,exact=True,**info);(output/'verification.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
        return result
    finally:env.close()

def main():
    p=argparse.ArgumentParser()
    for name in ('dll','checkpoint','evaluation','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--horizon',type=int,default=1800);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
    rows=[json.loads(l) for l in (a.evaluation/'games.jsonl').read_text().splitlines()];mean=np.mean([r['trips'] for r in rows])
    selected=dict(best=max(rows,key=lambda r:r['trips']),typical=min(rows,key=lambda r:abs(r['trips']-mean)),worst=min(rows,key=lambda r:(r['trips'],r['seconds'])))
    before=sha256(a.checkpoint);(a.output/'selection.json').write_text(json.dumps(dict(checkpoint_sha256=before,host_sha256=sha256(a.dll),criterion='Maximum score, closest to mean score, minimum score then shortest survival.',games=selected),indent=2))
    with ProcessPoolExecutor(max_workers=3,mp_context=mp.get_context('spawn')) as pool:
        results=[f.result() for f in [pool.submit(replay,a.dll,a.checkpoint,a.output/label,label,row,a.horizon) for label,row in selected.items()]]
    assert sha256(a.checkpoint)==before
    (a.output/'summary.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__':main()

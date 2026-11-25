"""Export a NEW frozen-checkpoint game as a standalone visual replay. No training.

The first pilot did not record exact action traces; this cannot recover those
historical training games. It runs the saved policy with updates disabled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import webbrowser

import torch
from connection_practice import ConnectionPractice
from edge_policy import checkpoint_policy
from hierarchy_checkpoint import load_checkpoint
from hierarchy_rollout import policy_fingerprint
from practice_replay import PracticeRecorder,identity

ROOT=Path(__file__).resolve().parents[1]


def frame(env,description):
    o=env.raw
    return dict(practice_bounds=env.practice_bounds,time=o['time'],score=o['tripsCompleted'],role=env.role,focus=env.focus,
        description=description,connections=[[i,v] for i,v in enumerate(o['connections']) if v],
        buildings=[{k:b[k] for k in ('cell','width','height','color','isHouse','demand')} for b in o['buildings']],
        cars=[{k:v[k] for k in ('x','y','color')} for v in o['vehicles'] if v['visible']])


def export_game(checkpoint,output,*,dotnet='dotnet',dll=None,seed=42,max_tokens=4096,sample=False):
    if max_tokens<1:raise ValueError('Positive token bound required')
    output=Path(output)
    if output.exists() or output.with_suffix('.json').exists():raise FileExistsError('Choose a new replay output name')
    # Only load your own trusted local checkpoints (pickle-based format).
    config=torch.load(checkpoint,map_location='cpu',weights_only=False)['config']
    env=ConnectionPractice(dotnet=dotnet,host_dll=dll,stage=config.get('stage','clear'),reward_mode=config.get('reward_mode','score'))
    try:
        if config['environment']!=identity(env):raise ValueError('Checkpoint environment/source/build differs')
        expected=config['source_hashes']['hierarchy_policy.py']
        if hashlib.sha256((ROOT/'training/hierarchy_policy.py').read_bytes()).hexdigest()!=expected:
            raise ValueError('Checkpoint policy code differs')
        policy=checkpoint_policy(env, lambda _: 0., config)
        load_checkpoint(checkpoint,policy,expected_config=config)
        policy.set_training_mode(False)
        before=policy_fingerprint(policy)
        recorder=PracticeRecorder(env,seed=seed);obs=recorder.initial_observation
        frames=[frame(env,'Initial practice layout')]
        print('Generating a frozen-checkpoint replay; no learning or weight updates.',flush=True)
        for n in range(max_tokens):
            action,_=policy.predict(obs,deterministic=not sample,action_masks=env.action_masks())
            obs,_,terminated,truncated,info=recorder.step(action)
            frames.append(frame(env,recorder.trace['tokens'][-1]['description']))
            if (n+1)%100==0:print(f'Replay: {n+1} decisions | game {info["seconds"]:.1f}s | trips {info["trips"]}',flush=True)
            if terminated or truncated:break
        if policy_fingerprint(policy)!=before:raise RuntimeError('Frozen playback changed weights')
        recorder.trace.update(origin='new frozen-checkpoint game, not the original training trajectory',
            policy_sha256=before,deterministic=not sample)
        output.parent.mkdir(parents=True,exist_ok=True)
        recorder.save(output.with_suffix('.json'))
        ending=recorder.trace['ending_reason'] if env.done else 'external decision limit — incomplete game'
        data=dict(frames=frames,ending=ending,seed=seed,origin=recorder.trace['origin'])
        template=(ROOT/'training/stage1_replay.html').read_text()
        encoded=json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c')
        output.write_text(template.replace('/*REPLAY_DATA*/',encoded))
        print(f'Saved {output}: {len(frames)-1} decisions, {env.raw["tripsCompleted"]} trips, {ending}',flush=True)
        return output
    finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True)
    p.add_argument('--dotnet',default='dotnet');p.add_argument('--dll',default='simulation/Headless/bin/Release/net8.0/TrafficHost.dll')
    p.add_argument('--seed',type=int,default=42);p.add_argument('--max-tokens',type=int,default=4096)
    p.add_argument('--sample',action='store_true');p.add_argument('--no-open',action='store_true')
    a=p.parse_args();torch.set_num_threads(2)
    path=export_game(a.checkpoint,a.output,dotnet=a.dotnet,dll=a.dll,seed=a.seed,max_tokens=a.max_tokens,sample=a.sample)
    if not a.no_open:webbrowser.open(path.resolve().as_uri())

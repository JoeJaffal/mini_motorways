"""Frozen seed5009 diagnosis: traced policies and fixed-command counterfactuals."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import hashlib
import json
from pathlib import Path
import torch
from sb3_contrib import MaskablePPO
from environment import ROOT,TrafficEnv
from train_goal import model_environment


def summary(e):
    o=e.raw;cars=o['vehicles']
    shops=[dict(id=b['id'],color=b['color'],cell=b['cell'],demand=b['demand'],reserved=b['reserved'],
                capacity=b['demandCapacity'],overcrowded=round(b['overcrowdedFor'],3),
                parked=sum(x>=0 for x in b['parking'])) for b in o['buildings'] if not b['isHouse']]
    return dict(time=o['time'],trips=o['tripsCompleted'],failed=o['failed'],inventory=o['inventory'],
        shops=shops,obstacles=dict(Counter(v['obstacle'] for v in cars if v.get('stage')!='Home')),
        signals=o['signals'],waiting_cars=[{k:v[k] for k in ['id','homeId','shopId','color','stage','x','y','waiting','speed','obstacle']}
            for v in cars if v['waiting']>=3],
        network_sha256=hashlib.sha256(json.dumps([o['infrastructure'],o['connections']]).encode()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Fresh diagnosis folder required')
    a.output.mkdir(parents=True);torch.set_num_threads(2)
    checkpoint=ROOT/'output/training/signals-night-01/validation-best.zip'
    checksum=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    expected=json.loads((ROOT/'output/experiments/lights-test-01/comparison.json').read_text())
    if checksum!=expected['checkpoint_sha256']:raise RuntimeError('Selected checkpoint differs from paired test')
    (a.output/'protocol.json').write_text(json.dumps(dict(seed=5009,checkpoint_sha256=checksum,no_training=True,
        diagnostic='Repeat ON/OFF to capture every ordinary command; replay ON commands with each/all light builds replaced by equal-time waits. Counterfactual commands are fixed, not optimized.',
        limits='Single exposed failure case; command-fixed counterfactuals separate physical light effects from planner feedback, not generalization evidence.'),indent=2)+'\n')
    def trace(disabled):
        name='off' if disabled else 'on'
        model=MaskablePPO.load(checkpoint,device='cpu')
        before=[v.detach().clone() for v in model.policy.parameters()]
        env=model_environment(model,dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),seconds=3600,
            skip_forced_wait=getattr(model,'skip_forced_wait',False))
        env.disable_light_actions=disabled;states=[];decisions=[];snapshots={}
        try:
            obs,_=env.reset(seed=5009,options={'scenario_seed':5009})
            original=env.base._advance
            def advance(request=None):
                pre=summary(env.base);result=original(request);post=summary(env.base)
                states.append(dict(command=request or dict(command='wait'),before=pre,after=post))
                if request and request.get('tool')=='TrafficLight':
                    o=env.base.raw
                    snapshots[f'light-{len(snapshots)}']={k:o[k] for k in ['time','infrastructure','connections','terrain','buildings','vehicles','signals','inventory']}
                return result
            env.base._advance=advance
            while True:
                action=int(model.predict(obs,deterministic=True,action_masks=env.action_masks())[0])
                decisions.append(dict(time=env.base.raw['time'],action=action,command_index=len(states)))
                obs,_,term,trunc,info=env.step(action)
                if term or trunc:break
            if not all(torch.equal(x,y) for x,y in zip(before,model.policy.parameters())):raise RuntimeError('Weights changed')
            replay=env.export_replay();replay['source']='hybrid-evaluation'
            (a.output/f'{name}-replay.json').write_text(json.dumps(replay,indent=2)+'\n')
            (a.output/f'{name}-trace.json').write_text(json.dumps(states,indent=2)+'\n')
            (a.output/f'{name}-decisions.json').write_text(json.dumps(decisions,indent=2)+'\n')
            (a.output/f'{name}-light-snapshots.json').write_text(json.dumps(snapshots,indent=2)+'\n')
            print(f'TRACE {name} | {info["trips"]} trips | {info["seconds"]:.1f}s | {info.get("signals_placed")} lights',flush=True)
            return states,replay
        finally:env.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(trace,disabled) for disabled in [False,True]]
        (on,on_replay),(off,off_replay)=[f.result() for f in futures]
    if (on_replay['score'],off_replay['score'])!=(279,475):raise RuntimeError('Diagnosis did not reproduce original test')
    first=next(i for i,(x,y) in enumerate(zip(on,off)) if x['command']!=y['command'])
    lights=[i for i,x in enumerate(on) if x['command'].get('tool')=='TrafficLight']
    counterfactuals=[]
    for omitted in [[i] for i in lights]+[lights]:
        e=TrafficEnv(dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),seconds=3600,record_replays=True,observation_mode='connectivity')
        states=[]
        try:
            e.reset(seed=5009,options={'scenario_seed':5009})
            for i,row in enumerate(on):
                req=row['command']
                e._advance(None if i in omitted or req['command']=='wait' else req)
                if i%10==0 or e.done:states.append(summary(e))
                if e.done:break
            # No further road decisions: after the recorded command horizon,
            # only wait to see if the existing network survives longer.
            while not e.done:
                e._advance()
                if e.commands%10==0 or e.done:states.append(summary(e))
            label='omit-'+'-'.join(map(str,omitted))
            replay=e.export_replay();replay['source']='fixed-command-counterfactual'
            (a.output/f'{label}-replay.json').write_text(json.dumps(replay,indent=2)+'\n')
            (a.output/f'{label}-trace.json').write_text(json.dumps(states,indent=2)+'\n')
            counterfactuals.append(dict(omitted_commands=omitted,score=e.raw['tripsCompleted'],seconds=e.raw['time'],
                rejected=e.rejected,final=states[-1],note='ON command schedule held fixed, then waits only; model not called'))
            print(f'COUNTERFACTUAL {label} | {e.raw["tripsCompleted"]} trips | {e.raw["time"]:.1f}s',flush=True)
        finally:e.close()
    result=dict(checkpoint_sha256=checksum,weights_unchanged=True,first_difference_index=first,
        first_difference_on=on[first],first_difference_off=off[first],
        lights=[dict(command_index=i,command=on[i]['command'],before=on[i]['before'],after=on[i]['after']) for i in lights],
        on_final=on[-1]['after'],off_final=off[-1]['after'],counterfactuals=counterfactuals)
    (a.output/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    print('DIAGNOSIS | first differing command',first,'| light commands',lights,flush=True)


if __name__=='__main__':main()

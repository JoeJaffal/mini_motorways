"""Paired frozen-policy traffic-light availability test; never trains."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from environment import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,default=ROOT/'output/training/signals-night-01/validation-best.zip')
    p.add_argument('--seed-start',type=int,default=5000)
    p.add_argument('--count',type=int,default=10)
    p.add_argument('--cap',type=int,default=3600)
    a=p.parse_args()
    if a.output.exists():p.error('Choose a new output folder; previous results are preserved')
    if a.count<1 or a.cap<1:p.error('Positive map count and simulated cap required')
    checkpoint=a.checkpoint.resolve();sha=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    a.output.mkdir(parents=True)
    protocol=dict(created_utc=datetime.now(timezone.utc).isoformat(),checkpoint=str(checkpoint),sha256=sha,
        seeds=list(range(a.seed_start,a.seed_start+a.count)),mode='deterministic',cap=a.cap,
        intervention='Mask only light placement actions; keep proposed light observations, simulator rules and weights unchanged',
        no_training=True,limitations='Tests light availability for this policy, including changed future routes/upgrades; not an optimal no-light agent or isolated junction throughput test')
    protocol['source_sha256']={n:hashlib.sha256((ROOT/'training'/n).read_bytes()).hexdigest() for n in
        ['compare_traffic_lights.py','evaluate_checkpoint.py','signal_agent.py','goal_agent.py','train_goal.py','environment.py','planner_diagnostic.py']}
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    def run(disabled):
        name='lights-off' if disabled else 'lights-on'
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=sha:raise RuntimeError('Checkpoint changed')
        cmd=[sys.executable,str(ROOT/'training/evaluate_checkpoint.py'),'--checkpoint',str(checkpoint),
            '--output',str(a.output/f'{name}.json'),'--seed-start',str(a.seed_start),'--seed-count',str(a.count),
            '--cap',str(a.cap),'--best-replay',str(a.output/f'{name}-replay.json')]
        if disabled:cmd.append('--disable-traffic-lights')
        with (a.output/f'{name}.txt').open('w') as log,(a.output/f'{name}-stderr.txt').open('w') as err:
            process=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=err,text=True)
            for line in process.stdout:log.write(line);log.flush();print(f'{name} | {line.strip()}',flush=True)
            if process.wait():raise RuntimeError(f'{name} failed; inspect stderr')
        data=json.loads((a.output/f'{name}.json').read_text())
        if not data['weights_unchanged'] or data['checkpoint_sha256']!=sha:raise RuntimeError('Policy mismatch/mutation')
        if disabled and any(r.get('signals_placed',0) for r in data['results']):raise RuntimeError('Disabled policy placed lights')
        return data
    print(f'LIGHT TEST | {a.count} maps x two conditions | frozen policy; no training',flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,disabled) for disabled in [False,True]]
        on,off=[f.result() for f in futures]
    rows=[]
    for x,y in zip(on['results'],off['results']):
        if x['scenario_seed']!=y['scenario_seed']:raise RuntimeError('Map mismatch')
        rows.append(dict(seed=x['scenario_seed'],on=x['trips'],off=y['trips'],difference=x['trips']-y['trips']))
    result=dict(lights_on_mean=on['mean_trips'],lights_off_mean=off['mean_trips'],
        mean_car_wait_on=sum(r['mean_car_wait'] for r in on['results'])/a.count,
        mean_car_wait_off=sum(r['mean_car_wait'] for r in off['results'])/a.count,
        better_with_lights=sum(r['difference']>0 for r in rows),ties=sum(r['difference']==0 for r in rows),
        worse_with_lights=sum(r['difference']<0 for r in rows),paired_scores=rows,
        weights_unchanged=True,waiting_limit='Descriptive episode averages; different survival/load can confound waiting',
        checkpoint_sha256=sha)
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=sha:raise RuntimeError('Checkpoint changed during test')
    (a.output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'COMPARISON | lights ON {on["mean_trips"]:.1f} vs OFF {off["mean_trips"]:.1f} trips | '
          f'better/tied/worse {result["better_with_lights"]}/{result["ties"]}/{result["worse_with_lights"]}',flush=True)
    print(f'Results: {a.output}/comparison.json',flush=True)


if __name__=='__main__':main()

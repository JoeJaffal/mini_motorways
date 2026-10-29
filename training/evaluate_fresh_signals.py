"""Predeclared fresh-map comparison of the selected signal policy; no training."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run',type=Path,default=Path('output/training/signals-night-01'))
    p.add_argument('--seed-start',type=int,default=4000)
    p.add_argument('--count',type=int,default=10)
    a=p.parse_args()
    if a.output.exists():p.error('Fresh output directory required; never overwrite a test')
    if a.count<1:p.error('Positive map count required')
    run=(ROOT/a.run).resolve()
    selected=json.loads((run/'validation-best.json').read_text())
    host=ROOT/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'
    checkpoints={k:dict(path=str((run/name).relative_to(ROOT)),sha256=digest(run/name))
        for k,name in [('initial','initial.zip'),('selected','validation-best.zip')]}
    protocol=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        selection='Run development validation-best selected before fresh tests; initial same-run baseline. No latest/best-training selection.',
        selected_development=selected,checkpoints=checkpoints,seeds=list(range(a.seed_start,a.seed_start+a.count)),
        primary='deterministic',secondary='sampled, one trajectory per map; common RNG seed 43 + scenario offset',
        cap_seconds=3600,city='LosAngeles',version='OriginalReference',workers_per_policy=1,max_concurrent_jobs=2,
        no_tuning_after_results=True,no_training=True,host_sha256=digest(host),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={name:digest(ROOT/'training'/name) for name in
            ['evaluate_checkpoint.py','goal_agent.py','signal_agent.py','train_goal.py','environment.py','planner_diagnostic.py']})
    a.output.mkdir(parents=True)
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    print(f'FROZEN PROTOCOL | seeds {a.seed_start}-{a.seed_start+a.count-1} | {4*a.count} games | initial vs validation-selected | no updates/reselection',flush=True)
    start=time.perf_counter()
    jobs=[(key,mode) for mode in ['deterministic','sampled'] for key in ['initial','selected']]
    def evaluate(job):
        key,mode=job;name=f'{key}-{mode}';checkpoint=ROOT/checkpoints[key]['path']
        if digest(checkpoint)!=checkpoints[key]['sha256'] or digest(host)!=protocol['host_sha256']:
            raise RuntimeError('Frozen checkpoint or runtime changed')
        cmd=[sys.executable,str(ROOT/'training/evaluate_checkpoint.py'),'--checkpoint',str(checkpoint),
             '--output',str(a.output/f'{name}.json'),'--seed-start',str(a.seed_start),'--seed-count',str(a.count),
             '--mode',mode,'--rng-seed','43','--cap','3600','--host-dll',str(host),
             '--best-replay',str(a.output/f'{name}-replay.json')]
        with (a.output/f'{name}.txt').open('w') as log,(a.output/f'{name}-stderr.txt').open('w') as err:
            process=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=err,text=True)
            for line in process.stdout:
                log.write(line);log.flush()
                if line.startswith('EVAL |') or line.startswith('RESULT |'):print(f'{name} | {line.strip()}',flush=True)
            if process.wait():raise RuntimeError(f'{name} failed; inspect stderr')
        report=json.loads((a.output/f'{name}.json').read_text())
        if not report['weights_unchanged'] or report['checkpoint_sha256']!=checkpoints[key]['sha256']:
            raise RuntimeError('Unexpected policy mutation or checkpoint mismatch')
        return name
    with ThreadPoolExecutor(max_workers=2) as pool:
        for finished in as_completed([pool.submit(evaluate,j) for j in jobs]):finished.result()
    results={}
    for mode in ['deterministic','sampled']:
        initial=json.loads((a.output/f'initial-{mode}.json').read_text())
        trained=json.loads((a.output/f'selected-{mode}.json').read_text())
        rows=[]
        for i,t,seed in zip(initial['results'],trained['results'],protocol['seeds']):
            if i['scenario_seed']!=seed or t['scenario_seed']!=seed:raise RuntimeError('Paired map mismatch')
            rows.append(dict(seed=seed,initial=i['trips'],selected=t['trips'],difference=t['trips']-i['trips'],
                initial_truncated=i['truncated'],selected_truncated=t['truncated']))
        results[mode]=dict(initial_mean=initial['mean_trips'],selected_mean=trained['mean_trips'],
            mean_difference=trained['mean_trips']-initial['mean_trips'],
            wins=sum(x['difference']>0 for x in rows),ties=sum(x['difference']==0 for x in rows),
            losses=sum(x['difference']<0 for x in rows),paired_scores=rows)
    for item in checkpoints.values():
        if digest(ROOT/item['path'])!=item['sha256']:raise RuntimeError('Checkpoint file changed during evaluation')
    report=dict(completed_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-start,
        protocol_sha256=digest(a.output/'protocol.json'),weights_unchanged=True,results=results,
        limits=f'{a.count} fresh maps, one training replicate; secondary sampling is one trajectory per seed. No tuning/reselection after these results.')
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print('ASSESSMENT '+json.dumps(results),flush=True)


if __name__=='__main__':main()

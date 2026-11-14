"""Run the predeclared frozen tests after development-only candidate selection."""
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--host-dll',type=Path,required=True);p.add_argument('--jobs',type=int,choices=[1,2],default=2)
    a=p.parse_args();selection=json.loads(a.selection.read_text())
    if a.output.exists():p.error('Fresh final-test directory required')
    if selection['test_seeds']!=list(range(3000,3010)):p.error('Unexpected reserved test partition')
    for key in ['primitive','goal_initial','goal_trained']:
        c=selection[key];actual=hashlib.sha256((ROOT/c['checkpoint']).read_bytes()).hexdigest()
        if actual!=c['sha256']:raise RuntimeError(f'Checkpoint changed after selection: {key}')
    a.output.mkdir(parents=True)
    jobs=[('old-baseline','output/training/multi-seed-shaped-01/final.zip','deterministic'),
          ('informed-initial','output/training/informed-spatial-20261028/initial.zip','deterministic'),
          ('primitive-selected',selection['primitive']['checkpoint'],'deterministic'),
          ('goal-initial',selection['goal_initial']['checkpoint'],'deterministic'),
          ('goal-trained',selection['goal_trained']['checkpoint'],'deterministic'),
          ('goal-initial-sampled',selection['goal_initial']['checkpoint'],'sampled'),
          ('goal-trained-sampled',selection['goal_trained']['checkpoint'],'sampled')]
    start=time.perf_counter()
    def run(job):
        key,checkpoint,mode=job
        command=[sys.executable,str(ROOT/'training/evaluate_checkpoint.py'),'--checkpoint',str(ROOT/checkpoint),
                 '--output',str(a.output/f'{key}.json'),'--seed-start','3000','--seed-count','10',
                 '--mode',mode,'--rng-seed','43','--cap','3600','--host-dll',str(a.host_dll.resolve()),
                 '--best-replay',str(a.output/f'{key}-replay.json')]
        with (a.output/f'{key}.log').open('w') as out,(a.output/f'{key}.err').open('w') as err:
            result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,timeout=300)
        if result.returncode:raise RuntimeError(f'{key} failed; inspect its .err log')
        report=json.loads((a.output/f'{key}.json').read_text())
        if not report['weights_unchanged']:raise RuntimeError('Frozen inference mutated weights')
        print(f"FINAL TEST | {key} | mean {report['mean_trips']:.2f} | best {report['best_trips']} | no updates",flush=True)
        return dict(key=key,checkpoint_sha256=report['checkpoint_sha256'],mean_trips=report['mean_trips'],mode=mode)
    results=[]
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for done in as_completed([pool.submit(run,job) for job in jobs]):results.append(done.result())
    record=dict(completed_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-start,
                selection_sha256=hashlib.sha256(a.selection.read_bytes()).hexdigest(),results=results,
                note='Inference only; no optimizer updates or candidate reselection after test results.')
    (a.output/'complete.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()

"""Bounded sequential learners plus frozen development evaluations and archives."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor


def dump(path, data):
    pending = path.with_suffix(path.suffix+'.pending')
    pending.write_text(json.dumps(data,indent=2)+'\n'); pending.replace(path)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True)
    a=p.parse_args(); root=Path.cwd(); out=a.output.absolute(); archive=a.archive.absolute()
    source=out/'runtime/training'; source.mkdir(parents=True,exist_ok=False)
    for path in (root/'training').glob('*.py'):shutil.copy2(path,source/path.name)
    shutil.copytree(source,archive/'runtime-source')
    host=out/'runtime/host'
    shutil.copytree(root/'output/road-cost-reward-build-02/bin/TrafficHost/release',host)
    evaluation=source/'evaluate_road_cost_frozen.py'
    old=root/'docs/training/road-cost-reward-2026-11-24/evaluate.py'
    text=old.read_text().replace("DLL='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'",'DLL='+repr(str(host/'TrafficHost.dll')))
    evaluation.write_text(text);shutil.copy2(evaluation,archive/'runtime-source'/evaluation.name)
    env=dict(os.environ,PYTHONPATH=str(source))
    state=dict(status='running',pid=os.getpid(),started=datetime.datetime.now().astimezone().isoformat(),
               target_decisions_per_arm=262144,evaluation='Development suite, not fresh confirmation')
    def publish():
        dump(out/'status.json',state);dump(archive/'status.json',state)
    def copy_small(arm):
        dest=archive/'measurements'/arm;dest.mkdir(parents=True,exist_ok=True)
        for name in ('config.json','checkpoints.json','status.json','progress.csv','episodes.jsonl','gradient_audit.jsonl','parameter_updates.jsonl','complete.json'):
            path=out/arm/name
            if path.exists():shutil.copy2(path,dest/name)
    def evaluate(arm,budget):
        dest=out/'evaluation'/f'{arm}-{budget}'
        args=[sys.executable,'-u',str(evaluation),'--checkpoint',str(out/arm/f'checkpoint-{budget:09d}.zip'),'--output',str(dest)]
        dump(archive/f'eval-{arm}-{budget}-command.json',args)
        with (out/f'eval-{arm}-{budget}.log').open('x') as log:
            subprocess.run(args,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        archived=archive/'evaluation'/f'{arm}-{budget}';shutil.copytree(dest,archived)
        summary=json.loads((dest/'summary.json').read_text())
        print('EVALUATION',arm,budget,json.dumps(summary['results']),flush=True)
        return dict(arm=arm,budget=budget,**summary)
    protected={}
    for arm in ('control','strong'):
        parent=root/'output/training/road-cost-reward-fit-01'/arm/'final.zip'
        protected[str(parent)]=hashlib.sha256(parent.read_bytes()).hexdigest()
    dump(archive/'protected-inputs.json',protected)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures=[]
            for arm,cost in [('control',0.),('strong',.04)]:
                state.update(phase='training',arm=arm);publish()
                args=[sys.executable,'-u',str(source/'continue_road_cost_trial.py'),
                      '--parent',str(root/'output/training/road-cost-reward-fit-01'/arm/'final.zip'),
                      '--dll',str(host/'TrafficHost.dll'),'--output',str(out/arm),
                      '--road-cost',str(cost),'--seed-start','208000000']
                dump(archive/f'{arm}-command.json',args)
                process=subprocess.Popen(args,cwd=root,env=env)
                queued=set()
                while process.poll() is None:
                    copy_small(arm)
                    for budget in (65536,131072,262144):
                        # The atomic checkpoint is complete before the status is published.
                        path=out/arm/f'checkpoint-{budget:09d}.zip'
                        if path.exists() and budget not in queued:
                            futures.append(pool.submit(evaluate,arm,budget));queued.add(budget)
                    time.sleep(10)
                copy_small(arm)
                if process.returncode:raise RuntimeError(f'{arm} exited {process.returncode}')
                for budget in (65536,131072,262144):
                    if budget not in queued:futures.append(pool.submit(evaluate,arm,budget))
            state.update(phase='evaluation',arm='both');publish()
            results=[f.result() for f in futures]
        dump(archive/'evaluation-results.json',results)
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
        subprocess.run([sys.executable,str(source/'summarize_road_cost_continuation.py'),'--archive',str(archive)],
                       cwd=root,env=env,check=True)
        with (root/'training/EXPERIMENT_HISTORY.md').open('a') as f:
            f.write('\n\n## 25 November 2026 — matched road-cost continuation completed\n\nBoth arms reached262144cumulative decisions; six128-game development evaluations completed. [Archived results](../docs/training/'+archive.name+'/RESULTS.md). One training seed, no automatic promotion or city-transfer claim. Review curves and paired intervals before choosing further training.\n')
        state.update(status='complete',phase='finished',finished=datetime.datetime.now().astimezone().isoformat());publish()
        print('COMPLETE: both arms reached262144 decisions; six development evaluations archived. No candidate automatically promoted.',flush=True)
    except BaseException as exc:
        state.update(status='error',error=repr(exc));publish();raise
    finally:
        manifest={str(p.relative_to(archive)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in archive.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts}
        dump(archive/'manifest.json',manifest)


if __name__=='__main__':main()

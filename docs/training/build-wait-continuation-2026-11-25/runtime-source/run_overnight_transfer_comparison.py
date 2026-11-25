"""One predeclared task-mix comparison; bounded training, then city retention."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import os
import signal
from pathlib import Path
import shutil
import subprocess
import sys
import time


def dump(path,data):
    temp=path.with_suffix(path.suffix+'.pending')
    temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(path)


def stop_owned_tree(process):
    """Stop this launched learner and its descendants only, never other training."""
    parents={}
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            try:parents[int(path.name)]=int((path/'stat').read_text().rsplit(')',1)[1].split()[1])
            except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    owned=[process.pid]
    for pid in owned:
        owned.extend(child for child,parent in parents.items() if parent==pid and child not in owned)
    for pid in reversed(owned):
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
    process.wait(timeout=30)


def main():
    p=argparse.ArgumentParser()
    for name in ('parent','output','archive'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path.cwd();out=a.output.absolute();archive=a.archive.absolute()
    source=out/'runtime/training';source.mkdir(parents=True,exist_ok=False)
    for path in (root/'training').glob('*.py'):shutil.copy2(path,source/path.name)
    host=out/'runtime/host';shutil.copytree(root/'output/road-cost-reward-build-02/bin/TrafficHost/release',host)
    evaluator=source/'evaluate_road_cost_frozen.py'
    text=(root/'docs/training/road-cost-reward-2026-11-24/evaluate.py').read_text()
    evaluator.write_text(text.replace("DLL='output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'",'DLL='+repr(str(host/'TrafficHost.dll'))))
    shutil.copytree(source,archive/'runtime-source')
    env=dict(os.environ,PYTHONPATH=str(source));parent=a.parent.absolute()
    original=root/'output/training/city-whole-initial-01/start.zip'
    protected={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (parent,original)}
    dump(archive/'protected-inputs.json',protected)
    state=dict(status='running',pid=os.getpid(),started=datetime.datetime.now().astimezone().isoformat(),
               parent=str(parent),completed_decisions=262144,target_decisions=524288,
               intervention='Lesson-only versus half-city worker mix; same parent, actor/critic settings and practice cost.04; city reward is native deliveries')
    def publish():
        dump(out/'status.json',state);dump(archive/'status.json',state)
    def copy_metrics(arm):
        dest=archive/'measurements'/arm;dest.mkdir(parents=True,exist_ok=True)
        for pattern in ('*.json','*.jsonl','*.csv'):
            for path in (out/arm).glob(pattern):shutil.copy2(path,dest/path.name)
    def evaluate(kind,label,checkpoint):
        dest=out/'evaluation'/f'{kind}-{label}'
        precheck=archive/f'precheck-city-{label}'
        if kind=='city' and label in ('original','parent') and (precheck/'summary.json').exists():
            record=json.loads((precheck/'summary.json').read_text())
            assert record['sha256']==hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest()
            assert record['host_sha256']==hashlib.sha256((host/'TrafficHost.dll').read_bytes()).hexdigest()
            shutil.copytree(precheck,dest);shutil.copytree(dest,archive/'evaluation'/f'{kind}-{label}')
            print('REUSED VERIFIED CITY PRECHECK',label,record['trips'],flush=True)
            return
        script=evaluator if kind=='lesson' else source/'evaluate_overnight_city.py'
        args=[sys.executable,'-u',str(script),'--checkpoint',str(checkpoint),'--output',str(dest)]
        if kind=='city':args += ['--dll',str(host/'TrafficHost.dll')]
        dump(archive/f'{kind}-{label}-command.json',args)
        with (out/f'{kind}-{label}.log').open('x') as log:
            subprocess.run(args,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        shutil.copytree(dest,archive/'evaluation'/f'{kind}-{label}')
        print('EVALUATION',kind,label,(dest/'summary.json').read_text().strip(),flush=True)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures=[pool.submit(evaluate,'city','original',original),pool.submit(evaluate,'city','parent',parent)]
            for arm,mixed in [('lesson-only',False),('mixed-city',True)]:
                state.update(phase='training',arm=arm);publish()
                args=[sys.executable,'-u',str(source/'continue_road_cost_trial.py'),
                      '--parent',str(parent),'--dll',str(host/'TrafficHost.dll'),'--output',str(out/arm),
                      '--road-cost','.04','--seed-start','210000000','--rng-seed','251125',
                      '--completed-decisions','262144','--target-decisions','524288']
                if mixed:args.append('--mixed-city')
                dump(archive/f'{arm}-command.json',args)
                process=subprocess.Popen(args,cwd=root,env=env)
                queued=set()
                last_activity=time.monotonic();last_stamp=None
                while process.poll() is None:
                    copy_metrics(arm)
                    activity=[path.stat().st_mtime_ns for name in ('episodes.jsonl','gradient_audit.jsonl','status.json')
                              if (path:=out/arm/name).exists()]
                    stamp=max(activity,default=None)
                    if stamp!=last_stamp:last_activity=time.monotonic();last_stamp=stamp
                    if time.monotonic()-last_activity>600:
                        stop_owned_tree(process)
                        raise RuntimeError(f'{arm}: no episode, gradient or checkpoint progress for10minutes; stopped owned learner tree')
                    for budget in (393216,524288):
                        checkpoint=out/arm/f'checkpoint-{budget:09d}.zip'
                        if checkpoint.exists() and budget not in queued:
                            futures.append(pool.submit(evaluate,'lesson',f'{arm}-{budget}',checkpoint));queued.add(budget)
                    time.sleep(10)
                copy_metrics(arm)
                if process.returncode:raise RuntimeError(f'{arm} exited {process.returncode}')
                for budget in (393216,524288):
                    if budget not in queued:futures.append(pool.submit(evaluate,'lesson',f'{arm}-{budget}',out/arm/f'checkpoint-{budget:09d}.zip'))
                futures.append(pool.submit(evaluate,'city',arm,out/arm/'checkpoint-000524288.zip'))
            state.update(phase='evaluation',arm='both');publish()
            for future in futures:future.result()
        subprocess.run([sys.executable,str(source/'summarize_overnight_transfer.py'),'--archive',str(archive)],cwd=root,env=env,check=True)
        assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in protected.items())
        state.update(status='complete',phase='finished',finished=datetime.datetime.now().astimezone().isoformat());publish()
        with (root/'training/EXPERIMENT_HISTORY.md').open('a') as f:
            f.write('\n\n## 25 November 2026 — overnight task-mix comparison completed\n\nBoth branches completed262144additional decisions, reaching524288cumulative from the same saved policy. The planned intervention was adding native city workers; critic and actor settings were unchanged. Four practice and four32-game city development evaluations completed. [Results](../docs/training/'+archive.name+'/RESULTS.md). No automatic promotion or further run; independent replication/confirmation remain open.\n')
        print('COMPLETE: both learners, practice curves and city retention finished; results archived. No automatic promotion.',flush=True)
    except BaseException as exc:
        state.update(status='error',error=repr(exc));publish();raise
    finally:
        dump(archive/'manifest.json',{str(path.relative_to(archive)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in archive.rglob('*') if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts})


if __name__=='__main__':main()

"""Bounded repeated-route PPO diagnostic with fixed and transfer reviews."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from prepare_city_policy import sha256
from run_overnight_transfer_comparison import stop_owned_tree
from run_mini_horizon_comparison import dump


def main():
    p=argparse.ArgumentParser()
    for name in ('output','archive','parent'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--seed',type=int,default=232000001);p.add_argument('--rollouts',type=int,default=8)
    a=p.parse_args()
    if a.rollouts<4 or a.rollouts%4:p.error('Rollouts must be a positive multiple of4')
    root=Path.cwd();out=a.output.absolute();archive=a.archive.absolute();parent=a.parent.absolute()
    baseline=json.loads((archive/'initial/config.json').read_text())
    assert baseline['checkpoint_sha256']==sha256(parent) and baseline['seed']==a.seed and baseline['horizon']==300
    assert baseline['action_seeds']==list(range(622000,622032)) and baseline['split']=='train'
    source=out/'runtime/training';source.mkdir(parents=True,exist_ok=False)
    for path in (root/'training').glob('*.py'):shutil.copy2(path,source/path.name)
    shutil.copy2(root/'training/stage1_replay.html',source/'stage1_replay.html')
    host=out/'runtime/host';shutil.copytree(root/'output/road-cost-reward-build-02/bin/TrafficHost/release',host)
    assert sha256(host/'TrafficHost.dll')==baseline['host_sha256']
    shutil.copytree(source,archive/'runtime-source')
    env=dict(os.environ,PYTHONPATH=str(source))
    state=dict(status='running',started=datetime.datetime.now().astimezone().isoformat(),pid=os.getpid(),
        parent=str(parent),parent_sha256=sha256(parent),seed=a.seed,added_decisions=8192*a.rollouts,
        phase='training',intervention='One repeated empty-board native training fixture; learned roads/Adam retained, Wait frozen and critic features detached. Native300second score, no teacher actions. Learnability diagnostic, not generalization or promotion.')
    def publish():dump(out/'status.json',state);dump(archive/'status.json',state)
    def evaluate(kind,label,checkpoint):
        dest=out/'evaluation'/f'{kind}-{label}'
        script={'fixed':'evaluate_fixed_mini.py','practice':'audit_mini_behavior.py','city':'evaluate_overnight_city.py'}[kind]
        command=[sys.executable,'-u',str(source/script),'--dll',str(host/'TrafficHost.dll'),'--output',str(dest),'--workers','2']
        if kind=='practice':command+=['--checkpoints',str(checkpoint),'--labels','candidate','--small-city-horizon','300']
        else:command+=['--checkpoint',str(checkpoint)]
        if kind=='fixed':command+=['--seed',str(a.seed)]
        dump(archive/f'{kind}-{label}-command.json',command)
        with (out/f'{kind}-{label}.log').open('x') as log:
            subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        shutil.copytree(dest,archive/'evaluation'/f'{kind}-{label}')
        print('EVALUATION',kind,label,(dest/'summary.json').read_text(),flush=True)
    try:
        publish()
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures=[];queued=set()
            command=[sys.executable,'-u',str(source/'train_city_curriculum.py'),
                '--parent',str(parent),'--dll',str(host/'TrafficHost.dll'),'--output',str(out/'training'),
                '--record-dir',str(archive/'measurements'),'--stage','single-connection',
                '--repeat-mini-seed',str(a.seed),'--seed-start',str(a.seed),'--workers','16',
                '--rollout-steps','512','--rollouts',str(a.rollouts),'--batch-size','128',
                '--learning-rate','.0003','--value-coefficient','.00001','--gae-lambda','1',
                '--collapse-forced-wait','--fast-small-city-tail','--cache-frozen-growth',
                '--small-city-horizon','300','--allow-bridges','--gradient-audit-steps','64','--save-every-rollouts','1']
            dump(archive/'training-command.json',command)
            process=subprocess.Popen(command,cwd=root,env=env)
            last_stamp=None;last_activity=time.monotonic()
            def queue_ready():
                path=out/'training/checkpoints.json'
                if not path.exists():return
                for item in json.loads(path.read_text()):
                    count=item['added_decisions']
                    if count in (2048*a.rollouts,4096*a.rollouts,8192*a.rollouts) and count not in queued:
                        futures.append(pool.submit(evaluate,'fixed',str(count),Path(item['path'])))
                        if count==8192*a.rollouts:
                            for kind in ('practice','city'):futures.append(pool.submit(evaluate,kind,'final',Path(item['path'])))
                        queued.add(count)
            while process.poll() is None:
                queue_ready()
                stamps=[path.stat().st_mtime_ns for name in ('episodes.jsonl','checkpoints.json','progress.csv') if (path:=out/'training'/name).exists()]
                stamp=max(stamps,default=None)
                if stamp!=last_stamp:last_stamp=stamp;last_activity=time.monotonic()
                if time.monotonic()-last_activity>600:
                    stop_owned_tree(process);raise RuntimeError('No progress for10minutes')
                time.sleep(10)
            queue_ready()
            if process.returncode:raise RuntimeError(f'Training exited{process.returncode}')
            assert queued=={2048*a.rollouts,4096*a.rollouts,8192*a.rollouts}
            state.update(phase='evaluation');publish()
            for future in futures:future.result()
        assert sha256(parent)==state['parent_sha256']
        read=lambda path:[json.loads(s) for s in path.read_text().splitlines()]
        initial=read(archive/'initial/games.jsonl');base={r['action_seed']:r for r in initial};curve=[]
        for count in sorted(queued):
            rows=read(archive/'evaluation'/f'fixed-{count}'/'games.jsonl')
            curve.append(dict(added_decisions=count,games=len(rows),successes=sum(r['success'] for r in rows),
                gained=sum(r['success'] and not base[r['action_seed']]['success'] for r in rows),
                lost=sum(not r['success'] and base[r['action_seed']]['success'] for r in rows)))
        report=dict(initial_successes=sum(r['success'] for r in initial),curve=curve,
            practice=json.loads((archive/'evaluation/practice-final/summary.json').read_text()),
            city=json.loads((archive/'evaluation/city-final/summary.json').read_text()),
            limits='Repeated training layout/action draws. Inspect fresh action draws, new layouts and city retention before any promotion. No automatic extension or overnight launch.')
        dump(archive/'results.json',report)
        lines=['# Repeated hard-connection PPO diagnostic','',report['limits'],'',
            f"Initial successes: {report['initial_successes']}/32.",'',
            '| Added decisions | Successes /32 | Gained draws | Lost draws |','|---:|---:|---:|---:|']
        for row in curve:lines.append(f"| {row['added_decisions']} | {row['successes']} | {row['gained']} | {row['lost']} |")
        lines+=['',f"Final development city mean: {report['city']['trips']:.2f}; scoring {report['city']['scoring']}/32. This is a retention review, not fresh confirmation."]
        (archive/'RESULTS.md').write_text('\n'.join(lines)+'\n')
        state.update(status='complete',phase='finished',finished=datetime.datetime.now().astimezone().isoformat());publish()
        with (root/'training/EXPERIMENT_HISTORY.md').open('a') as f:f.write('\n\n## Repeated hard-connection diagnostic completed\nDeclared budget and all fixed/practice/city reviews complete. See docs/training/'+archive.name+'/RESULTS.md. No automatic promotion or overnight launch.\n')
    except BaseException as exc:
        state.update(status='error',error=repr(exc));publish();raise
    finally:
        dump(archive/'manifest.json',{str(p.relative_to(archive)):sha256(p) for p in archive.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts})


if __name__=='__main__':main()

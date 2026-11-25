"""Bounded road-learning continuation with explicitly restored, frozen Wait."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from run_overnight_transfer_comparison import stop_owned_tree


def dump(path,data):
    pending=path.with_suffix(path.suffix+'.pending');pending.write_text(json.dumps(data,indent=2)+'\n');pending.replace(path)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--bank',type=Path,required=True);p.add_argument('--parent',type=Path,required=True);p.add_argument('--rollouts',type=int,choices=(16,32),default=16)
    a=p.parse_args();root=Path.cwd();out=a.output.absolute();archive=a.archive.absolute()
    source=out/'runtime/training';source.mkdir(parents=True,exist_ok=False)
    for path in (root/'training').glob('*.py'):shutil.copy2(path,source/path.name)
    shutil.copy2(root/'training/stage1_replay.html',source/'stage1_replay.html')
    host=out/'runtime/host';shutil.copytree(root/'output/road-cost-reward-build-02/bin/TrafficHost/release',host)
    bank=out/'runtime/starts.json';shutil.copy2(a.bank,bank)
    shutil.copytree(source,archive/'runtime-source')
    parent=a.parent.absolute();parent_hash=hashlib.sha256(parent.read_bytes()).hexdigest()
    # Reject an accidental joint-policy start before launching training.
    from sb3_contrib import MaskablePPO
    from city_road_choice_policy import CityRoadChoicePolicy
    import torch
    initial=MaskablePPO.load(parent,device='cpu')
    assert isinstance(initial.policy,CityRoadChoicePolicy)
    for name in ('growth_strategy_wait','growth_strategy_visual_wait'):
        module=getattr(initial.policy.features_extractor,name)
        assert not any(p.requires_grad for p in module.parameters())
        assert all(torch.count_nonzero(p)==0 for p in module[-1].parameters())
    policy_class=type(initial.policy).__name__
    critic_features_detached=bool(getattr(initial.policy,'critic_features_detached',False))
    del initial
    env=dict(os.environ,PYTHONPATH=str(source))
    state=dict(status='running',pid=os.getpid(),started=datetime.datetime.now().astimezone().isoformat(),
               parent=str(parent),parent_sha256=parent_hash,policy_class=policy_class,critic_features_detached=critic_features_detached,added_decisions=8192*a.rollouts,
               bank_sha256=hashlib.sha256(bank.read_bytes()).hexdigest(), intervention='Continue learned roads and Adam with explicitly restored frozen Wait; critic gradient contract recorded separately. Native300-second lessons, same8city+4pair+4single reset mix, validated cache/terminal-tail acceleration. Compare changes against this parent and retained original; not a matched causal test against joint training.')
    def publish():dump(out/'status.json',state);dump(archive/'status.json',state)
    def copy_metrics(arm):
        dest=archive/'measurements'/arm;dest.mkdir(parents=True,exist_ok=True)
        for pattern in ('*.json','*.jsonl','*.csv'):
            for path in (out/arm).glob(pattern):shutil.copy2(path,dest/path.name)
    def evaluate(kind,label,checkpoint):
        dest=out/'evaluation'/f'{kind}-{label}'
        script=source/'audit_mini_behavior.py' if kind=='practice' else source/'evaluate_overnight_city.py'
        args=[sys.executable,'-u',str(script),'--output',str(dest),'--dll',str(host/'TrafficHost.dll'),'--workers','2']
        args+=['--checkpoints',str(checkpoint),'--labels','candidate','--small-city-horizon','300'] if kind=='practice' else ['--checkpoint',str(checkpoint)]
        dump(archive/f'{kind}-{label}-command.json',args)
        with (out/f'{kind}-{label}.log').open('x') as log:
            subprocess.run(args,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        shutil.copytree(dest,archive/'evaluation'/f'{kind}-{label}')
        print('EVALUATION',kind,label,(dest/'summary.json').read_text().strip(),flush=True)
    original=root/'docs/training/city-transfer-diagnosis-2026-11-25/evaluation/city-initial'
    reference=json.loads((original/'summary.json').read_text())
    assert reference['host_sha256']==hashlib.sha256((host/'TrafficHost.dll').read_bytes()).hexdigest()
    shutil.copytree(original,archive/'evaluation/city-retained-original')
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures=[pool.submit(evaluate,kind,'initial',parent) for kind in ('practice','city')]
            for arm,lesson_horizon in [('road-learning',300)]:
                stage='expansion-balanced'
                state.update(phase='training',arm=arm);publish()
                args=[sys.executable,'-u',str(source/'train_city_curriculum.py'),
                      '--parent',str(parent),'--dll',str(host/'TrafficHost.dll'),'--output',str(out/arm),
                      '--stage',stage,'--workers','16','--rollout-steps','512','--rollouts',str(a.rollouts),
                      '--batch-size','128','--learning-rate','.0003','--value-coefficient','.00001','--gae-lambda','1',
                      '--collapse-forced-wait','--allow-bridges','--seed-start','241000000',
                      '--gradient-audit-steps','64','--save-every-rollouts','1']
                args.append('--task-minibatches')
                args+=['--mini-starts',str(bank),'--small-city-horizon',str(lesson_horizon),'--cache-frozen-growth','--fast-small-city-tail']
                dump(archive/f'{arm}-command.json',args)
                process=subprocess.Popen(args,cwd=root,env=env);queued=set();last_activity=time.monotonic();last_stamp=None
                def queue_ready():
                    file=out/arm/'checkpoints.json'
                    if not file.exists():return
                    for row in json.loads(file.read_text()):
                        budget=row['added_decisions']
                        if budget in (2048*a.rollouts,4096*a.rollouts,8192*a.rollouts) and budget not in queued:
                            for kind in ('practice','city'):futures.append(pool.submit(evaluate,kind,f'{arm}-{budget}',Path(row['path'])))
                            queued.add(budget)
                while process.poll() is None:
                    copy_metrics(arm);queue_ready()
                    stamps=[path.stat().st_mtime_ns for name in ('episodes.jsonl','gradient_audit.jsonl','checkpoints.json','progress.csv') if (path:=out/arm/name).exists()]
                    stamp=max(stamps,default=None)
                    if stamp!=last_stamp:last_activity=time.monotonic();last_stamp=stamp
                    if time.monotonic()-last_activity>600:
                        stop_owned_tree(process);raise RuntimeError(f'{arm}: no progress for10minutes')
                    time.sleep(10)
                copy_metrics(arm);queue_ready()
                if process.returncode:raise RuntimeError(f'{arm} exited{process.returncode}')
                assert queued=={2048*a.rollouts,4096*a.rollouts,8192*a.rollouts}
            state.update(phase='evaluation',arm='road-learning');publish()
            for future in futures:future.result()
        assert hashlib.sha256(parent.read_bytes()).hexdigest()==parent_hash
        subprocess.run([sys.executable,str(source/'summarize_mini_road_continuation.py'),'--archive',str(archive)],cwd=root,env=env,check=True)
        state.update(status='complete',phase='finished',finished=datetime.datetime.now().astimezone().isoformat());publish()
        with (root/'training/EXPERIMENT_HISTORY.md').open('a') as f:
            f.write('\n\n## 25 November 2026 — bounded road-learning continuation completed\n\nThe frozen-Wait native-score continuation completed its declared budget from the saved repaired policy, with road and critic Adam progress preserved. Fixed quarter/half/final practice and city evaluations completed. [Archived results](../docs/training/'+archive.name+'/RESULTS.md). No automatic promotion or further training; inspect uncertainty and transfer before deciding the next step.\n')
        print('COMPLETE: road-learning continuation and all practice/city learning-curve evaluations archived. No automatic promotion.',flush=True)
    except BaseException as exc:
        state.update(status='error',error=repr(exc));publish();raise
    finally:
        dump(archive/'manifest.json',{str(path.relative_to(archive)):hashlib.sha256(path.read_bytes()).hexdigest()
             for path in archive.rglob('*') if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts})


if __name__=='__main__':main()

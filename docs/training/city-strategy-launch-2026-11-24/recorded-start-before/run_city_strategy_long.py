"""Detached city PPO continuation with immutable runtime and paired regression guards."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.now(ZoneInfo('Asia/Beirut')).isoformat()
def publish(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)

def run_child(command, *, cwd, timeout=3600):
    """Bound each job and clean up its owned worker group, including on interrupt."""
    process=subprocess.Popen(command,cwd=cwd,start_new_session=True)
    try:
        code=process.wait(timeout=timeout)
        if code:raise subprocess.CalledProcessError(code,command)
    finally:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait(timeout=5)
        # A dead parent can leave a worker that ignores SIGTERM. Its session
        # belongs only to this finished job; never leave such workers running.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass

def review_decision(reference,candidate,failures):
    retained=(candidate['scoring_games']>=reference['scoring_games'] and candidate['mean_score']>=.9*reference['mean_score'])
    failures=0 if retained else failures+1
    catastrophic=candidate['mean_score']<.5*reference['mean_score']
    promote=retained and candidate['mean_score']>=reference['mean_score']
    return dict(retained=retained,promote=promote,failures=failures,stop=catastrophic or failures>=2)

def main():
    def interrupted(signum,frame):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted)
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('start','dll','output','record-dir'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--hours',type=float,default=8)
    p.add_argument('--horizon',type=int,default=1200)
    p.add_argument('--stage',choices=('city','strategy-balanced'),default='city')
    p.add_argument('--fast-priority-tail',action='store_true')
    p.add_argument('--reserve-warmup-seconds',type=int,default=0)
    p.add_argument('--reserve-delay-seconds',type=int,choices=range(1,17),default=None)
    p.add_argument('--allow-bridges',action='store_true')
    p.add_argument('--task-minibatches',action='store_true')
    p.add_argument('--reserve-return-advantages',action='store_true')
    p.add_argument('--seed-start',type=int,default=180_000_000)
    p.add_argument('--learning-rate',type=float,default=.003)
    p.add_argument('--value-coefficient',type=float,default=None)
    p.add_argument('--gradient-audit-steps',type=int,default=0)
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--review-every',type=int,default=4)
    p.add_argument('--review-games',type=int,default=24)
    p.add_argument('--segment-rollouts',type=int,default=4)
    args=p.parse_args()
    if not 0<args.hours<=24 or not 0<args.horizon<=3600 or min(args.workers,args.review_every,args.review_games,args.segment_rollouts)<1 or args.learning_rate<=0:
        p.error('Invalid budget or parameters')
    if args.gradient_audit_steps<0:p.error('Gradient audit steps cannot be negative')
    if args.value_coefficient is not None and not 0<args.value_coefficient<float('inf'):p.error('Value coefficient must be finite and positive')
    if args.stage=='strategy-balanced' and args.workers%16:
        p.error('Balanced strategy requires a multiple of 16 workers to preserve task proportions')
    if not 0<=args.reserve_warmup_seconds<=6:p.error('Reserve warmup must be 0..6 seconds')
    if args.reserve_delay_seconds is not None and args.reserve_warmup_seconds:p.error('Explicit reserve delay and warmup cannot be combined')
    if args.task_minibatches and args.stage!='strategy-balanced':p.error('Task minibatches require strategy-balanced')
    if args.reserve_return_advantages and not args.task_minibatches:p.error('Reserve return advantages require task minibatches')
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    record=args.record_dir.resolve();record.mkdir(parents=True,exist_ok=False)
    runtime=root/'runtime';source=runtime/'training';source.mkdir(parents=True)
    for file in (ROOT/'training').glob('*.py'):shutil.copy2(file,source/file.name)
    shutil.copytree(source,record/'runtime-source')
    native=runtime/'host';shutil.copytree(args.dll.resolve().parent,native)
    dll=native/args.dll.name
    current=best=args.start.resolve();identities={str(current):sha(current)}
    config=dict(start=str(current),start_sha256=sha(current),dll=str(dll),host_sha256=sha(dll),hours=args.hours,
        horizon=args.horizon,stage=args.stage,allow_bridges=args.allow_bridges,fast_priority_tail=args.fast_priority_tail,reserve_warmup_seconds=args.reserve_warmup_seconds,reserve_delay_seconds=args.reserve_delay_seconds,task_minibatches=args.task_minibatches,reserve_return_advantages=args.reserve_return_advantages,seed_start=args.seed_start,workers=args.workers,learning_rate=args.learning_rate,value_coefficient=args.value_coefficient,gradient_audit_steps=args.gradient_audit_steps,rollout_steps=512,batch_size=128,gae_lambda=1,
        review_every=args.review_every,review_games=args.review_games,segment_rollouts=args.segment_rollouts,created=now(),runtime_sources={f.name:sha(f) for f in source.glob('*.py')},
        child_timeout_seconds=3600,
        note='Training-time target checked at segment boundaries. Runtime frozen. Each child job has a one-hour timeout and owned-group cleanup. All saved checkpoints retained; no automatic deletion.')
    publish(root/'config.json',config);publish(record/'config.json',config)
    state=dict(status='running',pid=os.getpid(),started=now(),training_seconds=0.,segments=0,current_checkpoint=str(current),best_checkpoint=str(best),failed_reviews=0)
    def update():
        state['updated']=now();publish(root/'status.json',state);publish(record/'status.json',state)
    update()
    try:
        while state['training_seconds']<args.hours*3600:
            index=state['segments']+1;segment=root/f'segment-{index:03d}'
            state.update(active_segment=str(segment),phase='training');update()
            print(f'START | segment {index} | active training {state["training_seconds"]/3600:.2f} h | {now()}',flush=True)
            command=[sys.executable,'-u',str(source/'train_city_curriculum.py'),'--dll',str(dll),'--parent',str(current),'--output',str(segment),
                '--stage',args.stage,'--rollouts',str(args.segment_rollouts),'--rollout-steps','512','--batch-size','128','--gae-lambda','1','--horizon',str(args.horizon),
                '--record-dir',str(record/segment.name),
                '--save-every-rollouts','1',
                '--workers',str(args.workers),'--seed-start',str(args.seed_start+(index-1)*100_000),'--learning-rate',str(args.learning_rate),'--collapse-forced-wait',
                '--reserve-warmup-seconds',str(args.reserve_warmup_seconds)]
            if args.gradient_audit_steps:command.extend(['--gradient-audit-steps',str(args.gradient_audit_steps)])
            if args.allow_bridges:command.append('--allow-bridges')
            if args.value_coefficient is not None:command.extend(['--value-coefficient',str(args.value_coefficient)])
            if args.reserve_delay_seconds is not None:command.extend(['--reserve-delay-seconds',str(args.reserve_delay_seconds)])
            if args.fast_priority_tail:command.append('--fast-priority-tail')
            if args.task_minibatches:command.append('--task-minibatches')
            if args.reserve_return_advantages:command.append('--reserve-return-advantages')
            run_child(command,cwd=ROOT)
            completed=json.loads((segment/'complete.json').read_text());current=Path(completed['checkpoints'][-1]['path']).resolve()
            state.update(segments=index,current_checkpoint=str(current),current_sha256=sha(current),training_seconds=state['training_seconds']+completed['seconds'])
            durable=record/segment.name
            for name in ['config.json','complete.json','checkpoints.json','episodes.jsonl','progress.csv']:
                shutil.copy2(segment/name,durable/name)
            with (record/'checkpoints.jsonl').open('a') as stream:
                for row in completed['checkpoints']:stream.write(json.dumps(dict(segment=index,recorded=now(),**row))+'\n')
            update()
            if index%args.review_every==0 or state['training_seconds']>=args.hours*3600:
                review=root/f'review-{index:03d}'
                state.update(phase='review',active_review=str(review));update()
                print(f'REVIEW | segment {index} | paired {args.review_games} cities',flush=True)
                run_child([sys.executable,'-u',str(source/'evaluate_city_service.py'),'--dll',str(dll),'--checkpoints',str(best),str(current),
                    '--output',str(review),'--games',str(args.review_games),'--seed',str(960_000+index),'--workers','8','--horizon',str(args.horizon)]+(['--allow-bridges'] if args.allow_bridges else []),cwd=ROOT)
                report=json.loads((review/'summary.json').read_text());decision=review_decision(report['results']['0'],report['results']['1'],state['failed_reviews'])
                state.update(failed_reviews=decision['failures'],last_review=str(review),last_decision=decision)
                if decision['promote']:best=current
                state.update(best_checkpoint=str(best),best_sha256=sha(best))
                shutil.copytree(review,record/review.name)
                print(f'REVIEW RESULT | parent {report["results"]["0"]["mean_score"]:.2f} | current {report["results"]["1"]["mean_score"]:.2f} | {decision}',flush=True)
                if decision['stop']:
                    state.update(status='regression_stop',phase='finished');update();return
            assert all(sha(path)==digest for path,digest in identities.items()) and sha(dll)==config['host_sha256']
            update()
        state.update(status='complete',phase='finished');update()
    except BaseException as error:
        state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'error',error=repr(error));update();raise
    finally:
        print(json.dumps(state,indent=2),flush=True)

if __name__=='__main__':main()

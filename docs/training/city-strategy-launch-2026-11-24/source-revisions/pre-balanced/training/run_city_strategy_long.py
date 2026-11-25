"""Detached city PPO continuation with immutable runtime and paired regression guards."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.now(ZoneInfo('Asia/Beirut')).isoformat()
def publish(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)

def review_decision(reference,candidate,failures):
    retained=(candidate['scoring_games']>=reference['scoring_games'] and candidate['mean_score']>=.9*reference['mean_score'])
    failures=0 if retained else failures+1
    catastrophic=candidate['mean_score']<.5*reference['mean_score']
    promote=retained and candidate['mean_score']>=reference['mean_score']
    return dict(retained=retained,promote=promote,failures=failures,stop=catastrophic or failures>=2)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('start','dll','output','record-dir'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--hours',type=float,default=8)
    p.add_argument('--horizon',type=int,default=1200)
    p.add_argument('--learning-rate',type=float,default=.003)
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--review-every',type=int,default=4)
    p.add_argument('--review-games',type=int,default=24)
    p.add_argument('--segment-rollouts',type=int,default=4)
    args=p.parse_args()
    if not 0<args.hours<=24 or not 0<args.horizon<=3600 or min(args.workers,args.review_every,args.review_games,args.segment_rollouts)<1 or args.learning_rate<=0:
        p.error('Invalid budget or parameters')
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    record=args.record_dir.resolve();record.mkdir(parents=True,exist_ok=False)
    runtime=root/'runtime';source=runtime/'training';source.mkdir(parents=True)
    for file in (ROOT/'training').glob('*.py'):shutil.copy2(file,source/file.name)
    shutil.copytree(source,record/'runtime-source')
    native=runtime/'host';shutil.copytree(args.dll.resolve().parent,native)
    dll=native/args.dll.name
    current=best=args.start.resolve();identities={str(current):sha(current)}
    config=dict(start=str(current),start_sha256=sha(current),dll=str(dll),host_sha256=sha(dll),hours=args.hours,
        horizon=args.horizon,workers=args.workers,learning_rate=args.learning_rate,rollout_steps=512,batch_size=128,gae_lambda=1,
        review_every=args.review_every,review_games=args.review_games,segment_rollouts=args.segment_rollouts,created=now(),runtime_sources={f.name:sha(f) for f in source.glob('*.py')},
        note='Training-time target checked at segment boundaries. Runtime frozen. All saved checkpoints retained; no automatic deletion.')
    publish(root/'config.json',config);publish(record/'config.json',config)
    state=dict(status='running',pid=os.getpid(),started=now(),training_seconds=0.,segments=0,current_checkpoint=str(current),best_checkpoint=str(best),failed_reviews=0)
    def update():
        state['updated']=now();publish(root/'status.json',state);publish(record/'status.json',state)
    update()
    try:
        while state['training_seconds']<args.hours*3600:
            index=state['segments']+1;segment=root/f'segment-{index:03d}'
            state['active_segment']=str(segment);update()
            print(f'START | segment {index} | active training {state["training_seconds"]/3600:.2f} h | {now()}',flush=True)
            command=[sys.executable,'-u',str(source/'train_city_curriculum.py'),'--dll',str(dll),'--parent',str(current),'--output',str(segment),
                '--stage','city','--rollouts',str(args.segment_rollouts),'--rollout-steps','512','--batch-size','128','--gae-lambda','1','--horizon',str(args.horizon),
                '--record-dir',str(record/segment.name),
                '--save-every-rollouts','1',
                '--workers',str(args.workers),'--seed-start',str(180_000_000+index*100_000),'--learning-rate',str(args.learning_rate),'--collapse-forced-wait']
            subprocess.run(command,check=True,cwd=ROOT)
            completed=json.loads((segment/'complete.json').read_text());current=Path(completed['checkpoints'][-1]['path']).resolve()
            state.update(segments=index,current_checkpoint=str(current),current_sha256=sha(current),training_seconds=state['training_seconds']+completed['seconds'])
            durable=record/segment.name
            for name in ['config.json','complete.json','checkpoints.json','episodes.jsonl','progress.csv']:
                shutil.copy2(segment/name,durable/name)
            with (record/'checkpoints.jsonl').open('a') as stream:
                for row in completed['checkpoints']:stream.write(json.dumps(dict(segment=index,recorded=now(),**row))+'\n')
            if index%args.review_every==0 or state['training_seconds']>=args.hours*3600:
                review=root/f'review-{index:03d}'
                print(f'REVIEW | segment {index} | paired {args.review_games} cities',flush=True)
                subprocess.run([sys.executable,'-u',str(source/'evaluate_city_service.py'),'--dll',str(dll),'--checkpoints',str(best),str(current),
                    '--output',str(review),'--games',str(args.review_games),'--seed',str(960_000+index),'--workers','8','--horizon',str(args.horizon)],check=True,cwd=ROOT)
                report=json.loads((review/'summary.json').read_text());decision=review_decision(report['results']['0'],report['results']['1'],state['failed_reviews'])
                state.update(failed_reviews=decision['failures'],last_review=str(review),last_decision=decision)
                if decision['promote']:best=current
                state.update(best_checkpoint=str(best),best_sha256=sha(best))
                shutil.copytree(review,record/review.name)
                print(f'REVIEW RESULT | parent {report["results"]["0"]["mean_score"]:.2f} | current {report["results"]["1"]["mean_score"]:.2f} | {decision}',flush=True)
                if decision['stop']:
                    state['status']='regression_stop';update();return
            assert all(sha(path)==digest for path,digest in identities.items()) and sha(dll)==config['host_sha256']
            update()
        state['status']='complete';update()
    except BaseException as error:
        state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'error',error=repr(error));update();raise
    finally:
        print(json.dumps(state,indent=2),flush=True)

if __name__=='__main__':main()

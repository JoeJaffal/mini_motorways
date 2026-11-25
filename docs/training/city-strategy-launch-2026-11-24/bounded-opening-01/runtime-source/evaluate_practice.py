"""Frozen-checkpoint Stage 1 gate and durable review replays. Never learns."""
import json
import math
from pathlib import Path
import statistics
from time import monotonic

from connection_practice import ConnectionPractice
from hierarchy_rollout import policy_fingerprint
from practice_replay import PracticeRecorder

VALIDATION_SEEDS=tuple(range(20000,20100))


def select_review(outcomes,*,provisional):
    if not outcomes:return dict(provisional=True,mean_score=None,examples={})
    mean=statistics.mean(x['trips'] for x in outcomes)
    best=min(outcomes,key=lambda x:(-x['trips'],x['seed']))
    worst=min(outcomes,key=lambda x:(x['trips'],x['seed']))
    typical=min(outcomes,key=lambda x:(abs(x['trips']-mean),x['seed']))
    return dict(provisional=provisional,mean_score=mean,
        cohort='all_attempts' if provisional else 'complete_frozen_cohort',
        examples={name:dict(seed=row['seed'],score=row['trips'],replay=row['replay'])
                  for name,row in (('best',best),('worst',worst),('nearest_average',typical))})


def _write(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def evaluate_gate(policy,dotnet='dotnet',host_dll=None,*,replay_directory,wall_seconds,max_paused_tokens=4096):
    """Evaluate fixed100 layouts; preserve all traces and freeze weight identity.

    Operational interruptions invalidate promotion, rather than becoming scored
    losses. Simulator errors preserve partial evidence and propagate. No retries.
    A new output directory is required to avoid overwriting prior evaluations.
    """
    if not math.isfinite(wall_seconds) or wall_seconds<=0:
        raise ValueError('An explicit positive finite evaluation wall budget is required')
    deadline=monotonic()+wall_seconds
    directory=Path(replay_directory)
    directory.mkdir(parents=True,exist_ok=False)
    actor=getattr(policy,'policy',policy)
    fingerprint=policy_fingerprint(actor)
    actor.set_training_mode(False)
    env=None;outcomes=[];recorder=None
    summary=dict(kind='frozen-policy-stage1-gate',policy_sha256=fingerprint,
        wall_seconds=wall_seconds,complete_cohort=False,valid=False,passed=False,layouts_passed=0,layouts=outcomes)
    try:
        env=ConnectionPractice(dotnet=dotnet,host_dll=host_dll,split='validation',max_paused_tokens=max_paused_tokens)
        summary.update(environment_schema=env.schema,protocol=env.protocol_version,simulator=env.simulator_version)
        for seed in VALIDATION_SEEDS:
            if monotonic()>=deadline:raise TimeoutError('Evaluation wall budget exhausted; incomplete cohort')
            recorder=PracticeRecorder(env,seed=seed)
            obs=recorder.initial_observation
            while True:
                if monotonic()>=deadline:raise TimeoutError('Evaluation wall budget exhausted; incomplete episode')
                action,_=policy.predict(obs,deterministic=True,action_masks=env.action_masks())
                obs,_,terminated,truncated,info=recorder.step(action)
                if monotonic()>=deadline:raise TimeoutError('Evaluation wall budget exhausted; preserve partial evidence')
                if terminated or truncated:break
            relative='seed-'+str(seed)+'.json'
            recorder.save(directory/relative)
            outcomes.append(dict(seed=seed,trips=info['trips'],seconds=info['seconds'],
                passed=bool(info['pass_candidate']),operational_truncation=info['operational_truncation'],
                ending_reason=info['ending_reason'],replay=relative))
            recorder=None
            summary['layouts_passed']=sum(x['passed'] for x in outcomes)
            _write(directory/'summary.json',summary)
        if policy_fingerprint(actor)!=fingerprint:
            raise RuntimeError('Frozen evaluation policy changed during the cohort')
        valid=not any(x['operational_truncation'] for x in outcomes)
        count=sum(x['passed'] for x in outcomes)
        summary.update(complete_cohort=True,valid=valid,passed=valid and count>=90,layouts_passed=count)
    except BaseException as error:
        summary.update(error_type=type(error).__name__,error=str(error))
        if recorder is not None:
            recorder.save(directory/'interrupted-trace.json')
        raise
    finally:
        summary['review']=select_review(outcomes,provisional=not summary['valid'])
        try:_write(directory/'summary.json',summary)
        finally:
            if env is not None:env.close()
    return summary

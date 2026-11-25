"""Bounded Stage 1 integration runner; defaults to NO TRAINING dry-run.

Do not use --execute until the user authorizes a training session. Dry-run checks
real collection, returns, masks and loss only; parameters remain unchanged.
"""
import argparse
from dataclasses import asdict,replace
import hashlib,json,os,random,sys
from pathlib import Path
from time import monotonic

import numpy as np
import torch
from connection_practice import ConnectionPractice
from hierarchy_policy import HierarchyPolicy
from hierarchy_rollout import FrozenInferenceCollector,InferenceBatch,policy_fingerprint
from hierarchy_batches import prepare_batches
from hierarchy_updater import HierarchyUpdater,UpdateSettings
from hierarchy_checkpoint import save_checkpoint,load_checkpoint
from practice_replay import identity

ROOT=Path(__file__).resolve().parents[1]

def collect_boundary(collector,*,tokens,version,deadline,hard_limit,on_tokens):
    parts=[];count=0
    while count<tokens or (collector.env.role!='primary' and not collector.env.done):
        if monotonic()>=deadline:raise TimeoutError('Collection budget ended before a safe update boundary')
        if count>=hard_limit:raise TimeoutError('Hard token limit cuts a focus; incomplete rollout discarded')
        size=min(32,tokens-count) if count<tokens else 1
        part=collector.collect(max_tokens=min(size,hard_limit-count),policy_version=version)
        parts.append(part);count+=len(part.transitions);on_tokens(len(part.transitions))
        if collector.env.done:break
    return InferenceBatch(tuple(t for p in parts for t in p.transitions),parts[-1].final_observation,
        parts[-1].bootstrap_value,version,parts[0].policy_sha256,sum(p.score_delta for p in parts))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dotnet',default='dotnet');p.add_argument('--dll',default='simulation/Headless/bin/Release/net8.0/TrafficHost.dll')
    p.add_argument('--output',required=True);p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--seed',type=int,default=42);p.add_argument('--threads',type=int,default=1)
    p.add_argument('--rollout-tokens',type=int,default=256);p.add_argument('--minibatch-size',type=int,default=128)
    p.add_argument('--max-tokens',type=int,default=32768);p.add_argument('--wall-seconds',type=float,default=900)
    p.add_argument('--resume',help='Trusted local checkpoint; resets episode, not simulator state')
    p.add_argument('--execute',action='store_true',help='Actually update weights; use only after user authorizes training')
    args=p.parse_args()
    if min(args.threads,args.rollout_tokens,args.minibatch_size,args.max_tokens,args.wall_seconds)<=0:p.error('Positive bounds required')
    if not np.isfinite(args.wall_seconds):p.error('Finite wall budget required')
    if args.device=='cuda' and not torch.cuda.is_available():p.error('CUDA is unavailable')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed);torch.set_num_threads(args.threads)
    env=None;policy=None;config=None
    counters=dict(tokens=0,updates=0,episodes=0,version=0)
    status=dict(mode='training' if args.execute else 'dry-run-no-training',result='STARTING',optimizer_steps=0)
    start=monotonic();deadline=start+args.wall_seconds
    try:
        env=ConnectionPractice(dotnet=args.dotnet,host_dll=args.dll)
        policy=HierarchyPolicy(env.observation_space,env.action_space,lambda _:3e-4).to(args.device)
        settings=UpdateSettings()
        training_files=['hierarchy_policy.py','hierarchy_rollout.py','hierarchy_batches.py','hierarchy_updater.py','hierarchy_objective.py','hierarchy_checkpoint.py','prepare_stage1.py']
        config=dict(schema='hierarchical-stage1-integration-v1',environment=identity(env),seed=args.seed,
            device=args.device,threads=args.threads,rollout_tokens=args.rollout_tokens,minibatch_size=args.minibatch_size,
            gamma=1.,trace_lambda={'manager':1.,'executor':1.},trace_units='policy_tokens',level_weight='equal_roles_sample_weighted',
            manager_entropy='primary_entropy_plus_importance_weighted_conditional_entropy',update=asdict(settings),
            runtime=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__),workers=1,resume_semantics='restore policy/optimizer/RNG; restart current episode, not exact simulator continuation',source_hashes={name:hashlib.sha256((ROOT/'training'/name).read_bytes()).hexdigest() for name in training_files})
        (output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        if args.resume:counters=load_checkpoint(args.resume,policy,expected_config=config)
        collector=FrozenInferenceCollector(env,policy,seed=args.seed+counters['episodes'])
        updater=HierarchyUpdater(policy,settings)
        if args.execute:
            save_checkpoint(output/'initial.pt',policy,config=config,counters=counters)
            save_checkpoint(output/'latest.pt',policy,config=config,counters=counters)
        while counters['tokens']<args.max_tokens and monotonic()<deadline:
            before=policy_fingerprint(policy)
            remaining=args.max_tokens-counters['tokens']
            def counted(n):counters['tokens']+=n
            batch=collect_boundary(collector,tokens=min(args.rollout_tokens,remaining),
                                   version=str(counters['version']),deadline=deadline,hard_limit=remaining,on_tokens=counted)
            minibatches=prepare_batches(batch,device=policy.device,minibatch_size=args.minibatch_size)
            with torch.inference_mode():
                losses=[dict(role=b['role'],loss=float(updater.loss(b)[0])) for b in minibatches]
            if not all(np.isfinite(x['loss']) for x in losses):raise FloatingPointError('Nonfinite dry loss')
            if not args.execute:
                if policy_fingerprint(policy)!=before:raise RuntimeError('Dry run changed weights')
                status.update(result='DRY_RUN_PASS',losses=losses,weights_unchanged=True)
                break
            if monotonic()>=deadline:raise TimeoutError('Budget reached before update')
            # update() checks this deadline before each complete epoch.
            records=updater.update(minibatches,training_authorized=True,deadline=deadline)
            counters['updates']+=len(records);counters['version']+=1
            status['optimizer_steps']=counters['updates']
            if env.done:counters['episodes']+=1
            save_checkpoint(output/'latest.pt',policy,config=config,counters=counters)
            with (output/'progress.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(**counters,elapsed=monotonic()-start,losses=losses,score=batch.score_delta))+'\n')
            if env.done:
                collector.reset(seed=args.seed+counters['episodes'])
            status['result']='BOUNDED_TRAINING_COMPLETE'
        if status['result']=='STARTING':status['result']='BUDGET_EXHAUSTED'
    except KeyboardInterrupt:
        status['result']='INTERRUPTED'
    except TimeoutError as error:
        status.update(result='BUDGET_EXHAUSTED',detail=str(error))
    except BaseException as error:
        status.update(result='ERROR',error=type(error).__name__,detail=str(error));raise
    finally:
        # Never serialize potentially partly updated weights after an error.
        status.update(counters=counters,elapsed_seconds=monotonic()-start)
        try:
            temporary=output/'status.json.tmp'
            temporary.write_text(json.dumps(status,indent=2)+'\n');temporary.replace(output/'status.json')
        finally:
            if env is not None:env.close()
    print(json.dumps(status,indent=2))
    if status['result']=='ERROR':raise SystemExit(1)

if __name__=='__main__':main()

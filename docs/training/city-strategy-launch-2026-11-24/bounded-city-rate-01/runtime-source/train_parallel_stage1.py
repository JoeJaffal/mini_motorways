"""Parallel Stage 1 runner. Default dry-run; --execute actually trains.

One shared policy/update version; independent worker histories and option cuts.
Explicit checkpoint resume starts fresh games; no hidden reward changes.
"""
import argparse,hashlib,json,random,sys
from dataclasses import asdict
from pathlib import Path
from time import monotonic
import numpy as np
import torch
from connection_practice import ConnectionPractice, DIRECT_STAGES, SINGLE_BUILD_STAGE, WAIT
from edge_policy import BOARD_POLICY, EDGE_POLICY, stage1_policy
from hierarchy_updater import HierarchyUpdater,UpdateSettings
from hierarchy_checkpoint import save_checkpoint
from hierarchy_rollout import policy_fingerprint
from parallel_stage1 import ParallelCollector,parallel_batches
from practice_replay import identity
from checkpoint_tools import resume_checkpoint
from practice_reward import specification

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',choices=['clear','one-gap','one-gap-draw-only','one-gap-compact',*DIRECT_STAGES],default='clear')
    p.add_argument('--workers',type=int,default=16);p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    p.add_argument('--threads',type=int,default=2);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--rollout-tokens',type=int,default=2048);p.add_argument('--minibatch-size',type=int,default=128)
    p.add_argument('--max-tokens',type=int,default=4096);p.add_argument('--wall-seconds',type=float,default=300)
    p.add_argument('--reward-mode',choices=['score','connection-economy','single-build'],default=None)
    p.add_argument('--policy', choices=[BOARD_POLICY, EDGE_POLICY], default=BOARD_POLICY)
    p.add_argument('--resume',help='Trusted local checkpoint; restores model, Adam and RNG, starts fresh games')
    p.add_argument('--output',required=True);p.add_argument('--execute',action='store_true')
    p.add_argument('--dotnet',default='dotnet');p.add_argument('--dll',default='simulation/Headless/bin/Release/net8.0/TrafficHost.dll')
    args=p.parse_args()
    if min(args.workers,args.threads,args.rollout_tokens,args.minibatch_size,args.max_tokens,args.wall_seconds)<=0 or not np.isfinite(args.wall_seconds):p.error('Positive finite bounds required')
    if args.device=='cuda' and not torch.cuda.is_available():p.error('CUDA unavailable; select CPU explicitly')
    single_build = args.stage == SINGLE_BUILD_STAGE
    direct = args.stage in DIRECT_STAGES
    if args.policy == EDGE_POLICY and not single_build:
        p.error('Shared edge policy requires one-gap-single-build')
    if args.reward_mode is None:
        args.reward_mode = 'single-build' if single_build else 'score'
    if single_build and args.reward_mode != 'single-build':
        p.error('Single-build stage requires its binary connection reward')
    if args.reward_mode == 'single-build' and not single_build:
        p.error('Binary connection reward requires the single-build stage')
    if args.reward_mode == 'connection-economy' and args.stage != 'one-gap-compact':
        p.error('Connection-economy reward requires the compact stage')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed);torch.set_num_threads(args.threads)
    environments=[];collector=None;policy=None;updater=None
    counts=dict(tokens=0,updates=0,version=0,episodes=0)
    status=dict(result='STARTING',mode='training' if args.execute else 'dry-run-no-training',optimizer_steps=0)
    start=monotonic();deadline=start+args.wall_seconds
    worker_seed_indices=[0]*args.workers;start_tokens=0
    episode_counts=[0]*args.workers;stats=[None]*args.workers;reported=[False]*args.workers
    def fresh_stats():return dict(decisions=0,edits=0,waits=0,cancels=0,training_reward=0.,trip_reward=0.,connection_shaping=0.,road_cost=0.,draw_commands=0,changed_draws=0,no_change_draws=0,new_connections=0,road_units_spent=0,road_units_refunded=0,started=monotonic())
    def report(worker,partial=False):
        env=environments[worker];s=stats[worker]
        ending='partial (run stopped)' if partial else 'game over' if env.raw['failed'] else 'time limit' if env.raw['time']>=env.seconds else 'paused-action stall'
        if single_build and not partial:
            ending = "single build"
        row=dict(worker=worker+1,game=episode_counts[worker]+1,seed=env.scenario_seed,score=env.raw['tripsCompleted'],game_seconds=env.raw['time'],ending=ending,partial=partial,wall_seconds=monotonic()-s['started'],**{k:v for k,v in s.items() if k!='started'})
        if single_build:
            row["success"] = bool(s["training_reward"])
        else:
            print(f"{'PARTIAL GAME' if partial else 'GAME'} {row['game']} | worker {row['worker']} | seed {row['seed']} | score {row['score']} | survival {row['game_seconds']:.1f}s | draws {row['draw_commands']} (changed {row['changed_draws']}, no change {row['no_change_draws']}) | new links {row['new_connections']} | road units spent {row['road_units_spent']} | reward {row['training_reward']:.2f} | wait actions {row['waits']} | decisions {row['decisions']} | {ending}",flush=True)
        with (out/'episodes.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        reported[worker]=True
    def transition(worker,t,info):
        counts['tokens']+=1;s=stats[worker];s['decisions']+=1
        for key in ('draw_commands','changed_draws','no_change_draws','new_connections','road_units_spent','road_units_refunded'):s[key]+=info[key]
        for key in ('training_reward','trip_reward','connection_shaping','road_cost'):s[key]+=info[key]
        if direct:
            s['waits'] += int(t.action == WAIT)
            s['edits'] += info['draw_commands']
        elif t.role=='executor':
            phase=int(t.observation['context'][3:6].argmax())
            if phase and t.action==1500:s['cancels']+=1
            elif phase==0 and t.action==0:s['waits']+=1
            elif phase==2 or (phase==1 and t.observation['global'][40]>.5):s['edits']+=1
        if t.terminated or t.truncated:
            report(worker);counts['episodes']+=1;episode_counts[worker]+=1
    print(f"{'TRAINING' if args.execute else 'DRY RUN (no learning)'} | {args.workers} workers | shared {args.device} policy | stage {args.stage} | reward {args.reward_mode}",flush=True)
    try:
        for _ in range(args.workers):environments.append(ConnectionPractice(dotnet=args.dotnet,host_dll=args.dll,stage=args.stage,reward_mode=args.reward_mode))
        policy=stage1_policy(environments[0], lambda _: 3e-4, name=args.policy).to(args.device)
        settings=UpdateSettings();updater=HierarchyUpdater(policy,settings)
        files=['practice_reward.py','checkpoint_tools.py','parallel_stage1.py','train_parallel_stage1.py','hierarchy_policy.py','hierarchy_batches.py','hierarchy_rollout.py','hierarchy_updater.py','hierarchy_objective.py','hierarchy_checkpoint.py']
        config=dict(schema='parallel-hierarchy-stage1-v1',stage=args.stage,reward_mode=args.reward_mode,reward_spec=specification(args.reward_mode),workers=args.workers,device=args.device,threads=args.threads,seed=args.seed,
            rollout_tokens_global=args.rollout_tokens,minibatch_size=args.minibatch_size,gamma=1,trace_lambda=1,
            level_weight=('single policy, global normalization, sample weighted' if direct
                          else 'equal roles, global role normalization, sample weighted'),update=asdict(settings),
            environment=identity(environments[0]),runtime=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__),
            source_hashes={name:hashlib.sha256((ROOT/'training'/name).read_bytes()).hexdigest() for name in files})
        if args.policy == EDGE_POLICY:
            config['policy'] = args.policy
            config['source_hashes']['edge_policy.py'] = hashlib.sha256((ROOT/'training/edge_policy.py').read_bytes()).hexdigest()
        (out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        if args.resume:
            payload,restored=resume_checkpoint(args.resume,policy,config)
            counts.update({k:int(restored[k]) for k in counts})
            episode_counts[:]=list(restored['worker_episodes'])
            previous_indices=restored.get('worker_seed_indices',episode_counts)
            if len(episode_counts)!=args.workers or len(previous_indices)!=args.workers:raise ValueError('Worker counter count differs')
            worker_seed_indices[:]=[int(n)+1 for n in previous_indices]
            start_tokens=counts['tokens'];status['optimizer_steps']=counts['updates']
            (out/'resume.json').write_text(json.dumps(dict(parent_checkpoint=str(Path(args.resume).resolve()),
                parent_sha256=payload['policy_sha256'],parent_counters=restored,
                game_state='fresh games; unfinished parent games skipped, no bit-exact simulation continuation'),indent=2)+'\n')
            print(f"RESUMED | {counts['updates']} saved optimizer steps | fresh games",flush=True)
        def checkpoint_counters():return dict(counts,worker_episodes=list(episode_counts),worker_seed_indices=list(worker_seed_indices))
        collector=ParallelCollector(environments,policy,seeds=[args.seed+i+args.workers*worker_seed_indices[i] for i in range(args.workers)],on_transition=transition)
        stats[:]=[fresh_stats() for _ in environments]
        def reset_completed():
            resets = []
            for i, env in enumerate(environments):
                if env.done:
                    worker_seed_indices[i] += 1
                    resets.append((i, args.seed+i+args.workers*worker_seed_indices[i]))
            if single_build:
                collector.reset_many(resets)
            else:
                for i, seed in resets:
                    collector.reset(i, seed)
            for i, _ in resets:
                stats[i] = fresh_stats()
                reported[i] = False
        if args.execute:
            save_checkpoint(out/'initial.pt',policy,config=config,counters=checkpoint_counters())
            save_checkpoint(out/'latest.pt',policy,config=config,counters=checkpoint_counters())
        while counts['tokens']-start_tokens<args.max_tokens and monotonic()<deadline:
            before = policy_fingerprint(policy) if not args.execute else None
            left = args.max_tokens - (counts['tokens'] - start_tokens)
            collection_start = monotonic()
            target = min(args.rollout_tokens, left)
            version = str(counts['version'])
            if single_build:
                collections = collector.collect_single_builds(target_tokens=target, deadline=deadline,
                                                             policy_version=version, reset_completed=reset_completed)
                successes = sum(c.transitions[0].reward for _, c in collections)
                print(f'ROLLOUT | {int(successes)}/{len(collections)} successful builds | '
                      f'{counts["tokens"]} decisions collected', flush=True)
            else:
                collections = collector.collect(target_tokens=target, hard_limit=left, deadline=deadline,
                                                policy_version=version)
            collection_seconds=monotonic()-collection_start
            batches=parallel_batches(collections,device=policy.device,minibatch_size=args.minibatch_size,
                                     direct=direct,single_build=single_build)
            if not args.execute:
                with torch.inference_mode():losses=[dict(role=b['role'],loss=float(updater.loss(b)[0])) for b in batches]
                if policy_fingerprint(policy)!=before:raise RuntimeError('Dry run changed weights')
                status.update(result='DRY_RUN_PASS',weights_unchanged=True,losses=losses,collection_seconds=collection_seconds)
                break
            if monotonic()>=deadline:raise TimeoutError('Budget before shared update')
            update_start=monotonic();records=updater.update(batches,training_authorized=True,deadline=deadline)
            counts['updates']+=len(records);counts['version']+=1;status['optimizer_steps']=counts['updates']
            save_checkpoint(out/'latest.pt',policy,config=config,counters=checkpoint_counters())
            worker_tokens = {}
            for i, collection in collections:
                key = str(i + 1)
                worker_tokens[key] = worker_tokens.get(key, 0) + len(collection.transitions)
            progress = dict(**counts, collection_seconds=collection_seconds, update_seconds=monotonic()-update_start,
                            score=sum(c.score_delta for _, c in collections), worker_tokens=worker_tokens,
                            update_diagnostics=records)
            if single_build:
                progress.update(successful_builds=int(successes), build_attempts=len(collections))
            with (out/'progress.jsonl').open('a') as f:
                f.write(json.dumps(progress)+'\n')
            reset_completed()
            status['result']='BOUNDED_TRAINING_COMPLETE'
        if status['result']=='STARTING':status['result']='BUDGET_EXHAUSTED'
    except KeyboardInterrupt:status['result']='INTERRUPTED'
    except TimeoutError as e:status.update(result='BUDGET_EXHAUSTED',detail=str(e))
    except BaseException as e:status.update(result='ERROR',detail=str(e));raise
    finally:
        try:
            for i,env in enumerate(environments):
                if stats[i] is not None and stats[i]['decisions'] and not reported[i]:report(i,partial=not env.done)
            status.update(counters=counts,session_tokens=counts['tokens']-start_tokens,elapsed_seconds=monotonic()-start)
            temporary=out/'status.json.tmp';temporary.write_text(json.dumps(status,indent=2)+'\n');temporary.replace(out/'status.json')
        finally:
            if collector is not None:collector.close()
            for env in environments:env.close()
    print(json.dumps(status,indent=2))

if __name__=='__main__':main()

"""Paired frozen comparison on identical held-out layouts. No training."""
import argparse,json,hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic
import numpy as np
import torch
from connection_practice import ConnectionPractice, DIRECT_STAGE, DIRECT_STAGES, SINGLE_BUILD_STAGE
from edge_policy import checkpoint_policy
from practice_reward import connection_potential
from hierarchy_rollout import policy_fingerprint
from checkpoint_tools import read_checkpoint,load_frozen,migrate_single_build_config
from practice_replay import identity

def write(path,value):
    path=Path(path);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)

def evaluate(policy,envs,seeds,*,deadline,max_decisions,deterministic=False,on_game=None):
    before=policy_fingerprint(policy) if policy is not None else None
    rows=[]
    with ThreadPoolExecutor(max_workers=len(envs)) as pool:
        for offset in range(0,len(seeds),len(envs)):
            batch=seeds[offset:offset+len(envs)];active=list(range(len(batch)))
            observations=[envs[i].reset(seed=seed)[0] for i,seed in enumerate(batch)]
            generators=[torch.Generator().manual_seed(100000+seed) for seed in batch]
            decisions=[0]*len(batch)
            road_units = [0]*len(batch)
            repair_decisions = [None]*len(batch)
            first_connections = [
                0. if connection_potential(envs[i].raw, envs[i].practice_area) else None
                for i in active
            ]
            while active:
                if monotonic()>=deadline:raise TimeoutError('Comparison wall budget exhausted')
                masks=list(pool.map(lambda i:envs[i].action_masks(),active))
                if policy is None:
                    actions = []
                    for i, mask in zip(active, masks):
                        legal = np.flatnonzero(mask)
                        choice = torch.randint(len(legal), (1,), generator=generators[i]).item()
                        actions.append(int(legal[choice]))
                else:
                    obs={k:np.stack([observations[i][k] for i in active]) for k in observations[0]}
                    with torch.inference_mode():
                        tensor,_=policy.obs_to_tensor(obs)
                        dist=policy.get_distribution(tensor,action_masks=np.stack(masks))
                        probs=dist.distribution.probs.cpu()
                        actions=[int(probs[j].argmax()) if deterministic else int(torch.multinomial(probs[j],1,generator=generators[i])) for j,i in enumerate(active)]
                results=list(pool.map(lambda pair:envs[pair[0]].step(pair[1]),zip(active,actions)))
                next_active=[]
                for i,result in zip(active,results):
                    observations[i],_,terminated,truncated,info=result;decisions[i]+=1
                    road_units[i] += info['road_units_spent']
                    if (first_connections[i] is None and info['changed_draws']
                            and connection_potential(envs[i].raw, envs[i].practice_area)):
                        first_connections[i] = info['seconds']
                        repair_decisions[i] = decisions[i]
                    capped=decisions[i]>=max_decisions and not (terminated or truncated)
                    if terminated or truncated or capped:
                        row=dict(seed=batch[i],score=info['trips'],seconds=info['seconds'],decisions=decisions[i],
                            first_connection_seconds=first_connections[i],
                            first_connection_decision=repair_decisions[i], road_units_spent=road_units[i],
                            natural=bool(terminated and not truncated),ending='external_decision_limit' if capped else info['ending_reason'])
                        if envs[i].single_build:
                            row['task_score'] = int(repair_decisions[i] is not None)
                        rows.append(row)
                        if on_game:on_game(row)
                    else:next_active.append(i)
                active=next_active
    if policy is not None and policy_fingerprint(policy)!=before:raise RuntimeError('Evaluation changed weights')
    return sorted(rows,key=lambda x:x['seed'])

def summarize(rows):
    times = [r['first_connection_seconds'] for r in rows if r.get('first_connection_seconds') is not None]
    return dict(games=len(rows),connected_games=len(times),repair_rate=len(times)/len(rows) if rows else None,
        mean_first_connection_seconds=float(np.mean(times)) if times else None,
        mean_road_units_spent=float(np.mean([r.get('road_units_spent', 0) for r in rows])) if rows else None,
        natural_games=sum(r['natural'] for r in rows),scored_games=sum(r['score']>0 for r in rows),
        at_least3=sum(r['score']>=3 and r['natural'] for r in rows),mean_score=float(np.mean([r['score'] for r in rows])) if rows else None)

def paired(initial,trained,*,metric="score"):
    a={r['seed']:r for r in initial};b={r['seed']:r for r in trained}
    if set(a)!=set(b):raise ValueError('Unmatched layout sets')
    wins=sum(b[s][metric]>a[s][metric] for s in a);losses=sum(b[s][metric]<a[s][metric] for s in a)
    return dict(layouts=len(a),trained_higher_score=wins,initial_higher_score=losses,ties=len(a)-wins-losses,
        mean_score_difference=float(np.mean([b[s][metric]-a[s][metric] for s in a])) if a else None)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',required=True);p.add_argument('--trained',required=True);p.add_argument('--output',required=True)
    p.add_argument('--device',choices=['cpu','cuda'],default='cuda');p.add_argument('--workers',type=int,default=16)
    p.add_argument('--threads',type=int,default=2);p.add_argument('--layouts',type=int,default=100)
    p.add_argument('--max-decisions',type=int,default=12000);p.add_argument('--wall-seconds',type=float,default=3600)
    p.add_argument('--deterministic',action='store_true');p.add_argument('--dotnet',default='dotnet')
    p.add_argument('--dll',default='simulation/Headless/bin/Release/net8.0/TrafficHost.dll')
    args=p.parse_args()
    if min(args.workers,args.threads,args.layouts,args.max_decisions,args.wall_seconds)<=0 or not np.isfinite(args.wall_seconds):p.error('Positive finite bounds required')
    if args.layouts>100:p.error('Use the fixed 100-layout held-out cohort')
    if args.device=='cuda' and not torch.cuda.is_available():p.error('CUDA unavailable')
    torch.set_num_threads(args.threads);out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    start=monotonic();deadline=start+args.wall_seconds;envs=[]
    summary=dict(result='STARTING',learning=False,protocol='same validation layouts and per-layout CPU sampling RNG; default sampled actions',
        deterministic=args.deterministic,seeds=list(range(20000,20000+args.layouts)),models={})
    try:
        initial=read_checkpoint(args.initial);trained=read_checkpoint(args.trained)
        if migrate_single_build_config(initial['config'], trained['config']) != trained['config']:
            raise ValueError('Checkpoints must share the same training configuration')
        stage=initial['config'].get('stage','clear')
        for _ in range(min(args.workers,args.layouts)):
            envs.append(ConnectionPractice(dotnet=args.dotnet,host_dll=args.dll,stage=stage,split='validation',reward_mode=initial['config'].get('reward_mode','score')))
        summary.update(stage=stage,environment=identity(envs[0]),workers=len(envs),device=args.device,threads=args.threads,max_decisions=args.max_decisions,wall_seconds=args.wall_seconds,torch=torch.__version__,
            evaluation_sources={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('compare_stage1.py','checkpoint_tools.py')})
        models = [('initial', args.initial), ('trained', args.trained)]
        if stage in DIRECT_STAGES:
            if initial['counters']['updates'] != 0:
                raise ValueError('Direct comparison requires the original untrained checkpoint')
            if trained['counters']['updates'] <= 0:
                raise ValueError('Direct comparison requires a checkpoint after an optimizer update')
            models.append(('uniform_legal', None))
            summary['protocol'] += '; uniform legal reference samples all enabled actions'
        for label,path in models:
            policy = None
            summary['models'][label] = dict(games=[])
            if path is not None:
                policy = checkpoint_policy(envs[0], lambda _: 0., initial['config']).to(args.device)
                payload = load_frozen(path, policy, identity(envs[0]))
                summary['models'][label].update(checkpoint=str(Path(path).resolve()), policy_sha256=payload['policy_sha256'])
            def report(row):
                summary['models'][label]['games'].append(row)
                with (out/'games.jsonl').open('a') as f:f.write(json.dumps(dict(model=label,**row))+'\n')
                metric = f"build reward {row['task_score']}" if 'task_score' in row else f"score {row['score']}"
                print(f"{label.upper()} | seed {row['seed']} | {metric} | {row['seconds']:.1f}s | {row['ending']}",flush=True)
            rows=evaluate(policy,envs,summary['seeds'],deadline=deadline,max_decisions=args.max_decisions,deterministic=args.deterministic,on_game=report)
            summary['models'][label].update(games=rows,summary=summarize(rows))
            write(out/'summary.json',summary)
            del policy
        a=summary['models']['initial']['games'];b=summary['models']['trained']['games']
        valid = all(r['natural'] for model in summary['models'].values() for r in model['games'])
        metric = 'task_score' if stage == SINGLE_BUILD_STAGE else 'score'
        summary.update(result='COMPLETE', valid=valid, paired_metric=metric, paired=paired(a,b,metric=metric))
        if stage == DIRECT_STAGE:
            summary['gate_passed'] = valid and len(b) == 100 and summarize(b)['at_least3'] >= 90
        if stage in DIRECT_STAGES:
            summary['paired_against_uniform'] = paired(summary['models']['uniform_legal']['games'], b, metric=metric)
        # Bootstrap the paired score difference; uncertainty, not a promotion decision.
        differences=np.array([y[metric]-x[metric] for x,y in zip(a,b)])
        if len(differences)>1:
            means=np.random.default_rng(42).choice(differences,(10000,len(differences)),replace=True).mean(1)
            summary['paired']['bootstrap95_mean_difference']=np.quantile(means,[.025,.975]).tolist()
    except (KeyboardInterrupt,TimeoutError) as e:summary.update(result='INCOMPLETE',valid=False,detail=str(e))
    except BaseException as e:summary.update(result='ERROR',valid=False,detail=str(e));raise
    finally:
        summary['elapsed_seconds']=monotonic()-start;write(out/'summary.json',summary)
        for env in envs:env.close()
    compact={k:v for k,v in summary.items() if k not in ('models','seeds')}
    compact['models']={k:v.get('summary',{}) for k,v in summary['models'].items()}
    print(json.dumps(compact,indent=2))
if __name__=='__main__':main()

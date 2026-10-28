"""Frozen-policy evaluation and optional exact best replay; never optimizes weights."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import torch
from sb3_contrib import MaskablePPO
from environment import TrafficEnv,ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed-start',type=int,default=2000)
    p.add_argument('--seed-count',type=int,default=5)
    p.add_argument('--mode',choices=['deterministic','sampled'],default='deterministic')
    p.add_argument('--rng-seed',type=int,default=43)
    p.add_argument('--cap',type=int,default=3600)
    p.add_argument('--dotnet',default=str(ROOT/'tmp/dotnet/dotnet.exe'))
    p.add_argument('--host-dll',type=Path)
    p.add_argument('--draw-mask',choices=['all','productive'])
    p.add_argument('--best-replay',type=Path)
    a=p.parse_args()
    if a.output.exists() or (a.best_replay and a.best_replay.exists()):p.error('Choose fresh output paths')
    if a.seed_count<1:p.error('Positive seed count required')
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(a.rng_seed)
    model=MaskablePPO.load(a.checkpoint,device='cpu')
    initial=[v.detach().clone() for v in model.policy.parameters()]
    goal_policy='candidates' in model.observation_space.spaces
    mode='goal-candidates' if goal_policy else ('connectivity' if model.observation_space['grid'].shape[0]==52 else 'legacy')
    draw_mask=a.draw_mask or getattr(model,'draw_mask','all')
    if goal_policy:
        from goal_agent import GoalEnv
        env=GoalEnv(dotnet=a.dotnet,seconds=a.cap,host_dll=a.host_dll,skip_forced_wait=getattr(model,'skip_forced_wait',False))
    else:env=TrafficEnv(dotnet=a.dotnet,seconds=a.cap,observation_mode=mode,record_replays=bool(a.best_replay),draw_mask=draw_mask,host_dll=a.host_dll)
    results=[];best=None;rank=(-1,-1,0)
    try:
        for seed in range(a.seed_start,a.seed_start+a.seed_count):
            obs,_=env.reset(seed=seed,options={'scenario_seed':seed})
            while True:
                action,_=model.predict(obs,deterministic=a.mode=='deterministic',action_masks=env.action_masks())
                obs,_,terminated,truncated,info=env.step(action)
                if terminated or truncated:
                    result=dict(info,terminated=terminated,truncated=truncated)
                    results.append(result)
                    current=(info['trips'],info['seconds'],-info['rejected_actions'])
                    if current>rank:best=env.export_replay();rank=current
                    print(f"EVAL | {seed} | score {info['trips']} | {info['seconds']:.1f}s | draw noops {info['draw_noop_commands']}/{info['action_counts'].get('draw',0)}",flush=True)
                    break
    finally:env.close()
    if not all(torch.equal(x,y) for x,y in zip(initial,model.policy.parameters())):raise RuntimeError('Evaluation mutated policy')
    report=dict(checkpoint=str(a.checkpoint),checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
                mode=a.mode,rng_seed=a.rng_seed,cap=a.cap,observation_mode=mode,draw_mask=draw_mask,weights_unchanged=True,
                mean_trips=statistics.mean(x['trips'] for x in results),median_trips=statistics.median(x['trips'] for x in results),
                best_trips=max(x['trips'] for x in results),results=results)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    if a.best_replay and best:
        best.update(source='hybrid-evaluation' if goal_policy else 'evaluation',policySchema=env.schema,checkpoint=str(a.checkpoint),evaluationMode=a.mode)
        a.best_replay.parent.mkdir(parents=True,exist_ok=True);a.best_replay.write_text(json.dumps(best,indent=2)+'\n')
    print(f"RESULT | mean {report['mean_trips']:.2f}, best {report['best_trips']} | {a.output}",flush=True)


if __name__=='__main__':main()

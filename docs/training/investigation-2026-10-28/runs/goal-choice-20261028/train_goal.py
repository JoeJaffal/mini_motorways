"""Separate planner-aided goal PPO experiment; not the original all-tools policy."""
import argparse
from pathlib import Path
import json
import time
import hashlib
import subprocess
from datetime import datetime,timezone
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.logger import configure
from goal_agent import GoalEnv,GoalPolicy,GOAL_SCHEMA,vector
from environment import ROOT
from progress import BudgetCallback
from shutdown import save_checkpoint,stop_and_save


def evaluate(model,dotnet,host_dll,seeds,cap=3600,record_dir=None,deterministic=True):
    env=GoalEnv(dotnet=dotnet,host_dll=host_dll,seconds=cap,skip_forced_wait=getattr(model,'skip_forced_wait',False))
    results=[]
    try:
        for seed in seeds:
            obs,_=env.reset(seed=seed,options={'scenario_seed':seed})
            while True:
                action,_=model.predict(obs,deterministic=deterministic,action_masks=env.action_masks())
                obs,_,term,trunc,info=env.step(action)
                if term or trunc:
                    results.append(dict(info,scenario_seed=seed,terminated=term,truncated=trunc,deterministic=deterministic))
                    print(f"GOAL EVAL | {seed} | {info['trips']} trips | {info['seconds']:.1f}s | planner-aided",flush=True)
                    if record_dir:
                        record_dir.mkdir(parents=True,exist_ok=True)
                        replay=env.export_replay();replay['source']='hybrid-evaluation'
                        (record_dir/f'seed-{seed}.json').write_text(json.dumps(replay,indent=2)+'\n')
                    break
    finally:env.close()
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--minutes',type=float,default=25)
    p.add_argument('--steps',type=int,default=1000000);p.add_argument('--workers',type=int,choices=[1,2,4],default=2)
    p.add_argument('--dotnet',default=str(ROOT/'tmp/dotnet/dotnet.exe'));p.add_argument('--host-dll',type=Path)
    p.add_argument('--resume',type=Path);p.add_argument('--stop-file',type=Path)
    p.add_argument('--reward-scale',type=float,default=1.)
    p.add_argument('--skip-forced-wait',action='store_true')
    p.add_argument('--validation-minutes',type=float,default=6);p.add_argument('--eval-count',type=int,default=5)
    a=p.parse_args()
    if a.output.exists():p.error('Fresh run name required')
    if a.minutes<=0 or a.steps<1 or a.eval_count<1:p.error('Positive budgets and evaluation count required')
    a.output.mkdir(parents=True)
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    config=dict(schema=GOAL_SCHEMA,planner_aided=True,replay_source='hybrid-training',action_semantics='choose current house/destination connection; visible router executes ordinary strokes',
                restricted_tools=['road strokes including bridges','wait up to five seconds','upgrade choices'],
                excluded_tools=['motorways','roundabouts','traffic lights','demolition','manual driveway edits'],
                reward_schema='goal-trip-potential-gamma099-v1',reward='trip delta + gamma099 potential difference per macro decision',
                simulator_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                created_utc=datetime.now(timezone.utc).isoformat(),arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
                training_seeds=[1000,1099],validation_seeds=list(range(2000,2000+a.eval_count)),gamma=.99,gae_lambda=.99,
                learning_rate=.0001,ent_coef=.005,aggregate_rollout=256,reward_scale=a.reward_scale,
                decision_timing='choice-only-v1' if a.skip_forced_wait else 'five-second-wait-v1')
    if a.skip_forced_wait:config['reward_schema']='goal-trip-potential-gamma099-choice-v1'
    for name in ['goal_agent.py','planner_diagnostic.py','train_goal.py','environment.py','rewards.py','parallel.py','progress.py','shutdown.py']:
        (a.output/name).write_text((ROOT/'training'/name).read_text())
    env=vector(a.workers,a.output,dotnet=a.dotnet,host_dll=a.host_dll,seeds=range(1000,1100),episodes_per_seed=1,seed_schedule='random',reward_scale=a.reward_scale,skip_forced_wait=a.skip_forced_wait)
    try:
        if a.resume:
            model=MaskablePPO.load(a.resume,env=env,device='cpu',n_steps=256//a.workers)
            if not isinstance(model.policy,GoalPolicy):raise ValueError('Resume requires a goal-policy checkpoint')
        else:
            model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=256//a.workers,batch_size=64,n_epochs=4,
                              gamma=.99,gae_lambda=.99,learning_rate=.0001,ent_coef=.005,verbose=0)
        model.skip_forced_wait=a.skip_forced_wait
        config['trainable_parameters']=sum(x.numel() for x in model.policy.parameters())
        (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        model.set_logger(configure(str(a.output),['csv']));save_checkpoint(model,a.output/'initial.zip')
        initial=torch.cat([v.detach().flatten() for v in model.policy.parameters()]).clone()
        print(f'PLANNER-AIDED GOAL EXPERIMENT | {a.output} | {config["trainable_parameters"]} parameters',flush=True)
        torch.manual_seed(43)
        before=evaluate(model,a.dotnet,a.host_dll,range(2000,2000+a.eval_count),record_dir=a.output/'initial-evaluation')
        (a.output/'before.json').write_text(json.dumps(before,indent=2)+'\n')
        def validation(policy):
            training=policy.policy.training
            try:
                with torch.random.fork_rng(devices=[]):return evaluate(policy,a.dotnet,a.host_dll,range(2000,2000+a.eval_count))
            finally:policy.policy.set_training_mode(training)
        callback=BudgetCallback(a.output,a.minutes,a.steps,1,15,config,validation,a.validation_minutes,a.stop_file)
        interrupted=False;start=time.perf_counter()
        try:model.learn(total_timesteps=a.steps,callback=callback,reset_num_timesteps=True)
        except KeyboardInterrupt:
            interrupted=True;stop_and_save(model,env,callback,a.output)
        if not interrupted:save_checkpoint(model,a.output/'final.zip')
        elapsed=time.perf_counter()-start
        after=[]
        if not interrupted:after=evaluate(model,a.dotnet,a.host_dll,range(2000,2000+a.eval_count),record_dir=a.output/'final-evaluation')
        changed=not torch.equal(initial,torch.cat([v.detach().flatten() for v in model.policy.parameters()]))
        summary=dict(planner_aided=True,training_wall_seconds=elapsed,policy_steps=model.num_timesteps,completed_commands=callback.commands,
                     episodes=callback.episodes,best_training_score=callback.best,parameter_update_confirmed=changed,interrupted=interrupted,
                     stop_reason=callback.stop_reason or 'time_or_step_budget',before=before,after=after,
                     limitations='Restricted planner-aided action abstraction and informed initialization; not the primitive all-tools agent.')
        (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('RESULT '+json.dumps(summary),flush=True)
    finally:env.close()


if __name__=='__main__':main()

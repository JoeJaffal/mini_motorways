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
from goal_agent import GoalEnv,GoalPolicy,GOAL_SCHEMA,CONGESTION_SCHEMA,vector
from environment import ROOT
from progress import BudgetCallback
from shutdown import save_checkpoint,stop_and_save


def model_environment(model,**kwargs):
    supported=kwargs.pop('supported_upgrades',getattr(model,'supported_upgrades',False))
    if 'signals' in model.observation_space.spaces:
        from signal_agent import SignalEnv
        return SignalEnv(signal_context=model.observation_space['signals'].shape[1]==24,supported_upgrades=supported,**kwargs)
    if supported:raise ValueError('Supported-upgrade rule requires the signal agent')
    return GoalEnv(congestion_aware='traffic' in model.observation_space.spaces,**kwargs)


def evaluate(model,dotnet,host_dll,seeds,cap=3600,record_dir=None,deterministic=True):
    env=model_environment(model,dotnet=dotnet,host_dll=host_dll,seconds=cap,skip_forced_wait=getattr(model,'skip_forced_wait',False))
    results=[]
    try:
        for seed in seeds:
            obs,_=env.reset(seed=seed,options={'scenario_seed':seed})
            while True:
                action,_=model.predict(obs,deterministic=deterministic,action_masks=env.action_masks())
                obs,_,term,trunc,info=env.step(action)
                if term or trunc:
                    # Exact commands are saved separately below, not duplicated
                    # into every metric row and the console RESULT line.
                    metrics={k:v for k,v in info.items() if k!='episode_replay'}
                    results.append(dict(metrics,scenario_seed=seed,terminated=term,truncated=trunc,deterministic=deterministic))
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
    p.add_argument('--warm-start',type=Path,help='Explicit v3-to-v4 transfer with fresh optimizer; preserves existing learned weights')
    p.add_argument('--signal-context',action=argparse.BooleanOptionalAction,default=None)
    p.add_argument('--supported-upgrades',action=argparse.BooleanOptionalAction,default=None,
                   help='Optional package filter for restricted roads/bridges/lights agent; inherited on resume')
    p.add_argument('--reward-scale',type=float,help='Defaults to 1 for fresh models; inherited on resume')
    p.add_argument('--skip-forced-wait',action=argparse.BooleanOptionalAction,default=None)
    p.add_argument('--congestion-aware',action=argparse.BooleanOptionalAction,default=None,
                   help='v2 live traffic grid and bypass candidates; fresh model required when switching schemas')
    p.add_argument('--traffic-lights',action=argparse.BooleanOptionalAction,default=None,
                   help='v3 junction signal proposals, implies congestion inputs; fresh schema required')
    p.add_argument('--prior-temperature',type=float,help='Fresh-model prior softening; 1 is the original strength, inherited on resume')
    p.add_argument('--eval-seconds',type=int,default=3600)
    p.add_argument('--learning-rate',type=float,help='Explicit override; resume otherwise preserves checkpoint rate')
    p.add_argument('--validation-minutes',type=float,default=6);p.add_argument('--eval-count',type=int,default=5)
    a=p.parse_args()
    if a.output.exists():p.error('Fresh run name required')
    if a.resume and a.warm_start:p.error('Choose resume OR warm-start')
    if a.warm_start:
        if a.signal_context is False:p.error('Warm start targets signal-context v4')
        a.signal_context=True
    if a.minutes<=0 or a.steps<1 or not 1<=a.eval_count<=5 or a.eval_seconds<1:p.error('Positive budgets and 1-5 development evaluation maps required')
    if a.prior_temperature is not None and (not torch.isfinite(torch.tensor(a.prior_temperature)) or a.prior_temperature<=0):p.error('Positive finite prior temperature required')
    if a.learning_rate is not None and a.learning_rate<=0:p.error('Positive learning rate required')
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    if a.resume or a.warm_start:
        preview_path=a.resume or a.warm_start
        preview=MaskablePPO.load(preview_path,device='cpu')
        if not isinstance(preview.policy,GoalPolicy):p.error('Resume requires a goal-policy checkpoint')
        previous_signals='signals' in preview.observation_space.spaces
        previous_context=previous_signals and preview.observation_space['signals'].shape[1]==24
        if a.warm_start and (not previous_signals or previous_context):p.error('Warm-start requires a v3 signal checkpoint')
        if a.resume and a.signal_context is not None and a.signal_context!=previous_context:p.error('Use --warm-start to change v3 to v4 inputs')
        if a.resume:a.signal_context=previous_context
        if a.traffic_lights is not None and a.traffic_lights!=previous_signals:p.error('Cannot switch traffic-light schema on resume; start a fresh model')
        a.traffic_lights=previous_signals
        previous_temperature=getattr(preview.policy.features_extractor,'prior_temperature',1.)
        if a.prior_temperature is not None and a.prior_temperature!=previous_temperature:p.error('Prior temperature must match resumed policy; use a fresh controlled comparison to change it')
        a.prior_temperature=previous_temperature
        previous_congestion='traffic' in preview.observation_space.spaces
        if a.congestion_aware is not None and a.congestion_aware!=previous_congestion:
            p.error('Cannot switch congestion observation schema on resume; start a fresh model')
        a.congestion_aware=previous_congestion
        previous=preview_path.parent/'config.json'
        metadata=json.loads(previous.read_text()) if previous.exists() else {}
        if a.reward_scale is None:a.reward_scale=getattr(preview,'goal_reward_scale',metadata.get('reward_scale',1.))
        if a.skip_forced_wait is None:a.skip_forced_wait=getattr(preview,'skip_forced_wait',False)
        if a.supported_upgrades is None:a.supported_upgrades=getattr(preview,'supported_upgrades',False)
        if a.warm_start and a.learning_rate is None:a.learning_rate=float(preview.learning_rate)
        if a.resume:del preview
    if a.reward_scale is None:a.reward_scale=1.
    if a.signal_context:
        if a.traffic_lights is False:p.error('Signal context requires traffic lights')
        a.traffic_lights=True
    if a.traffic_lights:
        if a.congestion_aware is False:p.error('Traffic lights require congestion inputs')
        a.congestion_aware=True
    if a.prior_temperature is None:a.prior_temperature=2. if a.traffic_lights else 1.
    if a.congestion_aware is None:a.congestion_aware=False
    if a.skip_forced_wait is None:a.skip_forced_wait=False
    if a.supported_upgrades is None:a.supported_upgrades=False
    if a.supported_upgrades and not a.traffic_lights:p.error('Supported upgrades require traffic-light agent')
    if a.reward_scale<=0:p.error('Positive reward scale required')
    a.output.mkdir(parents=True)
    from signal_agent import SIGNAL_SCHEMA,CONTEXT_SCHEMA,signal_vector,transfer_signal_context
    schema=CONTEXT_SCHEMA if a.signal_context else (SIGNAL_SCHEMA if a.traffic_lights else (CONGESTION_SCHEMA if a.congestion_aware else GOAL_SCHEMA))
    config=dict(schema=schema,congestion_aware=a.congestion_aware,traffic_lights=bool(a.traffic_lights),signal_context=bool(a.signal_context),prior_temperature=a.prior_temperature,
                planner_aided=True,replay_source='hybrid-training',action_semantics='choose current house/destination connection or optional congestion bypass; visible router executes ordinary strokes'+('; place traffic lights at legal junctions' if a.traffic_lights else ''),
                restricted_tools=['road strokes including bridges','wait up to five seconds','upgrade choices']+(['traffic lights at legal junctions'] if a.traffic_lights else []),
                excluded_tools=['motorways','roundabouts','demolition','manual driveway edits']+([] if a.traffic_lights else ['traffic lights']),
                reward_schema='goal-trip-potential-gamma099-v1',reward='trip delta + gamma099 potential difference per macro decision',
                simulator_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                created_utc=datetime.now(timezone.utc).isoformat(),arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
                training_seeds=[1000,1099],validation_seeds=list(range(2000,2000+a.eval_count)),gamma=.99,gae_lambda=.99,
                learning_rate=.0001,ent_coef=.005,aggregate_rollout=256,reward_scale=a.reward_scale,
                decision_timing='choice-only-v1' if a.skip_forced_wait else 'five-second-wait-v1')
    if a.skip_forced_wait:config['reward_schema']='goal-trip-potential-gamma099-choice-v1'
    config['supported_upgrades']=a.supported_upgrades
    for name in ['goal_agent.py','signal_agent.py','upgrade_rules.py','planner_diagnostic.py','train_goal.py','environment.py','rewards.py','parallel.py','progress.py','shutdown.py']:
        (a.output/name).write_text((ROOT/'training'/name).read_text())
    factory=signal_vector if a.traffic_lights else vector
    extra=dict(signal_context=bool(a.signal_context),supported_upgrades=a.supported_upgrades) if a.traffic_lights else {}
    env=factory(a.workers,a.output,dotnet=a.dotnet,host_dll=a.host_dll,seeds=range(1000,1100),episodes_per_seed=1,seed_schedule='random',reward_scale=a.reward_scale,skip_forced_wait=a.skip_forced_wait,congestion_aware=a.congestion_aware,**extra)
    try:
        if a.resume:
            overrides=dict(n_steps=256//a.workers)
            if a.learning_rate is not None:overrides['learning_rate']=a.learning_rate
            model=MaskablePPO.load(a.resume,env=env,device='cpu',**overrides)
            if not isinstance(model.policy,GoalPolicy):raise ValueError('Resume requires a goal-policy checkpoint')
        else:
            model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=256//a.workers,batch_size=64,n_epochs=4,
                              gamma=.99,gae_lambda=.99,learning_rate=a.learning_rate or .0001,ent_coef=.005,verbose=0,
                              policy_kwargs=dict(features_extractor_kwargs=dict(prior_temperature=a.prior_temperature)))
            if a.warm_start:
                transfer_signal_context(model,preview)
                config['warm_start_source_sha256']=hashlib.sha256(a.warm_start.read_bytes()).hexdigest()
                config['optimizer_reset']=True
                del preview
        model.skip_forced_wait=a.skip_forced_wait
        model.congestion_aware=a.congestion_aware
        model.traffic_lights=bool(a.traffic_lights)
        model.supported_upgrades=a.supported_upgrades
        model.goal_reward_scale=a.reward_scale
        config['learning_rate']=model.learning_rate
        config['trainable_parameters']=sum(x.numel() for x in model.policy.parameters())
        (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        model.set_logger(configure(str(a.output),['csv']));save_checkpoint(model,a.output/'initial.zip')
        initial=torch.cat([v.detach().flatten() for v in model.policy.parameters()]).clone()
        print(f'PLANNER-AIDED GOAL EXPERIMENT | {a.output} | {config["trainable_parameters"]} parameters',flush=True)
        torch.manual_seed(43)
        before=evaluate(model,a.dotnet,a.host_dll,range(2000,2000+a.eval_count),cap=a.eval_seconds,record_dir=a.output/'initial-evaluation')
        (a.output/'before.json').write_text(json.dumps(before,indent=2)+'\n')
        def validation(policy):
            training=policy.policy.training
            try:
                with torch.random.fork_rng(devices=[]):return evaluate(policy,a.dotnet,a.host_dll,range(2000,2000+a.eval_count),cap=a.eval_seconds)
            finally:policy.policy.set_training_mode(training)
        callback=BudgetCallback(a.output,a.minutes,a.steps,1,15,config,validation,a.validation_minutes,a.stop_file)
        # The untrained starting policy is eligible, so a worse trained policy
        # cannot replace it merely by being the first periodic validation.
        callback.best_validation=sum(x['trips'] for x in before)/len(before)
        config['initial_validation_mean']=callback.best_validation
        (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        save_checkpoint(model,a.output/'validation-best.zip')
        from progress import atomic_json
        atomic_json(a.output/'validation-best.json',dict(mean_trips=callback.best_validation,policy_steps=0,
                    baseline=True,scores=[x['trips'] for x in before],checkpoint='validation-best.zip'))
        print(f'BASELINE | validation mean {callback.best_validation:.2f} | must improve to replace validation-best.zip',flush=True)
        interrupted=False;start=time.perf_counter()
        try:model.learn(total_timesteps=a.steps,callback=callback,reset_num_timesteps=True)
        except KeyboardInterrupt:
            interrupted=True;stop_and_save(model,env,callback,a.output)
        if not interrupted:save_checkpoint(model,a.output/'final.zip')
        elapsed=time.perf_counter()-start
        after=[]
        if not interrupted:
            after=evaluate(model,a.dotnet,a.host_dll,range(2000,2000+a.eval_count),cap=a.eval_seconds,record_dir=a.output/'final-evaluation')
            mean=sum(x['trips'] for x in after)/len(after)
            if mean>callback.best_validation:
                callback.best_validation=mean;save_checkpoint(model,a.output/'validation-best.zip')
                atomic_json(a.output/'validation-best.json',dict(mean_trips=mean,policy_steps=model.num_timesteps,baseline=False,
                            scores=[x['trips'] for x in after],checkpoint='validation-best.zip'))
        changed=not torch.equal(initial,torch.cat([v.detach().flatten() for v in model.policy.parameters()]))
        summary=dict(planner_aided=True,training_wall_seconds=elapsed,policy_steps=model.num_timesteps,completed_commands=callback.commands,
                     episodes=callback.episodes,best_training_score=callback.best,parameter_update_confirmed=changed,interrupted=interrupted,
                     stop_reason=callback.stop_reason or 'time_or_step_budget',before=before,after=after,
                     initial_validation_mean=sum(x['trips'] for x in before)/len(before),best_validation_mean=callback.best_validation,
                     limitations='Restricted planner-aided action abstraction and informed initialization; not the primitive all-tools agent.')
        (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('RESULT '+json.dumps(summary),flush=True)
    except KeyboardInterrupt:
        # Initial/final evaluation is outside learn(); preserve the current
        # model there too, rather than promising Ctrl+C saving only in rollouts.
        if 'model' in locals():
            path=save_checkpoint(model,a.output/'final.zip')
            print(f'STOP REQUESTED | saved {path} during evaluation; existing validation best retained',flush=True)
    finally:env.close()


if __name__=='__main__':main()

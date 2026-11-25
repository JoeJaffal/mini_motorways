"""Bounded PPO continuation of the same city policy on native practice or a mix."""
import argparse
from collections import defaultdict, deque
from functools import partial
import json
import shutil
from pathlib import Path
from time import monotonic
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.buffers import MaskableDictRolloutBuffer
from city_task_rollout_buffer import CityTaskRolloutBuffer
from city_gradient_audit import GradientAudit
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.logger import configure
from city_curriculum import CityCurriculumEnv, STAGES
from prepare_city_policy import sha256
from train_city_score_pilot import EPISODE_FIELDS, RecordEpisodes


class TaskEpisodes(RecordEpisodes):
    def __init__(self, output, worker_tasks=None, advantage_path=None):
        super().__init__(output)
        self.task_scores=defaultdict(lambda:deque(maxlen=100))
        self.worker_tasks=worker_tasks
        self.advantage_path=advantage_path

    def _on_step(self):
        # Copy native lesson outcomes into episode records; city rows use null.
        for info in self.locals['infos']:
            if 'episode' in info:
                info['episode'].update({key:info.get(key) for key in
                    ('new_deliveries','future_stock','future_targets','urgent_deliveries','bridge_stock','bridge_tiles')})
        result=super()._on_step()
        for info in self.locals['infos']:
            if 'episode' in info:
                episode=info['episode']
                self.task_scores[episode['exercise']].append(episode['r'])
        return result

    def _on_rollout_end(self):
        super()._on_rollout_end()
        if self.worker_tasks is not None:
            buffer=self.model.rollout_buffer
            labels=np.asarray(self.worker_tasks)
            assert buffer.advantages.shape==(self.model.n_steps,len(labels))
            groups={}
            for task in np.unique(labels):
                advantage=buffer.advantages[:,labels==task]
                returns=buffer.returns[:,labels==task]
                groups[str(task)]=dict(samples=int(advantage.size),advantage_mean=float(advantage.mean()),
                    advantage_std=float(advantage.std()),return_std=float(returns.std()))
                self.logger.record('pilot/advantage_std_'+str(task),float(advantage.std()))
            with self.advantage_path.open('a') as stream:
                stream.write(json.dumps(dict(decisions=self.num_timesteps,tasks=groups))+'\n')


def optimizer_steps(model):
    # Retained optimizer groups can contain frozen Wait/encoder parameters.
    # Count a trainable actor weight, rather than a frozen first group.
    optimizer=model.policy.optimizer
    parameter=next(p for group in optimizer.param_groups for p in group['params'] if p.requires_grad)
    step=optimizer.state.get(parameter,{}).get('step',0)
    return int(step.item() if isinstance(step,torch.Tensor) else step)


def publish(path, value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)


def worker(dll, stage, rank, count, seed, collapse, horizon, fast_priority_tail, reserve_warmup_seconds, reserve_delay_seconds, allow_bridges=False, city_starts=None, repeat_city_count=0, finite_city_horizon=False, mini_starts=None, small_city_horizon=60, fast_small_city_tail=False, repeat_mini_seed=None):
    if repeat_mini_seed is not None:
        from city_repeated_mini import CityRepeatedMiniEnv
        env=CityRepeatedMiniEnv(dll,repeat_mini_seed=repeat_mini_seed,stage=stage,worker=rank,workers=count,
            seed_start=seed,collapse_forced_wait=collapse,city_horizon=horizon,allow_bridges=allow_bridges,
            small_city_horizon=small_city_horizon,fast_small_city_tail=fast_small_city_tail)
        return Monitor(env,info_keywords=(*EPISODE_FIELDS,'exercise'))
    if mini_starts is not None:
        from mini_recorded_starts import MiniRecordedStartEnv
        env=MiniRecordedStartEnv(dll,mini_starts=mini_starts,stage=stage,worker=rank,workers=count,seed_start=seed,collapse_forced_wait=collapse,city_horizon=horizon,allow_bridges=allow_bridges,small_city_horizon=small_city_horizon,fast_small_city_tail=fast_small_city_tail)
        return Monitor(env,info_keywords=(*EPISODE_FIELDS,'exercise','prefix_id'))
    if repeat_city_count:
        from city_repeated_seeds import CityRepeatedSeedsEnv
        env=CityRepeatedSeedsEnv(dll,stage=stage,worker=rank,workers=count,seed_start=seed,collapse_forced_wait=collapse,city_horizon=horizon,allow_bridges=allow_bridges,repeat_city_count=repeat_city_count,finite_city_horizon=finite_city_horizon)
        return Monitor(env,info_keywords=(*EPISODE_FIELDS,'exercise','native_game_over','finite_horizon_end'))
    if city_starts is not None:
        from city_recorded_starts import CityRecordedStartEnv
        env=CityRecordedStartEnv(dll,stage=stage,worker=rank,workers=count,seed_start=seed,collapse_forced_wait=collapse,city_horizon=horizon,allow_bridges=allow_bridges,city_starts=city_starts)
        return Monitor(env,info_keywords=(*EPISODE_FIELDS,'exercise','initial_seconds','initial_trips','prefix_id'))
    return Monitor(CityCurriculumEnv(dll,stage,rank,count,seed,collapse_forced_wait=collapse,city_horizon=horizon,fast_priority_tail=fast_priority_tail,reserve_warmup_seconds=reserve_warmup_seconds,reserve_delay_seconds=reserve_delay_seconds,allow_bridges=allow_bridges,small_city_horizon=small_city_horizon,fast_small_city_tail=fast_small_city_tail), info_keywords=(*EPISODE_FIELDS,'exercise'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','parent','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--stage',choices=STAGES,required=True)
    parser.add_argument('--collapse-forced-wait',action='store_true')
    parser.add_argument('--fast-priority-tail',action='store_true')
    parser.add_argument('--fast-small-city-tail',action='store_true')
    parser.add_argument('--reserve-warmup-seconds',type=int,default=0)
    parser.add_argument('--reserve-delay-seconds',type=int,choices=range(1,17),default=None)
    parser.add_argument('--allow-bridges',action='store_true')
    parser.add_argument('--city-starts',type=Path,default=None)
    parser.add_argument('--mini-starts',type=Path,default=None)
    parser.add_argument('--cache-frozen-growth',action='store_true')
    parser.add_argument('--repeat-city-count',type=int,default=0)
    parser.add_argument('--repeat-mini-seed',type=int,default=None)
    parser.add_argument('--finite-city-horizon',action='store_true')
    parser.add_argument('--task-minibatches',action='store_true')
    parser.add_argument('--reserve-return-advantages',action='store_true')
    parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--rollouts',type=int,default=16)
    parser.add_argument('--seed-start',type=int,required=True)
    parser.add_argument('--learning-rate',type=float,default=1e-5)
    parser.add_argument('--value-coefficient',type=float,default=None)
    parser.add_argument('--critic-lr-scale',type=float,default=None)
    parser.add_argument('--gradient-audit-steps',type=int,default=0)
    parser.add_argument('--rollout-steps',type=int,default=128)
    parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--gae-lambda',type=float,default=None)
    parser.add_argument('--horizon',type=int,default=600)
    parser.add_argument('--small-city-horizon',type=int,default=60)
    parser.add_argument('--record-dir',type=Path,default=None)
    parser.add_argument('--save-every-rollouts',type=int,default=0)
    args=parser.parse_args()
    if args.repeat_mini_seed is not None and (args.stage!='single-connection' or args.mini_starts or args.city_starts or args.repeat_city_count or args.finite_city_horizon or args.fast_priority_tail or args.reserve_warmup_seconds or args.reserve_delay_seconds is not None):
        parser.error('Repeated mini seed requires single-connection stage and no other fixture overrides')
    if args.fast_small_city_tail and (not args.collapse_forced_wait or args.city_starts or args.repeat_city_count):
        parser.error('Fast small-city tail requires forced-Wait compression and ordinary or mini-start workers')
    if min(args.workers,args.rollouts,args.rollout_steps,args.batch_size)<1 or not np.isfinite(args.learning_rate) or args.learning_rate<=0:
        parser.error('Positive counts and finite positive learning rate required')
    if args.value_coefficient is not None and (not np.isfinite(args.value_coefficient) or args.value_coefficient<=0):
        parser.error('Value coefficient must be finite and positive')
    if args.critic_lr_scale is not None and (not np.isfinite(args.critic_lr_scale) or args.critic_lr_scale<=0):
        parser.error('Critic learning-rate scale must be finite and positive')
    if args.gae_lambda is not None and not 0<=args.gae_lambda<=1:
        parser.error('GAE lambda must be between zero and one')
    if args.workers*args.rollout_steps % args.batch_size:
        parser.error('Batch size must divide the rollout size')
    if not 0<args.horizon<=3600:
        parser.error('Horizon must be between one and 3600 seconds')
    if not 60<=args.small_city_horizon<=600:
        parser.error('Small-city horizon must be60..600 seconds')
    if args.gradient_audit_steps<0:parser.error('Gradient audit steps cannot be negative')
    if args.city_starts is not None and (args.stage!='city' or not args.allow_bridges or args.workers%4):
        parser.error('Recorded starts require bridge-enabled city training and a multiple of four workers')
    if args.mini_starts is not None and (args.stage!='expansion-balanced' or args.workers%16 or args.city_starts is not None or args.repeat_city_count or args.reserve_warmup_seconds or args.reserve_delay_seconds is not None or args.fast_priority_tail):
        parser.error('Mini starts require expansion-balanced, a multiple of16 workers and no other start/tail overrides')
    if args.repeat_city_count<0 or (args.repeat_city_count and (args.stage!='city' or args.city_starts is not None)):
        parser.error('Repeated seeds require city stage and no recorded starts')
    if args.finite_city_horizon and not args.repeat_city_count:
        parser.error('Finite horizon is restricted to repeated-city diagnostics')
    if args.save_every_rollouts<0:
        parser.error('Checkpoint interval cannot be negative')
    if args.fast_priority_tail and not args.collapse_forced_wait:
        parser.error('Fast priority tail requires forced-Wait compression')
    if not 0<=args.reserve_warmup_seconds<=6:
        parser.error('Reserve warmup must be 0..6 seconds')
    if args.reserve_delay_seconds is not None and args.reserve_warmup_seconds:
        parser.error('Explicit reserve delay and warmup cannot be combined')
    if args.task_minibatches and (args.stage not in ('strategy-balanced','expansion-balanced') or args.workers%16):
        parser.error('Task minibatches require a balanced stage and a multiple of16 workers')
    if args.reserve_return_advantages and args.stage!='strategy-balanced':
        parser.error('Reserve return advantages require strategy-balanced')
    if args.reserve_return_advantages and (not args.task_minibatches or args.gae_lambda!=1):
        parser.error('Reserve return advantages require task minibatches and GAE lambda=1')
    torch.set_num_threads(1)
    args.output.mkdir(parents=True,exist_ok=False)
    if args.record_dir is not None:
        args.record_dir.mkdir(parents=True,exist_ok=False)
    def archive_progress():
        if args.record_dir is not None:
            for name in ('config.json','checkpoints.json','complete.json','episodes.jsonl','progress.csv','task_advantages.jsonl','gradient_audit.jsonl'):
                source=args.output/name
                if source.exists():shutil.copy2(source,args.record_dir/name)
    config=vars(args).copy()
    config={k:str(v) if isinstance(v,Path) else v for k,v in config.items()}
    config.update(city_starts_sha256=sha256(args.city_starts) if args.city_starts else None,recorded_start_workers=args.workers*3//4 if args.city_starts else 0)
    config.update(mini_starts_sha256=sha256(args.mini_starts) if args.mini_starts else None,mini_start_workers=args.workers//4 if args.mini_starts else 0)
    config.update(parent_sha256=sha256(args.parent),host_sha256=sha256(args.dll),decision_budget=args.workers*args.rollout_steps*args.rollouts)
    publish(args.output/'config.json',config)
    archive_progress()
    env=SubprocVecEnv([partial(worker,args.dll,args.stage,i,args.workers,args.seed_start,args.collapse_forced_wait,args.horizon,args.fast_priority_tail,args.reserve_warmup_seconds,args.reserve_delay_seconds,args.allow_bridges,args.city_starts,args.repeat_city_count,args.finite_city_horizon,args.mini_starts,args.small_city_horizon,args.fast_small_city_tail,args.repeat_mini_seed) for i in range(args.workers)],start_method='forkserver')
    try:
        overrides={} if args.gae_lambda is None else dict(gae_lambda=args.gae_lambda)
        if args.value_coefficient is not None:overrides['vf_coef']=args.value_coefficient
        worker_tasks=([('city' if i%16<8 else 'reserve' if i%16<12 else 'priority')
                       for i in range(args.workers)] if args.stage=='strategy-balanced' else ['city']*args.workers if args.stage=='city' else None)
        if args.stage=='single-connection':worker_tasks=['single-connection']*args.workers
        if args.stage=='expansion-balanced':
            if args.workers%16:raise ValueError('Expansion balance requires a multiple of16 workers')
            worker_tasks=[('city' if i%16<8 else 'two-arrivals' if i%16<12 else 'single-connection') for i in range(args.workers)]
        buffer_options=dict(rollout_buffer_class=CityTaskRolloutBuffer if args.task_minibatches else MaskableDictRolloutBuffer,
                            rollout_buffer_kwargs=dict(worker_tasks=worker_tasks,return_advantage_tasks=('reserve',) if args.reserve_return_advantages else ()) if args.task_minibatches else {})
        model=MaskablePPO.load(args.parent,env=env,device='cuda',learning_rate=args.learning_rate,n_steps=args.rollout_steps,batch_size=args.batch_size,**buffer_options,**overrides)
        if getattr(model, 'route_outcome_critic', False) or getattr(model.policy, 'bandit_zero_baseline', False):
            raise ValueError('Export the native critic and PPO configuration before native curriculum training')
        if args.cache_frozen_growth:
            from city_wide_strategy_policy import CityWideStrategyFeatures
            if not isinstance(model.policy.features_extractor,CityWideStrategyFeatures):
                raise ValueError('Frozen-growth cache requires the wide city policy')
            model.policy.features_extractor.growth_cache_enabled=True
        if args.critic_lr_scale is not None:
            from city_optimizer_settings import set_critic_lr_scale
            config['critic_optimizer_group']=set_critic_lr_scale(model.policy,args.critic_lr_scale)
        if args.task_minibatches and not model.normalize_advantage:
            raise ValueError('Task minibatches require PPO advantage normalization')
        config.update(policy_class=type(model.policy).__name__,critic_features_detached=bool(getattr(model.policy,'critic_features_detached',False)),gamma=model.gamma,n_epochs=model.n_epochs,vf_coef=model.vf_coef,loaded_optimizer_steps=optimizer_steps(model),normalize_advantage=model.normalize_advantage,
                      sampling_seed=model.seed,
                      ent_coef=model.ent_coef,target_kl=model.target_kl,max_grad_norm=model.max_grad_norm,
                      optimizer_lr_scales=[group.get('lr_scale',1.) for group in model.policy.optimizer.param_groups])
        publish(args.output/'config.json',config);archive_progress()
        # Saved reporting history may contain another curriculum's short tasks.
        # Clear only statistics; retain weights, optimizer and update counters.
        if model.ep_info_buffer is not None:model.ep_info_buffer.clear()
        if model.ep_success_buffer is not None:model.ep_success_buffer.clear()
        audit=(GradientAudit(model.policy.optimizer,args.output/'gradient_audit.jsonl',args.gradient_audit_steps,
                             lambda:getattr(model.rollout_buffer,'active_task',args.stage)) if args.gradient_audit_steps else None)
        start=model.num_timesteps
        initial_optimizer_steps=optimizer_steps(model)
        model.set_logger(configure(str(args.output),['csv']))
        then=monotonic();saves=[]
        with (args.output/'episodes.jsonl').open('x') as stream:
            callback=TaskEpisodes(stream,worker_tasks,args.output/'task_advantages.jsonl')
            for i in range(args.rollouts):
                before_optimizer_steps=optimizer_steps(model)
                model.learn(total_timesteps=args.workers*args.rollout_steps,reset_num_timesteps=False,callback=callback)
                if audit is not None and audit.count>=audit.limit:audit.close()
                performed=optimizer_steps(model)-before_optimizer_steps
                possible=args.workers*args.rollout_steps//args.batch_size*model.n_epochs
                model.logger.record('pilot/optimizer_steps_this_rollout',performed)
                model.logger.record('pilot/optimizer_steps_possible',possible)
                print(f'OPTIMIZER | {performed}/{possible} maximum updates | KL safeguard retained',flush=True)
                metrics=model.logger.name_to_value
                if not all(np.isfinite(metrics[k]) for k in ('train/loss','train/approx_kl','train/value_loss')):
                    raise RuntimeError('Nonfinite PPO loss')
                model.logger.dump(step=model.num_timesteps)
                scores=[episode['r'] for episode in model.ep_info_buffer]
                mean=float(np.mean(scores)) if scores else float('nan')
                label='city + recorded starts' if args.city_starts else args.stage
                metric='remaining deliveries' if args.city_starts else 'mixed-task score (not city score)' if args.stage=='expansion-balanced' else 'score'
                mean_display=f'{mean:.2f}' if scores else 'pending (no completed episodes)'
                print(f'PPO | {label} | {model.num_timesteps-start} decisions | {callback.completed} episodes | recent mean {metric} {mean_display} | last scores {scores[-8:]}',flush=True)
                if args.stage!='city' or args.city_starts is not None:
                    print('TASK SCORES | recent completed episodes | '+' | '.join(
                        f'{task}: {np.mean(values):.2f} (n={len(values)})'
                        for task,values in sorted(callback.task_scores.items())),flush=True)
                if i+1 in {max(1,args.rollouts//2),args.rollouts} or (args.save_every_rollouts and (i+1)%args.save_every_rollouts==0):
                    name='final' if i+1==args.rollouts else 'midpoint' if i+1==max(1,args.rollouts//2) else f'checkpoint-{model.num_timesteps-start:09d}'
                    path=args.output/(name+'.zip')
                    pending=args.output/(name+'.pending.zip');model.save(pending);pending.replace(path)
                    saves.append(dict(path=str(path),sha256=sha256(path),added_decisions=model.num_timesteps-start,optimizer_steps_added=optimizer_steps(model)-initial_optimizer_steps,episodes=callback.completed,seconds=monotonic()-then))
                    publish(args.output/'checkpoints.json',saves)
                    archive_progress()
        assert model.num_timesteps-start == config['decision_budget']
        if args.city_starts is not None:assert sha256(args.city_starts)==config['city_starts_sha256']
        assert sha256(args.parent)==config['parent_sha256'] and sha256(args.dll)==config['host_sha256']
        publish(args.output/'complete.json',dict(checkpoints=saves,seconds=monotonic()-then))
        archive_progress()
    finally:env.close()

if __name__=='__main__':main()

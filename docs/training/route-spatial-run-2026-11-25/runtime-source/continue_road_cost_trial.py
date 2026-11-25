"""Continue a frozen road-cost recipe with fresh episodes and preserved Adam."""
import argparse
import json
import math
import random
import time
from functools import partial
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.logger import configure
from train_road_cost_trial import worker, Episodes
from train_city_curriculum import optimizer_steps
from city_gradient_audit import GradientAudit
from prepare_city_policy import sha256


def mixed_worker(dll,rank,cost,seed):
    from stable_baselines3.common.monitor import Monitor
    from mixed_city_road_cost_env import MixedCityRoadCostEnv
    from train_road_cost_trial import FIELDS
    return Monitor(MixedCityRoadCostEnv(dll,road_cost=cost,worker=rank,workers=16,seed_start=seed),info_keywords=FIELDS)


def publish(path, data):
    pending = path.with_suffix(path.suffix+'.pending')
    pending.write_text(json.dumps(data, indent=2)+'\n')
    pending.replace(path)


def main():
    p = argparse.ArgumentParser()
    for name in ('dll', 'parent', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--road-cost', type=float, required=True)
    p.add_argument('--seed-start', type=int, required=True)
    p.add_argument('--rng-seed', type=int, default=241124)
    p.add_argument('--completed-decisions', type=int, default=16384)
    p.add_argument('--target-decisions', type=int, default=262144)
    p.add_argument('--critic-lr-scale', type=float, choices=(.1, 1.), default=.1,
                   help='Explicit separate ablation: critic Adam rate only; actor rates/reward unchanged.')
    p.add_argument('--mixed-city',action='store_true',help='Half city workers; quarter tight and quarter generous practice. City reward remains native score.')
    a = p.parse_args()
    remaining = a.target_decisions-a.completed_decisions
    if remaining <= 0 or remaining % 8192:
        raise ValueError('Budget must be positive whole 8192-decision rollouts')
    a.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    random.seed(a.rng_seed); np.random.seed(a.rng_seed); torch.manual_seed(a.rng_seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(a.rng_seed)
    parent_hash, host_hash = sha256(a.parent), sha256(a.dll)
    factory=mixed_worker if a.mixed_city else worker
    env = SubprocVecEnv([partial(factory,a.dll,i,a.road_cost,a.seed_start) for i in range(16)],start_method='forkserver')
    try:
        model = MaskablePPO.load(a.parent, env=env, device='cuda')
        # Loading may restore the model's old seed; apply the declared continuation seed afterwards.
        random.seed(a.rng_seed); np.random.seed(a.rng_seed); torch.manual_seed(a.rng_seed)
        torch.cuda.manual_seed_all(a.rng_seed)
        expected = dict(n_steps=512, batch_size=128, n_epochs=4, gamma=1., gae_lambda=1.,
                        vf_coef=.00001, ent_coef=.01, target_kl=.03, learning_rate=.0003)
        for key, value in expected.items():
            if getattr(model,key) != value: raise RuntimeError(f'Recipe changed: {key}')
        loaded_scales = [g.get('lr_scale',1) for g in model.policy.optimizer.param_groups]
        assert loaded_scales[:3] == [1.,.3,.1] and loaded_scales[3] in (.1,1.)
        model.policy.optimizer.param_groups[3]['lr_scale'] = a.critic_lr_scale
        initial_steps = optimizer_steps(model)
        if initial_steps < 512: raise RuntimeError('Missing prior Adam progress')
        if model.ep_info_buffer is not None: model.ep_info_buffer.clear()
        if model.ep_success_buffer is not None: model.ep_success_buffer.clear()
        config = dict(parent=str(a.parent), parent_sha256=parent_hash, host_sha256=host_hash,
                      road_cost=a.road_cost, seed_start=a.seed_start, rng_seed=a.rng_seed,
                      initial_optimizer_steps=initial_steps, completed_decisions=a.completed_decisions,
                      model_start_timesteps=model.num_timesteps,
                      target_decisions=a.target_decisions, recipe=expected,
                      loaded_optimizer_lr_scales=loaded_scales,
                      optimizer_lr_scales=[g.get('lr_scale',1) for g in model.policy.optimizer.param_groups],
                      mixed_city=a.mixed_city,
                      continuation='Weights and Adam restored; fresh nonoverlapping episodes and explicit RNG reseed. Not bitwise trajectory continuation.')
        publish(a.output/'config.json', config)
        model.set_logger(configure(str(a.output), ['csv']))
        callback = Episodes(a.output/'episodes.jsonl')
        start = model.num_timesteps; then=time.monotonic(); saves=[]
        protected = {k:v.detach().cpu().clone() for k,v in model.policy.state_dict().items()
                     if 'growth_strategy_' not in k and not k.startswith('value_net.')}
        for rollout in range(remaining//8192):
            previous_groups = [[p.detach().clone() for p in g['params']] for g in model.policy.optimizer.param_groups]
            audit = GradientAudit(model.policy.optimizer,a.output/'gradient_audit.jsonl',4,
                                  task=lambda: a.completed_decisions+model.num_timesteps-start)
            model.learn(total_timesteps=8192, reset_num_timesteps=False, callback=callback)
            audit.close()
            metrics = model.logger.name_to_value
            if not all(math.isfinite(float(metrics[k])) for k in ('train/loss','train/value_loss','train/approx_kl')):
                raise RuntimeError('Nonfinite PPO metrics')
            assert all(torch.isfinite(v).all() for v in model.policy.state_dict().values())
            assert all(torch.equal(v,model.policy.state_dict()[k].cpu()) for k,v in protected.items())
            model.logger.dump(step=model.num_timesteps)
            cumulative = a.completed_decisions+model.num_timesteps-start
            group_updates = []
            for g, previous in zip(model.policy.optimizer.param_groups,previous_groups):
                delta = sum((p.detach()-old).square().sum() for p,old in zip(g['params'],previous)).sqrt()
                magnitude = sum(old.square().sum() for old in previous).sqrt()
                group_updates.append(dict(delta_l2=float(delta),initial_l2=float(magnitude),lr_scale=g.get('lr_scale',1)))
            with (a.output/'parameter_updates.jsonl').open('a') as f:
                f.write(json.dumps(dict(cumulative_decisions=cumulative,groups=group_updates))+'\n')
            checkpoint = a.output/f'checkpoint-{cumulative:09d}.zip'
            if checkpoint.exists(): raise FileExistsError(checkpoint)
            pending = checkpoint.with_suffix('.pending.zip')
            model.save(pending); pending.replace(checkpoint)
            row = dict(checkpoint=str(checkpoint), sha256=sha256(checkpoint), cumulative_decisions=cumulative,
                       added_decisions=model.num_timesteps-start, optimizer_steps=optimizer_steps(model),
                       optimizer_steps_added=optimizer_steps(model)-initial_steps, episodes=len(callback.rows),
                       seconds=time.monotonic()-then, next_seed_cursors=env.get_attr('cursor'),
                       next_episode_cursors=env.get_attr('episode'))
            saves.append(row); publish(a.output/'checkpoints.json',saves)
            recent=callback.rows[-100:]
            row['recent_native_mean']=sum(x['trips'] for x in recent)/len(recent)
            row['recent_paid_mean']=sum(x['paid_units'] for x in recent)/len(recent)
            row['recent_success_rate']=sum(x['trips']>0 for x in recent)/len(recent)
            publish(a.output/'status.json',dict(status='running',**row))
            print(f"PPO | cost={a.road_cost} | {cumulative}/{a.target_decisions} decisions | "
                  f"{'mixed-task-native' if a.mixed_city else 'native'}={row['recent_native_mean']:.3f} | success={row['recent_success_rate']:.1%} | "
                  f"paid={row['recent_paid_mean']:.3f} | Adam={row['optimizer_steps']}",flush=True)
            if a.mixed_city:
                # Do not present mixed-task return as a comparable city learning curve.
                for exercise in ('city','small-city-offset-single','small-city-offset-stock'):
                    group=[x for x in callback.rows if x['exercise']==exercise][-100:]
                    if group:
                        print(f"TASK | {exercise} | episodes={len(group)} | native={sum(x['trips'] for x in group)/len(group):.3f} | paid={sum(x['paid_units'] for x in group)/len(group):.3f}",flush=True)
        assert model.num_timesteps-start==remaining
        assert sha256(a.parent)==parent_hash and sha256(a.dll)==host_hash
        publish(a.output/'complete.json',dict(config=config,checkpoints=saves,seconds=time.monotonic()-then))
        publish(a.output/'status.json',dict(status='complete',**saves[-1]))
    finally:
        env.close()


if __name__ == '__main__':
    main()

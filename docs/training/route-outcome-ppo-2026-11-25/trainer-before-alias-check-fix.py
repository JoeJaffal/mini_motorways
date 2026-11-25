"""Bounded PPO road-placement practice with frozen shared-state Wait choices."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.logger import configure
from city_route_outcome import CityRouteOutcomeEnv
from city_wait_choice_policy import CityRoadHeadsAfterWaitPolicy
from prepare_city_policy import sha256
from prepare_city_wait_repair import optimizer_by_name, assert_state_equal
from train_city_wait_decision import publish_json


def worker(dll, rank, workers, seed):
    def make():
        return Monitor(CityRouteOutcomeEnv(dll, worker=rank, workers=workers,
                       seed_start=seed, fast_small_city_tail=True))
    return make


class Episodes(BaseCallback):
    def __init__(self, path, start):
        super().__init__()
        self.path, self.start, self.rows = path, start, []

    def _on_step(self):
        with self.path.open('a') as f:
            for info in self.locals['infos']:
                if 'episode' not in info:
                    continue
                episode = info['episode']
                assert not info['TimeLimit.truncated']
                assert abs(episode['r']-info['task_return']) < 1e-6
                assert (1 <= info['task_return'] <= 1.25) if info['task_success'] else info['task_return'] == 0
                row = dict(added_decisions=self.model.num_timesteps-self.start, **episode,
                    **{k: info[k] for k in ('exercise', 'seed', 'task_success', 'task_return',
                        'paid_units', 'road_actions', 'zero_cost_builds', 'trips', 'road_stock',
                        'seconds', 'terminal_observation_may_follow_forced_tail')})
                self.rows.append(row)
                f.write(json.dumps(row)+'\n')
        return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'dll', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--workers', type=int, default=16)
    p.add_argument('--rollout-steps', type=int, default=512)
    p.add_argument('--rollouts', type=int, default=8)
    p.add_argument('--batch-size', type=int, default=128)
    p.add_argument('--epochs', type=int, default=4)
    p.add_argument('--seed-start', type=int, default=248000000)
    p.add_argument('--device', default='cuda')
    a = p.parse_args()
    if min(a.workers, a.rollout_steps, a.rollouts, a.batch_size, a.epochs) < 1:
        p.error('Positive sizes required')
    a.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    digest, host_digest = sha256(a.parent), sha256(a.dll)
    env = SubprocVecEnv([worker(str(a.dll), i, a.workers, a.seed_start) for i in range(a.workers)], start_method='forkserver')
    try:
        model = MaskablePPO.load(a.parent, env=env, device=a.device, n_steps=a.rollout_steps,
                                batch_size=a.batch_size, n_epochs=a.epochs)
        assert model.route_outcome_critic and isinstance(model.policy, CityRoadHeadsAfterWaitPolicy)
        assert model.gamma == 1 and model.gae_lambda == 1 and model.vf_coef == .5
        model.policy.features_extractor.growth_cache_enabled = True
        model.set_logger(configure(str(a.output), ['csv']))
        trainable = {n for n, param in model.policy.named_parameters() if param.requires_grad}
        assert len(trainable) == 10
        fixed_weights = {k: v.detach().cpu().clone() for k, v in model.policy.state_dict().items() if k not in trainable}
        old_states = {k: v for k, v in optimizer_by_name(model.policy).items() if k not in trainable}
        start = model.num_timesteps
        budget = a.workers*a.rollout_steps
        callback = Episodes(a.output/'episodes.jsonl', start)
        config = dict(**{k: str(v) if isinstance(v, Path) else v for k, v in vars(a).items()},
            parent_sha256=digest, host_sha256=host_digest, start_timesteps=start,
            gamma=model.gamma, vf_coef=model.vf_coef, ent_coef=model.ent_coef,
            learning_rate=model.learning_rate, target_kl=model.target_kl,
            native_critic_template_sha256=model.native_critic_template_sha256,
            trainable=sorted(trainable), reward='First delivery:1+.20*remaining-stock fraction+.05/(1+road actions); failure0. Not city score.')
        (a.output/'config.json').write_text(json.dumps(config, indent=2)+'\n')
        checkpoints = []
        began = time.monotonic()
        for rollout in range(1, a.rollouts+1):
            previous = len(callback.rows)
            model.learn(total_timesteps=budget, reset_num_timesteps=False, callback=callback)
            assert np.isfinite(model.rollout_buffer.advantages).all()
            for name, value in fixed_weights.items():
                torch.testing.assert_close(value, model.policy.state_dict()[name].detach().cpu(), rtol=0, atol=0)
            assert all(torch.isfinite(v).all() for v in model.policy.state_dict().values())
            current = optimizer_by_name(model.policy)
            assert_state_equal(old_states, {k: v for k, v in current.items() if k not in trainable})
            rows = callback.rows[previous:]
            by_case = {case: dict(games=len(g), successes=sum(r['task_success'] for r in g),
                        mean_paid=float(np.mean([r['paid_units'] for r in g])),
                        mean_builds=float(np.mean([r['road_actions'] for r in g])))
                       for case in sorted({r['exercise'] for r in rows}) if (g := [r for r in rows if r['exercise'] == case])}
            added = model.num_timesteps-start
            path = a.output/('final.zip' if rollout == a.rollouts else f'checkpoint-{added:09d}.zip')
            model.save(path)
            checkpoints.append(dict(path=str(path.absolute()), sha256=sha256(path), added_decisions=added,
                seconds=time.monotonic()-began, cases=by_case, frozen_weights_and_adam_exact=True,
                trainable_adam_steps={k: int(v['step']) for k, v in current.items() if k in trainable}))
            publish_json(a.output/'checkpoints.json', checkpoints)
            print('PPO ROUTE OUTCOME |', added, 'decisions |', json.dumps(by_case), flush=True)
        assert sha256(a.parent) == digest and sha256(a.dll) == host_digest
        publish_json(a.output/'complete.json', dict(checkpoints=checkpoints, elapsed_seconds=time.monotonic()-began))
    finally:
        env.close()


if __name__ == '__main__':
    main()

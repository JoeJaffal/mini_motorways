"""Disposable PPO integration check for the opt-in route-outcome task."""
import json
from pathlib import Path
import time
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
from city_route_outcome import CityRouteOutcomeEnv
from prepare_city_policy import sha256
from prepare_city_wait_repair import optimizer_by_name, assert_state_equal


class Audit(BaseCallback):
    def __init__(self):
        super().__init__()
        self.rows = []

    def _on_step(self):
        for info in self.locals['infos']:
            if 'episode' not in info:
                continue
            assert not info['TimeLimit.truncated']
            assert abs(info['episode']['r']-info['task_return']) < 1e-6
            assert 1 <= info['task_return'] <= 1.25 if info['task_success'] else info['task_return'] == 0
            self.rows.append(dict(reward=info['task_return'], success=info['task_success'],
                                  native_trips=info['trips'], paid=info['paid_units'],
                                  zero_cost_builds=info['zero_cost_builds'], decisions=info['episode']['l']))
        return True


def main():
    torch.set_num_threads(1)
    root = Path.cwd()
    parent = root/'output/training/route-outcome-smoke-initial-01/start.zip'
    dll = root/'output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'
    output = root/'output/training/route-outcome-ppo-smoke-03'
    output.mkdir(exist_ok=False)
    archive = Path(__file__).parent
    env = DummyVecEnv([lambda i=i: Monitor(CityRouteOutcomeEnv(str(dll), worker=i, workers=16,
                                                            seed_start=244010000, fast_small_city_tail=True))
                       for i in (0, 12)])
    try:
        model = MaskablePPO.load(parent, env=env, device='cuda', n_steps=64, batch_size=32, n_epochs=1)
        assert model.route_outcome_critic and model.gamma == 1 and model.vf_coef == .5
        model.policy.features_extractor.growth_cache_enabled = True
        old_states = {n: {k: v.detach().cpu().clone() if torch.is_tensor(v) else v for k, v in state.items()} for n, state in optimizer_by_name(model.policy).items()}
        trainable = {name for name, p in model.policy.named_parameters() if p.requires_grad}
        assert len(trainable) == 10
        frozen = {name: p.detach().cpu().clone() for name, p in model.policy.named_parameters() if not p.requires_grad}
        start = model.num_timesteps
        before = sha256(parent)
        audit = Audit()
        began = time.monotonic()
        model.learn(total_timesteps=128, reset_num_timesteps=False, callback=audit)
        assert model.num_timesteps-start == 128 and audit.rows
        assert np.isfinite(model.rollout_buffer.advantages).all()
        assert all(torch.isfinite(value).all() for value in model.policy.state_dict().values())
        for name, p in model.policy.named_parameters():
            if name in frozen:
                torch.testing.assert_close(frozen[name], p.detach().cpu(), rtol=0, atol=0)
        model.save(output/'final.zip')
        restored = MaskablePPO.load(output/'final.zip', device='cpu')
        new_states = optimizer_by_name(restored.policy)
        assert_state_equal({n: s for n, s in old_states.items() if n not in trainable},
                           {n: s for n, s in new_states.items() if n not in trainable})
        for name in trainable:
            assert int(new_states[name]['step']) == int(old_states.get(name, {}).get('step', 0))+4
        assert restored.route_outcome_critic and sha256(parent) == before
        report = dict(decisions=128, episodes=len(audit.rows), updates=4,
                      seconds=time.monotonic()-began, checkpoint_sha256=sha256(output/'final.zip'),
                      parent_sha256=before, native_host_sha256=sha256(dll),
                      frozen_wait_encoder_and_their_adam_exact=True, task_critic_updated=True,
                      task_return_ledger=True, finite_task_no_bootstrap=True, finite_reload=True,
                      limits='Disposable PPO smoke only. No production route lesson or performance claim.')
        (archive/'ppo-smoke-verification.json').write_text(json.dumps(report, indent=2)+'\n')
        (archive/'ppo-smoke-episodes.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in audit.rows))
        print(json.dumps(report, indent=2))
    finally:
        env.close()


if __name__ == '__main__':
    main()

"""Preserve city weights/Adam while enabling only Wait-head bandit learning."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from city_wait_choice_policy import CityWaitBanditPolicy
from city_wait_decision import CityWaitDecisionEnv, SCHEDULE
from prepare_city_policy import masked_probs, sha256
from prepare_city_wait_repair import optimizer_by_name, assert_state_equal


def main():
    p = argparse.ArgumentParser()
    for name in ('parent', 'dll', 'output', 'archive'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); torch.set_num_threads(1)
    a.output.mkdir(parents=True, exist_ok=False); a.archive.mkdir(parents=True, exist_ok=False)
    digest = sha256(a.parent)
    source = MaskablePPO.load(a.parent, device='cpu')
    env = CityWaitDecisionEnv(str(a.dll))
    try:
        config = {name: deepcopy(getattr(source, name)) for name in (
            'n_steps', 'batch_size', 'n_epochs', 'learning_rate', 'gamma', 'gae_lambda',
            'ent_coef', 'vf_coef', 'max_grad_norm', 'target_kl', 'clip_range',
            'clip_range_vf', 'normalize_advantage', 'policy_kwargs')}
        config.update(gamma=0., vf_coef=0.)
        result = MaskablePPO(CityWaitBanditPolicy, env, device='cpu', seed=source.seed, **config)
        result.policy.load_state_dict(source.policy.state_dict(), strict=True)
        old_names = {id(p): name for name, p in source.policy.named_parameters()}
        new_names = {id(p): name for name, p in result.policy.named_parameters()}
        groups = {tuple(old_names[id(p)] for p in g['params']): g for g in source.policy.optimizer.param_groups}
        states = optimizer_by_name(source.policy)
        for group in result.policy.optimizer.param_groups:
            names = tuple(new_names[id(p)] for p in group['params'])
            if names in groups:
                group.update({k: deepcopy(v) for k, v in groups[names].items() if k != 'params'})
            for name, param in zip(names, group['params']):
                if name in states:
                    result.policy.optimizer.state[param] = deepcopy(states[name])
        assert_state_equal(states, optimizer_by_name(result.policy))
        for name in ('num_timesteps', '_n_updates', '_current_progress_remaining'):
            setattr(result, name, getattr(source, name))
        result.save(a.output/'start.zip')
        loaded = MaskablePPO.load(a.output/'start.zip', device='cpu')
        assert_state_equal(states, optimizer_by_name(loaded.policy))
        for name, value in source.policy.state_dict().items():
            torch.testing.assert_close(value, loaded.policy.state_dict()[name], rtol=0, atol=0)
        trainable = [name for name, p in loaded.policy.named_parameters() if p.requires_grad]
        assert len(trainable) == 8 and all('growth_strategy_wait.' in n or 'growth_strategy_visual_wait.' in n for n in trainable)
        errors = []
        for i, case in enumerate(SCHEDULE):
            obs, _ = env.reset(options=dict(case=case, scenario_seed=244002000+i))
            mask = env.action_masks(); x = masked_probs(source, obs, mask); y = masked_probs(loaded, obs, mask)
            np.testing.assert_allclose(x, y, rtol=1e-6, atol=1e-7); errors.append(float(abs(x-y).max()))
            tensor, _ = loaded.policy.obs_to_tensor(obs)
            with torch.no_grad():
                assert not loaded.policy.predict_values(tensor).count_nonzero()
                retained_value = MaskableActorCriticPolicy.predict_values(loaded.policy, tensor)
                torch.testing.assert_close(retained_value, source.policy.predict_values(tensor), rtol=0, atol=0)
        assert sha256(a.parent) == digest
        report = dict(parent=str(a.parent), parent_sha256=digest, checkpoint_sha256=sha256(a.output/'start.zip'),
            host_sha256=sha256(a.dll), preserved_timesteps=loaded.num_timesteps,
            retained_adam_parameters=len(states), retained_adam_steps=sorted({int(s['step']) for s in states.values()}),
            trainable=trainable, initial_actor_max_error=max(errors), shared_states=len(errors),
            all_weights_exact=True, original_city_critic_and_adam_preserved=True, bandit_values_zero=True,
            limits='Preparation only. One-step binary objective; not city promotion. Parent remains unchanged.')
        (a.archive/'migration-checks.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
    finally:
        env.close()


if __name__ == '__main__':
    main()

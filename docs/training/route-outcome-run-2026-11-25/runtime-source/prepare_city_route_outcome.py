"""Preserve the actor while switching between task and retained native critics."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_route_outcome import CityRouteOutcomeEnv
from city_curriculum import SMALL_TIGHT, SMALL_STOCK
from city_wait_choice_policy import CityNativeAfterWaitPolicy, CityRoadHeadsAfterWaitPolicy
from prepare_city_policy import masked_probs, sha256
from prepare_city_wait_repair import optimizer_by_name, assert_state_equal


def critic(name):
    return name.startswith('value_net.')


def groups_by_name(policy):
    names = {id(p): n for n, p in policy.named_parameters()}
    return {tuple(names[id(p)] for p in group['params']): group for group in policy.optimizer.param_groups}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'native-template', 'dll', 'output', 'archive'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--direction', choices=('lesson', 'native'), required=True)
    parser.add_argument('--native-mode', choices=('road-heads', 'joint'), default='road-heads')
    a = parser.parse_args()
    torch.set_num_threads(1)
    a.output.mkdir(parents=True, exist_ok=False)
    a.archive.mkdir(parents=True, exist_ok=False)
    digests = {str(p): sha256(p) for p in (a.parent, a.native_template, a.dll)}
    source = MaskablePPO.load(a.parent, device='cpu')
    template = MaskablePPO.load(a.native_template, device='cpu')
    assert not getattr(template, 'route_outcome_critic', False)
    assert not getattr(template.policy, 'bandit_zero_baseline', False)
    assert template.gamma > 0 and template.vf_coef > 0
    already_lesson = getattr(source, 'route_outcome_critic', False)
    if already_lesson:
        assert source.native_critic_template_sha256 == sha256(a.native_template)
    if a.direction == 'native' and not already_lesson:
        raise ValueError('Native restoration requires a route-outcome lesson checkpoint')
    old_states = optimizer_by_name(source.policy)
    native_states = optimizer_by_name(template.policy)
    if a.direction == 'lesson' and not already_lesson:
        # Record and verify the untouched checkpoint that retains the city critic.
        for name, value in source.policy.state_dict().items():
            if critic(name):
                torch.testing.assert_close(value, template.policy.state_dict()[name], rtol=0, atol=0)
        assert_state_equal({n: s for n, s in old_states.items() if critic(n)},
                           {n: s for n, s in native_states.items() if critic(n)})
    env = CityRouteOutcomeEnv(str(a.dll))
    try:
        names = ('n_steps', 'batch_size', 'n_epochs', 'learning_rate', 'gamma', 'gae_lambda',
                 'ent_coef', 'vf_coef', 'max_grad_norm', 'target_kl', 'clip_range', 'clip_range_vf',
                 'normalize_advantage', 'policy_kwargs')
        config_source = source if a.direction == 'lesson' else template
        config = {name: deepcopy(getattr(config_source, name)) for name in names}
        if a.direction == 'lesson':
            config.update(gamma=1., gae_lambda=1., vf_coef=.5, clip_range_vf=None)
        policy = (CityNativeAfterWaitPolicy if a.direction == 'native' and a.native_mode == 'joint'
                  else CityRoadHeadsAfterWaitPolicy)
        result = MaskablePPO(policy, env, device='cpu', seed=source.seed, **config)
        weights = deepcopy(source.policy.state_dict())
        if a.direction == 'native':
            weights.update({n: v for n, v in template.policy.state_dict().items() if critic(n)})
        result.policy.load_state_dict(weights, strict=True)
        fresh_critic = a.direction == 'lesson' and not already_lesson
        if fresh_critic:
            torch.nn.init.zeros_(result.policy.value_net[-1].weight)
            torch.nn.init.zeros_(result.policy.value_net[-1].bias)
        group_source = groups_by_name(source.policy)
        group_native = groups_by_name(template.policy)
        parameter_names = {id(p): n for n, p in result.policy.named_parameters()}
        for group in result.policy.optimizer.param_groups:
            group_names = tuple(parameter_names[id(p)] for p in group['params'])
            is_critic_group = all(critic(n) for n in group_names)
            assert is_critic_group or not any(critic(n) for n in group_names)
            reference = group_native if is_critic_group and a.direction == 'native' else group_source
            if group_names in reference:
                group.update({k: deepcopy(v) for k, v in reference[group_names].items() if k != 'params'})
            if is_critic_group and a.direction == 'lesson':
                group['lr_scale'] = 1.
            group['lr'] = result.lr_schedule(1.)*group.get('lr_scale', 1.)
            for name, param in zip(group_names, group['params']):
                states = native_states if critic(name) and a.direction == 'native' else old_states
                if name in states and not (critic(name) and fresh_critic):
                    result.policy.optimizer.state[param] = deepcopy(states[name])
        for name in ('num_timesteps', '_n_updates', '_current_progress_remaining'):
            setattr(result, name, getattr(source, name))
        result.route_outcome_critic = a.direction == 'lesson'
        result.native_critic_template_sha256 = sha256(a.native_template)
        result.native_critic_template_path = str(a.native_template.absolute())
        result.critic_provenance_parent = str(a.parent.absolute())
        result.save(a.output/'start.zip')
        loaded = MaskablePPO.load(a.output/'start.zip', device='cpu')
        states = optimizer_by_name(loaded.policy)
        assert_state_equal({n: s for n, s in old_states.items() if not critic(n)},
                           {n: s for n, s in states.items() if not critic(n)})
        if fresh_critic:
            assert not any(critic(n) for n in states)
        else:
            reference = native_states if a.direction == 'native' else old_states
            assert_state_equal({n: s for n, s in reference.items() if critic(n)},
                               {n: s for n, s in states.items() if critic(n)})
        for name, value in source.policy.state_dict().items():
            if not critic(name):
                torch.testing.assert_close(value, loaded.policy.state_dict()[name], rtol=0, atol=0)
        if a.direction == 'native':
            for name, value in template.policy.state_dict().items():
                if critic(name):
                    torch.testing.assert_close(value, loaded.policy.state_dict()[name], rtol=0, atol=0)
        errors = []
        for i in range(16):
            obs, _ = env.reset(options=dict(exercise=SMALL_TIGHT if i < 12 else SMALL_STOCK,
                                            scenario_seed=244009000+i))
            mask = env.action_masks()
            x, y = masked_probs(source, obs, mask), masked_probs(loaded, obs, mask)
            np.testing.assert_array_equal(x, y)
            errors.append(float(abs(x-y).max()))
            if fresh_critic:
                tensor, _ = loaded.policy.obs_to_tensor(obs)
                with torch.no_grad():
                    assert not loaded.policy.predict_values(tensor).count_nonzero()
        for path, digest in digests.items():
            assert sha256(Path(path)) == digest
        report = dict(direction=a.direction, native_mode=a.native_mode,
                      source_hashes=digests, checkpoint_sha256=sha256(a.output/'start.zip'),
                      actor_weights_and_adam_exact=True, actor_max_error=max(errors),
                      shared_states=len(errors), fresh_task_critic=fresh_critic,
                      native_critic_retained_in_template=True, native_critic_restored=a.direction == 'native',
                      timesteps=loaded.num_timesteps, retained_actor_adam_parameters=sum(not critic(n) for n in states),
                      critic_adam_parameters=sum(critic(n) for n in states),
                      gamma=loaded.gamma, vf_coef=loaded.vf_coef,
                      trainable=[n for n, p in loaded.policy.named_parameters() if p.requires_grad],
                      limits='Migration only. Practice critic differs from native critic; original parent/template and lesson checkpoints remain intact. No production launch or promotion.')
        (a.archive/'migration-checks.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
    finally:
        env.close()


if __name__ == '__main__':
    main()

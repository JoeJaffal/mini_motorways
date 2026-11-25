"""Restore zero-output Wait corrections, preserving trained roads and Adam state.

Explicit checkpoint migration, not learning or automatic model promotion.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_choice_policy import CityRoadChoicePolicy
from city_road_pilot import CityRoadEnv
from prepare_city_policy import masked_probs, sha256

WAIT_NAMES = ('growth_strategy_wait', 'growth_strategy_visual_wait')


def optimizer_by_name(policy):
    names = {id(p): n for n, p in policy.named_parameters()}
    return {names[id(p)]: deepcopy(state) for p, state in policy.optimizer.state.items()}


def assert_state_equal(left, right):
    assert left.keys() == right.keys()
    for name in left:
        assert left[name].keys() == right[name].keys(), name
        for key, value in left[name].items():
            other = right[name][key]
            if torch.is_tensor(value):
                torch.testing.assert_close(value, other, rtol=0, atol=0)
            else:
                assert value == other, (name, key)


def main():
    parser = argparse.ArgumentParser()
    for name in ('parent', 'wait-reference', 'output', 'archive', 'dll'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=False)
    args.archive.mkdir(parents=True, exist_ok=False)
    hashes = {name: sha256(getattr(args, name)) for name in ('parent', 'wait_reference', 'dll')}
    source = MaskablePPO.load(args.parent, device='cpu')
    reference = MaskablePPO.load(args.wait_reference, device='cpu')
    # A frozen zero final layer guarantees the shared spatial encoder cannot
    # alter Wait after subsequent road updates. Arbitrary Wait heads are unsafe.
    for name in WAIT_NAMES:
        module = getattr(reference.policy.features_extractor, name)
        assert all(torch.count_nonzero(p) == 0 for p in module[-1].parameters())
    source_state = source.policy.state_dict()
    reference_state = reference.policy.state_dict()
    for key in source_state:
        if not any(part in key for part in (*WAIT_NAMES, 'growth_strategy_roads', 'growth_strategy_spatial', 'value_net')):
            torch.testing.assert_close(source_state[key], reference_state[key], rtol=0, atol=0)
    env = CityRoadEnv(str(args.dll), horizon=600, allow_bridges=True)
    try:
        config = {name: deepcopy(getattr(source, name)) for name in (
            'n_steps', 'batch_size', 'n_epochs', 'learning_rate', 'gamma',
            'gae_lambda', 'ent_coef', 'vf_coef', 'max_grad_norm', 'target_kl',
            'clip_range', 'clip_range_vf', 'normalize_advantage', 'policy_kwargs')}
        result = MaskablePPO(CityRoadChoicePolicy, env, device='cpu', seed=source.seed, **config)
        result.policy.load_state_dict(source_state, strict=True)
        for name in WAIT_NAMES:
            getattr(result.policy.features_extractor, name).load_state_dict(
                getattr(reference.policy.features_extractor, name).state_dict(), strict=True)
        old_names = {id(p): n for n, p in source.policy.named_parameters()}
        new_names = {id(p): n for n, p in result.policy.named_parameters()}
        old_groups = {tuple(old_names[id(p)] for p in group['params']): group
                      for group in source.policy.optimizer.param_groups}
        states = optimizer_by_name(source.policy)
        retained = {}
        for group in result.policy.optimizer.param_groups:
            names = tuple(new_names[id(p)] for p in group['params'])
            previous = old_groups[names]
            group.update({key: deepcopy(value) for key, value in previous.items() if key != 'params'})
            for name, param in zip(names, group['params']):
                assert param.requires_grad and name in states, name
                result.policy.optimizer.state[param] = deepcopy(states[name])
                retained[name] = states[name]
        result.num_timesteps = source.num_timesteps
        result._n_updates = source._n_updates
        result._current_progress_remaining = source._current_progress_remaining
        for key, value in result.policy.state_dict().items():
            expected = reference_state[key] if any(name in key for name in WAIT_NAMES) else source_state[key]
            torch.testing.assert_close(value, expected, rtol=0, atol=0)
            assert torch.isfinite(value).all(), key
        assert_state_equal(retained, optimizer_by_name(result.policy))
        result.save(args.output/'start.zip')
        loaded = MaskablePPO.load(args.output/'start.zip', device='cpu')
        assert loaded.num_timesteps == source.num_timesteps and loaded._n_updates == source._n_updates
        assert_state_equal(retained, optimizer_by_name(loaded.policy))
        for key, value in result.policy.state_dict().items():
            torch.testing.assert_close(value, loaded.policy.state_dict()[key], rtol=0, atol=0)
        for name in WAIT_NAMES:
            assert not any(p.requires_grad for p in getattr(loaded.policy.features_extractor, name).parameters())
        # Verify the actual migrated actor equals the diagnosed component swap
        # on states sampled from both original and repaired city trajectories.
        errors = []; wait_errors = []; states_checked = 0
        for seed in range(184000000, 184000004):
            for rollout_model in (reference, loaded):
                obs, _ = env.reset(options=dict(scenario_seed=seed))
                rng = np.random.default_rng(seed+103)
                for step in range(48):
                    mask = env.action_masks()
                    a = masked_probs(reference, obs, mask).astype(float); a /= a.sum()
                    b = masked_probs(source, obs, mask).astype(float); b /= b.sum()
                    c = masked_probs(loaded, obs, mask).astype(float); c /= c.sum()
                    expected = np.zeros_like(c); expected[0] = a[0]
                    if b[1:].sum(): expected[1:] = (1-a[0])*b[1:]/b[1:].sum()
                    np.testing.assert_allclose(c, expected, rtol=2e-5, atol=2e-7)
                    errors.append(float(abs(c-expected).max())); wait_errors.append(float(abs(c[0]-a[0])))
                    assert not c[~mask].any()
                    states_checked += 1
                    p = a if rollout_model is reference else c
                    obs, *_ = env.step(int(rng.choice(len(p), p=p)))
                    if env.done: break
        for name, digest in hashes.items(): assert sha256(getattr(args, name)) == digest
        report = dict(parent=str(args.parent), wait_reference=str(args.wait_reference), hashes=hashes,
            checkpoint=str(args.output/'start.zip'), checkpoint_sha256=sha256(args.output/'start.zip'),
            preserved_timesteps=result.num_timesteps, preserved_ppo_update_counter=result._n_updates,
            retained_adam_parameters=len(retained), omitted_wait_adam_parameters=len(states)-len(retained),
            retained_adam_steps=sorted({int(state['step']) for state in retained.values()}),
            shared_states=states_checked, max_component_probability_error=max(errors),
            max_wait_probability_error=max(wait_errors), non_wait_weights_exact=True,
            retained_adam_exact_after_reload=True,
            limits='Explicit Wait restoration, not a PPO improvement. No new training, promotion or overnight authorization inferred from this check.')
        (args.archive/'migration-checks.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2), flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()

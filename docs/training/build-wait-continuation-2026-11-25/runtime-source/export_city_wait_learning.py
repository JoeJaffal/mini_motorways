"""Restore native PPO configuration after binary Wait practice, without learning."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from city_wait_choice_policy import CityWaitBanditPolicy, CityNativeAfterWaitPolicy
from city_wait_decision import CityWaitDecisionEnv, SCHEDULE
from prepare_city_policy import masked_probs, sha256
from prepare_city_wait_repair import optimizer_by_name, assert_state_equal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'native-template', 'dll', 'output', 'archive'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=False)
    args.archive.mkdir(parents=True, exist_ok=False)
    digests = {str(p): sha256(p) for p in (args.parent, args.native_template, args.dll)}
    source = MaskablePPO.load(args.parent, device='cpu')
    template = MaskablePPO.load(args.native_template, device='cpu')
    assert isinstance(source.policy, CityWaitBanditPolicy)
    assert not getattr(template.policy, 'bandit_zero_baseline', False)
    assert template.gamma > 0 and template.vf_coef > 0
    env = CityWaitDecisionEnv(str(args.dll))
    try:
        names = ('n_steps', 'batch_size', 'n_epochs', 'learning_rate', 'gamma',
                 'gae_lambda', 'ent_coef', 'vf_coef', 'max_grad_norm', 'target_kl',
                 'clip_range', 'clip_range_vf', 'normalize_advantage', 'policy_kwargs')
        config = {name: deepcopy(getattr(template, name)) for name in names}
        result = MaskablePPO(CityNativeAfterWaitPolicy, env, device='cpu', seed=source.seed, **config)
        result.policy.load_state_dict(source.policy.state_dict(), strict=True)
        # Both policies deliberately retain the identical four optimizer groups.
        old_groups = [[n for n, p in source.policy.named_parameters() if any(p is q for q in g['params'])]
                      for g in source.policy.optimizer.param_groups]
        new_groups = [[n for n, p in result.policy.named_parameters() if any(p is q for q in g['params'])]
                      for g in result.policy.optimizer.param_groups]
        assert old_groups == new_groups
        result.policy.optimizer.load_state_dict(deepcopy(source.policy.optimizer.state_dict()))
        for name in ('num_timesteps', '_n_updates', '_current_progress_remaining'):
            setattr(result, name, getattr(source, name))
        result.save(args.output/'start.zip')
        loaded = MaskablePPO.load(args.output/'start.zip', device='cpu')
        assert_state_equal(optimizer_by_name(source.policy), optimizer_by_name(loaded.policy))
        for name, value in source.policy.state_dict().items():
            torch.testing.assert_close(value, loaded.policy.state_dict()[name], rtol=0, atol=0)
        assert not getattr(loaded.policy, 'bandit_zero_baseline', False)
        errors = []
        for i, case in enumerate(SCHEDULE):
            obs, _ = env.reset(options=dict(case=case, scenario_seed=244003000+i))
            mask = env.action_masks()
            a, b = masked_probs(source, obs, mask), masked_probs(loaded, obs, mask)
            np.testing.assert_allclose(a, b, rtol=0, atol=0)
            errors.append(float(abs(a-b).max()))
            tensor, _ = loaded.policy.obs_to_tensor(obs)
            with torch.no_grad():
                expected = MaskableActorCriticPolicy.predict_values(source.policy, tensor)
                torch.testing.assert_close(expected, loaded.policy.predict_values(tensor), rtol=0, atol=0)
        for path, digest in digests.items():
            assert sha256(Path(path)) == digest
        states = optimizer_by_name(loaded.policy)
        report = dict(source_hashes=digests, checkpoint_sha256=sha256(args.output/'start.zip'),
                      timesteps=loaded.num_timesteps, gamma=loaded.gamma, vf_coef=loaded.vf_coef,
                      actor_max_error=max(errors), shared_states=len(errors),
                      weights_and_adam_exact=True, restored_native_values_exact=True,
                      retained_adam_parameters=len(states),
                      trainable=[n for n, p in loaded.policy.named_parameters() if p.requires_grad],
                      limits='Export only; no learning, city promotion or readiness claim. Native PPO smoke required before use.')
        (args.archive/'export-checks.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
    finally:
        env.close()


if __name__ == '__main__':
    main()

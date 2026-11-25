"""Prepare and check a frozen growing-city Maskable PPO starting checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from city_road_pilot import FIXTURE_ROAD, FIXTURE_SEED, CityRoadEnv, edge_action
from city_road_policy import CityEdgeFeatures, CityRoadPolicy, transfer_construction
from connection_practice import ARENA_SIZE
from edge_policy import LocalEdgeFeatures
from visible_observation import WIDTH


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def masked_probs(model, obs, mask):
    with torch.no_grad():
        inputs, _ = model.policy.obs_to_tensor(obs)
        return model.policy.get_distribution(inputs, mask).distribution.probs[0].cpu().numpy()


def verify_crop_parity(model, obs):
    """Match old crop logits on edges whose endpoint neighborhoods fit the crop."""
    board = torch.as_tensor(obs['grid'])[None].to(model.device)
    visible = obs['grid'][0]
    y0, x0 = np.argwhere(visible).min(axis=0)
    features = model.policy.features_extractor
    legacy = LocalEdgeFeatures(model.observation_space).to(model.device)
    legacy.load_state_dict({
        name: features.state_dict()[name] for name in legacy.state_dict()
    }, strict=True)
    with torch.no_grad():
        old = features.road_score(legacy({'grid': board}).reshape(1, ARENA_SIZE**2*4, -1)).flatten()
        new = features.local_scores(board).flatten()
    local, absolute = [], []
    for y in range(2, ARENA_SIZE - 2):
        for x in range(2, ARENA_SIZE - 2):
            for direction in range(4):
                local.append((y * ARENA_SIZE + x) * 4 + direction)
                absolute.append(((y0 + y) * WIDTH + x0 + x) * 4 + direction)
    torch.testing.assert_close(old[local], new[absolute], rtol=1e-5, atol=1e-5)
    return dict(edges=len(local), max_abs_difference=float((old[local] - new[absolute]).abs().max()))


def check_ppo_paths(model, obs, mask):
    """Check PPO log-probabilities and gradients without stepping the optimizer."""
    inputs, _ = model.policy.obs_to_tensor(obs)
    inputs = {key: value.expand(2, *value.shape[1:]) for key, value in inputs.items()}
    masks = np.stack((mask, np.arange(len(mask)) == 0))
    actions, values, initial_log_probs = model.policy(inputs, action_masks=masks)
    estimate, log_probs, entropies = model.policy.evaluate_actions(inputs, actions, action_masks=masks)
    torch.testing.assert_close(log_probs, initial_log_probs)
    torch.testing.assert_close(values, estimate)
    assert actions[1].item() == 0 and masks[0, actions[0].item()]
    torch.testing.assert_close(log_probs[1], torch.zeros_like(log_probs[1]))
    gradients = torch.autograd.grad(estimate.mean() - log_probs.mean() - .01*entropies.mean(),
                                    tuple(model.policy.parameters()))
    if not all(torch.isfinite(gradient).all() for gradient in gradients):
        raise RuntimeError('PPO actor or critic has a nonfinite gradient')
    return dict(parameter_tensors=len(gradients), legal_roads=int(mask[1:].sum()),
                build_available_wait_probability=float(masked_probs(model, obs, mask)[0]))


def fixture_rank(env, model, scratch):
    edges = [edge_action(start, end) for start, end in zip(FIXTURE_ROAD, FIXTURE_ROAD[1:])]
    rows = []
    for gap in edges:
        obs, _ = env.reset(options={'scenario_seed': FIXTURE_SEED})
        for action in edges:
            if action != gap:
                obs, *_ = env.step(action)
        mask = env.action_masks()
        if not mask[gap]:
            raise RuntimeError('Fixture gap is not buildable')
        row = dict(gap=gap, legal_roads=int(mask[1:].sum()))
        for name, policy in [('transferred', model), ('scratch', scratch)]:
            p = masked_probs(policy, obs, mask)[1:]
            row[name] = dict(rank=1 + int((p > p[gap - 1]).sum()),
                             tied=int(((p == p[gap - 1]) & mask[1:]).sum()),
                             p_given_build=float(p[gap - 1] / p.sum()))
        rows.append(row)
    return rows


def frozen_game(env, model, seed, *, connected=False, greedy=False,
                probabilities=masked_probs, action_seed=None):
    obs, initial = env.reset(options={'scenario_seed': seed})
    first_award = None
    if connected:
        for start, end in zip(FIXTURE_ROAD, FIXTURE_ROAD[1:]):
            obs, *_ = env.step(edge_action(start, end))
    starting_roads = env.road_actions
    rng = np.random.default_rng(seed if action_seed is None else action_seed)
    reward_total = 0
    peak_buildings = initial['buildings']
    first_score = None
    forced_waits = 0
    while not env.done:
        mask = env.action_masks()
        probs = probabilities(model, obs, mask)
        if not np.isfinite(probs).all() or probs[~mask].any():
            raise RuntimeError('Policy assigned invalid probability to the native mask')
        probs = probs.astype(np.float64)
        action = int(probs.argmax() if greedy else rng.choice(len(probs), p=probs / probs.sum()))
        forced_waits += not mask[1:].any()
        obs, reward, terminated, truncated, info = env.step(action)
        if not env.observation_space.contains(obs):
            raise RuntimeError('City returned an invalid observation')
        peak_buildings = max(peak_buildings, info['buildings'])
        reward_total += reward
        if first_score is None and reward:
            first_score = info['seconds']
        if first_award is None and info['weekly_awards']:
            first_award = dict(seconds=info['seconds'], stock=info['road_stock'])
    if reward_total != info['trips'] or env.action_masks().any():
        raise RuntimeError('Expected native score parity and an empty terminal mask')
    return dict(**info, greedy=greedy, scripted_opening_roads=starting_roads,
                policy_draws=env.road_actions - starting_roads, forced_waits=forced_waits,
                peak_buildings=peak_buildings, first_score=first_score, first_award=first_award,
                native_game_over=terminated, truncated=truncated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', default='cuda', choices=('cpu', 'cuda'))
    args = parser.parse_args()
    if args.device == 'cuda' and not torch.cuda.is_available():
        parser.error('CUDA unavailable; use --device cpu for the frozen checks')
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    env = CityRoadEnv(args.dll)
    try:
        settings = dict(
            policy_kwargs=dict(features_extractor_class=CityEdgeFeatures, normalize_images=False),
            learning_rate=3e-4, gamma=1.0, gae_lambda=.95, n_steps=128, batch_size=32,
            seed=82217, device=args.device,
        )
        scratch = MaskablePPO(CityRoadPolicy, env, **settings)
        model = MaskablePPO(CityRoadPolicy, env, **settings)
        source_hash = sha256(args.parent)
        parent = MaskablePPO.load(args.parent, device='cpu')
        copied = transfer_construction(parent.policy, model.policy)
        obs, _ = env.reset(options={'scenario_seed': FIXTURE_SEED})
        mask = env.action_masks()
        ppo = check_ppo_paths(model, obs, mask)
        parity = verify_crop_parity(model, obs)
        fixture = fixture_rank(env, model, scratch)
        print(f'CHECKS | {len(copied)} copied tensors | {parity["edges"]} matching logits', flush=True)
        games = []
        for label, policy, seed, connected, greedy in [
            ('transferred', model, FIXTURE_SEED, False, False),
            ('scratch', scratch, FIXTURE_SEED, False, False),
            ('transferred', model, 16005, False, False),
            ('scratch', scratch, 16005, False, False),
            ('transferred', model, FIXTURE_SEED, False, True),
            ('transferred', model, FIXTURE_SEED, True, False),
        ]:
            result = frozen_game(env, policy, seed, connected=connected, greedy=greedy)
            games.append(dict(initialization=label, **result))
            print(f'GAME | {label} {seed} | {result["trips"]} trips | '
                  f'{result["weekly_awards"]} awards | {result["seconds"]:.2f}s', flush=True)
        if sha256(args.parent) != source_hash or model.num_timesteps or model.policy.optimizer.state:
            raise RuntimeError('Unexpected modification to the parent or frozen starting model')
        if not any(game['first_award'] for game in games if game['scripted_opening_roads']):
            raise RuntimeError('The frozen connected-city check did not reach a weekly award')
        if not all(game['native_game_over'] for game in games):
            raise RuntimeError('A frozen run did not reach native game-over')
        checkpoint = args.output / 'city-start.zip'
        model.save(checkpoint)
        restored = MaskablePPO.load(checkpoint, env=env, device=args.device)
        np.testing.assert_array_equal(masked_probs(restored, obs, mask), masked_probs(model, obs, mask))
        summary = dict(
            result='PASS', device=str(model.device), parent=str(args.parent), parent_sha256=source_hash,
            host=str(args.dll), host_sha256=sha256(args.dll), checkpoint_sha256=sha256(checkpoint),
            policy_seed=settings['seed'], training_timesteps=restored.num_timesteps,
            optimizer_state_entries=len(restored.policy.optimizer.state), restored_masked_prediction='identical',
            copied_tensors=copied, crop_parity=parity, ppo_paths=ppo, fixture_ranks=fixture, games=games,
        )
        (args.output / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(f'PASS | {checkpoint}', flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()

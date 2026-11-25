"""Frozen-policy Monte Carlo diagnostics; never takes an optimizer step."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_road_cost_env import CityRoadCostEnv
from prepare_city_policy import sha256


def main():
    p = argparse.ArgumentParser()
    for name in ('checkpoint', 'dll', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--road-cost', type=float, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    m = MaskablePPO.load(a.checkpoint, device='cpu')
    m.policy.set_training_mode(False)
    before = {k: v.clone() for k, v in m.policy.state_dict().items()}
    digest = sha256(a.checkpoint)
    env = CityRoadCostEnv(str(a.dll), road_cost=a.road_cost, collapse_forced_wait=True, validation=True)
    rows, episodes, samples = [], [], []
    try:
        for i in range(16):
            exercise = ('small-city-offset-single', 'small-city-offset-stock')[i % 2]
            obs, info = env.reset(options=dict(exercise=exercise, scenario_seed=207000000+i//2))
            rng = np.random.default_rng(271000+i)
            trajectory = []
            for step in range(2000):
                mask = env.action_masks()
                with torch.no_grad():
                    ot, _ = m.policy.obs_to_tensor(obs)
                    dist = m.policy.get_distribution(ot, action_masks=mask)
                    probs = dist.distribution.probs[0].numpy()
                    value = float(m.policy.predict_values(ot).item())
                action = int(rng.choice(len(probs), p=probs/probs.sum()))
                saved = {k: v.copy() for k, v in obs.items()}
                served = info['trips'] > 0
                obs, reward, terminated, truncated, info = env.step(action)
                trajectory.append((saved, mask.copy(), action, value, reward, served))
                if terminated or truncated:
                    assert terminated and not truncated, 'Finite lesson must not bootstrap'
                    break
            else:
                raise RuntimeError('Lesson did not terminate')
            total = 0.
            for state, mask, action, value, reward, served in reversed(trajectory):
                total += reward
                samples.append((state, mask, action, value, total, served))
            assert abs(total-info['shaped_return']) < 1e-5
            episodes.append(dict(seed=207000000+i//2, exercise=exercise, native_score=info['trips'],
                                 paid_units=info['paid_units'], shaped_return=total, decisions=len(trajectory)))
    finally:
        env.close()
    # Uniform deterministic subsampling of complete-episode states. No optimizer/RNG mutations.
    chosen = np.linspace(0, len(samples)-1, min(256, len(samples)), dtype=int)
    data = [samples[i] for i in chosen]
    parameters = [p for g in m.policy.optimizer.param_groups for p in g['params']]
    sizes = [len(g['params']) for g in m.policy.optimizer.param_groups]
    for start in range(0, len(data), 32):
        batch = data[start:start+32]
        obs = {k: np.stack([s[0][k] for s in batch]) for k in batch[0][0]}
        ot, _ = m.policy.obs_to_tensor(obs)
        masks = np.stack([s[1] for s in batch])
        actions = torch.tensor([s[2] for s in batch])
        returns = torch.tensor([s[4] for s in batch], dtype=torch.float32)
        values, logp, entropy = m.policy.evaluate_actions(ot, actions, action_masks=masks)
        values = values.flatten()
        advantages = returns-values.detach()
        advantages = (advantages-advantages.mean())/(advantages.std()+1e-8)
        dist = m.policy.get_distribution(ot, action_masks=masks)
        probs = dist.distribution.probs
        build = probs[:, 1:].sum(1)
        q = probs[:, 1:]/build[:, None].clamp_min(1e-12)
        road_h = -(q*q.clamp_min(1e-12).log()).sum(1)
        binary_h = -(build*build.clamp_min(1e-12).log() + probs[:, 0]*probs[:, 0].clamp_min(1e-12).log())
        assert torch.allclose(entropy, binary_h+build*road_h, atol=2e-5)
        losses = dict(policy=-(advantages*logp).mean(), entropy=-m.ent_coef*entropy.mean(),
                      value=m.vf_coef*(returns-values).square().mean())
        norms = {}
        for label, loss in losses.items():
            grads = torch.autograd.grad(loss, parameters, retain_graph=True, allow_unused=True)
            offset = 0
            norms[label] = []
            for size in sizes:
                group = grads[offset:offset+size]
                norms[label].append(float(sum((g.square().sum() for g in group if g is not None), torch.tensor(0.)).sqrt()))
                offset += size
        for j, sample in enumerate(batch):
            rows.append(dict(value=float(values[j].detach()), mc_return=sample[4], served=sample[5],
                             build_probability=float(build[j].detach()), road_entropy=float(road_h[j].detach()),
                             binary_entropy=float(binary_h[j].detach()), legal_roads=int(masks[j, 1:].sum())))
        with (a.output/'gradient_batches.jsonl').open('a') as f:
            f.write(json.dumps(dict(samples=len(batch), gradient_norms=norms))+'\n')
    assert all(torch.equal(before[k], v) for k,v in m.policy.state_dict().items())
    assert digest == sha256(a.checkpoint)
    targets = np.array([x['mc_return'] for x in rows]); values = np.array([x['value'] for x in rows])
    report = dict(checkpoint=str(a.checkpoint), sha256=digest, weights_unchanged=True,
                  episodes=episodes, sampled_states=len(rows), total_states=len(samples),
                  value_mse=float(np.mean((targets-values)**2)),
                  explained_variance=float(1-np.var(targets-values)/np.var(targets)) if np.var(targets)>0 else None,
                  value_mean=float(values.mean()), return_mean=float(targets.mean()),
                  note='Frozen sampled trajectories; normalized Monte Carlo policy-gradient diagnostic, not causal attribution or exact training-minibatch gradients.')
    (a.output/'states.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()

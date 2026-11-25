"""Frozen finite-lesson critic calibration; never updates a checkpoint."""
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv
from prepare_city_policy import masked_probs, sha256

ROOT = Path('docs/training/mini-task-repair-2026-11-25')
DLL = Path('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll')
MODELS = dict(original=Path('output/training/city-whole-initial-01/start.zip'),
    reset131=Path('output/training/mini-reset-comparison-01/reset-curriculum/midpoint.zip'))


def worker(label, horizon, jobs):
    torch.set_num_threads(1)
    model = MaskablePPO.load(MODELS[label], device='cpu')
    env = CityCurriculumEnv(str(DLL), validation=True, small_city_horizon=horizon)
    rows = []
    try:
        for exercise, seed in jobs:
            obs, info = env.reset(options=dict(exercise=exercise, scenario_seed=seed))
            rng = np.random.default_rng(seed + 103)
            steps = []
            while not env.done:
                mask = env.action_masks()
                with torch.no_grad():
                    tensor, _ = model.policy.obs_to_tensor(obs)
                    features = model.policy.extract_features(tensor)
                    pi, vf = model.policy.mlp_extractor(features)
                    dist = model.policy._get_action_dist_from_latent(pi)
                    dist.apply_masking(mask)
                    probs = dist.distribution.probs[0].cpu().numpy().astype(float)
                    value = float(model.policy.value_net(vf).item())
                    if not steps:
                        np.testing.assert_allclose(probs, masked_probs(model, obs, mask), rtol=1e-6, atol=1e-7)
                        assert abs(value - model.policy.predict_values(tensor).item()) < 1e-5
                action = int(rng.choice(len(probs), p=probs / probs.sum()))
                obs, reward, terminal, truncated, info = env.step(action)
                steps.append(dict(value=value, reward=reward, action=action, choices=int(mask.sum())))
            future = 0
            for step in reversed(steps):
                future += step['reward']
                step.update(return_to_go=future, finite_advantage=future-step['value'])
            assert future == info['trips']
            rows.append(dict(model=label, horizon=horizon, exercise=exercise, seed=seed,
                score=info['trips'], seconds=env.raw['time'], native_game_over=terminal, steps=steps))
            print('VALUES', label, horizon, exercise, seed, info['trips'], flush=True)
        return rows
    finally:
        env.close()


def main():
    out = ROOT / 'value-calibration'
    out.mkdir(exist_ok=False)
    config = dict(models={k: dict(path=str(p), sha256=sha256(p)) for k,p in MODELS.items()},
        host_sha256=sha256(DLL), training=False, reference_queries=False,
        limits='Frozen development episodes; finite Monte Carlo targets, not live rollout bootstrap targets. Calibration/noise diagnostics do not prove causal training failure.')
    (out / 'config.json').write_text(json.dumps(config, indent=2))
    jobs = [(ex,231000000+i) for ex in ('small-city-offset-single','small-city-offset-pairs') for i in range(16)]
    with ProcessPoolExecutor(max_workers=8, mp_context=mp.get_context('spawn')) as pool:
        futures = [pool.submit(worker,label,horizon,jobs[k::2]) for label in MODELS for horizon in (60,300) for k in range(2)]
        rows = [r for f in futures for r in f.result()]
    (out / 'games.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary = []
    for label in MODELS:
        for horizon in (60,300):
            for ex in sorted({x['exercise'] for x in rows}):
                games = [x for x in rows if x['model']==label and x['horizon']==horizon and x['exercise']==ex]
                steps = [s for g in games for s in g['steps'] if s['choices']>1]
                ret = np.array([s['return_to_go'] for s in steps]);v=np.array([s['value'] for s in steps]);adv=ret-v
                summary.append(dict(model=label,horizon=horizon,exercise=ex,games=len(games),choice_states=len(steps),
                    mean_score=float(np.mean([g['score'] for g in games])),return_mean=float(ret.mean()),value_mean=float(v.mean()),
                    return_std=float(ret.std()),value_std=float(v.std()),advantage_std=float(adv.std()),
                    explained_variance=float(1-adv.var()/ret.var()) if ret.var()>0 else None,
                    return_advantage_correlation=float(np.corrcoef(ret,adv)[0,1]) if ret.std()*adv.std()>0 else None))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    assert sha256(DLL)==config['host_sha256']
    assert all(sha256(p)==config['models'][k]['sha256'] for k,p in MODELS.items())
    print('COMPLETE',len(rows),'frozen games',flush=True)


if __name__=='__main__':main()

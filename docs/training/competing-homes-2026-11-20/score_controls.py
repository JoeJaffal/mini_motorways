"""Compare frozen timed scores against a legal native build-and-wait witness."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import numpy as np

from bend_ppo import digest, write
from evaluate_triad_ppo import witness
from triad_score_ppo import DECISIONS, WAIT_TICKS, ScoreTriadEnvironment


def play(env, stage, seed):
    env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
    actions = witness(env.env)
    total = 0
    for action in actions + [0] * (env.decision_limit - len(actions)):
        _, reward, done, truncated, info = env.step(action)
        total += reward
        if done:
            break
    if truncated or total != info['trips'] or total < 3:
        raise RuntimeError('Timed offline witness failed')
    return dict(seed=seed, trips=total, stock=env.env.inventory, spent=info['spent'])


def analyze(source, dll):
    run = json.loads(source.read_text())
    if digest(dll) != run['native_sha256']:
        raise ValueError('Use the evaluator’s exact native host')
    controllers = []
    controls = {}
    try:
        for _ in range(8):
            controllers.append(ScoreTriadEnvironment(dll, decision_limit=run.get('decision_limit', DECISIONS),
                                                      wait_ticks=run.get('wait_ticks', WAIT_TICKS)))
        groups = run['results']
        with ThreadPoolExecutor(max_workers=len(controllers)) as pool:
            for key, rows in groups.items():
                stage, _ = key.split('/')
                unique = sorted({r['seed'] for r in rows})
                missing = [seed for seed in unique if (stage, seed) not in controls]
                for first in range(0, len(missing), len(controllers)):
                    group = missing[first:first+len(controllers)]
                    observations = pool.map(lambda pair: play(pair[0], stage, pair[1]), zip(controllers, group))
                    controls.update({(stage, row['seed']): row for row in observations})
    finally:
        for env in controllers:
            env.close()
    results = {}
    for key, rows in groups.items():
        stage, _ = key.split('/')
        expected = [controls[(stage, row['seed'])]['trips'] for row in rows]
        actual = [row['trips'] for row in rows]
        results[key] = dict(layouts=len(rows), policy_mean=float(np.mean(actual)),
                            witness_mean=float(np.mean(expected)),
                            ties_or_exceeds_witness=sum(a >= b for a,b in zip(actual, expected)),
                            connections_before_wait=sum(r['first_connection'] is not None and
                                                        r['first_connection']['seconds']==0 for r in rows),
                            edits_after_connection=sum(r['builds_after_connection'] for r in rows))
    return dict(source_sha256=digest(source), native_sha256=digest(dll), results=results,
                witnesses={f'{stage}/{seed}': row for (stage, seed), row in controls.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = analyze(args.evaluation, args.dll)
    write(args.output, payload)
    print(payload['results'])


if __name__ == '__main__':
    main()

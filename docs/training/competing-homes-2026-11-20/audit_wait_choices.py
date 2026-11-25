"""Replay scored games to distinguish a chosen Wait from a forced Wait."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from bend_ppo import digest, write
from triad_score_ppo import DECISIONS, WAIT_TICKS, ScoreTriadEnvironment


def replay(env, stage, record):
    env.reset(options=dict(stage=stage, split='validation', layout_seed=record['seed']))
    connected = False
    available = []
    remaining = None
    waited = 0
    total = 0.
    for action in record['actions']:
        if connected:
            legal_draws = int(env.action_masks()[1:].sum())
            if legal_draws:
                available.append(legal_draws)
                waited += int(action == 0)
        _, reward, done, truncated, info = env.step(action)
        total += reward
        if info['connected'] and not connected:
            remaining = env.env.raw['inventory'][0]
        connected = info['connected']
    if truncated or not done or total != record['trips']:
        raise RuntimeError('Archived timed actions diverged on replay')
    return dict(seed=record['seed'], trips=total, stock_remaining_at_connection=remaining,
                decisions_with_draw_alternative=len(available), chose_wait=waited,
                maximum_draw_alternatives=max(available, default=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.evaluation.read_text())
    if source['native_sha256'] != digest(args.dll):
        raise RuntimeError('Expected exact archived native host')
    envs = []
    rows = {}
    try:
        for _ in range(8):
            envs.append(ScoreTriadEnvironment(args.dll, decision_limit=source.get('decision_limit', DECISIONS),
                                             wait_ticks=source.get('wait_ticks', WAIT_TICKS)))
        with ThreadPoolExecutor(max_workers=8) as pool:
            for label, records in source['results'].items():
                stage, _ = label.split('/')
                result = []
                for start in range(0, len(records), len(envs)):
                    batch = records[start:start+len(envs)]
                    result.extend(pool.map(lambda pair: replay(pair[0], stage, pair[1]), zip(envs, batch)))
                rows[label] = result
    finally:
        for env in envs:
            env.close()
    summary = {}
    for label, records in rows.items():
        summary[label] = dict(
            boards_with_paid_stock_after_first_connection=sum((r['stock_remaining_at_connection'] or 0) > 0
                                                              for r in records),
            boards_with_legal_draws_after_connection=sum(r['decisions_with_draw_alternative'] > 0 for r in records),
            opportunities_with_legal_draws=sum(r['decisions_with_draw_alternative'] for r in records),
            chose_wait=sum(r['chose_wait'] for r in records))
    write(args.output, dict(source_sha256=digest(args.evaluation), native_sha256=digest(args.dll),
                            summary=summary, results=rows))
    print(summary)


if __name__ == '__main__':
    main()

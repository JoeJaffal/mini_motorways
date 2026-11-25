"""Break down frozen obstacle results by visible layout and edit-set variation."""

import argparse
from collections import Counter
import json
from pathlib import Path

from bend_ppo import digest, write
from spare_road_ppo import SpareRoadEnvironment


def geometry(dll, seeds):
    env = SpareRoadEnvironment(dll)
    out = {}
    try:
        for stage, seed in sorted(seeds):
            env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
            out[(stage, seed)] = dict(span=env.distance, offset=env.offset,
                                      orientation=env.env.shop['drivewayDirection'])
    finally:
        env.close()
    return out


def analyze(path, dll):
    report = json.loads(path.read_text())
    results = report['results']
    metadata = geometry(dll, {(label.split('/')[0], row['seed'])
                              for label, rows in results.items() for row in rows})
    summaries = {}
    for label, rows in results.items():
        stage, _ = label.split('/')
        by_feature = {}
        for feature in ('span', 'offset', 'orientation'):
            total, passed = Counter(), Counter()
            for row in rows:
                value = metadata[(stage, row['seed'])][feature]
                total[value] += 1
                passed[value] += int(row['trips'] >= 3)
            by_feature[feature] = {value: [passed[value], count] for value, count in sorted(total.items())}
        summaries[label] = by_feature
    variety = {}
    for stage in sorted({label.split('/')[0] for label in results}):
        greedy = {r['seed']: r for r in results[f'{stage}/greedy']}
        sampled = {r['seed']: r for r in results[f'{stage}/sampled']}
        both = [(greedy[seed], sampled[seed]) for seed in greedy.keys() & sampled.keys()
                if min(greedy[seed]['trips'], sampled[seed]['trips']) >= 3]
        variety[stage] = dict(
            both_delivered=len(both),
            different_edit_sets=sum(set(a['actions']) != set(b['actions']) for a, b in both))
    return dict(evaluation_sha256=digest(path), fixture_sha256=digest(dll),
                by_visible_layout=summaries, edit_set_comparison=variety)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    write(args.output, analyze(args.evaluation, args.dll))


if __name__ == '__main__':
    main()

"""Summarize equal-budget lesson-duration comparisons without promotion."""
import argparse
import json
from pathlib import Path
import numpy as np
from summarize_expansion_comparison import paired


def summarize(root):
    def read(kind, label):
        path = root / 'evaluation' / f'{kind}-{label}' / 'games.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()]

    budget = json.loads((root / 'status.json').read_text())['added_decisions_per_arm']
    parent = read('city', 'initial')
    retained = read('city', 'retained-original')
    baseline = read('practice', 'initial')
    curves, contrasts = [], []
    metrics = ('score', 'first_served', 'both_served', 'later_served',
               'native_game_over', 'paid', 'outside_routes')
    for decisions in (budget // 4, budget // 2, budget):
        arms = {}
        for arm in ('short-control', 'long-window'):
            city = read('city', f'{arm}-{decisions}')
            practice = read('practice', f'{arm}-{decisions}')
            arms[arm] = city
            row = dict(arm=arm, added_decisions=decisions,
                       city_mean=float(np.mean([x['trips'] for x in city])),
                       city_games=len(city), city_scoring=sum(x['trips'] > 0 for x in city),
                       city_delta_parent=paired(city, parent, ('trips', 'paid_units', 'outside_routes')),
                       city_delta_retained=paired(city, retained, ('trips', 'paid_units', 'outside_routes')),
                       practice={})
            for task in sorted({x['exercise'] for x in baseline}):
                group = [x for x in practice if x['exercise'] == task]
                old = [x for x in baseline if x['exercise'] == task]
                row['practice'][task] = dict(games=len(group),
                    **{k: float(np.mean([x[k] for x in group])) for k in metrics},
                    delta_parent=paired(group, old, metrics))
            curves.append(row)
        contrasts.append(dict(added_decisions=decisions,
            long_minus_short=paired(arms['long-window'], arms['short-control'], ('trips', 'paid_units', 'outside_routes'))))
    result = dict(curves=curves, contrasts=contrasts,
        parent_city_mean=float(np.mean([x['trips'] for x in parent])),
        retained_city_mean=float(np.mean([x['trips'] for x in retained])),
        limits='One training seed per arm; repeated development evaluations. Both arms are evaluated on the same 300-second small-city lessons and 600-second cities. Longer lesson returns cannot be compared directly with historical 60-second returns. No automatic promotion or generalization claim.')
    (root / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Lesson-duration comparison', '', result['limits'], '',
        '| Added decisions | Arm | City mean | Scoring games | Tight single served | Both pairs served |',
        '|---:|---|---:|---:|---:|---:|']
    for row in curves:
        single = row['practice']['small-city-offset-single']['first_served']
        both = row['practice']['small-city-offset-pairs']['both_served']
        lines.append(f"| {row['added_decisions']} | {row['arm']} | {row['city_mean']:.2f} | {row['city_scoring']}/{row['city_games']} | {single:.1%} | {both:.1%} |")
    lines += ['', f"Parent city mean: {result['parent_city_mean']:.2f}; retained original: {result['retained_city_mean']:.2f}.", '',
              'Final city comparisons against the retained original:', '']
    for row in curves[-2:]:
        delta = row['city_delta_retained']['trips']
        lines.append(f"- {row['arm']}: {delta['mean']:+.2f}, paired seed-bootstrap 95% interval {delta['ci95']}.")
    lines += ['', 'Inspect behavior and fresh held-out confirmation before claiming readiness. Improving from a regressed parent alone does not establish a better model.']
    (root / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    summarize(parser.parse_args().archive)

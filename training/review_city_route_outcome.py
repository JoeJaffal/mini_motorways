"""Summarize completed route practice separately from native city retention."""
import argparse
import json
from pathlib import Path
from summarize_expansion_comparison import paired


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--parent-archive', type=Path, required=True)
    p.add_argument('--original-city', type=Path, required=True)
    a = p.parse_args()
    status = json.loads((a.archive/'status.json').read_text())
    assert status['status'] == 'complete'
    city = rows(a.archive/'evaluation/city-final/games.jsonl')
    parent_city = rows(a.parent_archive/'evaluation/city-final/games.jsonl')
    original_city = rows(a.original_city/'games.jsonl')
    comparisons = {label: paired(city, baseline, ('trips', 'paid_units', 'outside_routes'))
                   for label, baseline in [('parent', parent_city), ('original', original_city)]}
    mini = json.loads((a.archive/'evaluation/practice-final/summary.json').read_text())['candidate']
    parent_mini = json.loads((a.parent_archive/'evaluation/practice-final/summary.json').read_text())['candidate']
    curve = []
    for label in ['initial', str(status['budget']//4), str(status['budget']//2), str(status['budget'])]:
        path = a.archive/f'evaluation/outcome-{label}/summary.json'
        curve.append(dict(added_decisions=0 if label == 'initial' else int(label), cases=json.loads(path.read_text())))
    before = rows(a.archive/'evaluation/outcome-initial/games.jsonl')
    after = rows(a.archive/f'evaluation/outcome-{status["budget"]}/games.jsonl')
    paired_outcomes = {}
    for case in curve[0]['cases']:
        baseline = {(r['seed'], r['action_seed']): r for r in before if r['exercise'] == case}
        games = [r for r in after if r['exercise'] == case]
        assert len(games) == len(baseline)
        paired_outcomes[case] = dict(
            gained=sum(r['task_success'] and not baseline[r['seed'], r['action_seed']]['task_success'] for r in games),
            lost=sum(not r['task_success'] and baseline[r['seed'], r['action_seed']]['task_success'] for r in games))
    tight = mini['small-city-offset-single']['success']*16
    both = mini['small-city-offset-pairs']['both_served']*16
    mean = sum(r['trips'] for r in city)/len(city)
    original_mean = sum(r['trips'] for r in original_city)/len(original_city)
    gates = dict(short_retention=all(mini[k]['success'] >= parent_mini[k]['success']-1/16
                                    for k in ('adjacent', 'bend', 'clear', 'obstacle')),
                 tight_routes=tight >= 14, both_pairs=both >= 8,
                 city_mean=mean >= original_mean,
                 city_zeros=sum(r['trips'] == 0 for r in city) <= sum(r['trips'] == 0 for r in original_city)+1)
    report = dict(city_mean=mean, scoring=sum(r['trips'] > 0 for r in city),
                  city_comparisons=comparisons, outcome_curve=curve, paired_outcomes=paired_outcomes,
                  native_mini=mini, development_gates=gates, development_screen_passed=all(gates.values()),
                  clear_city_regression=comparisons['parent']['trips']['ci95'][1] < 0,
                  limits='Consumed development scenarios; practice return is not city score. No automatic promotion. Fresh confirmation remains required even if every development gate passes.')
    (a.archive/'review.json').write_text(json.dumps(report, indent=2)+'\n')
    lines = ['# Bounded varied-route study results', '', report['limits'], '',
             '| Review | Tight successes /32 | Generous successes /32 |', '|---|---:|---:|']
    for point in curve:
        c = point['cases']
        lines.append(f"| {point['added_decisions']} added decisions | {c['small-city-offset-single']['successes']} | {c['small-city-offset-stock']['successes']} |")
    lines += ['', f'Native city mean: {mean:.2f}; scoring {report["scoring"]}/{len(city)}.',
              f'Paired change versus parent: {comparisons["parent"]["trips"]}.',
              f'Native mini tasks: tight {tight:.0f}/16; both pairs {both:.0f}/16.',
              f'Development gates: {gates}.', '']
    (a.archive/'RESULTS.md').write_text('\n'.join(lines))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

"""Compare policies to fixed and delayed native controls on matched timing boards."""

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean, median


def read_evidence(path):
    return json.loads(path.read_text())['results']


def first_edit(row):
    return next((action for action in row['actions'] if action), None)


def summarize(controls, evaluation, start=15, delay=35):
    groups = {}
    variants = sorted({key.split('/')[0].replace('-low-', '-{}-').replace('-high-', '-{}-')
                       for key in controls})
    for variant in variants:
        sides = {side: variant.format(side) for side in ('low', 'high')}
        lookups = {
            side: {label: {r['seed']: r for r in rows} for key, rows in controls.items()
                   if key.split('/')[0] == stage for label in [key.split('/')[1]]}
            for side, stage in sides.items()
        }
        goals = {'low': 'feeder', 'high': 'separate-exit'}
        benchmarks = {}
        for side, by_mode in lookups.items():
            benchmarks[side] = {key: mean(row['trips'] for row in rows.values())
                                for key, rows in by_mode.items()}
        groups[variant] = {'controls': benchmarks}
        fixed = {choice: mean(benchmarks[side][f'{choice}@{start}'] for side in sides)
                 for choice in goals.values()}
        adaptive = mean(benchmarks[side][f'{goals[side]}@{delay}'] for side in sides)
        groups[variant].update(best_fixed=max(fixed.values()), fixed=fixed, delayed_oracle=adaptive)
        if not evaluation:
            continue
        for mode in ('greedy', 'sampled'):
            answer = {}
            for side, stage in sides.items():
                rows = evaluation[f'{stage}/{mode}']
                controls_for_mode = lookups[side][f'{goals[side]}@{delay}']
                assert {r['seed'] for r in rows} == controls_for_mode.keys()
                times = [r['first_build_time'] for r in rows]
                built = [t for t in times if t is not None]
                right = [first_edit(r) == first_edit(controls_for_mode[r['seed']]) for r in rows]
                answer[side] = dict(
                    count=len(rows), mean_trips=mean(r['trips'] for r in rows),
                    stopped=mean(r['stopped_cars_mean'] for r in rows),
                    failures=sum(r['native_failure'] for r in rows),
                    built_immediately=sum(t == start for t in times),
                    first_build_at_delay=sum(t == delay for t in times),
                    median_build_time=median(built) if built else None,
                    build_times=dict(sorted(Counter(built).items())),
                    never_built=times.count(None), preferred_branch=sum(right),
                    preferred_branch_at_delay=sum(a and t == delay for a, t in zip(right, times)),
                )
            groups[variant][mode] = dict(sides=answer, mean_trips=mean(v['mean_trips'] for v in answer.values()))
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('controls', type=Path)
    parser.add_argument('evaluation', type=Path, nargs='?')
    parser.add_argument('--start', type=int, default=15)
    parser.add_argument('--delay', type=int, default=35)
    args = parser.parse_args()
    print(json.dumps(summarize(read_evidence(args.controls),
                               read_evidence(args.evaluation) if args.evaluation else {},
                               args.start, args.delay), indent=2))


if __name__ == '__main__':
    main()

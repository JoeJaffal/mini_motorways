"""Summarize native score, queue and matched construction choices from saved replays."""

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean, median


def read(path):
    return json.loads(path.read_text())['results']


def edits(row):
    return tuple(sorted(action for action in row['actions'] if action))


def top_two_service(row):
    pins = dict(zip(sorted(row['served'], key=int), row['initial_pins']))
    eligible = sorted(pins, key=pins.get, reverse=True)[:2]
    return all(row['served'][shop] > 0 for shop in eligible)


def summarize(results, controls, initial_time):
    by_stage = {}
    for name, rows in controls.items():
        stage, label = name.split('/')
        options = by_stage.setdefault(stage, {})
        options[label] = {row['seed']: row for row in rows}
    output = {}
    for name, rows in results.items():
        stage = name.split('/')[0]
        witnesses = by_stage.get(stage, {})
        counts = Counter()
        comparisons = {mode: [] for mode in witnesses}
        for row in rows:
            seed = row['seed']
            found = False
            for mode, trials in witnesses.items():
                if seed not in trials:
                    continue
                control = trials[seed]
                comparisons[mode].append(row['trips'] - control['trips'])
                if edits(row) != edits(control):
                    continue
                if '@' in mode and row['first_build_time'] != control['first_build_time']:
                    continue
                counts[mode] += 1
                found = True
            if not found:
                counts['other_action_or_time'] += 1
        build_times = [row['first_build_time'] for row in rows if row['first_build_time'] is not None]
        output[name] = dict(boards=len(rows), trips=mean(row['trips'] for row in rows),
                            stopped=mean(row['stopped_cars_mean'] for row in rows),
                            failures=sum(row['native_failure'] for row in rows),
                            committed_after_start=sum(time > initial_time for time in build_times),
                            median_build_time=median(build_times) if build_times else None,
                            witnesses=counts, delta_to_controls={mode: mean(values) for mode, values
                                                                 in comparisons.items() if values})
        if rows and len(rows[0]['served']) == 3:
            output[name]['top_two_destinations_served'] = sum(top_two_service(row) for row in rows)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evaluation', type=Path)
    parser.add_argument('--controls', type=Path)
    parser.add_argument('--initial-time', type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(summarize(read(args.evaluation), read(args.controls) if args.controls else {},
                               args.initial_time), indent=2))


if __name__ == '__main__':
    main()

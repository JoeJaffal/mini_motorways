"""Summarize frozen unequal-distance tests by whether the matching home is nearer."""

import argparse
import json
from pathlib import Path

from bend_ppo import digest, write
from construction_practice import tile
from environment import DIRS
from evaluate_triad_ppo import TriadEnvironment


def analyze(source, dll):
    data = json.loads(source.read_text())
    if digest(dll) != data['native_sha256']:
        raise RuntimeError('Expected the exact native fixture from the saved evaluation')
    env = TriadEnvironment(dll)
    results = {}
    try:
        for label, rows in data['results'].items():
            stage, _ = label.split('/')
            totals = {distance: dict(played=0, passed=0, trips=0) for distance in ('nearer', 'farther')}
            for row in rows:
                env.reset(options=dict(stage=stage, split='validation', layout_seed=row['seed']))
                world = env.env
                heading = DIRS[world.shop['drivewayDirection']]
                values = [sum(a*b for a,b in zip(tile(home['cell']), heading)) for home in world.homes]
                if len(set(values)) != 2:
                    raise RuntimeError('Unequal-distance fixture unexpectedly tied')
                group = 'nearer' if world.match == world.homes[values.index(min(values))] else 'farther'
                totals[group]['played'] += 1
                totals[group]['passed'] += int(row['trips'] >= 3)
                totals[group]['trips'] += row['trips']
            results[label] = totals
    finally:
        env.close()
    return dict(source_sha256=digest(source), native_sha256=digest(dll), results=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--dll', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.evaluation, args.dll)
    write(args.output, report)
    print(report['results'])


if __name__ == '__main__':
    main()

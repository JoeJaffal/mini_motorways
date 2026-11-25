"""Plot training connection rates and native scores from archived rollout records."""

import argparse
from collections import deque
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def series(directory, field, keys, numerator, denominator):
    config = json.loads((directory/'config.json').read_text())
    rows = [json.loads(line) for line in (directory/'progress.jsonl').read_text().splitlines()]
    start = config.get('starting_decisions', 0)
    window = deque(maxlen=5)
    for row in rows:
        data = [row[field][k] for k in keys if k in row[field]]
        games = sum(entry[denominator] for entry in data)
        if not games:
            continue
        window.append((sum(entry[numerator] for entry in data), games))
        yield (row['decisions']-start)/1000, sum(p for p, _ in window)/sum(n for _, n in window)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output name')
    base = Path(__file__).with_name('runs')
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    route_runs = [
        ('triad-stub-ppo-01', 'Stub curriculum'),
        ('triad-empty-control-ppo-01', 'Empty boards from the start'),
        ('triad-frame-ppo-01', 'Static frame, new scorer only'),
        ('triad-network-ppo-01', 'Built-network context'),
    ]
    timed_runs = [
        ('triad-score-ppo-01', 'Transferred Wait'),
        ('triad-score-ppo-02', '20% initial Wait'),
        ('triad-score-network-01', 'Built-network draw actor'),
        ('triad-score-joint-01', 'Joint score-only continuation'),
    ]
    for axis, runs, field, keys, index in (
            (left, route_runs, 'cases', ('triad-left', 'triad-right'), 0),
            (right, timed_runs, 'native_score', ('pair-triad-left', 'pair-triad-right'), 2)):
        for run, label in runs:
            points = list(series(base/run, field, keys, index, 1))
            x, y = zip(*points)
            axis.plot(x, y, label=label, linewidth=1.7)
        axis.set_axisbelow(True)
        axis.grid(color='#e2e8f0')
        axis.set_xlabel('Added PPO decisions (thousands)')
        axis.legend(loc='lower right', fontsize=8, frameon=True)
    left.set_title('Full roads on empty boards')
    left.set_ylabel('Sampled connection rate')
    left.yaxis.set_major_formatter(PercentFormatter(1))
    left.set_ylim(0, 1.035)
    right.set_title('Timed Build-or-Wait on mirrored boards')
    right.set_ylabel('Mean native deliveries')
    right.set_ylim(0, 9)
    figure.suptitle('Training rollouts for competing homes · five-rollout averages',
                    fontsize=14, weight='bold')
    figure.savefig(args.output, dpi=160, facecolor='white')


if __name__ == '__main__':
    main()

"""Plot rollout success from the archived Maskable PPO progress records."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def read_progress(path):
    with path.open() as records:
        return [json.loads(line) for line in records]


def curve(ax, rows, field, name, label):
    points = [(row['decisions'] / 1000, wins / games) for row in rows
              for wins, games in [row[field][name]] if games]
    ax.plot([x for x, _ in points], [y for _, y in points], label=label, linewidth=1.7)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output filename')
    data = Path(__file__).with_name('runs')
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.1), sharey=True, layout='constrained')
    for ax, run, title in zip(axes, ('pair-ppo-hour-01', 'pair-ppo-hour-02', 'pair-ppo-hour-03'),
                              ('Original Finish gate', 'Visible color interaction', 'Commitment warm-up')):
        rows = read_progress(data / run / 'progress.jsonl')
        for key, label in [('match', 'Matching pair'), ('mismatch', 'Mismatched pair'),
                           ('homes', 'Two homes'), ('destinations', 'Two destinations')]:
            curve(ax, rows, 'cases', key, label)
        ax.set_title(title)
        ax.set_xlabel('Training decisions (thousands)')
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_ylim(-.035, 1.035)
        ax.grid(color='#e2e8f0', linewidth=.7)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('Success in individual training rollout')
    axes[-1].legend(loc='center right', fontsize=8)
    figure.suptitle('Learning when to build or finish on isolated pairs', fontsize=14, fontweight='bold')
    figure.savefig(args.output, dpi=160, facecolor='white')


if __name__ == '__main__':
    main()

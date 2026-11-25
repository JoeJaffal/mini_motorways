"""Plot native first-action Wait during the fixed-start PPO runs."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt


def series(run):
    config = json.loads((run / 'config.json').read_text())
    rows = [json.loads(row) for row in (run / 'progress.jsonl').read_text().splitlines()]
    progress = [row['decisions'] - config['start'] for row in rows]
    rates = []
    for row in rows:
        stages = row['stages'].values()
        starts = sum(s['games_built_before_20'] for s in stages)
        rates.append(100 * (1 - starts / sum(s['games'] for s in stages)))
    return progress, rates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).with_name('runs')
    methods = (
        ('timing-joint-02', 'Whole policy, standard traffic', '#78909a'),
        ('timing-wait-only-03', 'Wait head, standard traffic', '#4759a0'),
        ('timing-contrast-wait-01', 'Wait head, stronger traffic', '#a95c18'),
        ('timing-clock-wait-01', 'Trainable clock feature, stronger traffic', '#007865'),
    )
    fig, ax = plt.subplots(figsize=(8.3, 4.2), layout='constrained')
    for run, label, color in methods:
        progress, rates = series(root / run)
        ax.plot(progress, rates, label=label, color=color, linewidth=2)
    ax.set_title('Voluntary waiting before the surge during training', loc='left', weight='bold')
    ax.set_xlabel('Added PPO decisions')
    ax.set_ylabel('Games starting with Wait (%)')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=.2)
    ax.spines[['right', 'top']].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc='best')
    fig.savefig(args.output, dpi=190)


if __name__ == '__main__':
    main()

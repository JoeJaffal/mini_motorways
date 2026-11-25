"""Rebuild the archived matched native controls figure."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    measurements = Path(__file__).with_name('measurements')
    experiments = [
        ('Two units, network still being built', 'traffic-stockrush-heldout-controls-01.json',
         'stockrush', ('share+feeder', 'separate-entry+separate-exit', 'wait')),
        ('One unit, both networks already serving', 'traffic-live-heldout-controls-01.json',
         'live', ('feeder', 'separate-exit', 'wait')),
    ]
    labels = ('Extend shared service', 'Complete bypass', 'Wait throughout')
    palette = ('#0a7869', '#b85b14', '#6c7887')
    periods = ('low', 'high')
    x = np.arange(len(periods))
    offsets = np.array([-.24, 0, .24])
    fig, panels = plt.subplots(2, 2, figsize=(9.2, 6.2), sharey='col')
    fig.subplots_adjust(left=.10, right=.98, top=.87, bottom=.16, hspace=.56, wspace=.29)
    fig.suptitle('A shared road serves more homes until heavy traffic changes the payoff',
                 fontsize=14, weight='bold', y=.97)
    for row, (title, filename, stage, modes) in zip(panels, experiments):
        result = json.loads((measurements / filename).read_text())['results']
        for ax, (field, axis_title) in zip(row, (
            ('trips', 'Mean native deliveries'), ('stopped_cars_mean', 'Mean visible stopped cars'),
        )):
            for offset, color, mode, label in zip(offsets, palette, modes, labels):
                values = [np.mean([r[field] for r in result[f'traffic-junction-{period}-{stage}/{mode}']])
                          for period in periods]
                bars = ax.bar(x + offset, values, width=.20, color=color, label=label)
                ax.bar_label(bars, fmt='%.2f', padding=2, fontsize=8)
            ax.set_xticks(x, ('Light traffic', 'Heavy traffic'))
            ax.set_ylabel(axis_title)
            ax.set_title(title, loc='left', fontsize=10, weight='bold')
            ax.set_ylim(0, 42 if field == 'trips' else 8)
            ax.grid(axis='y', alpha=.18)
            ax.set_axisbelow(True)
            ax.spines[['right', 'top']].set_visible(False)
    handles, legend = panels[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend, loc='lower center', ncol=3, bbox_to_anchor=(.5, .057), frameon=False)
    fig.text(.5, .025, '100 paired layouts per traffic condition and fixture. Scripted controls used only for evaluation.',
             ha='center', fontsize=8, color='#384452')
    fig.savefig(args.output, dpi=192)


if __name__ == '__main__':
    main()

"""Render the same validation board before and after the stub curriculum."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


def trace(path, seed):
    data = json.loads(path.read_text())
    row, = (entry for entry in data['results']['pair-triad-left/greedy'] if entry['seed'] == seed)
    return row


def draw(ax, board, title, buildings, bounds):
    destination, = (b for b in buildings if b['role'] == 'destination')
    for building in buildings:
        x, y = building['location']
        matching = building['color'] == destination['color']
        mark = '#b4a9ff' if matching else '#d9dde5'
        ax.add_patch(Rectangle((x-.43, y-.43), building['width']-.14, building['height']-.14,
                               facecolor=mark, edgecolor='#555678', linewidth=1.0, zorder=3))
        if building['role'] == 'home':
            label = 'Matching home' if matching else 'Other home'
            ax.text(x, y-.64, label, ha='center', va='bottom', fontsize=8, color='#343343')
        else:
            ax.text(x+(building['width']-1)/2, y+(building['height']-1)/2, 'Shop',
                    ha='center', va='center', fontsize=9, color='#343343', zorder=5)
    for step in board['trace']:
        if not step['cells']:
            continue
        (x, y), (xx, yy) = step['cells']
        failed_step = step['step'] == board['first_deficit']
        color = '#d23745' if failed_step else '#1e6c70' if step['paid'] else '#7b8797'
        ax.plot([x, xx], [y, yy], color=color, linewidth=3 if failed_step else 2,
                linestyle='-' if step['paid'] else '--', zorder=5)
        ax.text((x+xx)/2, (y+yy)/2, str(step['step']), ha='center', va='center', fontsize=8,
                color='white', zorder=6, bbox=dict(boxstyle='circle,pad=.18', facecolor=color, edgecolor='none'))
    x0, x1, y0, y1 = bounds
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_xticks(range(int(x0), int(x1)+1), labels=[])
    ax.set_yticks(range(int(y0), int(y1)+1), labels=[])
    ax.tick_params(length=0)
    ax.grid(color='#e3e8ef')
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=13, weight='bold')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=54200)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output filename')
    before, after = trace(args.before, args.seed), trace(args.after, args.seed)
    buildings = after['buildings']
    points = [p for board in (before, after) for step in board['trace'] for p in step['cells']]
    for building in buildings:
        x, y = building['location']
        points.extend(((x, y), (x+building['width']-1, y+building['height']-1)))
    xs, ys = zip(*points)
    bounds = min(xs)-1.4, max(xs)+1.1, min(ys)-1.2, max(ys)+.7
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 5.1), layout='constrained')
    draw(axes[0], before, 'Before stub training', buildings, bounds)
    draw(axes[1], after, 'After stub training', buildings, bounds)
    figure.suptitle(f'Greedy construction on the same board · seed {args.seed}', fontsize=15, weight='bold')
    figure.legend(handles=[
        Line2D([0], [0], color='#1e6c70', lw=2, label='Paid road'),
        Line2D([0], [0], color='#7b8797', lw=2, linestyle='--', label='Free parcel attachment'),
        Line2D([0], [0], color='#d23745', lw=3, label='First edit that exhausted the route budget'),
    ], loc='outside lower center' if matplotlib_compatible() else 'lower center', ncol=3, frameon=False)
    figure.savefig(args.output, dpi=160, facecolor='white')


def matplotlib_compatible():
    import matplotlib
    return tuple(int(x) for x in matplotlib.__version__.split('.')[:2]) >= (3, 7)


if __name__ == '__main__':
    main()

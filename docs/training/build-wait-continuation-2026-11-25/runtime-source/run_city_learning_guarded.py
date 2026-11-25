"""Run up to eight hours of city PPO with a paired review after each half hour."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from prepare_city_policy import sha256
from run_city_overnight import publish_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=Path, required=True)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = args.output.resolve()
    start, dll = args.start.resolve(), args.dll.resolve()
    config = dict(start=str(start), start_sha256=sha256(start), dll=str(dll), host_sha256=sha256(dll),
                  hours=8, segment_hours=.5, learning_rate=1e-6, workers=16)
    if args.resume:
        if json.loads((root/'config.json').read_text()) != config:
            raise RuntimeError('Resume requires the original checkpoint and simulator')
    else:
        root.mkdir(parents=True, exist_ok=False)
        publish_json(root/'config.json', config)
    status = root/'status.json'
    if status.exists() and json.loads(status.read_text())['status'] in ('complete', 'regression'):
        print(status.read_text(), flush=True)
        return
    current = start
    for index in range(16):
        segment = root/f'segment-{index+1:02d}'
        command = [
            sys.executable, '-u', str(ROOT/'training/run_city_service_training.py'),
            '--output', str(segment), '--dll', str(dll), '--start', str(current),
            '--hours', '.5', '--save-minutes', '15', '--workers', '16',
            '--seed-start', str(98_800_000+index*10_000),
            '--review-games', '24', '--review-seed', str(563901+index),
            '--review-interval-minutes', '15', '--learning-rate', '0.000001', '--reserve',
        ]
        if segment.exists():
            command.append('--resume')
        subprocess.run(command, check=True, cwd=ROOT)
        state = json.loads((segment/'state.json').read_text())
        if not state['training_complete']:
            publish_json(status, dict(status='interrupted', segment=index+1))
            return
        review = json.loads((segment/'review.json').read_text())
        models = review['models']
        reference = review['results'][str(models.index(str(current)))]
        candidates = [
            (review['results'][str(i)], Path(path))
            for i, path in enumerate(models) if Path(path).parent == segment/'checkpoints'
        ]
        # Require scoring-city retention and allow at most a 5% score decrease
        # on the paired development cohort before continuing to another segment.
        eligible = [(metrics, path) for metrics, path in candidates
                    if metrics['scoring_games'] >= reference['scoring_games']
                    and metrics['mean_score'] >= .95*reference['mean_score']]
        if not eligible:
            publish_json(status, dict(status='regression', segment=index+1,
                                     retained_checkpoint=str(current), reference=reference))
            print(f'STOPPED | paired retention failed | retained {current}', flush=True)
            return
        selected, current = max(eligible, key=lambda item:item[0]['mean_score'])
        publish_json(status, dict(status='running' if index<15 else 'complete',
                                 segment=index+1, selected_checkpoint=str(current),
                                 selected_sha256=sha256(current), measurements=selected))
        print(f'REVIEW | segment {index+1}/16 | selected {current}', flush=True)


if __name__ == '__main__':
    main()

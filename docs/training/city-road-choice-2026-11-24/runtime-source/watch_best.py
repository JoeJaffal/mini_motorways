"""Open a recorded game in Traffic Lab Original; never starts a learner."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, help='Training run directory; defaults to newest run with a best game')
    parser.add_argument('--replay', type=Path, help='Open a specific recording instead')
    parser.add_argument('--play', action='store_true', help='Start at the beginning, paused; press Play or Space')
    args = parser.parse_args()
    if args.replay:
        recording = args.replay.resolve()
    elif args.run:
        recording = args.run.resolve()/'best-game.json'
    else:
        candidates = list((ROOT/'output/training').glob('*/best-game.json'))
        if not candidates:
            parser.error('No best game yet. Wait for a training episode to finish, or use --replay FILE.')
        recording = max(candidates,key=lambda p:p.stat().st_mtime)
    if not recording.is_file():
        parser.error(f'No completed best game at {recording}')
    data = json.loads(recording.read_text(encoding='utf-8'))
    player = ROOT/'simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe'
    if not player.is_file():
        parser.error('Build Traffic Lab Original in Unity first. See training/README.md.')
    print(f'Opening {data.get("source", "recorded")} game | seed {data["seed"]} | '
          f'{data["score"]} trips | {data["duration"]:.1f} simulated seconds\n{recording}')
    command = [str(player),'--replay',str(recording)]
    if not args.play:
        command.append('--replay-final')
    subprocess.Popen(command,cwd=ROOT)


if __name__ == '__main__':
    main()

"""Bounded varied-route PPO with frozen runtime and separate native reviews."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from prepare_city_policy import sha256
from train_city_wait_decision import publish_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'native-template', 'host-directory', 'output', 'archive'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--rollouts', type=int, default=8)
    p.add_argument('--seed-start', type=int, default=248000000)
    p.add_argument('--train-road-encoder', action='store_true')
    a = p.parse_args()
    if a.rollouts < 4 or a.rollouts % 4:
        p.error('Rollouts must be a positive multiple of four')
    root = Path.cwd()
    out, archive = a.output.absolute(), a.archive.absolute()
    out.mkdir(parents=True, exist_ok=False)
    archive.mkdir(parents=True, exist_ok=False)
    source = out/'runtime/training'
    source.mkdir(parents=True)
    for path in (root/'training').glob('*.py'):
        shutil.copy2(path, source/path.name)
    shutil.copy2(root/'training/stage1_replay.html', source/'stage1_replay.html')
    shutil.copytree(source, archive/'runtime-source')
    host = out/'runtime/host'
    shutil.copytree(a.host_directory, host)
    env = dict(os.environ, PYTHONPATH=str(source))
    state = dict(status='running', phase='migration', pid=os.getpid(),
        started=datetime.datetime.now().astimezone().isoformat(),
        parent=str(a.parent.absolute()), parent_sha256=sha256(a.parent),
        native_template_sha256=sha256(a.native_template), host_sha256=sha256(host/'TrafficHost.dll'),
        replay_template_sha256=sha256(source/'stage1_replay.html'),
        budget=a.rollouts*8192, train_seed_start=a.seed_start, validation_seed_start=249000000,
        train_road_encoder=a.train_road_encoder,
        limits='Bounded practice repair, no automatic promotion, extension or overnight training.')

    def publish():
        publish_json(out/'status.json', state)
        publish_json(archive/'status.json', state)

    def run(script, label, args):
        state['phase'] = label
        publish()
        command = [sys.executable, '-u', str(source/script), *map(str, args)]
        (archive/(label+'-command.json')).write_text(json.dumps(command, indent=2)+'\n')
        print('START', label, flush=True)
        with (out/(label+'.log')).open('x') as log:
            subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('COMPLETE', label, flush=True)

    def evaluate(kind, label, checkpoint):
        dest = out/'evaluation'/f'{kind}-{label}'
        scripts = dict(outcome='evaluate_city_route_outcome.py', practice='audit_mini_behavior.py', city='evaluate_overnight_city.py')
        args = ['--dll', host/'TrafficHost.dll', '--output', dest, '--workers', '2']
        if kind == 'practice':
            args += ['--checkpoints', checkpoint, '--labels', 'candidate', '--small-city-horizon', '300']
        else:
            args += ['--checkpoint', checkpoint]
        run(scripts[kind], f'{kind}-{label}', args)
        shutil.copytree(dest, archive/'evaluation'/f'{kind}-{label}')

    try:
        publish()
        run('prepare_city_route_outcome.py', 'migration', ['--parent', a.parent.absolute(),
            '--native-template', a.native_template.absolute(), '--dll', host/'TrafficHost.dll',
            '--output', out/'initial', '--archive', archive/'migration', '--direction', 'lesson']
            + (['--train-road-encoder'] if a.train_road_encoder else []))
        evaluate('outcome', 'initial', out/'initial/start.zip')
        run('train_city_route_outcome.py', 'training', ['--parent', out/'initial/start.zip',
            '--dll', host/'TrafficHost.dll', '--output', out/'training', '--rollouts', a.rollouts,
            '--seed-start', a.seed_start])
        measurements = archive/'measurements'
        measurements.mkdir()
        for name in ('config.json', 'checkpoints.json', 'episodes.jsonl', 'progress.csv', 'complete.json'):
            shutil.copy2(out/'training'/name, measurements/name)
        checkpoints = json.loads((out/'training/checkpoints.json').read_text())
        for row in checkpoints:
            if row['added_decisions'] in (state['budget']//4, state['budget']//2, state['budget']):
                evaluate('outcome', str(row['added_decisions']), Path(row['path']))
        final = out/'training/final.zip'
        for kind in ('practice', 'city'):
            evaluate(kind, 'final', final)
        run('prepare_city_route_outcome.py', 'native-export', ['--parent', final,
            '--native-template', a.native_template.absolute(), '--dll', host/'TrafficHost.dll',
            '--output', out/'native-export', '--archive', archive/'native-export', '--direction', 'native'])
        assert sha256(a.parent) == state['parent_sha256']
        assert sha256(a.native_template) == state['native_template_sha256']
        assert sha256(host/'TrafficHost.dll') == state['host_sha256']
        state.update(status='complete', phase='complete', finished=datetime.datetime.now().astimezone().isoformat())
        publish()
        print('BOUNDED STUDY COMPLETE; review evidence before any further training.', flush=True)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        publish()
        raise


if __name__ == '__main__':
    main()

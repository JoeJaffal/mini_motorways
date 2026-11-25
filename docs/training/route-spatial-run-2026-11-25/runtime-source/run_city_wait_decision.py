"""Bounded Wait-head PPO study with separate native retention reviews."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from prepare_city_policy import sha256
from run_mini_horizon_comparison import dump
from run_overnight_transfer_comparison import stop_owned_tree


def main():
    p = argparse.ArgumentParser()
    for name in ('parent', 'host-directory', 'city-host-directory', 'output', 'archive'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--rollouts', type=int, default=4)
    p.add_argument('--seed-start', type=int, default=245000000)
    a = p.parse_args()
    if a.rollouts < 4 or a.rollouts % 4:
        p.error('Rollouts must be a positive multiple of four')
    root = Path.cwd(); out = a.output.absolute(); archive = a.archive.absolute(); parent = a.parent.absolute()
    archive.mkdir(parents=True, exist_ok=True)
    source = out/'runtime/training'; source.mkdir(parents=True, exist_ok=False)
    for path in (root/'training').glob('*.py'):
        shutil.copy2(path, source/path.name)
    shutil.copy2(root/'training/stage1_replay.html', source/'stage1_replay.html')
    host = out/'runtime/host'; shutil.copytree(a.host_directory, host)
    city_host = out/'runtime/city-host'; shutil.copytree(a.city_host_directory, city_host)
    shutil.copytree(source, archive/'runtime-source')
    env = dict(os.environ, PYTHONPATH=str(source))
    budget = a.rollouts*8192
    state = dict(status='running', pid=os.getpid(), started=datetime.datetime.now().astimezone().isoformat(),
        parent=str(parent), parent_sha256=sha256(parent), host_sha256=sha256(host/'TrafficHost.dll'),
        city_host_sha256=sha256(city_host/'TrafficHost.dll'),
        added_decisions=budget, seed_start=a.seed_start, phase='migration', intervention='Only Wait corrections learn from explicit one-decision task reward. Conditional roads and original city critic/Adam retained. Native score reviews remain separate.')

    def publish():
        dump(out/'status.json', state); dump(archive/'status.json', state)

    def command_run(command, label):
        dump(archive/(label+'-command.json'), command)
        with (out/(label+'.log')).open('x') as log:
            subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

    def evaluate(kind, label, checkpoint):
        dest = out/'evaluation'/f'{kind}-{label}'
        script = {'decision': 'evaluate_city_wait_decision.py', 'native': 'evaluate_city_wait_decision.py',
                  'practice': 'audit_mini_behavior.py', 'city': 'evaluate_overnight_city.py'}[kind]
        evaluation_host = city_host if kind in ('practice', 'city') else host
        command = [sys.executable, '-u', str(source/script), '--dll', str(evaluation_host/'TrafficHost.dll'),
                   '--output', str(dest), '--workers', '2']
        if kind == 'practice':
            command += ['--checkpoints', str(checkpoint), '--labels', 'candidate', '--small-city-horizon', '300']
        else:
            command += ['--checkpoint', str(checkpoint)]
        if kind == 'native':
            command += ['--native']
        command_run(command, f'{kind}-{label}')
        shutil.copytree(dest, archive/'evaluation'/f'{kind}-{label}')
        print('REVIEW COMPLETE', kind, label, str(archive/'evaluation'/f'{kind}-{label}'/'summary.json'), flush=True)

    try:
        publish()
        command_run([sys.executable, '-u', str(source/'prepare_city_wait_learning.py'), '--parent', str(parent),
            '--dll', str(host/'TrafficHost.dll'), '--output', str(out/'initial'), '--archive', str(archive/'migration')], 'migration')
        evaluate('decision', 'initial', out/'initial/start.zip')
        state['phase'] = 'training'; publish()
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures = [pool.submit(evaluate, 'native', 'initial', out/'initial/start.zip')]
            queued = set()
            command = [sys.executable, '-u', str(source/'train_city_wait_decision.py'), '--parent', str(out/'initial/start.zip'),
                '--dll', str(host/'TrafficHost.dll'), '--output', str(out/'training'), '--workers', '16',
                '--rollout-steps', '512', '--rollouts', str(a.rollouts), '--batch-size', '128', '--epochs', '4',
                '--seed-start', str(a.seed_start)]
            dump(archive/'training-command.json', command)
            process = subprocess.Popen(command, cwd=root, env=env)
            last_stamp = None; last_activity = time.monotonic()

            def queue_ready():
                path = out/'training/checkpoints.json'
                if not path.exists():
                    return
                for item in json.loads(path.read_text()):
                    count = item['added_decisions']
                    if count in (budget//4, budget//2, budget) and count not in queued:
                        futures.append(pool.submit(evaluate, 'decision', str(count), Path(item['path'])))
                        if count == budget:
                            for kind in ('native', 'practice', 'city'):
                                futures.append(pool.submit(evaluate, kind, 'final', Path(item['path'])))
                        queued.add(count)
                measurements = archive/'measurements'; measurements.mkdir(exist_ok=True)
                for name in ('config.json', 'checkpoints.json', 'episodes.jsonl', 'progress.csv', 'complete.json'):
                    if (path := out/'training'/name).exists():
                        shutil.copy2(path, measurements/name)

            while process.poll() is None:
                queue_ready()
                stamps = [path.stat().st_mtime_ns for name in ('episodes.jsonl', 'checkpoints.json', 'progress.csv')
                          if (path := out/'training'/name).exists()]
                stamp = max(stamps, default=None)
                if stamp != last_stamp:
                    last_stamp = stamp; last_activity = time.monotonic()
                if time.monotonic()-last_activity > 600:
                    stop_owned_tree(process); raise RuntimeError('No training progress for ten minutes')
                time.sleep(10)
            queue_ready()
            if process.returncode:
                raise RuntimeError(f'Training exited {process.returncode}')
            assert queued == {budget//4, budget//2, budget}
            state['phase'] = 'evaluation'; publish()
            for future in futures:
                future.result()
        assert sha256(parent) == state['parent_sha256']
        summary = lambda kind, label: json.loads((archive/'evaluation'/f'{kind}-{label}'/'summary.json').read_text())
        report = dict(initial=summary('decision', 'initial'),
            curve=[dict(added_decisions=n, cases=summary('decision', str(n))) for n in sorted(queued)],
            native_initial=summary('native', 'initial'), native_final=summary('native', 'final'),
            practice_final=summary('practice', 'final'), city_final=summary('city', 'final'),
            limits='Binary practice correctness is not city score. Check repeated behavior, generalization and native retention. No automatic promotion, extension or overnight launch.')
        dump(archive/'results.json', report)
        lines = ['# Build-or-Wait PPO study', '', report['limits'], '',
                 '| Case | Initial correct probability | Final correct probability | Final native games without construction |',
                 '|---|---:|---:|---:|']
        for case, row in report['curve'][-1]['cases'].items():
            native = report['native_final'][case]
            lines.append(f"| {case} | {report['initial'][case]['mean_correct_probability']:.1%} | {row['mean_correct_probability']:.1%} | {native['no_build']}/{native['games']} |")
        lines += ['', f"Development city mean {report['city_final']['trips']:.2f}, scoring {report['city_final']['scoring']}/32. See raw native/mini reviews for service and construction."]
        (archive/'RESULTS.md').write_text('\n'.join(lines)+'\n')
        state.update(status='complete', phase='finished', finished=datetime.datetime.now().astimezone().isoformat()); publish()
        with (root/'training/EXPERIMENT_HISTORY.md').open('a') as f:
            f.write('\n\n## Build-or-Wait bounded study completed\nAll declared checkpoints and native/practice/city reviews completed. See docs/training/'+archive.name+'/RESULTS.md. No automatic promotion or overnight launch.\n')
    except BaseException as exc:
        state.update(status='error', error=repr(exc)); publish(); raise
    finally:
        dump(archive/'manifest.json', {str(p.relative_to(archive)): sha256(p) for p in archive.rglob('*')
             if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts})


if __name__ == '__main__':
    main()

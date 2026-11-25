"""Finalize this one recovered replay-export incident, only after all work ends."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / 'output/training/mini-reset-comparison-01'
ARCHIVE = ROOT / 'docs/training/mini-task-repair-2026-11-25'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    state = json.loads((OUT / 'status.json').read_text())
    assert state['status'] == 'error' and state['phase'] == 'evaluation' and state['arm'] == 'both', state
    assert 'CalledProcessError' in state['error'] and 'practice-reset-curriculum-65536' in state['error']
    recovery = json.loads((ARCHIVE / 'evaluation-recovery.json').read_text())
    assert recovery['recovered_evaluation_complete']
    assert sha(Path(state['parent'])) == state['parent_sha256']
    host_hash = sha(OUT / 'runtime/host/TrafficHost.dll')
    checks = []
    for arm in ('reset-curriculum', 'cold-control'):
        completed = json.loads((OUT / arm / 'complete.json').read_text())
        saved = json.loads((OUT / arm / 'checkpoints.json').read_text())
        assert saved[-1]['added_decisions'] == 262144
        assert completed['checkpoints'] == saved
        for row in saved:
            assert sha(Path(row['path'])) == row['sha256']
        for budget in (65536,131072,262144):
            checkpoint = next(row for row in saved if row['added_decisions'] == budget)
            for kind, count in (('practice',112),('city',32)):
                name = f'{kind}-{arm}-{budget}'
                source = OUT / 'evaluation' / name
                dest = ARCHIVE / 'evaluation' / name
                games = [json.loads(line) for line in (source / 'games.jsonl').read_text().splitlines()]
                assert len(games) == count
                assert sha(source / 'games.jsonl') == sha(dest / 'games.jsonl')
                meta = json.loads((source / ('config.json' if kind=='practice' else 'summary.json')).read_text())
                saved_hash = meta['models']['candidate']['sha256'] if kind=='practice' else meta['sha256']
                assert saved_hash == checkpoint['sha256'] and meta['host_sha256'] == host_hash
                checks.append(dict(evaluation=name, games=count, checkpoint_sha256=saved_hash,
                                   measurement_sha256=sha(source/'games.jsonl')))
    # Keep the original failure record; never silently replace its meaning.
    with (ARCHIVE/'controller-final-error.json').open('x') as stream:
        json.dump(state, stream, indent=2)
    subprocess.run([sys.executable, str(OUT/'runtime/training/summarize_mini_comparison.py'),
                    '--archive',str(ARCHIVE)],check=True)
    final=dict(state,status='complete-recovered',phase='finished',
               finished=datetime.datetime.now().astimezone().isoformat(),
               recovery_note='Training completed unchanged. Replay-template failure preserved; same evaluation rerun and all twelve evaluations/checkpoints verified. No promotion.')
    for path in (OUT/'status.json', ARCHIVE/'status.json'):
        temporary=path.with_suffix('.recovered.pending')
        temporary.write_text(json.dumps(final,indent=2)+'\n');temporary.replace(path)
    recovery.update(finalization_requires_recovery_review=False,finalization_complete=True,
                    evaluation_checks=checks,original_error_preserved='controller-final-error.json')
    (ARCHIVE/'evaluation-recovery.json').write_text(json.dumps(recovery,indent=2)+'\n')
    with (ROOT/'training/EXPERIMENT_HISTORY.md').open('a') as stream:
        stream.write('\n\n### Mini-task reset comparison completed with explicit export-error recovery\nBoth arms completed262144added decisions. All saved checkpoint hashes and12evaluation measurements verified. The first replay-template error is retained separately; its successful identical rerun is used in the summary. No training restart or promotion. [Results](../docs/training/mini-task-repair-2026-11-25/RESULTS.md).\n')
    print('Recovered comparison complete; all training and evaluation integrity checks passed. No promotion.')


if __name__=='__main__':main()

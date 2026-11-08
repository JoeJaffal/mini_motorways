"""Record reward-fixture-v5 for the 77-suite rules (native common-endpoint joins in ordinary play).

Same recipe as docs/training/event-parity-2026-11-08/source/record_reward_fixture.py (v4): the
historical v2 opening commands, then wait until the actual terminal. The cap is 900 s instead of
300 s because the current rules end this game at 305.15 s. Run from the repository root after
building simulation/Headless in Debug. v4 and earlier fixtures stay unchanged as history.
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path('training').resolve()))
from environment import TrafficEnv

out = pathlib.Path('docs/training/simulator-repairs-2026-11-08/reward-fixture-v5.json')
old = json.loads(pathlib.Path('docs/training/gameplay-fidelity-repairs-2026-11-08/reward-fixture-v2.json').read_text())
dotnet = sys.argv[1] if len(sys.argv) > 1 else 'dotnet'
env = TrafficEnv(dotnet=dotnet, seeds=[old['seed']], record_replays=True, seconds=900)
try:
    env.reset(seed=42)
    for event in old['actions']:
        if event['command'] == 'wait':
            break
        env._advance({k: v for k, v in event.items() if k in ['command', 'tool', 'x', 'y', 'toX', 'toY', 'id', 'choice']})
    while not env.done:
        env._advance(None)
    rec = env.export_replay()
    assert rec['terminated'] and not rec['truncated']
    rec['source'] = ('Ordinary-command reward correctness fixture for the 77-suite rules (native common-endpoint '
                     'joins apply in ordinary play); same initial commands as historical v2; wait to actual terminal '
                     'within 900s. No learning or policy performance.')
    out.write_text(json.dumps(rec, indent=2), encoding='utf-8')
    print(rec['score'], rec['duration'], len(rec['actions']))
finally:
    env.close()

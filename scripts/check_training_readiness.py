"""Exercise OriginalReference without constructing or training a model (stdlib only)."""
import argparse
import hashlib
import json
import math
import pathlib
import queue
import subprocess
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAPS = ['LosAngeles', 'Beijing', 'Tokyo', 'DarEsSalaam', 'London']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dotnet', default='dotnet')
parser.add_argument('--seconds', type=int, default=300)
args = parser.parse_args()
host = ROOT / 'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'
process = subprocess.Popen([args.dotnet, str(host)], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
messages = queue.Queue()
def read_messages():
    for line in process.stdout:
        messages.put(line)
    messages.put(None)
threading.Thread(target=read_messages, daemon=True).start()
requests = 0
def call(**request):
    global requests
    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()
    line = messages.get(timeout=30)
    if line is None:
        raise RuntimeError('Host exited unexpectedly')
    requests += 1
    return json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def valid(o):
    assert o['version'] == 'OriginalReference' and not o['unlimitedConstruction']
    assert o['width'] == 50 and o['height'] == 30
    for key in ['infrastructure', 'terrain', 'buildingColors', 'buildingKinds', 'demand',
                'reservations', 'connections', 'pendingRemovals']:
        assert len(o[key]) == 1500, key
    assert all(x >= 0 for x in o['inventory'])
    for vehicle in o['vehicles']:
        assert all(math.isfinite(vehicle[k]) for k in ['x', 'y', 'speed', 'waiting'])
        assert vehicle['speed'] >= 0 and vehicle['waiting'] >= 0

def episode(city, seed, policy):
    answer = call(command='reset', version='OriginalReference', scenario=city, seed=seed)
    digest = hashlib.sha256()
    samples = 0
    while True:
        assert 'error' not in answer, answer
        o = answer['observation']
        valid(o)
        digest.update(json.dumps(o, sort_keys=True, separators=(',', ':')).encode())
        samples += 1
        if answer['terminated'] or answer['truncated'] or o['time'] >= args.seconds:
            break
        if o['upgradeChoices']:
            assert call(command='upgrade', choice=0)['accepted']
        if policy == 'debug_roads':
            call(command='reference')  # Privileged diagnostic, NEVER a learned action.
        answer = call(command='step', ticks=200)
    if answer['terminated']:
        after = call(command='step', ticks=200)
        assert after['observation'] == o and after['terminated'], 'terminal must be absorbing'
    return dict(map=city, seed=seed, policy=policy, seconds=o['time'], trips=o['tripsCompleted'],
                terminated=answer['terminated'], rejected=answer['truncated'],
                capped=not (answer['terminated'] or answer['truncated']),
                maxWaiting=max((v['waiting'] for v in o['vehicles']), default=0),
                samples=samples, digest=digest.hexdigest())

started = time.perf_counter()
runs = []
try:
    base = call(command='reset', version='OriginalReference', scenario='LosAngeles', seed=42)
    assert 'error' in call(command='step', ticks=-1)
    assert 'error' in call(command='unknown-command')
    assert not call(command='build', tool='Road', x=-1, y=-1)['accepted']
    assert call(command='observe')['observation'] == base['observation'], 'invalid actions mutated state'
    assert call(command='step', ticks=0)['observation'] == base['observation']
    assert 'error' in call(command='reset', requireExact=True)
    for city in MAPS:
        for seed in [0, 42, 99]:
            for policy in ['wait', 'debug_roads']:
                first = episode(city, seed, policy)
                replay = episode(city, seed, policy)
                assert first == replay, ('nondeterministic replay', first, replay)
                runs.append(first)
        print(f'PASS: {city}: six episodes and six exact replays', flush=True)
    report = dict(result='PASS', version='OriginalReference', modelTrainingPerformed=False,
                  simulatorCommit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  seeds=[0, 42, 99], episodeLimitSeconds=args.seconds, episodes=len(runs)*2,
                  requests=requests, wallSeconds=time.perf_counter()-started,
                  checks=['fixed array shapes', 'finite vehicle values', 'nonnegative materials',
                          'exact deterministic replays', 'absorbing failures', 'reset isolation',
                          'invalid input recovery', 'zero-tick identity', 'exact-parity guard'],
                  scope='Wait and privileged debug-road diagnostics; no learned policy or throughput claim for a full RL adapter.',
                  runs=runs)
    (ROOT / 'simulation/Reports/training-readiness.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'PASS: {len(runs)*2} episodes; no model trained; {report["wallSeconds"]:.1f}s wall time')
finally:
    if process.poll() is None:
        process.stdin.write('{"command":"quit"}\n')
        process.stdin.flush()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

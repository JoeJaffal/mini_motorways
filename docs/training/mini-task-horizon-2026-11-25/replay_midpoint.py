"""Paired illustrative city replay nearest the median positive midpoint gain."""
import json, statistics
from pathlib import Path
from replay_city_suite import replay
from prepare_city_policy import sha256
r=Path('docs/training/mini-task-horizon-2026-11-25')
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
base={(x['seed'],x['action_seed']):x for x in read(r/'evaluation/city-initial/games.jsonl')}
rows=read(r/'evaluation/city-long-window-131072/games.jsonl')
positive=[x for x in rows if x['trips']>base[x['seed'],x['action_seed']]['trips']]
delta=lambda x:x['trips']-base[x['seed'],x['action_seed']]['trips']
median=statistics.median(map(delta,positive))
x=min(positive,key=lambda x:(abs(delta(x)-median),x['seed'],x['action_seed']))
out=r/'midpoint-city-replay';out.mkdir(exist_ok=False)
models={'original':Path('output/training/city-whole-initial-01/start.zip'),'midpoint':Path('output/training/mini-horizon-comparison-01/long-window/midpoint.zip')}
dll=Path('output/training/mini-horizon-comparison-01/runtime/host/TrafficHost.dll')
selected={'original':base[x['seed'],x['action_seed']],'midpoint':x}
config=dict(criterion='Closest gain to median among positive paired gains, tie lowest seed/action RNG. Selected illustration, not representative of losses or all games.',positive_count=len(positive),median_positive_gain=median,selected=selected,models={k:dict(path=str(p),sha256=sha256(p)) for k,p in models.items()},host_sha256=sha256(dll))
(out/'selection.json').write_text(json.dumps(config,indent=2)+'\n')
for label,expected in selected.items():
    replay(str(dll),str(models[label]),out/label,label,expected,600)
    assert sha256(models[label])==config['models'][label]['sha256']
assert sha256(dll)==config['host_sha256']
print('Paired midpoint replay exact; no learning.',flush=True)

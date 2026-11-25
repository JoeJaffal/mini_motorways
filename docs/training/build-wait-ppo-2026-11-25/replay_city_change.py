"""Paired city replay nearest the median score change across all development games."""
import json, statistics
from pathlib import Path
from replay_city_suite import replay
from prepare_city_policy import sha256
r=Path('docs/training/build-wait-ppo-2026-11-25')
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
base={(x['seed'],x['action_seed']):x for x in read(Path('docs/training/mini-fixed-route-2026-11-25/evaluation/city-final/games.jsonl'))}
rows=read(r/'evaluation/city-final/games.jsonl')
positive=rows
delta=lambda x:x['trips']-base[x['seed'],x['action_seed']]['trips']
median=statistics.median(map(delta,positive))
x=min(positive,key=lambda x:(abs(delta(x)-median),x['seed'],x['action_seed']))
out=r/'city-behavior-replay';out.mkdir(exist_ok=False)
models={'parent':Path('output/training/mini-fixed-route-01/training/final.zip'),'wait':Path('output/training/build-wait-01/training/final.zip')}
dll=Path('output/training/build-wait-01/runtime/city-host/TrafficHost.dll')
selected={'parent':base[x['seed'],x['action_seed']],'wait':x}
config=dict(criterion='Closest score change to median across ALL32paired games, tie lowest seed/action RNG. One illustration, not a substitute for the full distribution.',paired_games=len(positive),median_score_change=median,selected=selected,models={k:dict(path=str(p),sha256=sha256(p)) for k,p in models.items()},host_sha256=sha256(dll))
(out/'selection.json').write_text(json.dumps(config,indent=2)+'\n')
for label,expected in selected.items():
    replay(str(dll),str(models[label]),out/label,label,expected,600)
    assert sha256(models[label])==config['models'][label]['sha256']
assert sha256(dll)==config['host_sha256']
print('Paired Wait-study city replay exact; no learning.',flush=True)

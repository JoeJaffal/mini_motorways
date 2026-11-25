"""Paired illustrative regression replay: lowest seed newly failing after continuation."""
import json, statistics
from pathlib import Path
from replay_city_suite import replay
from prepare_city_policy import sha256
r=Path('docs/training/mini-fixed-route-continuation-2026-11-25')
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
base={(x['seed'],x['action_seed']):x for x in read(Path('docs/training/mini-fixed-route-2026-11-25/evaluation/city-final/games.jsonl'))}
rows=read(r/'evaluation/city-final/games.jsonl')
positive=[x for x in rows if x['trips']==0 and base[x['seed'],x['action_seed']]['trips']>0]
delta=lambda x:x['trips']-base[x['seed'],x['action_seed']]['trips']
median=statistics.median(map(delta,positive))
x=min(positive,key=lambda x:(x['seed'],x['action_seed']))
out=r/'city-regression-replay';out.mkdir(exist_ok=False)
models={'parent':Path('output/training/mini-fixed-route-01/training/final.zip'),'continuation':Path('output/training/mini-fixed-route-02/training/final.zip')}
dll=Path('output/training/mini-fixed-route-02/runtime/host/TrafficHost.dll')
selected={'parent':base[x['seed'],x['action_seed']],'continuation':x}
config=dict(criterion='Lowest seed/action RNG among new zero-score games after continuation. Selected failure illustration, not representative of all games.',new_zero_count=len(positive),median_delta_among_new_zeros=median,selected=selected,models={k:dict(path=str(p),sha256=sha256(p)) for k,p in models.items()},host_sha256=sha256(dll))
(out/'selection.json').write_text(json.dumps(config,indent=2)+'\n')
for label,expected in selected.items():
    replay(str(dll),str(models[label]),out/label,label,expected,600)
    assert sha256(models[label])==config['models'][label]['sha256']
assert sha256(dll)==config['host_sha256']
print('Paired regression replay exact; no learning.',flush=True)

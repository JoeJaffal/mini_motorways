"""Selected final-budget city behavior, not only the earlier positive example."""
import json,statistics
from pathlib import Path
from replay_city_suite import replay
from prepare_city_policy import sha256
r=Path('docs/training/route-spatial-run-2026-11-25')
assert json.loads((r/'status.json').read_text())['status']=='complete'
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
old={(x['seed'],x['action_seed']):x for x in read(Path('docs/training/build-wait-ppo-2026-11-25/evaluation/city-final/games.jsonl'))}
new=read(r/'evaluation/city-final/games.jsonl')
delta=lambda x:x['trips']-old[x['seed'],x['action_seed']]['trips']
median=statistics.median(map(delta,new))
row=min(new,key=lambda x:(abs(delta(x)-median),x['seed'],x['action_seed']))
out=r/'final-city-replay';out.mkdir(exist_ok=False)
models={'parent':Path('output/training/build-wait-01/training/final.zip'),'final':Path('output/training/route-spatial-01/training/final.zip')}
expected={'parent':old[row['seed'],row['action_seed']],'final':row}
dll=Path('output/training/route-spatial-01/runtime/host/TrafficHost.dll')
selection=dict(criterion='Closest paired score change to median across ALL32final-budget city plays, tie lowest seed/action RNG. One diagnostic illustration; later layouts can diverge.',median_change=median,selected=expected,models={k:dict(path=str(p),sha256=sha256(p)) for k,p in models.items()},host_sha256=sha256(dll))
(out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
for name,path in models.items():replay(str(dll),str(path),out/name,name,expected[name],600)
assert all(sha256(p)==selection['models'][k]['sha256'] for k,p in models.items()) and sha256(dll)==selection['host_sha256']
print('Final-budget paired city replay exact.',flush=True)

behavior={}
for name in models:
    steps=read(out/name/'steps.jsonl')
    v=json.loads((out/name/'verification.json').read_text())
    behavior[name]=dict(score=v['trips'],seconds=v['seconds'],builds=v['road_actions'],
        first_stockout=next((s['time'] for s in steps if s['stock']==0),None),
        first_delivery=next((s['time'] for s in steps if s['reward']>0),None))
(out/'behavior-summary.json').open('x').write(json.dumps(behavior,indent=2)+'\n')

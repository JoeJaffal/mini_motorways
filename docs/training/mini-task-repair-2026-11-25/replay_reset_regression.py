"""Exact paired replay of the largest loss among newly zero-scoring games."""
import json
from pathlib import Path
from replay_city_suite import replay
from prepare_city_policy import sha256

r=Path('docs/training/mini-task-repair-2026-11-25')
read=lambda p:[json.loads(line) for line in p.read_text().splitlines()]
original={(x['seed'],x['action_seed']):x for x in read(r/'evaluation/city-initial/games.jsonl')}
final=read(r/'evaluation/city-reset-curriculum-262144/games.jsonl')
failures=[x for x in final if x['trips']==0 and original[(x['seed'],x['action_seed'])]['trips']>0]
selected=max(failures,key=lambda x:original[(x['seed'],x['action_seed'])]['trips'])
before=original[(selected['seed'],selected['action_seed'])]
out=r/'reset-regression-replay';out.mkdir(exist_ok=False)
models=dict(original=Path('output/training/city-whole-initial-01/start.zip'),
            reset_final=Path('output/training/mini-reset-comparison-01/reset-curriculum/final.zip'))
dll=Path('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll')
config=dict(criterion='Largest original score among matched games newly scoring zero; illustrative selected failure, not representative average.',
            newly_zero_games=len(failures),original=before,reset_final=selected,
            models={k:dict(path=str(p),sha256=sha256(p)) for k,p in models.items()},host_sha256=sha256(dll))
(out/'selection.json').write_text(json.dumps(config,indent=2)+'\n')
for label,expected in [('original',before),('reset_final',selected)]:
    replay(str(dll),str(models[label]),out/label,label,expected,600)
    assert sha256(models[label])==config['models'][label]['sha256']
assert sha256(dll)==config['host_sha256']
print('Paired regression replay exact; no learning.',flush=True)

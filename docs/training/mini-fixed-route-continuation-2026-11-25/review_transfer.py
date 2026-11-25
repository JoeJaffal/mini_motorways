"""Review fixed-board learning and transfer against both retained references."""
from pathlib import Path
import json
from summarize_expansion_comparison import paired
r=Path('docs/training/mini-fixed-route-continuation-2026-11-25')
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
assert json.loads((r/'status.json').read_text())['status']=='complete'
city=read(r/'evaluation/city-final/games.jsonl');mini=read(r/'evaluation/practice-final/games.jsonl')
refs={
 'focused_run01_parent':Path('docs/training/mini-fixed-route-2026-11-25/evaluation/city-final/games.jsonl'),
 'retained_original':Path('docs/training/mini-task-horizon-2026-11-25/evaluation/city-initial/games.jsonl')}
report=dict(city_mean=sum(x['trips'] for x in city)/len(city),scoring=sum(x['trips']>0 for x in city),city_deltas={name:paired(city,read(path),('trips','paid_units','outside_routes')) for name,path in refs.items()},mini={})
base=read(Path('docs/training/mini-fixed-route-2026-11-25/evaluation/practice-final/games.jsonl'))
for exercise in sorted({x['exercise'] for x in mini}):
 rows=[x for x in mini if x['exercise']==exercise];old=[x for x in base if x['exercise']==exercise]
 report['mini'][exercise]=dict(games=len(rows),successes=sum(x['success'] for x in rows),first_served=sum(x['first_served'] for x in rows),both_served=sum(x['both_served'] for x in rows),parent_successes=sum(x['success'] for x in old),parent_both_served=sum(x['both_served'] for x in old))
report['limits']='Consumed development layouts. Parent is focused run01 final; this continues its unchanged fixed-board lesson. Neither reference is new held-out evidence. Fixed training board learning does not establish strategy.'
(r/'transfer-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

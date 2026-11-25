"""Describe completed reset-arm training episodes; not evaluation performance."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
root=Path('docs/training/mini-task-repair-2026-11-25')
path=root/'measurements/reset-curriculum/episodes.jsonl'
data=path.read_bytes();rows=[json.loads(s) for s in data.splitlines()]
# Original lifetime count is fixed in the retained checkpoint/migration evidence.
start=425984
buckets=defaultdict(list)
for row in rows:
    quarter=min(3,(row['decisions']-start-1)//65536)
    prefix=bool(row.get('prefix_id'))
    task=row['exercise']
    if task=='small-city-offset-pairs':
        later=row['new_deliveries'] if prefix else row['new_deliveries']-row['urgent_deliveries']
        assert 0<=later<=row['trips']
        success=later>0
    else:success=row['trips']>0
    buckets[(quarter,task,prefix)].append(dict(success=success,**row))
summary=[]
for (quarter,task,prefix),group in sorted(buckets.items()):
    summary.append(dict(quarter=quarter+1,task=task,recorded_start=prefix,games=len(group),
        success_definition='later destination delivered' if task.endswith('pairs') else 'at least one delivery',
        successes=sum(x['success'] for x in group),success_rate=statistics.mean(x['success'] for x in group),
        mean_score=statistics.mean(x['trips'] for x in group),mean_builds=statistics.mean(x['road_actions'] for x in group),
        unique_scenarios=len({x['seed'] for x in group})))
report=dict(source=str(path),source_sha256=hashlib.sha256(data).hexdigest(),games=len(rows),rows=summary,
    limits='Training episodes grouped by completion decision. Fixed prefix bank versus changing cold seeds; no randomized paired outcome inference. Later service derives from native new_deliveries minus initial urgent_deliveries for cold pairs; prefix pairs exclude already served initial shop.')
(root/'reset-training-behavior.json').write_text(json.dumps(report,indent=2)+'\n')
for r in summary:print(r['quarter'],r['task'],r['recorded_start'],r['games'],round(r['success_rate'],3),round(r['mean_builds'],2))

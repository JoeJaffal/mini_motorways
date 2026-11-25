"""Exactly replay the lowest-seed new both-pair success and first tight failure."""
import json
from pathlib import Path
from audit_mini_behavior import worker
from prepare_city_policy import sha256
root=Path('docs/training/mini-task-repair-2026-11-25/wait-repair')
out=root/'selected-replays';out.mkdir(exist_ok=False)
read=lambda path:[json.loads(s) for s in path.read_text().splitlines()]
models=dict(original=('output/training/city-whole-initial-01/start.zip',Path('docs/training/mini-task-horizon-2026-11-25/evaluation/practice-initial/games.jsonl')),
            wait_restored=('output/training/mini-reset-wait-repair-01/start.zip',root/'practice-300/games.jsonl'))
jobs=[('small-city-offset-pairs',231000003),('small-city-offset-single',231000000)]
checks=[]
for label,(path,record) in models.items():
    folder=out/label;folder.mkdir()
    expected={(r['exercise'],r['seed']):r for r in read(record)}
    digest=sha256(Path(path))
    rows=worker('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll',path,label,jobs,folder,300,(231000003,))
    for row in rows:
        old=expected[row['exercise'],row['seed']]
        for key,value in old.items():
            if key!='model':assert value==row[key],(label,key,value,row[key])
        checks.append(dict(model=label,exercise=row['exercise'],seed=row['seed'],score=row['score'],checkpoint_sha256=digest,all_existing_fields_exact=True))
    assert sha256(Path(path))==digest
(out/'checks.json').write_text(json.dumps(dict(selection='Lowest-seed newly both-served pair and lowest-seed tight failure; illustrative, not representative sampling.',checks=checks),indent=2)+'\n')
print('All four replays exactly match archived metrics.',flush=True)

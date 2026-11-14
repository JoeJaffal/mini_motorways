#!/bin/sh
# rebuild the draft replay and run it with unlimited stock; extra env vars pass through to the harness
cd "/c/Projects/490 - Project/mm-fidelity/tmp/video/g2"
py -3 build_replay.py >/dev/null && py -3 post_erase.py >/dev/null && py -3 - <<'PY'
import json
r=json.load(open('replay-g2-draft1.json'))
for e in r['events']:
    if e['kind'] in ('draw','erase','driveway'):e['allowRejection']=True
r['startingInventory']=[500,20,0,0,0,0]
json.dump(r,open('replay-g2-draft1c.json','w'),indent=1)
PY
cd ../../..; P=${PH:-$(head -1 tmp/runs/plausible-phases-v21e-60.txt)}
tmp/hbin-g2/Harness.exe tmp/video/g2/replay-g2-draft1c.json - $P 2>&1 | grep -E "ROUTE|AUDIT|# end|^AT|Unhandled"

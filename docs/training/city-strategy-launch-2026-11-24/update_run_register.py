from pathlib import Path
from collections import defaultdict
import json,re
root=Path.cwd();rec=root/'docs/training/city-strategy-launch-2026-11-24';rows=[]
stopped={'city-strategy-wide-pilot-01':'Chat interruption; unsaved updates lost','city-strategy-wide-pilot-02':'Stopped for RAM pressure before first checkpoint','city-strategy-longer-pilot-01':'Chat interruption before checkpoint','city-strategy-mixed-pilot-01':'Stopped at saved32k to correct sample allocation','city-strategy-balanced-pilot-01':'Stopped at saved8k for parity-checked acceleration; worker-close hang cleaned up'}
for config in sorted((root/'output/training').glob('city-strategy-*/**/config.json')):
 d=json.loads(config.read_text())
 if 'decision_budget' not in d:continue
 folder=config.parent;complete=folder/'complete.json';checkpoint=folder/'checkpoints.json';saves=json.loads(checkpoint.read_text()) if checkpoint.exists() else []
 episodes=folder/'episodes.jsonl';groups=defaultdict(list)
 if episodes.exists():
  for line in episodes.read_text().splitlines():
   try:r=json.loads(line)
   except json.JSONDecodeError:continue
   groups[r['exercise']].append(r)
 state='complete' if complete.exists() else stopped.get(folder.name,'incomplete; inspect controller status')
 if 'city-strategy-short-delay-01' in str(folder) and not complete.exists():state='Stopped at saved16384 midpoint after measured gradient imbalance; unsaved tail not carried forward'
 if 'city-strategy-bridge-balanced-01' in str(folder) and not complete.exists():state='Stopped at saved24576 after longer baseline favored calibrated reference; unsaved tail not carried forward'
 if 'integration-smoke' in str(folder) and complete.exists():state='Complete integration smoke only; never a performance candidate'
 rows.append(dict(path=str(folder.relative_to(root)),status=state,config=d,checkpoints=saves,episodes_by_task={k:dict(count=len(v),mean_training_score=sum(x['r'] for x in v)/len(v),completed_decisions=sum(x['l'] for x in v)) for k,v in groups.items()},note='Training means are descriptive, not frozen evaluation. Completed episode lengths omit unfinished episodes.'))
(rec/'run-register.json').write_text(json.dumps(rows,indent=2)+'\n');print(len(rows),'trainer records')

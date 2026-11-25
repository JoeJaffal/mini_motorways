"""Reconstruct terminal coverage from recorded fixed-worker episode boundaries."""
from pathlib import Path
import json
root=Path.cwd();rec=root/'docs/training/city-strategy-launch-2026-11-24'
folder=root/'output/training/city-strategy-bridge-reference-city-01/segment-001'
config=json.loads((folder/'config.json').read_text());rows=[json.loads(x) for x in (folder/'episodes.jsonl').read_text().splitlines()]
workers=config['workers'];seed0=config['seed_start'];steps=config['decision_budget']//workers
initials=[r['decisions']-r['l']*workers for r in rows if seed0<=r['seed']<seed0+workers]
assert len(set(initials))==1;offset=initials[0]
ends={w:[] for w in range(workers)}
for row in rows:
 assert (row['decisions']-offset)%workers==0
 w=(row['seed']-seed0)%workers
 ends[w].append(((row['decisions']-offset)//workers,row['truncated']))
for w,items in ends.items():
 last=0
 for end,truncated in items:
  row=next(r for r in rows if (r['seed']-seed0)%workers==w and (r['decisions']-offset)//workers==end)
  assert end-last==row['l'];last=end
result={}
for window in (512,1024):
 direct=0
 for w in range(workers):
  items=ends[w]
  for t in range(1,steps+1):
   boundary=((t-1)//window+1)*window
   next_end=next(((end,truncated) for end,truncated in items if end>=t),None)
   direct+=bool(next_end and next_end[0]<=boundary and not next_end[1])
 result[str(window)]=dict(direct_terminal_return_samples=direct,total_samples=steps*workers,direct_terminal_return_fraction=direct/(steps*workers))
report=dict(source=str(folder.relative_to(root)),measurements=result,note='Same recorded trajectories regrouped retrospectively. Time-limit terminations retain bootstrap. Unfinished tails require bootstrap. This estimates return-target coverage only, not score improvement or trajectories of the new policy.')
(rec/'rollout-bootstrap-coverage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

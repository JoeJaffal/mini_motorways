import json
from pathlib import Path
import numpy as np
from summarize_expansion_comparison import paired
root=Path('docs/training/mini-task-repair-2026-11-25/wait-repair')
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
rows=read(root/'practice-300/games.jsonl')
base=read(Path('docs/training/mini-task-horizon-2026-11-25/evaluation/practice-initial/games.jsonl'))
result={}
for ex in sorted({r['exercise'] for r in rows}):
    candidate=[r for r in rows if r['exercise']==ex];original=[r for r in base if r['exercise']==ex]
    result[ex]=dict(games=len(candidate),success=sum(r['success'] for r in candidate),
        first_served=sum(r['first_served'] for r in candidate),both_served=sum(r['both_served'] for r in candidate),
        original_success=sum(r['success'] for r in original),original_both=sum(r['both_served'] for r in original),
        score=float(np.mean([r['score'] for r in candidate])),
        delta=paired(candidate,original,('score','success','first_served','both_served','paid','outside_routes')))
report=dict(practice=result,screen_pass=False,
    reason='Tight single8/16<14; both pairs5/16<8. Short skills retained. City component swap not a fresh confirmation.',
    limits='Reused development layouts, one candidate, no new training or promotion. Restoration is an engineering intervention, not learning by itself.')
(root/'practice-review.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Wait restoration review','','The explicit checkpoint migration retains trained road weights and Adam history, restores original zero-output Wait corrections, and freezes them. This recovers much of the observed city regression in the probability-component diagnostic; it does not establish a gain over the original.','',
'| Exercise | Original success | Restored success |','|---|---:|---:|']
for ex,row in result.items():
    key='both_served' if ex.endswith('pairs') else 'success';baseline='original_both' if ex.endswith('pairs') else 'original_success'
    lines.append(f"| {ex} | {row[baseline]}/16 | {row[key]}/16 |")
lines+=['','Small-city evaluation uses300seconds for both policies; the four old geometry tasks remain60seconds. Two-pair success in this table requires both destinations served. Native score only.','',
'The restored policy fails the declared development screen: tight singles remain8/16, and both-pair service is5/16 versus a target of8/16. No promotion or overnight launch. Preserve this candidate for possible bounded road-learning work after the ongoing comparisons.','',
'Migration checks preserve all non-Wait weights,22named Adam states at8192steps, lifetime decision and SB3 update counters.384shared states match the intended component distribution within5.35e-7. A disposable optimizer update changes roads/spatial encoder/critic while Wait stays within3.58e-7 on12shared states; the saved checkpoint and8192step optimizer remain unchanged. This checks mechanics, not training effectiveness.','',
'Checkpoint weights are local-only at output/training/mini-reset-wait-repair-01/start.zip. Source, hashes, raw112-game results and optimizer checks accompany this report.']
(root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(report,indent=2))

import json
from pathlib import Path
import statistics
root=Path('docs/training/mini-task-repair-2026-11-25/wait-repair')
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
a=read(root/'gradient-diagnostic/states.jsonl');b=read(root/'gradient-direction/states.jsonl')
assert a==b
old=json.loads((root/'gradient-diagnostic/report.json').read_text());new=json.loads((root/'gradient-direction/report.json').read_text())
assert old['episodes']==new['episodes']
rows=read(root/'gradient-direction/gradient_batches.jsonl');summary=[]
for task in sorted({r['task'] for r in rows}):
    group=[r for r in rows if r['task']==task]
    valid=[r for r in group if r['gradient_norms']['policy'][1]>1e-8]
    projections=[r['gradient_cosines']['policy_vs_value'][1]*r['gradient_norms']['value'][1]/r['gradient_norms']['policy'][1] for r in valid]
    summary.append(dict(task=task,batches=len(group),nondegenerate_encoder_batches=len(valid),
        opposing_encoder_batches=sum(r['gradient_cosines']['policy_vs_value'][1]<0 for r in valid),
        value_projection_relative_to_actor=projections,
        mean_norms={name:[statistics.mean(r['gradient_norms'][name][i] for r in group) for i in range(3)] for name in ('policy','entropy','value','return_policy')}))
report=dict(summary=summary,identical_episodes_and_sampled_states=True,
    limits='Frozen finite on-policy MonteCarlo diagnostic,256choice states from16development games. Seven nondegenerate shared-encoder batches; one nearzero actor gradient excluded from cosine interpretation. Does not reconstruct actual PPO minibatch/Adam updates or isolate causal city effects.')
(root/'gradient-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

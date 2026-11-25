"""Plot completed fixed-board diagnostic; training and evaluation are separate."""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('docs/training/mini-fixed-route-2026-11-25')
assert json.loads((r/'status.json').read_text())['status']=='complete'
read=lambda p:[json.loads(s) for s in p.read_text().splitlines()]
episodes=read(r/'measurements/episodes.jsonl');start=688128
batches=[]
for end in range(8192,65537,8192):
 rows=[x for x in episodes if end-8192<x['decisions']-start<=end]
 batches.append(dict(through_decisions=end,episodes=len(rows),success_fraction=sum(x['trips']>0 for x in rows)/len(rows)))
points=[]
for count,folder in [(0,r/'initial')]+[(n,r/'evaluation'/f'fixed-{n}') for n in (16384,32768,65536)]:
 d=json.loads((folder/'summary.json').read_text());points.append(dict(decisions=count,successes=d['successes'],games=d['games']))
source=dict(training_batches=batches,evaluation_points=points,episode_source_sha256=hashlib.sha256((r/'measurements/episodes.jsonl').read_bytes()).hexdigest(),limits='One repeated training layout. Evaluation reuses32action draws. Training batches contain changing episode boundaries; no geometry generalization claim.')
(r/'learning-curve.json').write_text(json.dumps(source,indent=2)+'\n')
fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
axes[0].plot([x['through_decisions']/1000 for x in batches],[100*x['success_fraction'] for x in batches],marker='o');axes[0].set_title('Training: successful completed games')
axes[1].plot([x['decisions']/1000 for x in points],[100*x['successes']/x['games'] for x in points],marker='o');axes[1].axhline(100*29/32,ls='--',color='gray',label='Practical mastery target');axes[1].legend(loc='lower right');axes[1].set_title('Fixed review: same 32 action draws')
for ax in axes:ax.set(xlabel='Added decisions (thousands)',ylabel='Successful games (%)',ylim=(0,105));ax.grid(alpha=.2)
fig.suptitle('One difficult connection — native-score PPO, no teacher actions')
fig.savefig(r/'learning-curve.png',dpi=150);plt.close(fig)

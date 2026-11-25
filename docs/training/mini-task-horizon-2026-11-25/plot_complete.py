"""Completed matched-budget curves; no inference from training collection scores."""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path(__file__).parent
assert json.loads((r/'status.json').read_text())['status']=='complete'
data=json.loads((r/'results.json').read_text())
fig,axes=plt.subplots(1,3,figsize=(16,4.5),constrained_layout=True)
for arm,label,color in [('short-control','60-second lessons','#597cb0'),('long-window','300-second lessons','#bc795a')]:
 rows=[x for x in data['curves'] if x['arm']==arm]
 x=[p['added_decisions']/1000 for p in rows]
 axes[0].plot([0]+x,[data['parent_city_mean']]+[p['city_mean'] for p in rows],marker='o',label=label,color=color)
 axes[1].plot(x,[100*p['practice']['small-city-offset-single']['first_served'] for p in rows],marker='o',label=label,color=color)
 axes[2].plot(x,[100*p['practice']['small-city-offset-pairs']['both_served'] for p in rows],marker='o',label=label,color=color)
axes[0].axhline(data['parent_city_mean'],color='#777',ls='--',lw=1)
axes[0].set(ylabel='Mean native city score',title='Same32development plays,600-second cap')
axes[1].set(ylabel='Successful service (%)',ylim=(0,105),title='Tight single connection,16layouts')
axes[2].set(ylabel='Both pairs served (%)',ylim=(0,105),title='Two arrivals,16layouts')
for ax in axes:
 ax.set_xlabel('Added PPO decisions (thousands)');ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('Lesson duration: inspect the full curve, not only an early improvement\nOne training seed per arm; fixed consumed development layouts')
fig.savefig(r/'complete-learning-curves.png',dpi=150)
plt.close(fig)
(r/'complete-figure-source.json').open('x').write(json.dumps(dict(results_sha256=hashlib.sha256((r/'results.json').read_bytes()).hexdigest(),limits=data['limits']),indent=2)+'\n')

"""Rebuild the documented four-hour learning plot from archived monitor CSV."""
from pathlib import Path
import csv
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parent
rows=[]
for path in (BASE/'evidence-2026-10-28/runs/seed-1000-parallel-02').glob('*.monitor.csv'):
    with path.open() as handle:
        next(handle)
        rows.extend((float(r['t']),float(r['r'])) for r in csv.DictReader(handle))
rows.sort()
scores=[score for _,score in rows]
rolling=[statistics.mean(scores[i-99:i+1]) for i in range(99,len(scores))]
hourly=[statistics.mean(score for t,score in rows if h*3600<=t<(h+1)*3600) for h in range(4)]
fig,axes=plt.subplots(1,2,figsize=(12,4.2),gridspec_kw={'width_ratios':[2,1]},layout='constrained')
axes[0].scatter(range(1,len(scores)+1),scores,s=3,alpha=.2,color='#087f83',label='Completed game')
axes[0].plot(range(100,len(scores)+1),rolling,color='#b55c17',linewidth=1.8,label='100-game mean')
axes[0].set(xlabel='Completed game (all four workers)',ylabel='Trips',title='Consistency improves, then plateaus',ylim=(0,80))
axes[0].legend(frameon=False,fontsize=8)
axes[1].bar(range(1,5),hourly,color='#087f83',width=.6)
for h,mean in enumerate(hourly,1):axes[1].text(h,mean+1,f'{mean:.2f}',ha='center',fontsize=9)
axes[1].set(xlabel='Monitor elapsed hour',ylabel='Mean trips',title='Hourly averages',ylim=(0,80),xticks=[1,2,3,4])
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',alpha=.15)
fig.suptitle('Seed 1000 | resumed MaskablePPO | four workers | one four-hour run',fontsize=12)
fig.savefig(BASE/'four-hour-performance.png',dpi=180)
plt.close(fig)
print(f'Plotted {len(rows)} games; hourly means: {hourly}')

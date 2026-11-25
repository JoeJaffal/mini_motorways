"""Draw frozen evaluation curves after the bounded study completes."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('docs/training/route-spatial-run-2026-11-25')
review=json.loads((r/'review.json').read_text())
curve=review['outcome_curve']
fig,axes=plt.subplots(1,3,figsize=(15,4.5),constrained_layout=True)
for key,label in [('small-city-offset-single','Tight stock'),('small-city-offset-stock','Generous stock')]:
    x=[p['added_decisions']/1000 for p in curve]
    axes[0].plot(x,[100*p['cases'][key]['successes']/p['cases'][key]['games'] for p in curve],marker='o',label=label)
    axes[1].plot(x,[p['cases'][key]['mean_builds'] for p in curve],marker='o',label=label)
axes[0].set(xlabel='Added PPO decisions (thousands)',ylabel='Successful first delivery (%)',ylim=(0,105),title='Fixed development layouts')
axes[1].set(xlabel='Added PPO decisions (thousands)',ylabel='Mean construction actions',title='All games, including failures')
for ax in axes[:2]:
    ax.grid(alpha=.2);ax.legend()
mean=review['city_mean']
parent=mean-review['city_comparisons']['parent']['trips']['mean']
original=mean-review['city_comparisons']['original']['trips']['mean']
axes[2].bar(['Original','Parent','Route lesson'],[original,parent,mean],color=['#aaa','#597cb0','#61a876'])
axes[2].set(ylabel='Mean native city score',title='32 development plays,600-second cap')
for i,v in enumerate([original,parent,mean]):axes[2].text(i,v+2,f'{v:.1f}',ha='center')
axes[2].set_ylim(0,max(original,parent,mean)*1.2)
fig.suptitle('Practice learning and city transfer are separate results')
fig.savefig(r/'learning-and-transfer.png',dpi=150)
plt.close(fig)
(r/'figure-source.json').open('x').write(json.dumps(dict(review_sha256=hashlib.sha256((r/'review.json').read_bytes()).hexdigest(),scope='Consumed development layouts; no independent confirmation.'),indent=2)+'\n')

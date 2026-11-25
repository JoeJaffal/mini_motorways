from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('docs/training/overnight-learning-2026-11-25');data=json.loads(Path('docs/training/road-cost-continuation-2026-11-24/results.json').read_text())['curves']
fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
for ax,stock,title in zip(axes,['single','stock'],['Tight road stock','Generous road stock']):
 for arm,label,color in [('control','Deliveries only','#777777'),('strong','Deliveries minus road cost','#007c91')]:
  rows=sorted([x for x in data if x['arm']==arm and x['exercise'].endswith(stock)],key=lambda x:x['budget'])
  ax.plot([x['budget']/1000 for x in rows],[x['first_served']*100 for x in rows],marker='o',label=label,color=color)
 ax.set(title=title,xlabel='Training decisions (thousands)',ylabel='Connections successful (%)',ylim=(40,100));ax.grid(alpha=.2)
axes[1].legend(loc='lower right');fig.suptitle('Longer practice helped — city transfer remains a separate test')
fig.savefig(r/'completed-practice-curves.png',dpi=170)
(r/'plot-source.json').write_text(json.dumps(data,indent=2)+'\n')

import ast,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('docs/training/route-spatial-run-2026-11-25/remaining-failure-replay')
selection=json.loads((r/'selection.json').read_text());labels=list(selection['selected'])
node=ast.parse(Path('training/environment.py').read_text())
dirs=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d','#36bbb1','#de8cb3']
fig,axes=plt.subplots(2,len(labels),figsize=(8*len(labels),8),squeeze=False,constrained_layout=True)
for col,label in enumerate(labels):
 data={name:json.loads((r/label/name/'trace.json').read_text())['frames'][-1] for name in ['parent','candidate']}
 points=[(c%50,c//50) for f in data.values() for c,bits in f['connections']]+[(b['cell']['x'],b['cell']['y']) for f in data.values() for b in f['buildings']]
 xs,ys=zip(*points)
 for row,(name,f) in enumerate(data.items()):
  ax=axes[row,col]
  for cell,bits in f['connections']:
   x,y=cell%50,cell//50
   for k,(dx,dy) in enumerate(dirs[:4]):
    if bits&(1<<k):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#777',lw=2,zorder=1)
  for b in f['buildings']:
   x,y=b['cell']['x'],b['cell']['y']
   ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']%8],zorder=2))
   ax.text(x+.5*b['width'],y+.5*b['height'],'H' if b['isHouse'] else 'D',color='white',ha='center',va='center')
  info=json.loads((r/label/name/'verification.json').read_text())
  ax.set(xlim=(min(xs)-2,max(xs)+4),ylim=(max(ys)+4,min(ys)-2),aspect='equal',title=f"{label} / {name}\n{'Service succeeded' if info['task_success'] else 'No service'}; stock {info['road_stock']}; builds {info['road_actions']}")
fig.suptitle('Remaining failure: both policies exhaust stock without connecting\nFinal observed board after native waiting')
fig.savefig(r/'paired-examples.png',dpi=150)
plt.close(fig)

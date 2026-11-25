from pathlib import Path
import ast,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('docs/training/city-negative-pair-audit-2026-11-25')
node=ast.parse(Path('training/environment.py').read_text());dirs=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d','#36bbb1','#de8cb3']
fig,axes=plt.subplots(1,4,figsize=(14,4),constrained_layout=True)
for ax,case in zip(axes,('match','mismatch','homes','destinations')):
 d=json.loads((r/'evaluation'/f'focused_final-{case}.json').read_text());f=d['replay']['frames'][-1]
 points=[(cell%50,cell//50) for cell,bits in f['connections']]+[(b['cell']['x'],b['cell']['y']) for b in f['buildings']];xs,ys=zip(*points)
 for cell,bits in f['connections']:
  x,y=cell%50,cell//50
  for k,(dx,dy) in enumerate(dirs[:4]):
   if bits&(1<<k):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#777',lw=2,zorder=1)
 for b in f['buildings']:
  x,y=b['cell']['x'],b['cell']['y'];ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']],zorder=2));ax.text(x+b['width']/2,y+b['height']/2,('H' if b['isHouse'] else 'D')+str(b['color']),color='white',ha='center',va='center')
 ax.set(xlim=(min(xs)-1,max(xs)+4),ylim=(max(ys)+3,min(ys)-1),aspect='equal',title=f"{case}\nscore {f['score']}, stock {f['road_stock']}")
fig.suptitle('Focused-route final: first audit seed of each isolated pair\nH = home, D = destination; no later arrivals in these fixtures')
fig.savefig(r/'cases.png',dpi=150);plt.close(fig)

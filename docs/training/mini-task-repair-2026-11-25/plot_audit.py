from pathlib import Path
import json,ast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('docs/training/mini-task-repair-2026-11-25/audit')
node=ast.parse(Path('training/environment.py').read_text());dirs=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d']
for case in ('clear','obstacle','small-city-offset-single','small-city-offset-pairs'):
 paths=[r/'replays'/f'{name}-{case}-231000000.json' for name in ('original','expansion')]
 if not all(p.exists() for p in paths):continue
 data=[json.loads(p.read_text())['replay'] for p in paths];fig,axes=plt.subplots(2,4,figsize=(15,8),constrained_layout=True)
 points=[(b['cell']['x'],b['cell']['y']) for d in data for f in d['frames'] for b in f['buildings']]
 points += [(cell%50,cell//50) for d in data for f in d['frames'] for cell,bits in f['connections']]
 xs,ys=zip(*points)
 for i,(d,label) in enumerate(zip(data,['Original','Expansion'])):
  frames=d['frames'];chosen=[min(frames,key=lambda f:abs(f['time']-t)) for t in (0,10,30)]+[frames[-1]]
  for ax,f in zip(axes[i],chosen):
   for cell,bits in f['connections']:
    x,y=cell%50,cell//50
    for k,(dx,dy) in enumerate(dirs[:4]):
     if bits&(1<<k):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#777',lw=2,zorder=1)
   for b in f['buildings']:
    x,y=b['cell']['x'],b['cell']['y'];ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']%len(colors)],zorder=2));ax.text(x+.5*b['width'],y+.5*b['height'],'H' if b['isHouse'] else 'D',color='white',ha='center',va='center',fontsize=8)
   ax.set(xlim=(min(xs)-2,max(xs)+4),ylim=(max(ys)+4,min(ys)-2),aspect='equal',title=f"{label}: {f['time']:.0f}s / score {f['score']} / stock {f['road_stock']}")
 fig.suptitle(f"Mini-task audit: {case} (H=home, D=destination; final column is each game's own end)")
 fig.savefig(r/(case+'-frames.png'),dpi=140);plt.close(fig)

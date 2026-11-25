from pathlib import Path
import json,ast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('docs/training/mini-task-repair-2026-11-25/long-replays')
node=ast.parse(Path('training/environment.py').read_text());dirs=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d','#36bbb1','#de8cb3']
for case in ('best','typical','worst'):
 data=json.loads((r/case/'trace.json').read_text());frames=data['frames'];end=frames[-1]['time'];chosen=[min(frames,key=lambda f:abs(f['time']-t)) for t in (min(30,end/4),min(180,end/2),min(600,end*.75))]+[frames[-1]]
 fig,axes=plt.subplots(1,4,figsize=(18,3.8),constrained_layout=True)
 points=[(cell%50,cell//50) for f in frames for cell,bits in f['connections']]+[(b['cell']['x'],b['cell']['y']) for f in frames for b in f['buildings']];xs,ys=zip(*points)
 for ax,f in zip(axes,chosen):
  for cell,bits in f['connections']:
   x,y=cell%50,cell//50
   for k,(dx,dy) in enumerate(dirs[:4]):
    if bits&(1<<k):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#888',lw=1.2,zorder=1)
  for b in f['buildings']:
   x,y=b['cell']['x'],b['cell']['y'];ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']%len(colors)],zorder=2));ax.text(x+.5*b['width'],y+.5*b['height'],('H' if b['isHouse'] else 'D')+str(b['color']),color='white',ha='center',va='center',fontsize=5)
  if f['cars']:ax.scatter([v['x'] for v in f['cars']],[v['y'] for v in f['cars']],s=3,c='#151515',zorder=3)
  ax.set(xlim=(min(xs)-2,max(xs)+4),ylim=(max(ys)+4,min(ys)-2),aspect='equal',title=f"{f['time']:.0f}s / score {f['score']} / stock {f['road_stock']}")
 fig.suptitle(f"Original policy, {case} of16 long diagnostic plays — H=home, D=destination, dots=cars")
 fig.savefig(r/f'{case}-frames.png',dpi=140);plt.close(fig)

from pathlib import Path
import ast
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

root=Path('docs/training/mini-fixed-route-continuation-2026-11-25/city-regression-replay')
node=ast.parse(Path('training/environment.py').read_text())
dirs=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d','#36bbb1','#de8cb3']
data={label:json.loads((root/label/'trace.json').read_text()) for label in ('parent','continuation')}
points=[(cell%50,cell//50) for d in data.values() for frame in d['frames'] for cell,bits in frame['connections']]
points += [(b['cell']['x'],b['cell']['y']) for d in data.values() for frame in d['frames'] for b in frame['buildings']]
xs,ys=zip(*points)
fig,axes=plt.subplots(2,4,figsize=(16,8),constrained_layout=True)
for row,(label,d) in enumerate(data.items()):
    frames=d['frames']
    chosen=[next(f for f in reversed(frames) if f['time']<=t) for t in (1,30,140)]+[frames[-1]]
    for col,(ax,f) in enumerate(zip(axes[row],chosen)):
        for cell,bits in f['connections']:
            x,y=cell%50,cell//50
            for k,(dx,dy) in enumerate(dirs[:4]):
                if bits&(1<<k):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#777',lw=1.2,zorder=1)
        for b in f['buildings']:
            x,y=b['cell']['x'],b['cell']['y']
            ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']%8],zorder=2))
            ax.text(x+.5*b['width'],y+.5*b['height'],('H' if b['isHouse'] else 'D')+str(b['color']),color='white',ha='center',va='center',fontsize=6)
        if f['cars']:ax.scatter([v['x'] for v in f['cars']],[v['y'] for v in f['cars']],s=4,c='#111',zorder=3)
        ax.set(xlim=(min(xs)-2,max(xs)+4),ylim=(max(ys)+4,min(ys)-2),aspect='equal',
               title=f"{'End: ' if col==3 else ''}{f['time']:.0f}s · score {f['score']} · stock {f['road_stock']}")
        if col==0:ax.set_ylabel('Focused run01 parent' if row==0 else 'Focused run02 continuation')
fig.suptitle('Same city and action RNG: selected new zero-score regression\nH = home, D = destination, number = color ID; black dots = cars')
fig.savefig(root/'comparison.png',dpi=150)
plt.close(fig)

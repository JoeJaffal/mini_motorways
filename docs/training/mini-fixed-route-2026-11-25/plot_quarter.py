from pathlib import Path
import ast,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path('docs/training/mini-fixed-route-2026-11-25/quarter-replay')
node=ast.parse(Path('training/environment.py').read_text())
dirs=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d','#36bbb1','#de8cb3']
data={name:json.loads((root/(name+'.json')).read_text())['replay'] for name in ('parent','quarter')}
points=[(cell%50,cell//50) for d in data.values() for f in d['frames'] for cell,bits in f['connections']]
points += [(b['cell']['x'],b['cell']['y']) for d in data.values() for f in d['frames'] for b in f['buildings']]
xs,ys=zip(*points);fig,axes=plt.subplots(2,3,figsize=(12,8),constrained_layout=True)
for row,(name,d) in enumerate(data.items()):
    frames=d['frames'];chosen=[next(f for f in reversed(frames) if f['time']<=t) for t in (2,30)]+[frames[-1]]
    for col,(ax,f) in enumerate(zip(axes[row],chosen)):
        for cell,bits in f['connections']:
            x,y=cell%50,cell//50
            for k,(dx,dy) in enumerate(dirs[:4]):
                if bits&(1<<k):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#777',lw=2,zorder=1)
        for b in f['buildings']:
            x,y=b['cell']['x'],b['cell']['y']
            ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']%8],zorder=2))
            ax.text(x+b['width']/2,y+b['height']/2,('H' if b['isHouse'] else 'D')+str(b['color']),color='white',ha='center',va='center',fontsize=7)
        if f['cars']:ax.scatter([v['x'] for v in f['cars']],[v['y'] for v in f['cars']],s=8,c='#111',zorder=3)
        ax.set(xlim=(min(xs)-1,max(xs)+3),ylim=(max(ys)+3,min(ys)-1),aspect='equal',title=f"{'End: ' if col==2 else ''}{f['time']:.0f}s · score {f['score']} · stock {f['road_stock']}")
        if col==0:ax.set_ylabel('Starting candidate' if row==0 else 'After 16k focused decisions')
fig.suptitle('Selected newly successful hard connection\nSame training board / action RNG; H = home, D = destination; black dots = cars')
fig.savefig(root/'comparison.png',dpi=150);plt.close(fig)

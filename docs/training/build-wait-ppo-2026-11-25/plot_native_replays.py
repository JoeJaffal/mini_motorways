from pathlib import Path
import ast,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).parent
node=ast.parse(Path('training/environment.py').read_text());dirs=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d','#36bbb1','#de8cb3']
fig,axes=plt.subplots(2,4,figsize=(14,8),constrained_layout=True)
for col,case in enumerate(('match','mismatch','quiet','route')):
 frames=[json.loads((r/f'replays-{label}'/case/'trace.json').read_text())['frames'][-1] for label in ('initial','final')]
 points=[(cell%50,cell//50) for f in frames for cell,bits in f['connections']]+[(b['cell']['x'],b['cell']['y']) for f in frames for b in f['buildings']];xs,ys=zip(*points)
 for row,f in enumerate(frames):
  ax=axes[row,col]
  for cell,bits in f['connections']:
   x,y=cell%50,cell//50
   for k,(dx,dy) in enumerate(dirs[:4]):
    if bits&(1<<k):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#777',lw=2,zorder=1)
  for b in f['buildings']:
   x,y=b['cell']['x'],b['cell']['y'];ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']],zorder=2));ax.text(x+b['width']/2,y+b['height']/2,('H' if b['isHouse'] else 'D')+str(b['color']),color='white',ha='center',va='center',fontsize=8)
  ax.set(xlim=(min(xs)-1,max(xs)+4),ylim=(max(ys)+3,min(ys)-1),aspect='equal',title=f"{case}: {f['time']:.0f}s · score {f['score']} · stock {f['road_stock']}")
  if col==0:ax.set_ylabel('Before Wait lesson' if row==0 else 'After 32k decisions')
fig.suptitle('Exact lowest-seed native replays: better first decisions do not yet prevent repeated building\nH = home, D = destination; colors identify demand groups')
fig.savefig(r/'native-replay-comparison-32768.png',dpi=150);plt.close(fig)

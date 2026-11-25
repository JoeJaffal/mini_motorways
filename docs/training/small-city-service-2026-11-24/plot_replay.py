from pathlib import Path
import argparse,json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();data=json.loads(a.input.read_text());frames=data['frames'];directions=[(0,-1),(-1,-1),(-1,0),(-1,1)]
# Match native enum directions used by the action interface.
import sys
sys.path.insert(0,'training')
# Plotting is system-Python only; do not import Torch-dependent environment.
source=Path('training/environment.py').read_text();import ast
node=ast.parse(source);directions=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DIRS' for t in n.targets))
colors=['#dd4b61','#439cc0','#d5ad30','#60a16d','#a071ba','#dc884d']
selected=[frames[0],min(frames,key=lambda f:abs(f['time']-20)),min(frames,key=lambda f:abs(f['time']-35)),frames[-1]]
fig,axes=plt.subplots(2,2,figsize=(10,9));points=[]
for f in frames:
 for b in f['buildings']:points.extend([(b['cell']['x']-1,b['cell']['y']-1),(b['cell']['x']+b['width']+1,b['cell']['y']+b['height']+1)])
 for cell,bits in f['connections']:points.append((cell%50,cell//50))
xs,ys=zip(*points)
directions=directions[:4]
for ax,f in zip(axes.flat,selected):
 for cell,bits in f['connections']:
  x,y=cell%50,cell//50
  for d,(dx,dy) in enumerate(directions):
   if bits&(1<<d):ax.plot([x+.5,x+dx+.5],[y+.5,y+dy+.5],color='#777',lw=3,zorder=1)
 for b in f['buildings']:
  x,y=b['cell']['x'],b['cell']['y'];ax.add_patch(Rectangle((x,y),b['width'],b['height'],color=colors[b['color']%len(colors)],zorder=2));ax.text(x+b['width']/2,y+b['height']/2,'H' if b['isHouse'] else 'D',color='white',ha='center',va='center',weight='bold',zorder=3)
 for c in f['cars']:ax.scatter(c['x'],c['y'],color=colors[c['color']%len(colors)],s=12,zorder=4)
 ax.set(xlim=(min(xs)-1,max(xs)+1),ylim=(max(ys)+1,min(ys)-1),aspect='equal',title=f"{f['time']:.0f}s · deliveries {f['score']} · roads left {f['road_stock']}")
fig.suptitle(f"Native small city · seed {data['result']['seed']} · H=home, D=destination");fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(a.output,dpi=150);plt.close(fig)

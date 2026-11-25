from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import argparse
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();data=json.loads(Path(a.input).read_text());frames=data['frames'];chosen=[min(frames,key=lambda f:abs(f['time']-t)) for t in [0,60,120,frames[-1]['time']]]
colors=['#d84a5b','#409ac7','#d8ac32','#53955f','#a36dad','#e27f41','#7583b8','#606b75'];dirs=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
fig,axes=plt.subplots(2,2,figsize=(12,9))
for ax,f in zip(axes.flat,chosen):
 for i,kind in enumerate(f['terrain']):
  if kind:ax.add_patch(Rectangle((i%50,i//50),1,1,color='#acd2e4' if kind==1 else '#999f90'))
 for i,bits in enumerate(f['connections']):
  for d in range(4):
   if bits&(1<<d):dx,dy=dirs[d];ax.plot([i%50+.5,i%50+.5+dx],[i//50+.5,i//50+.5+dy],color='#777',lw=3,zorder=2)
 for b in f['buildings']:
  x,y=b['cell']['x'],b['cell']['y'];ax.add_patch(Rectangle((x+.1,y+.1),b['width']-.2,b['height']-.2,color=colors[b['color']%8],zorder=3));ax.text(x,y-.2,('H' if b['isHouse'] else 'D')+str(b['id']),fontsize=8);ent=b['entrance'];ax.scatter([ent['x']+.5],[ent['y']+.5],s=12,c='white',zorder=4)
 for v in f['vehicles']:
  if v.get('visible'):ax.scatter([v['x']+.5],[v['y']+.5],s=12,color=colors[v['color']%8],zorder=5)
 ax.set_xlim(8,32);ax.set_ylim(23,4);ax.set_aspect('equal');ax.set_title(f"{f['time']:.1f}s · score {f['tripsCompleted']} · roads {f['inventory'][0]}")
fig.suptitle('Recorded reference failure · seed 99020130 · H=home, D=destination; white dots=entrances')
fig.tight_layout();fig.savefig(a.output,dpi=140)

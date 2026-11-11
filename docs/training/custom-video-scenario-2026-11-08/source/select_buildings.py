import sys,pathlib,json,numpy as np
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
out=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');raw=json.loads((out/'objects-raw.json').read_text());clock=json.loads((out/'clock-raw.json').read_text());bycell={}
shops=[('yellow',18,8,16,7,3,10,'shop'),('red',12,9,10,8,2,60,'shop'),('yellow',17,12,15,11,2,100,'shop'),('cyan',25,8,24,7,1,150,'shop'),('navy',14,15,12,14,3,180,'shop'),('cyan',28,15,27,14,0,220,'shop'),('red',17,17,16,16,0,270,'shared'),('green',24,18,23,17,1,350,'shop'),('yellow',28,19,27,18,1,360,'shop'),('red',31,19,30,18,0,360,'shop'),('yellow',19,17,16,16,0,600,'join'),('red',12,19,10,18,3,630,'shop'),('cyan',40,8,39,7,0,670,'shop'),('green',40,17,39,16,1,840,'shop')]
footprints={}
for color,cx,cy,x,y,layout,first,kind in shops:
 if kind=='join':continue
 w,h=(4,3) if kind=='shared' else (2,3) if layout<2 else (3,2)
 for yy in range(y,y+h):
  for xx in range(x,x+w):footprints[(xx,yy)]=(color,kind)
for key,obs in raw.items():
 if not key.startswith('house:'):continue
 _,color,xy=key.split(':');x,y=map(int,xy.split(','))
 if (x,y) in footprints:continue
 entry=bycell.setdefault((x,y),dict(observations={},colors={}))
 for v in obs:entry['observations'][v['t']]=v;entry['colors'][color]=entry['colors'].get(color,0)+1
houses=[];final=cv2.imread(str(out/'boards/1000.png'));hsv=cv2.cvtColor(final,cv2.COLOR_BGR2HSV)
for (x,y),entry in bycell.items():
 obs=entry['observations'];first=min(obs);available=sum(int(t)>=first for t in json.loads((out/'cameras.json').read_text()))
 if len(obs)<3 or not(len(obs)/available>.55 or len(obs)>=20):continue
 cx,cy=round((x+.5)*20),round((y+.5)*20);v=hsv[cy-6:cy+2,cx-5:cx+5];v=v[v[:,:,1]>70];color=max(entry['colors'],key=entry['colors'].get)
 if len(v):
  h,s,val=np.median(v,axis=0)
  if 88<h<130:color='navy' if h>=105 else 'cyan'
 houses.append(dict(x=x,y=y,color=color,first=first,key=f'house:{color}:{x},{y}',seen=len(obs)))
(out/'houses-final-selection.json').write_text(json.dumps(sorted(houses,key=lambda v:v['first']),indent=2));(out/'shops-manual.json').write_text(json.dumps(shops,indent=2));print('houses',len(houses));print([(v['first'],v['key']) for v in sorted(houses,key=lambda v:v['first'])])

import json,pathlib,sys,numpy as np
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
root=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');clock=json.loads((root/'clock-raw.json').read_text());houses=json.loads((root/'houses-final-selection.json').read_text());shops=json.loads((root/'shops-manual.json').read_text());changes=json.loads((root/'road-changes-filtered.json').read_text());edgesnew=json.loads((root/'road-changes-v6.json').read_text());terrain=json.loads((root/'terrain.json').read_text());foot={};access={};bounds={}
for color,cx,cy,x,y,layout,first,kind in shops:
 if kind=='join':continue
 w,h=(4,3) if kind=='shared' else (2,3) if layout<2 else (3,2)
 for yy in range(y,y+h):
  for xx in range(x,x+w):foot[xx,yy]=True
 if kind=='shared':access[x,y+2]=(x-1,y+2);access[x+3,y+2]=(x+4,y+2)
 elif layout==0:access[x,y+2]=(x-1,y+2)
 elif layout==1:access[x+1,y+2]=(x+2,y+2)
 elif layout==2:access[x,y]=(x,y-1)
 else:access[x,y+1]=(x,y+2)
houses=[v for v in houses if (v['x'],v['y']) not in foot]
if not any(v['x']==30 and v['y']==8 for v in houses):houses.append(dict(x=30,y=8,color='green',first=890,key='house:green:30,8'))
colors={'yellow':0,'red':1,'cyan':2,'navy':3,'green':4}
def color_mask(im,color):
 hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);h,s,v=cv2.split(hsv)
 if color=='yellow':return (h>=12)&(h<=32)&(s>70)&(v>100)
 if color=='red':return ((h<7)|(h>163))&(s>100)&(v>80)
 if color=='cyan':return (h>=90)&(h<108)&(s>65)&(v>110)
 if color=='navy':return (h>=105)&(h<130)&(s>65)&(v>50)&(v<195)
 return (h>=55)&(h<86)&(s>65)&(v>70)
images={}
def board(t):
 if t not in images:images[t]=cv2.imread(str(root/'boards'/f'{t:04}.png'))
 return images[t]
def onset(color,wx,wy,first):
 if first==10:return 7
 seq=[]
 for t in range(max(7,first-12),min(1007,first+5)):
  if clock[t]['menu']:seq.append(False);continue
  im=board(t);x,y=round(wx*20),round(wy*20);mask=color_mask(im[y-7:y+7,x-7:x+7],color);seq.append(mask.mean()>.3)
 for i in range(len(seq)-1):
  if seq[i] and seq[i+1]:return max(7,first-12)+i
 return first
raw=np.cumsum([r['speed'] for r in clock]);anchors=[86,160,232,307,416,537,712,803,877];anchorraw=[raw[t] for t in anchors]
def game_time(video):
 t=min(1007,max(0,int(video)));r=float(raw[t])
 if t<20:return max(0.,t-10.)
 for i,v in enumerate(anchors):
  if t<=v:
   if i==0:return max(0,r+140-anchorraw[0])
   return i*140+(r-anchorraw[i-1])*140/(anchorraw[i]-anchorraw[i-1])
 return 1260+r-anchorraw[-1]
events=[];metadata=[]
def add(video,kind,**kwargs):events.append(dict(at=round(game_time(video)/.05)*.05,videoTime=video,kind=kind,**kwargs))
for v in houses:
 x,y=v['x'],v['y'];t=onset(v['color'],x+.5,y+.4,v['first']);v['birth']=t
 im=board(min(1007,t+6));white=(im.min(axis=2)>245).astype(float);scores=[]
 for dx,dy in [(1,0),(0,1),(-1,0),(0,-1)]:
  samples=[]
  for distance in [.5,.65,.8]:
   px,py=round((x+.5+dx*distance)*20),round((y+.5+dy*distance)*20);samples.append(white[py-1:py+2,px-1:px+2].mean())
  scores.append(float(np.mean(samples)))
 direction=[0,2,4,6][int(np.argmax(scores))];v['direction']=direction
 add(0 if v['first']==10 else t,'house',id=v['key'],x=x,y=y,color=colors[v['color']],direction=direction)
 metadata.append(dict(kind='house',id=v['key'],video=t,grid=[x,y],direction=direction,confidence='pixel detection; approx1second plus clock calibration'))
for color,cx,cy,x,y,layout,first,kind in shops:
 t=onset(color,cx,cy,first);id=f'shop:{color}:{cx},{cy}';data=dict(id=id,x=x,y=y,color=colors[color],layout=layout)
 if kind=='join':data['target']='shop:red:17,17'
 add(0 if first==10 else t,kind,**data);metadata.append(dict(kind=kind,id=id,video=t,origin=[x,y],layout=layout,confidence='manually checked footprint; onset sampled at1second'))
# Match the observed weekly package choices, not merely mouse hover.
offers=[([(3,2,20),(4,1,20)],1), ([(0,30,0),(3,2,20)],1), ([(2,1,10),(1,1,20)],0), ([(1,1,20),(0,30,0)],0), ([(2,1,10),(1,1,20)],0), ([(0,30,0),(2,1,10)],1), ([(1,1,20),(4,1,20)],0), ([(3,2,20),(4,1,20)],0), ([(2,1,10),(0,30,0)],0)]
for week,(video,(choices,selected)) in enumerate(zip(anchors,offers),1):
 at=week*140.;events.append(dict(at=at,videoTime=video,kind='offer',offers=[dict(type=typ,amount=amount,roads=roads) for typ,amount,roads in choices]));events.append(dict(at=at,videoTime=video+.1,kind='choose',choice=selected))
# Endpoint identities tracked between successive stable marker sets.
add(284,'motorway',id='m1',x=15,y=6,toX=14,toY=18)
add(435,'motorway',id='m2',x=13,y=10,toX=26,toY=17)
add(511,'editMotorway',target='m1',x=15,y=6,toX=29,toY=20)
add(667,'editMotorway',target='m2',x=13,y=10,toX=25,toY=15)
add(686,'editMotorway',target='m1',x=15,y=6,toX=38,toY=9)
add(775,'motorway',id='m3',x=19,y=6,toX=15,toY=20)
add(901,'editMotorway',target='m3',x=19,y=6,toX=15,toY=18)
add(1000,'motorway',id='m4',x=20,y=18,toX=29,toY=20)
add(275,'build',tool='TrafficLight',x=20,y=13);add(480,'build',tool='TrafficLight',x=25,y=14)
add(750,'build',tool='Roundabout',x=19,y=9)
for color,cx,cy,start in [('navy',14,15,730),('yellow',19,17,780),('green',24,18,850)]:
 times=[]
 for t in range(start,min(start+60,1007)):
  im=board(t);mask=color_mask(im,color);vals=[]
  for dx,dy in [(-14,-14),(-14,14),(14,-14),(14,14)]:
   px,py=cx*20+dx,cy*20+dy;vals.append(mask[py-1:py+2,px-1:px+2].mean())
  if np.mean(vals)<.3:times.append(t)
 chosen=next((a for a,b in zip(times,times[1:]) if b==a+1),start+10);add(chosen,'circle',target=f'shop:{color}:{cx},{cy}')
# Only observed buildable edges; no guessed bridges along pale coastlines.
def valid(edge):
 a,b=tuple(edge[:2]),tuple(edge[2:]);water=[v for v in [a,b] if terrain[v[1]][v[0]]=='~']
 if water and (a[1]!=b[1] or any(v not in [(22,13),(33,22)] for v in water)):return False
 if any(terrain[v[1]][v[0]] in '#^' for v in [a,b]):return False
 if (a in foot or b in foot) and not(access.get(a)==b or access.get(b)==a):return False
 if any(v in {(19,9),(19,8),(18,9),(19,10),(20,9)} for v in [a,b]):return True
 return True
house_by_cell={(v['x'],v['y']):v for v in houses}
# Manually verified native left entrance stub, visible from spawn at video143.
edgesnew.append(dict(video=143,kind='add',edge=[23,9,24,9],score=1.0))
for change in edgesnew:
 if not valid(change['edge']):continue
 video=change['video'];a=tuple(change['edge'][:2]);b=tuple(change['edge'][2:]);touch=[v for v in [a,b] if v in house_by_cell]
 if any(video<house_by_cell[v]['birth'] for v in touch):continue
 if video>=748 and any(v in {(19,9),(19,8),(18,9),(19,10),(20,9)} for v in [a,b]):continue
 if touch and b in house_by_cell:a,b=b,a
 add(video,'draw' if change['kind']=='add' else 'erase',x=a[0],y=a[1],toX=b[0],toY=b[1])
events.sort(key=lambda e:(e['at'],e['videoTime'],0 if e['kind'] in ['house','shop','shared','join'] else 1))
# Normalize pixel disappearances caused by a driveway rotation: DrawRoad already removes the previous stub.
active=set();automatic=set();normalized=[];normalization=[]
for e in events:
 if e['kind'] in ['draw','erase']:
  a=(e['x'],e['y']);b=(e['toX'],e['toY']);edge=tuple(sorted((a,b)))
  if e['kind']=='draw':
   for house in [v for v in (a,b) if v in house_by_cell]:
    for old in list(active):
     if house in old and old!=edge:active.remove(old);automatic.add(old)
   active.add(edge);automatic.discard(edge)
  else:
   if edge not in active and edge in automatic:
    normalization.append(dict(event=e,reason='Driveway rotation already removed this connection'));automatic.remove(edge);continue
   active.discard(edge)
 normalized.append(e)
events=normalized
(root/'normalization-v1.json').write_text(json.dumps(normalization,indent=2))
# An explicit deterministic carrier seed, derived from the video's hash, never fit to its score.
seed=int('c9762eb1',16);seed=seed if seed<2**31 else seed-2**32
scenario=dict(schemaVersion=1,id='video-c9762eb1-la-reconstruction-v1',city='LosAngeles',seed=seed,referenceScore=835,duration=game_time(1007)+.6,source='User video reconstruction',sourceSha256='c9762eb1d8c474c328b01f59a4a0ca744a0c8a06e2794e2dafe285712b1d4629',startingInventory=[25,1,0,0,0,0],paletteRgb=[0xffc568,0xf24c5c,0x6fc5e0,0x4f689e,0x69bb89],bounds=[0,0,50,30],uncertainties='Video reconstruction, not recovered original RNG. Grid registration, ~1s video sampling, calibrated pauses/speed, and occluded edits require validation. Carrier seed is hash-derived; demand phase unknown.',events=events)
(root/'scenario-v1.json').write_text(json.dumps(scenario,indent=2));(root/'building-annotations-v1.json').write_text(json.dumps(metadata,indent=2));(root/'game-clock-calibration.json').write_text(json.dumps(dict(anchors=list(zip(anchors,[int(v) for v in anchorraw],[140*i for i in range(1,10)])),end=game_time(1007),events=sum(e['kind'] in ['draw','erase'] for e in events)),indent=2));print(dict(seed=seed,houses=len(houses),shops=len(shops),events=len(events),duration=scenario['duration']));print('early',[(e['at'],e['kind'],e.get('id')) for e in events[:14]])

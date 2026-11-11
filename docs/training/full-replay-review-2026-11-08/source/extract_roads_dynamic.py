import sys,pathlib,json,numpy as np,time
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
out=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');clock=json.loads((out/'clock-raw.json').read_text());shops=json.loads((out/'shops-manual.json').read_text());houses=json.loads((out/'houses-final-selection.json').read_text());sink=pathlib.Path('tmp/full-replay-review-2026-11-08');cameras=json.loads((sink/'cameras-every-second.json').read_text());edges=[]
for y in range(30):
 for x in range(50):
  for dx,dy in [(1,0),(0,1),(1,1),(-1,1)]:
   if 0<=x+dx<50 and y+dy<30:edges.append((x,y,x+dx,y+dy))
e=np.array(edges);d=e[:,2:]-e[:,:2];u=np.linspace(.3,.7,7);points=(e[:,:2,None]+.5+d[:,:,None]*u[None,None,:])*20;px=np.rint(points[:,0,:]).astype(int);py=np.rint(points[:,1,:]).astype(int);state=np.zeros(len(e),bool);positive=np.zeros(len(e),int);negative=np.zeros(len(e),int);observations=[];changes=[];markers={};start=time.perf_counter()
footprint={};access={}
for color,cx,cy,x,y,layout,first,kind in shops:
 if kind=='join':continue
 w,h=(4,3) if kind=='shared' else (2,3) if layout<2 else (3,2)
 for yy in range(y,y+h):
  for xx in range(x,x+w):footprint[xx,yy]=first
 if kind=='shared':access[x,y+2]=(x-1,y+2);access[x+3,y+2]=(x+4,y+2)
 elif layout==0:access[x,y+2]=(x-1,y+2)
 elif layout==1:access[x+1,y+2]=(x+2,y+2)
 elif layout==2:access[x,y]=(x,y-1)
 else:access[x,y+1]=(x,y+2)
# Reject white carpark circulation as public road edges, while retaining the actual entrances.
allowed=np.array([not(any((int(v[0]),int(v[1])) in footprint for v in [a[:2],a[2:]]) and not(access.get(tuple(a[:2]))==tuple(a[2:]) or access.get(tuple(a[2:]))==tuple(a[:2]))) for a in e])
terrain=json.loads((out/'terrain.json').read_text());water=np.zeros((600,1000),np.uint8)
for yy,line in enumerate(terrain):
 for xx,ch in enumerate(line):
  if ch=='~':water[yy*20:(yy+1)*20,xx*20:(xx+1)*20]=1
coast=cv2.dilate(water,np.ones((31,31),np.uint8))>0
for row in clock:
 t=row['video'];im=cv2.imread(str(sink/'boards'/f'{t:04}.png'))
 if t<14 or row['menu'] and t>80:continue
 hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);white=cv2.dilate(((im.min(axis=2)>248)|((im.min(axis=2)>205)&(im.max(axis=2)-im.min(axis=2)<13)&~coast)).astype(np.uint8),np.ones((5,5),np.uint8))>0;p=im[py,px];h=hsv[py,px];scores=white[py,px].mean(axis=1)
 unknown=((h[:,:,1]>65)&(h[:,:,2]>70)).mean(axis=1)>.22
 outside=np.any((p[:,:,0]==128)&(p[:,:,1]==128)&(p[:,:,2]==128),axis=1)
 cam=cameras[str(t)]['camera'];sx=px/20*cam['scale']+cam['tx'];sy=py/20*cam['scale']+cam['ty'];outside|=np.any((sy>1080)|(sx>1780)&(sy<310)|(sx<100)&(sy<200),axis=1)
 activeparcel=np.array([any(tuple(p) in footprint and t>=footprint[tuple(p)] for p in (edge[:2],edge[2:])) for edge in edges]);currentAllowed=~activeparcel|allowed
 on=(scores>.55)&currentAllowed&~outside;off=((scores<.18)|~currentAllowed)&~unknown&~outside
 positive=np.where(on,positive+1,0);negative=np.where(off,negative+1,0)
 additions=(positive>=2)&~state;removals=(negative>=3)&state
 for i in np.flatnonzero(additions|removals):changes.append(dict(video=max(14,t-(1 if additions[i] else 2)),kind='add' if additions[i] else 'remove',edge=e[i].tolist(),score=float(scores[i])))
 state[additions]=True;state[removals]=False
 if t%10==0:observations.append(dict(video=t,edges=e[state].tolist(),cost=sum(1 for a in e[state] if tuple(a[:2]) not in access and tuple(a[2:]) not in access)))
 if t%120==0:print(t,'edges',int(state.sum()),'wall',round(time.perf_counter()-start,1),flush=True)
(sink/'road-changes-v7-dynamic.json').write_text(json.dumps(changes,indent=2));(sink/'road-observations-v7-dynamic.json').write_text(json.dumps(observations,indent=2));print('changes',len(changes));print('costs',[(v['video'],v['cost']) for v in observations if v['video'] in [20,30,80,90,170,240,320,430,550,720,810,890,1000]])

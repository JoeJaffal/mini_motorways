import sys,pathlib,json,numpy as np,time
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
out=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');clock=json.loads((out/'clock-raw.json').read_text());shops=json.loads((out/'shops-manual.json').read_text());houses=json.loads((out/'houses-final-selection.json').read_text());edges=[]
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
for row in clock:
 t=row['video'];im=cv2.imread(str(out/'boards'/f'{t:04}.png'))
 if t<14 or row['menu'] and t>80:continue
 hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);white=cv2.dilate(((im.min(axis=2)>205)&(im.max(axis=2)-im.min(axis=2)<13)).astype(np.uint8),np.ones((5,5),np.uint8))>0;p=im[py,px];h=hsv[py,px];scores=white[py,px].mean(axis=1)
 unknown=((h[:,:,1]>65)&(h[:,:,2]>70)).mean(axis=1)>.22
 outside=np.any((p[:,:,0]==128)&(p[:,:,1]==128)&(p[:,:,2]==128),axis=1)
 on=(scores>.55)&allowed;off=(scores<.18)&~unknown&~outside
 positive=np.where(on,positive+1,0);negative=np.where(off,negative+1,0)
 additions=(positive>=2)&~state;removals=(negative>=3)&state
 for i in np.flatnonzero(additions|removals):changes.append(dict(video=max(14,t-(1 if additions[i] else 2)),kind='add' if additions[i] else 'remove',edge=e[i].tolist(),score=float(scores[i])))
 state[additions]=True;state[removals]=False
 if t%10==0:observations.append(dict(video=t,edges=e[state].tolist(),cost=sum(1 for a in e[state] if tuple(a[:2]) not in access and tuple(a[2:]) not in access)))
 if t%120==0:print(t,'edges',int(state.sum()),'wall',round(time.perf_counter()-start,1),flush=True)
(out/'road-changes-v5.json').write_text(json.dumps(changes,indent=2));(out/'road-observations-v5.json').write_text(json.dumps(observations,indent=2));print('changes',len(changes));print('costs',[(v['video'],v['cost']) for v in observations if v['video'] in [20,30,80,90,170,240,320,430,550,720,810,890,1000]])

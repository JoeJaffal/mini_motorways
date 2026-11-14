import sys,pathlib,json,numpy as np
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
out=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');cams=json.loads((out/'cameras.json').read_text());seen={};counts={}
ranges={'yellow':[(15,60,140,30,255,255)],'red':[(0,130,130,5,255,255),(174,130,130,179,255,255)],'cyan':[(90,65,110,108,255,255)],'navy':[(109,65,50,128,255,200)],'green':[(55,75,70,85,255,240)]}
for ts,cam in cams.items():
 t=int(ts);im=cv2.imread(str(out/f'frame-{t:04}.jpg'));hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);s=cam['scale'];objects=[]
 for color,rs in ranges.items():
  mask=np.zeros(im.shape[:2],np.uint8)
  for h,ss,v,hh,sss,vv in rs:mask|=cv2.inRange(hsv,np.array([h,ss,v]),np.array([hh,sss,vv]))
  mask[:160,1580:]=0;mask[1050:]=0
  mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
  n,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
  for i in range(1,n):
   x,y,w,h,area=stats[i];cx,cy=centers[i];wx=(cx-cam['tx'])/s;wy=(cy-cam['ty'])/s
   if not(0<wx<50 and 0<wy<30) or area<.15*s*s:continue
   if max(w,h)<1.05*s:kind='house';gx,gy=round(wx-.5),round(wy-.5)
   elif w>1.2*s and h>1.1*s:kind='shop';gx,gy=round(wx),round(wy)
   else:continue
   key=f'{kind}:{color}:{gx},{gy}'
   seen.setdefault(key,[]).append(dict(t=t,cx=float(cx),cy=float(cy),wx=wx,wy=wy,w=int(w),h=int(h),area=int(area)))
objects=[]
for key,obs in sorted(seen.items()):
 if len(obs)<3:continue
 obj=dict(key=key,first=min(v['t'] for v in obs),last=max(v['t'] for v in obs),seen=len(obs));objects.append(obj)
(out/'objects-raw.json').write_text(json.dumps(seen,indent=2));(out/'objects.json').write_text(json.dumps(objects,indent=2));print(json.dumps(sorted(objects,key=lambda v:v['first']),indent=1))

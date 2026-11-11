import sys,pathlib,json,numpy as np,time
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2,av
out=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');boards=out/'boards';boards.mkdir(exist_ok=True);cams={int(k):v for k,v in json.loads((out/'cameras.json').read_text()).items()};keys=sorted(cams)
for cam in cams.values():
 old=cam['scale'];cam['scale']*=44.85/45;cam['tx']+=(.95)*old/45;cam['ty']+=(1.05)*old/45
base=cv2.imread(str(out/'frame-1000.jpg'));pm=np.max(base[155:181,1854:1892],axis=2)<100;fm=np.max(base[212:236,1854:1892],axis=2)<100
names=['MON','TUE','WED','THU','FRI','SAT','SUN'];templates=[]
for t in [20,30,40,50,60,70,80]:
 im=cv2.imread(str(out/f'frame-{t:04}.jpg'));templates.append(cv2.cvtColor(im[32:72,1770:1840],cv2.COLOR_BGR2GRAY)<115)
c=av.open('C:/Users/moham/Downloads/screen-capture (2).webm');nextt=0;rows=[];start=time.perf_counter()
for f in c.decode(video=0):
 t=float(f.time or 0)
 if t<nextt:continue
 at=nextt;nextt+=1
 if at>1007:break
 im=f.to_ndarray(format='bgr24');lo=max([k for k in keys if k<=at] or [keys[0]]);hi=min([k for k in keys if k>=at] or [keys[-1]]);u=0 if hi==lo else (at-lo)/(hi-lo)
 cam={k:cams[lo][k]*(1-u)+cams[hi][k]*u for k in ['scale','tx','ty']};s=cam['scale'];mat=np.array([[20/s,0,-cam['tx']*20/s],[0,20/s,-cam['ty']*20/s]])
 board=cv2.warpAffine(im,mat,(1000,600),borderValue=(128,128,128));cv2.imwrite(str(boards/f'{at:04}.png'),board)
 patch=im[34:69,1856:1890];yy,xx=np.indices(patch.shape[:2]);disk=((xx-17)**2+(yy-17)**2<15**2);color=np.median(patch[disk],axis=0);play=np.median(im[155:181,1854:1892][pm],axis=0);fast=np.median(im[212:236,1854:1892][fm],axis=0)
 paused=color[2]-color[1]>45;menu=min(play[2],fast[2])>155;speed=0 if paused or menu or at<12 else 1 if play[2]>fast[2] else 2
 daymask=cv2.cvtColor(im[32:72,1770:1840],cv2.COLOR_BGR2GRAY)<115;cost=[np.mean(daymask!=tpl) for tpl in templates];day=int(np.argmin(cost));day=day if min(cost)<.14 and not menu else None
 rows.append(dict(video=at,actual=t,speed=speed,paused=bool(paused),menu=bool(menu),day=names[day] if day is not None else None,dayError=min(cost),camera=cam))
 if at%120==0:print('decoded',at,'wall',round(time.perf_counter()-start,1),flush=True)
(out/'clock-raw.json').write_text(json.dumps(rows,indent=2));print('done',len(rows),'wall',time.perf_counter()-start)

import sys,pathlib,json,numpy as np,time
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2,av
src=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');out=pathlib.Path('tmp/full-replay-review-2026-11-08');boards=out/'boards';boards.mkdir(exist_ok=True);clock=json.loads((src/'clock-raw.json').read_text());anchors={int(k):v for k,v in json.loads((src/'cameras.json').read_text()).items()};keys=sorted(anchors)
for cam in anchors.values():
 old=cam['scale'];cam['scale']*=44.85/45;cam['tx']+=.95*old/45;cam['ty']+=1.05*old/45
orb=cv2.ORB_create(nfeatures=2500);matcher=cv2.BFMatcher(cv2.NORM_HAMMING);cache={};rows={};start=time.perf_counter()
def features(im):
 small=cv2.resize(im,(960,600));mask=np.full(small.shape[:2],255,np.uint8);mask[:110,780:]=0;mask[530:]=0;return orb.detectAndCompute(cv2.cvtColor(small,cv2.COLOR_BGR2GRAY),mask)
def reference(t):
 if t not in cache:cache[t]=features(cv2.imread(str(src/f'frame-{t:04}.jpg')))
 return cache[t]
c=av.open('C:/Users/moham/Downloads/screen-capture (2).webm');nextt=0
for f in c.decode(video=0):
 timecode=float(f.time or 0)
 if timecode<nextt:continue
 t=nextt;nextt+=1
 if t>1007:break
 if time.perf_counter()-start>300:raise RuntimeError('Fixed300second registration wall cap')
 im=f.to_ndarray(format='bgr24');cam=clock[t]['camera'];quality={'status':'fallback'}
 if t>=10 and not clock[t]['menu']:
  k1,d1=features(im);best=None
  for ref in sorted(keys,key=lambda x:abs(x-t))[:2]:
   k2,d2=reference(ref)
   if d1 is None or d2 is None:continue
   pairs=matcher.knnMatch(d1,d2,k=2);good=[a for a,b in pairs if a.distance<.68*b.distance]
   if len(good)<20:continue
   a=np.array([k1[m.queryIdx].pt for m in good]);b=np.array([k2[m.trainIdx].pt for m in good]);mat,valid=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=1.3)
   if mat is None:continue
   mask=valid.ravel().astype(bool);a=a[mask];b=b[mask];ma=a.mean(axis=0);mb=b.mean(axis=0);scale=float(np.sum((a-ma)*(b-mb))/np.sum((a-ma)**2));delta=mb-scale*ma;error=float(np.median(np.linalg.norm(a*scale+delta-b,axis=1)))
   if len(a)<20 or not(.75<scale<1.25) or error>1.5:continue
   old=anchors[ref];candidate=dict(scale=old['scale']/scale,tx=(old['tx']-delta[0]*2)/scale,ty=(old['ty']-delta[1]*2)/scale)
   choice=(len(a),-error,candidate,dict(status='measured',anchor=ref,inliers=len(a),pixelError=error*2))
   if best is None or choice[:2]>best[:2]:best=choice
  if best is not None:cam=best[2];quality=best[3]
 s=cam['scale'];mat=np.array([[20/s,0,-cam['tx']*20/s],[0,20/s,-cam['ty']*20/s]]);board=cv2.warpAffine(im,mat,(1000,600),borderValue=(128,128,128));cv2.imwrite(str(boards/f'{t:04}.png'),board);rows[t]=dict(camera=cam,quality=quality)
 if t%100==0:print(t,quality,'wall',round(time.perf_counter()-start,1),flush=True)
(out/'cameras-every-second.json').write_text(json.dumps(rows,indent=2));print('done',len(rows),'measured',sum(v['quality']['status']=='measured' for v in rows.values()),'wall',time.perf_counter()-start)

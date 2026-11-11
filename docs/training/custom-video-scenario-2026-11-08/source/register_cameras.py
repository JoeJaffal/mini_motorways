import sys,pathlib,json,numpy as np
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
out=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');orb=cv2.ORB_create(nfeatures=5000);matcher=cv2.BFMatcher(cv2.NORM_HAMMING);cache={};cams={1000:dict(scale=45.,tx=-185.5,ty=-101.5)};fail=[]
def key(t):
 if t not in cache:
  im=cv2.imread(str(out/f'frame-{t:04}.jpg'));mask=np.full(im.shape[:2],255,np.uint8);mask[:160,1580:]=0;mask[1050:]=0
  cache[t]=orb.detectAndCompute(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY),mask)
 return cache[t]
forward=1000
for t in range(990,0,-10):
 if t==160:continue
 k1,d1=key(t);k2,d2=key(forward);pairs=matcher.knnMatch(d1,d2,k=2);good=[a for a,b in pairs if a.distance<.7*b.distance]
 p1=np.array([k1[m.queryIdx].pt for m in good]);p2=np.array([k2[m.trainIdx].pt for m in good]);mat,mask=cv2.estimateAffinePartial2D(p1,p2,method=cv2.RANSAC,ransacReprojThreshold=2.5)
 if mat is None:fail.append((t,'none'));continue
 valid=mask.ravel().astype(bool);a=p1[valid];b=p2[valid];ma=a.mean(axis=0);mb=b.mean(axis=0);scale=float(np.sum((a-ma)*(b-mb))/np.sum((a-ma)**2));delta=mb-scale*ma;prior=cams[forward]
 if valid.sum()<25 or scale<.5 or scale>2:
  fail.append((t,int(valid.sum())));continue
 cams[t]=dict(scale=prior['scale']/scale,tx=(prior['tx']-delta[0])/scale,ty=(prior['ty']-delta[1])/scale,inliers=int(valid.sum()),error=float(np.median(np.linalg.norm(a*scale+delta-b,axis=1))))
 forward=t
(out/'cameras.json').write_text(json.dumps(cams,indent=2));print('weak',fail);print('first',cams[10])
for t in [10,20,80,160,400,700,1000]:
 cam=cams.get(t,cams.get(t+10));s,tx,ty=cam['scale'],cam['tx'],cam['ty'];im=cv2.imread(str(out/f'frame-{t:04}.jpg'))
 for y in range(30):
  for x in range(50):
   xx,yy=round((x+.5)*s+tx),round((y+.5)*s+ty)
   if 0<xx<1920 and 0<yy<1200:cv2.putText(im,f'{x},{y}',(xx-12,yy+4),cv2.FONT_HERSHEY_SIMPLEX,.35,(20,20,20),1)
 cv2.imwrite(str(out/f'grid-{t}.jpg'),im)

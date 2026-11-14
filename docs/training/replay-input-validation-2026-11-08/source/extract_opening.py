import pathlib,sys,json
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import av,cv2,numpy as np
r=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');out=pathlib.Path('tmp/replay-validation-2026-11-08');folder=out/'samples';folder.mkdir(exist_ok=True)
cams={int(k):v for k,v in json.loads((r/'cameras.json').read_text()).items()};keys=sorted(cams)
for cam in cams.values():
 old=cam['scale'];cam['scale']*=44.85/45;cam['tx']+=.95*old/45;cam['ty']+=1.05*old/45
c=av.open('C:/Users/moham/Downloads/screen-capture (2).webm');nextt=8.;rows=[]
points=[(16,9),(16,10),(15,10),(14,10),(13,10),(13,11),(11,11),(11,10),(12,10),(19,10),(19,9),(19,8),(18,11),(10,7)]
for f in c.decode(video=0):
 t=float(f.time or 0)
 if t<nextt:continue
 at=round(nextt,1);nextt+=.1
 if at>60:break
 if 25<at<54:continue
 im=f.to_ndarray(format='bgr24');lo=max([k for k in keys if k<=at] or [keys[0]]);hi=min([k for k in keys if k>=at] or [keys[-1]]);u=0 if hi==lo else (at-lo)/(hi-lo);cam={k:cams[lo][k]*(1-u)+cams[hi][k]*u for k in ['scale','tx','ty']};s=cam['scale'];mat=np.array([[20/s,0,-cam['tx']*20/s],[0,20/s,-cam['ty']*20/s]]);board=cv2.warpAffine(im,mat,(1000,600),borderValue=(128,128,128));scores=[]
 for x,y in points:
  px,py=round((x+.5)*20),round((y+.5)*20);p=board[py-1:py+2,px-1:px+2];scores.append(float(((p.min(axis=2)>205)&(p.max(axis=2)-p.min(axis=2)<15)).mean()))
 rows.append(dict(video=at,actual=t,scores=scores))
 cv2.imwrite(str(folder/f'board-{at:05.1f}.png'),board[100:280,180:460]);cv2.imwrite(str(folder/f'inventory-{at:05.1f}.png'),im[1080:1190,700:1150])
(out/'pixel-observations.json').write_text(json.dumps(dict(points=points,rows=rows),indent=2));print('samples',len(rows))

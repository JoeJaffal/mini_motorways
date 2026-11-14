import sys,pathlib,json,numpy as np,time
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
out=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');shops=json.loads((out/'shops-manual.json').read_text());exclude={(20,13),(25,14)}
for color,cx,cy,x,y,layout,first,kind in shops:
 if kind=='join':continue
 w,h=(4,3) if kind=='shared' else (2,3) if layout<2 else (3,2)
 for yy in range(y,y+h):
  for xx in range(x,x+w):exclude.add((xx,yy))
kernels=[]
for r in [3,4]:
 k=np.zeros((2*r+1,2*r+1),np.float32);cv2.circle(k,(r,r),r,1,1);kernels.append(k/k.sum())
result={}
for t in range(270,1008):
 im=cv2.imread(str(out/'boards'/f'{t:04}.png'));gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY);dark=(gray<115).astype(np.float32);score=np.maximum(*[cv2.filter2D(dark,-1,k) for k in kernels]);score[gray<185]=0;score=cv2.dilate(score,np.ones((9,9),np.uint8));found=[]
 for y in range(5,24):
  for x in range(5,47):
   if (x,y) in exclude or t>=740 and (x,y)==(19,9):continue
   val=score[y*20+10,x*20+10]
   if val>.74:found.append([x,y,round(float(val),3)])
 result[t]=found
(out/'endpoints-v2.json').write_text(json.dumps(result))
for t in [290,300,400,430,480,510,550,680,710,740,800,890,970,1000]:print(t,result.get(t))

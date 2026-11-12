import numpy as np, glob, json
from PIL import Image
from detect import names
import os
fs=sorted(glob.glob('feat/*.npz'));N=max(int(os.path.basename(f)[:4]) for f in fs)+1
CF=np.zeros((N,30,50,5),np.float32);VS=np.zeros((N,30,50),bool)
for f in fs:
    i=int(os.path.basename(f)[:4]);z=np.load(f);CF[i]=z['cf'];VS[i]=z['vis']
for _b in json.load(open('bad_frames.json')):
    VS[_b]=False
LOTS={(10,9):(3,2),(11,12):(3,2),(15,12):(3,2),(12,15):(3,2),(16,17):(3,2),(28,9):(4,3),(27,15):(3,2),(27,18):(3,2),(38,15):(2,3)}
inlot=np.zeros((30,50),bool)
for (x,y),(w,h) in LOTS.items():inlot[y:y+h,x:x+w]=True
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
def game(v):
    for end,c in W:
        if v<=end+2:return v+c
pres=(CF.max(-1)>0.25)
out=[]
for y in range(30):
    for x in range(50):
        if inlot[y,x]:continue
        p=pres[:,y,x]&VS[:,y,x]
        for t in range(N-6):
            if p[t] and p[t:t+6].sum()>=5:
                col=int(np.bincount(CF[t:t+6,y,x].argmax(-1),minlength=5).argmax())
                # must stay present to the end most of the time
                tail=pres[t:,y,x][VS[t:,y,x]]
                if tail.mean()<0.6:break
                out.append(dict(x=x,y=y,color=col,name=names[col],t=t,video=t+0.5,game=round(game(t+0.5),2)))
                break
out.sort(key=lambda h:h['t'])
json.dump(out,open('houses_raw.json','w'),indent=0)
print(len(out));print([(h['x'],h['y'],h['name'],h['video']) for h in out])

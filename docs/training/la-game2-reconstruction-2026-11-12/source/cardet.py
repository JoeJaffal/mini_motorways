import numpy as np, json, sys
from PIL import Image
from scipy import ndimage
T=32
houses=json.load(open('houses_raw.json'))
hroof=np.zeros((960,1600),bool)
for h in houses:  # roof square (upper 70% of tile) only; driveway side stays visible
    hroof[h['y']*T+3:h['y']*T+26,h['x']*T+4:h['x']*T+28]=True
col=np.array(json.loads(sys.argv[3])) if len(sys.argv)>3 else np.array([211,15,125])
bad=set(json.load(open('bad_frames.json')))
out={}
for t in range(int(sys.argv[1]),int(sys.argv[2])):
    if t in bad:continue
    a=np.asarray(Image.open(f'boards/{t:04d}.png').convert('RGB'),float)
    d=np.sqrt(((a-col)**2).sum(-1))
    m=(d<60)&~hroof
    lab,k=ndimage.label(m)
    if k==0:out[t]=[];continue
    idx=range(1,k+1);sz=ndimage.sum(m,lab,idx);cm=ndimage.center_of_mass(m,lab,idx)
    out[t]=[(round(c[1]/T,2),round(c[0]/T,2),int(s)) for c,s in zip(cm,sz) if 6<=s<=70]
json.dump(out,open(sys.argv[4] if len(sys.argv)>4 else 'cars_mag.json','w'))
print('frames',len(out),'mean dets',round(np.mean([len(v) for v in out.values()]),1))

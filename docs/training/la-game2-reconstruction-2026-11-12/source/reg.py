import numpy as np, re, math
from PIL import Image
src=open(r'C:/Projects/490 - Project/mm-fidelity/simulation/Assets/Simulation/CityCatalog.cs',encoding='utf-8').read()
terr=re.search(r'Name="LosAngeles",Terrain=new string\[\]\{(.*?)\}',src).group(1)
rows=re.findall(r'"([^"]*)"',terr);W=np.array([[c=='~' for c in r] for r in rows],dtype=float)  # 30x50
TOP=35
def herm(t):
    keys=[(2.0,8.0,0.0,0.0),(25.0,15.5,0.374947190284729,0.374947190284729),(54.0,21.0,0.0,0.0)]
    if t<=keys[0][0]:return keys[0][1]
    if t>=keys[-1][0]:return keys[-1][1]
    for (t0,v0,i0,o0),(t1,v1,i1,o1) in zip(keys,keys[1:]):
        if t0<=t<=t1:
            dt=t1-t0;u=(t-t0)/dt;h00=2*u**3-3*u**2+1;h10=u**3-2*u**2+u;h01=-2*u**3+3*u**2;h11=u**3-u**2
            return h00*v0+h10*o0*dt+h01*v1+h11*i1*dt
def frame_mask(im,ds):
    a=np.asarray(im.convert('RGB'),dtype=float)[TOP:]
    water=(a[...,2]-a[...,0]>40)&(a[...,1]>195)
    valid=np.ones(water.shape,bool)
    valid[:110,1300:]=False   # score and clock
    valid[790:,600:1000]=False # toolbar
    valid[380:560,1520:]=False # tools
    f=np.where(water,1.0,-1.0)*valid
    h,w=f.shape;f=f[:h//ds*ds,:w//ds*ds].reshape(h//ds,ds,w//ds,ds).mean(axis=(1,3))
    return f
def register(im,s_list,ds=4):
    f=frame_mask(im,ds);fh,fw=f.shape;best=None
    for s in s_list:
        sp=s/ds;H=int(round(30*sp));Wd=int(round(50*sp))
        yy=(np.arange(H)/sp).astype(int).clip(0,29);xx=(np.arange(Wd)/sp).astype(int).clip(0,49)
        T=(2*W[yy][:,xx]-1)
        # correlate: offset (oy,ox) = position of map origin in frame coords (can be negative)
        PH=H+fh;PW=Wd+fw
        Fa=np.fft.rfft2(T,(PH,PW));Fb=np.fft.rfft2(f[::-1,::-1],(PH,PW))
        c=np.fft.irfft2(Fa*Fb,(PH,PW))
        # c[i,j] = sum_{y,x} T[y,x] f[y-(i-fh+1), x-(j-fw+1)] ... index of map-origin-in-frame = -(i-fh+1)
        i,j=np.unravel_index(np.argmax(c),c.shape);score=c[i,j]/(f!=0).sum()
        oy=-(i-fh+1);ox=-(j-fw+1)   # frame pixel (ds) where map tile (0,0) corner sits = -oy? 
        if best is None or score>best[0]:best=(score,s,ox*ds,oy*ds)
    return best
if __name__=='__main__':
    import sys
    for name,game in [('f60',61),('f600',587),('f1150',1124)]:
        im=Image.open(f'frames/{name}.png');day=game/20;size=herm(day);sp=893/size
        b=register(im,np.arange(sp*0.6,sp*1.6,sp*0.02))
        print(name,'day',round(day,2),'size',round(size,2),'pred px/tile',round(sp,1),'best score %.3f s %.1f origin %s'%(b[0],b[1],b[2:]))

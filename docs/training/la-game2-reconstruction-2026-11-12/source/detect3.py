import numpy as np
from PIL import Image
T=32
ys,xs=np.mgrid[0:30,0:50]
D=[(1,0),(0,1),(1,1),(-1,1)]
def samples(dx,dy,us,offs):
    n=(dx*dx+dy*dy)**.5;nx,ny=-dy/n,dx/n
    return [((xs+0.5+dx*u)*T+o*nx,(ys+0.5+dy*u)*T+o*ny) for u in us for o in offs]
BINS=[(0.12,0.26),(0.26,0.40),(0.40,0.60),(0.60,0.74),(0.74,0.88)]
SPEC=[]
for dx,dy in D:
    per=[]
    for lo,hi in BINS:
        us=np.linspace(lo,hi,4)
        per.append((samples(dx,dy,us,(-2,0,2)),samples(dx,dy,us,(-9,-8,-7)),samples(dx,dy,us,(7,8,9))))
    SPEC.append(per)
def frac(mask,P):
    acc=np.zeros((30,50))
    for px,py in P:acc+=mask[np.clip(py.astype(int),0,959),np.clip(px.astype(int),0,1599)]
    return acc/len(P)
def roadfeat(path):
    a=np.asarray(Image.open(path).convert('RGB'),dtype=np.int16);R,G,B=a[...,0],a[...,1],a[...,2]
    white=(np.minimum(np.minimum(R,G),B)>238)&(np.abs(B-R)<10)&(np.abs(G-R)<10)
    edge=(R>=195)&(R<=234)&(G-R>=5)&(G-R<=22)&(B-R>=3)&(B-R<=22)
    land=(R-B>8)&(R>200)&(G>190)
    out=np.zeros((30,50,4),np.float32);lout=np.zeros((30,50,4),np.float32)
    for k,per in enumerate(SPEC):
        lout[...,k]=np.mean([frac(land,C) for C,L,Rr in per],axis=0)
        bins=[np.maximum(frac(white,C),np.minimum(frac(edge,L),frac(edge,Rr))*1.5) for C,L,Rr in per]
        out[...,k]=np.min(np.clip(bins,0,1),axis=0)
    return out,lout
if __name__=='__main__':
    import sys
    a,b=int(sys.argv[1]),int(sys.argv[2])
    for i in range(a,b):
        o,l=roadfeat(f'boards/{i:04d}.png');np.save(f'feat/rd3_{i:04d}.npy',o.astype(np.float16));np.save(f'feat/ld3_{i:04d}.npy',l.astype(np.float16))
    print('done',a,b)

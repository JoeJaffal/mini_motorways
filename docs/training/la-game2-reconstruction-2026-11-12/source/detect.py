import numpy as np, glob, sys, os
from PIL import Image
T=32
COL={'yellow':(247,200,18),'magenta':(211,15,125),'blue':(47,129,215),'charcoal':(75,93,106),'green':(196,234,205)}
names=list(COL);cols=np.array([COL[n] for n in names],float)
ys,xs=np.mgrid[0:30,0:50]
# road sample points per link type: E, S, SE, SW (from tile x,y to neighbour)
def pts(dx,dy,us):
    P=[]
    for u in us:
        for off in (-2,0,2):
            px=(xs+0.5+dx*u)*T;py=(ys+0.5+dy*u)*T
            # perpendicular offset
            nx,ny=-dy,dx;n=max(1e-9,(nx*nx+ny*ny)**.5)
            P.append((px+off*nx/n,py+off*ny/n))
    return P
LINKS=[(1,0),(0,1),(1,1),(-1,1)]
SP=[pts(1,0,np.arange(.25,.76,.05)),pts(0,1,np.arange(.25,.76,.05)),pts(1,1,np.arange(.35,.66,.05)),pts(-1,1,np.arange(.35,.66,.05))]
def features(path):
    a=np.asarray(Image.open(path).convert('RGB'),dtype=float)
    R,G,B=a[...,0],a[...,1],a[...,2]
    road=(np.minimum(np.minimum(R,G),B)>238)&(np.abs(B-R)<10)&(np.abs(G-R)<10)
    gray=(a==128).all(-1)
    # colour fractions in inner tile area
    inner=a[:, :, :].reshape(30,T,50,T,3)[:,6:26,:,6:26,:]
    d=np.sqrt(((inner[...,None,:]-cols[None,None,None,None])**2).sum(-1))  # 30,20,50,20,5
    thr=np.array([38,38,38,30,12.0])
    cf=(d<thr).mean(axis=(1,3))   # 30,50,5
    out=np.zeros((30,50,4))
    for k,P in enumerate(SP):
        acc=np.zeros((30,50));n=0
        for px,py in P:
            ix=np.clip(px.astype(int),0,1599);iy=np.clip(py.astype(int),0,959)
            acc+=road[iy,ix];n+=1
        out[...,k]=acc/n
    vis=~gray.reshape(30,T,50,T).any(axis=(1,3))
    return cf.astype(np.float16),out.astype(np.float16),vis
if __name__=='__main__':
    fs=sorted(glob.glob('boards/*.png'))
    start=int(sys.argv[1]) if len(sys.argv)>1 else 0
    CF=[];RD=[];VS=[]
    for f in fs:
        c,r,v=features(f);CF.append(c);RD.append(r);VS.append(v)
    np.savez_compressed('features.npz',cf=np.array(CF),rd=np.array(RD),vis=np.array(VS))
    print('frames',len(fs))

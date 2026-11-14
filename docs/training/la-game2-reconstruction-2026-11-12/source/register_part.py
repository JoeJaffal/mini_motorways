import numpy as np, json, time, imageio_ffmpeg
from PIL import Image
from reg import herm, register
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
def game(v):
    for end,c in W:
        if v<=end+2:return v+c
K=0.79*893
import sys
START=int(sys.argv[1]) if len(sys.argv)>1 else 0
rd=imageio_ffmpeg.read_frames('../la-game2-score-601.mp4',input_params=['-ss',str(START)] if START else [],output_params=['-vf','fps=1'])
meta=next(rd);w,h=meta['size'];out={};t0=time.time();prev=None
for i,buf in enumerate(rd,START):
    v=i+0.5  # fps=1 filter picks frames centred on each second
    a=np.frombuffer(buf,np.uint8).reshape(h,w,3);im=Image.fromarray(a)
    g=game(v);sp=K/herm(max(g,0)/20)
    if prev is None or prev[0]<0.8:
        b=register(im,np.arange(sp*0.93,sp*1.07,sp*0.01),ds=8)
        b=register(im,np.arange(b[1]*0.985,b[1]*1.016,b[1]*0.005),ds=4)
    else:
        b=register(im,np.arange(prev[1]*0.99,prev[1]*1.011,prev[1]*0.0033),ds=4)
    prev=b
    score,s,ox,oy=b;out[i]=dict(v=v,game=g,score=float(score),s=float(s),ox=float(ox),oy=float(oy))
    # board: 32 px per tile, map 50x30
    board=im.transform((1600,960),Image.AFFINE,(s/32,0,ox,0,s/32,oy+35),resample=Image.BILINEAR,fillcolor=(128,128,128))
    board.save(f'boards/{i:04d}.png')
    if i%100==0:print(i,round(score,3),round(s,1),ox,oy,round(time.time()-t0),flush=True)
json.dump(out,open(f'cameras_{START}.json','w'),indent=1)
print('done',len(out))

import sys, numpy as np, imageio_ffmpeg, subprocess
from PIL import Image, ImageDraw
from reg import register, herm
v=float(sys.argv[1]);out=sys.argv[2]
FF=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([FF,'-v','error','-y','-ss',str(v),'-i','../la-game2-score-601.mp4','-frames:v','1','_f.png'])
im=Image.open('_f.png').convert('RGB')
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
g=next(v+c for end,c in W if v<=end+2);sp=0.79*893/herm(max(g,0)/20)
b=register(im,np.arange(sp*0.93,sp*1.07,sp*0.01),ds=8);b=register(im,np.arange(b[1]*0.985,b[1]*1.016,b[1]*0.003),ds=2)
s,ox,oy=b[1],b[2],b[3]+35
d=ImageDraw.Draw(im)
x0=int(np.floor(-ox/s));x1=int(np.ceil((1596-ox)/s));y0=int(np.floor((35-oy)/s));y1=int(np.ceil((928-oy)/s))
for x in range(x0,x1+1):d.line([(ox+x*s,35),(ox+x*s,928)],fill=(255,120,120),width=1)
for y in range(y0,y1+1):d.line([(0,oy+y*s),(1596,oy+y*s)],fill=(255,120,120),width=1)
for x in range(x0,x1):
    for y in range(y0,y1):d.text((ox+x*s+3,oy+y*s+2),f'{x},{y}',fill=(200,0,0))
im.save(out);print('camera',round(s,1),ox,oy,'score',round(b[0],3))

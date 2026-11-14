import json, sys, collections
from PIL import Image, ImageDraw
T=32;S=2  # upscale
t=int(sys.argv[1]);x0,y0,x1,y1=[int(v) for v in sys.argv[2:6]]
ev=json.load(open('roads_fixed.json'))
man=json.load(open('manual.json')) if __import__('os').path.exists('manual.json') else {'add':[],'remove':[],'driveway':{}}
st={}
for e in ev:
    if e['t']<=t:st[(e['x'],e['y'],e['toX'],e['toY'])]=e['kind']=='draw'
for a in man['add']:
    if a[4]<=t and (len(a)<6 or a[5]>t):st[tuple(a[:4])]=True
for a in man['remove']:
    if a[4]<=t and (len(a)<6 or a[5]>t):st[tuple(a[:4])]=False
im=Image.open(f'boards/{t:04d}.png').convert('RGB').crop((x0*T,y0*T,x1*T,y1*T)).resize(((x1-x0)*T*S,(y1-y0)*T*S),Image.LANCZOS)
d=ImageDraw.Draw(im);G=T*S
for x in range(x1-x0+1):d.line([(x*G,0),(x*G,im.height)],fill=(255,200,200))
for y in range(y1-y0+1):d.line([(0,y*G),(im.width,y*G)],fill=(255,200,200))
for x in range(x0,x1):
    for y in range(y0,y1):d.text(((x-x0)*G+2,(y-y0)*G+1),f'{x},{y}',fill=(170,0,0))
for (x,y,x2,y2),on in st.items():
    if on and x0<=x<x1 and y0<=y<y1:
        d.line([((x-x0+.5)*G,(y-y0+.5)*G),((x2-x0+.5)*G,(y2-y0+.5)*G)],fill=(255,0,0) if (x==x2 or y==y2) else (0,170,0),width=2)
DIRS={0:(1,0),1:(1,1),2:(0,1),3:(-1,1),4:(-1,0),5:(-1,-1),6:(0,-1),7:(1,-1)}
for h in json.load(open('houses_dom.json')):
    if h['t']>t:continue
    cs=[dd for tt,dd in h['conn'] if dd is not None];dd=man['driveway'].get(f"{h['x']},{h['y']}",collections.Counter(cs).most_common(1)[0][0] if cs else 2)
    cx,cy=(h['x']-x0+.5)*G,(h['y']-y0+.5)*G;dx,dy=DIRS[dd];d.line([(cx,cy),(cx+dx*G*.6,cy+dy*G*.6)],fill=(0,0,255),width=4)
im.save(sys.argv[6] if len(sys.argv)>6 else f'rev_{t}.png')

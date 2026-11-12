import json, sys, numpy as np
tr=json.load(open(sys.argv[1]));color=int(sys.argv[2])
COLOR={'yellow':0,'magenta':1,'charcoal':2,'blue':3,'green':4}
H=[(h['x'],h['y']) for h in json.load(open('houses_raw.json')) if COLOR[h['name']]==color]
LOTS={1:[((10,9),(3,2)),((16,17),(3,2)),((27,18),(3,2))],0:[((12,15),(3,2)),((15,12),(3,2))],3:[((11,12),(3,2))],2:[((27,15),(3,2)),((28,9),(4,3))]}[color]
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
def game(v):
    for end,c in W:
        if v<=end+2:return v+c
def house_at(x,y):
    for hx,hy in H:
        if abs(x-(hx+.5))<1.1 and abs(y-(hy+.5))<1.1:return (hx,hy)
def lot_at(x,y):
    for (lx,ly),(w,h) in LOTS:
        if lx-0.3<=x<=lx+w+0.3 and ly-0.3<=y<=ly+h+0.3:return (lx,ly)
res=[]
for t in tr:
    p=t['pts'];h=house_at(p[0][1],p[0][2])
    if not h:continue
    for k in range(1,len(p)):
        l=lot_at(p[k][1],p[k][2])
        if l:
            res.append((h,l,p[0][0],p[k][0],p[k][0]-p[0][0]));break
for r in sorted(res,key=lambda r:r[2]):print(r[0],'->',r[1],'video',r[2],r[3],'dur',r[4])
if res:print('n',len(res),'mean dur',round(np.mean([r[4] for r in res]),1),'median',np.median([r[4] for r in res]))

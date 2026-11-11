import pathlib,sys,json,numpy as np,math
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2
from PIL import Image,ImageDraw
src=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');out=pathlib.Path('tmp/full-replay-review-2026-11-08');houses=json.loads((src/'houses-final-selection.json').read_text());clock=json.loads((src/'clock-raw.json').read_text())
for x,y,c in [(10,12,'yellow'),(10,14,'yellow'),(39,5,'yellow'),(41,5,'yellow'),(30,8,'green')]:
 if not any(v['x']==x and v['y']==y for v in houses):houses.append(dict(x=x,y=y,color=c,first=0,key=f'house:{c}:{x},{y}'))
rows={v['key']:[] for v in houses}
for t in range(8,1008):
 if clock[t]['menu']:continue
 im=cv2.imread(str(out/'boards'/f'{t:04}.png'));hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
 for house in houses:
  x,y=house['x'],house['y'];px,py=round((x+.5)*20),round((y+.5)*20);a=hsv[py-6:py,px-4:px+5];b=hsv[py+2:py+6,px-4:px+5];h,s,v=a[:,:,0],a[:,:,1],a[:,:,2];c=house['color']
  if c=='yellow':mask=(h>=12)&(h<27)&(s>100)&(v>140);front=(b[:,:,0]<15).mean()>.55
  elif c=='red':mask=((h<10)|(h>165))&(s>100)&(v>100);front=True
  elif c=='cyan':mask=(h>=88)&(h<108)&(s>55)&(v>100);front=True
  elif c=='navy':mask=(h>=105)&(h<130)&(s>55)&(v>50)&(v<200);front=True
  else:mask=(h>=53)&(h<79)&(s>60)&(v>65)&(v<250);front=True
  if mask.mean()>.6 and front and float(a[:,:,2].mean()-b[:,:,2].mean())>8:rows[house['key']].append(t)
for i,house in enumerate(houses):
 observations=rows[house['key']];hits=set(observations);first=next((t for t in observations if sum(v in hits for v in range(t,t+7))>=5),observations[0] if observations else None);house['onset']=first;house['index']=i;house['samplesSeen']=len(observations)
 if first is None:continue
 im=cv2.imread(str(out/'boards'/f'{min(1007,first+1):04}.png'));white=(im.min(axis=2)>205)&(im.max(axis=2)-im.min(axis=2)<16);scores=[]
 for dx,dy in [(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]:
  norm=1 if dx==0 or dy==0 else 2**.5;values=[]
  for dist in np.linspace(.6,1.,8):
   xx,yy=round((house['x']+.5+dx/norm*dist)*20),round((house['y']+.5+dy/norm*dist)*20);values.append(float(white[yy-1:yy+2,xx-1:xx+2].mean()))
  scores.append(float(np.mean(values)))
 house['directionScores']=scores;house['direction']=int(np.argmax(scores))
(out/'house-onsets-v1.json').write_text(json.dumps(houses,indent=2))
for page in range(math.ceil(len(houses)/12)):
 sheet=Image.new('RGB',(1000,810),'white');draw=ImageDraw.Draw(sheet)
 for j,house in enumerate(houses[page*12:page*12+12]):
  x=(j%4)*250;y=(j//4)*270;t=house['onset']
  if t is None:continue
  im=Image.open(out/'boards'/f'{min(1007,t+1):04}.png');px,py=round((house['x']+.5)*20),round((house['y']+.5)*20);sheet.paste(im.crop((px-30,py-30,px+30,py+30)).resize((220,220)),(x+15,y+45));draw.text((x+3,y+3),f"H{house['index']:02} {house['color']} {house['x']},{house['y']} / t={t} dir={house['direction']} old={house['first']}",fill='black')
 sheet.save(out/f'houses-{page:02}.png')
print('houses',len(houses));print([(v['index'],v['key'],v['onset'],v.get('direction')) for v in houses])

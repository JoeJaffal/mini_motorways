import pathlib,sys,json,time
sys.path.insert(0,str(pathlib.Path('tmp/video-analysis-deps').resolve()));import cv2,av,numpy as np
r=pathlib.Path('tmp/recorded-game-comparison-2026-11-08');out=pathlib.Path('tmp/event-parity-2026-11-08');templates=[]
def digits(im):
 g=cv2.cvtColor(im[25:80,1580:1705],cv2.COLOR_BGR2GRAY);mask=(g<110).astype(np.uint8);n,l,stats,c=cv2.connectedComponentsWithStats(mask);boxes=sorted([v for v in stats[1:] if v[4]>12 and v[3]>14],key=lambda v:v[0]);return [(cv2.resize(mask[y:y+h,x:x+w],(20,28),interpolation=cv2.INTER_NEAREST),[int(x),int(y),int(w),int(h)]) for x,y,w,h,a in boxes]
for t,label in [(30,'2'),(40,'3'),(50,'4'),(60,'6'),(70,'7'),(80,'10'),(90,'11')]:
 im=cv2.imread(str(r/f'frame-{t:04}.jpg'));parts=digits(im)
 for (glyph,box),digit in zip(parts,label):templates.append((digit,glyph))
container=av.open('C:/Users/moham/Downloads/screen-capture (2).webm');rows=[];nextt=18.;start=time.perf_counter()
for f in container.decode(video=0):
 t=float(f.time or 0)
 if t<nextt:continue
 nextt+=.1
 if t>40:break
 im=f.to_ndarray(format='bgr24');parts=digits(im);text='';errors=[]
 for glyph,box in parts:
  error,digit=min((float(np.mean(glyph!=tpl)),label) for label,tpl in templates);text+=digit if error<.14 else '?';errors.append(error)
 rows.append(dict(video=t,score=int(text) if text.isdigit() else 0 if not text else None,glyphErrors=errors))
 if abs(t-round(t))<.06:cv2.imwrite(str(out/f'hud-{int(round(t)):03}.png'),im[25:80,1630:1705])
(out/'first-score-measurements.json').write_text(json.dumps(rows,indent=2));print('first known scores',[(score,next((v for v in rows if v['score']==score),None)) for score in [1,2,3]],'wall',time.perf_counter()-start)

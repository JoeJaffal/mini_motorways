import json,zipfile,hashlib
from pathlib import Path
from xml.etree import ElementTree as E
folder=Path(__file__).resolve().parent
root=folder.parents[2]
n={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read(p):
 z=zipfile.ZipFile(p);assert z.testzip() is None
 ss=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',n)]
 sheets=[];trees=[]
 for i in (1,2):
  tree=E.fromstring(z.read(f'xl/worksheets/sheet{i}.xml'));trees.append(tree);cells={}
  for c in tree.findall('.//s:sheetData/s:row/s:c',n):
   v=c.find('s:v',n);f=c.find('s:f',n);t=v.text if v is not None else ''
   if c.attrib.get('t')=='s':t=ss[int(t)]
   elif c.attrib.get('t')=='inlineStr':t=''.join(c.find('s:is',n).itertext())
   if t or f is not None:cells[c.attrib['r']]=(t,f.text if f is not None else None)
  sheets.append(cells)
 return sheets,trees
source=Path('C:/Users/moham/Downloads/Maskable_PPO_Decisions_Clean.xlsx')
target=folder/'Maskable_PPO_Decisions_Reviewed.xlsx'
a,at=read(source);b,bt=read(target)
pending={20,28,47,48,49,51,52,53,54,55,56,57,58}
for row in range(8,59):assert b[0][f'E{row}'][0]==('Not reviewed' if row in pending else 'Reviewed')
changes=[]
for addr in a[0].keys()|b[0].keys():
 if a[0].get(addr)!=b[0].get(addr):
  assert addr=='A4' or addr in {f'E{i}' for i in range(8,59)}
  changes.append(addr)
assert a[1]==b[1]
for old,new in zip(at,bt):assert E.tostring(old.find('s:sheetViews',n))==E.tostring(new.find('s:sheetViews',n))
assert a[0]['A4'][1]==b[0]['A4'][1]
assert target.read_bytes()==(root/'outputs/maskable-ppo-reviewed-2026-11-16/Maskable_PPO_Decisions_Reviewed.xlsx').read_bytes()
qa={'checks':['ZIP integrity','Only review cells and cached summary changed','All51review states match user row list','Full detail sheet values/formulas unchanged','Original summary formula and freeze panes preserved','Both source views visually checked; unchanged detail view checked previously','Archive/output bytes identical'],'reviewed':38,'notReviewed':13,'changed_cells':sorted(changes),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'nativeExcelTested':False,'runtimeNote':'Artifact Node returned1 after completed export without error text; independent exported-file checks pass.'}
(folder/'QA.json').write_text(json.dumps(qa,indent=2)+'\n');print(json.dumps(qa))

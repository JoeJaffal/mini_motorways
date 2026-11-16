import json,zipfile,hashlib
from pathlib import Path
from xml.etree import ElementTree as E

folder=Path(__file__).resolve().parent
root=folder.parents[2]
source=json.loads((root/'docs/training/maskable-ppo-spec-v1-2026-11-16/decisions.json').read_text())
p=folder/'Maskable_PPO_Decisions_Clean.xlsx'
z=zipfile.ZipFile(p);assert z.testzip() is None
n={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
strings=[''.join(s.itertext()) for s in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',n)]
def values(idx):
    out={};s=E.fromstring(z.read(f'xl/worksheets/sheet{idx}.xml'))
    for c in s.findall('.//s:sheetData/s:row/s:c',n):
        v=c.find('s:v',n);text=v.text if v is not None else ''
        if c.attrib.get('t')=='s':text=strings[int(text)]
        out[c.attrib['r']]=text
    return out
t,d=values(1),values(2)
for i,r in enumerate(source,8):
    assert t[f'A{i}']==d[f'A{i}']==r['id']
    assert t[f'E{i}']==r['review'] and t[f'F{i}']==r['work']
    assert [d[f'{c}{i}'] for c in 'BCDEFG']==[r['topic'],r['explanation'],r['reason'],r['basis'],r['next'],r['source']]
assert t['A4']=='51 decisions selected. 33 not yet reviewed by you.'
assert p.read_bytes()==(root/'outputs/maskable-ppo-decisions-clean-2026-11-16/Maskable_PPO_Decisions_Clean.xlsx').read_bytes()
tables=[E.fromstring(z.read(x)).attrib['ref'] for x in z.namelist() if x.startswith('xl/tables/table') and x.endswith('.xml')]
assert set(tables)=={'A7:F58','A7:G58'}
qa={'zip_integrity':'pass','records':51,'all_review_work_statuses_preserved':True,'all_original_detail_fields_preserved':True,'summary_cached_value':'pass','tables':tables,'archive_identical':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'native_excel_tested':False}
(folder/'EXPORT_CHECKS.json').write_text(json.dumps(qa,indent=2)+'\n');print(json.dumps(qa))

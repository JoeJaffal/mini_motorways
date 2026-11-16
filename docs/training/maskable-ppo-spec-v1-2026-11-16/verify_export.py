"""Independent native-file checks without launching Excel."""
import json, zipfile, hashlib
from pathlib import Path
from xml.etree import ElementTree as E

folder=Path(__file__).resolve().parent
root=folder.parents[2]
old_path=root/'docs/training/decision-tracker-2026-11-16/Maskable_PPO_Decisions.xlsx'
new_path=folder/'Maskable_PPO_Decisions_v1.xlsx'
output=root/'outputs/maskable-ppo-spec-v1-2026-11-16/Maskable_PPO_Decisions_v1.xlsx'
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read(p):
    z=zipfile.ZipFile(p);assert z.testzip() is None
    ss=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        ss=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
    sheets=[E.fromstring(z.read(f'xl/worksheets/sheet{i}.xml')) for i in [1,2]]
    vals=[]
    for sheet in sheets:
        table={}
        for c in sheet.findall('.//s:sheetData/s:row/s:c',ns):
            v=c.find('s:v',ns);text=v.text if v is not None else ''
            if c.attrib.get('t')=='s':text=ss[int(text)]
            elif c.attrib.get('t')=='inlineStr':text=''.join(c.find('s:is',ns).itertext())
            table[c.attrib['r']]=text
        vals.append(table)
    return z,sheets,vals
zo,so,vo=read(old_path);zn,sn,vn=read(new_path)
rows=json.loads((folder/'decisions.json').read_text())
for i,r in enumerate(rows):
    excelrow=i+12
    assert vn[0][f'A{excelrow}']==r['id']
    assert vn[0][f'D{excelrow}']=='Done'
    assert vn[0][f'E{excelrow}']==r['review']
    if r['review']=='Reviewed':
        for col in 'ABCDEFH':assert vo[0][f'{col}{excelrow}']==vn[0][f'{col}{excelrow}']
        for col in 'ABCDEG':assert vo[1][f'{col}{i+8}']==vn[1][f'{col}{i+8}']
assert vn[0]['B7']=='51' and vn[0]['F7']=='0' and vn[0]['B8']=='18' and vn[0]['F8']=='33'
for i in [0,1]:
    assert E.tostring(so[i].find('s:sheetViews',ns))==E.tostring(sn[i].find('s:sheetViews',ns))
tables=[E.fromstring(zn.read(x)) for x in zn.namelist() if x.startswith('xl/tables/table') and x.endswith('.xml')]
assert {t.attrib['ref'] for t in tables}=={'A11:H62','A7:G58'}
assert new_path.read_bytes()==output.read_bytes()
qa={'checks':['ZIP integrity','Both original sheetViews/freeze panes preserved','All51IDs/statuses match record source','All18previous reviewed choices/reasons/review flags unchanged; execution next steps refreshed','Saved cached count values 51done,0open,18reviewed,33unreviewed','Native table ranges extended to A11:H62/A7:G58','Archive/output byte identity'], 'native_tables':[t.attrib['ref'] for t in tables],'sha256':hashlib.sha256(new_path.read_bytes()).hexdigest(),'native_excel_ui_tested':False}
(folder/'EXPORT_CHECKS.json').write_text(json.dumps(qa,indent=2)+'\n')
print(json.dumps(qa))

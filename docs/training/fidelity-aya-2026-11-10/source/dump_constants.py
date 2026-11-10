import UnityPy,json,pathlib,sys
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
root=pathlib.Path(r"C:\Program Files (x86)\Steam\steamapps\common\Mini Motorways\Mini Motorways_Data")
out=pathlib.Path(r"C:\Projects\490 - Project\mm-original-reference\assets")
gen=TypeTreeGenerator('2022.3.62f2');gen.load_local_dll_folder(str(root/'Managed'))
want={'SimulationConstantsData','VisualConstantsData','GameRules','EndlessGameRules'}
files=[p for p in root.rglob('*') if p.is_file() and (p.suffix in ('','.assets','.bundle') or 'level' in p.name or 'AssetBundles' in str(p)) and p.stat().st_size>1000]
found={}
for f in files:
  try: env=UnityPy.load(str(f))
  except Exception: continue
  env.typetree_generator=gen
  for o in env.objects:
    if o.type.name!='MonoBehaviour':continue
    try:
      h=o.parse_monobehaviour_head();s=h.m_Script.deref_parse_as_object()
      if s.m_ClassName in want or 'Constants' in s.m_ClassName or 'Rules' in s.m_ClassName:
        nodes=gen.get_nodes_up(s.m_AssemblyName,(s.m_Namespace+'.' if s.m_Namespace else '')+s.m_ClassName)
        t=o.read_typetree(nodes=nodes);name=f"{s.m_ClassName}_{t.get('m_Name','')}_{o.path_id}"
        found[name]=str(f);(out/(name+'.json')).write_text(json.dumps(t,indent=1,default=str))
    except Exception as e: pass
print(json.dumps(found,indent=1))

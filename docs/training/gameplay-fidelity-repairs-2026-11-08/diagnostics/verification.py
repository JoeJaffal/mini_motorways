import json,pathlib,subprocess,time
root=pathlib.Path.cwd();out=root/'docs/training/gameplay-fidelity-repairs-2026-11-08/logs';py=str(root/'.venv/Scripts/python.exe');dn=str(root/'tmp/dotnet/dotnet.exe')
commands={'environment-final':[py,'training/test_environment.py','--dotnet',dn,'-v'],'rewards-final':[py,'training/test_rewards.py','--dotnet',dn,'-v'],'maps-final':[py,'scripts/verify_five_maps.py','--dotnet',dn]}
for name,cmd in commands.items():
 start=time.perf_counter()
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=180);data=dict(command=cmd,returncode=p.returncode,seconds=time.perf_counter()-start,stdout=p.stdout,stderr=p.stderr)
 except subprocess.TimeoutExpired as e:data=dict(command=cmd,returncode=None,seconds=time.perf_counter()-start,timeout=True)
 (out/(name+'.json')).write_text(json.dumps(data,indent=2));print(name,data['returncode'],round(data['seconds'],2),flush=True)
 if data['returncode']!=0:print(data.get('stderr',''),flush=True)

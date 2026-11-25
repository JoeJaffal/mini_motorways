from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument('--candidate-prefix',required=True);p.add_argument('--output',required=True);p.add_argument('--extra-prefix');a=p.parse_args();rec=Path('docs/training/city-whole-policy-2026-11-24')
def read(folder):
 page=(rec/folder/'replay.html').read_text();return json.loads(page.split('const replay=',1)[1].split(';\nconst canvas',1)[0])
runs={str(seed):dict(reference=read('watched-reference'+suffix),candidate=read(a.candidate_prefix+suffix)) for seed,suffix in [(184000000,''),(184000003,'-success')]}
if a.extra_prefix:
 for seed,suffix in [(184000000,''),(184000003,'-success')]:runs[str(seed)]['finite']=read(a.extra_prefix+suffix)
page=Path('training/stage1_replay.html').read_text().replace('Decision ${index}', 'Frame ${index}');payload=json.dumps(runs,separators=(',',':')).replace('<','\\u003c')
page=page.replace('const replay=/*REPLAY_DATA*/;',f'const runs={payload};let replay=runs["184000000"].reference;')
page=page.replace('<header>','<header><label>City <select id="city"><option>184000000</option><option>184000003</option></select></label><label>Policy <select id="policy"><option value="reference">Reference</option><option value="candidate">Whole-city PPO</option></select></label>')
page=page.replace('</script>','''
function switchReplay(){pause();replay=runs[document.getElementById('city').value][document.getElementById('policy').value];index=0;seek.max=replay.frames.length-1;document.getElementById('title').textContent=replay.title;document.getElementById('intro').textContent=replay.intro;draw();}
document.getElementById('city').onchange=switchReplay;document.getElementById('policy').onchange=switchReplay;
</script>''')
if a.extra_prefix:page=page.replace('Whole-city PPO</option>','Whole-city PPO</option><option value="finite">Finite-horizon PPO</option>')
Path(a.output).write_text(page);print(a.output)

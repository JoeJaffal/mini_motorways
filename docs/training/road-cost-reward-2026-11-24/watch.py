from pathlib import Path
import argparse,json,torch
from sb3_contrib import MaskablePPO
from evaluate import play
from prepare_city_policy import sha256
p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--arm',required=True);a=p.parse_args();torch.set_num_threads(1);r=Path('docs/training/road-cost-reward-2026-11-24');m=MaskablePPO.load(a.checkpoint,device='cpu')
for condition in ['small-city-offset-single','small-city-offset-stock']:
 result,frames=play(m,'validation',condition,199000001,251001,capture=True);suffix='tight' if condition.endswith('single') else 'generous';dest=r/f'watch-{a.arm}-{suffix}';dest.mkdir(exist_ok=False)
 (dest/'trace.json').write_text(json.dumps(dict(result=result,frames=frames,checkpoint=a.checkpoint,sha256=sha256(Path(a.checkpoint))))+'\n')
 page=dict(title=f'{a.arm} · {suffix} stock · {result["score"]:.0f} deliveries',intro='Native single-connection practice; policy actions, no prescribed route. Displayed score is delivered trips, not penalized training return.',speed='8',ending='60-second lesson limit',terrain=[],frames=frames)
 (dest/'replay.html').write_text(Path('training/stage1_replay.html').read_text().replace('/*REPLAY_DATA*/',json.dumps(page).replace('<','\\u003c')))
 print(result,flush=True)

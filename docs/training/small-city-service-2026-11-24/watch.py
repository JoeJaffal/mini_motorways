from pathlib import Path
import json,torch,argparse
from sb3_contrib import MaskablePPO
from evaluate_offset import play
from prepare_city_policy import sha256
p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--label',required=True);a=p.parse_args();torch.set_num_threads(1);r=Path('docs/training/small-city-service-2026-11-24');m=MaskablePPO.load(a.checkpoint,device='cpu')
for seed,action_seed in [(191000100,214000),(191000108,214008)]:
 result,frames=play(m,'validation','small-city-offset-pairs',seed,action_seed,capture=True)
 dest=r/f'watch-{a.label}-{seed}';dest.mkdir(exist_ok=False)
 data=dict(result=result,frames=frames,checkpoint=a.checkpoint,checkpoint_sha256=sha256(Path(a.checkpoint)))
 (dest/'trace.json').write_text(json.dumps(data)+'\n')
 page=dict(title=f'{a.label} · seed {seed} · {result["score"]:.0f} deliveries',intro='Native small city. No prepared roads or scripted policy actions. Complete decision trace.',speed='8',ending='60-second practice limit',terrain=[],frames=frames)
 (dest/'replay.html').write_text(Path('training/stage1_replay.html').read_text().replace('/*REPLAY_DATA*/',json.dumps(page).replace('<','\\u003c')))
 print(result,flush=True)

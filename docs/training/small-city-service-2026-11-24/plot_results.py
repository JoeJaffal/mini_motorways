from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('docs/training/small-city-service-2026-11-24');d=json.loads((r/'results.json').read_text());k='validation/small-city-offset-pairs';p=d['practice']['parent'][k];f=d['practice']['final'][k]
fig,axes=plt.subplots(1,3,figsize=(12,4.6));colors=['#777777','#357ca9'];x=np.arange(2)
for ax,metric,title,ylabel in zip(axes,['both_served','outside_routes','score'],['Both pairs served','Construction outside observed routes','Native delivery score'],['Successful games /32','Mean road units','Mean deliveries at60s']):
 vals=[v[metric]*(32 if metric=='both_served' else 1) for v in [p,f]];ax.bar(x,vals,color=colors);ax.set_xticks(x,['Parent','PPO final']);ax.set_title(title,fontsize=11);ax.set_ylabel(ylabel);ax.set_ylim(0,(32 if metric=='both_served' else max(vals)*1.3+1))
 for i,v in enumerate(vals):ax.text(i,v+.02*ax.get_ylim()[1],f'{v:.0f}' if metric=='both_served' else f'{v:.2f}',ha='center')
fig.suptitle('Longer offset pairs ·16 separate layouts ×2 action RNGs')
fig.text(.5,.02,'Outside-route units are a diagnostic proxy, not a reward penalty. Practice outcomes only; one training RNG.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.06,1,.95]);fig.savefig(r/'practice-results.png',dpi=150)

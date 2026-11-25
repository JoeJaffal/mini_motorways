from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('docs/training/city-road-choice-2026-11-24');d=json.loads((r/'results.json').read_text());fig,axes=plt.subplots(1,2,figsize=(11,4.5))
colors=['#777777','#c88736','#3179b9']
for ax,split,title in zip(axes,['repeated','heldout'],['Repeated training cities','Separate development cities']):
 for i,name in enumerate(['reference','joint','roads']):
  values=d['results'][name][split];ax.bar(i,values['mean'],color=colors[i]);ax.text(i,values['mean']+3,f"{values['mean']:.1f}\n{values['scoring']}/16 scored",ha='center',fontsize=10)
 ax.set_xticks(range(3),['Reference','Joint PPO','Road-only PPO']);ax.set_ylim(0,190);ax.set_title(title);ax.set_ylabel('Mean native deliveries at 600 seconds')
fig.suptitle('Matched city evaluation · 8 layouts × 2 action RNGs per split')
fig.text(.5,.01,'One training RNG; development comparison, not proof of broad strategy improvement.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.05,1,.95]);fig.savefig(r/'scores.png',dpi=160);plt.close(fig)

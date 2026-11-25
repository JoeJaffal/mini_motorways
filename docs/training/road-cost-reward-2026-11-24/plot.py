from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('docs/training/road-cost-reward-2026-11-24');data=json.loads((r/'results.json').read_text())['results'];arms=['parent','control','mild','strong'];labels=['Parent','No cost','Cost .01','Cost .04'];colors=['#888888','#4477aa','#eeaa44','#55aa77']
fig,axes=plt.subplots(2,2,figsize=(11,8))
for row,(condition,title) in enumerate([('small-city-offset-single','Tight stock'),('small-city-offset-stock','Generous stock')]):
 for col,(metric,ylabel) in enumerate([('first_served','Successful games /64'),('outside_routes','Mean paid units outside observed routes')]):
  ax=axes[row,col];values=[data[a]['validation/'+condition][metric]*(64 if metric=='first_served' else 1) for a in arms];ax.bar(range(4),values,color=colors);ax.set_xticks(range(4),labels);ax.set_title(title);ax.set_ylabel(ylabel);ax.set_ylim(0,68 if metric=='first_served' else max(values)*1.2+1)
  for i,v in enumerate(values):ax.text(i,v+.02*ax.get_ylim()[1],f'{v:.0f}' if metric=='first_served' else f'{v:.2f}',ha='center')
fig.suptitle('Same layouts, starting weights and training budget · only road cost differs')
fig.text(.5,.015,'Native service first, road economy second. One training RNG per arm; paired uncertainty in the report.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.05,1,.96]);fig.savefig(r/'comparison.png',dpi=150)

"""Plot available frozen-policy reviews, never training collection accuracy."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument('--name', required=True)
a = p.parse_args()
r = Path(__file__).parent
paths = [(0, r/'evaluation/decision-initial/summary.json')]
paths += sorted((int(d.name.split('-')[-1]), d/'summary.json')
                for d in (r/'evaluation').glob('decision-*') if d.name != 'decision-initial')
records = [(n, json.loads(path.read_text())) for n, path in paths if path.exists()]
assert records
fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
for case in sorted(records[0][1]):
    ax.plot([n/1000 for n, _ in records],
            [100*d[case]['mean_correct_probability'] for _, d in records], marker='o', label=case)
ax.set(xlabel='Added PPO decisions (thousands)', ylabel='Appropriate action-group probability (%)',
       ylim=(0, 102), title='Wait continuation: baseline already has 32k practice decisions')
ax.grid(alpha=.2)
ax.legend(loc='center left', bbox_to_anchor=(1, .5))
fig.savefig(r/(a.name+'.png'), dpi=150)
plt.close(fig)
source = dict(reviews=records, sources={str(path.relative_to(r)): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for _, path in paths if path.exists()},
              limits='Mean first-decision probabilities on consumed development fixtures. Repeated native play and city score are separate checks.')
with (r/(a.name+'.json')).open('x') as f:
    json.dump(source, f, indent=2)

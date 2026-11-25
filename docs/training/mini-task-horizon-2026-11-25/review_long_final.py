"""Review the complete long arm; matched control remains a separate study arm."""
import json
from pathlib import Path
from summarize_expansion_comparison import paired

r = Path(__file__).parent
read = lambda p: [json.loads(line) for line in p.read_text().splitlines()]
city = read(r/'evaluation/city-long-window-262144/games.jsonl')
comparisons = {name: paired(city, read(path), ('trips', 'paid_units', 'outside_routes'))
               for name, path in (
                   ('original', r/'evaluation/city-initial/games.jsonl'),
                   ('midpoint', r/'evaluation/city-long-window-131072/games.jsonl'))}
mini = json.loads((r/'evaluation/practice-long-window-262144/summary.json').read_text())['candidate']
report = dict(city_mean=sum(row['trips'] for row in city)/len(city),
              scoring=sum(row['trips'] > 0 for row in city),
              comparisons=comparisons,
              mini={case: dict(successes=16*row['success'], both_served=16*row['both_served'])
                    for case, row in mini.items()},
              limits='Consumed development scenarios. Full long-arm budget completed; matched short control still running. Earlier midpoint gain did not persist. No promotion or attribution to lesson duration alone.')
(r/'long-262144-review.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))

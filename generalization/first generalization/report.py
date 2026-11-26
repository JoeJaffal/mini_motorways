"""Render measured candidate metrics beside explicitly published reference values."""
from pathlib import Path
import argparse
from experiment import read, write, evaluate
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--design',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=evaluate(read(ROOT/'data/harare.json'),read(args.design))
    m=result['metrics']; refs=read(ROOT/'data/published_reference.json')
    lines=['# First generalization: graph metrics','',f"Candidate: {result['design_label']}",'',
           '| Method | Origin | NR | AD | SC |','|---|---|---:|---:|---:|',
           f"| Candidate | Measured locally | {m['NR']} | {m['AD']} | {m['SC']:.6f} |"]
    for label,row in refs['rows'].items(): lines.append(f"| {label} | Published, rounded | {row['NR']} | {row['AD']} | {row['SC']} |")
    lines += ['',f"Added segments: {m['added_segments']}/33. Unserved places: {m['unserved_places']}.",'',
              'Graph metrics and masks were checked against released KDD code. The exact training seed/checkpoint behind the paper is unavailable.',
              'The all-roads row is an unconstrained distance reference, not a budget-feasible competitor.']
    if not m['budget_complete']: lines += ['', '**Incomplete budget: do not interpret this table as a matched final-plan comparison.**']
    lines += ['', 'NR is the first construction step achieving universal access. AD/SC are evaluated on the submitted final plan.',
              'No GP performance or statistical superiority is claimed by an engineering fixture.', '',f"Source: {refs['source']}"]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(args.output.with_suffix('.json'),result)

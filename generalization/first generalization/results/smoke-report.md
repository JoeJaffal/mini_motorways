# First generalization: graph metrics

Candidate: random legal engineering fixture; not GP

| Method | Origin | NR | AD | SC |
|---|---|---:|---:|---:|
| Candidate | Measured locally | 10 | 1.0165060966813824 | 6.241118 |
| DRL-GNN | Published, rounded | 9 | 0.5 | 4.6 |
| HS-MC | Published, rounded | 13 | 0.62 | 5.31 |
| Build All Roads | Published, rounded | None | 0.47 | 11.5 |

Added segments: 33/33. Unserved places: 0.

Graph metrics and masks were checked against released KDD code. The exact training seed/checkpoint behind the paper is unavailable.
The all-roads row is an unconstrained distance reference, not a budget-feasible competitor.

NR is the first construction step achieving universal access. AD/SC are evaluated on the submitted final plan.
No GP performance or statistical superiority is claimed by an engineering fixture.

Source: https://fi.ee.tsinghua.edu.cn/~dingjingtao/papers/RoadPlan-KDD23.pdf

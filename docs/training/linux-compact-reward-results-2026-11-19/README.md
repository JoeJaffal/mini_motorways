# Linux compact connection-economy pilot results

Verified on 19 November 2026 from the local run `output/training/compact-reward-pilot-01` on `Maskable-PPO`, with HEAD `6bd7f71` and the implementation in the worktree. All 18 source hash entries in the saved config match current files, including one entry shared by both hash lists. The run used CUDA, 16 workers, two threads, 2,048 global rollout tokens and minibatches of 128 on simulator `2026-11-10.f34`. It reached its 1,800-second wall budget with 304,505 collected tokens, 592 optimizer steps and 148 policy versions. The last incomplete rollout was discarded.

Of 341 completed training games, six reached the three-trip threshold, best score was 13 and total score was 65 native trips. The episode log includes 16 additional partial games, excluded from the table. Games are ordered by report completion across workers.

| Completed games | Road units spent | Mean per game | Best score | Repeated draws with no change |
| --- | ---: | ---: | ---: | ---: |
| 1–100 | 2,000 | 20.00 | 11 | 6,559 |
| 101–200 | 761 | 7.61 | 13 | 869 |
| 201–300 | 106 | 1.06 | 0 | 6 |
| 301–341 | 9 | 0.22 | 0 | 0 |

All final 141 completed games scored zero. The decline in building alongside the loss of trips suggests construction avoidance. This training log cannot isolate the effect of the road-use penalty or establish held-out performance. No frozen comparison for this reward run was located. The earlier score-only frozen comparison reported in the extracted handoff was inconclusive, with 6/100 initial and 7/100 trained successes. The Stage 1 gate of at least three trips on 90 of 100 held-out layouts remains unmet.

The current implementation still uses manager and executor substeps, allows legal repeated draws and charges 0.01 per positive road unit consumed in connection-economy mode. The next proposal is scoped to introductory practice. Each decision would select one new legal connection or Wait, removing manager, tool and operand substeps and repeated draws, with the road-use penalty postponed. The proposal is pending approval and implementation. Implementation and a later training run require separate authorization.

[Episode measurement extract](episodes.csv), [saved configuration](config.json), [terminal status](status.json). The CSV preserves JSONL row order. Full logs and checkpoints remain local in the run directory. [Reward design and previous verification](../reward-experiment-2026-11-17/README.md).

# One-build accuracy continuation results

User authorized continuing on the same layouts and binary reward. The run resumed the final first-pilot checkpoint without resetting learned state. It reached the requested 131,072 additional attempts in 1,451.43 seconds and saved a final cumulative checkpoint at 253,952 attempts, 496 optimizer steps and policy version 124. Median collection was 19.03 seconds per 2,048 attempts. The first five rollouts got 4,908/10,240 correct (47.9%), the last five 5,091/10,240 (49.7%), and the run as a whole 64,387/131,072 (49.1%). [Saved settings](config.json), [resume provenance](resume.json), [status](status.json), [rollouts](progress.jsonl).

## Fixed held-out evaluation

All 300 games finished naturally in each comparison on layouts 20000–20099. The same sampling and action rules were used as in the [first pilot](../one-gap-single-build-results-2026-11-19/README.md).

| Trained checkpoint | Sampled correct | Highest-probability correct |
|---|---:|---:|
| First pilot | 46/100 | 50/100 |
| Continuation | 50/100 | 50/100 |

On the paired sampled comparison, four layouts improved and 96 tied. In the highest-probability comparison, all 100 outcomes were unchanged. Baselines got zero in both modes. Sampling moved closer to what the existing ranking achieves, with no gain in the layouts it can reliably solve. [Sampled summary](sampled-summary.json), [sampled games](sampled-games.jsonl), [highest-probability summary](greedy-summary.json), [highest-probability games](greedy-games.jsonl), [paired checkpoint metrics](metrics.json).

## What is missing

The frozen highest-probability policy solved **50/50 vertical gaps and 0/50 horizontal gaps**. Every selected highest-probability action was vertical. On the 50 horizontal-gap boards, the chosen vertical action was the same arena-relative slot. Swapping each board observation for every other board while retaining the target board's own valid-action mask left **all 9,900 choices identical** to the real-board choice. The test still supplies the correct legal mask. It shows no evidence that the board observation contributes to the choice on these layouts. The near-50% plateau is consistent with using vertical build preferences and the legal mask on this evenly split set, rather than selecting the gap orientation from the board. [Exact action and orientation measurements](action-diagnosis.json).

Engineering recommendation pending user approval: preserve the gap placements and immediate reward, and test a shared per-edge actor that scores the neighborhood of each legal connection with the same weights, using a consistent orientation so the scorer can recognize both horizontal and vertical instances. Compare accuracy split by orientation and rerun the board-swap control. These measurements do not establish which part of the current architecture caused the behavior. No promotion to the delivery stage and no further training or simulator change. Checkpoints and full episode logs remain local.

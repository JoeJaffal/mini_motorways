# Reward-only PPO with temporary spare road stock

User approved returning to the 66/100 clear-land checkpoint and trying two spare road units for exploration on the shortest two-build offsets. This is a continuation of the reward-trained policy; the earlier offset pilot checkpoint is not used. The parent weights, Adam state and 131,072 saved decision counter were restored. [Parent results](../reward-only-clear-roads-2026-11-20/README.md#completed-pilot).

An isolated host variant adds two or one temporary road units and corresponding action opportunities on targeted training boards. Its matched normal-stock fixtures produce identical observation planes and legal masks. The shortest distance-3 left and right layouts verified scripted deliveries with zero, one and two extra units. Native costs and legal mask rules are unchanged. [Fixture patch](extra-stock-fixture.patch), [fixture checks](fixture-verification.json).

Eight CUDA workers target two-tile offsets in equal numbers by side. Six rehearse ordinary clear boards, primarily one-tile offsets, and two rehearse adjacent gaps and bends. Only targeted episodes use higher sampling temperature during training; the PPO action likelihood uses the same temperature. Rehearsal and all evaluations use temperature one. The policy weights and untempered distribution matched the parent in preflight. The binary reward remains one for any legal connecting route, or zero. No teacher actions or route planner enter training. [Policy parity](policy-parity.json).

The schedule starts with two extra units on distance-3 boards. It reduces to one, then zero, and only then widens distances if both directions reach 85% across three completed rollouts at the current stock. The run stops at 131,072 additional build decisions, 30 minutes, or a predeclared insufficient-signal bound of no more than two successes in at least 6,000 targeted games at +2 stock. The latter avoids spending the remainder of the pilot repeating the previous near-zero signal failure. Final standard evaluation uses the original 100-layout suite and road budgets. A separate extra-stock evaluation is diagnostic only.

The service writes one line per PPO rollout. Live monitor: `tail -F output/training/spare-road-ppo-pilot-01-launch/training.log`. The `SPARE` line measures the actual targeted task independently from rehearsal.

The parent still solved 66/100 with two additional units offered at frozen evaluation. All 34 two-tile offsets still failed, so extra units by themselves did not improve its highest-probability choices. This check isolates the intended extra-stock training effect from a free-stock allowance at evaluation. [Parent extra-stock control](initial-extra-stock.json).

## Outcome and the edit-limit finding

Both spare-stock phases reached the advancement threshold. The +2 phase took 18 rollouts and the +1 phase took six. During the 16 strict zero-spare rollouts, the targeted episodes produced 0/5,453 successes. The run was stopped at a saved checkpoint after 81,920 additional decisions (212,992 cumulative) and 626.02 seconds. Sixteen newly collected decisions were discarded at the interruption. [Training progress](progress.jsonl), [status](status.json), [saved boundary](early-stop-boundary.json).

A paired check identified why the previously successful shortest routes appeared to fail. In six frozen examples, the network built both native driveway attachments explicitly, then two paid edges. The attachments are free. With two road units, the routine used two units regardless of whether the fixture offered one or two spares. The original harness allowed three edits when stock was two and therefore stopped the four-edit sequence after the first paid edge. The native construction rules permit the two free attachments. [Six exact paired traces](zero-stock-transition.json).

We corrected this in a separate paired evaluation arm by allowing one additional legal edit while retaining each board's original paid road stock and all native masks. The comparison logs the cost of every chosen edit and confirms zero paid-budget violations. That extra edit may be the final paid connection because it compensates for an earlier free driveway attachment. The old cap remains in a paired arm for comparability. The first diagnostic attempt failed before scoring because SB3's mutable distribution was shared among inference threads. Serialized policy inference fixed the diagnostic while preserving parallel native worlds. [Paired evaluator](evaluate_edit_limit.py).

| Frozen checkpoint and action selection | Original edit cap | Original road stock with room for both free attachments | Two-offset successes with room |
|---|---:|---:|---:|
| Parent, highest probability | 66/100 | 66/100 | 0/34 |
| Early zero-spare checkpoint, highest probability | 33/100 | 100/100 | 34/34 |
| Early zero-spare checkpoint, sampled | 34/100 | 98/100 | 33/34 |
| Last checkpoint, highest probability | 66/100 | 66/100 | 0/34 |
| Last checkpoint, sampled | 64/100 | 68/100 | 2/34 |

The earlier checkpoint represents 186,368 cumulative decisions. Under the original road stock plus the additional free-attachment opportunity its highest-probability choices averaged 11.52 deliveries, and 67 successful layouts needed the fourth or corresponding extra edit slot. Both frozen modes retained 100/100 on adjacent gaps and bends with their unchanged limits. The last checkpoint solved 100/100 with two extra paid units available, but the late strict-cap training erased much of the earlier no-spare ability. Preserve the early checkpoint as the best *paid-stock* policy on this suite and preserve the 66/100 parent as the best strict-cap reference. The 98/100 and 100/100 results are on the reused held-out set used to inspect the transition, with one sampled trial per layout. They do not replace the original edit-cap benchmark or establish new-layout generalization.

[Parent paired data](stock-only-parent.json), [early sampled](stock-only-sampled.json), [early highest probability](stock-only-greedy.json), [late sampled](final-stock-only-sampled.json), [late highest probability](final-stock-only-greedy.json), [early sampled regressions](transition-regression-sampled.json), [early highest-probability regressions](transition-regression-greedy.json), [grouped metrics](metrics.json).

The working early checkpoint is local at `output/training/spare-road-ppo-pilot-01/zero-stock-transition.zip`. The full run checkpoint remains `latest.zip`. No further training ran. For future clear-road evaluation that aims to constrain road units rather than keystrokes, use the stock-only arm and preserve the strict arm when comparing to historical results. For a new phase, verify this checkpoint on independent layouts before promoting it.

## Independent verification

The preserved early checkpoint passed 100/100 with highest-probability choices and 100/100 sampled on fresh seeds 36200–36299 from the same fixture distribution. The two-tile cases were 33/33 and 33/33 respectively. The same paid road stock was enforced on every board, with zero violations. This independent seed set was used after the candidate checkpoint was selected. [Summary](fresh-stock-summary.json), [per-board evidence](fresh-stock-only.json), [verification source](verify_fresh_layouts.py).

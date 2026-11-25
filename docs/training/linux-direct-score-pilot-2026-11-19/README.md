# Linux direct score-only pilot

On 19 November 2026 the user ran `direct-score-pilot-01` on the local `Maskable-PPO` worktree. The [saved configuration](config.json) hashes match current source and the separate direct Release binary. The stage was `one-gap-direct` with native trip reward, CUDA, 16 workers, two threads, 2,048 global rollout decisions and minibatches of 128. The [terminal status](status.json) records a normal 1,800-second wall-budget stop, with the incomplete rollout discarded. It collected 250,028 decisions and completed 724 optimizer steps and 181 policy versions.

The [episode extract](episodes.csv) preserves log order across workers. There were 1,440 completed training games, of which 108 (7.5%) scored at least three trips. Those 108 scored 10–13 trips and reached the time limit. The remaining 1,332 scored zero. Total completed-game score was 1,213. Sixteen partial games, two with eight trips each, are excluded. Every completed game spent all 20 available road units and no repeated draw was logged.

| Completion order | Games with at least three trips | Total trips |
|---|---:|---:|
| 1–240 | 19 | 212 |
| 241–480 | 15 | 171 |
| 481–720 | 15 | 177 |
| 721–960 | 14 | 153 |
| 961–1200 | 19 | 210 |
| 1201–1440 | 26 | 290 |

The first and last 100 games had 8 and 14 successes respectively. Games use different layouts and evolving weights, so that change is preliminary and may reflect chance or layout mix. The construction collapse from the earlier connection-economy pilot did not recur. Heavy construction coexisted with rare service, and the score-only pilot changed both the controls and reward, so it cannot isolate either effect. The training log lacks per-action histories needed to distinguish a deliberate gap repair from a chance connection or alternate path.

The next measurement is the frozen initial/latest/uniform comparison on 100 held-out layouts. No held-out comparison ran in this review. The Stage 1 promotion criterion remains unverified for these checkpoints. The original logs, progress, `initial.pt`, `latest.pt` and the direct Release binary remain local under ignored output.

## Frozen held-out comparison

Evaluated the original initial and latest pilot checkpoints and a uniform legal-action reference on layouts 20000–20099. Each layout used a fixed sampling seed. All 300 games completed naturally without weight updates. [Evaluation configuration, checkpoint fingerprints and summary](heldout-summary.json), [per-game measurements](heldout-games.jsonl).

| Policy | Connected | At least 3 trips | Mean native trips | Mean road units spent |
|---|---:|---:|---:|---:|
| Initial | 5/100 | 5/100 | 0.60 | 20.00 |
| Trained | 10/100 | 10/100 | 1.17 | 20.00 |
| Uniform legal-action | 4/100 | 4/100 | 0.45 | 20.00 |

The trained policy scored higher than its initial checkpoint on five layouts, tied on 95, and scored lower on none. The paired mean difference was +0.57 trips (95% bootstrap interval +0.12 to +1.12). Against the uniform reference it scored higher on ten layouts, lower on four, and tied on 86. This is evidence of a modest improvement over initialization for this run and sampling protocol. The trained policy still failed to deliver on 90 layouts. The Stage 1 target is 90 successes, and it remains unmet. Every policy used the full road stock on average. All games that connected delivered at least three trips. First connection, as measured here, is graph connectivity and can include an alternate route. The comparison used one sampled play per policy per layout and one trained seed.

## Why the pilot is struggling

The read-only diagnosis verified checkpoint identity and inspected the action distribution at reset. Ground-truth gap actions were determined by the scripted feasibility helper strictly for evaluation. The policy received its normal observation and legal-action mask. Across 100 held-out layouts, 457–460 builds were legal plus Wait. Mean probability of the direct repair on the first decision rose from 0.218% to 0.490%. Median rank moved from 260th to 30th, and the trained policy ranked the exact repair first on eight layouts. Similar low probabilities on the first 100 training seeds argue against held-out board position being the sole problem. [Per-layout probabilities and ranks](reset-policy-diagnostic.json).

A board-matching control evaluated each held-out board and then reused the logits from every other board with the target board's original legal mask. Across all 9,900 mismatches, the mean correct-edge probability was 0.4896%, essentially identical to 0.4897% with matched observations. The repair ranked first 8% of the time in either case. The most frequent repair slot in the first 100 training seeds occurred on 14 held-out layouts, compared with eight first-ranked repairs from the trained policy. At reset these measurements fail to show useful board-specific selection. They do not test all later decisions or rule out small observation effects. [Board-matching control](board-matching-diagnostic.json).

In completed training games 218,780 of 247,580 decisions (88.4%) were waits, and every game spent all 20 road units. Once the mask leaves only Wait, the actor has no choice to learn from on that step. At score-only reward, the successful placement earns zero until vehicles deliver. Many legal placements precede the eventual score, so that reward has weak information about which placement mattered. The saved progress log shows published policy versions and 724 optimizer steps. Ninety of 181 recorded rollout versions had zero approximate KL as logged in all epochs. The median last-epoch approximate KL was 0.00000141. These are aggregate actor-distribution diagnostics and do not identify the cause of small updates or establish an optimizer defect. [Decision and update measurements](decision-and-update-diagnostic.json).

Engineering recommendation, pending user approval: test a diagnostic stage with one legal build per episode and immediate reward for connecting house to destination. Keep legal distractors and vary the missing link location. Hold score-only delivery evaluation for the full practice game. Use matched-versus-mismatched board results and top-ranked repair rate to measure whether the policy reads the layout. If it still relies on position, test an actor that scores each candidate edge with shared weights and local board features. The current encoder pools the canvas before mapping to fixed arena-relative action slots. The probe does not establish that pooling caused the behavior. More wall-clock training on the existing setup cannot isolate these hypotheses. No implementation or optimizer update was performed.

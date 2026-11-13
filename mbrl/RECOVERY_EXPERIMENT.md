# Controlled recovery experiment

Artifacts: `output/mbrl/recovery-20261101/`. Training and test city membership remains fixed. Validation uses Dar es Salaam seeds 200000 and 200001. Final test selection is locked before London seeds 300000 and 300001 are opened.

## Frozen old controls

The original implementation is preserved in `legacy_source/`. Its demonstration state was reconstructed from seed 1000, training seeds 150000–150002 and the original 16 updates per demonstration. Episode 5 and 10 use the saved checkpoints from `full-20261101-001754`.

| Checkpoint | Policy mean trips | MCTS-8 mean trips |
| --- | ---: | ---: |
| Demonstration-warmed | 56 | 56 |
| Episode 5 | 33.5 | 33.5 |
| Episode 10 | 20 | 20 |

The original heuristic averaged 58. `checkpoint-baseline-best.pt` preserves the strongest old network. `baseline-comparison.json` contains per-seed outcomes and runtimes.

## Candidate changes and attribution controls

Native preflight checks simulator acceptance and actual state changes on clones. It preserves useful partial draws. Cooldowns follow actual driveway orientations, motorway IDs/endpoints and delayed removals. Driveway proposals require a service or queue benefit; motorway edits require improved road access.

The current-generator heuristic averaged 100.5 validation trips with 7 driveway reversals. Applying the same guards as the network averaged 80 trips with zero rejected actions and reversals. These are additional controls: gains over the original 58-trip heuristic cannot all be attributed to neural learning. See `generator-ablation.json`.

## Loss comparison

Both normalized losses trained on the same permanent replay for 384 updates, batch size 32, seed 1000. Calibration used full trajectory returns from unseen training-city seed LosAngeles/100090, with discount 0.999. This seed was not fitted.

| Value model | Calibration RMSE | Explained variance |
| --- | ---: | ---: |
| Old demonstration value against long-return targets | 43.33 | -0.23 |
| Normalized MSE | 33.58 | 0.57 |
| Normalized Huber | 35.65 | 0.52 |

Early shared-encoder gradient norms were policy 0.096/value 0.205 for MSE and policy 0.086/value 0.101 for Huber. Huber reduced gradient imbalance; MSE had lower held-out RMSE in this comparison. Both resulting policy-only models averaged 211.5 validation trips with zero rejected actions and reversals. These remain two-seed development results.

## Controlled self-play and search budgets

`controlled-v3/` continues the saved demonstration state from `controlled-v2/`, including optimizer, RNG states and permanent replay. It uses up to six episodes, 64 updates per episode and policy evaluation after every episode. Validation patience is three rounds, with at least three training episodes. Every checkpoint is saved and the best is preserved, including the initial model.

The permanent/recent/successful replay mixture is 35/40/25 percent. Value targets use full observed trajectories with discount 0.999, scale 100 and Huber loss. Reward coefficients are unchanged. Initial validation and optimizer measurements are recorded rather than inferred from combined training loss.

The recorded initial search-budget sweep compared a fixed normalized value model with policy-only and 8/32/64/128 simulations, using a common 300-second validation horizon and maximum depth eight. New evaluations use a common 1800-second horizon by default, matching training, and end earlier on natural game failure. Keep the earlier 300-second artifacts as historical results and save longer evaluations separately. Record actual depth, runtime, rejected actions, reversals, trips and search overrides. Search is not assumed beneficial merely because its budget is larger.

`pipeline-status.json` records progress. `final-selection.json` will identify the locked checkpoint, implementation and budget. `final-test.json` will hold the London results. Until these files exist, the complete experiment is still in progress. No claim of general improvement follows from the development seeds alone.

# First CPU training trial — 28 October 2026

The training pipeline ran successfully on this PC. The model did **not** learn a
useful held-out strategy or meet the 1,000-trip target. Everything is on branch
`mohammad`; the simulator core and branch `main` are unchanged.

## Run and results

Source revision: `30ef7ab15da7b0452e588cf171ba905ba7121459` (clean working tree).
Experiment schema: `full-tools-staged-grid-v1`. Configuration and exact source
snapshots are saved with the run under `output/training/first-full-tools/`.

```powershell
.venv/Scripts/python.exe training/train.py --dotnet ./tmp/dotnet/dotnet.exe --minutes 29.5 --steps 65536 --eval-episodes 3 --output output/training/first-full-tools
```

The run hit its decision budget before the time ceiling. A preceding 512-decision
checkpoint smoke test took 4.3 seconds of learning time. Installation, integration
checks and evaluation time are separate from these learner timings.

| Measurement | Result |
| --- | --- |
| Learner wall time | 431.1 seconds (7 minutes 11 seconds) |
| Policy decisions | 65,536 |
| Completed gameplay commands | 35,610 |
| Completed training episodes | 242 |
| Best training score | 7 trips |
| Total trips across completed training episodes | 10 |
| Episodes with any completed trip | 4 of 242 |
| Mean completed-episode score | 0.0413 trips |
| Last 30 completed episodes' mean score | 0 trips |
| Longest completed episode | 210.05 simulated seconds |
| Episode outcomes | 242 ordinary failures; 0 external time caps |
| Policy decisions / second | 152.0 |
| Gameplay commands / second | 82.6 |
| Policy parameters | 450,610 |
| PPO training epochs recorded by the model | 1,024 |
| Policy weights changed | Confirmed |
| Sampled Python working set during training | Approximately 378 MB; not a whole-system peak measurement |

Hardware: Intel i7-1185G7 (4 cores / 8 logical processors), 32 GB installed RAM,
Intel Iris Xe graphics. Training used CPU PyTorch with two threads and one host.

Training used Los Angeles seeds 1000–1099, OriginalReference, finite materials and
normal failure rules. Reward was only the increase in completed trips. Every
ordinary tool was available subject to its stock/targets. No route suggestions,
debug reference roads, future spawn information or stock grants were used.

## Held-out evaluation

Each evaluation below used the same masks and 3,600-second safety cap. All games
ended by ordinary failure at about 140 simulated seconds, well before the cap.

| Seed | Starting policy, sampled actions | Final policy, sampled actions | Final policy, highest-probability actions |
| --- | --- | --- | --- |
| 2000 | 0 | 0 | 0 |
| 2001 | 0 | 0 | 0 |
| 2002 | 0 | 0 | 0 |

The seven-trip training episode is a best observed exploratory outcome, not
evidence of a learned seven-trip policy. There is no held-out improvement in this
small evaluation. A separate fresh-process reload of `final.zip` also worked:
on seed 2000 its highest-probability policy placed 25 road tiles and then waited
116 times, completing zero trips. It exhausted its starting concrete without
building a productive network.

This points to exploration/action coordination as the next experiment to address.
The current measurements establish that this PC can run the pipeline; they do not
justify a training-time prediction for a 1,000-trip agent. At unchanged throughput,
one million policy decisions would take roughly 1 hour 50 minutes, but that is
only a compute estimate. No longer run has been started.

## Verification and artifacts

- All seven adapter checks passed: Gymnasium contract, information boundary,
  invalid-action timing/reset/truncation, ordinary termination, all tool command
  decoders, ordinary scripted roads yielding positive rewards, and exact replay
  of masked random actions across five maps. Tool decoder fixtures are isolated
  protocol tests; they do not grant training stock or create policy suggestions.
- Existing simulator checks passed: 37 shared suites and five-map protocol checks
  covering ten version/map combinations.
- Repository hygiene, dependency consistency and whitespace checks passed.
- Initial, periodic and final checkpoints were saved. Final weights were reloaded
  for evaluation and in a separate Python process.

Local generated artifacts are intentionally ignored by Git:

- `output/training/first-full-tools/final.zip`: final policy and optimizer.
- `output/training/first-full-tools/config.json`: revision, seeds, dependencies and experiment contract.
- `output/training/first-full-tools/summary.json`: learner speed and before/after evaluation.
- `output/training/first-full-tools/episodes.jsonl`: completed training episodes.
- `output/training/first-full-tools/progress.csv`: optimization statistics.

See [the training guide](README.md) for installation, observation/action encoding
and commands to resume a checkpoint in a new run directory.

# Connectivity reward experiment — 28 October 2026

The user authorized adding a carefully designed reward for useful connections.
The training CLI/PowerShell helper now default to `connectivity`; `trips` retains
the old reward for comparisons. At implementation, no shaped learning had run.
The user has since launched shaped trials; see the [current status](CURRENT_STATUS.md)
and live-check evidence. Faster learning has not been demonstrated. The recorded
73-trip result still belongs to the earlier trip-only policy.

## What counts as useful

A house counts once if current ordinary dispatch routing can reach an existing
same-color destination and return from that selected destination entrance to
the house. The diagnostic uses `BestRouteTo` and `FindRoute` from the actual
simulator, including directed roundabouts, bridges, entrances and motorways.
Pending/retired links are excluded, as they are for new ordinary trips. Extra
tiles, nearby but unlinked roads, wrong-color destinations, multiple paths to
the same destination and outbound-only routes do not add house credit.

This measures structural reachability, not congestion, parking throughput,
sufficient car supply, future demand or guaranteed delivery. A connected house
may still be part of a failing city. Counts are recomputed after topology
changes and cached otherwise. The optional headless diagnostic neither builds
roads, steps time, changes stock/RNG nor gives a suggested route to the actor.
The 50-channel/42-global observation schema and action masks are unchanged.

## Reward accounting

At each policy selection, including intermediate tool/endpoint choices:

```text
Phi(state) = 0.25 * min(usefully_connected_houses, 8)
shaping = 0.999 * Phi(next_state) - Phi(current_state)
training_reward = completed_trip_delta + shaping
```

The discount must equal the policy's gamma. Both are 0.999; incompatible resumed
checkpoints are rejected in connectivity mode. A true game failure has next
potential zero. An external time cap keeps its live potential, because SB3
bootstraps that truncated transition. Reset initializes the potential from the
new city without awarding reward. Intermediate selections still advance no
simulation time; they now receive the discount correction when connected.

Examples with no trip finishing:

| Transition | Shaping reward |
| --- | ---: |
| Zero to one connected house | +0.24975 |
| One house stays connected for one selection | -0.00025 |
| One to zero connected houses | -0.25 |
| Failure from one connected house | -0.25 |

The quarter-trip weight and eight-house cap are initial engineering choices,
not optimized settings. Potential is bounded by two trip units, emphasizing
early useful construction. Beyond eight simultaneously connected houses there
is no additional connectivity bonus; actual trips remain the source of ongoing
reward. There is no road-length, survival or construction-cost reward.

## Why this avoids a rebuild reward loop

This is discounted potential-based shaping, rather than paying an independent
bonus each time a connection appears. Discounted shaping telescopes:

```text
sum(t=0..T-1, gamma^t * shaping_t)
    = -Phi(initial) + gamma^T * Phi(final)
```

An episode ending in failure has final potential zero. A repeated
create/delete loop ending at its starting zero potential has zero discounted
shaping return, not a positive bonus. Failing/disconnecting cashes out the
remaining potential negatively. Applying the correction only on completed
commands would be wrong here: PPO discounts intermediate selections too.
Small negative unchanged-state corrections are accounting, not a congestion
penalty. Undiscounted shaping totals need not equal zero.

The design follows [Ng, Harada and Russell's original potential-based shaping
paper](https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf). Its ideal discounted
MDP result motivates this form; it does not guarantee faster convergence for
our finite, partially observed neural-network experiment. Approximate critic
fitting, truncation bootstrap and optimization still matter. Sparse discovery
of the first complete route remains possible; no partial-road-distance signal
or planner has been added.

## Scores, logs and compatibility

- `score`, best-game ranking, seed means and held-out evaluation remain actual
  trips. Final evaluation uses trip-only environments.
- `trip_reward`, `shaping_reward` and their cumulative totals are separate in
  info; logs/status expose reward mode, connected houses and potential.
- Monitor CSV's `r` is now the sum of shaped training rewards in connectivity
  mode. Use its `trips` column for the game score. Older archived charts use
  trip-only `r`; do not silently reuse that convention for new runs.
- Replay command/score/time checks stay unchanged. New replay metadata records
  the reward schema; `config.json` and source snapshots preserve `rewards.py`.
- Input schema is still `full-tools-staged-grid-v1`; reward schema is separately
  versioned as `trip-plus-connectivity-potential-v1` (baseline `trip-delta-v1`).
- Existing checkpoints can warm-start this experiment. Their critic/optimizer
  learned the old returns and may need to adapt; this is not a controlled
  comparison with a fresh model or proof of an improvement.
- Low-level `TrafficEnv` defaults to trip-only for legacy evaluation/tests;
  the training CLI/helper explicitly select the new default. The throughput
  benchmark remains trip-only so its established protocol is unchanged.

## Verification and measured audit

Six reward tests cover exact create/delete-loop accounting, failure/reset,
the potential cap and non-terminal bootstrap convention, intermediate choices,
baseline/shaped host equality, and a full normal-material replay. The core's
41st suite covers matching color, a legal return path, one-credit-per-house,
cache invalidation, detached/deleted links, reset and no gameplay mutation.
The parallel suite also checks four shaped hosts autoresetting correctly and
loading the old checkpoint with unchanged inputs, without optimizer updates.

The [fixed-command audit](../docs/training/connectivity-reward-audit-2026-10-28.json)
replayed the existing best recording in two real hosts. It ran no policy and
performed no optimizer updates. Results:

| Measurement | Result |
| --- | --- |
| Fixed commands | 462 |
| Score / simulated duration | 73 trips / 461.35 seconds |
| Baseline/shaped encoded observations and outcomes | Identical after every command |
| First positive shaping | Command 23, time 23 s, score still zero: +0.24975 |
| Peak connected houses | 12 (potential still capped at eight houses) |
| Positive / negative shaping transitions | 8 / 432 |
| Discounted shaping sum from zero initial potential | Approximately zero (2.22e-15 rounding residual) |
| Undiscounted shaping / training reward totals | -0.70775 / 72.29225 |

The audit advances one recorded gameplay command per transition, without its
historical intermediate actor selections; selection accounting is tested
separately. Its totals are a reward verification trace, not the rewards of a
new learned trajectory. It is not a speed/convergence benchmark. The audit
records the base revision plus dirty-source flag; the implementing commit
contains the exact source and JSON.

Reproduce without training (choose a fresh output path):

```powershell
.venv/Scripts/python.exe training/test_rewards.py --dotnet ./tmp/dotnet/dotnet.exe -v
.venv/Scripts/python.exe training/audit_rewards.py --dotnet ./tmp/dotnet/dotnet.exe --output tmp/reward-audit-repeat.json
```

## Run when ready

Suggested first trial: 15 learner minutes on seed 1000, four workers, warm-start
the last trip-only checkpoint. Use a fresh run name; shaped-01 has now been used:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\training\start_training.ps1 -Minutes 15 -StartSeed 1000 -SeedCount 1 -Workers 4 -RewardMode connectivity -RunName seed-1000-shaped-02 -Resume output/training/seed-1000-parallel-02/final.zip
```

For a matched baseline choose another fresh run name and `-RewardMode trips`.
Compare actual trips, last-window means, held-out scores, action mix, useful
connections and throughput. Multiple seeds/repeated trials are needed before
claiming faster learning. Do not compare shaped reward totals with old trip
scores as if they were the same metric.

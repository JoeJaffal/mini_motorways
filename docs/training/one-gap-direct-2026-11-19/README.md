# Direct one-gap practice

On 19 November 2026 the user approved direct connection actions, native trip reward, and a three-policy comparison for introductory practice. Implementation is local on `Maskable-PPO`, based on `6bd7f71` plus the existing uncommitted trainer. The [connection-economy pilot](../linux-compact-reward-results-2026-11-19/README.md) motivated the change. Its late decline in construction suggested avoidance, with cause unresolved.

Select `--stage one-gap-direct` in `training/train_parallel_stage1.py`. The stage retains the existing 12×12 compact arena, 20 road units, one-gap layouts, no-delete rule, paused edits, native waits and 180-second game horizon. Wait is action zero. The remaining 576 action slots encode four canonical neighbor directions for each arena tile. The native mask admits a distinct new link when both endpoints and the connection are legal. It excludes duplicate directions, existing links, tile-only draws, failed parcel connections and driveway rotations. It leaves legal links available independent of their strategic value. The simulator applies the usual draw command and the wrapper verifies exactly one new reciprocal edge and no deletion.

The stage uses a single Maskable-PPO actor and value stream with the existing visible encoder. The collector can cut between any two direct decisions. Score is the sole reward. Connection detection and road use are evaluation metrics. The historical hierarchy and reward modes remain available on their original stages.

## Verification commands

Use the separate headless build so the historical binary stays available. From the project root, choose a new artifact directory.

```bash
dotnet build simulation/Headless/TrafficHost.csproj -c Release --artifacts-path output/direct-host
host="$PWD/output/direct-host/bin/TrafficHost/release/TrafficHost.dll"
STAGE1_DIRECT_DLL="$host" PYTHONPATH=training .venv/bin/python -m unittest -v test_direct_practice
.venv/bin/python training/train_parallel_stage1.py --stage one-gap-direct \
  --device cpu --workers 2 --rollout-tokens 63 --minibatch-size 32 \
  --dll "$host" --output output/training/direct-dry-new
```

The dry runner does a forward-only collection and loss check. A new pilot requires separate authorization. The direct stage requires a fresh model because its action space and policy differ from existing checkpoints.

## Held-out evaluation

Once authorized training produces checkpoints, pass the original `initial.pt` and a trained checkpoint from the same configuration to `training/compare_stage1.py`, with `--dll "$host"`, a new `--output` directory, and `--layouts 100`. It evaluates initial, trained and uniform-legal-action policies on layouts 20000–20099 with per-layout sampling seeds. The uniform reference samples among all enabled actions including Wait. Each game records first connection time and decision, road use, native score and how it ended. Summary reports include repair rate, mean simulated repair time among repaired games, trips, natural completions and paired comparisons. The gate requires at least three trips on 90 of 100 layouts and a valid comparison. A capped or operationally truncated game invalidates the comparison.

The first direct pilot tests action and reward changes together. Separating their effects needs a controlled follow-up. Scripted feasibility and forward-only tests do not establish a learned result.

The historical connection-economy weights, logs and Release binary remain local. The pre-change source archive at `output/training/pre-direct-source.7uNyp8/source.tar` matches all 17 unique source files hashed by that run. Use that source in an isolated directory with the historical Release binary for strict checkpoint replay or resume.

## Recorded checks

The Release build succeeded and 23 tests passed. A scripted one-action repair produced 10–13 native trips on each of the 100 held-out layouts. The two-worker dry run collected exactly 63 decisions, computed the PPO loss and left weights unchanged with zero updates. A two-layout CLI smoke completed all three policy arms using identical untrained fixture weights and synthetic checkpoint counters. No optimizer step or training pilot ran. [Verification evidence](verification.json).

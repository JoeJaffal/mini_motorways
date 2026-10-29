# Signal context v4: preserve learned weights, add queue causes

The first user trial finished: development average204.2 ->228.0, mostly from one
map. Before extending training, run the frozen fresh-map comparison:

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\evaluate_fresh_signals.py --run output/training/signals-context-01 --seed-start 6000 --output output/experiments/signals-context-fresh-01
```

This compares the warm-start initial and development-selected best models on
ten new maps in deterministic/sampled modes (40 games), with no updates. Source
and checkpoint hashes/seeds are recorded before inference. Tell the assistant
when complete; do not tune or reselect models using these results and call them
fresh again. The assistant has not started this evaluation. Use a new output
name if the folder exists. This tests transfer of this run's learning, not the
causal benefit of new inputs over equal-budget additional v3 training.

The preparation/training instructions below are historical and remain supported.

User requested implementing the diagnosis while conserving assistant credits:
only short correctness checks were run. The user will launch and wait for the
longer experiment. No full evaluation or long training was started here.

Start a one-hour trial in PowerShell:

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\train_goal.py --output output/training/signals-context-01 --signal-context --warm-start output/training/signals-night-01/validation-best.zip --minutes 60 --workers 4 --validation-minutes 15
```

This transfers the existing best v3 weights into v4. It does **not** discard the
learned road/light policy. The two widened light-input matrices copy their old
columns and initialize new columns to zero; all other weights copy unchanged.
The optimizer resets because input shapes changed. Reward scale, learning rate,
prior temperature and decision timing inherit the provided checkpoint. Reward,
legal placements, proposal ordering and simulator rules are unchanged. There
is no seed5009-specific ban or hand penalty for parking queues.

Initial predictions match v3 up to floating-point tolerance. The additional
information must be learned; this is not an immediate performance fix. No
improvement is established by the preparation checks. Initial/final development
evaluation adds time; periodic validation counts within the one-hour window.
Ctrl+C saves. If the folder exists, change01 to02. Tell the assistant when done;
summary.json/validation-best.json can be read locally without pasting long logs.

For another continuation, use `--resume` with the new v4 checkpoint and a new
output directory. `--warm-start` is specifically v3->v4 with a new optimizer;
`--resume` keeps a matching-schema optimizer. They cannot be combined. Direct
v3-to-v4 resume is rejected. V3 remains available and old checkpoints load as v3.
The generic frozen evaluator infers v4 from the24-wide signal observations.

## Inputs and exact feature definitions

Schema `visible-route-signal-context-v4`,547 actions,21,503 parameters. Route
rows, globals and five-plane traffic map retain v3 meanings. Signal rows expand
from12 to24 values; the first12 remain unchanged. New fields are clipped[0,1]:

| Index | Value |
| --- | --- |
| 12 | Fraction of nearby stopped cars blocked by carpark access |
| 13 | Fraction blocked by crossing vehicle or approaching-vehicle priority |
| 14 | Fraction blocked by a traffic light |
| 15 | Fraction reporting queue ahead |
| 16-17 | Maximum parking-access wait /60; maximum crossing-priority wait /60 |
| 18 | Maximum overcrowding timer /50 among destinations of nearby outbound/entering-parking cars |
| 19 | Maximum unreserved demand / destination capacity for those destinations |
| 20 | Maximum visible destination overcrowding timer /50 across the city |
| 21 | Fraction of those related destinations with a positive overcrowding timer |
| 22 | Candidate is the road cell immediately outside a shop entrance |
| 23 | Existing light fraction across candidate cell and visible eight neighbors |

Nearby means the candidate and its eight visible neighboring integer cells.
Stopped means waiting>=3 simulated seconds. Fractions use the stopped-car count,
minimum denominator1. Other obstacle reasons remain uncategorized. This is current
structured simulator information, not future-event data, a complete approach-flow
model, or a forecast of downstream congestion. Returning cars are not assigned a
current outbound destination for pressure fields.

The diagnostic5009 and exposed test seeds4000-4009/5000-5009 are not training or
development maps. Training remains1000-1099, validation2000-2004. A future final
test needs a new held-out partition; these input changes are not a new test result.

## Checks

A synthetic observation-only fixture checks parking/crossing distinction and
destination pressure. Synthetic stock/queues are never executed as simulator
commands or used for performance measurement. V3->v4 probability preservation,
zero new columns, fresh optimizer, nonzero gradients into new inputs and saved
schema detection were checked. Three existing real-stock/replay checks still pass.
One tiny CLI warm-start/save/evaluation smoke completed in0.255 learner seconds,
three decisions, no PPO update. It is a wiring test, not learning evidence.

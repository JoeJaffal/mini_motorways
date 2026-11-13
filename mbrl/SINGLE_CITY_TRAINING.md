## Current behavior - saved AlphaZero restored, 12 November 2026

User clarified restoration of earlier AlphaZero. Saved WIP e53f3bb core and matching host API restored; default snapshot branch/native preflight/search-only future forking. Incoming f23 gameplay and reward counters retained (host2026-11-12.f23-alpha1). The recovered host implements snapshots and preflight by C# history replay, not instant state cloning. Native checks pass, but100-history2-rollout search took28.9seconds; no practical-speed or quality claim. No production training restarted. [Source/checks/limits](../docs/training/alphazero-restore-2026-11-12/README.md). The no-snapshot/replay-only descriptions below are superseded historical records.

## Current training path - 12 November 2026

User revoked native snapshots. Active training/evaluation use deterministic reset-and-replay, with no saveSnapshot/loadSnapshot, forkFuture or validateActions requirement. Candidate acceptance occurs on execution; prior preflight and alternate-future descriptions below are historical. Simulator reporting counters restored in 2026-11-12.training1. Three tiny training rounds plus validation and one resumed round passed; full-episode speed/quality unmeasured. See [current commands and evidence](../docs/training/replay-training-ready-2026-11-12/README.md). Older details below describe earlier implementations where superseded.

# Los Angeles training with held-out seeds

New experiments use `single-city-seeds-v1` in `experiment.py` and `protocol.py`.
The city is **LosAngeles** for training, validation and testing. The previous
Dar es Salaam validation and London test split remains attached to historical
checkpoints and frozen source snapshots; new experiments do not use it.

| Purpose | City | Seeds | When run |
| --- | --- | --- | --- |
| Training | LosAngeles | Random positive signed 32-bit integers, without replacement | Each training episode |
| Validation | LosAngeles | **200000**, fixed | After every **three** completed agent-training episodes |
| Test | LosAngeles | **300000**, fixed | Only when explicitly requested |

Both held-out seeds are excluded from training draws. An independent seed sampler
keeps game-seed selection separate from MCTS exploration and replay sampling.
Each fresh experiment generates a sampler seed and records it in `config.json`
as `seed_sequence_seed`. Pass `--seed-sequence-seed N` to reproduce the sequence.
The sampled game seed is logged in every episode row and trace.

The defaults are `--city LosAngeles --validation-seed 200000 --test-seed 300000
--validate-every 3 --validation-seeds 1 --test-seeds 1 --bootstrap-episodes 0`.
There are no automatic heuristic demonstrations, validation baselines, initial
validation games, or extra final validation games for an incomplete group of
three. With six episodes, the sequence is:

```text
train A -> train B -> train C -> validate 200000
train D -> train E -> train F -> validate 200000
```

Validation defaults to policy-only (`--evaluation-budgets 0`). Search/reward/input
settings are independent of the seed split and remain configurable. Validation
produces no replay samples or optimizer updates. The latest model remains the
selected checkpoint; validation does not restore an earlier model.

The current reward includes +10 per trip, a delivery-linked bonus of
`0.1 * trips * (1 - blocked_fraction)`, and a bounded congestion penalty of
`0.02 * blocked_fraction * elapsed_seconds`, alongside existing penalties.
Active cars waiting at least two seconds count as blocked; Home/Parking cars
are excluded. Rewards and the threshold are saved in checkpoints and must match
when resuming; older reward versions require a weights-only warm start.

## Continuing a run

`--resume <checkpoint-last.pt>` restores model, optimizer, replay, recorded RNG
states, the seed sampler/used-seed ledger and completed-example count. A run
stopped after two training examples validates after its first resumed example,
then again after example six. Seed split and validation cadence must match.

Existing mixed-city checkpoints require `--init-checkpoint <latest-checkpoint>`
for a weights-only transition to this protocol. Their previous replay and
validation metadata must not be treated as Los Angeles seed-split experience.
An exact resume across different data protocols is rejected. Historical weights
and artifacts are retained.

If a run finishes after four examples, the selected checkpoint is episode four,
while its latest validation describes episode three. `selection.json` keeps
these separate; it does not claim the final checkpoint was evaluated.

## Deferred testing

Normal training does not open seed 300000. It records `testDeferred: true` and
does not write `test.jsonl`. Training's `--final-test` flag and the evaluator's
explicit `--split test` are the CLI routes that open that seed; do not pass either
until the user requests testing. No real test game was run while implementing
this protocol.

For a new-protocol checkpoint, `evaluate.py` reads the saved city and fixed seed.
Its default split is validation, and the split has exactly one case. Historical
checkpoints continue to use their historical city split unless migrated through
a new experiment. Frozen source remains historical.

## Verification

`check_single_city.py` covers random-seed collisions, exclusion of both held-out
seeds, sampler restoration, evaluation-case selection, no early/final-extra
validation, exact three-example cadence and continuation across an incomplete
group. A short native simulator smoke check ran three random Los Angeles games
followed by the fixed validation case. No production-length training was started.

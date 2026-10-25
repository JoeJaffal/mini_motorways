# OriginalReference training readiness — 26 October 2026

**Verdict:** the headless simulator passed this bounded integration audit. A model-facing training adapter is still missing; raw protocol output should not be fed directly into a policy. No model was created, trained or evaluated in this audit. Game behavior and the Windows apps were not changed.

## Executed checks

Run `dotnet build simulation/Headless`, then `python scripts/check_training_readiness.py --dotnet <SDK executable>` from the repository root. Python uses only its standard library. [Machine-readable results](training-readiness.json) include per-run outcomes and observation-sequence hashes.

- OriginalReference only, normal material limits and overcrowding failure rules.
- Five maps, seeds 0/42/99, two scripted modes, each replayed exactly: **60 episodes**.
- Each episode capped at 300 simulated seconds; failures can end earlier.
- Wait mode performs no construction. Debug-road mode invokes the privileged reference-road helper every ten seconds and selects the first weekly package. It is a diagnostic control, not a model or an allowed policy action.
- **2,473 requests**, approximately **70.2 seconds wall time** for this run. This includes serialization, resets, scripting and replay checks; it is not an estimate of learner throughput.
- Core grid arrays stayed at 1,500 entries, materials stayed nonnegative, and inspected vehicle positions/speeds/waiting stayed finite.
- Full sampled observations replayed exactly for each seed/map/mode. Invalid requests did not corrupt the tested state, zero-tick steps were unchanged, failed episodes stopped advancing, and subsequent resets/replays matched.

Among the 30 unique episodes before their replays, all 15 wait-only episodes failed normally with zero trips. The 15 debug-road episodes completed 504 trips in total: 14 reached the cap, while London seed 42 failed normally at 279.2 seconds. No scenario was rejected. The largest final-snapshot vehicle wait in debug-road mode was 6.3 seconds. These are diagnostic outcomes, not learned performance or proof that no longer waits occurred between snapshots.

## Required before connecting a learner

| Item | Finding / required adapter behavior |
| --- | --- |
| Version | Explicitly reset `OriginalReference`; do not silently switch to Custom or grant extra materials |
| Observations | Encode/pad variable-length building, car and infrastructure lists into the chosen policy input |
| Privileged information | Exclude `scheduledSpawns`, RNG diagnostics, future `upgradeAt` and planned demand multipliers; audit the remaining fields for the intended player information boundary |
| Actions | Define a stable model action space and validation/masking; exclude `reference`, reset, stepping controls and other diagnostic commands from model choices |
| Time | Construction commands do not advance the simulation; specify the simulation ticks per policy decision so a policy cannot act forever without time passing |
| Reward | No scalar reward exists. Choose an explicit formula using score/survival diagnostics; the simulator's `objective` text is not a reward |
| Episodes | Treat game failure as termination, enforce an external time cap as truncation, and prevent further model actions until reset |
| Reproducibility | Record simulator commit, map/seed distribution, encoder, reward and decision interval; keep held-out evaluation seeds |

The distinction between termination and external truncation follows the [Gymnasium environment contract](https://gymnasium.farama.org/api/env/). This repository currently exposes JSON requests, not that model-facing environment wrapper.

## Limits

These scripted runs do not cover arbitrary learned action sequences, all legal construction operations, adversarial road edits, concurrent workers, crash recovery, very long episodes or transfer to the actual game. Traffic/parking/spawn approximations remain, and `exactReplicaValidated` remains false. No claim of full original-game fidelity or a finished training pipeline follows from this PASS.

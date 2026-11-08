# Event parity requirement and movement audit — 8 November 2026

User decision: “I need them to perform identically.” Improved scores and passing unit suites are not acceptance. Treat matching observed events/causal behavior as the target; label current state **NOT IDENTICAL**. This supersedes any implication that the previous30/37-trip repair establishes parity. No training, score fitting, seed search or stock/demand grants.

## Measured earliest deliveries

Original HUD sampled at0.1video-second intervals, templates derived from known visible digits. First score1/2/3 changes confirmed across3 consecutive samples. Registration/clock/action uncertainty remains; reported game times are estimates from the earlier weekly calibration. Raw video/crops/artwork local only.

| Delivery | Original first-seen estimated game time | Before movement audit | Factor3 only | Factor3 + weighted lookahead |
| --- | ---: | ---: | ---: | ---: |
|1|17.418|25.15|17.55|17.45|
|2|29.826|44.55|32.15|32.05|
|3|47.408|56.05|47.15|41.15|

The original event occurs between preceding sample and first-seen sample; numeric intervals archived. First delivery now agrees within reconstruction uncertainty, but2remains~2.2seconds late and3~6.3seconds early. Do not cherry-pick1or the factor-only3coincidence, or declare identical behavior. At330s,69-rule candidate50trips/no failure/99events, compared with preceding carpark-only37at330s. This is a paired simulator improvement on the same inferred inputs, NOT a validated comparison to original835. Full draft retains later invalid CV diagonals.

## Confirmed implementation errors corrected

Read-only audit of installed reference movement logic/configuration reveals:
- Lane values are multiplied by a distinct movement factor3 and configuration multiplier1 when computing desired vehicle speed. Our code converted lane values for tile width2 but omitted the factor. Ordinary target should be1.5tiles/s from lane value1world-scale, not0.5. Route-cost lane values remain separate and unchanged. Motorway follows the same explicit factor, rather than an unproven fixed cap.
- Ordinary movement uses distance-weighted lane lookahead; motorway uses the minimum. Our low-speed/deceleration-envelope approximation was different. Independently implement the configured lookahead, preserving physical collision/merge guards.

Numeric facts and private-evidence hashes archived; private decompiled content/assemblies remain local. These corrections are rule-derived, not selected by score. Weighted correction worsens the third-delivery match despite passing first-delivery/overall improvement; preserve that negative observation. Remaining phase/parking RNG, input timing, geometry and process differences are open hypotheses, not proven causes of that event.

## Checks and fixture chronology

Before audit67 suites; factor3 plus long-free-flow speed regression68PASS. Added analytical ordinary/motorway lookahead example gives69PASS. All four orientations/two seeds/recorded prefix still pass, including physical separation and return progress. Adapter7environment and10map-version checks PASS. Reward checks initially fail because historical fixture v2expected terminal at209.9s but corrected simulator survives. Preserve v2 in earlier report. Separate factor-only v3ordinary-command fixture records12trips/252.95s/253actions; weighted rule changes it to13, so preserve v3and create v4using identical initial commands, normal waits, actual terminal, fixed300sim-second budget. No expected outcome fabricated or test relaxed. v4reward verification pending. These are scripted correctness diagnostics with no learning/optimizer or policy performance claims.

## Reproduction

```powershell
.\tmp\dotnet\dotnet.exe run --project simulation/Headless/TrafficHost.csproj -- --self-test
.\tmp\dotnet\dotnet.exe run --no-build --project simulation/Headless/TrafficHost.csproj -- --run-scenario simulation/Scenarios/recorded-la-prefix330.json
.\tmp\dotnet\dotnet.exe run --project tmp/event-parity-2026-11-08/Trace.csproj -- simulation/Scenarios/recorded-la-draft.json
.\.venv\Scripts\python.exe tmp/event-parity-2026-11-08/measure_first_scores.py
```

Trace.cs is a local non-learning diagnostic with150sim-second/30wall-second bounds; source archived. OCR script decodes only through40video seconds; no original art in archive. Source video SHA256c9762eb1d8c474c328b01f59a4a0ca744a0c8a06e2794e2dafe285712b1d4629. Numeric carrier seed remains-915001679, not original RNG recovery. No journal/matching seed available in scoped prior searches; original process not running during this continuation. Full same-state parity cannot be certified from this partially observed trace. Required next evidence is matching demand/dispatch/parking events and validated full action reconstruction, or an original state/event record. Do not substitute score equality or broad tolerances for that evidence.

Unity rebuilt factor-only player locally but not installed; final weighted69-rule player build pending. Generated binaries/logs and private extracts/video remain local. No commit/push/training. Prior global documentation check non-UTF8 historical blocker unchanged.

## Final verification and deployment

69core,7environment,6reward-v4,10map-version checks PASS. Original Unity build passes; player prefix50/330/99 matches headless and normal LA startup20s passes. Installed after graceful close check, previous app backed up at local tmp/event-parity-2026-11-08/previous-player. Reopened prefix330 paused. Installed assembly SHA256473F03D7972553A41C4DF81BF2928559187DCD097EB9E2A75C67836A6DBA62D7. Supersedes earlier pending checks/build notes; factor-only build not installed.

Machine-readable observed timing gate: `python docs/training/event-parity-2026-11-08/source/compare_events.py` exits1, statusNOT_MATCHED. First event within estimated observation interval plus one0.05s tick;2and3outside. This does not remove clock/input reconstruction uncertainty or certify hidden state. Internal/unit/player PASS must not be confused with this failed original-event comparison. No overall parity success or full final score comparison. All historical fixtures/results retained; no learning/weights/promotion/commit/push.

Follow-up read-only dispatch review: original normal-timer dispatch selects the lowest available path-cost house, consistent with our intended policy. The10-second at-house availability property is used by the separate permanent-balanced demand path; it is not a reason to add a10s normal-timer dispatch cooldown. No cooldown change made. Vehicle waiting-queue order/driveway start poses, path geometry/cost detail and the unknown group phase/parking choices still require matched observations before attributing the third-delivery error. These are open questions, not accepted explanations.

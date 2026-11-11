# Carpark gate ignores red-light cars — 9 November 2026

[Report section 13](../../docs/training/simulator-repairs-2026-11-08/README.md#13-map-3101-a-red-light-car-held-the-carpark-gate-simulator-2026-11-087), [handoff](HANDOFF-2026-11-sim-fix.md). A car waiting at a red light can no longer take or keep the engineered carpark gate (simulator `2026-11-08.7`); this fixes LA 3101's late collapse. 85 core/7 environment/6 reward/10 map PASS. Deterministic lights comparison: 580.3 with lights vs 535.5 without (6 better, 4 worse). `main` carries the same simulator, as a simulator-only copy. No training.

# Carpark chunk arbitration — 8 November 2026

[Report section 12](../../docs/training/simulator-repairs-2026-11-08/README.md#12-carpark-lanes-as-original-chunks-gate-kept-simulator-2026-11-086), [handoff](HANDOFF-2026-11-sim-fix.md). Carpark lanes arbitrated as the original's chunks and registered as inbound lanes (simulator `2026-11-08.6`); removing the engineered gate deadlocks our entrance geometry, so it stays. 84 core/7 environment/6 reward/10 map PASS. Lights comparison 529.7 vs 535.5 without. Ready for the Evolved Rules re-evaluation and gp-5. No training here.

# Original traffic lights replicated — 8 November 2026

[Report section 11](../../docs/training/simulator-repairs-2026-11-08/README.md#11-original-traffic-lights-replicated-simulator-2026-11-085). Original traffic-light phases and permissions replicated from Mohammad's inspected rules (simulator `2026-11-08.5`). Three new checks fail on .4 and pass; 83 core/7 environment/6 reward/10 map PASS. Deterministic lights on/off (LA 3100-3109): stuck time up to 237 s → ≤4.7 s; lights 408.4→510.5 vs 513.2 without. Carpark chunk arbitration is next. No training.

# Original signal/carpark follow-up documented — 8 November2026

[Read-only response](../../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SIGNALS_CARPARKS_ANSWER.md). Signal blocked-count/weights/amber semantics and carpark chunk arbitration documented with numeric evidence. No engine edits, model evaluations, training or deployment; runtime merge-toggle/other overrides remain uncertain.

# Carpark gate measures every car at one point — 8 November 2026

[Report section 9](../../docs/training/simulator-repairs-2026-11-08/README.md#9-carpark-gate-cars-passing-through-measured-at-the-same-point-simulator-2026-11-084), [note to Mohammad](../../docs/training/simulator-repairs-2026-11-08/NOTE_CARPARK_GATE_CHANGE.md). Carpark approach gate: cars passing through a shared lot are now gated at the same outside-approach point as arriving cars, and gate waits are visible to cycle recovery (simulator `2026-11-08.4`). The v20 lock reconstruction fails on .3 and passes; 82 core/7 environment/6 reward/10 map PASS. v20 replay: 620 trips, no deadlock. New finding: a signal phase that never switches in v21; question sent to Mohammad with a note on the gate change. No training.

# Original junction arbitration replicated — 8 November 2026

[Report section 8](../../docs/training/simulator-repairs-2026-11-08/README.md#8-original-junction-arbitration-replicated-simulator-2026-11-083), [handoff](HANDOFF-2026-11-sim-fix.md). The original's junction entry arbitration is replicated from Mohammad's rule description (simulator `2026-11-08.3`): lane-count gate, red light, blocking-cycle shove, shared-exit space test, committed-candidate eligibility and route-time registration. Three new checks fail on the previous engine; 81 core/7 environment/6 reward/10 map PASS. Replays v20 and v21 have no deadlock (490 and 488 trips). A carpark gate lock at shared lot 20 now ends them; not fixed, awaiting the user. No training.

# Original junction-rule answer documented — 8 November 2026

[Six-question response](../../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SPACE_CHECK_RULE_ANSWER.md). Conditional gap checking plus eligible-prefix arbitration/blocking-cycle recovery confirmed; no blanket box rule or guarantee ofv21fix. Read-only source/config audit only; no engine/fixture/run changes. Runtime45sfeature and stopped-connection geometry remain unresolved.

# Simulator repairs after resume — 8 November 2026

[Report](../../docs/training/simulator-repairs-2026-11-08/README.md), [re-evaluation handoff](HANDOFF-2026-11-sim-fix.md). Reward-v4 drift isolated to the intended rule-77 native join (new fixture v5); stale `Waiting` on arrival fixed; additive `simulatorVersion` (`2026-11-08.2`); permanent roundabout/junction yield-cycle deadlock proven and fixed; v21 regenerated from the builder with the seven handoff corrections (topology check passes 400/400). 79 core/7 environment/6 reward-v5/10 map PASS. A physical adjacent-junction gridlock ends v21 and awaits a user rule decision; Unity player not rebuilt; no training or push.

# Missing-file handoff ready locally — 8 November 2026

[Transfer bundle and review response](../../docs/training/full-replay-review-2026-11-08/LOCAL_TRANSFER_RESPONSE.md). Verified2368payloads,924MiBlocalZIP; no external upload. Simulator work remains stopped in this handoff iteration. Source77checks from Aya are recorded; reward-v4drift remains unexplained. No engine/fixture/training change.

# Resume check: reward-v4 regression found — 8 November 2026

[Resume review for approval](../../docs/training/full-replay-review-2026-11-08/RESUME_REVIEW_FOR_APPROVAL.md). Committed 77-suite source (`f7ce005`, including the dedup edit) re-checked on another machine: 77 core PASS, 10 map PASS; environment 6/7 (missing local `tmp/` only); **reward v4 FAILS: ordinary LA fixture now 23 trips/no game-over vs 13/game-over**, so the 75–77 changes alter ordinary play (cause not yet isolated). No engine, fixture or test changes. Awaiting Mohammad's approval and local files; no training.

# EMERGENCY STOP — 8 November 2026

User requested stop/save. [Saved state and exact continuation plan](../../docs/training/full-replay-review-2026-11-08/EMERGENCY_HANDOFF.md). Installed74-suite player; source77candidate ahead, final small dedup edit not retested. No active matching diagnostics found. Full replay/parity unvalidated; do not resume automatically. No training.

# Shared-carpark replay repair under verification — 8 November 2026

[Full review](../../docs/training/full-replay-review-2026-11-08/README.md): shared-lot through-routing independently implemented; initial71core/7environment/6reward/10mapPASS. Erased old motorway endpoint cleanup72PASS. v15reaches371/game-over957.05s with shared outside-turn deadlock; approach-boundary correction and bent mixed-flow regression pending. Strict input reconstruction435events still incomplete; partial scores are not a valid835comparison. Installed69-rule player unchanged. No learning, grants or score fitting.

# Movement audit installed; original event parity NOT matched — 8 November 2026

Missing reference movement factor3 and ordinary weighted/motorway minimum lookahead corrected.69 core/7 environment/6 reward-v4/10 map-version PASS; Unity prefix50/330/99 and startup verified. Installed with backup. [Audit and failing original timing gate](../../docs/training/event-parity-2026-11-08/README.md). Original first-delivery estimate17.418vs17.45, but later events still mismatch. No exact original state/full trace or identical behavior claim. No learning.

# Recorded carpark performance repair — 8 November 2026

Boundary reservation bypass and bay merge cycles repaired;67 core/7 environment/6 reward/10 map-version checks PASS. Same297.45s trace improves24/game-over→30/no game-over,330s37/no failure. [Details](../../docs/training/video-performance-repair-2026-11-08/README.md). Full original parity and later trace remain unvalidated; no demand/stock/seed tuning or learning. Player rebuilt/verified/installed with local backup; visible prefix330 reopened paused.

# Custom seed and scenario playback — 8 November 2026

Numeric seed input/CLI and fixed-event JSON playback installed in Original player.58 core checks plus Unity/headless scenario agreement and normal startup smoke pass. [Usage](../Scenarios/README.md), [evidence/limits](../../docs/training/custom-video-scenario-2026-11-08/README.md). Video reconstruction remains draft: original835 vs simulation24 at297.45s,84/780events; not exact recovered seed or validated full parity. Red dynamic parking blockage remains open; no gameplay fix to fit score.

# Current implementation status — 28 October 2026

This is the current snapshot. [VERSIONS.md](VERSIONS.md) specifies the rule sets; [Reports/README.md](../Reports/README.md) indexes the supporting evidence. Earlier reports and the decision history describe their dated milestones and may use smaller test counts.

## Implemented

| Area | Current behavior |
| --- | --- |
| Packaging | Separate Original and Custom apps, fixed rules per scene, one shared Unity-independent core |
| Cities | Los Angeles, Beijing, Tokyo, Dar es Salaam and London; Tokyo retains all six color groups |
| Original progression | Recovered playable bounds, expansion curves, starting offsets, demand ramps and schedule metadata |
| Original materials | City starting stocks, partial weekly package choices, retirement and material reuse |
| Motorways | Two-way links, vehicle paths, finite stock, retirement and endpoint editing retaining committed paths |
| Destinations | Scheduled circle upgrades, age eligibility, doubled demand, capacity 6 to 9, three-bay single lots |
| Shared lots | Two colors sharing nine bays and two entrances in four orientations |
| London rail | Train movement/stops, four-cell station platforms, batch demand and crossing closures/release |
| Original parking | Connected circulation/branch lanes, diagonal bay midpoint stops/headings, drive-through paths and release before lot exit |
| Custom | Fixed working area, unlimited construction, permanent spending, prices 2/5 additional/10/8, 30-second grace and approximate rejection; no motorways or trains |
| Headless | The same simulation files exposed through JSON requests and detached observations |
| AI replay (`mohammad` branch) | Exact ordinary-command recordings, per-command outcome validation, read-only Original player playback and final-map inspection; no gameplay rule changes |
| Driveway connections | Building a road at a visible driveway end automatically attaches the parcel; ordinary adjacent roads still require a drawn link |
| House driveway editing | Draw outward from a house with the Road tool to choose a cardinal or diagonal exit; invalid terrain and occupied parcels are rejected |
| Roundabout conversion | Placement accepts moving traffic; committed lane paths can clear while subsequent routes use the circle |
| Geometry and crossing clearance | Circular roundabout paths/rendering share the researched radius; road width and lane offset follow atlas constants; exit-section crossing reservations release without holding the previous lane |

## Evidence

- **39 shared suites** pass in .NET and Unity, including two AI replay checks added on `mohammad`. The Original player was rebuilt for replay support; earlier Original/Custom builds and geometry checks are documented in the [investigation](../Reports/traffic-and-scale-investigation.md). These checks show internal consistency, not original-game parity.
- The RNG component matches **180 installed-assembly values** across five seeds. Full random call order and seeded-run equivalence are unverified.
- All **53 ordered London rail cells**, loop flag and origin index match the installed topology component. This does not validate train movement timing.
- Live London observation and selected LA/London footage informed visual and parking corrections. These are exploratory structural comparisons, not synchronized motion measurements.
- An original London Classic journal is preserved privately. Its supported envelope is decoded; the full simulation object graph is not.

## Accepted for now

The user accepted the current parking entrance and concurrency approximations while work proceeds on other differences. Surface paths connect to entrance centers, access is conservatively serialized, and a trip retains its selected entrance for its return. These remain documented timing/capacity differences; they do not require another user decision.

## Remaining replication work

- Exact spawn placement, support-house logic, random draw ordering, seed initialization and fixed-point/process timing. (`2026-11-11.g1`, decisions 085–088: OriginalReference free play now follows the original's placement weights, building influence, dead zones, driveways, edges, house scheduling and double-lot/circle fallbacks; random draw ordering and process timing remain open.)
- Full motorway/traffic geometry, merge/conflict/rerouting rules and queue behavior.
- Weekly weighting/history, bridge/edit accounting and tunnels.
- Exact station placement, train stopping/motion, batch demand and crossing timing.
- Full original-journal graph import and controlled successive-state comparisons.
- Broader presentation/input differences. Independent viewer drawings are not original game artwork or UI.

`exactReplicaValidated` remains false, and `requireExact:true` refuses a reset. Internal tests show reconstruction consistency, not original-game equivalence. Numeric source hashes are in [REFERENCE_DATA.json](REFERENCE_DATA.json).

8 November fidelity repair: [roundabout concrete conservation](../../docs/training/roundabout-concrete-fix-2026-11-08/README.md) implemented in source;44 shared suites pass. Other approximation entries remain open; current Windows player has not been rebuilt.

8 November repairs: [verification/deployment](../../docs/training/gameplay-fidelity-repairs-2026-11-08/README.md),54 suites plus adapter/player checks. Supersedes parking entrance-center/whole-lot gate and tile-based material descriptions above for current source/Original build. Exact placement/RNG/traffic parity remains open. New recording request now freezes further changes: [comparison audit](../../docs/training/recorded-game-comparison-2026-11-08/README.md),835 original, matched simulator score unavailable.

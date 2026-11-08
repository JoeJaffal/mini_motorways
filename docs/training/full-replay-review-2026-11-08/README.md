# Full recorded-input review — 8 November 2026 (in progress)

User explicitly accepts the reviewed opening and authorizes continuing independently with their gameplay/simulator. Continue input reconstruction first, then diagnose remaining engine mismatches. No user timestamp review required. No learning/model decision/training, score fitting or extra material grants. Current candidate is NOT a validated full replay or original parity result.

## Measured reconstruction findings

- Re-register source at every sampled second rather than interpolate10s camera anchors:956/1008frames directly measured; others mostly menu/intro fallback. Compared with prior calibration, median maximum-of3probe displacement0.00390tiles, worst0.16352tiles atvideo306. Camera error is real but small; it does not establish a multi-tile camera error or explain all missing buildings.300s wall budget, completed156.32s.
- Independently inspected final roofs: old automatic selection omitted yellow houses10,12;10,14;39,5;41,5. Add these four to prior51-house draft (including green30,8), total55observed houses. Connected-component size/persistence filters can discard houses with parked cars; causal score contribution not measured. Roof/onset candidates manually inspected; green42,21native actuallywest, not detector diagonal, confirmed video876/879 before SW user turn880. Green30,8visible spawn888, native direction partly motorway-occluded; retain south as explicit unresolved assumption.
- Reviewed117diagonal candidates and subsequent stable crops;18are visually supported, most others rounded corners, native halos, motorway deck/labels or UI toast text. Classification remains input reconstruction, not an original internal graph dump; cancelled previews/action timing remain uncertain. Preserve actual diagonal strokes rather than globally disabling diagonals.
- Destination entrance audit: navy at12,14has TOP entrance(layout2), not bottom3. Later green at39,16has LEFT entrance(layout0), not right1. Other12destination/slot event footprints reviewed. Wrong entrances can completely disconnect routes despite a plausible drawing. No engine rules changed.
- Previous extraction rejected roads through future destination parcels before those destinations existed. Make footprint filtering time-dependent; this matters for roads near early motorway endpoint14,18before later red shared parcel spawns. Full correctness still under validation.
- Native stub additions become explicit driveway direction changes; free native segments are not separately replayed as user-created road cells. Direct, undilated stub evidence screens turns. Search later frames to distinguish first preview from visible stable turn; e.g.green34,20turnsouth becomes clear at382, not first noisy detection378.

## Strict diagnostic chronology

All custom replays use existing120s wall cap, stop on rejected input/normal game-over. No rejected input ignored, no inventory replenished. Scores below are conditional diagnostic outputs, NOT valid full comparisons to835.

| Candidate | Stop/result | Diagnostic output |
| --- | --- | --- |
|v10|game-over461.05s,97/456events|87trips; navy0served because entrance still incorrectly bottom|
|v11|rejected road at542.5s,128/456events|126trips; corrected navy/green entrances; insufficient stock|
|v12|game-over786.65s,182/439events|249trips; green23,17disconnected due missing bridge/native turn|
|v13|rejected road832.95s,195/443events|286trips, alive; input validation still incomplete|

v11road stock agrees with video at90(21),170(23),240(23). At280video15vs candidate12; at290video15vs candidate9. Inspected6false additions: two orthogonal sides of actual diagonal20,10–21,9, false25,12–25,13corner leg, motorway-deck false stems14,17–14,18and15,6–15,7, plus false26,12–26,13near a rounded road. Source stock unchanged15during motorway placement280–290also rejects three inferred paid road edits in that interval. Remove specific visually unsupported activation windows, not random roads to match stock. Later uses remain separately reviewed/uncertain.

v12missing bridge was our overly late guard390; actual second bridge is visible384at33,22, confirmed source crops. Correct that data guard and native green turnSouth at382; no bridge grant/physics change. v13gets past former green failure but another material mismatch remains. Native-only common endpoint auto-connectivity is an open modeling question for later green38,19/39,16pair; not yet changed or asserted as measured cause.

## Artifacts and scope

Own scripts/numeric findings archived. Raw source video, crops/contact sheets and generated players/logs stay local under tmp/full-replay-review-2026-11-08. Old frozen/opening datasets remain historical. Candidate source path and raw road transitions are local pending validation; source video SHA256c9762eb1d8c474c328b01f59a4a0ca744a0c8a06e2794e2dafe285712b1d4629. Existing69-rule engine unchanged. No build/deployment or original game writes this iteration yet. Full destination/house timing, road edits, wall-clock pause/speed synchronization and hidden RNG remain unverified. Do not report286vs835 as a valid comparison.


## Shared-carpark routing and deferred cleanup — continuation

Engineering finding: the simulator explicitly rejected intermediate building traversal, including shared lots. Read-only private installed-reference evidence establishes physical circulation between both shared entrances and a doubled carpark path cost. Independently implement the shared-lot traversal using our actual internal lanes; no bay reservation/delivery for passing through. Generalize entrance and clearance bookkeeping to the physical carpark rather than the trip's final destination. Tests cover both directions, mixed passing/parking traffic, continuous lane joins, no overlaps and no extra points. Initial implementation passes71core suites,7environment,6reward-v4 and10map/version checks. These checks do not establish identical original behavior.

Same v14 inputs with earlier69-rule engine:295trips/game-over847.45s,214/436events, far red served0. With shared transit:335trips/alive, rejected insufficient concrete895.2s,226/436events. These partial/rejected scores are diagnostics, not a valid835comparison. v14 stock at source320=23,430=11,480=7 agrees with video after specific input corrections;540=10vs13 and570/590=7vs8 remain mismatches. Paused intervals require an end-of-pause comparison or video-prefix filtering, since events on one game-time plateau apply together.

Rejected hypothesis: the five vertical roads x15,y13–18 appearing around source513 are NOT false old-motorway detections. Source500/510stock6 drops to0by520 after those five plus one upper link. Keep them. SourceHUD540=13,550=12,560/570/590=8,600=0. Visually confirmed false extra24,11–24,12 is a rounded diagonal curve, removed only for its unsupported activation window549–1007 in v15. Strict rejection then moves to shared spawn918.85s,353trips,236/435events.

Causal engine finding: erased old motorway endpoint14,18 remains a degree-zero Road cell after the old motorway disappears. It blocks the source622destination despite having no edges. Preserve deferred cleanup only for cells whose connections were explicitly erased while an endpoint still existed; do not delete arbitrary roads. Added cleanup regression passes72core suites. Same v15 reaches371trips/game-over957.05s,242/435events. No full comparison yet.

The later v15 failure exposes another circulation interaction: car12(outbound to shared20) and car20(returning from navy14, passing shared20) face each other in the outside right-angle approach at tile20,18; car26departing the lot also waits. Gate owner20is correctly retained, but the arriving car waits partway into the outside turn, obstructing the exit. Instrumented physical-carpark/gate state archived. Proposed correction reserves the outside approach before its turn, retaining ownership through it; mixed bent-approach regression added. First new test setup was invalid (destination entrance faced left while approach came from below); corrected fixture uses explicit bottom entrance. Final checks/replay pending. This is an engineering clearance rule, not proof of exact original lane control.

Source/video crops and private code stay local. Numeric diagnostics, own scripts and private evidence hashes only are archived. Installed player is still69-rule build; no deployment yet. Original hidden RNG, precise recorded clock/preview edits and later unvalidated actions remain open. No learning, extra stock, tolerated rejection, score fitting or commit/push.


## Approach gate and signal retirement verified — continuation

Approach-boundary correction passes73core suites, including the new mixed bent shared-lot case. Samev15then rejects stock895.2s with338trips because circulation changes refund timing; do not claim the full trace passed from unit tests. Inspecting source590prefix finds road19,13–20,13still held by outbound car25at signal20,13. Confirmed cause: deleting the connection removes its signal phase while a committed car still has that approach, so it waits indefinitely. Retain signal pairs for retired connections until retirement clears, and refresh pairs on clearance. Added bounded300sim-second regression requires both deliveries and both returns across the retired approach. Test setup corrections: argument order and light inventory index3 (initial fixture used4) fixed; production behavior unchanged by those setup corrections. Final74core/7environment/6reward-v4/10map-version PASS.

v16also corrects source cyan8,8birth665→664: explicit image663empty,664roof/native stub,665pulse. Avoids a paid native draw before its house. v16with signal correction reaches396trips/alive at970.15s,262/434events then rejects concrete. This gets beyond preceding371/shared deadlock but remains an incomplete trace, not a valid comparison to835.

Separate topology-only diagnostic suppresses all demand timers and generates no traffic or score;30s wall cap. It checks strict event placement/material feasibility with immediate unused-edge refunds, not simulator performance or original inventory timing. v15rejects false pre-house native draw; v16rejects concrete263/434at970.15. Use it to inspect later data without ignoring gameplay rejection or modifying scored runs. Further video findings:25,11–25,12at608is another rounded cyan diagonal side;37,9–38,9at686is the motorway ribbon before its endpoint38,9. Specific unsupported windows omitted in v17. Source stock620/640=7,650/660/670/680/690=5,700/710=0; preserve five actual upper-left cyan connection edges. v17strict/topology diagnostics pending. No stock grants or ignored rejection.


## Emergency stop — user request

Work stopped immediately on user request. [Exact saved state and continuation plan](EMERGENCY_HANDOFF.md). Installed verified74-suite player; source77candidate adds native motorway/common-endpoint attachment, initial77PASS but final dedup edit not retested. Latest v20/75diagnostic586trips/game-over1185.95s/340of406events is incomplete, not valid835comparison. Seven late input corrections visually identified but NOT applied; source77not built/deployed. No matching active diagnostics at stop. Do not resume automatically.


## Resume review — awaiting approval

[RESUME_REVIEW_FOR_APPROVAL.md](RESUME_REVIEW_FOR_APPROVAL.md). Committed 77-suite source (`f7ce005`, including the dedup edit) re-checked on another machine: 77 core PASS, 10 map PASS; environment 6/7 (missing local `tmp/` only); **reward v4 FAILS: ordinary LA fixture now 23 trips/no game-over vs 13/game-over**, so the 75–77 changes alter ordinary play (cause not yet isolated). No engine, fixture or test changes. Awaiting Mohammad's approval and local files; no training.


## Missing local files packaged — 8 November 2026

[Transfer response and review clarifications](LOCAL_TRANSFER_RESPONSE.md). User requests action on Aya review; local-only924MiBZIP contains2368payload files including video/boards/crops, all payload hashes verified. No external media upload, engine edits, fixture change or training. Simulator work remains stopped this iteration.

# Replay input validation: reviewed opening — 8 November 2026

User asks what now after accepting that wrong reconstructed actions prevent a fair comparison. Engineering choice: freeze simulator tuning for this iteration, validate replay inputs directly. No traffic/core/viewer code changed, no model decisions or learning. This is a first60-video-second review, not full-game validation.

## Measured input errors

The detector treated automatic native house/shop driveway stubs as player road draws. The viewer already renders native stubs; synthetic DrawRoad calls prematurely create ordinary road infrastructure at their endpoints. In particular, red home19,11was born facing WEST, but inference from later images set it north and then synthetic road edits turned it west/north. The west road cell18,11remained orphaned after rotation. Another synthetic road cell10,7appeared at the red destination before any user road action there.

Corrected only the scenario data: initial native directions, observed second-house/red-building visible onsets with uncertainty, actual paid-road stroke order, explicit red west→north driveway change and removal of synthetic native-stub construction.16events replace old21through video60. First path: destination down/left/down to house; second north/east connection; red stroke north after turning the driveway. Building-owned native stubs remain visual/access geometry, not separately annotated user-built roads.

Seven independent manual checkpoints (video14,16,18,21,24,57,60) specify player-built road cells/connections excluding native-only stubs, native driveway directions and stock. Old draft2/7match; corrected7/7match. Counts are generated from the simulator and compared with manually transcribed visual layout, not re-derived from the corrected event list. This is a mapping of observed player infrastructure, NOT access to the original internal lane graph.

| Video second | Estimated game second | Observed road stock |
| --- | ---: | ---: |
|14|4|25|
|16|6|24|
|18|8|20|
|21|12|20|
|24|18|17|
|57|84|17|
|60|90|15|

Original stock snapshots independently reviewed from the video. Both old/new stock can match despite false **free** road cells: stock alone is not a sufficient input validation gate. Red north turn no longer leaves the false western road cell. Exact birth/commit times remain uncertain: first visibility/road animation is not the hidden simulation frame. Annotated intervals remain, no fabricated exactness. In-between events may need further review even when checkpoint layouts match.

## Scope / what this does not prove

Only the opening60video seconds, approximately90simulator seconds. Source clock is approximate (early1x then2x); carrier RNG is not original state. Event choice/layout checks do not certify matching demand, dispatch, parking RNG, vehicle positions or scores. Existing original-event timing comparator remains NOT_MATCHED. Do not present source full835 against this prefix. Full draft/330prefix and their historical measurements preserved; later false diagonals and all remaining video actions unvalidated.

The current viewer plays simulator time at selectable1x/4x/16x; it does not reproduce the recording's wall-clock pauses/2x settings. Scheduled game-time edits and wall-clock-synchronized video playback are separate requirements. This is an additional open playback limitation, not a reason to alter traffic speed. No videosync feature added in this iteration.

## Verification / use

Installed existing69-rule player loads corrected JSON without a rebuild. Batch verification PASS6trips/90game seconds/16events.6is incidental loader output, not a new parity claim. Seven input checkpoints PASS; no simulator code changed and no broad core rerun needed. Source observations use232samples at0.1video-second increments in the opening/action windows, manually inspected road/inventory crops. Raw video/crops/artwork remain local under tmp/replay-validation-2026-11-08, not archived. Only own scripts and numeric annotations/measurement outputs are archived.

Watch `simulation/Scenarios/recorded-la-reviewed-opening60.json` using --scenario-file; starts paused. Closed only our previously launched read-only replay if still present, then opened this reviewed input clip. No binary replacement or original-game writes. No learning/weights/source commit/push. Existing global documentation checker blocker remains historical non-UTF8 report.

Reproduce numerical comparison:

```powershell
.\.venv\Scripts\python.exe docs/training/replay-input-validation-2026-11-08/source/compare_checkpoints.py
.\tmp\dotnet\dotnet.exe run --project tmp/replay-validation-2026-11-08/Checkpoints.csproj -- simulation/Scenarios/recorded-la-reviewed-opening60.json tmp/replay-validation-2026-11-08/reference-checkpoints.json
```

Diagnostic project source expects its original tmp location (restore from source/ there). Fixed90sim-second/30wall-second check budget, no learning. Source video SHA256c9762eb1d8c474c328b01f59a4a0ca744a0c8a06e2794e2dafe285712b1d4629. Next stage: continue manually validating remaining input segments and clock/pause mapping before attributing full score differences to engine behavior.

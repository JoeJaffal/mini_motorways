# First fidelity repair: roundabout concrete — 8 November 2026

User authorized starting fixes and plans to upload a complete original-game recording for matched choices/end-score comparison. Recording is future evidence, not yet supplied. Video alone cannot guarantee extraction of original seed; current simulator seeded streams do not match whole-run original spawns. Reconstruct visible layout/events/actions and label divergences; report matched-layout/choice comparison separately from proven same-seed replay. No original game/save settings touched.

## Implementation and checks

Engineering choice: first isolate confirmed lost concrete during roundabout conversion rather than simultaneously rewriting connection pricing and traffic. Intended scope announced before editing. On mohammad, existing dirty tree preserved. TrafficWorld records the count of ordinary road tiles replaced in the circle footprint; RoundaboutState holds that pending credit. Conversion refunds immediately if no away-from-home car retains an old non-roundabout/non-parking/non-motorway lane through the footprint. Otherwise FinishRemovals returns stock once those remaining lane paths clear, before removing the roundabout state. Zeroing credit prevents repeated refunds. Custom unchanged; no traffic/spawn/demand constants changed. Concrete accounting still uses tile occupancy; this is an incremental conservation fix, not full original pricing/retirement parity.

Added two regression suites: all five footprint road tiles refunded exactly once across three construction/removal cycles; an occupied three-road footprint retains credit then refunds exactly once even when circle removal is queued immediately. Existing42 plus2 new suites: PASS44, command `.\tmp\dotnet\dotnet.exe run --project simulation/Headless -- --self-test`. git diff --check passes (line-ending notices only). No training, optimizer, model evaluation or long diagnostics. No claim of learned skill, score improvement or commercial timing parity.

Source snapshots archived under source/. Base revision a65204242056c26c97b22f31fc4392f495429020 plus dirty working tree; manifest hashes final source/report. No commit/push. Headless build is local-only. Open TrafficLabOriginal player remains prior build and has NOT been replaced or restarted; Unity build/pixel verification not performed. This source fix does not become visible in that process without a rebuilt app. Historical replays/checkpoint comparisons may differ if they use affected conversions: preserve old source/binaries and do not relabel old reports.

## Remaining work

Connection-based pricing requires separate stock accounting across ordinary edges, branches/cycles, free building edges, bridges, conversion and delayed deletion. Parking/roundabout movement and supporting-house logic remain unrepaired; original trace needed to calibrate throughput/progression without arbitrary easing. Weekly reward UI and refund timing still require comparison. No full-list completion claim.

Links: [original investigation](../gameplay-fidelity-check-2026-11-08/README.md), [stock checks](../gameplay-fidelity-check-2026-11-08/ROAD_STOCK.md), [roundabout checks](../gameplay-fidelity-check-2026-11-08/ROUNDABOUTS.md).

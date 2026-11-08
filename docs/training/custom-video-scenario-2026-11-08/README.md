# Custom seeding and recorded-game reconstruction — 8 November 2026

User decision: after the comparison freeze (design063), the user explicitly authorized adding custom seeding and reconstructing it from the uploaded video. Scope: reproducible seeds and scheduled visible events; no gameplay/demand tuning to match835, no learning or new training run.

Engineering choice: a numeric seed selects the simulator RNG; a JSON custom scenario additionally fixes building spawns, choices and edits, replacing automatic growth/rewards. This is required because a video does not reveal the original RNG seed/state. The carrier seed -915001679 comes from the video hash, not score fitting. Strict rejected-event checks stop playback; referenceScore is display-only and never injected.

Measured checks:58 core suites pass (54 preceding fidelity suites,3 custom replay/validation suites,1 connection-erasure/refund regression). Unity player build pending. These are infrastructure/behavior checks, not proof of original parity.

Source recording: screen-capture (2).webm,1920x1200,last packet1012.202s,SHA256 c9762eb1d8c474c328b01f59a4a0ca744a0c8a06e2794e2dafe285712b1d4629. Last visible original score835. Original seed and demand phase unavailable.

Reconstruction: registered camera to50x30 numeric LA terrain; sampled images at1s video intervals; calibrated paused/1x/2x time to9 weekly140-second boundaries. Estimated last gameplay time1314s.51 candidate houses,14 destination events including shared/joined destinations; offers/choices, motorway edits, lights and roundabout manually checked. These counts are draft observations, not verified complete.

Chronological diagnostics:
- Road detector v4 used near-white pixels and missed roads under building shadows. First strict replay exposed duplicate erasure after a driveway rotation; normalized that duplicate because drawing the new driveway already removes the old stub.
- Next v4 replay failed at232.65 game seconds with8 trips,65/580 events consumed. This is an invalid comparison: roads were missing. Do not present8vs835 as simulator performance.
- Close-up inspection disproved an earlier hypothesis that gray early roads were deleted/retired; they are active roads darkened by building shadows. The shadow interpretation supersedes that hypothesis. Connection-erasure support remains necessary for actual recorded deletions, but these pixels do not establish retirement timing.
- Broader grayscale v5 detector also detected riverbanks/UI. Strict replay rejected event38 at106 seconds for exhausted road inventory. This trace is invalid, no comparison score.
- v6 masks near-water grayscale and screen UI; validation pending.

Limits: sampled timing, camera interpolation, occluded edits and unknown original RNG/demand phase prevent an exact-same-everything claim. Never skip rejected actions or add road stock to make a trace run. Preserve failed revisions and audit evidence. Raw video/frames/artwork, extracted private game files and generated binaries stay local under tmp; only our code, numeric annotations and small results belong here. No original art/decompiled code included.

## Subsequent checks and current result

v6 shadow/UI filtering produced a strict24-trip replay after the first cyan entrance annotation was corrected from right to left; a native left entrance stub is visible from video143. Two corrected headless v7 outputs match exactly (SHA256 ccce30fe7508e0d36fccec6fa957b2219a217e6cd4f08bde07f635e55bf85987). Corrected simulation game-over297.45s,84/780 events applied,24trips; original final835. Raw difference-811 is NOT a validated parity measurement. Original HUD at video170 is49. Original duration≈1314s versus early simulator end. All later events remain unvalidated.

At failure, red destination(10,8),layout2,served2,demand10,reserved4; cars waited142.2s and139.1s on lane clearance/entrance merge and entering car waited141.9s. Hypothesis: a dynamic carpark queue/clearance deadlock. A deliberately isolated static same-red-network control (all spawns/roads at time zero, different arrival sequence, no other destinations) serves22 through400s without failing; this contradicts any claim that layout2 always deadlocks. It does not clear the observed dynamic blockage. No traffic rule was changed in response.

Initial Unity build succeeded but player verification rejected recorded offers: the shared runtime offer model was not Unity-serializable. Replaced the scenario offer representation with serializable lowercase type/amount/roads fields and added offer/choice coverage to the fixture. Core58 suites pass again. Rebuild/player verification pending; do not install the rejected first build.

Archive: measurements/ holds numeric annotations, drafts, audit and controls; source/ holds our reconstruction and custom scenario code. Raw PNG/JPEG/video/private extracts and generated Unity logs/players stay local. Scripts refer to the local scratch folder and video path; rebuild terrain from existing CityCatalog and install local av/Pillow/OpenCV deps to reproduce extraction. No full camera/observation claim is inferred from source hashes or infrastructure checks.

## Verified feature and installed build

Corrected Unity rebuild passed. Headless example4/80s/5events matches Unity4/80/5. Unity recorded draft24/297.45/84 matches corrected headless, and normal Original seed12345 LA startup smoke passes20s.58 core suites pass. These checks certify loader/determinism/installed behavior, not the unvalidated future video events or original parity.

Installed corrected build at simulation/Builds/Windows/TrafficLabOriginal; installed and staged Assembly-CSharp SHA256 D4AB71D0AC869FA89498E3DE924E1DDBC3F451BA88A7F73AE76D6A9AAC2482AD. Previous installed app preserved locally in tmp/custom-video-scenario-2026-11-08/previous-installed-player. Generated binaries/logs are local-only. Player was closed during replacement. No commits/pushes or training.

Use the numeric seed textbox/Use seed for ordinary runs; JSON path/Load custom scenario JSON for reconstructed playback. [Usage, example and draft](../../../simulation/Scenarios/README.md). Draft is deliberately named recorded-la-draft.json. Full remaining annotations require validation; original hidden seed/state was not recovered. Current measured24vs835 is preliminary only; no simulator performance/parity acceptance or claim that all fidelity issues are fixed.

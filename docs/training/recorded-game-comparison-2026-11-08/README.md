# Recorded original-game comparison — 8 November 2026

## User request and current outcome

User requests the exact same seed, choices and timing replayed in our simulator and a final score comparison, with no further changes. Gameplay code/builds/settings are frozen as of this request. Analysis/scratch evidence and required durable documentation only; no training or model evaluation.

| Quantity | Verified result |
| --- | --- |
| Original final visible HUD score | **835** immediately before the game-over transition |
| Matched simulator score | **Not measured: exact scenario/replay is unavailable** |
| Score difference | Not computable without a valid matched run |
| Map | Los Angeles, identified visually from terrain; local profile lists Normal mode, but the recording does not show mode selection |
| Recording |1920x1200; last packet timestamp1012.202seconds (~16m52s), variable frame timestamps |

Source input is the user's C:/Users/moham/Downloads/screen-capture (2).webm,224730766bytes, SHA256 c9762eb1d8c474c328b01f59a4a0ca744a0c8a06e2794e2dafe285712b1d4629. File unchanged. Raw video, extracted frames/contact sheets and save/profile research stay local-only; no original artwork, profile identifiers or private extracts archived. Scratch path tmp/recorded-game-comparison-2026-11-08. Numeric observations/index/fingerprints retained here.

## Score correction and timing evidence

Initial10-second sampling saw826 at980.012 and1000.005 seconds; assistant prematurely described it as final. Fine inspection corrected that: user remains paused at826 through approximately1003.51, resumes, reaches827 by1004.529,829 by1005.008,832 by1005.514,833 by1006.027,834 at1007.228, then835 at1007.259.835 remains visible through1007.670 as HUD leaves during failure transition. Game-over screen appears at1010.012. These are video timestamps, not simulation-clock times.835 is the last visible HUD score at failure; recording ends before a separate result summary panel. Earlier826 claim is superseded, not a second outcome.

Numerous pauses and speed changes mean wall-clock video time cannot be used directly as game time. Full exact input/spawn/clock sequence has not been transcribed.102 ten-second sample frames and35 detailed final-transition frames were inspected, plus half-second ending samples; no claim of frame-by-frame full-game action extraction.

## Exact replay gate and local research

Read-only checked LocalLow Dinosaur Polo Club/Mini Motorways profile and logs, Steam app1127500 remote profile files, and existing private ReferenceRuns. Local profiles are UTF-16LE; correctly decoded rather than treating initial JSON parse failure as absence. No seed/replay/journal key found in those profiles or current/previous logs. Steam remote directory contained profiles/settings, not a current replay. Only an old25October London exploratory journal was found in existing private reference runs; it does not represent this game. This is a scoped search, not proof that no other backup exists anywhere.

Headless requireExact reset returned: Exact-original parity is not yet validated. OriginalReference remains under development. This existing guard is consistent with documented differing seed initialization/random call order/placement. Even recovering the seed would not alone produce the same evolving city in this simulator. No arbitrary seed, debug road builder, new layout or historical model score was substituted and labeled matched.

An asynchronous clarification asks whether a separately labeled reconstruction of visible spawns/timed choices would be acceptable if exact replication remains unavailable. No answer received at the time of this record; a pending question is not consent. No forced-spawn replay or simulation score generated. The requested exact comparison is incomplete, with explicit missing evidence/capability, rather than a failed score of zero.

## What would support a valid comparison

Exact original replay/journal/event data plus compatible importer/process/spawn implementation would support same-seed/state claims. Alternatively, user acceptance of a visible-event reconstruction would allow a separately labeled scenario replay, preserving uncertainty in grid coordinates, frame/clock timing and hidden RNG state. That is a different experimental condition and must not be called same everything. The recording must not silently become training data or a final evaluation holdout.

[Prior repairs and deployed version](../gameplay-fidelity-repairs-2026-11-08/README.md) records changes made BEFORE the freeze. Current installed player and source were not altered after this video request. Required documentation does not authorize further gameplay changes.

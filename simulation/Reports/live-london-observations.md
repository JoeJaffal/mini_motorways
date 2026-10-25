# Live London observations — 25 October 2026

Reference: installed Mini Motorways, `release-24-patch-3 (202609181350)` as shown in its Options screen. London, Classic. A new run was started through the normal UI. This was a visual exploratory session, not a synchronized replay or numerical motion trace.

Observed directly:

- The opening station has one colored destination and a dashed outline reserving the second destination.
- Rail passes through one edge of the station footprint; the destination sits in the middle row and parking is on the opposite edge.
- The train has three visible carriages and stops across the station platform.
- The opening red destination had one demand pin after the first observed station visit. No exact arrival timestamp was recorded.
- The opening red house showed two cars. Blue houses and a normal blue destination appeared as the run progressed through Wednesday.
- The initial inventory showed 30 road tiles and two bridges.

Interaction limitation:

Menu clicks, city selection, pause/resume and settings changes worked through the Windows computer-use tool. Repeated road drag attempts did not create roads or consume stock. No house-to-station trip, queue or crossing driving behavior was successfully measured. Do not treat these attempts as completed gameplay validation.

Draw Mode Toggle and Hold to Draw/Delete were temporarily tested, then restored to their original values (off and on respectively). The reference run was left paused in Options. No original game assemblies or assets were modified.

Replica comparison and fix:

The runnable Original app was inspected on all five city selections. In London its station destination overlapped the rail row and its car park background hid the track. The viewer now places the station destination in the middle row, draws rail above the lot background and shows the reserved second-destination outline. This changes presentation only; it does not certify station placement or traffic parity.

The rebuilt London app was opened and inspected again. The rail remains visible through the station, the destination occupies the middle row, the empty second slot is outlined, and the train renders on approach. The debug road builder connected the starting house. Both apps build and the 29 shared checks pass.

## Preserved original journal

The live game created an autosave journal during this session. A private copy is held under the local `MotorwaysResearch/ReferenceRuns` directory, outside the repository. The raw file contains device information and is not included in reports.

`scripts/inspect_reference_journal.py` validates the supported header schema, envelope sizes, object counts and matching header/body serializer hashes. It omits device strings and exports gameplay metadata only. The saved snapshot is London Classic at 39.900000037 simulated seconds with zero completed trips and 573 serialized simulation objects. The sanitized envelope report is `reference-london-journal-envelope.json`. This is an original simulation snapshot, but its object graph has not been decoded into vehicle/building state; it is not yet a live trace importer.

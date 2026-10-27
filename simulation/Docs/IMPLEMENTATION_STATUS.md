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

- Exact spawn placement, support-house logic, random draw ordering, seed initialization and fixed-point/process timing.
- Full motorway/traffic geometry, merge/conflict/rerouting rules and queue behavior.
- Weekly weighting/history, bridge/edit accounting and tunnels.
- Exact station placement, train stopping/motion, batch demand and crossing timing.
- Full original-journal graph import and controlled successive-state comparisons.
- Broader presentation/input differences. Independent viewer drawings are not original game artwork or UI.

`exactReplicaValidated` remains false, and `requireExact:true` refuses a reset. Internal tests show reconstruction consistency, not original-game equivalence. Numeric source hashes are in [REFERENCE_DATA.json](REFERENCE_DATA.json).

# Roundabout behavior follow-up — 8 November 2026

User reports roundabouts act very differently. Continued checks-only scope; no production or game changes, no learning. Existing installed-build private Roundabout and RoadChunkModel extracts inspected read-only. Private extracts not regenerated; installed assembly hash was checked in parent report. No synchronized original-game traffic measurement performed.

## Confirmed implementation differences

- Our MayEnter comparator uses CurrentLane.IsRoundabout, distance to target tile, then JourneyStarted and vehicle ID. Installed RoadChunkModel comparator first handles IsShoving, then its lane-topology-based IsVehicleOnRoundabout test, distance to chosen lane, and inbound registration timestamp. Our journey-start tie-break is not the same as arrival/registration time at a junction. Shoving priority is absent. These can change who yields and queue discharge. No measured score/throughput magnitude or guarantee of worse behavior.
- Ours approximates entry/exit connectors with cubic curves and conflicts by sample proximity (<0.13 tiles) within one tile, plus reconstructed crossing release. Original uses lane/chunk connectivity and traversing-vehicle tests. Previously researched circular radius does not establish matched merge behavior.
- Route planning cancels the 1.2 roundabout speed multiplier even though actual lane speed retains it. Graph costs use center-to-center distances rather than full sampled lane lengths. Confirmed representation difference inside our code, not independently demonstrated incorrect relative to original pathfinding.
- Placement AddRoundabout automatically links ring cells to every neighboring existing non-roundabout road without the original Roundabout.GetValidExitsForConnection directional-mask check. Original defines explicit valid/invalid exit masks. Some constraints may be implicit in our geometry; do not claim every generated link is illegal without checking the exact direction mapping.
- Conversion still accepts vehicles with retained committed old geometry; existing tests validate completion, not original conversion appearance/timing. Earlier road-stock audit establishes overwritten ordinary roads are not refunded.

## Fresh bounded topology fixture

Command `.\tmp\dotnet\dotnet.exe run --project tmp/roundabout-check-2026-11-08/Check.csproj`; two static topology observations, no world stepping, ~4.76 wall seconds including build. Exact scratch source archived in roundabout-source (relative csproj intended at original tmp path).

OriginalReference EmptyLab seed40, city growth disabled, explicit one-roundabout stock for isolated test. Center(15,15), existing ordinary corner road(14,14): placing roundabout gives corner degree2 automatically. North ring(15,14) to west ring(14,15) direct route has2 cells; reverse route takes west -> corner(14,14) -> north,3 cells. Thus outside corner road bypasses part of ring without an explicit drawn link. Whether original would permit this exact connection/shortcut is unverified; not a demonstrated commercial parity failure by itself.

After removing unused corner road, bare ring forward route has2 cells and reverse4, as expected for directed circulation. LaneSpeed=0.6 tile/s, while forward RouteCost=28 integer cost units, reflecting center-distance/speed cancellation and flooring; cost units are not seconds. This fixture checks topology/pricing representation only, not vehicle merging, acceleration, collision, saturation, or throughput.

Existing42 core suites passed earlier today; no need to rerun them for unchanged production code. Existing roundabout suites cover direction, radius/joins, moving conversion and six-car completion; they do not validate commercial merge capacity or prolonged saturated traffic.

## Interpretation

User experience is consistent with known material reconstruction differences; evidence is insufficient to isolate the specific observed behavior or rank its score impact. Next useful comparison is the same simple multi-approach layout in original and replica, recording arrivals, yielding, queue discharge and conversion transitions at controlled simulation times. No fix proposed as validated yet. Documentation/scratch checks only; installed game not launched, settings/saves untouched, no binaries/private extracts copied, no commit/push.

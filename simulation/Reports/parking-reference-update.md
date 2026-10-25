# Parking reference update — 25 October 2026

## Footage inspected

- [Fusionlit Games — full playthrough](https://www.youtube.com/watch?v=GKqlRgPVmM4): LA at approximately 0:41 and 5:00. The early close view shows the internal car park circulation and diagonal parking. The later sample includes multiple lots and a roundabout; no junction timing was measured from that frame.
- [BKRA Gaming — London Classic](https://www.youtube.com/watch?v=sybjBr59_hQ): opening station/house connection at approximately 0:32. The station has one destination, a reserved second slot, a rail platform and diagonal parking on the opposite edge.
- The earlier Real Civil Engineer train candidate, `Bbz9ivOeZDg`, identifies its opening chapter as Mumbai. It was excluded as a London-specific reference.

These were viewed through the browser player. No video files were downloaded. Footage speed, game version and seed are not controlled, so the observations are structural evidence, not exact motion measurements.

## Implemented changes

Original uses a connected internal parking graph rather than one direct curve from entrance to bay and back. Separate outer and inner circulation lanes connect the bay branches. Each bay has a diagonal parking segment with a midpoint stop, consistent entry/exit heading, and recovered one-third-tile spacing and geometric offsets. The graph supports three-bay single lots, nine-bay shared/station lots, both entrance ends and all four orientations.

The geometry and parking lifecycle were independently expressed using numeric rules inspected in the installed CarparkModel and ParkVehiclesProcess. No original source or assemblies are included in the reconstruction.

Full-lot arrivals now follow an internal circuit without occupying a bay. They count a delivery once the entry connector clears and internal circulation begins, then continue through the lot to their return route. A departing vehicle frees its bay after leaving the parking segment, before it finishes traversing the lot. Full lots with outstanding demand can release the longest-parked vehicle early. Normal Original dwell uses the strict elapsed-greater-than-three-second condition. Custom keeps its existing parking paths and timing.

The viewer paints diagonal bay markings and displays the parked vehicle's actual bay heading.

## Validation

- 31 shared simulation suites pass in .NET and Unity.
- New geometry checks cover every bay and entrance across single/shared lots in four orientations: lane joins, entrance/bay continuity, parking-strip confinement, heading and release markers.
- New integration checks cover full-lot circulation, delayed entry delivery, no duplicate score and bay release before lot exit.
- Existing oriented/shared-lot trip checks and Custom fixtures pass.
- Ten map/version headless protocol checks pass.
- Both Windows apps build successfully.
- Original app smoke checks pass on all five cities; Custom London smoke passes.
- The rendered LA app was inspected with debug roads: diagonal markings and parked cars are visible, and four trips completed during the exploratory visual run.

## Remaining limits

Entrance connectors still join our existing centre-based surface endpoints. Original uses boundary-based entrance lanes. Fixed-point spline rasterization and end-to-end motion timing are not matched. The reconstruction still serializes car park access conservatively, and shared-lot return trips retain their selected entrance rather than evaluating every possible exit. These affect capacity and journey duration. Exact original timing, queue behavior and whole-run parity remain unverified; `exactReplicaValidated` stays false.

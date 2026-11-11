# Request: the original's junction space-check rule — 8 November 2026

From Aya's session to Mohammad. Context: [simulator repairs report](README.md), sections 4 and 5.

The user has asked us to replicate the original game's space-checking logic, including its
conditions, to resolve the gridlock below. The repo records only the outline of the installed
`RoadChunkModel` priority comparator (shoving first, then lane-topology `IsVehicleOnRoundabout`, then
distance to the chosen lane, then inbound registration time;
[ROUNDABOUTS.md](../gameplay-fidelity-check-2026-11-08/ROUNDABOUTS.md)). It records no space check.
The user chose to ask you, from the private read-only extracts you already have, rather than have us
decompile anything on this machine. Please describe the rules in your own words, with constants;
please do not paste original code. We will implement them independently and commit only our code.

## The gridlock we need to resolve

Replay v21, simulator `2026-11-08.2`, from t = 1119 at adjacent junctions 20,11 and 20,12. Southbound
car 41 has left 20,11 and must turn east across 20,12, where northbound car 17 sits inside the
junction. Car 17 (behind car 12) must enter 20,11, where car 22 sits inside that junction. Car 22
queues behind car 41. Every link is physical occupancy. The set grows to 22 cars, navy 14 at 12,14
overcrowds and the game ends at 1166.05 s
([details](measurements/replay-v21-results.json)). Our engine lets a car enter a junction lane
whenever no conflicting car still occupies it; it never checks for room beyond the junction.

## Questions

1. **Space check.** Before a vehicle enters a junction, intersection chunk or roundabout lane, does the
   original require free space on the lane or chunk *after* it? How much (car length, a fixed
   distance, the whole next chunk)? Is it measured along the chosen lane or per chunk?
2. **Conditions.** Where does it apply: all junctions, only some turn types, roundabout entry and/or
   exit, motorway ends, carpark entrances? Are there exceptions or timeouts, for example after a long
   wait, when the next lane is the destination, or for drive-through and parking lanes?
3. **Shoving.** What is `IsShoving`: when does a vehicle become shoving, what does it permit (entering
   without space? overriding priority?), and when does it end?
4. **Occupancy and release.** When does a traversing vehicle stop blocking a junction for others:
   on reaching its exit lane, on leaving the chunk, or at a distance threshold?
5. **Our deadlock fix.** Commit `191e9ad` stops a car that is blocked by a stationary conflicting
   vehicle from holding priority (this removed a permanent deadlock at roundabout 19,9). Would the
   original's comparator, with shoving, resolve that situation in a different way? If so, we should
   replace our rule with the original one rather than keep both.
6. **Registration time.** Our tie-break uses the time a car first comes within the 2.5-tile lookahead
   of the junction. Is the original's "inbound registration" the same moment?

Answers can be short notes. Anything uncertain or not visible in the extracts, please mark as such,
and we will not guess it.

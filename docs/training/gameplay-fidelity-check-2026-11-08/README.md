# Gameplay difficulty investigation — 8 November 2026

User observation: usually high 800s in the Steam original, 200s in Traffic Lab. This is user-reported, not a paired measured comparison. User authorizes checks only; no gameplay fixes or learning. Previously accepted parking approximations do not establish acceptable difficulty parity.

## Fresh checks and provenance

Branch mohammad; pre-existing large dirty working tree preserved. Steam App.dll SHA256 76c9d9069d61160a5c20afa62d33c0272173ab46682db28214374e56b557c638 matches REFERENCE_DATA.json. Running app is simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe. Its Assembly-CSharp.dll timestamp is 28 October 2026 13:59:54; timestamp alone does not prove binary/source equivalence. Shared current-source self-test: PASS 42 suites. These are internal tests, not commercial difficulty validation.

Commands executed from repository root:

```
.\tmp\dotnet\dotnet.exe run --project simulation/Headless -- --self-test
.\tmp\dotnet\dotnet.exe run --project tmp/fidelity-check-2026-11-08/Check.csproj
```

Second check: four previously exposed LA diagnostic seeds 40–43, 8000 ticks each / 400 simulated seconds, explicit 120-second total wall stop. Completed all four in 12.215 seconds as reported by harness (excludes build). No optimizer/model/training. Reused historical crossing fixture: replenish roads to 1000 and build debug network every 10 simulated seconds; failure timer set to 100000 seconds in isolated worlds. These are privileged diagnostic controls, not changed production rules, normal-play performance, optimal networks, or evidence of attainable original scores. Trips 70/56/65/78 reproduce the historical traffic investigation.

measurements.csv preserves selected numeric outputs; source/ preserves exact scratch harness. Dictionary counters accumulate each tick's reported obstacle label across vehicles; units are vehicle-seconds, not player elapsed seconds. Labels may reflect the motion system's most recent obstacle classification; not a causal attribution or pure incremental delay estimator. Full stdout/time-series were returned in tool output but were not captured to a raw file. No graph/PDF produced.

## Confirmed differences and priorities

1. **Whole-lot serialization, high priority.** TrafficControl.cs MayEnter blocks outbound entry whenever another car in the same carpark is EnteringParking or LeavingParking. UpdateVehicles also gates parked departures on lot-wide accessBusy. This applies across shared entrances. Private installed-build ParkVehiclesProcess initiates departure after >3 seconds and requests a lane path without that same whole-lot stage gate; original lane traffic constraints still apply. Numeric check reports 391.45, 486.70, 397.70, 477.85 vehicle-seconds labeled Carpark access occupied. This confirms a substantial simulated restriction; it does NOT measure how many extra points removing it would produce. Parking route geometry and selected-return-entrance remain additional timing differences. Earlier accepted approximation is documented in IMPLEMENTATION_STATUS and DESIGN_DECISIONS; acceptance is not parity evidence.

2. **House supply and placement are a different algorithm, high priority.** CityDemand.UpdateCity tries at most one additional house per 20-second interval and skips a color at homes >= destinations*5. TrySpawnHouse ranks candidates toward six-tile distance and restricts distance to 3–18. Original inspected BuildingSpawningProcess schedules houses using demand/supply sufficiency (or city-house-curve rule branches); DemandModel contributions depend on distance and destination-count scale. Destination.IsSupplySufficient compares contributed supply times group scale against RequiredSupply. Our schedule does not reproduce this. No matched live original trace establishes magnitude or even direction for every city. Upgraded demand and uneven same-color travel make the substitute particularly worth investigating; causal score impact is a hypothesis.

3. **Demand/progression incomplete, confirmed but mixed direction.** OriginalSchedule explicitly skips non-destination plan items and uses separate supporting-house logic. Placement/random-call ordering differ. Original GenerateDemandProcess also balances delayed destination spawns into extra demand; no equivalent found in our UpdateDemand. Missing this feature can make some situations easier, so it cannot simply explain lower scores. Original initial interval has a 3-second branch near time zero versus our fixed FirstDemandDelay=4; small discrepancy, not evidence for a fourfold score loss. Current demand code's ramp cancellation is not a demonstrated double-ramp bug: interval includes inverse ramp and countdown reset multiplies it back.

4. **Failure/dispatch/traffic parity still open.** Installed failure logic has rules/time-dependent multipliers and fixed-point frame ordering, while ours uses simplified timer integration. Original parking chooses free bays randomly; our geometry and lane arbitration are reconstructed. No new causal magnitude is assigned without controlled traces.

## Conclusion and remaining evidence

There are material gameplay differences, especially a measured parking restriction and provisional supply generation. Passing 42 suites does not validate acceptable original-game difficulty; the 3 November fidelity audit explicitly limited itself to internal consistency. No evidence yet supports claiming these findings fully explain 800 versus 200 or that one fix would restore it.

Needed next: capture the failing user's simulator city/seed/network and compare isolated lot entry/exit throughput and same-color house-supply progression against the Steam game at controlled simulated times. The original was not launched or its save/settings altered during this audit. Existing private extracts were inspected read-only and remain outside Git under AppData/Local/MotorwaysResearch/PrivateExtracts. No original binaries, decompiled source, secrets or journals copied. Current installed assembly identity verified, but historical extracts were not freshly regenerated. No production code, scenes, binaries or game settings changed; only scratch diagnostic files and durable documentation added. No commit/push.

Follow-up: [road scarcity checks](ROAD_STOCK.md) confirm six-versus-five base connection cost in an isolated chain and lost ordinary-road stock on roundabout conversion/removal. Redraw and unused-road refunds pass. Pending rewards and route-wide retirement are additional possible contributors, with limits documented.

Roundabout follow-up: [priority, geometry and topology checks](ROUNDABOUTS.md). Confirmed comparator differences and automatic corner-road shortcut; bare directed ring passes. Original shortcut legality and throughput impact unmeasured. No gameplay change.

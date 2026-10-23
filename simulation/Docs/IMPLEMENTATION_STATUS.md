# Current implementation status - 24 October 2026

The authoritative current status is [VERSIONS.md](VERSIONS.md). It supersedes the 22 October single-version snapshot.

- Two isolated selectable rule sets: OriginalReference (default, unfinished) and Custom.
- Custom: roads 2, lights 5 additional, bridge water tiles 10, roundabouts 8; unlimited items, permanent spending, no motorways.
- Custom: 30-second grace; supply-screen rejection, no demand cap to rescue a scenario. Staying alive first; waiting/cost secondary; learning method and color penalty out of scope.
- Both run options: fixed map with varied events or varied maps/events; Los Angeles, Beijing and Tokyo cropped profiles.
- Original target: limited material stock, road reuse, bridge reservations and city-configured weekly material choices. No custom price, grace or feasibility rejection.
- Shared recovered car/road/parking/signal structures retain the approximations listed in VERSIONS.md. Original motorways, destination upgrades, complete map/expansion, exact spawning/resource accounting and live original parity tests remain unfinished.

Exact-original replication is the objective, not a completed result. The original target must not be described or evaluated as exact. All observations report exactReplicaValidated=false; requireExact reset requests are refused.

Private research still references installed Steam build 25381668, App.dll SHA-256 76C9D9069D61160A5C20AFA62D33C0272173AB46682DB28214374E56B557C638. Installed files were only read. The original process and asset provenance remain in the local MotorwaysResearch directory.

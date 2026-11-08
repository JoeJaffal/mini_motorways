# Simulator fix handoff for model re-evaluation — 8 November 2026

For the session that re-evaluates Evolved Rules (`gp4`) and PPO on the repaired simulator.
Full evidence: [simulator repairs report](../../docs/training/simulator-repairs-2026-11-08/README.md).

## Where it is

- **Branch:** `mohammad` in worktree `C:\Projects\490 - Project\mm-ppo`. The commits below are local
  only: not pushed (the fork `origin/mohammad` is at `1779c0b`, Mohammad's `upstream/mohammad` at
  `8a4b447`) and not merged anywhere.
- **Simulator version:** `2026-11-08.2`.

## Commits (in order, after Mohammad's `8a4b447`)

| Commit | Change | Gameplay/scoring? | Protocol? |
| --- | --- | --- | --- |
| `d586183` | Reward-v4 drift isolated to the rule-77 native join; new `reward-fixture-v5.json`; `test_rewards.py` points at v5 | No (test fixture only) | No |
| `517469d` | A car's current `Waiting` is cleared when it arrives home or parks | Yes, minor (traffic-light weighting starts from 0) | `waiting` values for home/parked cars |
| `1b27821` | `simulatorVersion` on every reply; `TrafficHost --version` | No | Yes, additive |
| `191e9ad` | A car blocked by a stationary conflicting vehicle no longer holds junction priority (removes a permanent roundabout/junction deadlock) | **Yes** | No |
| `615f08c` | Replay input v21 regenerated from the builder with the seven handoff corrections | No (replay data only) | No |
| next commit | Documentation, including this note | No | No |

## Which old results are invalid

**All Evolved Rules results.** `gp4`'s simulation core is byte-identical to `e6119eb` (28 October).
This branch adds Mohammad's 8 November fidelity repairs (`f7ce005`) as well as the commits above.
Results from `e6119eb` must not be reused or compared as if they came from the same simulator. Main
gameplay changes since `e6119eb`:

- **Movement:** a reference movement factor of 3 (cars much faster) and distance-weighted lookahead.
- **Construction:** concrete priced per connection, with refunds after traffic clears; roundabout
  concrete is conserved.
- **Demand and timing:** demand rates, per-colour supply cadence and demand/failure timing changed;
  weekly upgrade offers now use weighted offers (not-offered growth, milestones).
- **Parking:** carpark boundary/lane clearance, bay-merge reservations, an approach gate before the
  outside turn, and through-traffic across shared lots (doubled route cost, no delivery credit).
- **Roads and signals:** traffic-light phases kept for deleted connections until their cars clear;
  erased motorway-endpoint cells cleaned up later.
- **Native joins (rules 75 and 77):** a motorway onto a building's native driveway end attaches for
  free; two native stubs meeting at an empty cell join for free, including at spawn time. This alone
  changes ordinary games: the reward fixture went from 13 trips/game-over to 30 trips/game-over at
  305 s.
- **Junction priority (`191e9ad`):** changes decisions in heavy traffic and removes a deadlock form.

**PPO results** recorded on the 74-suite or older simulator are likewise historical: the native-join
rules and `191e9ad` change ordinary games. Old results stay valid only for the simulator they were
produced on.

## Headless protocol

Backward compatible from `e6119eb` to `2026-11-08.2`: no request or reply field was removed or
renamed, and the observation layout is unchanged. Additions:

- **`simulatorVersion`** (string) on every reply, including errors and `drawchoices`, and in the
  `--run-scenario`/`--verify-replay` summaries. `TrafficHost --version` prints it. Hosts built before
  8 November send no such field: treat its absence as "pre-versioning". Key caches on it; the value
  changes with any gameplay, scoring or observation-meaning change ([table](VERSIONS.md#simulator-version-string)).
- From Mohammad, since `e6119eb`: request `includeConnectivity` (reset) with replies
  `usefulConnectedHouses`/`usefulConnectivity`; command `drawchoices`; reply `networkVersion`; CLI
  `--run-scenario`.

**Semantics** ([README](../Headless/README.md)):

- Vehicle `waiting` is the current continuous wait (speed below 0.02 tiles/s, not counting bay time).
  Since `2026-11-08.1` it is 0 for cars at home or parked. The stale case was real but rare: 0 of
  about 317,000 home/parked samples before the fix.
- Observation `meanWaiting` is the mean, over all cars ever spawned, of cumulative waiting seconds. It
  only grows; neither agent reads it.
- `stage`, `speed`, `TrafficLight`, `Roundabout` and `upgrade` requests are unchanged in form.

**Things `gp4` must update:**

- **Verifier:** `evolved_rules/verify.py` builds `--verify-replay` from `git archive e6119eb`, the old
  engine. Point it at the new simulator before verifying new games. Recordings made on `e6119eb` will
  not reproduce on `2026-11-08.2`; this is expected, because gameplay changed.
- **Cache:** key results on `simulatorVersion`, and record it with each game next to
  `simulatorCommit`.

## Build and check commands (from the worktree root)

```
dotnet build simulation/Headless -c Release      # DLL used by Evolved Rules
dotnet simulation/Headless/bin/Release/net8.0/TrafficHost.dll --version   # 2026-11-08.2
dotnet run --project simulation/Headless/TrafficHost.csproj -- --self-test   # 79 suites PASS
dotnet build simulation/Headless -c Debug        # DLL used by PPO and the checks below
python scripts/verify_five_maps.py               # 10 runs PASS (rewrites simulation/Reports/five-map-protocol-checks.json)
cd training && python test_environment.py && python test_rewards.py   # 7/7 and 6/6; needs an existing tmp/ folder
```

All of these were run on source `615f08c` and passed.

## Not verified or still open

- **A physical gridlock is unfixed.** Cars can enter a junction without room to leave it; at adjacent
  junctions this can lock permanently. Replay v21 ends that way. The user chose to replicate the
  original's space-check rule once Mohammad describes it; `simulatorVersion` will change when it lands.
- **Unity:** the Original player has not been rebuilt with these changes.
- **Original parity:** exact parity, hidden RNG and action timing are unverified;
  `exactReplicaValidated` is false. Replay scores (v21: 570 trips) are partial diagnostics, not a
  comparison with 835.
- **Parallel hosts:** the 10-host 0x800705AA crash has no host-side cause in measurement (about 56 MB,
  177 handles and 8 threads per host). It was not reproduced. Eight hosts remain the safe setting
  observed.

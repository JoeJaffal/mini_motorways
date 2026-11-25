# Growing-city road preflight

Run from the Linux training checkout on `mohammad`.

```bash
cd /home/mohammadjaffal/mini_motorways
bash training/verify_city_road_pilot.sh
```

The launcher builds a Release host into a fresh directory under the ignored `output/` tree. It runs a scripted seed-2004 verification game through the Gymnasium interface. The fixture places four connections from the first home's approach to its matching destination, then waits through normal city growth and native game-over. The route is a fixed test input and is independent of the adapter's legal action mask. The launcher performs no training.

## Interface

The adapter reuses the published visible-state encoder on the full native 50 × 30 map. Its action space is Wait plus one canonical action per neighboring edge. The new native query allows ordinary dry-road connections with the current stock, visible bounds, existing parcel access and native diagonal rules. Bridges, rail-crossing draws and upgrades are outside this road-only action space. Edits run while paused. Wait advances at most one second and stops at a pending weekly offer. The adapter takes the real offer that grants the most concrete and returns the native trip increment as reward. It keeps the weekly choice automatic until tool training.

## Verified outcome

The native Los Angeles fixture began with two buildings, 25 road units and zero roads. Four builds consumed four units without advancing time. The city recorded its first delivery at second 13, grew to 11 buildings, and received 20 road units at second 140. The simulator ended the game at second 212.1. Total Gymnasium reward matched the 14 native scored trips. Across six nearby and independent seeds a separate probe executed 157 masked draws and checked that querying the mask left the observed simulator state unchanged. The existing 14-test construction and visibility suite and 99 native simulation suites passed. [Launcher log](preflight.log).

The successful preflight verifies the native game loop and the road-only adapter. Existing training checkpoints use other action or observation shapes. Selecting a compatible starting checkpoint and measuring a frozen full-game baseline are the next milestones before the PPO pilot.

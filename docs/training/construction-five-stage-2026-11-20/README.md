# Five-stage construction curriculum

The user authorized completing the adjacent-gap, unfinished-bend, driveway-rotation, full clear-land road and blocked-detour exercises in a single project, with a record of each run and fix. The existing shared-edge checkpoint and earlier run directories were preserved. The exact previous training source is archived locally at `output/training/pre-five-stage-source.6z5jzT/source.tar`.

The new opt-in native exercise interface uses the original paused draw, driveway, inventory, traffic and scoring mechanics. It introduces only test scenario geometry, an explicit driveway choice for that exercise, and a native legality query guarded to this curriculum. Obstacles are blocked dry terrain. Models receive visible geometry and native legal masks, without reference edits. All named fixtures use a 12×12 arena. After construction, the native simulator advances automatically to 180 seconds or game over. The task gate is at least three deliveries on at least 90 of 100 held-out layouts per exercise.

| Exercise | Fixture |
|---|---|
| Adjacent | Two missing links touch a bare tile within a straight or diagonal route, two road units. |
| Bend | Two prebuilt stubs have different headings and two or three missing links. |
| Driveway | A road spur is attached to the wrong side of the house in three quarters of layouts. The remaining quarter already works. Choose one rotation or Finish. |
| Clear | House and shop on clear land, no supplied roads, varying distance and offset. |
| Obstacle | A two-tile blocked patch lies on the direct route, with space to go around. |

Training and validation use disjoint seed ranges and separate destination placements. The scripted arm follows only the private reference edits built into these test fixtures and verifies native deliveries. The frozen and learned arms may use any legal sequence that actually delivers. The reference query is used for the scripted arm and training demonstrations and is excluded from policy inputs and rollout actions during evaluation.

Early feasibility smoke covered 30 validation layouts per stage and produced at least three native deliveries on all 150 known routes. The full phase uses 100 held-out layouts per stage. The previous shared-edge actor is an explicit frozen baseline. It lacks a driveway rotation action, so its driveway control is reported separately from model accuracy.

## Frozen baseline and feasibility

The scripted arm passed 100/100 on all five exercises. The original frozen policy passed the adjacent-gap gate at 100/100. It reached 51/100 unfinished bends, 33/100 clear-land roads, and 0/100 blocked detours. It has no driveway rotation action. The 25 already-correct driveway controls delivered as they stood; the 75 rotation-required cases served none. The limited local repair scorer remains available as a baseline. [Scripted summary](scripted-summary.json), [scripted games](scripted-games.json), [original frozen summary](legacy-summary.json), [original frozen games](legacy-games.json).

The first combined training run uses masked behavior cloning, since multi-edit binary reward would discard the available supervised signal from verified examples. This is an engineering choice under the requested curriculum training, and is separate from the historical Maskable-PPO runs. Actor inputs are visible road, blocking, parcel and driveway planes, relative geometry to the visible approach points, road stock, edit budget, and exercise identity. The visible destination driveway provides a consistent board orientation. A shared spatial network scores actions. No shortest path, future deliveries, or teacher data enter the model during play. Adjacent-gap demonstrations rehearse the already-passed skill while the other four develop in one checkpoint.

## Run-by-run summary

| Run | What was tried | Result |
|---|---|---|
| Native Release build and targeted checks | Validated host capabilities, rotation/action-ID round trips, blocked endpoint exclusion, and the difference between Rotate and Finish. | Build had no warnings or errors; all three targeted checks passed. |
| Scripted smoke | Ran the reference construction on 30 validation boards per stage. | 150/150 produced at least three deliveries. |
| Full scripted feasibility | Tested edit budgets and timed native deliveries on 100 held-out boards per stage. | 500/500 passed, in 32.2 seconds. |
| Original frozen baseline | Applied the best local shared-edge checkpoint to the five exercises. | Adjacent 100/100, bend 51/100, driveway 25 starts already served with no rotation available, clear 33/100, obstacle 0/100. Took 37.1 seconds. |
| `imitation-01` | Trained one orientation-aligned spatial scorer on 512 scripted layouts per stage, 7,171 labeled legal actions in total. Fresh weights, RTX 2080 Ti, AdamW, seed 42, 36 epochs. | Training accuracy was 71.3% in epoch one and 100% by epoch five. Dataset collection and training took 33.5 seconds total. No PPO updates in this run. |
| `imitation-01-greedy` | Froze the trained checkpoint and chose its highest-scoring legal action. | 500/500 passed, in 36.5 seconds. |
| `imitation-01-sampled` | Froze the same checkpoint and sampled legal actions with a fixed per-layout CPU seed. | 500/500 passed, in 36.7 seconds. |

## Final acceptance

Each stage had 100 distinct held-out layouts. Both policy modes passed at least three native deliveries on every layout. All successful games survived to 180 seconds. Taken together the two runs represent 500 distinct layouts and 1,000 plays, since the same layouts were reused across modes.

| Exercise | Old frozen | Final highest-probability | Final sampled | Mean deliveries |
|---|---:|---:|---:|---:|
| Adjacent gaps | 100/100 | 100/100 | 100/100 | 11.24 |
| Unfinished bends | 51/100 | 100/100 | 100/100 | 11.18 |
| Driveway rotation | 25 already correct; rotation unavailable | 100/100 | 100/100 | 11.35 |
| Full clear-land roads | 33/100 | 100/100 | 100/100 | 11.52 |
| Blocked detours | 0/100 | 100/100 | 100/100 | 11.34 |

In both modes the final policy deliberately left 25 correct driveways alone and corrected all 75 wrong driveways. It used at most two actions for adjacent gaps, three for bends, one for driveways and six for full road and obstacle cases. Aggregate delivery scores ranged from 10 to 13, with a mean of 11.326 per layout. All action sequences and scores matched the scripted reference on this fixture suite. The frozen policy path does not request reference actions. These experiments establish learned reproduction on the five tested fixture families, including their held-out seeds and positions. Unseen template families, more complex terrain, and autonomous Wait decisions remain outside this result.

The fixes were explicit native Rotate and Finish choices for driveway practice, a blocked-aware native mask scoped to these fixtures, and a shared spatial scorer with a larger view than the old local edge scorer. Existing simulation physics and ordinary practice actions were retained. The prior source archive and unchanged checkpoints preserve historical evaluation. The single learned checkpoint is locally saved under `output/training/construction-five-stage.MasJ47/imitation-01/latest.pt`. Weights, generated native binaries and complete raw output are local. No training or evaluation remains active.

[Training settings](imitation-01-config.json), [training progress](imitation-01-progress.json), [highest-probability results](greedy-games.json), [sampled results](sampled-games.json), [verification and timing](verification.json).

## Reproduction

From the project root, build the .NET headless host into a new artifact directory, then use its generated DLL. For a frozen check, select a fresh output directory.

```bash
dotnet build simulation/Headless/TrafficHost.csproj -c Release --artifacts-path output/construction-curriculum-host
host="$PWD/output/construction-curriculum-host/bin/TrafficHost/release/TrafficHost.dll"
.venv/bin/python training/construction_curriculum.py sampled \
  --dll "$host" \
  --checkpoint output/training/construction-five-stage.MasJ47/imitation-01/latest.pt \
  --output output/training/construction-curriculum-recheck
```

Checkpoint validation requires the native host build hash to match; use the recorded local host at `output/training/five-stage-host.xrTqaW/bin/TrafficHost/release/TrafficHost.dll` if rebuilding on another toolchain changes it. Use the archived exact pre-change source in a fresh directory with the original release host for strict historical checkpoint reproduction.

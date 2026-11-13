# AlphaZero traffic agent

The model integration now runs against the merged simulator through the rebuilt
`simulation/Headless/bin/Debug/net8.0/TrafficHost.dll` (simulator
`2026-11-10.1`, gameplay rules from `2026-11-08.7`). Existing checkpoints were
trained on earlier simulator versions; they can be evaluated on this host, but
their weights have not been updated. Exact resume rejects a changed host hash;
use `--init-checkpoint` when training on the new simulator later.

New experiments train on **Los Angeles only**, using distinct random game seeds.
Validate on **Los Angeles / 200000** after every **three** training episodes.
Reserve **Los Angeles / 300000** for testing only when explicitly requested.
Both held-out seeds are excluded from training. See the
[single-city protocol](SINGLE_CITY_TRAINING.md) for cadence and continuation.

Current congestion shaping adds `0.1 * completed_trips * (1 - blocked_fraction)`
and subtracts `0.02 * blocked_fraction * elapsed_seconds`, with +10 base reward
per trip and existing penalties. Blocked means an active car waiting at least
two seconds; Home/Parking cars are excluded. No deliveries means no bonus.
Configure with `--clear-trip-bonus`, `--congestion-fraction-penalty` and
`--congestion-wait-threshold`. Historical checkpoint evaluation defaults the new
coefficients to zero. Both MCTS and real gameplay use the same reward settings.

The agent uses structured observations, a candidate policy/value network and single-agent PUCT over headless simulator transitions. Every real policy decision still advances 20 ticks. See [the design plan](alphazero_implementation_plan.md) and [the controlled recovery experiment](RECOVERY_EXPERIMENT.md).

New to the project? Read the [implementation and onboarding guide](ONBOARDING.md) for the architecture, training loop, saved experiment results, checkpoint behavior and replay workflow.

## Components

| File | Responsibility |
| --- | --- |
| `actions.py` | Route and local gameplay proposals, explicit command/tool features |
| `proposals.py` | Observed-state edit history, configurable cooldowns, deduplication and native preflight |
| `environment.py` | JSON protocol, reward components, independent snapshots and replay fallback |
| `alphazero.py` | Grid encoder, variable candidate policy, value head, MCTS and mixed replay learner |
| `train.py` | Episode collection, actual modifications, reversals, returns and value diagnostics |
| `experiment.py` | Controlled training, atomic checkpoints, frequent evaluation and stopping rules |
| `evaluate.py` | Policy-only evaluation, search-budget comparisons and an explicit held-out test split |
| `loss_ablation.py` | Identical-data normalized MSE/Huber comparison on an unseen training seed |
| `baseline.py` | Goal heuristic; native legality and cooldowns enabled unless `--raw-proposals` is supplied |
| `check_recovery.py` | Preflight, partial draw, cooldown, gradient, replay and truncation regressions |

The encoder has 42 grid channels and 19 scalar features. The 26 candidate features distinguish command/tool types, coordinates and upgrade offers. Scheduled spawns and random diagnostics are excluded from network inputs.

## Legal candidates and search

`validateActions` applies proposals to disposable simulator clones without advancing time or mutating the live city. Production actions and preflight use the same C# command dispatcher. Rejected and no-effect requests are removed before the policy or MCTS sees them. An accepted draw that changes only part of the requested stroke remains eligible; actual observations determine subsequent actions and costs.

Driveway proposals require new service, recovery from blocked access or queue relief. Motorway edits require a better surface connection. Default cooldowns are 20 seconds for driveway changes, 30 for motorway changes and 10 for construction reversals; direct driveway reversals are blocked for 60 seconds. They can be configured through `--driveway-cooldown`, `--motorway-cooldown`, `--construction-cooldown` and `--reversal-window`. A blocked driveway can bypass its cooldown. Search copies this observed history into each branch and follows new motorway IDs from returned observations.

The independent search host restores a checked snapshot for every simulation. Counterfactual traffic uses a separate random stream and resampled pending events. This future sampler is approximate and needs further distribution validation. PUCT uses value-scale-normalized Q scores. Training adds root exploration noise; evaluation does not. Logs include actual depth reached, root actions visited, runtime and policy/search action differences.

### Parallel search on CPU cores

Training, evaluation and checkpoint visualization accept `--search-workers N` and
`--torch-threads N`, both defaulting to 1. Search workers are Python threads with
independent .NET simulator processes; the simulator computation can run on
different CPU cores. There is one live host plus one host per search worker.
`--torch-threads` controls PyTorch's internal CPU computation threads, not CPU
affinity or the simulator worker count. Start with 2 or 4 search workers and one
PyTorch thread to avoid excessive CPU contention.

```powershell
.venv\Scripts\python.exe mbrl/evaluate.py `
  --checkpoint output/mbrl/recovery-20261101/controlled-v3/checkpoint-best.pt `
  --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll `
  --dotnet tmp/dotnet/dotnet.exe `
  --simulations 32 --search-depth 4 --search-workers 4 --torch-threads 1 `
  --output output/mbrl/parallel-evaluation.json
```

Add the same worker/thread arguments to `train.py` or `visualize.py`. The rollout
budget is **total per decision**: 32 simulations with four workers still means
32 completed rollouts. One worker uses the serial search algorithm. Multiple
workers use a shared tree and deterministic batches: the coordinator reserves
paths with temporary visit counts, workers execute on isolated cities, and the
coordinator applies results in reservation order. Existing snapshots and
reset-and-replay branching are supported. Guards and future streams remain
separate from the live city. Worker exceptions propagate after pending jobs are
drained; extra hosts are closed when the run exits.

Batch reservations can choose different paths from serial search. Results are
repeatable for fixed seeds, worker count and settings, independently of completion
order; changing worker count is an experiment change, not a promise of identical
actions or improved score. Source/config records include worker/thread settings,
and search traces include completed rollouts, executed transitions, actual depth,
worker count, peak active workers and batch count. Frozen `--source-dir` controls
only support one worker. Live-view callbacks run on the coordinator after each
batch; display delays and rendering can still reduce throughput.

Use a saved-state benchmark to measure local scaling without running whole games:

```powershell
.venv\Scripts\python.exe mbrl/benchmark_search.py `
  --checkpoint output/mbrl/recovery-20261101/controlled-v3/checkpoint-best.pt `
  --trace output/mbrl/controlled-20261104-205734/traces/train-7-LosAngeles-100006.json `
  --decision 120 --workers 1 2 4 --simulations 32 --search-depth 4 --repeats 3 `
  --dotnet tmp/dotnet/dotnet.exe `
  --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll
```

The benchmark replays the recorded prefix without its original search, restores
the same full city and edit history, warms the hosts, resets Python proposal caches
for each timed sample and alternates worker-count order. Setup/replay and warm-up
are excluded. It records root/source/host/checkpoint hashes, visits and transition
counts as well as median/max elapsed times. With no trace it constructs a baseline
prefix on a development city. London is excluded. Fixed budgets can still execute
different paths/transition counts; this benchmark measures latency, not game quality.

Local measurement on 7 November 2026: Los Angeles/100006 at decision 400
(30 buildings, 48 vehicles), fixed 32 rollouts and depth 4, one PyTorch thread,
three timed repeats. All three worker settings executed 60 hypothetical
transitions per search in this case:

| Workers | Median search time | Speedup versus one |
| --- | ---: | ---: |
| 1 | 3.625 s | 1.00x |
| 2 | 2.399 s | 1.51x |
| 4 | 1.765 s | 2.05x |

The local report is `output/mbrl/parallel-benchmark-20261106-221442.json`
(UTC filename). This is one restored-state latency measurement; full-episode
speedup and gameplay quality were not established.

Parallel regression checks:

```powershell
.venv\Scripts\python.exe mbrl/check_parallel_search.py --dotnet tmp/dotnet/dotnet.exe --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll
```

## Learning and rewards

The reward is `tripReward*trips + clearTripBonus*clearTripUnits - congestionFractionPenalty*congestionFractionSeconds - alpha*waitingSeconds - lambdaCost*modificationCost - betaCongestion*congestionSeconds - failurePenalty*failure - unansweredPenalty*unansweredRequestSeconds - overcrowdingPenalty*capacityPressureSeconds`. The waiting/modification/congestion coefficients now default to `0.05`, `0.01` and `0`; `--failure-penalty` defaults to 10 and `--unanswered-penalty` to 0.01. Failure is charged once on natural game loss, excluding healthy time cutoffs. Request-seconds are final observed destination demand (including reserved requests until delivery) times actual elapsed simulated seconds. Counters cover the whole action-plus-step interval. Modification cost uses observed tile/link/motorway/driveway changes and does not credit delayed refunds. New components and coefficients are recorded in traces/checkpoints; current evaluation uses saved values or the new defaults when absent, with explicit penalty overrides available. Historical frozen-source evaluations retain their original rules. `--overcrowding-penalty` defaults to 0.05 for new training: add `elapsed * sum(max(0, demand - demandCapacity + 1))` times this weight as a penalty. It starts at capacity, increases per excess request, stops below capacity, and uses each destination's actual capacity. For example, 6/6 costs an extra 0.05/second, 7/6 costs 0.10, and 8/6 costs 0.15. Saved checkpoint modification weights are preserved during evaluation; missing historical overcrowding weights mean zero. Use evaluator `--lambda-cost .01 --overcrowding-penalty .05` to explicitly compare the new rewards. Both weights and `capacityPressureSeconds` are recorded. There is no extra overlap-specific ban. Three spatial risk inputs are now included: capacity, demand/capacity and overcrowding time.

Both destination loops now consider up to 20 destinations instead of 8. The five-house cutoff, local 20-center budget, 48-candidate cap and neural input schema are unchanged. See [handwritten rules](limitations/HANDWRITTEN_RULES.md) for the current formulas and limits. Existing weights have not been retrained by this code change.

Search/candidate defaults are now **16 rollouts and 48 final candidates** per decision, with a raw proposal pool of 128. The depth cap remains 4. Explicit `--simulations 8` still requests eight; use `--simulations 16` for the new budget. Training validation remains policy-only unless `--evaluation-budgets` includes a positive budget. Network weights remain compatible, and mixed historical 24-row/new 48-row replay is padded during training.

Search now first compares up to four distinct root actions: wait, the highest-prior alternative, then preferably other command/tool families. Each receives one rollout before normal PUCT uses the remaining budget. With 16 rollouts this leaves 12 after a four-action opening. Parallel workers reserve different opening actions and complete that phase before normal search. Traces log each visited root action's prior, visits and mean return; progress logs report comparison counts. This guarantees a few alternatives are tested, rather than exhaustive coverage of 48 choices.

Mandatory opening visits are now excluded from action-selection and policy-target weights: a required one-visit inspection does not itself make an action desirable. Ordinary subsequent visits provide the support distribution; raw visits/Q remain in diagnostics. Training still samples from the corrected search policy, and MCTS evaluation selects its maximum. Tiny probe-only budgets fall back to original priors among visited actions. Logs distinguish raw `visits`, `searchSupportVisits` and `policyWeight`; config records `rootPolicyMode=post-comparison-visits-v1`.

Local connections now receive the extra `+2` proposal priority only when an active vehicle currently occupies either existing endpoint road. At-home and parked vehicles do not qualify; stopped/queued active vehicles do. Otherwise priority is base urgency alone. This uses current endpoint occupancy, not historical use or a guarantee that the new connection helps.

Value targets use full observed trajectory returns, with discount `0.999` per one-second decision and a default value scale of 100. Both collection and MCTS bootstrap external truncation consistently. `--value-loss huber` is the default; `mse` is available for controlled comparisons. `optimizer.jsonl` records policy loss, normalized value loss, raw value RMSE, separate shared-encoder gradient norms, gradient cosine and total gradient norm.

Permanent demonstrations receive 35% of replay draws, recent episodes 40% and successful trajectories 25%. Successful trajectories reference the stronger recent episodes for each training city. Missing pools redistribute their weights. Recent replay is bounded by `--replay-states`, default 6000. Defaults are 128 optimizer updates per demonstration and 64 per training episode, with batch size 32.

## Run and stopping

From the repository root, install `requirements.txt` and .NET 8, then:

```powershell
dotnet build simulation/Headless
dotnet simulation/Headless/bin/Debug/net8.0/TrafficHost.dll --self-test
python mbrl/smoke.py
python mbrl/check_agent.py
python mbrl/check_recovery.py
python mbrl/train.py --episodes 6 --validation-seeds 2 --validate-every 1 --evaluation-budgets 0
```

Use `--dotnet .\tmp\dotnet\dotnet.exe` with the workspace SDK. A short wiring check can use `--cap-seconds 5 --episodes 1 --bootstrap-updates 2 --updates-per-episode 2`; it cannot assess policy quality.

For historical replay, pass the archived host explicitly, for example
`--host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll`. For new work,
build the current host and use the default Debug DLL. `--host-dll` overrides
`TRAFFIC_HOST_DLL`, selects both live/search hosts and records the host hash.
The current host supports exact command replay for snapshots and preflight;
these operations become slower as the episode history grows. `forkFuture` is an
approximate search sampler, not an exact conditional simulator distribution.

Each episode ends on natural game failure or at `--cap-seconds` (default 1800). Training stops at its episode budget or after `--patience` validation rounds without improvement, after `--min-episodes`. Defaults are six episodes and patience zero (early stopping disabled). New experiments validate only after each three completed training examples; there is no initial validation or incomplete-final-group validation. Add budgets such as `--evaluation-budgets 0 16` for repeated MCTS validation, or use the separate budget sweep to bound compute.

New experiments use Los Angeles with distinct random training seeds, fixed validation seed 200000, and deferred test seed 300000. Both held-out seeds are excluded from training. Episode checkpoints and the latest state are saved; validation ranks are diagnostic and the latest weights are selected. No best-model checkpoint is created. Outputs include source snapshots and hashes, action traces and component metrics. `--init-checkpoint` is a model warm start. `--resume-demonstration` plus `--demonstrations` restores an episode-zero model, optimizer and RNG state without repeating demonstrations; use `--resume <checkpoint-last.pt> --bootstrap-episodes 0` for full continuation from new-format checkpoints, including optimizer, all replay pools, RNG and episode position.

## Evaluation

```powershell
python mbrl/evaluate.py --checkpoint <checkpoint.pt> --simulations 0 --validation-seeds 2 --output <policy.json>
python mbrl/evaluate.py --checkpoint <checkpoint.pt> --budgets 0 8 32 64 128 --search-depth 8 --cap-seconds 1800 --output <budgets.json>
```

Evaluations default to 1800 simulated seconds per game, ending earlier on natural game failure. Budget comparisons use identical validation seeds and a common horizon. Shorter runs require an explicit `--cap-seconds` override. Saved traces keep their original duration; evaluating to a longer horizon requires a new run and a separate output path. `--split test` opens the checkpoint's reserved test seed explicitly (London for historical city-split checkpoints) and permits only one locked budget; test outcomes cannot select checkpoints. `--source-dir` evaluates a frozen implementation for a historical control.

## Watch the model in Unity

`visualize.py` opens the **Traffic Lab Original Unity app** and runs the model through the existing headless hosts. The window shows the real trajectory on the left and, with `--view-mcts`, the current hypothetical search branch on the right. Unity draws the observations returned by the hosts; it does not run another traffic simulation or choose actions. This also avoids requiring the renderer's simulation code to match a historical training host.

For the checkpoints already in this workspace:

```powershell
.venv\Scripts\python.exe mbrl/visualize.py `
  --checkpoint output/mbrl/recovery-20261101/controlled-v3/checkpoint-best.pt `
  --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll `
  --dotnet tmp/dotnet/dotnet.exe `
  --simulations 16 --search-depth 4 --view-mcts --cap-seconds 1800
```

Use `--simulations 0` and omit `--view-mcts` to watch the policy alone. The default city is the validation city, Dar es Salaam, seed 200000. Choose `--map` and `--seed` for another case; choosing London explicitly opens held-out test data. New visualization runs default to 1800 simulated seconds, ending earlier on natural game failure, and do not train or update the checkpoint. Replaying a saved trace preserves its recorded duration.

The Unity executable defaults to `simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe`. Supply `--unity-exe <path>` for another build. Older players must be rebuilt once to include `Assets/Viewer/ModelLiveViewer.cs`; a startup handshake detects a player without this support. In Unity, use **Traffic Lab > Build Original Windows app**, or build from PowerShell:

```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe' `
  -batchmode -nographics -quit -projectPath "$PWD\simulation" `
  -executeMethod ProjectSetup.BuildOriginalWindows -logFile "$PWD\output\unity-build.log"
```

The current recovery models require the recovery headless build shown above. The default `simulation/Headless/bin/Debug/net8.0/TrafficHost.dll` in this checkout lacks the newer snapshot/preflight protocol. Use the host that produced a run when replaying it; divergence stops replay instead of presenting an inaccurate trajectory.

Unity controls include pause/resume computation, separate main-decision and search-node delays, grid, wheel zoom, middle-drag pan, and clicking cars/buildings for waiting, blockage and demand. The sidebar shows the real selected action, reward components, value estimate and candidate scores. Scores mean policy probabilities for policy-only runs or corrected root search-policy weights for MCTS. Branch labels include the root decision, rollout number, depth, simulated time and immediate branch reward. Hypothetical rewards are separate from the actual trajectory. Search futures use the learner's existing approximate future sampler.

Live frames are observed at decision boundaries, normally one simulated second apart. Search frames are observed at each restored root and each branch transition. `--view-delay` and `--search-view-delay` control wall-clock pacing; both default to 0.1 seconds. Viewing does not consume agent RNG or modify rewards, candidates or simulator state, but rendering and pacing increase wall time. Closing the Unity window allows computation to continue.

### Watch training or evaluation

Add `--live` to the normal commands, and add `--view-mcts` to see their searches. The same Unity window follows demonstrations, training and evaluation episodes as they start. For this workspace, first select the matching host:

```powershell
$env:TRAFFIC_HOST_DLL = (Resolve-Path output/mbrl/recovery-20261101/host/TrafficHost.dll).Path
.venv\Scripts\python.exe mbrl/train.py --live --view-mcts --simulations 16 --dotnet tmp/dotnet/dotnet.exe
.venv\Scripts\python.exe mbrl/evaluate.py --checkpoint output/mbrl/recovery-20261101/controlled-v3/checkpoint-best.pt --live --view-mcts --simulations 16 --output output/mbrl/watched-evaluation.json --dotnet tmp/dotnet/dotnet.exe
```

These are separate commands: training starts a new training run; evaluation watches a saved model. Viewing is disabled by default for ordinary training/evaluation. Frozen implementations selected with `evaluate.py --source-dir` cannot use the new callbacks; visualize their saved traces instead.

### Revisit decisions and reward ideas

Standalone viewing saves `output/mbrl/visualization/run.trace.json`, `run.session.json` and `run.html`. Training/evaluation with live viewing saves session/HTML companions beside each saved trace. Each session retains every main decision and the latest **512 search states**, to bound search memory. A Unity live window stays on its final frame after Python ends; its live folder also contains an archive. To reopen an archive in Unity:

```powershell
& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe `
  --model-session "$PWD\output\mbrl\visualization\run.session.json"
```

Saved Unity sessions support play/pause, single decisions, speed changes, a main timeline and an independent search-history slider. The retained search states carry their original root decision and rollout labels. Older command traces can be rendered without loading a model:

```powershell
.venv\Scripts\python.exe mbrl/visualize.py --trace <trace.json> --host-dll <matching-TrafficHost.dll> --dotnet tmp/dotnet/dotnet.exe
```

An old trace contains real actions only; it cannot recover the original MCTS rollouts or unrecorded candidate scores. `--no-live` generates the archives without opening a window. `--output <name.html>` changes their location.

The optional browser inspector (`--viewer browser`, then open the printed localhost URL) adds reward-weight previews and timestamped **Reward / Penalize / Investigate** notes for main or search states. Export notes as JSON to keep them. Its HTML archive works offline. Weight previews re-score the recorded trajectory only; they neither change training nor predict a retrained policy's behavior.

Verification:

```powershell
.venv\Scripts\python.exe mbrl/check_visualization.py --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll --dotnet tmp/dotnet/dotnet.exe
node mbrl/check_viewer.cjs
```

The first checks action/outcome isolation, MCTS root restoration, fractional horizons, replay divergence, Unity packet/archive contracts and browser pause/resume. The second exercises browser rendering/control logic without npm dependencies. Unity sessions can also be parsed and validated by the built player using `--model-session <file> --model-verify -batchmode -nographics`.

The original 10-episode run did not beat its 58-trip heuristic baseline. Its demonstration-warmed model scored 56 mean trips, episode 5 scored 33.5 and episode 10 scored 20, with or without eight-simulation MCTS. Those controls and ongoing recovery results are stored under `output/mbrl/recovery-20261101/`. The historical [MuZero report](TRAINING_REPORT.md) does not describe the current learner.


## Current learning update — 7 November 2026

- New training rewards each completed trip with **10**, configurable with
  `--trip-reward`; other reward coefficients are unchanged. Raw trip counters and
  displayed scores remain unscaled. Traces/config record `tripReward`.
  Historical checkpoints without this field evaluate with trip reward 1 unless
  explicitly overridden; frozen-source runs retain their original behavior.
- Schema **traffic-risk-v3** has **42 grid channels**, 19 scalars and 26 candidate
  features. Channels 39–41 are destination capacity / 10, demand / capacity, and
  overcrowdedFor / 50, rasterized across destination footprints, zero on houses
  and masked outside playable bounds. Ratios are not clipped at 1. Positive
  capacity and a finite nonnegative timer are required. Only current observations
  are used. The divisor 50 matches OriginalReference; another ruleset needs an
  explicit schema review.
- Serial and parallel PUCT use the current node value for unvisited actions;
  parallel pending work also uses that baseline. Raw measured Q/visit logging and
  the opening-visit policy correction remain in place.
- Warm-start migration copies all 39 historical first-convolution input weights
  and zero-initializes the three added channel weights. Existing predictions are
  preserved initially, and the added weights remain trainable. All other layer
  shapes are unchanged. Reward changes require fresh matching replay; legacy
  tensors are not silently reinterpreted as risk-aware observations.
- Training saves `checkpoint-last.pt` and per-episode full states, selects the
  latest weights, and creates no best-model checkpoint. Validation rank history
  remains diagnostic. Patience defaults to 0. Existing historical files are kept.
- `--resume <checkpoint-last.pt> --bootstrap-episodes 0` restores complete replay,
  optimizer, Python/NumPy/PyTorch RNG and episode position with compatible schema,
  reward, search, training and simulator settings. Successful replay is derived
  from restored recent episodes; city ordering is sorted for reproducible draws.
  `--init-checkpoint` remains an explicit weights-only warm start.

Checks: return-offset invariance and useful construction in serial/parallel search,
feature sensitivity/masking, legacy prediction preservation, trainable new input
weights, reward multiplier, replay/optimizer restoration and native split-versus-
uninterrupted training equality. These checks do not establish a 300-trip score.

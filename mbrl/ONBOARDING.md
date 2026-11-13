## Current behavior - saved AlphaZero restored, 12 November 2026

User clarified restoration of earlier AlphaZero. Saved WIP e53f3bb core and matching host API restored; default snapshot branch/native preflight/search-only future forking. Incoming f23 gameplay and reward counters retained (host2026-11-12.f23-alpha1). The recovered host implements snapshots and preflight by C# history replay, not instant state cloning. Native checks pass, but100-history2-rollout search took28.9seconds; no practical-speed or quality claim. No production training restarted. [Source/checks/limits](../docs/training/alphazero-restore-2026-11-12/README.md). The no-snapshot/replay-only descriptions below are superseded historical records.

## Current training path - 12 November 2026

User revoked native snapshots. Active training/evaluation use deterministic reset-and-replay, with no saveSnapshot/loadSnapshot, forkFuture or validateActions requirement. Candidate acceptance occurs on execution; prior preflight and alternate-future descriptions below are historical. Simulator reporting counters restored in 2026-11-12.training1. Three tiny training rounds plus validation and one resumed round passed; full-episode speed/quality unmeasured. See [current commands and evidence](../docs/training/replay-training-ready-2026-11-12/README.md). Older details below describe earlier implementations where superseded.

**Traffic agent implementation and onboarding guide**

Current experiment protocol: **Los Angeles only**, random distinct training seeds,
one validation seed (**200000**) after each three training episodes, and one test
seed (**300000**) reserved until explicitly requested. Both held-out seeds are
excluded from training draws. See [SINGLE_CITY_TRAINING.md](SINGLE_CITY_TRAINING.md).
Results and references to the earlier multi-city split below are historical.

Reviewed against the working tree and saved experiment artifacts on 4 November 2026; host integration updated on 10 November 2026 for simulator `2026-11-10.1`. The current host provides replay-backed snapshots and native action preflight. Older model weights remain historical until trained on this simulator. Saved source snapshots and historical reports can describe earlier implementations.

**What the project does**

The agent constructs and edits a traffic network in the repository's `OriginalReference` simulation. Cars move automatically; the agent selects construction, demolition, driveway, motorway and upgrade actions. It learns a policy for choosing actions and a value estimate of future reward, and can use Monte Carlo tree search (MCTS) before committing an action.

The model is implemented in Python/PyTorch. A persistent C#/.NET process executes the traffic simulation. Unity renders manual games or observations from the headless hosts. Training and evaluation do not require Unity or the commercial Mini Motorways game.

`OriginalReference` has finite construction inventory and evolving city demand. The separate Custom simulator has different rules and is not the training environment. This reconstruction is not validated as an exact replica of the commercial game.

The current learner searches the real simulator implementation. It does not learn a dynamics model. The old `TRAINING_REPORT.md` describes a historical MuZero implementation and is not the current architecture specification. `legacy/cpp/` is also separate from the active training stack.

**Code map and reading order**

| File or directory | Responsibility |
| --- | --- |
| `protocol.py` | Fixed city/seed split and checkpoint ranking |
| `environment.py` | JSON host connection, filtered observations, rewards, episode limits and search branches |
| `actions.py` | Deterministic route/edit proposals and candidate features |
| `proposals.py` | Duplicate removal, action-history guards and simulator preflight |
| `alphazero.py` | Neural network, PUCT search, replay mixture, return targets and optimizer step |
| `train.py` | One episode's action loop, samples, metrics and action recording; delegates CLI training to `experiment.py` |
| `experiment.py` | Demonstrations, training, validation, checkpoint selection and stopping |
| `evaluate.py` | Fixed-model evaluation, paired search budgets and explicit test access |
| `baseline.py` | Handwritten candidate-priority policy |
| `loss_ablation.py` | MSE/Huber comparison with identical demonstrations and a separate calibration trajectory |
| `live_view.py`, `visualize.py`, `viewer.html` | Live observation delivery and saved replay visualization |
| `report_experiment.py` | Summaries generated from saved measurements; check their generation time |
| `simulation/Assets/Simulation/` | Shared C# traffic simulation |
| `simulation/Headless/` | JSON command host |
| `simulation/Assets/Viewer/ModelLiveViewer.cs` | Unity rendering of observed main/search states and archived sessions |

**One real decision**

1. Read the current simulator observation.
2. Construct useful candidate actions from the visible network and current demand.
3. Apply history guards, remove duplicate requests and ask the host to preflight the actions on disposable copies.
4. Encode the state and candidate features for the neural network.
5. Choose the highest-probability candidate directly, or run MCTS and choose using the corrected root search policy. Training samples choices rather than always taking the maximum.
6. Execute one gameplay command in the live host, then advance 20 simulation ticks, normally one simulated second.
7. Calculate reward from the whole command-plus-time interval, update edit history and record the result.
8. Repeat until game failure or the evaluation time limit.

A rejected gameplay command still consumes its decision interval. `wait` advances time without issuing a construction command. A multi-tile road stroke is one decision, not one decision per tile. The final interval can be shorter to reach a fractional time limit exactly.

There are three different time/count concepts: a real decision, a hypothetical MCTS rollout and wall-clock execution time. A rollout does not advance the live game. More rollouts increase calculation time, not the amount of live gameplay per decision.

**Observation representation**

The canvas is fixed at 50 columns by 30 rows. The network receives a `42 x 30 x 50` grid, 19 scalar features and a padded candidate matrix. This is structured simulator data, not screenshots.

| Grid channel group | Channels |
| --- | ---: |
| Terrain, infrastructure, connection bitfield, building colors/kinds, demand, reservations, pending removal | 8 |
| Rail occupancy, vehicle density, playable-area mask | 3 |
| Individual road-link directions | 8 |
| House driveway directions | 8 |
| Destination entrance directions | 8 |
| Motorway endpoint presence and opposite-end coordinates | 3 |
| Waiting traffic density | 1 |
| Destination capacity, load ratio and overcrowding timer | 3 |
| Total | 42 |

Values are scaled; counts/densities have explicit normalization and some clipping. Cells outside the currently playable bounds are masked. Scalar features include time, completed trips, motorway count, current total demand, building/vehicle counts, six inventory counts, upgrade-offer count and features for up to two offers.

The encoder explicitly selects current-state fields. Future scheduled spawns and RNG diagnostics are not policy inputs. The action proposer also uses current building/vehicle and network data. Information is richer than a rendered screenshot, so describe experiments as structured-state agents.

**Action representation and candidate generation**

The policy scores a maximum of 48 candidates at each decision. Candidate identity and ordering can change between observations; output index 5 is not a fixed global action.

The generator proposes waiting, upgrade choices, road/bridge strokes, local road/bridge construction, traffic lights, roundabouts, demolition, explicit road connections, driveway changes, motorway creation, motorway endpoint edits and motorway removal.

Road proposals use weighted path search between compatible houses and destinations, respecting entrances, driveways, playable terrain, occupied parcels, existing links and stock. Existing roads are cheaper in the path heuristic. Bridge crossings and rail crossings receive additional path costs. Paths become short straight strokes, with alternatives where available. Demand and waiting vehicles identify locations for local edits. Candidate selection reserves room for available command/tool families before filling by heuristic priority.

Each candidate has 26 numerical features: nine action-kind indicators, five tool indicators, four coordinates, urgency/length/stock features, three upgrade-offer features, an identifier feature and the handwritten priority. Batches pad to `48 x 26`; a boolean mask disables padding.

The network learns how to rank proposed actions. It cannot choose an action that the proposer did not offer, and the heuristic priority is itself a model input. Improvements must therefore be attributed across both learned weights and changes to the proposal machinery.

`proposals.py` first asks for up to 128 raw candidates, applies guards and canonical duplicate removal, then calls `validateActions`. Rejected or no-effect actions are filtered, with wait explicitly retained. Accepted partial road strokes remain eligible: actual simulator state changes determine their cost and outcome.

Default history guards are 20 simulated seconds for driveway changes, 30 for motorway changes, 10 for construction reversals and 60 for immediate driveway reversals. Rejected requests are temporarily suppressed. A blocked driveway has recovery exceptions. Search branches clone these histories so hypothetical edits do not contaminate the real episode.

**Neural network**

For the default hidden width of 128, the model has 524,546 trainable parameters. There is one shared state encoder and separate policy and value heads.

| Stage | Implementation |
| --- | --- |
| Spatial encoder | Conv `42 -> 32`, kernel 5, stride 2, padding 2; ReLU; Conv `32 -> 32`, kernel 3, stride 2, padding 1; ReLU |
| Grid embedding | Flatten `32 x 8 x 13`; linear projection to 128; ReLU |
| Shared state embedding | Concatenate the 128 grid features and 19 scalars; linear `147 -> 128`; ReLU |
| Candidate policy head | For each candidate, concatenate state and 26 action features; linear `154 -> 128`; ReLU; linear `128 -> 1` |
| Value head | Linear `128 -> 128`; ReLU; linear `128 -> 1`; multiply by the configured value scale |

The policy head produces masked logits, converted to probabilities. The value head estimates discounted future shaped reward, not final trip count alone. There is no recurrent network or learned transition head. Edit history is maintained outside the network by the guards.

Current training uses value scale 100. The bare `Network` constructor retains a legacy default of 10, so code loading a checkpoint must use its saved `config.valueScale`.

**Reward, score and checkpoint ranking**

The per-decision training reward is:

```text
reward = 10 * completed_trip_delta
       + 0.1 * completed_trip_delta * (1 - blocked_fraction)
       - 0.02 * blocked_fraction * elapsed_seconds
       - 0.05  * waiting_seconds_delta
       - 0.01  * modification_cost
       - 0.0   * congestion_seconds_delta
       - 10.0  * natural_failure
       - 0.01  * unanswered_request_seconds
       - 0.05  * capacity_pressure_seconds
```

The coefficients are configurable through `alpha`, `lambdaCost` and `betaCongestion`. Waiting and congestion are accumulated counters; the reward uses their deltas. Modification cost counts actual changed infrastructure cells, changed links, motorway identity/removal-state changes and changed house driveway directions. Delayed inventory refunds do not earn a negative construction cost. The diagnostic `spendingDelta` is separate from this reward component.

Natural failure now incurs a one-time penalty of 10; healthy time cutoffs and protocol errors do not. Undelivered demand incurs 0.01 per request-second, using final observed demand times actual elapsed time. Demand already includes reservations until delivery. Configure these with `--failure-penalty` and `--unanswered-penalty`; trace components and checkpoint config preserve the settings. Current checkpoint evaluation uses saved settings or these defaults if absent. Frozen-source runs preserve historical rewards. There is no separate positive survival-time reward. Capacity pressure is now penalized using `elapsed * sum(max(0, demand - demandCapacity + 1))`, with `--overcrowding-penalty` default 0.05 for new training. Thus 6/6 costs an additional 0.05/second, 7/6 costs 0.10, and the penalty stops below capacity. This uses actual per-destination capacities and supplements the unanswered-request penalty. Modification cost now defaults to 0.01. Existing checkpoint modification weights are preserved and absent historical overcrowding weights default to zero during evaluation/visualization; the evaluator accepts explicit overrides. Both destination loops consider 20 destinations; the other candidate limits and input schema remain as documented in [the rules](limitations/HANDWRITTEN_RULES.md).

Displayed score is completed trips. Checkpoint selection ranks the mean completed trips across validation games first, then lower accumulated waiting, then lower modification cost. It does not rank training loss or survival time first. Historical documents with other ranking definitions should not override `protocol.aggregate_rank`.

**MCTS implementation**

Search uses single-agent PUCT. The policy supplies action priors; the value head estimates unexpanded futures. Each edge stores a prior, visit count and cumulative return. Selection uses:

```text
Q / value_scale + 1.5 * prior * sqrt(parent_visits + 1) / (edge_visits + 1)
```

The implementation allows up to two sampled stochastic outcomes per action. Each expansion draws a future seed and executes that action in an independent simulator host. Existing outcomes are revisited using their recorded seed, with an equality check on the resulting observation. Returns back up as `reward + discount * child_value`; there is no alternating-player sign flip.

`SnapshotBranch` saves the current real root in the second host, restores it before each rollout and advances the saved root only when a real action is committed. `ReplayBranch` is an alternative that resets and replays real action history to recover the same root, with a larger restore cost.

`forkFuture` resamples pending future events using an independent stream. This avoids handing the real future schedule to the search policy, but its stochastic future sampler remains an approximation that needs validation.

The simulation budget is total rollouts per real decision. Search depth is an upper bound in decisions, not a promise every rollout reaches that depth. A newly expanded outcome ends the current rollout with a value estimate. Small rollout budgets can therefore produce shallow search.

The first up to four rollouts now compare distinct root requests: wait, the highest-prior non-wait action, then alternatives favoring different command/tool families. Original policy priors order these comparisons; root noise still governs subsequent PUCT. Fewer legal requests or a smaller budget reduce the target. Parallel workers reserve different initial requests and finish all initial comparisons before normal search. Logs contain root comparison counts and per-action visits/mean returns; this does not guarantee useful service coverage or comparison of every candidate.

Training adds 15% root exploration noise using concentration 0.3 and samples from root support visits after subtracting mandatory opening visits. Evaluation adds no root noise and chooses the largest corrected policy weight, with deterministic tie breaking. Policy-only evaluation chooses the highest policy probability. Training defaults to sixteen rollouts and maximum depth four; separate evaluation sweeps have used depth eight.

**Training and optimizer loop**

The fresh experiment seeds action/optimizer Python, NumPy and PyTorch RNGs with 1000, initializes the network and Adam optimizer, and trains on random Los Angeles seeds from a separate logged sampler. Bootstrap demonstrations default to zero; there is no initial validation or validation-baseline run. Optional demonstrations receive 128 updates each.

The experiment collects up to six agent episodes by default, applies 64 updates after each episode and validates on Los Angeles seed 200000 after every three training examples. These defaults are configurable. Demonstration actions teach through one-hot policy targets; agent trajectories use the corrected MCTS root support distribution as targets.

| Training setting | Current experiment default |
| --- | ---: |
| Batch size | 32 |
| Learning rate | 0.0003 |
| Adam weight decay | 0.00001 |
| Gradient norm clipping | 5 |
| Discount per decision | 0.999 |
| Value scale | 100 |
| Policy/value loss weights | 1 / 1 |
| Value loss | Huber; normalized MSE available |
| Recent replay target size | 6,000 states |

Policy loss is cross-entropy against the demonstration/corrected-search distribution. Value targets are full discounted observed trajectory returns. A natural game failure has a zero terminal bootstrap. An external time cutoff bootstraps from the network's estimated remaining value rather than treating the healthy city as a terminal failure. The value loss compares prediction and target after dividing both by the configured value scale.

Replay draws nominally come 35% from permanent demonstrations, 40% from recent episodes and 25% from stronger recent trajectories for each training city. Empty pools redistribute their weights. Pool selection is followed by uniform episode and state selection, so this is not simply a uniform draw across all stored states. Successful trajectories reference recent replay rather than forming an independent permanent archive. Recent eviction happens by whole episode, retaining at least one episode, so 6,000 states is not a strict cap on a single long episode.

`optimizer.jsonl` tracks losses, raw value RMSE, separate policy/value gradient norms on the shared encoder, gradient cosine and total gradient norm. Episode metrics include trips, duration, waiting, modifications, invalid requests, reversals, achieved search depth and search overrides. These distinguish better policy performance from better loss fitting.

**Train/validation/test split and stopping**

| Role | Cities | Seed allocation |
| --- | --- | --- |
| Training | Los Angeles, Beijing, Tokyo, rotating | `100000 + episode_index` |
| Demonstrations | Same three training cities | Separate offsets; default first seed 150000 |
| Validation | Dar es Salaam | 200000 onward; normally two seeds |
| Final test | London | 300000 onward; normally two seeds |

Validation selects checkpoints. London is reserved for an explicitly requested final test and cannot select search budgets. Merely specifying London in a standalone visualization also opens test data, so it must be treated as test access rather than an ordinary development case.

Default experiment stopping is at most six training episodes. Validation patience is disabled by default. `--patience 0` disables that early-stopping criterion. This experiment-level stopping rule is separate from one game's failure/time limit.

Training, evaluation and newly generated visualization games currently default to a maximum of 1,800 simulated seconds (30 simulated minutes). They end earlier if the city fails. The previous budget sweep explicitly used 300 seconds (five simulated minutes); its files remain historical 300-second results. The time limit says nothing about elapsed computer time. The low-level `TrafficEnv` constructor still has a 300-second fallback for callers that omit its argument; the main entry points supply their own horizon. Frozen source snapshots also retain their original defaults.

Use the same horizon, seed set, rules, checkpoint and implementation for a paired search comparison. A 300-second trip total cannot be compared directly with a game's eventual score after more than 800 seconds.

**What is saved, and what restarting means**

| Artifact | Contents and use |
| --- | --- |
| `checkpoint-last.pt` | Latest model, optimizer, complete replay, RNG, configuration and episode position; use this for continuation |
| `checkpoint-demonstration.pt` | Demonstration-stage model, optimizer and Python/NumPy/PyTorch RNG state |
| `checkpoint-episode-N.pt`, `checkpoint-last.pt` | Training-stage model, optimizer, RNG state and episode metadata |
| `demonstrations.pt` | Permanent demonstration replay |
| `config.json` | Run settings, host/source hashes and output locations |
| `training.jsonl`, `validation.jsonl`, `optimizer.jsonl` | Episode, evaluation and update measurements |
| `selection.json` | Chosen checkpoint and experiment stopping reason |
| `traces/*.json` or `*-trace.json` | Initial scenario/seed, real gameplay commands and outcome checks |
| `*.session.json`, `*.html` | Observed-state archive and portable visual replay |
| `source/`, `*-source/` | Implementation copies for provenance; older snapshots may lack current viewer callbacks |

Evaluation requires an explicit `--checkpoint`; there is no automatic selection of the previous model. It loads weights, starts a fresh city and does not update the network. Increasing the horizon cannot extend an existing recording: a new evaluation is required.

`train.py --init-checkpoint ...` loads weights for a new training experiment. It creates a new optimizer and replay setup. This is a warm start, not exact continuation.

`--resume-demonstration ... --demonstrations ... --bootstrap-episodes 0` restores the supported episode-zero demonstration state, optimizer, RNG states and permanent demonstrations. `controlled-v3` used this path from `controlled-v2`. New-format checkpoints support `--resume <checkpoint-last.pt> --bootstrap-episodes 0`: model, optimizer, replay, RNG and episode position are restored. Reward/schema/settings must match. Historical checkpoints without replay require a weights-only warm start.

Training requires a new output directory. Evaluation writes recorded traces and can reuse an exactly matching completed evaluation according to saved settings and provenance; use separate output names when changing the horizon or experiment settings.

**Current saved experimental evidence**

The following measurements are local development results, primarily on just two Dar es Salaam validation seeds.

| Experiment stage | Measured outcome |
| --- | --- |
| Historical old learner | Validation mean 56 after demonstrations, 33.5 at episode 5, 20 at episode 10 |
| Historical original heuristic | Mean 58 trips |
| Current-generator heuristic controls | Mean 100.5 without guards, 80 with guards; proposal changes matter |
| Normalized MSE/Huber demonstration policies | Both averaged 211.5 trips: 286 and 137 on the two validation seeds |
| `controlled-v2`, initial model, one MCTS validation game | 288 trips, seed 200000, natural failure at 823.45 simulated seconds |
| `controlled-v3`, initial policy-only model | 278 and 137 trips; mean 207.5 |
| `controlled-v3`, final episode-3 policy-only model | 268 and 137 trips; mean 202.5 |
| `controlled-v3` selection | Initial episode-zero model retained; stopped on validation patience after three agent episodes |
| Historical 300-second budget sweep | Mean trips: 44.5 for policy-only, 43.5 for eight rollouts, 44.5 for 32 and 64 rollouts |
| Latest saved 128-rollout trace in that sweep | Seed 200000, 45 trips at the 300-second cutoff; city still alive |

The 288-trip game itself had 44 completed trips at 300 seconds. Its full-game score and the latest 45-trip cutoff are therefore compatible observations, not evidence of a collapse to 45 eventual trips.

`budget-sweep.json` contains completed paired summaries only through budget 64. There is a 128-rollout first-seed trace, but no saved second-seed trace or completed 128 paired summary in the inspected artifacts. `final-selection.json` and `final-test.json` do not exist. `controlled-v3/selection.json` explicitly defers the test. A stale generated `EXPERIMENT_REPORT.md` predates completion of `controlled-v3`; prefer the stage-specific logs and selection file for its actual status.

These measurements do not establish improved self-play learning: in `controlled-v3`, the extra training did not beat its initial checkpoint. They also do not establish a consistently beneficial search budget or general performance on unseen cities. Simulator parity, future sampling and small validation coverage remain material limitations.

**Running in this workspace**

Use PowerShell from the repository root. Dependencies are Python with NumPy/PyTorch, .NET 8 and, for graphical playback, the built Unity Original player. `mbrl/requirements.txt` declares NumPy and PyTorch. This workspace already has `.venv/Scripts/python.exe` and `tmp/dotnet/dotnet.exe`.

The historical recovery models require the recovery host. Select it before calling training/evaluation scripts:

```powershell
$env:TRAFFIC_HOST_DLL = (Resolve-Path output/mbrl/recovery-20261101/host/TrafficHost.dll).Path
```

Environment variables must be set before Python imports `environment.py`. Training and evaluation also accept `--host-dll`, which overrides the environment variable and explicitly selects both simulator processes. Prefer that option in copied commands. The default built Debug host in this checkout lacks protocol operations needed by the recovery code. Reset checks required observation counters and rejects an incompatible host with a helpful error. Do not rebuild/replace a historical run's host and assume it is interchangeable; preserve the matching binary and hashes.

To evaluate the same model and 128-rollout/depth-eight setup as the latest recorded game, but with the requested 1,800-second horizon, run:

```powershell
.venv\Scripts\python.exe mbrl/evaluate.py `
  --checkpoint output/mbrl/recovery-20261101/loss-ablation-v2/checkpoint-mse.pt `
  --simulations 128 --search-depth 8 --validation-seeds 2 `
  --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll `
  --cap-seconds 1800 --dotnet tmp/dotnet/dotnet.exe `
  --output output/mbrl/recovery-20261101/budget128-1800.json
```

This is a new paired evaluation, not training or continuation of the old city's process. It may require substantial wall time. It was not started while preparing this guide. To evaluate policy-only instead, set `--simulations 0` and use a different output name. To compare several budgets in one invocation, replace the single budget with `--budgets 0 8 32 64 128`; use the same 1,800-second horizon throughout.

To start a fresh training experiment with the current defaults and explicit settings:

```powershell
.venv\Scripts\python.exe mbrl/train.py `
  --episodes 6 --validation-seeds 2 --validate-every 1 `
  --evaluation-budgets 0 --simulations 16 --search-depth 4 `
  --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll `
  --cap-seconds 1800 --dotnet tmp/dotnet/dotnet.exe
```

This initializes a new model unless a supported checkpoint option is supplied. It measures baselines and demonstrations before agent episodes. Training on the GPU is optional (`--device`); traffic simulation and search still use the CPU.

**Watching existing games**

An observed session opens directly in Unity without running a model or another simulation. The two prepared archives are:

```powershell
& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe `
  --model-session "$PWD\output\mbrl\visualization\saved-288-trips.session.json"

& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe `
  --model-session "$PWD\output\mbrl\visualization\saved-latest-45-trips.session.json"
```

These sessions have play/pause, decision stepping and timeline inspection. Their companion HTML files open offline in a browser.

An older action trace contains commands rather than every observed frame. Convert it using the matching host, which replays the recorded commands and checks acceptance, time, trips, dispatch totals and inventory where present:

```powershell
.venv\Scripts\python.exe mbrl/visualize.py `
  --trace output/mbrl/recovery-20261101/budget-sweep-128-200000-trace.json `
  --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll `
  --dotnet tmp/dotnet/dotnet.exe
```

This reruns recorded actions to reconstruct their observed states; it does not ask the model to choose again. Divergence stops playback. The viewer's new-run time limit does not change trace duration. A trace cannot recover hypothetical branches or candidate scores that were never recorded.

For future runs, `evaluate.py --live` or `train.py --live` saves observation/session companions while showing the computation. Add `--view-mcts` to observe search as well. Unity is the default viewer; `--viewer browser` serves the inspector at the printed localhost URL. `visualize.py --checkpoint ...` creates a new model run, while `--trace ...` reconstructs a previously recorded run. These are different operations despite sharing a script.

Live rendering is observational. It changes wall-clock pacing, not the chosen actions, rewards or simulator RNG. Archives retain all main decisions but only the latest 512 search states. Saved Unity sessions do not need a model checkpoint or Python to view them.

**Verification and practical first steps**

Read `protocol.py`, then follow one `run_episode` through `TrafficEnv.step`, `proposals`, `predict/search` and `train_batch`. Use a prepared replay to connect logged actions to network changes. Then inspect `controlled-v3/config.json`, `validation.jsonl` and `selection.json` before interpreting model quality.

Existing checks cover synthetic model/feature behavior (`smoke.py`), encoding/reward/snapshot isolation (`check_agent.py`), preflight/partial draws/cooldowns/loss behavior (`check_recovery.py`), viewer action isolation/replay/controls (`check_visualization.py`) and browser rendering (`check_viewer.cjs`). Run host-dependent checks against the intended host, not an unrelated default build:

```powershell
.venv\Scripts\python.exe mbrl/smoke.py
.venv\Scripts\python.exe mbrl/check_agent.py --dotnet tmp/dotnet/dotnet.exe
.venv\Scripts\python.exe mbrl/check_recovery.py --dotnet tmp/dotnet/dotnet.exe
.venv\Scripts\python.exe mbrl/check_visualization.py `
  --host-dll output/mbrl/recovery-20261101/host/TrafficHost.dll `
  --dotnet tmp/dotnet/dotnet.exe
node mbrl/check_viewer.cjs
```

This guide inventories the checks; it does not claim a fresh full-suite execution. Model structure/parameter count, checkpoint contents, saved selections and the cited trace scores were inspected while preparing it. Both prepared action replays were verified against the recovery host earlier in this session.

Keep weights, host binary/hash, source snapshot, proposal/guard settings, reward coefficients, seeds and horizon together when comparing results. Treat a protocol error as an integration failure, a time cutoff as truncation and overcrowding failure as termination. Those are different outcomes and should remain distinguishable in reports.


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

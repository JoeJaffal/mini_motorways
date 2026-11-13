# MuZero training implementation report

**Status:** The .NET 8 SDK and CPU PyTorch are available on this machine. Real-host training and baseline trials have run. The guided short trial matched, but did not beat, the goal baseline on two Dar es Salaam seeds. This report describes the code and its approximations; it does not claim a top policy or parity with the commercial Mini Motorways game.

## 1. Objective and fixed city split

The agent trains against the repository's `OriginalReference` reconstruction. The user chose goal-based road proposals and this outcome priority: **survival time, completed trips, lower waiting, lower construction cost**. OriginalReference has finite item stock rather than Custom's cumulative point cost. The current fourth metric is a provisional material-use proxy: occupied infrastructure cells plus active motorways. The four evaluation measurements are kept separate and ranked lexicographically.

| Role | Cities | Seeds | Code use |
| --- | --- | --- | --- |
| Train | Los Angeles, Beijing, Tokyo | `100000 + episode index` | Rotate the three maps; collect experience and update weights |
| Validate | Dar es Salaam | `200000 ...` | Evaluate deterministically every `--validate-every` episodes and at the end; select the best checkpoint |
| Test | London | `300000 ...` | Evaluate the selected checkpoint once, after selection; compare with the goal baseline on identical seeds |

The split is fixed in [`protocol.py`](protocol.py). `train.py` has no map override that can accidentally add the validation or test city to training. Seed blocks cannot overlap for permitted run sizes. The same validation seeds are reused across checkpoints, which makes checkpoint comparisons consistent but can encourage tuning to that validation set. London is not sampled, searched, scored or used for checkpoint selection until the best checkpoint is fixed. London has rail behavior absent from the three training maps, so its result is a stringent transfer test. A single held-out city cannot estimate performance on all unseen cities.

This split answers a generalization question. It does **not** measure the best achievable policy when all five cities are available for training; that would be a separate later experiment with new test seeds.

## 2. Files and environment contract

| File | Implemented role |
| --- | --- |
| [`environment.py`](environment.py) | Persistent .NET JSON-line host, reset/step contract, filtered observation encoder and vector outcomes |
| [`actions.py`](actions.py) | Goal proposals and translation to normal construction requests |
| [`muzero.py`](muzero.py) | Neural model, latent tree search, replay targets and optimizer step |
| [`train.py`](train.py) | 3/1/1 experiment, checkpoint selection, final test and AI replays |
| [`baseline.py`](baseline.py) | Nonlearning goal heuristic for training/validation cities, without PyTorch |
| [`smoke.py`](smoke.py) | Fake-host contract and split checks |
| [`requirements.txt`](requirements.txt) | NumPy and PyTorch dependencies |

The wrapper launches one `simulation/Headless` process and exchanges one JSON object per line. Each episode resets with `version=OriginalReference`, an explicit city, `variation=SameMap`, and a seed. It checks that construction is material limited. The policy can choose only `wait`, `draw`, `build`, `driveway`, `motorway`, `editMotorway`, `removeMotorway`, or `upgrade` requests; the present proposal generator emits **wait, draw, motorway and weekly upgrade** actions. Reset, `step`, `reference`, diagnostic labs and privileged stock grants are outside the model action space.

Every selected action advances **20 simulation ticks**, or one simulated second at the game's 0.05-second tick. Construction commands do not advance time by themselves, so the wrapper calls `step` afterward even if construction was rejected. A road stroke may succeed partially; `accepted` and the resulting observation are recorded. `terminated` means normal game failure. Training and baseline CLI runs default to an **1800-second external cap**, configurable with `--cap-seconds`; the wrapper reports reaching it as truncation. The raw host's `truncated` flag is also honored. No gameplay action is sent after either ending.

The host has no live snapshot/restore API. MuZero searches inside its learned latent model and therefore does not need host cloning. The host is used to collect real transitions. Process errors, timeouts and malformed responses raise integration exceptions rather than becoming game losses.

## 3. Observation and action encoding

The model receives an **11 × 30 × 50** float grid and **13** scalar features. The grid contains normalized terrain, infrastructure, connection bits, building color, building kind, demand, reservations and pending removal; then rail occupancy, current vehicle density and a playable-cell mask. Cells outside OriginalReference's current expanding bounds are zeroed. Vehicle density is clipped at five cars per cell. Scalars are normalized current time, trip count, motorway count, total destination demand, building count, vehicle count, six inventory counts and number of upgrade offers.

The first eight grid channels divide raw values by `[2,4,255,7,2,9,9,1]`, respectively. Negative empty-building colors are clamped to zero. Rail occupancy and the playable mask are binary; vehicle density is `min(cars_in_cell / 5, 1)`. The 13 scalar entries are exactly `[time/1800, trips/100, motorways/10, total_destination_demand/100, buildings/100, vehicles/200, six inventory counts individually clamped to 0..100 and divided by 100, upgrade_offer_count/2]`. These are numerical scales for learning, not game-rule changes.

The policy input does not include `scheduledSpawns`, RNG state/draw counts, future upgrade times or planned demand multipliers. Raw observations are retained by the wrapper for metrics and proposal generation. Exact player-information parity is still unaudited for every retained current-state field.

At each decision, [`actions.py`](actions.py) returns at most **16 proposals**, always including wait. It adds available weekly material choices. For the eight destinations with highest current demand plus reservations, it considers up to five nearby houses of a matching color. It skips already connected pairs, finds a weighted eight-neighbor route from the existing house driveway to a valid destination entrance, and offers the first missing straight stroke of at most five cells. Existing roads cost less in path search, while water and rail crossings cost more; unavailable bridge stock blocks new water traversal. It filters current playable bounds, blocked terrain, occupied building cells, pending removals and road stock conservatively. Repeated strokes are removed and proposals are prioritized by demand, distance and whether they start at a house. The heuristic can still propose a stroke the simulator rejects or builds only partly; the wrapper observes the actual result.

Each proposal has eleven float features: three action-type indicators (wait, draw, upgrade), normalized start and end coordinates, urgency, stroke length, stock and the goal heuristic's priority divided by 100. Motorway proposals have all three type indicators zero. Proposal arrays are padded to 16, with a Boolean mask for actual choices. A longer route is reconsidered after each one-second decision rather than built instantaneously. Current choices do not include removal, traffic lights, roundabouts or driveway edits. That restricts achievable performance and is an explicit next extension.

Path search uses cell costs `0.2` for existing infrastructure, `1` for empty land and `4` for water, then adds `0.4` for a diagonal move and `2` on a rail cell. New water traversal is blocked if no bridge item is in stock. The baseline's road priority is `10 * (destination_demand + reservations) - path_cell_count + 4` when a stroke starts at the house (otherwise without `+4`). An upgrade offer gets priority `100 + roads_in_offer`, plus 25 for a motorway offer; wait has priority zero. A motorway shortcut is proposed only between ordinary-road endpoints that already connect a compatible house and destination, are at least ten tiles apart, and satisfy endpoint availability checks. Its priority is `10 * (demand + reservations) + span_length - 15`. These are proposal heuristics, not the MuZero reward formula. The model can choose a lower-priority proposal based on its learned estimates and search.

## 4. MuZero model and search

[`muzero.py`](muzero.py) implements a compact **MuZero-style** latent search model:

1. A representation network maps the 11-channel grid through two 32-channel convolution layers (kernel/stride 5/2 then 3/2), a linear layer and the 13 scalars into a **128-dimensional hidden state** `h_t`.
2. A dynamics network takes `(h_t, action_features)` and predicts next hidden state `h_(t+1)` and a four-component immediate reward vector.
3. A prediction network takes the hidden state and current candidate features and predicts four value components plus one policy logit per candidate. Invalid padded candidates are masked.

At a real decision, the model predicts root priors and value. Tree search performs **24 simulations** by default, with depth at most **3**. The selection score for action `a` at node `s` is:

```text
score(s,a) = dot(Q(s,a) / [1800,100,30,100], [1,.001,.00001,.0000001])
           + 1.5 * P(s,a) * sqrt(N(s)+1) / (N(s,a)+1)
```

`P` blends the model softmax prior with a one-hot prior for the highest-priority goal action; the default goal weight is 0.75. `N` is visits; `Q` is mean backed-up vector value. A newly expanded edge predicts a hidden state, reward, policy and value. Backups use `G = predicted_reward + 0.997 * future_value`. Search returns root visit counts. During training, an action is sampled according to those counts; during validation and test, the highest count wins (lowest index breaks ties). Search never queries the real simulator for imaginary branches.

**Dynamic-action approximation:** the candidate set from the real root is reused at every imagined depth. Actual candidate sets are regenerated from new real observations after actions. The latent model receives action features, but deeper imagined actions may no longer be legal or useful. This is a prototype approximation, not a full solution to changing action sets. Search weighting also approximates, rather than mathematically guarantees, the strict four-level outcome ranking.

## 5. What one training episode and optimizer step do

The agent resets a training city and seed, then repeats: encode the observation; generate proposals; run latent tree search; sample one proposal from root visit counts; apply its ordinary gameplay command; advance 20 ticks; and save the real transition. It stops at game failure or the configured cap. Optional `--bootstrap-episodes` first collects goal-policy demonstrations on separate training seeds and updates the model from them. Episode grids, scalars and proposal features are stored as float16 to reduce memory; the replay buffer retains at most **16 episodes**.

The real per-decision reward is a **vector**, with components:

```text
r_t = [ time_after - time_before,
        trips_after - trips_before,
        mean_waiting_before - mean_waiting_after,
        material_use_before - material_use_after ]
material_use = count(infrastructure_cell != None) + count(motorways)
```

This reward records survival and trip increments plus changes in current mean accumulated waiting and the material proxy. Mean waiting can change when the car population changes, so it is not a time-integrated queue measure. The fourth component is not a monetary cost in OriginalReference. These definitions are versioned in each run's config and are technical choices pending real-world performance measurements.

After the episode, each saved position receives a discounted Monte Carlo value target:

```text
V_target(t) = r_t + 0.997*r_(t+1) + 0.997^2*r_(t+2) + ...
```

The target policy is the normalized root search visits: `pi_target(a) = visits(a) / sum(visits)`. For goal-policy demonstrations it is one-hot on the selected action. The dynamics reward target is the actual next transition reward. A training update samples **16 positions** from stored episodes, drawing half of starting positions from construction decisions when available, and unrolls up to **3 recurrent actions** after each start. Non-wait policy losses receive four times the weight of wait policy losses to counter the large wait majority. It computes value, reward and policy losses at the available unroll steps:

```text
L_value  = MSE(value_prediction, V_target / [1800,100,30,100])
L_reward = MSE(reward_prediction, real_reward / [1,10,10,10])
L_policy = action_weight * -sum_a pi_target(a) * log softmax(policy_logits)(a)
action_weight = 4 for non-wait actions, otherwise 1
L_total  = mean of available loss terms across unrolls and sampled positions
```

The optimizer is Adam at learning rate **0.0003**, with gradient norm clipped to **5**. The default is **8 optimizer updates after each episode**. Python, NumPy and PyTorch receive seed 1000. Hardware-specific exact reproducibility of floating-point training is not guaranteed; the simulator's map/seed episodes are repeatable for the same action sequence.

## 6. Validation, selection and final test

After every `--validate-every` training episodes and after the last episode, the current model runs deterministically on the fixed Dar es Salaam validation seeds. No validation transition enters replay and no optimizer update uses validation data. The checkpoint is selected by lexicographically comparing **mean survival time**, then **mean trip count**, then **negative mean waiting**, then **negative mean material use** across validation seeds. The selected weights are saved as `checkpoint-best.pt`; the latest training weights are separately saved as `checkpoint-last.pt`. The selected model is then compared with the goal baseline on those same seeds. `selection.json` records `beatsGoalBaseline`; matching the baseline is not counted as improvement.

Only after training and checkpoint selection does `train.py` load the best weights. London remains sealed by default; `--final-test` explicitly opens its test cases. It runs the learned policy and the nonlearning goal baseline on the **same London seeds**, with no updates to weights or hyperparameters. Per-seed lexicographic winners and aggregate metrics are saved. This single test is intended as a final estimate, not a set to tune against. Changing code or settings based on London scores would make London a development set; a new untouched test set would then be needed for a fresh final claim.

The baseline chooses the highest-priority proposal from the same generator, so the comparison asks whether learned search improves over the proposal heuristic, given the same limited action set. It does not compare against a human, commercial game, full OriginalReference tool set or a stronger search baseline.

## 7. Run instructions and artifacts

Run from the repository root in PowerShell after installing the **.NET 8 SDK**, Python 3.10+ and a compatible PyTorch build. A local environment keeps Python dependencies out of the game project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r mbrl\requirements.txt
& .\tmp\dotnet\dotnet.exe build simulation\Headless
.\.venv\Scripts\python.exe mbrl\smoke.py
.\.venv\Scripts\python.exe scripts\check_repository.py
.\.venv\Scripts\python.exe mbrl\baseline.py --map train --episodes 1 --dotnet .\tmp\dotnet\dotnet.exe
.\.venv\Scripts\python.exe mbrl\train.py --episodes 10 --validation-seeds 2 --validate-every 5 --simulations 24 --cap-seconds 1800 --bootstrap-episodes 5 --dotnet .\tmp\dotnet\dotnet.exe
```

The ten-episode run is an **integration trial**, not enough training for a strong policy. It does not open London. Check legality, losses, timings and `beatsGoalBaseline` before increasing `--episodes`, validation seed counts or search simulations. The London test should be opened only for a final locked run. `--device cuda` uses a compatible PyTorch GPU installation; CPU is the default. `--dotnet <path>` selects a nonstandard SDK executable. `--output <new-directory>` sets a new run directory; existing directories are refused so runs are not silently overwritten.

`--init-checkpoint <checkpoint-last.pt>` loads model and optimizer weights into a new run. Unless `--episode-offset` is supplied, the saved episode number becomes the offset, so fresh training seeds follow earlier ones. Replay and random-generator state are reset; this is a warm start, not an exact continuation of an interrupted process. Checkpoints made before the eleven-feature proposal change are incompatible.

Each run creates an ignored `output/mbrl/run-<UTC timestamp>/` directory containing:

| Artifact | Contents |
| --- | --- |
| `config.json` | Simulator Git commit, split, seeds, algorithm settings and dependency/device information |
| `training.jsonl` | Per-training-episode metrics and loss |
| `bootstrap.jsonl` | Goal-policy demonstration episodes used for warm start |
| `validation.jsonl` | Dar es Salaam metrics at each candidate checkpoint |
| `baseline-validation.jsonl` | Goal-policy outcomes on the same validation seeds |
| `checkpoint-last.pt` | Latest model and optimizer |
| `checkpoint-best.pt` | Model selected by validation rank |
| `selection.json` | Winning episode, validation ranks and baseline comparison |
| `test.jsonl`, `test-summary.json` | One final London comparison with the goal baseline; created only with `--final-test` |
| `replay-London-<seed>.json` | Deterministic AI command recording for the Original viewer; created only with `--final-test` |

When an Original Windows player build is available, pass `--replay <absolute JSON path>` to inspect an exported test run. The viewer starts paused. See [`simulation/README.md`](../simulation/README.md) for replay flags, including batch verification. GUI playback is a visual check; it does not replace host metrics or prove original-game fidelity.

## 8. Checks actually performed and remaining risks

On this machine, `python mbrl/smoke.py`, Python syntax checks and `scripts/check_repository.py` pass. An initial ten-episode run with the former 300-second cap reached that cap on all training cities but survived only 138–199 seconds on Dar es Salaam validation seeds. The goal baseline reached the cap on both seeds. A longer goal baseline survived 565 seconds on Los Angeles seed 100000 and 800 seconds on Dar es Salaam seed 200000. A short strongly guided trial with a 900-second cap matched the goal baseline on Dar es Salaam seeds 200000 and 200001: 800.05 seconds/262 trips and 895.65 seconds/347 trips. It did **not** beat the baseline. With five goal demonstrations, five training episodes, a 900-second cap and a weaker 0.25 guide, the learned model averaged 654 seconds/178.5 trips on those validation seeds, versus the goal baseline's 847.85 seconds/304.5 trips. The shorter 300-second experiment showed that balanced demonstration updates taught the unguided model to draw roads and complete 43 trips on validation seed 200000, versus 45 for the baseline. Adding a motorway shortcut proposal raised the goal baseline on seed 200000 to 821.3 seconds/279 trips, while seed 200001 stayed at 895.65 seconds/347 trips. A three-episode warm-started model trial with the expanded proposals averaged only 616.575 seconds/158.5 trips against that 858.475-second/313-trip baseline. Longer-horizon generalization remains poor. London final test and Unity replay inspection remain unperformed.

Other important limits: OriginalReference is an unverified reconstruction; the goal generator covers only some normal game actions; path filtering can still produce rejected or partially built strokes; candidate reuse inside imagined search is approximate; and search scalarization can violate the stated strict outcome order. The reported London score will measure transfer from three reconstructed city profiles under this particular action space and training budget.

**Recommended changes following the replay review — 5 November 2026**

Implementation status, 7 November 2026: only the requested destination cutoff
increase from 8 to 20 (both destination loops), a configurable natural-failure
penalty (default 10), and an undelivered-request penalty (default 0.01 per
request-second) have been applied. The historical findings and broader proposals
below remain for reference. See [the current rules](limitations/HANDWRITTEN_RULES.md).

Requested follow-up, 7 November 2026: modification cost now defaults to 0.01
(previously 0.005), and configurable capacity-pressure cost defaults to 0.05
per second times `max(0, demand - demandCapacity + 1)` for each destination.
This starts at capacity and stops below it. No new input channels, overlap-specific
construction ban, forced root coverage or other proposed changes were added.

Subsequent requested updates: local connection priority keeps its +2 bonus only
with active traffic on an existing endpoint road. Training/evaluation search
defaults are now 16 rollouts, with 48 final candidates and 128 raw proposals.
Latest requested update: initial comparison of up to four root actions is now
implemented (wait, highest-prior alternative, then prefer other command/tool
families). Parallel workers reserve different opening actions and complete that
phase before normal PUCT. Coverage counts, priors, visits and mean returns are logged.

Regression correction: compulsory opening visits are excluded from the real-action
sampling and policy-target weights; only subsequent search support supplies those
weights. Raw visit counts/Q still include all investigations. Training remains
stochastic and MCTS-guided; this does not replace it with greedy neural selection.

This is a proposed implementation plan, not an implemented change to the running learner. Findings refer to episode 7, Los Angeles/100006, in `output/mbrl/controlled-20261104-205734`. See `REVIEW_NOTES.md` for verified observations.

- **First fix candidate coverage.** The main route proposer iterates only over the eight destinations with the greatest demand-plus-reservations, and considers only the five closest compatible houses for each. A new destination or useful unserved house can be excluded before the neural network has a chance to choose its route.
- **The purple factory demonstrates this cutoff.** It appeared at second 724, ranked ninth of nine destinations, and first entered the top-eight set at second 766. Connection work began at 767 and useful connectivity appeared at 770. This strongly explains the initial delay in the main route proposals; it does not explain all subsequent traffic failures or prove that no local construction action could have helped earlier.
- **Reserve candidates for urgent and neglected service needs.** Include routes for disconnected destinations, destinations close to failure and useful unserved houses. Retain the bounded final candidate set, but allocate it by service coverage and risk as well as demand, rather than letting the fixed top-eight/top-five cutoffs repeatedly exclude the same buildings. Age should help break persistent ties. Do not require connecting every house regardless of usefulness.
- **Give the model explicit current service-risk features.** The current encoder includes demand and reservations but not explicit per-destination capacity or overcrowding time. Add normalized capacity pressure, overcrowding progress, absence of a route to matching houses and relevant service-coverage features. These must use current observable state, not future spawn schedules. Capacity and timer features are particularly important because equal demand can have different urgency at different destination capacities and timer states.
- **Version the observation schema.** Adding channels makes old first-layer weights and stored replay tensors incompatible without migration. Preserve old checkpoints, migrate compatible weights explicitly, and regenerate or re-encode demonstration/replay observations from the matching traces where feasible. Do not silently load old tensors into a changed model.
- **Keep completed trips as the main outcome and make destination risk visible in reward.** Test a bounded service-risk shaping term that penalizes deteriorating service and rewards relief. Risk should account for demand relative to capacity and proximity to failure; raw demand alone is not enough, and reservations are not completed deliveries. Do not make every new building instantly a large negative reward. Log each component separately.
- **Distinguish shaping from changing the objective.** Potential-based shaping, with `gamma * Phi(next) - Phi(current)`, can give intermediate guidance while preserving the base optimal policy under the appropriate assumptions and terminal handling. Arbitrary persistent penalties and a new failure cost deliberately change the objective. Calibrate them in trip-reward units and compare variants instead of treating large negative numbers as a fix. See [Ng, Harada and Russell](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf).
- **Evaluate an explicit natural-failure cost.** The current final reward can be positive because trips completed elsewhere outweigh waiting costs; episode termination already removes future rewards, but has no separate immediate cost. A failure term can make this event explicit. Apply it to genuine game failure, not to the 1,800-second evaluation cutoff or a protocol error. It is not sufficient on its own to teach timely intervention, and it need not be judged solely by whether every terminal reward becomes negative.
- **Preserve legitimate incremental construction.** The strokes at 621–623 were a route completed at 624. Assess useful progress over a construction sequence and eventual service, not whether every intermediate tile immediately increases connectivity. If retaining route intent, permit interruptions for more urgent needs and keep the original action/time contract.
- **Treat redundant links through measured utility.** Evaluate decision 12 against skipping it. Reduce the priority of extra links that add neither service nor useful routing alternatives. Do not prohibit all cycles, extra junctions or same-component connections: some can shorten routes or relieve traffic. Stronger universal construction costs could also suppress needed late-game capacity.
- **Make small-budget MCTS compare real alternatives.** With eight rollouts, the recorded search often explores only one initial action. Budget initial coverage over a small set, such as wait plus two or three distinct useful construction/relief actions, before spending the rest on promising branches. Compare actions under controlled sampled futures where appropriate. Log priors, visits, Q estimates, actual root coverage and selected-action changes.
- **Consider Gumbel/Sequential Halving as a separately tested search variant.** The low-budget planning literature directly addresses insufficient root-action coverage. It is a candidate design, not a guarantee of improvement with this simulator, action generator or value estimates. Start with a transparent root-coverage baseline before implementing a more complex search. See [Danihelka et al.](https://openreview.net/pdf?id=bERaNdoegnO).
- **Strengthen learning stability and resumption.** Support explicit restoration of optimizer state, permanent demonstrations, recent/successful replay, RNG state, episode position and stopping metadata. The latest batch warm-started weights with fresh optimizer/replay state; it was not an exact continuation. Compare demonstrations retained versus absent in controlled trials rather than assuming either is always superior. Keep the best checkpoint independent of the latest weights.
- **Make runtime observable before extending training.** Write a heartbeat to both terminal and a progress file on a wall-clock interval, including phase, episode, decision, simulated time, trips and current search activity. Instrument host commands and search phases. A thread can report a stale/current phase while a command is slow, without consuming policy RNG or changing the simulation. Make the last completed decision distinguishable from an in-progress rollout.
- **Optimize the measured simulator bottleneck.** The active Python profile attributed approximately 87% of sampled time to hypothetical simulator transitions, with around 11% in node construction/preflight and under 1% in network prediction. Obtain a managed C# profile before claiming the cause is routing, queues, copying or garbage collection. Benchmark one PyTorch computation thread, then two independent branch workers with appropriate tree coordination; expand worker count only after measuring useful throughput and result quality.
- **Create focused regression cases before changing weights.** Include decision 12's redundant edge, the useful four-decision connection at 621–624, the persistently isolated house, the ninth-destination exclusion and the purple factory's escalating overcrowding. Check candidate availability and reward-component behavior, plus examples where an extra link or temporarily incomplete route is beneficial. Do not encode the visual judgment that any single shape is universally bad.
- **Run controlled changes in stages.** Preserve the current best checkpoint and matching host. First compare the candidate-coverage fix with the existing setup; next test observation and reward changes; then test root-coverage/search variants. Observation changes require a compatible initialization/migration baseline. Fix seeds, horizon and rules, record source hashes, and avoid attributing a combined change to one mechanism.
- **Evaluate on more development cases.** Keep the existing validation seeds for continuity and add a fixed set of additional Dar es Salaam seeds for broader development checks. Keep London held out for final testing. Use the same 1,800-second cap, but report natural failures separately from time cutoffs. Compare completed trips, survival, late-game throughput, worst-destination risk, useful house coverage and real runtime. Newly selected development seeds can subsequently be overfit too, so they are not a substitute for a locked final test.
- **Choose changes by useful gameplay improvement per unit of computation.** A lower training loss, more tree nodes, a negative terminal reward or faster rollouts alone is not success. The desired behavior is timely useful construction, sustained destination service and better trip/survival results at an acceptable runtime.

Suggested implementation order: candidate coverage and diagnostic logging; explicit service-risk observations with schema handling; reward variants and targeted cases; small-budget root coverage; stateful training continuation and broader evaluation; managed-runtime optimization and parallel search.


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

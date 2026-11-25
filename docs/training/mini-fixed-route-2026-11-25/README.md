# One difficult connection: bounded PPO practice

25November2026. User approved flexible-duration mini-task repair and conditional overnight readiness. The completed60-second reset/cold comparison did not repair hard connections. Longer300-second lessons have improved development city scores at the midpoint, but tight single success is9/16 and both-pair service3/16. Preserve that ongoing comparison. Before launching another broad mixture from the protected-road candidate, test focused learning on one difficult empty board.

## Fixed lesson and starting model

Native training seed232000001, small-city-offset-single. It is the lowest seed among the original policy's previously successful bank-collection examples outside its six-cell specialist range: approach distance7, stock8. Selection uses an existing successful game, not reference edits or a planner. No recorded road prefix is applied: every game starts empty. Initial32sampled action draws succeed5times, mean score2.8125. The same native simulator,300-second deadline, native completed-trip reward and legal connection/Wait actions remain in use.

Parent: output/training/mini-road-detached-initial-01/start.zip, SHA7582e285e3f6b2b44487cf3fe86156169aa80d79272dccbe21dc408fed0bf324. It retains road/critic weights and22Adam states at8192steps from the reset-trained road candidate, restores original zero-output Wait corrections and freezes them, and prevents value loss from changing road features. The critic value head still learns. [Preparation and limitations](../mini-task-repair-2026-11-25/critic-detach/PLAN.md). No new imitation, reward shaping or hidden future inputs.

## Declared budget and reviews

65536additional decisions:16workers×512steps×8rollouts, batch128, four PPO epochs, LR.0003, existing road/spatial/critic scales.3/.1/.1, native score, gamma/GAE1, entropy.01, value coefficient1e-5, KL safeguard.03. Fixed training scene with independently sampled policy actions. Validated frozen-computation cache and terminal-tail acceleration enabled. All checkpoints retained; no early termination for one low score.

Evaluate the same32action RNGs at16384/32768/65536added decisions. A practical mastery target is29/32successes; if reached, verify on new action draws before expanding layouts. This establishes performance on one training layout only. A positive but incomplete trend may justify a separately documented continuation; flat results require diagnosis, not a convergence claim. Final broad112-game mini and32-city development reviews check retention, even if the fixed lesson fails. No automatic promotion or overnight launch.

Source snapshot, commands, logs, measurements, and local checkpoint hashes will be archived. Weights/native binaries stay local under output/training/mini-fixed-route-01. Broader prepared run_mini_road_continuation.py remains unlaunched;241M training range and236M/237Mconfirmation ranges remain unused.

Preflight: repeated reset fingerprints identical across32baseline games. Disposable actual-factory GPU resume128decisions/4updates/10episodes passed native reward/no-terminal-bootstrap, frozen Wait/prior, finite tensors and save/reload. Source compilation passed. The disposable checkpoint is excluded.


## Focused route quarter review and exact visual check
At16384added decisions, fixed-layout successes12/32 versus5/32 initially;9actiondraws gained success and2lost it. Mean native score6.75 versus2.8125. Early learning movement on one training layout, not generalization or convergence. Full65536budget continues.

Selected the lowest-RNG newly successful draw622005 for exact paired replay. Expanded only forced Wait periods for visualization; every compact native boundary and final evaluation counter matches. Starting candidate0deliveries/nativefailure near148seconds; quartercandidate18deliveries by300, firstdelivery15seconds. Both make10construction edits and no edits afterfirstdelivery. The quarter policy completes a functioning route but also places a remote stray fragment. Thus route completion improves while conservation is not yet demonstrated. Frame sheet visually inspected, including all road coordinates. Source, HTML, rawframes, selection andchecks in mini-fixed-route/quarter-replay/; plot source plot_quarter.py.


## Focused connection midpoint, 25 November 18:30 Beirut
Measured: at32768added decisions the fixed board succeeds15/32 (initial5,quarter12); gained11 and lost1 draws against initial. Checkpoint SHA8601e00f53432f0b951e46cc6c8e7cca6d629cd30844a9eec2ea68b75adaa658. Positive movement, still below29/32mastery; declared65536budget continues unchanged. Same training layout/action draws, not geometry generalization. Evidence docs/training/mini-fixed-route-2026-11-25/evaluation/fixed-32768 and midpoint-review.json.


### Scope of the fixed-board test
Engineering interpretation: a successful native-score route can include a harmless extra road when stock allows it. This lesson therefore tests reliable connection completion, not minimal construction or reserving stock for a future arrival. The Wait correction heads remain frozen; relative road preferences still affect action probabilities, but this stage is not new joint Wait/road strategy training. After reliable fixed-board success, test new action draws and varied empty-board connections before judging later-arrival conservation and city transfer. No new road penalty or hidden reference route is added.

Clarification: frozen Wait correction heads mean their logits remain unchanged on a shared state. Actual Wait probability can still change when learned road logits change through softmax normalization. Thus this is protected-head road learning, not a guarantee of invariant overall Wait behavior.


## Full fixed-board budget, 25 November 18:46 Beirut
Measured final fixed review:24/32 successes, mean13.5, after65536added decisions and5529completed training episodes. Initial5/32,quarter12/32,midpoint15/32. Final checkpoint SHA c86c0db95e28951c3e9ed36d5a29eb94d7faa4cbddbfddaed18700dc70121eb3. Still below practical29/32 mastery, but substantial improvement across the declared budget. Broader112mini/32city retention reviews remain running. No promotion or overnight launch. Further same-task continuation is under consideration, not yet started.


### Final fixed-board visual review
Exact replay of the lowest-action-RNG success and failure under the final checkpoint: success18deliveries (first15s), failure0/nativeend147.9s; each10construction edits, stock0, no post-first-delivery edits. All compact native boundaries and final metrics match; visualization expands only forced Wait ticks. Figure visually inspected: successful draw completes a direct functioning route but includes a remote stray fragment; failed draw builds two disconnected sides and an unnecessary branch, exhausting inventory before bridging the gap. This selected failure is a construction-choice issue, not demonstrated congestion. Different sampled actions on the same training board; no population frequency claim beyond the32-game review. Source/frames/HTML/checks/figure: final-replay/, replay_final.py, plot_final.py.


### Broader mini review after fixed practice, 25 November 18:52 Beirut
Measured112developmentgames: adjacent/bend/clear16/16each, obstacle14/16 (short skills retained); tight singles8/16 unchanged versus forward-equivalent parent; generous singles12/16 versus8/16; firstpair12/16, bothpairs3/16 versus5/16 parent. This does not establish general tight-stock improvement or later-connection mastery. Finalcity review still running. Fixedboard24/32 is a learning diagnostic, not transferable strategy certification.

Superseding correction25November19:10: custom CityActionDistribution normalizesconditionalroadlogits separately, so frozenWaitheads/progresscoupling preserveWaitprobability onsharedstates. Earlier ordinary-softmax speculation was incorrect. Currentnegativepairaudit confirmsall48negativecases/model stillspendstock; see ../city-negative-pair-audit-2026-11-25/README.md.

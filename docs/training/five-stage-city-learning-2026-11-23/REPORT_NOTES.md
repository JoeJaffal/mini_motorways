# Interpretation, changes and remaining gates

This record distinguishes user instructions, engineering choices, measurements
and hypotheses. The user authorized all five bounded stages and explicitly chose
`/home/mohammadjaffal/mini_motorways`, branch `Maskable-PPO`. Existing files,
checkpoints and uncommitted changes were preserved. The Desktop/main checkout
was checked clean at the end. No long training session was launched.

## What changed and why

1. Integrated the previously local traffic fixtures as opt-in native curricula.
   The simulator now guards traffic-surge updates by curriculum identity. Added
   an established third-color route to demand exercises so the existing opening
   protection allows later-city learning. Quiet exercises start fully connected.
   See the corresponding simulator design-decision entry and archived source.
2. Added one observation/action interface and bounded continuation/evaluation
   scripts for connection, waiting, demand/congestion and mixed city practice.
   All new training uses Maskable PPO and native completed deliveries. Named
   reference edits are evaluation controls only; no planner, teacher actions or
   imitation targets were added. Existing engineered service preferences remain.
3. Added optional forced-Wait compression: collect native rewards while there
   are no legal builds, stopping immediately when a build becomes possible.
   Gamma is one. Frame history is still updated on every native step. Native
   state/reward parity passed on all eight lessons and a growing-city stock
   return check. Finite practice windows terminate in this mode; city limits
   remain truncations. This changes credit assignment and decision-count meaning.
4. Diagnosed nearly absent exploration of a useful light-traffic feeder (roughly
   5e-14 probability in the original diagnostic state). Broadly softening road
   preferences made exploration possible but badly damaged city performance.
   Both broad-exploration candidates were rejected, with checkpoints retained.
5. Probed a missing visible relation: extra homes supplying an already-served
   destination received no old service-progress/join/urgency signal. Added a
   separately loadable, narrow policy with ten zero-initialized linear weights
   over visible home supply, existing road components/cycles, traffic counts,
   motion-derived stopping, displayed demand and inherited service features.
   Original actor/reference weights are frozen. Only these ten coefficients and
   the critic learn. This is a diagnostic representation improvement, not a
   general learned city strategy or evidence that the missing signal caused
   every failure. No internal vehicle routes/speeds or future events are inputs.
6. The new trainable parameter set starts fresh optimizer state. RelativeRateAdam
   maintains a critic learning rate of 1% of the relation actor's scheduled rate;
   a numerical check verifies the ratio and restoration. Earlier compatible
   continuations retain their optimizer state.
7. Separately calibrated conditional road sampling by a factor of twenty after
   the two relation PPO runs. It preserves Wait/build probability, road argmax,
   legal masking and the protected opening distribution. Both the zero-weight
   initialization and trained policy receive identical calibration. These saved
   checkpoints are inference candidates; calibration is not a PPO update.
   Their optimizer moments come from the warm distributions, so they are not
   automatically validated warm starts for long training at the old rates.
8. A second inference variant restored the generic prior and scaled learned
   coefficients instead, resetting optimizer moments. It scored 89.50 on the
   development cities with 30/32 scoring and was not preferred. It remains saved.

## Attribution and unresolved behavior

Longer-route completion improves already at calibrated zero initialization.
Credit that to engineering/inference calibration, not PPO. Demand prioritization
improves further after PPO relative to that exact initialization, including the
color/location-swapped exercise. Light-traffic scores improve partially while
heavy-traffic performance stays similar. These controlled results do not prove
broad congestion management in arbitrary cities.

Quiet cases still spend both spare road units. Waiting controls earn similar
scores while keeping the roads: the short quiet horizon does not impose a
meaningful future cost for spending them. A next experiment should introduce
later visible service needs for which retained stock changes native deliveries,
and evaluate waiting/stockouts over that longer consequence window. This is a
proposal, not an implemented lesson or a justification for adding a planner.

Full-city tests remain native Los Angeles episodes up to 600 simulation seconds,
with one legal road edge or Wait and inherited scripted weekly choices. They do
not cover every tool, player-chosen weekly awards, arbitrary maps or leaderboard
performance. Scoring-game count is only a coarse regression measure. Protected
opening weights do not guarantee every sampled city survives after service is
established. Component-summed traffic/demand features might extrapolate poorly
to larger cities; this is an untested hypothesis.

## Evidence and reproducibility

Each training directory's archived config records its parent hash, host hash,
seed start, learning rate and budget. `run-register.json` records all eleven
runs. Paired city suites share scenario and action RNG seeds within each suite.
Development results were inspected repeatedly and are selection data. The final
independent city/practice suites were evaluated after candidate construction;
no updates used their results. `final-comparison.json` gives paired bootstrap
intervals (12,000 resamples, seed142915) and cross-suite city-seed overlap.

Practice success means serving the initially unserved target for connection and
delay, or serving the urgent destination for priority. It is not a useful
junction metric (there is no initially unserved target there); compare native
scores and evaluator controls instead. Quiet success is also not conservation.
The multi-edge evaluator's first-road label may say `other` for a correct early
edge because its reference dictionary retains the last `draw`; use final native
service outcomes, not that label, to judge longer-route success.

Checks: 99 native suites; 1,116 legality actions; exact old/new ordinary-city
state parity on 364 transitions; forced-Wait parity on eight controls plus city
availability interruptions; seven final focused Python tests; opening/temperature
parity, supply-feature and relative-optimizer-rate checks; checkpoint weight
and hash audits. An early exploration test mistakenly compared indistinguishable
cells; corrected geometry passes and both logs remain archived.

`measurements/` preserves small run/evaluation configs, episodes, progress and
logs. `source/` preserves current local training modules and simulator sources,
including inherited work, not only this task's edits. `native-tracked-context.diff`
also includes earlier uncommitted work and is not an incremental patch to apply.
`local-artifacts.json` records hashes of weights/host binaries kept only locally.
`manifest.json` authenticates archive contents. No weights or binaries belong in
this report archive. Original runs and earlier reports remain unchanged.

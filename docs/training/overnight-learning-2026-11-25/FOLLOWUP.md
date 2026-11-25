# Overnight follow-up —25November2026

User authorized a check30minutes later, further justified training and research while asleep, with no further clicks. The follow-up remains in the active chat; no recurring automation was created for the specific job. Requested check target02:29Beirut. Existing training was left uninterrupted and finished02:11:48.

## Completed comparison: measured findings

The longer road-cost comparison reached262144decisions per arm. In the generous-stock development lesson, the .04model connected55/64games versus46/64for control (85.9%versus71.9%). Mean native deliveries2.875versus2.484; paired difference+0.391,95%clustered interval[+0.031,+0.766]. Roads outside observed vehicle routes4.828versus6.031, difference−1.203[−2.156,−0.359]. Total road spending slightly increased10.438versus10.375. This is better placement/service in that evaluation, not demonstrated road-stock conservation. Tight-stock success37/64versus35/64remains uncertain.

The growing separation across the fixed65536/131072/262144checkpoints supports the user's warning that the16kpilot was too short. One training seed and reused development layouts still limit claims. Full-city transfer is not implied. See ../road-cost-continuation-2026-11-24/RESULTS.md and raw archived games.

## Pending checks and provisional next experiment

Read-only city comparisons of the strong final policy and original whole-policy initialization run on the existing184M/185Mdevelopment suite, with matched action RNGs, bridges and600-second native scoring. These are development retention checks, not untouched confirmation. A frozen critic diagnostic uses the same207Mdiagnostic layouts as earlier. No teacher/reference edits or path estimates are used by the policy or evaluation (trace estimate=False).

The control's frozen critic MSE fell20.67→5.14 with longer training, but explained variance remains−1.39on sampled states. This motivates checking the strong candidate before choosing the next stage. Prepared, not yet launched: preserve the strong final as parent, continue an unchanged branch alongside a branch changing only critic Adam rate scale0.1→1. Both receive262144more decisions under the same cost.04recipe, reaching524288each. Actor rates, masks, reward, architecture and optimizer moments remain unchanged at the split. New seed stream210M, sampling seed251125; independent test budgets/schedules fixed before launch. A disposable one-rollout critic-rate smoke must pass first and will not seed either experiment arm.

Research follow-up: Andrychowicz et al., https://arxiv.org/html/2006.05990v1 , sections3.3/3.7: value fitting and learning-rate choices materially affect performance in their continuous-control study, with task-dependent normalization results. This supports measuring a targeted optimization change, not a claim that the proposed critic rate is optimal for our game. Preserve an unchanged continuation because current practice learning is improving; do not discard it to chase a new hypothesis.

No score guarantee, planner, new imitation, automatic promotion, unlimited extension or destructive file action is authorized by this plan. Final choice and launch evidence will be appended after the requested follow-up check.


## Superseding finding and decision,02:17Beirut

The city prechecks finished: original mean126.09375with30/32scoring, strong practice-final86.96875with27/32scoring. Paid units99.125→86.21875and outside-observed-route units32.28125→33.375. Better single-pair practice is not better city play. Preserve the original; do not promote the practice final. Its critic diagnostic also remains weak (MSE5.057,EV−1.127), but that does not justify changing critic optimization before addressing the observed transfer failure.

Engineering decision: defer the prepared critic-rate ablation (code retained, never trained). Instead compare lesson-only continuation with a mixed-city continuation from the same strong262144parent, using unchanged actor/critic rates and Adam state. Both receive262144additional decisions and fixed393216/524288practice evaluations plus final city evaluations. Eight workers train native600-second cities; four train tight-stock and four generous-stock60-second lessons. This guarantees50%of collected rollout decisions come from city workers, not50%of completed games. All tasks share one policy. The existing common minibatch advantage normalization is unchanged; differing task return scales are a known limitation, and task-specific training reports are printed separately.

The .04road-unit cost remains confined to the bounded lessons; native city reward is completed deliveries, with no city road penalty. City workers include legal bridges and normal weekly stock, keeping ordinary city action/reward semantics. The accounting wrapper records spending before forced waits can replenish stock. No teacher-generated routes, imitation, hidden future inputs or simulator changes. Finite lessons terminate without bootstrapping; city time limits retain existing bootstrap semantics. No new task-ID/horizon observation is added; the preexisting partial-observability limitation across lesson/city regimes remains explicit.

Fresh training stream210000000, sampling RNG251125; disposable parity checks212M and future smoke213M are excluded. Seed/action pairs for city prechecks remain the existing consumed184M/185Mdevelopment suite. Reuse verified prechecks rather than replaying identical games. Only final checkpoints enter the city comparison; no best-checkpoint cherry-picking, automatic promotion, fresh confirmation consumption or unlimited extension.

The user's requested02:29follow-up remains the launch decision point. Mixed wrapper transition checks and a subsequent disposable resume smoke must pass. Existing comparison is complete and no new training has yet started.


Wrapper checks passed: 497paired transitions across six complete games, including two cities and four rewarded lessons. Observations, legal masks, rewards and termination flags exactly matched existing environments. City rewards remain native153and5in these two check games; practice penalties and terminal flags matched existing cost wrappers. These checks are not learning results. Paired city score regression interval is[-63.94,-11.50]around−39.125,clustered over16development layouts. Summary identity check passes: duplicated city inputs produce exactlyzero differences and intervals.


## Smoke defect found and repaired before long launch

First mixed-worker smoke failed when a city episode completed: the shared Monitor requested stock_initial, which the city info dictionary lacked. This was a reporting integration defect, not a simulator/policy change. Collection stalled after a worker exception; no rollout update or checkpoint was saved. Stopped only the verified owned smoke process tree; preserved logs and partial episode records. The wrapper now captures native reset stock and consistently exposes stock_initial for both task families. A new smoke uses213100000and a new output directory from the unchanged parent.

The overnight controller also gains a10-minute no-progress watchdog over episodes, gradient records and checkpoints; it stops only its own learner subtree and records an error instead of silently hanging overnight. No completed checkpoint is removed. This is failure containment, not automatic crash recovery or an automatic model rollback.


## Launch decision

Corrected mixed smoke completed8192decisions/133episodes in181.72seconds. Adam8192→8448verified on reload; all three task ledgers, finite parameters and protected parent hash pass. It is excluded from the experiment. Launched the bounded task-mix comparison after the requested half-hour check and smoke. See launch.json for exact time/PID/command. Both experiment branches start from the original strong262144checkpoint, not a smoke checkpoint. Roughly3hours expected with evaluation; no further approval or click is required. Original city policy remains retained, and no result is automatically promoted.

# Saving roads for later service

Started 23 November 2026; work continued into 24 November (Asia/Beirut).
Status: completed. One bounded PPO run, a diagnosed transfer failure, a separate feature repair and two city suites. No overnight run.

User request: teach saving roads for later connections and measure full-city
scores. Checkout `/home/mohammadjaffal/mini_motorways`, branch `Maskable-PPO`.
The Desktop/main checkout and all earlier checkpoints are preserved.

## Implementation and limits

The native `midgame-network-reserve` lesson begins with two homes supplying one
shop. Stock is limited; a new pair appears8–16 seconds later. Legal unrelated
builds can consume the stock. A road obstructing the scheduled parcel may prevent
its appearance; there is no hidden repair. Visible road stubs make this a bounded
route task, not arbitrary new-city growth. Target positions/timing are not policy
inputs. Controls use reference edits only in evaluation.

Reward is solely native completed deliveries, excluding warmup. Wait itself has
no bonus and building has no new penalty. The environment updates bookkeeping
when destinations appear, so future deliveries are included in its episode
ledger. Forced Wait is combined only when no legal build exists; its native
state/reward and reset behavior passed separate checks. Finite lesson horizons
terminate; ordinary city limits retain truncation.

The new policy starts exactly at the best calibrated parent. Six zero-initialized
coefficients adjust Wait using current visible service availability, quiet/blocked
context and stock. Only those coefficients and the critic learn. Conditional
road selection and the protected opening remain unchanged. Fresh Adam state is
explicit because the trainable parameter set changed. Actor LR .03; critic rate
.0003. This is a narrow PPO experiment, not a claim of unrestricted strategy
learning. No planner, teacher actions or imitation were added.

## Preflight evidence

- 99 native suites pass;364 ordinary city transitions exactly match the prior host.
- Eight focused Python tests pass, including trainable-set and stock-encoding checks.
- Zero-init distribution equality on opening and nine lessons.
- Native controls on 8 cases: saving then connecting 8/8; wasting then attempting
 the same connection 0/8; permanent Wait 0/8. Parent 2/8.
- Mean stock when the new destination appears: saving 3.625, wasting 0, parent 1.125.
- Reset cancels pending events; ordinary city behavior matches a fresh environment.
- Compressed/uncompressed saving controls have identical native state and reward.

[Plan and budgets](PLAN.md) records selection rules and fixed test seeds.
Parent is `output/training/city-five-stage-cold-initial-01/candidate.zip`; keep
`city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip` as older rollback.
Results, run measurements, source snapshots and local-only checkpoint hashes are archived below. Prior reports remain historical.


## Bounded run and repair

`city-road-reserve-pilot-01` added 8,192 PPO decisions,454 episodes in 223.7 seconds
with 16 workers. Parent: calibration-only city candidate; initial and all saves
remain intact. Midpoint at 4,096 decisions had 273 episodes. Native rewards stayed
finite and the episode ledger matched deliveries. Only six Wait weights and the
critic changed. No road ranking or opening weights changed.

Development later-target success parent/mid/final: 2/8,3/8,6/8. Arrival stock:
1.125,2.5,3.125. Longer routes stayed8/8; delayed connections improved6/8→8/8.
Quiet stock at episode end improved0→0.875. Final was frozen before city review.

City review exposed this experiment's feature defect: missing local progress
was treated as blocked. Two native replays showed 169/145 such decisions and
>99% Wait with 211/274 legal builds and no visible approach blocker. This is
archived in `wait-context-diagnosis.json`. The first city's results are now
diagnostic evidence, not the final independent confirmation.

`CityVisibleReserveFeatures` restricts the last two inputs to visible blocked
shop approaches. Its separately saved checkpoint has exactly the same learned
weights; no extra PPO or probability calibration occurred. Initial nine-lesson
probabilities and road rankings remain unchanged. Native replay checks show
fallback to the parent's probabilities when there is no visible blocker.
The old class and rejected checkpoint remain reproducible. This repair is an
engineering contribution; conservation weights came from native-score PPO.
Copied optimizer moments are not proof of safe long-run continuation after the
input semantics change. No such continuation was launched.

## Full-city measurements

All games are sampled native Los Angeles, maximum 600 simulation seconds,
road-or-Wait with inherited scripted weekly picks. Paired scenario/action seeds
within each suite; 32 games per policy. These are not leaderboard scores.

| Suite / policy | Mean score | Scoring games | New targets served | Arrivals with zero stock | Mean paid road units |
|---|---:|---:|---:|---:|---:|
| First / original | 105.38 | 30/32 | 125 | 36 | 87.31 |
| First / calibrated parent | 98.03 | 30/32 | 115 | 29 | 83.28 |
| First / unrepaired PPO | 37.44 | 30/32 | 62 | 0 | 26.53 |
| Confirmation / calibrated parent | 81.88 | 23/32 | 101 | 29 | 77.53 |
| Confirmation / repaired PPO | 54.97 | 23/32 | 77 | 3 | 50.38 |

Confirmation paired mean change: **-26.91**,95% bootstrap interval [-43.50,-11.81] (12,000 resamples). Retention gate: **FAIL** (at least 95% of parent mean and no fewer scoring cities). Shared city seeds between the two suites: [].

The second suite RNG 940128 was fixed after the feature correction and was not
used for further changes. The first suite RNG 940127 diagnosed the defect.
Comparing means across suites does not isolate the repair; use each paired
parent comparison. Outside-observed-route counts are diagnostic, not proof that
every such road is waste. Source JSONL and hashes are archived.

## Fresh practice checks

Sixteen cases per lesson, seeds 132000000 onward. Construction success means a
new target receives a native delivery; demand success means urgent target
service. Quiet success is not conservation. Junction success counts are not
meaningful; compare scores. Native controls supply no actions to PPO.

| Measure | Parent | Unrepaired PPO | Repaired PPO |
|---|---:|---:|---:|
| One-edge success /16 | 16 | 16 | 16 |
| Longer-route success /16 | 16 | 16 | 16 |
| Delayed success /16 | 15 | 16 | 16 |
| Future-target success /16 | 2 | 13 | 13 |
| Stock at future target arrival | 1.06 | 3.00 | 3.00 |
| Quiet stock left | 0.00 | 0.88 | 0.88 |
| Light-traffic mean score | 12.06 | 11.75 | 11.81 |
| Heavy-traffic mean score | 32.25 | 31.12 | 31.56 |
| Urgent service /32 | 17 | 17 | 17 |

The reserve controls compare saving then connecting, wasting then attempting the
same route, and permanent Wait. Some useful prebuilding is possible from visible
stubs and is legitimate; success does not imply all successful games waited until
spawn. The policy still lacks proof of arbitrary-city traffic management or
optimal inventory planning. High-stock contexts extend beyond the narrow
curriculum's 2–5-road budget; transfer tests matter more than parameter signs.

## Checks, artifacts and decision

Nine final focused Python tests pass. All99 native suites,364 ordinary-city
transition comparisons, reset isolation, forced-Wait native parity, exact
zero-initialization/opening and conditional-road checks pass. A native replay
verifies the context repair falls back to the parent's probabilities in the
misclassified state. No old checkpoint was overwritten and main stays untouched.

- [Run and evaluation measurements](measurements/output/training/)
- [Detailed results](final-results.json), [first paired comparison](city-comparison.json)
- [Native repair check](context-repair-native-check.json), [parameter audit](repaired-audit.json)
- [Final Python checks](python-final-checks.txt), [native checks](native-checks.txt)
- [Local-only checkpoint and host hashes](local-only-artifacts.json)
- [Source snapshot](source/), [archive checksums](manifest.json)

New checkpoint: `output/training/city-road-reserve-repaired-01/candidate.zip`.
Original failed transfer: `output/training/city-road-reserve-pilot-01/final.zip`.
Reference: `output/training/city-five-stage-cold-initial-01/candidate.zip`.
Weights/binaries stay local; the archive includes only code and small evidence.

The repaired checkpoint fails retention. Keep the calibrated parent selected. Conservation practice gains do not justify replacing it or launching a long run; next work must distinguish useful network expansion from unproductive spending in mixed city states.


### Final decision — 24 November 2026

The repaired candidate averages54.96875 versus81.875 for its exact calibrated
parent on the final32-city suite (both23/32 scoring). Difference−26.90625,
95% paired interval[−43.5,−11.8125]: reject for city continuation. The learned
reservation benefit is real on held-out lessons (13/16 versus2/16), but it is
not a city-score improvement. Keep the calibrated parent and older protected
reference; preserve the new candidate as a diagnostic artifact only.

The remaining policy increases Wait even for available service: on the archived
route probe it rises from14.54% to42.55%. That is a measured behavior; its precise
share of the city-score loss has not been isolated. The small-stock lesson also
does not cover large inventories and long city routes. Next proposed work:
train the conservation/expansion tradeoff in mixed city states with tight service
deadlines, explicitly checking prompt useful construction and a wider stock
range. Do not simply extend this reservation-only run. No further training is
active and no long-run command is recommended from these checkpoints.

Forced-Wait parity includes exact-stock cases reducing64→20 and62→15 wrapper
steps with identical final native state/reward; these supplement the spare-stock
controls. Final source and evidence archive is checksummed in manifest.json.

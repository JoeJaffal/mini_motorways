# Current model report: searchable text

Extracted from the dated 12-page PDF; use the PDF for graphs and layout.


## PDF page 1

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
01
The current Mini Motorways model
Prepared for Mohammad | 28 October 2026 | Branch mohammad
It learned greater consistency on one seed, then plateaued.
This report explains the current learner and the latest completed experiment. The objective remains 1,000
completed trips on Los Angeles in OriginalReference. That goal has not been met.
Latest four-hour run
Measured outcome
Best observed game
73 trips; 461.4 simulated seconds
Completed games
4,549
Policy selections
2,271,492
Mean score: first / last 100 games
24.88 / 52.10
Held-out final sampled scores
3, 0, 0 on seeds 2000-2002
Training device
CPU; four independent games, one shared model
How to read this report
Pages 2-5 explain what it sees, what it can do, and how learning works. Pages 6-9 show results, transfer,
the original baseline and throughput. Pages 10-12 cover fixes, decisions, unresolved limits and the exact
input schema.
Source: archived seed-1000-parallel-02 summary/config/monitor files. This was a resumed run, not training from random weights.
OriginalReference is a reconstruction, not a validated exact copy of the commercial game. No additional training was performed to
produce this report.



## PDF page 2

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
02
1 / What the model can see
It reads structured numerical state, not the rendered game image.
Information
What enters the policy
Map and roads
Playable area, terrain, infrastructure categories, eight connection directions and pending
demolition
Buildings
Locations/footprints, kinds, colors, entrances, demand, reservations and overcrowding
timers
Traffic
Per-tile car count, maximum speed and maximum current waiting time
Motorways
Endpoints, other-end coordinates, link number and retirement status
Global state
Materials, time, week, trips, current upgrade offers and action-selection stage
The important missing information
It does not receive each individual car's color, destination or route. It is not explicitly told which houses
have a working connection to a matching destination. It must infer that relationship from the map.
The policy has no recurrent memory and receives no stack of previous observations. Current waiting and
overcrowding timers provide some accumulated state, but they are not a memory of past decisions.
Future spawns, planned building changes and random-generator state are withheld. Cells outside
playable bounds are zeroed. Values are normalized and clipped; multiple entities sharing a tile lose detail.
London-specific rail/train channels are absent.
Exact representation: 50 channels over 50 x 30 cells plus 42 global values. Current internal diagnostics are exposed; this is not
claimed to be identical to a human player's visual information. Source: training/environment.py and its documented allowlist.



## PDF page 3

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
03
2 / Actions and the network
All ordinary tools remain available, subject to current resources and targets.
Action
Selection after choosing a tool
Wait / upgrade
None; command completes immediately
Road, bridge, light, roundabout, remove
One tile
Road stroke / house driveway
Start and end/direction tiles
Create motorway
Two endpoints
Edit motorway
Existing endpoint plus two replacements
Remove motorway
An active endpoint
The action vocabulary contains 1,513 IDs: 1,500 cells and 13 tools/upgrade choices. A command uses
one to four policy selections. Intermediate selections advance no game time; a completed command
advances 20 ticks, normally one simulated second. Rejected commands consume time too.
A compact actor-critic network
Stage
Shape / role
Map encoder
50 x 30 x 50 input; 16 then 24 convolution filters, 3 x 3 kernels, stride 2
Combine
Flatten 2,496 features + 42 globals; project to 128 shared features
Actor
64 hidden units; 1,513 action scores, filtered by the mask
Critic
64 hidden units; one estimate of discounted future trip reward
450,610 trainable parameters are numerical weights adjusted by optimization, not 450,610 rules or games. Masks remove locally
unavailable choices; the host still decides final legality, including partial strokes. No path planner supplies routes. Sources: train.py,
environment.py and original checkpoint inspection.



## PDF page 4

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
04
3 / How it learns
Maskable PPO = Proximal Policy Optimization with unavailable actions masked out.
Step
What happens
Observe
Encode the current city and available choices.
Choose
Sample an allowed action from the actor's probabilities.
Collect
Record observations, actions, rewards and critic predictions.
Estimate
Compare outcomes with predictions to estimate advantage.
Update
Adjust weights using PPO's clipped policy objective, value loss and entropy term.
Repeat
Use the updated shared policy for new interactions.
The reward has only one component
reward = trips after the command - trips before the command
No completed trip means zero reward, even for a useful road. Two completed trips mean +2. There is no
construction penalty, demolition penalty, survival bonus or explicit negative failure reward. Failure matters
indirectly because it ends future opportunities for trips.
Cars take time to deliver, so useful early decisions may receive credit much later. PPO and the critic
estimate this connection; they do not automatically know what makes a correct road network.
Intermediate endpoint choices also affect the selection-level discount.
Exploration versus deterministic playback
Training samples actions to explore. Deterministic evaluation chooses the highest-probability allowed
action. Watching the best recorded game replays exact commands; it does not ask the final model to
recreate that game.
PPO is on-policy: updates use recent rollouts, not a persistent replay dataset. A parameter update or low value loss alone does not
establish better gameplay. The original report contains the schematic clipped probability-ratio objective and detailed glossary.



## PDF page 5

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
05
4 / Current training configuration
Parallel games collect experience for one policy, not four independently trained models.
Setting
Current experiment
Version / city / materials
OriginalReference / Los Angeles / normal finite stock
Training seed
1000 only, repeatedly reset after game failure
Held-out seeds
2000, 2001, 2002; excluded from training
Workers / device
4 simulator hosts / CPU; two PyTorch threads
Aggregate rollout
256 selections = 64 per worker
Minibatch / epochs
64 / 4
Learning rate / optimizer
0.0003 / Adam
Gamma / GAE lambda
0.999 / 0.95
PPO clip / entropy coefficient
0.2 / 0.01
Value coefficient / gradient norm cap
0.5 / 0.5
Game cap
3,600 simulated seconds; ordinary failure usually occurs first
Latest learner budget
240 minutes or 10,000,000 selections, whichever first
The run stopped normally at its four-hour learner limit. Setup, initial evaluation and final evaluation are
outside that timer. Resuming keeps policy/optimizer weights but starts new episodes, metrics and a fresh
timestep counter; it is not a saved live city.
A label such as try 9/100 counts the current scheduling block. With one seed, reaching 100 starts another block on seed 1000; it
does not stop training. Gamma discounts every policy selection, including intermediate selections. Shorter fragments with more
workers may affect delayed credit. Sources: run config, train.py and parallel.py.



## PDF page 6

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
06
5 / Four hours: what improved?
The model improved its usual score on the practiced layout, without setting a new best.
Comparison
First 100 games
Last 100 games
Mean score
24.88
52.10
Games scoring 50 or more
7 / 100
75 / 100
Hourly mean scores were 31.97, 45.92, 52.64 and 52.64. The final two hours show a plateau in these
averages. The best game still scored 73, matching the earlier record.
Total / rate
Measured result
Learner wall time
14,400.7 seconds
Gameplay commands
1,650,223
Selections / second
157.7
Commands / second
114.6
Weight updates
Confirmed; final checkpoint saved
Data: archived worker monitor CSV and summary.json, 4,549 completed games. Games are merged by monitor completion time.
The rolling mean covers 100 games. Hour bins use monitor time and may exclude boundary completions; setup precedes the
learner timer. First/last comparisons are within this resumed run, not random initialization versus final policy.



## PDF page 7

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
07
6 / Did it learn other layouts?
The held-out evidence remains weak despite better training-seed consistency.
Seed
Starting sampled
Final sampled
Final deterministic
2000
0
3
0
2001
2
0
2
2002
0
0
0
On the practiced seed, the model learned a limited, repeatable pattern. On these unfamiliar seeds, final
scores are only 0-3. This does not demonstrate a strong network-building strategy that transfers to other
layouts.
Three held-out seeds are a small evaluation, not a reliable estimate across all city variations. A broader,
predeclared test would be required for a general performance claim. No transfer to the commercial game
has been tested.
Source: archived four-hour summary.json. Sampled and deterministic evaluations are different action-selection modes. The three
evaluations are not independent training runs or a controlled comparison of learning algorithms.



## PDF page 8

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
08
7 / How this compares with the
beginning
Historical baseline: the first run, not the current policy.
The first run completed 242 games in 431.1 seconds. Only four games earned any trips; the best was
seven. All held-out evaluations scored zero. The final deterministic replay spent 25 road tiles, then waited
116 times and failed with no trips.
The later single-seed experiment clearly found more reliable ways to earn some trips. However, these
runs differ in starting weights, seed schedule, duration and worker count. They do not isolate which
change caused the improvement.
Baseline: first-full-tools, revision 30ef7ab, 65,536 selections, 35,610 commands, random seeds 1000-1099. Baseline mean score
0.0413; all 242 games failed normally. The original 16-page report is preserved unchanged, including survival, optimizer,
material-use and network/parameter graphics.



## PDF page 9

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
09
8 / Can parallel games make it
faster?
Yes for measured collection throughput; faster convergence is not established.
Two short trials at each worker count measured about 60.3, 70.3 and 74.9 commands/second with one,
two and four workers. That is roughly 17% and 24% more commands with two and four workers than one
in this benchmark.
These were 12-second trials after warm-up, in order 1/2/4/4/2/1, while another training run was active.
They are under-load comparisons, not hardware maximums. Disposable clones performed brief learner
updates without overwriting production weights.
The completed four-hour run averaged 114.6 commands/second under its own workload. That number is
not directly comparable to the short under-load benchmark. Games/second also depends on how long the
model survives: better play can make each game take longer.
Why speed does not scale fourfold
Simulator work runs in independent .NET processes, but Python JSON processing still shares the GIL.
Policy calls are batched centrally. The thread-pool wrapper keeps large observation arrays in shared
Python memory, avoiding another process-pipe copy.
Sources: archived parallel-benchmark.json, parallel.py and latest summary. No deliberate 0.8-games/second limit was configured.
Throughput is not a prediction of time to 1,000 trips.



## PDF page 10

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
10
9 / Fixes since the first report
The learner, the viewer and the simulator need separate evidence.
Visible best-game recording
Training now saves exact ordinary commands for the best game globally and per seed. Ranking is
highest trips, then longest survival, then fewer rejected actions. Partial games can qualify at stop. The
native viewer supports play, step, 1x/4x/16x, restart and reload-best.
Cars appearing to drive across grass
Driveway edits removed the old connection from the drawn map immediately, while active cars retained
committed lane snapshots and return routes. The viewer now draws pale gray retiring pavement until
those trips clear. This does not reopen routing, alter stock or change the reward.
Ctrl+C crash during parallel training
The earlier shutdown waited on failed workers before saving, and invalid pipes caused another error.
Windows hosts now have separate process groups; interruption saves final.zip atomically before worker
cleanup. Worker/replay cleanup failures produce warnings after the checkpoint is safe.
The crashed run had no final.zip. Its valid latest.zip at 423,892 selections was used for the four-hour run.
A periodic save can lose roughly the last two minutes before a crash. A new run folder is required when
resuming.
What the checks establish
Forty simulator suites, seven environment tests, four workflow tests, three parallel tests, the shutdown
test and five-map protocol checks passed at the fix revision. The earlier
73-trip/479.8-second/480-command replay verified in headless and native runtimes. That is a different
recording from the latest 73-trip/461.4-second best.
Source: revision e6119eb and documented validation. Exact command replay and internal tests do not establish commercial-game
parity. Roundabout connectors, parking and other rendering/geometry approximations remain documented limits.



## PDF page 11

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
11
10 / Decisions and what comes
next
Preserve the task while testing specific explanations for the plateau.
Decision / change
Status
High score, OriginalReference, structured input, trial and
error, all tools
User-selected task; 1,000 trips remains provisional goal
Branch mohammad; main stays playground
Implemented and published to GitHub
Repeated seed practice, then one seed only
Implemented; faster learning was a hypothesis, not a
controlled result
Best-game maps and live seed/wait/ETA output
Implemented
Parallel collection and four-hour run
Implemented and explicitly authorized; run completed
Every update, decision, analysis and performance finding
documented
Ongoing project requirement; report/graphs/evidence
archived
Recommended next investigation, not implemented
Inspect recurring failure states and count working house-to-destination connections, material waste and
missed demand. Then compare one targeted change at a time. Candidate bottlenecks include spatial
action coordination, missing connectivity features, delayed credit, sparse reward and exploration.
No connectivity labels, new reward shaping, route suggestions, demonstrations or recurrent memory
have been added. The observations suggest possible bottlenecks; they do not prove a single cause.
More unchanged four-hour training is not currently recommended.
The original report's proposals are still proposals unless the history explicitly records their implementation. No new training was
started for this report. User choices, engineering choices, measured facts and hypotheses are separated in
training/EXPERIMENT_HISTORY.md.



## PDF page 12

MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026
12
11 / Exact inputs and evidence
Reference for checking what changed between model versions.
Grid channel
Encoding
0
Playable-cell visibility
1-3 / 4-8 / 9-11
Terrain / infrastructure / building-kind categories
12-19 / 20-27
Building colors / eight connection bits
28
Pending removal
29-31
Demand / 20; reservations / 20; overcrowding / 50
32-39
Eight entrance/driveway directions
40-42
Car count / 10; max speed / 2; max current wait / 60
43-47
Motorway endpoint; retirement; other x / 50, y / 30; number / 20
48-49
First selected cell; existing selected motorway endpoint
Global indices
Encoding
0-5
Six inventories: roads / 100, other materials / 10
6-8
Time / cap; week / 100; trips / 1000
9-24
Two offers: six type flags, amount / 100, roads / 100 each
25-28 / 29-41
Four action phases / thirteen selected tools
All inputs clip to [0, 1]. Schema: full-tools-staged-grid-v1. Unknown colors, changed grid sizes or more than two upgrade offers raise
errors rather than being silently truncated.
Evidence and reproduction
Latest run: seed-1000-parallel-02; source e6119eb; resumed parallel-01/latest.zip; 240-minute budget. Sources: archived configs,
summaries, episodes, monitor and optimizer CSV under docs/training/evidence-2026-10-28/. The evidence index includes hash
manifests and all historical PDF figures. Checkpoints/player binaries remain local and are not backed up by the documentation
archive.
Readable sources: training/README.md (contract), CURRENT_STATUS.md (latest results), EXPERIMENT_HISTORY.md
(decisions/analysis), QUICKSTART.md (commands), docs/training/README.md (evidence). Rebuild source:
docs/training/build_current_report.py. Algorithm explanations follow the implemented SB3-Contrib MaskablePPO setup and the
original report's PPO references; no algorithm comparison was performed.

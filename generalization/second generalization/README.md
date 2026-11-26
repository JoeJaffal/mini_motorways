# Second generalization: controlled synthetic-traffic experiment

## Purpose and current status

User decision (26 November 2026): implement our own external-layout experiment,
separate from first generalization's comparison against published KDD metrics.
The future GP policy builds roads under Mini Motorways construction demand;
freeze that design and compare it with the published reblocking heuristic under
identical held-out vehicle requests in SUMO. No DRL model retraining is required.

The paired SUMO pipeline is implemented and has run successfully on Harare.
SUMO 1.28.0 is installed in ../.venv. No GP policy has been integrated or tested.
The supplied candidate is another heuristic run, used ONLY as an engineering
fixture. The eight unit tests and real SUMO acceptance checks pass.

Read [the current pilot report](results/pilot-004/REPORT.md) and
[the acceptance evidence](results/validation-002-validation.json).
Results have `research_ready: false`: implementation success does not establish
real-world validity, a usable native-game building layout, or GP performance.

## How this differs from first generalization

| Item | First experiment | This experiment |
|---|---|---|
| Main question | GP versus published graph-metric results | How do fixed designs serve the same synthetic travel needs? |
| Primary comparator | Published KDD DRL-GNN values | Executable published Brelsford heuristic underlying HS-MC |
| Evaluation | NR, AD, SC | SUMO completion, failure, delay and travel-time outcomes |
| Construction constraint | Released KDD 33-segment protocol | Shared source-cost cap, with actual spending reported |
| Traffic simulation | None | SUMO, with the same request manifest for both designs |
| Learned baseline weights | Not needed for table comparison | Not needed for the heuristic |

This does not reproduce KDD's exact HS-MC evaluation settings or DRL-GNN network.
The original heuristic source and our local run provenance are documented in
[the preceding verification](../VERIFICATION.md).

## Frozen pilot inputs

The preparation command copies, rather than mutates, the first experiment's
canonical Harare graph and checked 50x30 corridor projection. Static inputs are
under data/:

- scenario.json: 32 places, 54 junction nodes, 85 graph edges including 20
  existing road segments. Stable IDs retain source geometry and costs.
- grid.json: source junctions and full corridor paths on the common grid.
  Geometry is audited again before each run.
- reference-design.json: Brelsford probabilistic reblocking, fixed seed 0,
  alpha=8, wholepath=True, stopping at universal parcel access. The source
  revision and the fact that this is not an exact KDD reproduction are recorded.
- construction-setup.json: fixed seeded assignment of 24 houses and eight
  destinations, one color. These are synthetic roles, not measured Harare POIs.
- protocol.json: the predeclared budget, seeds, physical assumptions and SUMO
  settings, with scenario/reference/setup hashes.

The primary baseline was selected before traffic evaluation; it is not selected
by finding a favorable traffic seed. It adds 11 corridors and costs
1.2344853073654307 in original source-weight units. This is the common budget
CAP. The other design may spend less; its actual cost and raster road length
are reported. Equal cap does not imply identical spending or physical length.
Neither source cost nor the synthetic grid scale is calibrated monetary cost.

## Candidate construction and the GP input boundary

Use bridge.Bridge or pipeline.DesignState for THIS experiment. They enforce:

- Preserve all existing roads and use only the same legal source corridors.
- Add one complete corridor at a time, attached to the existing road network.
- Reject duplicate additions, barriers, unknown edges and budget violations.
- Do not apply KDD's stage-one priority mask or its 33-step limit here.
- The candidate may stop early. Disconnected places are not silently repaired.

```python
from pipeline import read, ROOT
from bridge import Bridge

bridge = Bridge(read(ROOT/'data/scenario.json'),
                read(ROOT/'data/grid.json'),
                read(ROOT/'data/construction-setup.json'),
                read(ROOT/'data/protocol.json'))
payload = bridge.observe()
# Future host adapter supplies GP's actual observation format and maps actions.
payload = bridge.apply(source_edge_id)
# Or submit exactly one full corridor path; reverse orientation is accepted.
payload = bridge.apply_complete_corridor_path(cells)
design = bridge.freeze('GP revision / run identifier')
```

The input payload contains current roads, available legal corridors, remaining
cost, inaccessible places, the static grid mapping and construction-role setup.
No mbrl tensors or GP-specific action format are assumed. The frozen output is
schema_version=1, scenario_sha256, a descriptive label, and an ordered list of
source-edge IDs in actions. An example is examples/candidate-design.json.

The native Mini Motorways demand generator remains the intended construction
signal. We save its setup and seed, rather than pretend an explicit SUMO OD file
is already consumable by GP. Connecting native game time/demand, placing real
house/shop footprints and driveways, and binding GP's actual observations remain
host-adapter work. The grid's parcel markers are not valid spawn fixtures. Any
such adapter must preserve legal corridors and document parcel access semantics.
No candidate is automatically altered to pass validation.

## Traffic generation and what 'held out' means

The runner validates and saves both complete designs before it generates the
evaluation request lists. A request is `(id, origin place, destination place,
requested departure time)`. The generator uses the fixed role assignment:

1. Uniformly sample one of the 24 house origins.
2. Uniformly sample one of the eight destinations.
3. Uniformly sample an integer departure time in the departure window.

Default: 120 one-way vehicle requests in 600 seconds, repeated with seeds 1001,
1002 and 1003. Construction seed is 0 and cannot also be an evaluation seed.
Both designs get EXACTLY the same list for each evaluation seed. The lists and
hashes are saved, and routing is checked not to change IDs, endpoints or requested
departure times. No separate road-based randomTrips generator is called.

These are independently sampled vehicle trips, not the game's finite reusable
household fleet or its round-trip lifecycle. No trained demand model is used.
The generator and dynamics differ from native Mini Motorways: this is held-out
synthetic external evaluation, not simply a new seed of identical game dynamics.
New destination assignments or intensity changes are separate scenarios to
predeclare, not choices to tune after inspecting GP results.

## SUMO network and access representation

Both designs go through the same exporter. Each constructed corridor becomes
one lane per direction, with the same grid path and physical assumptions. There
are no automatically created graph crossings. The exporter checks that SUMO
preserves every intended external edge and its endpoints.

Defaults (engineering assumptions, editable before research evaluation):

| Setting | Value |
|---|---:|
| Physical grid-cell scale | 10 meters |
| Road speed | 8.33 m/s, approximately 30 km/h |
| Access-connector speed | 3 m/s |
| Lane width | 3 meters |
| Vehicle length / minimum gap | 4.5 / 2.5 meters |
| Driver tau / sigma | 1 second / 0 |
| Vehicle speed factor / deviation | 1 / 0 |
| Junctions | Unsignalized priority, default radius 5 m |
| Simulation step | 0.5 seconds |
| Final cutoff | 1200 seconds |
| Teleport recovery | Disabled |
| Departure expiry | Disabled |

The scale is synthetic. It is NOT an estimate of actual Harare dimensions or
travel behavior. Source costs and physical raster lengths are both reported.

Parcel endpoint locations are fixed across designs. To retain KDD's allowance
of road access at ANY parcel boundary node, every built boundary-road node is
an admissible access. We use a TAZ per parcel plus separate directed source and
sink connectors. A source has no incoming edges; a sink has no outgoing edges.
Therefore vehicles cannot traverse a parcel as a shortcut between roads. The
runner also rejects any returned route with an access connector in its interior.
These are virtual intra-parcel access links, not extra constructed public roads.
Their travel time is included; they are not charged as source-corridor investment.

The router can choose different access nodes and paths in the two designs, under
the same rule. This changes how the SAME physical parcel-to-parcel request is
served; it does not resample its origin or destination. An inaccessible parcel
gets no artificial connection or nearest-road snapping. Missing routes between
source-graph-connected endpoints are treated as exporter/routing errors and
abort the run, rather than penalize a design for an implementation mismatch.

Routing uses duarouter's Dijkstra routing and the same settings in both networks.
It chooses routes before simulation using the exported network, not a dynamic
user-equilibrium assignment. Vehicles then interact in SUMO along those routes.

## Accounting and reports

Every requested trip must receive exactly one outcome:

- completed;
- unroutable (no endpoint access or disconnected road components);
- never_departed by the cutoff;
- unfinished at the cutoff;
- removed for another reason.

SUMO's `vaporized="end"` denotes end-of-run truncation and is classified by its
depart/arrival fields, not as an exceptional removal. Unexpected IDs, missing
routed requests and changed endpoints cause an error. Collision or teleport
counts invalidate the run. Export warnings are preserved in comparison.json.

Reports show all completion/failure counts, completion fraction, completed-trip
travel time, requested-departure-to-arrival time, waiting and departure delay.
For paired time differences we use ONLY trip IDs completed in BOTH networks,
and always show that subset's size alongside all completion counts. We never
infer a superior design merely because its surviving trips are faster.

Across-seed summaries currently include mean/standard deviation of completion
count differences. Three seeds are an engineering pilot, not a powered study;
there is no significance claim. NR/AD/SC are retained as supplemental source-graph
measures, without first experiment's segment-budget eligibility label.

## Commands

Run from this folder. The shared isolated environment is already installed.

```powershell
# Only needed on a new environment:
../.venv/Scripts/python.exe -m pip install -r requirements-sumo.txt

# Prepare/reset the documented pilot defaults. Do not run over custom inputs.
../.venv/Scripts/python.exe -B pipeline.py prepare

# Validate/observe a supplied candidate without SUMO:
../.venv/Scripts/python.exe -B pipeline.py observe --design examples/candidate-design.json --output candidate-state.json

# Real paired experiment; choose a NEW output name for every run:
../.venv/Scripts/python.exe -B pipeline.py run --candidate examples/candidate-design.json --output runs/my-pilot

# Test suite:
../.venv/Scripts/python.exe -B test_pipeline.py
../.venv/Scripts/python.exe -B integration_checks.py --prefix my-check-001
```

Pass `--bin-dir PATH` to run with another installation containing netconvert,
duarouter and sumo. Exact executable versions are recorded. Use `--config PATH`
for a predeclared alternate intensity/horizon/physical assumption; reference and
construction-setup identities must still match. The installation tested here is
SUMO 1.28.0. No GUI windows or GPU are required.

Large/raw network, routing and simulation artifacts stay under ignored runs/.
A durable small snapshot under results/<run-name>/ retains frozen protocol and
designs, request manifests, individual outcomes, comparison JSON and Markdown.
Use unique run names: existing evidence is not overwritten. Protocol/scenario/
design/setup hashes and implementation-file hashes identify the evaluated inputs.

## Verification actually performed

- Eight unit tests pass: budget legality, corridor constraints, seed/reordering
  reproducibility, held-out seed separation, complete accounting, paired metrics,
  topology integrity and the cost-budget GP bridge.
- Real paired pilot (pilot-004): two legal heuristic designs, three seeds,
  120/120 requests completed on each design per seed. Zero observed collisions
  or teleports. This is an engineering test, not a GP result.
- Same design versus itself: identical per-request outcomes on all three seeds,
  zero paired differences (validation-002-self).
- No-added-road candidate: 70, 79 and 72 requests were explicitly unroutable;
  remaining completion counts were 50, 41 and 48 (validation-002-disconnected).
- Cutoff stress: all 120 requests retained: 64 unfinished and 56 never departed,
  zero completed (validation-002-cutoff).
- All-unroutable workload: its single request was retained as unroutable, even
  with no vehicles to route/simulate (validation-002-validation.json).

A first cutoff check exposed the `vaporized="end"` classification error; fixed
and regression-tested. validation-001-cutoff is historical, superseded evidence,
not a valid classification result. Early pilot-002 used earlier junction export
settings; pilot-004 is the current pilot. All historical files remain historical.

## Remaining limitations and research interpretation

The current network export emits some intersecting-left-turn geometry warnings
at junctions with multiple parcel-access connectors. Accepted pilot runs have no
observed collision/teleport, but this does not establish junction correctness
under heavier traffic. Radius/scale checks at 15, 20 and 30 meters per cell did
not eliminate all warnings; results/geometry-checks.json records those checks.
We retained the declared 10m/5m defaults rather than select a configuration by
favorable traffic results. Junction/connector geometry needs further review
before publication-quality traffic claims, and failures at higher loads must
not be hidden. `research_ready` is deliberately false.

The native-game GP host remains pending, including building/driveway placement
and matching its access model to the SUMO parcel abstraction. The heuristic is
access-oriented and does not optimize demand/congestion, whereas GP will see
construction demand. A positive result supports transfer relative to THIS
published infrastructure heuristic under specified synthetic assumptions. It does
not establish superiority to KDD DRL-GNN or performance under measured Harare
traffic. Additional maps, role assignments, demand levels and held-out seeds
remain necessary for broader claims.

## Sources

- Published reblocking paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC6114988/
- Original code: https://github.com/brelsford/topology/tree/2232a3da3cfa7bbe3f4e5eb48049baac6e67f662
- KDD paper (names this baseline HS-MC): https://fi.ee.tsinghua.edu.cn/~dingjingtao/papers/RoadPlan-KDD23.pdf
- SUMO installation: https://sumo.dlr.de/docs/Downloads.php
- Explicit trips, TAZ routing and routing failures: https://sumo.dlr.de/docs/Demand/Shortest_or_Optimal_Path_Routing.html
- Vehicle outputs and cutoff accounting: https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html
- Source input notice/license: ../first%20generalization/data/KDD-LICENSE.txt

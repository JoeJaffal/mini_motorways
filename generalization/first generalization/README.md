# First generalization: GP transfer evaluated with KDD graph metrics

## Purpose and current status

User decision (26 November 2026): first evaluate the future GP Mini Motorways
policy using KDD's original road-planning metrics and constraints. No SUMO,
DRL-GNN retraining, or mbrl model integration is part of this experiment. The GP
branch is not ready. This folder prepares the scenario, observation/action
boundary and evaluator; it does not contain a GP performance result.

Implemented:
- Portable, hash-linked Harare graph: 54 nodes, 85 edges, 32 places, 20 existing
  road edges and 65 candidate segments. No pickle is needed for normal use.
- Released-code action masks and 33-addition episode limit.
- Ordered design validation and NR, AD, SC evaluation, with per-action trace.
- A 50x30 corridor projection with no detected node merges, corridor overlaps,
  diagonal crossings or changed cyclic junction order. A bounded layout search
  and one-waypoint detours preserve the source graph; original distances and
  costs remain the scoring reference.
- Model-neutral observation/action bridge, including exact complete-corridor
  path mapping. No assumed mbrl tensor shape or GP observation format.
- Seeded construction role assignment: default 24 houses, eight destinations,
  all one color. This is an engineering default, not a KDD dataset attribute.
- Engineering fixtures, automated tests, upstream parity checks and reports.

NOT yet implemented/validated:
- Simulator house/shop footprints, driveways, demand reset/replay and native
  game placement. `runnable_in_game` deliberately remains false.
- GP policy adapter or inference. No model has been trained or evaluated here.
- Proof that the released configuration is exactly the one used for the paper's
  reported DRL-GNN checkpoint. Published numbers are external point estimates.

## Input format and the future GP integration

`data/harare.json` is the canonical scenario. Nodes have stable IDs and source
coordinates. Edges have stable IDs, source weights, existing/barrier flags and
original indices. Places retain ALL parcel boundary nodes. The model must not
replace these with building-centroid distance for scoring.

`data/grid-draft.json` maps each source junction to a grid cell and each source
corridor to an ordered sequence of adjacent cells. Existing and candidate roads
share this map. Corridor paths use explicit links: merely adjacent grid cells
must not automatically create additional connections. Source costs are charged
once per completed corridor, not per raster cell. The grid's physical lengths
are not the KDD metric lengths.

`data/construction-setup.json` specifies reproducible house/destination roles,
colors, and the construction-demand seed. The future host adapter will use the
native Mini Motorways demand generator, not train another generator. The seed
is construction context; there is no randomly generated evaluation traffic in
this graph-only experiment. NR/AD/SC do not use destination weights or colors.
Role counts can be changed BEFORE evaluating GP; record any such change.

The bridge interface is:

```python
bridge = Bridge(scenario, grid, construction_setup)
payload = bridge.observe()
# Future adapter supplies the GP's real observations and translates its actions.
payload = bridge.apply(source_edge_id)
# Alternatively, accept exactly one complete corridor's ordered grid path:
payload = bridge.apply_complete_corridor_path(cells)
design = bridge.design('GP run identifier')
```

A payload includes built corridors, legal corridors, parcel boundaries, grid
paths, construction setup, remaining segment budget and current stage. The GP
adapter will translate the actual GP branch's inputs/outputs; the policy is not
required to consume this JSON directly. A saved design is an ORDERED list of
source-edge IDs plus the exact scenario SHA-256. Order is necessary for NR.
Partial corridors, off-corridor drawing, duplicate construction and illegal
masked actions are rejected at this boundary. Multi-corridor strokes must be
split in their construction order. Undo/removal/motorways are not supported by
this add-only source protocol. The host must enforce the budget/mask before
accepting actions rather than repairing a finished illegal design silently.

The unresolved host task is specific: real game buildings occupy area and have
access directions, whereas KDD parcels can access roads at any boundary node.
Parcel centroid markers in the draft are NOT valid spawn positions. Before
connecting GP, select and verify building footprints/driveways and ensure they
do not obstruct corridors or silently restrict/change source access. If exact
representation is impossible, report that mismatch rather than claim strict
KDD equivalence. The grid check establishes corridor topology only.

## Metrics and construction protocol

- NR: first added-segment count at which all places have boundary-road access.
  Null means access was not achieved. It is not the final number of additions.
- AD: average shortest road distance over distinct pairs of places, using the
  minimum between their accessible boundary nodes. Shared accessible nodes give
  zero distance. Any unreachable pair makes AD null (infinite/unavailable), not
  an average over only reachable pairs.
- SC: sum of original source edge weights for added roads, excluding existing
  roads. Source geometric lengths are also retained, but not substituted.
- Stage-one mask: unbuilt edge incident to a road node; prioritize such edges
  incident to an inaccessible place's nodes if any exist. After full access,
  any otherwise permitted road-connected addition is allowed.
- Budget: 65 initially non-road segments * 0.5 = 32.5. Released RoadEnv.step
  stops after the total exceeds that value, producing 33 additions. The
  epwoth.yaml configuration also gives maximum sequence length 33. This is
  explicitly named the released-code protocol, not an inferred 32-step cap.

The original Brelsford heuristic stops at full access (11 additions in our saved
seed-zero example), so it is an incomplete final-budget fixture here. Its final
AD/SC must not be presented as a matched 33-step result. We do not arbitrarily
extend that heuristic and label it original HS-MC.

## Running (from this folder)

Normal evaluation uses Python's standard library. The parent isolated environment
can also be used; no GPU is needed.

```powershell
python experiment.py observe --output examples/initial-observation.json
python experiment.py smoke-design --seed 0 --output examples/smoke-seed0.json
python experiment.py evaluate --design examples/smoke-seed0.json --output results/smoke-seed0.json
python report.py --design examples/smoke-seed0.json --output results/smoke-report.md
python bridge.py --output-dir examples/bridge
python test_experiment.py
```

Resume a supplied sequence with `bridge.py --design PATH --edge eNNN` (choose an
ID from the observation's legal list). This writes the updated observation and
design. `smoke-design` is masked random construction for engineering checks;
it is NOT a proposed research baseline or the GP policy.

`grid_projection.py` regenerates the corridor draft and SVG. `prepare.py`
regenerates the scenario and heuristic examples from the hash-verified local
input and pinned topology source used in the previous verification. It needs
the parent environment. `check_upstream.py` compares against the KDD source in
`../../tmp/kdd-upstream` and needs the dependencies pinned in
`requirements-audit.txt`. It loads graph code without the package initializer
that otherwise imports unrelated RoadEnv/geopandas; graph methods are unmodified.

## Validation and measured engineering results

Ten automated checks cover inaccessible-demand accounting, all-roads anchors,
repeatability, budget termination, duplicate/disconnected actions, scenario hash
mismatch, incomplete heuristic design, boundary-node distances, grid topology,
weighted grid/source distance equivalence, and bridge replay/path rejection.

Direct upstream-code checks on 33-step random and 11-step heuristic sequences
agree at each step for action masks, accessibility and cost; NR agrees, and AD
agrees after universal access. See `results/upstream-parity.json`.

The full-network anchor gives AD=0.47452159485682716 and SC=11.500936793918758,
which round to Table 3's 0.47 and 11.50. This validates units/metric alignment on
that anchor; it does not reproduce the learned model or its training process.
The random fixture gives NR=10, AD=1.0165060966813824, SC=6.241118433413958 at
33 additions. These values test the pipeline and say nothing about GP quality.

## Published comparison and provenance

`data/published_reference.json` stores cited, rounded Table 3 values separately
from measured results. Reports mark those rows as published. A complete legal
GP design can be compared using this released-code protocol, with the input
representation limitation above disclosed. No paired significance test against
the authors' unavailable runs is possible. Do not tune on one map and then claim
that same map is untouched generalization.

- KDD paper: https://fi.ee.tsinghua.edu.cn/~dingjingtao/papers/RoadPlan-KDD23.pdf
- Code revision: https://github.com/tsinghua-fib-lab/road-planning-for-slums/tree/a3d86fbb201545415ddc1e09ea997b20089effd1
- Protocol: road_planning/envs/road.py, RoadEnv.step and _compute_total_road_steps.
- Metrics/mask: road_planning/envs/my_graph.py, _get_edge_mask, td_dict_init,
  face2face_avg, td_dict_update, interior_parcels_update.
- Config: road_planning/cfg/epwoth.yaml (upstream spelling).
- Original heuristic: https://github.com/brelsford/topology/tree/2232a3da3cfa7bbe3f4e5eb48049baac6e67f662
- Input hash and source indices are embedded in data/harare.json.

The pinned raw downloads and environment remain local-only in the parent
folder. Portable scenario data, small example/results manifests, source hashes,
code and this documentation are retained. See data/KDD-LICENSE.txt for the
upstream repository license. No weights, game binaries or private research
material are included.

# KDD generalization pipeline

## 2026-11-25 pretrained artifact clarification

The absence of a checkpoint in the inspected tracked tree establishes only
that no checkpoint was found there. Targeted public searches for pretrained
weights, checkpoints and plan.p downloads returned the official code and paper
but no verified artifact download. Existence elsewhere remains unresolved.
The earlier preference for immediate reproduction is superseded by seeking an
author-provided checkpoint or final Harare edge list first. A final edge list
with provenance suffices for the fixed-network SUMO comparison.

An alternative without learned weights is the paper's greedy road-cost baseline
or its genetic algorithm, using the same Harare input and budget. This would
change the comparator and must be named explicitly. It can support pipeline
validation while DRL-GNN remains pending. The paper reports these baseline
implementations in its framework. No replacement comparator has been selected,
and no author has been contacted. Source consulted:
https://davymorgan.github.io/assets/pdf/KDD23-road-planning.pdf

## 2026-11-25 evaluation protocol assessment

Engineering choices for the pilot, following the user's request to choose a
defensible implementation path:

- Obtain a verified upstream DRL-GNN plan/checkpoint if available. Otherwise
  reproduce DRL-GNN on Epworth using the pinned source and epwoth configuration.
  Label that result a local reproduction. Retain all compatibility patches,
  dependency versions, seed, action sequence and checkpoint hash.
- Select the checkpoint using the upstream planning reward before generating
  evaluation traffic. Freeze the baseline design and its source edge IDs.
  Set the pilot's common budget to its measured added source-edge cost. This
  defines a comparison at the reproduced baseline's spending level. Both
  designs must satisfy that cap before SUMO runs. A numerical cap awaits the
  baseline, and is a required comparison input.
- Charge construction by selected source corridors using upstream edge weights.
  Grid subdivisions retain source corridor IDs and cannot create additional
  buildable connections. Check crossings, shared cells and access points for
  accidental junctions. Report geometric length separately. Confirm coordinate
  units before selecting a physical scale for SUMO.
- Preserve source parcel access rules explicitly. A parcel with multiple access
  points needs a common endpoint mapping fixed before either design is evaluated.
  Neither arbitrary centroid snapping nor design-dependent endpoint selection
  establishes equivalent access. Resolve this from source geometry before export.
- Compare reachability and shortest-path distances before and after conversion
  using the same source costs. Reject new connectivity, lost connectivity and
  reduced distances beyond numerical tolerance. Also report geometric distance
  distortion and all affected places. Grid resolution is an engineering input
  to validate against these gates.
- Use the implemented uniform OD generator as a declared pilot workload. Its
  assumptions are synthetic. Fix request count, departure window, vehicle
  parameters, simulation end and seeds before inspecting comparison outcomes.
  A single map and a supplied candidate establish pipeline functionality.
- Preserve departure delays and failures in the report alongside completed-trip
  durations. Disable teleport-based recovery for the pilot so an artificial
  relocation cannot appear as a successfully completed road journey. Verify
  this setting against the installed SUMO version when the runner is built.

Reproduction proposal awaiting long-run authorization: one training seed (0),
100 upstream iterations, epwoth configuration, Epworth_Demo input, rl-ngnn
agent after verifying its architecture mapping. Use the upstream best-reward
checkpoint and deterministic greedy inference. The configuration requests
1,200 episodes per iteration with maximum sequence length 33. Runtime on this
machine is unmeasured. First perform dependency and short execution checks,
then report any required source repairs before a full run. Training work must
use mohammad as required by AGENTS.md. The generalization branch holds pipeline
work. The user has requested implementation, while AGENTS.md explicitly reserves
authorization for another long training run.

Verification for this assessment was source inspection of road.py stage
termination and road_planning_agent.py checkpoint selection/persistence. No
training or traffic performance measurements were produced. The checkpoint
contains best/current plans and actor_critic_dict, so obtaining one can avoid
retraining. Remaining blockers to the complete pilot are the DRL-GNN artifact,
validated grid conversion, a supplied or scripted legal candidate, SUMO setup
and actual paired-run acceptance checks.

## 2026-11-25 Harare pilot implementation update

This update supersedes the provisional workload and comparison rules below.

**User decisions.** Use Harare (Epworth) from the official KDD repository and
DRL-GNN as the primary baseline. Retain the original baseline and evaluate its
grid-converted version. Both designs share fixed existing roads, place access,
obstacles and permitted construction corridors. Exclude motorways for the
pilot. Require a common added-road cost or length cap before comparison and
apply it to both designs. Reject conversions that create shortcuts or lose
existing accessibility, and report changes in topology and distances.

Use Mini Motorways demand during construction and persist destination
assignments, demand settings and seed. Defer the construction replay interface
until the GP implementation is available. Use a separate, road-independent
held-out synthetic trip manifest for the paired SUMO runs. Pilot acceptance
requires legality and budget parity, export connectivity and endpoint checks,
identical requests, complete trip accounting, repeatable results and a matching
design-versus-itself SUMO run.

**Upstream inspection.** Pinned [official source](https://github.com/tsinghua-fib-lab/road-planning-for-slums/tree/a3d86fbb201545415ddc1e09ea997b20089effd1)
at `a3d86fbb201545415ddc1e09ea997b20089effd1`. The input is
`data/Epworth_Demo.mg` (SHA-256
`4145ba0189e9d99d5f973abf3b71ae15aeda4edb33b932683bff225cac5fdbbf`).
The complete tracked tree contains the initial graph, preprocessing source and
figures, but no machine-readable final design or model checkpoint. The
Harare-named configuration is `road_planning/cfg/epwoth.yaml` (upstream
spelling), with two GCN layers, `build_ration: 0.5`, 100 iterations,
1,200 episodes per iteration and maximum sequence length 33. The published
revision does not establish the exact seed, checkpoint or configuration used
for the published Harare result. The build ratio governs stage transitions in
the upstream environment and does not provide a common length cap. Upstream
accumulates selected graph edge weights as road cost. The supported inference
path appears to be `road_planning.train --infer`; the standalone `eval.py`
imports an agent module absent from the tree. No inference or training was run.
The checkout, archive and tree listing under `tmp/kdd-*` are local-only.

**Implemented and checked.** `simulation/generalization/workload.py` generates
seeded, uniformly sampled ordered pairs of distinct endpoints and integer
departure times from an explicit time window. It joins the manifest to routing
failures and SUMO tripinfo, requiring an output record for every routed trip.
Configure SUMO with both tripinfo unfinished and undeparted output enabled.

```text
python -m simulation.generalization.workload generate endpoints.json trips.json --seed 15 --count 100 --departure-window 60
python -m simulation.generalization.workload account trips.json unroutable.json tripinfo.xml outcomes.csv
```

A synthetic XML fixture passed repeatability, endpoint-order independence,
classification of all four outcomes and rejection of a missing routed trip.
SUMO and netconvert were not found on PATH. The Harare converter, common budget
value, construction scenario, exporter and comparison report remain pending.
The real baseline requires a supplied plan, an upstream checkpoint, or an
authorized reproduction run. No pilot acceptance or performance result yet.

## 2026-11-25 planning update

User decisions: prepare the pipeline independently of `mbrl` and integrate the
GP model after its branch is ready. Represent the KDD baseline and the candidate
in a common grid format with source mappings. Generate seeded construction demand,
then replay a separately seeded evaluation workload on both frozen networks.
Readiness means a supplied legal design completes the full comparison. Scripted
or manual validation provides engineering evidence only.

Proposed implementation:

1. Ingest a pilot KDD map and baseline. Record source provenance and map source
   junctions, road segments and traffic endpoints to stable grid identifiers.
   Check directionality, connectivity and any topology lost in conversion.
2. Define and validate shared scenario data, construction constraints and road
   designs. Keep the model adapter boundary to scenario initialization, state
   access, building actions and final network extraction.
3. Generate and save construction demand and separate held-out evaluation trip
   manifests. Use stable endpoint IDs and identical request IDs, endpoints and
   departure times across both networks. Resolve routes per network.
4. Export both fixed designs through the same SUMO pipeline. Use matched settings
   and report paired results, including unfinished and unroutable requests,
   travel times for completed trips, and comparable construction cost where defined.
5. Run the full pipeline with a supplied legal design. Verify reproducibility,
   manifest equality and failure accounting before integrating the GP adapter.

Open questions: which KDD source and pilot map to use, which baseline and road
layers are fixed, and which construction constraints apply to the candidate.
Determine from the future GP implementation whether it uses a fixed evolved
program or runs additional search per map. Record the latter's compute budget
if applicable.

Status: planning on `generalization`. No implementation, simulation, training
or performance measurement was performed for this update. See the
[experiment history](../../training/EXPERIMENT_HISTORY.md) for earlier training
and generalization evidence.

## 2026-11-25 latest user correction: published heuristic, no DRL training

This entry supersedes the DRL-GNN artifact and retraining requirements above.
The user explicitly rejects retraining and requests verification of the published
heuristic baseline. Verification work is in ../../generalization. Existing demand
code is retained. Exact KDD HS-MC settings are not yet established; a successful
run of the published heuristic is distinct from reproducing their numerical result.

Verification outcome (2026-11-26): the published Brelsford heuristic successfully
ran on the KDD Harare input without training. See
[verification report](../../generalization/VERIFICATION.md) for source revisions,
compatibility shims, checks, road manifests and remaining scope. This removes
the need for a learned checkpoint for the heuristic comparison. It does not
establish reproduction of KDD's reported HS-MC numerical results.

## 2026-11-26 current first milestone: graph-only published-results comparison

The user now prioritizes the original KDD NR/AD/SC experiment. SUMO is deferred,
not a dependency of this milestone. Implementation and current input/GP contract:
[First generalization README](../../generalization/first%20generalization/README.md).
No GP branch exists yet. Core graph evaluation, protocol validation and checked
50x30 corridor layout are implemented; actual building placement/access and GP
host integration remain pending. No model training is planned or performed.

## 2026-11-26 second experiment implemented alongside the first

The graph-only first experiment remains separate. The user requested the second,
controlled synthetic-traffic experiment now. Its runnable SUMO pipeline, input
contracts, default cost budget, acceptance tests and limitations are documented in
[second generalization](../../generalization/second%20generalization/README.md).
Pilot and failure-accounting runs succeeded without any model training. Native
GP/game host integration and junction geometry review remain pending; this is
engineering readiness, not a GP generalization result or a calibrated traffic study.

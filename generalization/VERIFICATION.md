# Published heuristic verification - 2026-11-26

## Result

Successfully ran Brelsford et al.'s published probabilistic reblocking routine
on the pinned KDD Harare input, on CPU and without training. This is a local
run of the published heuristic, not a reproduction of KDD Table 3's HS-MC result.

| Check | Observed result |
|---|---|
| Input | KDD data/Epworth_Demo.mg |
| Nodes / graph edges / places | 54 / 85 / 32 |
| Existing boundary road edges | 20 |
| Initially inaccessible places | 12 |
| Seed 0 | 11 added edges, zero inaccessible places, 0.4475 seconds |
| Seed 0 repeat | Identical actions, roads and costs, 0.4885 seconds |
| Seed 1 | Different design, 11 added edges, zero inaccessible places, 0.4958 seconds |
| Initial road preservation | Passed |
| No edges outside original candidate graph | Passed |
| Final road graph connected | Passed |

Times measure only build_all_roads, not environment setup/imports. These are
engineering smoke tests, not comparative traffic performance measurements.
Source geometric lengths and source edge weights differ slightly; both are
saved. Neither is identified as meters. No physical scale has been established.

## Provenance

Heuristic: https://github.com/brelsford/topology
Revision: 2232a3da3cfa7bbe3f4e5eb48049baac6e67f662
Entry point: my_graph_helpers.build_all_roads; Example.py uses this routine.
Parameters: alpha=8, wholepath=True, strict_greedy=False, outsidein=False.
Original source remains unmodified. The wrapper restores three old NetworkX
APIs: connected_component_subgraphs, nodes_iter, and list-valued neighbors.
No path-selection objective or probability rule was changed.

KDD: https://github.com/tsinghua-fib-lab/road-planning-for-slums
Input revision: a3d86fbb201545415ddc1e09ea997b20089effd1
Input SHA-256: 4145ba0189e9d99d5f973abf3b71ae15aeda4edb33b932683bff225cac5fdbbf
The runner refuses an input with a different hash. It rebuilds the original
spatial graph from the trusted pickle, preserving node coordinates and edge
weights, discards cached faces, and verifies that reconstructed boundary roads
exactly match the input's road flags before running the heuristic.

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC6114988/
KDD paper: https://fi.ee.tsinghua.edu.cn/~dingjingtao/papers/RoadPlan-KDD23.pdf
KDD names the heuristic HS-MC and says it uses the code released by Brelsford
et al. This establishes the source relationship, not the exact evaluation
configuration. The KDD preprocessing directory also contains a modified copy;
that copy was inspected but was not used for these runs.

## Remaining distinctions

- The original routine stops at universal parcel access. It has no budget cap.
  Match GP's budget to a predeclared heuristic cost or implement and document
  a budget-limited adapter; do not imply this wrapper already enforces a cap.
- Access is the upstream road-node/parcel-boundary definition. This does not
  establish a vehicle driveway or a valid SUMO endpoint.
- KDD's paper evaluates under a segment budget. Its exact HS-MC settings,
  random seeds and post-connectivity behavior are not established here.
- No grid conversion, SUMO export, traffic run or GP evaluation was performed.
- Repeatability was checked in separate processes in the same pinned runtime;
  cross-platform set ordering and numerical behavior remain untested.

## Files and commands

Run from generalization:

```powershell
.venv/Scripts/python.exe -B verify_heuristic.py --seed 0 --output results/harare-seed0.json
.venv/Scripts/python.exe -B verify_heuristic.py --seed 1 --output results/harare-seed1.json
```

requirements-verification.txt pins the tested environment. The inputs directory
contains the locally copied input. upstream contains the pinned archive source.
Those directories and the virtual environment are ignored; the runner, this
report, dependency lock and small result manifests are retained as evidence.
Result manifests contain the full initial/final coordinate edge lists and the
ordered construction actions, along with source hashes, parameters and checks.

## Workspace decision

User requested C:/Users/user/Desktop/mini_motorways/generalization on branch
generalization. Existing simulation/generalization/workload.py is preserved.
The earlier audit text is historical. No DRL training or model modification
was performed. Interrupted clone attempts are local-only and not used.

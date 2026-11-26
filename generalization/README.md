# Generalization verification

Work moved here at the user's request on 2026-11-25, branch generalization.
The GP model will be imported later; no mbrl coupling or DRL training is authorized.

Current check: run the published Brelsford probabilistic reblocking heuristic
on the KDD Harare/Epworth graph, without training. Upstream topology revision:
2232a3da3cfa7bbe3f4e5eb48049baac6e67f662.

Downloaded upstream sources and the isolated environment are local-only.
The existing pipeline module remains at ../simulation/generalization/workload.py.
The earlier audit is historical and is not evidence of a successful experiment.

This verification does not establish reproduction of KDD Table 3's exact HS-MC
settings or results. The original routine stops at universal parcel access and
has no construction-budget argument. Budget enforcement needs an explicit adapter.

Verification completed: see [VERIFICATION.md](VERIFICATION.md). The published
routine ran on KDD Harare in approximately half a second per seeded run,
connected all places, and reproduced the same network for a repeated seed.
Result manifests are in results/. No KDD numerical reproduction, SUMO run,
grid conversion or GP evaluation is claimed.

Two independent experiment folders are now available:
- [First generalization](first%20generalization/README.md): original KDD graph metrics.
- [Second generalization](second%20generalization/README.md): our paired synthetic SUMO traffic experiment.
Both prepare a model-independent interface for the future GP branch; neither
contains a GP performance result or neural retraining.

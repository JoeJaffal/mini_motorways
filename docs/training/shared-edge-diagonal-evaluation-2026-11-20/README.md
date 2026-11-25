# Frozen diagonal-gap evaluation

On 20 November 2026 the user authorized testing the trained shared-edge policy on diagonals. The checkpoint was `output/training/shared-edge-pilot-02/latest.pt`, previously evaluated at 100/100 on horizontal and vertical gaps. The original host and source identity were checked when loading the checkpoint. The policy was then evaluated against a separate test host compiled from a copy of the native source. The only test-host change adds a diagonal scenario at reset. It does not alter native draw legality, the encoder, the policy, or the production training layouts. The Release fixture build had zero warnings and errors. [Original policy result](../shared-edge-results-2026-11-19/README.md#continuation-results), [isolated fixture patch](diagonal-fixture.patch).

The diagnostic uses 100 distinct diagonal layouts, seeds 20100–20199, with 50 of each diagonal slope. The destination keeps its normal driveway. The fixture builds a straight diagonal road from the house to the destination's outside approach and removes exactly one interior edge. The model sees the ordinary board and legal mask. A separate scripted arm verifies the expected missing edge is legal and actually gives a positive native binary reward. Scripted, sampled, highest-probability and uniform arms each start from identical observations and legal actions, checked for each seed. Sampling uses CPU seed 100000 plus the layout seed. The test checks both connectivity and exact placement.

| Policy | Down-right | Down-left | Exact repairs |
| --- | ---: | ---: | ---: |
| Scripted check | 50/50 | 50/50 | 100/100 |
| Shared-edge, sampled | 50/50 | 50/50 | 100/100 |
| Shared-edge, highest probability | 50/50 | 50/50 | 100/100 |
| Uniform legal build | 0/50 | 0/50 | 0/100 |

All correct builds placed the exact missing diagonal edge and connected the house to the destination. The trained policy assigned the exact edge a mean probability of 99.86% across 457–460 legal builds per layout. This supports generalization to straight diagonal one-gap roads without training on those gaps. It does not test junctions, curved road stubs, other diagonal constructions, or delivery performance. One checkpoint and one sampled attempt per board. No weights were updated or new training run started. [Per-layout data and fingerprints](results.json), [evaluation code](evaluate_diagonals.py).

To reproduce, copy `simulation/Assets/Simulation/*.cs`, `simulation/Headless/Program.cs`, and `simulation/Headless/TrafficHost.csproj` into a fresh directory preserving paths. Apply the fixture patch only in that directory, then build its headless project in Release. From the original project root run `PYTHONPATH=training .venv/bin/python docs/training/shared-edge-diagonal-evaluation-2026-11-20/evaluate_diagonals.py` with `--checkpoint`, `--native-host` pointing to the original checked host, `--fixture-host` pointing to the isolated build, and a fresh `--output`. Both binaries and the checkpoint remain local.

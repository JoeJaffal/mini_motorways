# Frozen one-build delivery evaluation

On 20 November 2026 the user authorized checking whether the frozen `shared-edge-pilot-02/latest.pt` connectivity repairs carry traffic. It was loaded against the original host and source identity. Evaluated the same 100 straight-gap layouts (20000–20099) and 100 isolated [diagonal fixtures](../shared-edge-diagonal-evaluation-2026-11-20/README.md) (20100–20199) used previously. Each comparison arm used identical initial observations and masks, verified by hash and mask equality per layout.

The policy took exactly one build at time zero, with either sampled or highest-probability selection. The single-build wrapper then ended and the native world simulated until 180 seconds or game over with no further actions. The no-build control advanced the same world without any construction. The sampled arm used CPU sampling seed 100000 plus the layout seed. All 600 runs reached a natural ending. No optimizer updates or simulator source changes were made.

| Gap direction | Layouts with at least 3 deliveries | Mean deliveries | Min–max |
|---|---:|---:|---:|
| Horizontal | 50/50 | 11.82 | 10–13 |
| Vertical | 50/50 | 11.64 | 10–13 |
| Down-right diagonal | 50/50 | 11.36 | 10–13 |
| Down-left diagonal | 50/50 | 11.32 | 10–13 |
| Total | 200/200 | 11.535 | 10–13 |

The sampled and highest-probability arms picked the exact gap on all 200 boards. Their delivery outcomes matched on every layout and all reached 180 seconds. All 200 no-build controls ended by game over with zero deliveries. The result exceeds the 90-of-100 three-delivery benchmark on each 100-layout cohort under the one-build plus automatic advance protocol. It does not establish the autonomous Stage 1 Build-or-Wait gate, and it covers the existing one-gap geometry rather than more complex layouts. A two-separated-gap, two-build diagnostic is the proposed next milestone, pending approval. [Per-layout results](results.json), [grouped measurements](metrics.json), [evaluation source](evaluate_delivery.py).

Reproduce from the project root with `PYTHONPATH=training .venv/bin/python docs/training/shared-edge-delivery-evaluation-2026-11-20/evaluate_delivery.py --checkpoint <trusted-checkpoint> --native-host <original-Release-dll> --fixture-host <diagonal-fixture-Release-dll> --output <fresh-json-path>`. The separate fixture build is documented in the diagonal evaluation. Both host binaries, the scratch output, and checkpoint remain local.

# Frozen two-gap, two-build evaluation

On 20 November 2026 the user authorized a frozen two-gap test. The shared-edge continuation checkpoint was originally trained on one missing connection. It had passed the [one-gap native delivery test](../shared-edge-delivery-evaluation-2026-11-20/README.md). The new isolated fixture host uses the same native build and traffic mechanics. Its reset-only patch makes a straight road with two missing interior edges, at least one intact link between them, and two road units in stock. The original training setup and host were preserved. The fixture Release build had zero errors and warnings. [Fixture patch](two-gap-fixture.patch).

Tested 200 layouts with 50 gaps per direction group (horizontal, vertical and both diagonal slopes). Each layout has two gaps of the same direction. The comparison used 20000–20099 for axis-aligned boards and 20100–20199 for diagonals. Seeds match earlier test lists, with different reset geometry. Each arm started from the same verified observation and legal mask. The policy saw the updated observation and legal mask after the first build. Wait was masked out and the harness allowed exactly two native builds, using one road unit each. Order was unrestricted. After the two builds, the native world advanced to 180 seconds or game over. Scripted and uniform arms checked feasibility and provided a chance reference. The sampling arm used one CPU generator per seed seeded with 100000 plus the layout seed. No weights changed.

| Direction | Both exact repairs, sampled | Both exact repairs, highest probability | Mean native deliveries |
|---|---:|---:|---:|
| Horizontal | 50/50 | 50/50 | 11.70 |
| Vertical | 50/50 | 50/50 | 11.34 |
| Down-right diagonal | 50/50 | 50/50 | 10.98 |
| Down-left diagonal | 50/50 | 50/50 | 11.02 |
| All layouts | 200/200 | 200/200 | 11.26 |

Every successful model run was disconnected after the first build, connected after the second, reached 180 seconds and made 10–13 deliveries. Delivery counts matched the scripted arm on the test layouts. Uniform builds completed no repairs and scored zero trips. Uniform choices hit two individual prescribed edges across the 200 games but never both on one board. All 800 comparison runs ended naturally.

The behavior generalizes from one trained missing edge to two separated tested edges with updated observations. The test does not distinguish sequential planning from applying the learned local repair rule twice. Adjacent gaps, mixed directions, junctions, and autonomous waiting remain untested. No training or change to production implementation. [Per-layout actions and deliveries](results.json), [aggregates](metrics.json), [evaluator](evaluate_two_gaps.py).

To reproduce, copy `simulation/Assets/Simulation/*.cs`, `simulation/Headless/Program.cs`, and `simulation/Headless/TrafficHost.csproj` into a clean fixture directory. Apply the linked patch only there and build the headless project in Release. From the project root run `PYTHONPATH=training .venv/bin/python docs/training/shared-edge-two-gap-evaluation-2026-11-20/evaluate_two_gaps.py --checkpoint <trusted-checkpoint> --native-host <original-Release-dll> --fixture-host <two-gap-fixture-Release-dll> --output <fresh-json-path>`. Native binaries and checkpoints remain local.

# Road-cost reward pilot — inconclusive at16k/arm

[Results and corrected interpretation](RESULTS.md) · [Plan and user timing feedback](PLAN.md) · [Measurements](results.json)

Three matched short PPO arms completed49,152total decisions. Reward wiring, native parity and success-over-Wait ordering pass. There is no clear penalty benefit yet; no construction-avoidance collapse. The user correctly challenged judging after only16,384decisions/arm. No convergence has been demonstrated; this does not reject road penalties. Checkpoints/Adam preserved for a longer matched comparison. No extended run is currently active.

[Comparison graph](comparison.png) · [Strong-cost replay](watch-strong-generous/replay.html)

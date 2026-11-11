# Two-hour v4 continuation — 30 October 2026

Measured user-run signals-context-02 completed normally after 7200.58 learner seconds,
56,352 policy decisions, 255,084 commands and 370 episodes. Parameter updates confirmed.
Best training game: 480 trips; this is not a validation score or proof of improvement.

Development seeds2000–2004: starting scores235/259/155/122/369 (mean228.0),
final83/259/139/122/329 (mean186.4, -18.25%). Three maps worse, two tied.
Every periodic validation was below228.0. Best-selection retained the starting
checkpoint (baseline:true, steps0); it did not select the regressed final policy.
This means no demonstrated development improvement in this continuation, not
that parameters never changed or that all previous learning was absent.

Engineering recommendation: pause additional long training, keep the protected
228.0 checkpoint and diagnose the regression on development trajectories before
changing settings. No unseen-map test is needed to confirm selection of the same
starting checkpoint. Possible policy instability/credit assignment limitations are
hypotheses, not established causes; no new hyperparameter choice is justified yet.

Inspection only: no training, evaluation, replay execution or simulator changes.
Raw small run files and checkpoint hashes are archived here. Weights and full
training episode/replay data remain local under output/training/signals-context-02.
No new PDF/graph was generated. Earlier PDFs remain historical.

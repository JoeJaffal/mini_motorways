# Build-or-Wait PPO repair

The model could connect matching buildings in these small scenes, but also spent its roads in scenes with no useful connection to make. The native score gives no learning signal for choosing Wait in an isolated zero-delivery scene. This study supplies an explicit binary practice reward for choosing the appropriate action group.

Only the existing Wait corrections learn. Conditional road-placement weights, the native city critic and their optimizer history stay unchanged. There is no new planner, demonstration route or behavior-cloning loss. This is a limited lesson about when to act, not a claim that its routes are efficient.

## First budget: 32,768 decisions

Training completed on 25 November 2026. Final frozen first-action probability of choosing Wait rose from about 6–7% to 60–67% in incompatible scenes. It chooses build with about 95% probability in partial-network scenes. Matching empty boards fell from 97.5% to 89.5%; a tradeoff to monitor.

Actual native play still builds eventually in every negative test game. The right first decision is not enough when the decision repeats. All matching/partial-network targets were still served in 16/16 games per family. Broader mini-task and city retention reviews are pending. No promotion or overnight launch.

The parent is focused run01 final, not the later run02 checkpoint. Run02 learned its single training board better, but produced four extra zero-score city games; it remains preserved. See ../mini-fixed-route-continuation-2026-11-25/INTERPRETATION.md.

## Evidence

- PLAN.md: objective, risks, preflight and predeclared checks.
- launch.json: exact command, parent choice, revision and budget.
- evaluation/: frozen one-decision, repeated native play and retention measurements.
- decision-curve-32768.png/json and plot_reviews.py: frozen review curve, distinct from training batch accuracy.
- replays-initial/ and replays-final/: lowest seed per family, exact evaluation-counter verification, traces and playable HTML.
- native-replay-comparison-32768.png and plot_native_replays.py: inspected examples. Prebuilt connections are included in each scene; use the step records to identify newly built roads.
- native-export-smoke/: returning to native PPO preserves all weights and Adam states, restores native values/configuration and passes a disposable native learning/reload check. A failed pre-learning counter assertion is retained and explained.
- bandit-resume-smoke/: continuing the same lesson retains all30 named Adam states; disposable128-decision resume passed. Smoke weights are excluded from candidates.

Binary practice correctness is not city score. The city evaluator uses the unchanged production host and native rewards. All weights and binaries remain local under output/. This archive preserves source and small measurement evidence.


## Completed review and continuation
Full results and uncertainty are in INTERPRETATION.md. City retention held (mean141.09vs129.25parent,31/32scoringboth; scoregainuncertain). Unchanged65,536decisioncontinuation launched20:14,output/training/build-wait-02. No overnightpromotion.

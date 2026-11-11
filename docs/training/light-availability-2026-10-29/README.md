# Traffic-light availability result - 29 October 2026

Twenty deterministic games completed naturally on seeds5000-5009 using the same
preselected frozen policy. The sole intervention masks placement actions; all
other actions and observations are retained at a shared state. Later routing,
upgrades, stock and survival may differ. This is a policy-availability test, not
an isolated traffic-light physics experiment or optimized no-light opponent.

| Condition | Mean completed trips | Mean per-game car waiting |
| --- | ---: | ---: |
| Lights enabled | 190.9 | 0.69014s |
| Lights disabled | 209.9 | 0.68990s |

Enabled wins2, ties5, loses3. Its mean is9.05% below disabled, but **one map
dominates**: seed5009 scores279 ON versus475 OFF (-196). Across the other nine,
ON totals6 more trips. Waiting averages are essentially equal and can be
confounded by different survival/load; they do not establish equal throughput.
ON placed14 lights; OFF placed none. All evaluator tensors were unchanged and
checkpoint hash matches the earlier preselected fresh-map candidate.

The result does not establish reliable beneficial placement for this policy.
It does not prove that lights always hurt or identify the junction/decision
responsible for the5009 decline. Comparing existing5009 trajectories is the next
diagnostic; no new training, inference or simulator changes were done for this
assessment. No post-test checkpoint reselection occurred. Exposed seeds are no
longer an unseen tuning test.

[Full paired scores](comparison.json), [assessment](assessment.json) and
[protocol](protocol.json) are archived with original policy reports, traces and
two best replay files. Those best recordings need not be seed5009 in both cases;
the stdout/per-map metrics identify all scores. Replay verification was not
newly performed here. The [manifest](manifest.json) preserves source-byte hashes;
weights remain local under output/training/signals-night-01. Runtime originals
remain under output/experiments/lights-test-01.

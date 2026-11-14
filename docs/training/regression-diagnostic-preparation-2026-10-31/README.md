# Frozen regression diagnostic preparation - 31 October 2026

User authorized preparing the proposed comparison, preserving the preference to
run and wait themselves. Added training/diagnose_policy_regression.py. No training
or full diagnostic was launched. The two-second-per-policy wiring check completed:
both zero trips, capped rather than natural ends, weights unchanged. This is only
an integration check, not performance evidence.

Engineering choice: development seed2000, the largest observed regression (235 to83)
in signals-context-02. Compare validation-best.zip with final.zip, deterministic,
cap3600 simulation seconds. Save ordinary-command traffic/queue/shop-pressure
traces, replay files and macro decisions. Both policies are scored on each visited
state with the same action mask; top five choices include route geometry or light
cell and candidate features. Records available route/light counts and first policy
disagreement. Check in-memory tensors and checkpoint file hashes remain unchanged.
Runs sequentially to avoid a long concurrent job; no optimizer call.

Limits: an exposed development failure case, not generalization evidence. First
disagreement is descriptive, not causal proof. Planner option limitations require
follow-up inspection; an unavailable option does not establish impossibility. No
new reward, tool, simulator rule or training setting chosen. Full execution time
has not been measured. Full traces and weights stay local; archive compact findings
when user reports completion. Smoke metadata is preserved here.

Run from PowerShell:

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\diagnose_policy_regression.py --output output/experiments/regression-2000-01
```

Wait for DIAGNOSIS COMPLETE and the returned PowerShell prompt, then report done.

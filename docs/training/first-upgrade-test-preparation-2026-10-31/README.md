# First-upgrade intervention prepared - 31 October 2026

User authorized preparation and explicitly reserved long execution/waiting for
themselves. Added training/test_first_upgrade.py; no full test or training launched.
Two-second-per-condition wiring smoke passed with unchanged weights; no intervention
occurred in this short check, so the intervention branch remains untested at runtime.

Predeclared protocol: exposed development seed2000, final checkpoint frozen to
original diagnosis SHA256, original3600s cap, deterministic final-policy baseline
versus exactly one override. At140s replace action1 (upgrade choice0) with action2
(upgrade choice1), then use final policy normally on resulting states. Validate
exact intervention state, legal replacement and expected original choice. Compare
all baseline ordinary commands and pre-intervention prefix against diagnosed trace;
require baseline83 trips/469.7s and actual intervention. Record outcomes, full command
traffic traces, decisions and replays. Verify parameter tensors/file hash unchanged.
No optimizer calls, simulator changes, reward changes, grants or forced later actions.

This measures total effect of the one upgrade under this policy, including later
inventory/policy feedback. It does not isolate traffic-light physics, prove which
later decision matters, or establish generalization. Even recovery would not justify
a global hard-coded upgrade rule. If baseline/state guard fails, inspect before
interpreting any outcome. Runtime of full test not measured; two games sequential.
Weights/traces remain local; small protocol/smoke evidence retained here.

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\test_first_upgrade.py --output output/experiments/first-upgrade-2000-01
```

Wait for UPGRADE TEST COMPLETE and returned PowerShell prompt, then report done.

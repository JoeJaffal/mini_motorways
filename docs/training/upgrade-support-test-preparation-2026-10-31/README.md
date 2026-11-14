# Upgrade support comparison prepared - 31 October 2026

User asked next step under standing authorization to prepare changes, reserving
long jobs for themselves. Source inspection: GoalEnv masks both offers legal;
SignalEnv adds light placement, but neither implements roundabout/motorway/tunnel
actions. Existing global observation already includes offer type/amount/roads
and inventory; this is not a missing-offer-observation bug. MaterialInventory.cs
increments package counts, which can affect later offers. No simulator bug claimed.

Prepared compare_upgrade_support.py, optional frozen evaluation only. Predeclared
final signals-context-02 policy, deterministic paired exposed development2000-2004,
3600s cap, baseline versus supported-package filter,10 games sequentially. For an
unsupported-extra offer (types2/4/5), mask only its upgrade action if another legal
offer has positive supported extra (roads0/bridge1/lights3) and no fewer bonus road
tiles. Keep observations and all non-upgrade actions intact. Supported extras are
not guaranteed useful on the current map; this is a heuristic, not mathematical
dominance. No masks changed in actual training or ordinary evaluation defaults.

Baseline must reproduce recorded final evaluation on every seed (score/time).
Checkpoint hash and in-memory parameters must remain unchanged. Record each offer,
masked/original/executed action, per-map score/survival/light count, paired outcome
and best replay per condition. This measures total selection-rule effect under
frozen final policy; it does not demonstrate learned improvement or generalization.
No protected checkpoint replaced. No long training/full test launched by assistant.

Checks: six synthetic rule cases passed (supported/unsupported combinations,
road budget and zero quantity; masks/input preserved). Two-second-per-condition
wiring smoke passed, unchanged weights; no upgrade occurs in smoke. After smoke,
added full-run baseline score/time guard; checked syntax/help, not full runtime.

If development outcomes justify continuing, compare to protected policy and test
on predeclared unused maps before adoption/long training. Do not hard-code seed2000
or always pick lights from its one-map result.

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\compare_upgrade_support.py --output output/experiments/upgrade-support-01
```

Wait for UPGRADE COMPARISON COMPLETE and returned shell prompt, then report done.
Full runtime unmeasured. Weights/local full outputs remain ignored; small smoke
metadata is preserved here. No new PDF/graph created; historical reports unchanged.

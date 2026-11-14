# Supported-upgrade development results - 31 October 2026

User completed ten frozen final-policy games (signals-context-02/final.zip).
Baseline186.4 versus filter228.8 trips (+42.4,+22.75%);4 wins,1 tie,0 losses.
Pairs2000:83->245;2001:259->288;2002:139->146;2003:122->122;2004:329->343.
Seed2000 contributes162 of212 total gained trips; other four net+50. Policy weights
unchanged, all ten games natural failures, baseline score/time guard passed.
Filtered games changed2/1/2/0/2 decisions and placed4/2/4/0/4 lights. This is a
selection-rule effect, not new learning or proof of generalization. Its228.8 mean
is numerically near protected228.0; not grounds for replacing protected checkpoint.

This rule can change multiple upgrades, explaining245 versus the earlier266 from
only one override on2000. It is not mathematically dominant: supported extras can
be unnecessary, and package counts affect future offers. No training default changed.
Full raw result files (small JSONs, offer events and two best replays) archived here;
weights remain local. No additional replay playback verification, training or full
evaluation performed by assistant. No new PDF/graph created.

Next predeclared test: same frozen final checkpoint, same filter, deterministic
paired seeds8000-8009,3600s cap,20 games. These seeds have not been used in the
recorded experiments. Compare baseline/filter mean and per-map wins/ties/losses;
report concentration, caps and mutation checks; no tuning/reselection from test.
Retain protected checkpoint and keep training paused until reviewed. Added CLI
seed-start/count options to existing evaluator; default development behavior
unchanged, recorded-baseline guard applies only to2000-2004. Short CLI help passed;
no fresh-map games launched. User executes and waits per credit preference.

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\compare_upgrade_support.py --seed-start 8000 --count 10 --output output/experiments/upgrade-support-fresh-01
```

Wait for UPGRADE COMPARISON COMPLETE and returned shell prompt, then report done.

# Four-hour supported-upgrade training preparation - 31 October 2026

User chose a long training run instead of further evaluation before sleep, reserved
execution/waiting for themselves, and explicitly corrected8h to4h. Fresh8000-8009
test remains unexecuted/unread in this preparation; no unseen benefit is claimed.

Engineering: opt-in --supported-upgrades on train_goal.py; old defaults false.
Moved identical filter into upgrade_rules.py, used by SignalEnv action_masks and
comparison CLI. Signal-only option; saved model attribute inherited on resume and
model_environment evaluation, including periodic/final validation. Config and info
record flag; run source snapshot includes helper. Explicit --no-supported-upgrades
available on resume. Comparison CLI explicitly disables inherited environment rule
so its baseline remains genuine. Observation shapes/reward/PPO settings unchanged.

Command resumes protected signals-context-02/validation-best.zip (228 development
without filter), preserving weights/optimizer and enabling filter. The new run's
initial baseline is remeasured with filter; starting checkpoint is eligible and
strict-gain validation retains it if learning regresses. Original checkpoint stays
in its source directory. Uses4workers,240 learner minutes,10M step ceiling,
validation every30 learner minutes, seeds1000-1099 and development2000-2004.
Initial/final evaluations add time outside learner budget; not an exact4h alarm.
No rate/entropy/reward changes or long job launched by assistant. Periodic saving
and Ctrl+C handling already exist. Source/checkpoint artifacts remain local.

Checks: synthetic SignalEnv mask integration(default/opt-in), preservation of
non-upgrade masks, road-budget rule, saved model metadata roundtrip and evaluation
inheritance/explicit override; unchanged parameter tensors. No optimizer updates or
games. First synthetic fixture omitted action_space and was corrected; check then
passed. CLI help and repository check passed. Full multiworker training path not
executed in preparation; no promised learning-speed or performance improvement.

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\train_goal.py --output output/training/upgrades-night-01 --resume output/training/signals-context-02/validation-best.zip --supported-upgrades --minutes 240 --steps 10000000 --workers 4 --validation-minutes 30
```

Keep PC powered and awake. Screen may turn off; system sleep suspends training.
Ctrl+C requests saving. After completion return for summary/validation review;
compare selected checkpoint, not just best training score. Do not infer fresh-map
improvement from validation. Full fresh test remains pending and8000-8009 should
stay untouched until checkpoint selection/protocol is frozen.

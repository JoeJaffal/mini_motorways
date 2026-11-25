# City replay near the median paired score change

Chosen before replay from all32development pairs: closest score change to the median (2points), ties lowest scenario/action RNG. Selected seed184000003,action RNG193354; actual scorechange3points. This is one illustration, not the best game or a substitute for the complete distribution.

Before Wait practice:170deliveries at600seconds,112paid roadunits,123build actions,26units outside final working routes,13stock remaining. After32kWait practice:173deliveries,84paid units,95build actions,16outside-route units,31stock remaining. Both native replay final counters and checkpoint/host hashes match their evaluation exactly.

The inspected frame comparison shows a simpler early connection and more retained stock after Wait practice, with continued excess branches later. Atabout30seconds the parent has added a loop/second-home connection whereas the Wait candidate keeps its opening route. This does not imply that second-home connections are always unnecessary. The two trajectories generate different later building layouts (24vs25buildings by600seconds), so later geometry is not controlled-identical. Stock difference is not simply the road-cost difference because native arrivals/awards can diverge. The complete paired city suite reports uncertainty separately.

Files: selection.json, parent/ and wait/ trace/HTML/steps/verification, comparison.png; source replay_city_change.py and plot_city_change.py in the parent archive. No learning occurred during replay.

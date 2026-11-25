# Small-city service experiment — complete

[Full results](RESULTS.md) · [Plan and scope changes](PLAN.md) · [Practice measurements](results.json) · [Fresh city confirmation](confirmation-results.json)

Easy straight pairs already pass64/64 before training. Longer offset pairs expose failures, but32,768-decision PPO does not fix them: separate-layout both-pair service9/32→9/32; first-pair20/32→17/32; outside-route units8.34→9.25. Development-city score126.09→143.06 does not confirm reliably on fresh cities121.53→123.53 (paired95% interval−16.84..+20.72). No promotion or long run; all jobs ended.

The easy pilot stopped with its8,192-decision checkpoint preserved. All native hosts, parent and trial checkpoints remain local-only. Sources, small measurements, graphs, logs and replays are archived here.

[Failed final replay](watch-final-191000100/replay.html) · [Failed final frames](watch-final-191000100/frames.png) · [Practice graph](practice-results.png)

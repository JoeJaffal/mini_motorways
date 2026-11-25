# Continuation decision record

Worktree: `/home/mohammadjaffal/mini_motorways`, `Maskable-PPO`; separate Desktop/main unchanged. All checkpoints and inherited changes retained.

| Completed test | Full-city mean | Reference mean | Decision |
|---|---:|---:|---|
| Recorded native starts,65,536 decisions |234.91|230.97|No promotion: uncertain gain; stockout arrivals104 vs44|
| Faster dedicated value head,32,768 decisions |220.53|230.97|No promotion: value fit improved, city score did not|
| Longer rollout,32,768 decisions |213.03|230.97|No promotion: modest midpoint gain did not persist|

Each evaluation uses32 matched consumed development cities at1200 native seconds,29 scoring games for each model. None passes the predeclared substantial-gain gate. Independent confirmation remains unused. No long session has launched.

Implementation: optional recorded starts (previous phase), exact-parity per-forward evidence caching (previous phase), optional critic-head optimizer scale with preserved Adam state, and optional runner rollout length defaulting to512. No planner, imitation target, native physics change or new reward term was added during this continuation.

Checks: six optimizer/runner/reporting tests; real checkpoint weights/moments/save-load integrity; exact initial ten training episodes; gradient audits; default runner checks. Each run freezes its own source and host.

All training and reviews are complete; no processes are queued. Longer rollouts increased observed terminal-return coverage to52.8%,but final city score declined. Protected opening checks passed and checkpoints remain local-only. The reference stays retained. No overnight run is justified by these results.

Open question: whether any current PPO variant learns decisions that substantially improve full-city scores. Faster value fitting and successful synthetic lessons do not answer that question. Do not promote a model or launch an overnight run from those metrics alone.

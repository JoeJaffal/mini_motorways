## Stage 1 evaluation rule approved — 16 November 2026

User explicitly approves the proposed starting rule:

- Each practice episode lasts 180 simulated seconds; paused editing does not consume simulated time. Native game-over still terminates earlier. An operational truncation is not a completed successful episode.
- Evaluate a frozen checkpoint on a cohort of 100 held-out practice layouts. Pass when at least 90 episodes each complete at least 3 scored trips. This is a count of successful episodes, not a threshold on cohort-average score.
- These are initial engineering targets, not measured optimums or a demonstrated achievable result. Before using this rule, verify that native trip generation/service timing in the selected scenario permits three scored trips within the horizon. If infeasible, report the evidence and propose a documented revision rather than silently altering the threshold or simulator physics.
- These are evaluation criteria only. Preserve native score-only reward; no reward for passing, connectivity, focus completion or intermediate construction. No generated construction routes.

No feasibility run, implementation or training has occurred. Layout generation, inventory/event setup, cohort seed list and hierarchy integration details still require engineering reconciliation with existing records. This approval does not authorize an unbounded or long training run.

## Approval update — 16 November 2026

User explicitly says "i approve your desicions" after the Stage 1 explanation. Adopt the first-stage concept: one matching house/destination, varied short unobstructed land layouts, model-selected focus and individual connections, explicit waits, game score only, validation layouts separate from training, and success based on actual repeated scored service rather than connectivity alone. Exact horizon, thresholds, inventory/event setup and budgets were not specified and remain open. The earlier discussion below is preserved as history. No implementation or training has occurred.

# Curriculum direction — 16 November 2026

## User decision and scope

User replies "sure yeah" to discussing a staged curriculum after adopting the manager/executor hierarchy. Accept the broad progression as the working direction: basic matching connections; construction challenges; shared networks; growing cities; full games. This resumes the previously deferred curriculum discussion. Exact scenario construction, stage boundaries, promotion thresholds, budgets and retention schedule are not approved by this brief assent. No training authorized or started.

Keep the accepted physical game rules, score-only reward, model-chosen neighboring connections, paused editing and explicit wait. No generated construction paths, route candidates, demonstrations or strategic masks are introduced. Scenario simplification must be explicit: reduced building counts, controlled spawn schedules or resource setup are training distributions, not new simulator physics or evidence of full-game ability.

## Engineering proposal: first stage, awaiting review

Start with one house and one matching destination on land, with a short unobstructed constructible separation. Vary their relative placement and orientation across layouts; keep disjoint training and validation seeds. Sample feasible setups without furnishing the policy a solution path or pruning legal actions to useful ones. Do not expose a hidden reference route. All native actions physically available in the scenario remain available; the hierarchy receives the same full observation structure as later stages. Water and resource-pressure scenarios enter later.

The policy must choose a focus, construct every edge, and choose waits to allow actual scored trips. A drawn connection alone is not a successful training outcome, and has no added reward. Use native trip/game score behavior. First-stage evaluation should report score and repeat service over a fixed, explicitly chosen game-time horizon, with an external operational decision budget to identify paused loops. Native game-over remains terminal; external budgets require separate truncation handling. No exact horizon, score threshold, decision limit or promotion rule selected yet. Investigate resource/horizon choices before specifying numbers.

Promotion should require consistent service across unseen layouts and several frozen-policy evaluations, plus replay review of failures and stalls; do not use a single solved layout or training-step count alone. Later retain simpler cases alongside harder ones if forgetting appears; mixture weights and retention policy are unresolved. This is a proposal, not a measured learning result or guarantee score-only learning succeeds.

## Next decisions and limits

Define first-stage scenario generation and feasibility checks, visible information, inventory and event setup, time horizon, success definition, validation cohort and advancement thresholds. Later settle stage mixing and transition rules. Preserve no-generated-routes and physical masks while doing so. Do not alter the reserved final test city for curriculum tuning. No runnable new-trainer command exists.

Evidence this turn is conversational acceptance only. No new research result, benchmark, episode, code implementation, commit or push. The agent is responsible for documenting and revising these recommendations against subsequent validation evidence.

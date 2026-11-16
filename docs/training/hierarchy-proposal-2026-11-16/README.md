# Hierarchy adopted — 16 November 2026

User decision: after confirming there is no road planner or route menu, the user says this is the agent's decision to follow and requires the agent to justify, fix and change it when needed. Adopt the proposed manager-focus / primitive-executor hierarchy as the initial design. The original proposal below remains a historical snapshot.

Engineering responsibility: explain rationale and changes, diagnose failures using logged evidence, preserve prior revisions, and document what changed and why. Adoption does not establish performance or guarantee human-level play. The eight-edit/one-wait review cadence remains an adopted provisional starting setting, subject to evidence-based revision. No generated construction routes, candidates or completion; executor selects each neighboring connection. Score-only reward and physical legality constraints remain binding. Changes to these user constraints require explicit user agreement.

Evidence plan: inspect held-out score distributions and best/worst/near-average replays; measure focus conditioning, switching, stalls and time advancement. If focus is ignored, switching cycles dominate, or matched-budget comparisons do not support benefit, investigate and revise the representation, cadence or training credit rather than defend the initial choice as proven. Any subsequent changes must distinguish engineering choices from user decisions and measured results. No numerical acceptance threshold or training budget has been approved here.

Status: design accepted for implementation planning; no implementation, experiment, training run, commit or push in this turn. Exact encodings, network sizes, two-level PPO returns/GAE details and deferred curriculum still need resolution. This acceptance does not authorize a long training run.

---

# Proposed hierarchy — 16 November 2026

Status: engineering proposal for user review; NOT approved, implemented or measured. User requested the best-supported plan and reasons. Hierarchy itself is a user requirement; this particular structure is not. No training authorized or run.

## Context and branch

Work is now in `C:/Users/moham/mini_motorways-maskable-ppo`, branch `Maskable-PPO`, based on `938b9f80e67ca5341920a10e9e671164a474fc38`, simulator `2026-11-10.f34`. The separate dirty `mini_motorways` checkout remains on `codex/driveway-physics` and was not switched or cleaned. This follows the user's explicit branch correction and supersedes AGENTS.md's older training-branch preference for this experiment. No commit or push of this proposal has occurred.

Earlier local restart/hierarchy records remain in that older checkout under `docs/training/hierarchy-design-2026-11-16/` and `maskable-ppo-restart-decisions-2026-11-15.md`; they are not yet migrated or published on this branch. The published roundabout comparison is at commit `c37ce9a6eee1a5621bc40c1b546281a9ebc9f482` on `codex/driveway-physics`. User delegated roundabout work to another person; this proposal does not change its physics or approve its control semantics.

Authoritative constraints carried forward from user discussion: fresh model; local neighboring road/bridge edits including physically legal diagonals; paused edits with observations after each; one-second wait ending early for native weekly/game-over events; score-only reward; no generated construction routes, candidate routes or path completion; masks enforce physical game legality only. Curriculum remains deferred. Hierarchy-dependent architecture, PPO integration and credit settings remain open. User reviewed many spreadsheet topics; that is not approval of this new proposal or superseded defaults.

## Recommendation: persistent focus, followed by unrestricted execution

Use two policy levels. Manager chooses the current focus; executor chooses ordinary game actions conditioned on that focus and the full current board. Operand selection (tool, tiles, endpoints) remains part of execution, not a third strategic agent. Start with one shared board encoder and distinct manager/executor policy and value heads; exact network dimensions remain undecided. Shared features may reduce duplicated processing but do not prove a speed or learning advantage, and gradient interference must be monitored.

Represent focus with a primary board location and an optional secondary location. Visible building identities can be attached to selected building tiles for replay labels; any exposed board tile remains selectable, including empty tiles. All secondary tiles and NONE remain selectable; no compatible-color, disconnected-only, congestion or distance shortlist. Target availability follows visibility/board bounds, not engineering judgment of usefulness. Choose coordinates sequentially to avoid treating every coordinate pair as one huge independent categorical menu. This does not generate a path.

Examples: a destination as primary and NONE as secondary; house A and destination B; junction B and junction D; a currently empty crossing area and NONE. These mean 'work with this focus', not a hard-coded obligation to connect, remove or improve a prescribed metric. Do not add named connect/decongest/repair modes initially: their meanings, prerequisites and success detectors would introduce more assumptions. Intent is learned from context. The tradeoff is that a focus has weaker semantics than a formally achieved subgoal; call this a focus hierarchy, not proof of goal completion.

Executor sees global traffic, inventory, visible demand and time/event state, the focus, and the ordinary operand-selection context. It can build/delete anywhere physically legal, use available native tools, wait, or return control. Focus is an input, never an edit boundary or a strategic legality mask. No automatic action is selected by the manager's coordinates. Motorway native geometry and traffic routing stay ordinary simulator mechanisms, not external road planning.

## Persistence and interruption

Provisional scheduling value: review after at most 8 completed edits, or after one time-advancing wait, whichever comes first. The executor can return control earlier between completed actions. The manager can reselect the same focus; a review does not force a focus change, wait, deletion, or completed road. Eight counts committed edits, not tool/coordinate tokens. Reason: allow a coherent short batch while giving frequent opportunities to reprioritize; eight is an unmeasured starting hypothesis, not a human-derived or literature-proven optimum. Later compare a small set of review intervals under matched budgets if separately authorized.

After every completed action observe again, so the executor can react within the batch. While edits are paused, traffic does not evolve; after each wait the manager sees the changed traffic. Do not declare success merely because a graph connection exists: a connected road may still fail to serve demand. There is no automatic 'congestion solved' threshold or completion bonus.

Game-over ends the episode. Native weekly offer interrupts execution immediately; choose its item from the offered items using a dedicated policy head, then ask the manager for focus again. This is an action context, not a third planner or hand-written item ranking. An unfinished focus can be chosen again. Full reset clears focus. Selected tiles remain meaningful when roads change, so demolition alone need not invalidate a coordinate focus. Episode timeouts and operational zero-time guards are external truncations, not invented game losses. The previously discussed guard must cover manager reselection/return-control cycles as well as construction tokens; preserve the proposed 4096-token guard only as an unvalidated operational setting. Do not use focus review to force game-time advance.

## Why this rather than the alternatives

| Alternative | Benefit | Reason not to choose it first |
| --- | --- | --- |
| Only choose a house-destination pair | Easy to explain and inspect | Shared networks, demolition, junction repairs and resource-saving edits need broader context; mandatory pair tasks prescribe too much strategy |
| Fixed connect/repair/decongest goal vocabulary | Human-readable intent | Requires defining distinct modes and often success criteria; may bake in weak assumptions about traffic |
| Unnamed learned modes | Can discover its own abstractions | Harder for the user to understand; modes can collapse or fail to specialize |
| Region-only focus | Small, general interface | Optional second location expresses relationships without designing a route; its added complexity must earn its place |
| Three independently trained strategic networks | More decomposition | More nonstationarity and credit interfaces before evidence that an extra level helps |
| Flat control | Simpler learning pipeline | Does not satisfy the user's required persistent hierarchy; useful only as a later diagnostic comparison if authorized |

This is an engineering preference for an inspectable, broad interface, not a measured claim of best performance. Coordinate pairs are still a large search space, and globally unrestricted execution can ignore focus. These are explicit failure risks.

## Reward, PPO and credit

The environment emits only the change in game score. No reward for selecting a focus, making a connection, obeying it, finishing a batch or ending a goal. Both policy levels learn from the same eventual score stream: worker transitions carry their actual score changes; manager transitions carry accumulated score change during that focus interval. Do not count manager bookkeeping as extra environmental score. Zero-time construction intervals often have zero immediate reward at both levels; later value estimates must propagate information. Hierarchy does not eliminate sparse exploration or delayed credit, and there is no guarantee this learns from scratch under score-only feedback.

Implementing temporally extended manager decisions needs explicit manager/executor rollout accounting and duration-aware returns. This is not achieved by merely nesting two stock MaskablePPO.learn calls. Store manager decision, exact focus, masks, behavior-policy probabilities, intervening transitions and boundaries; value targets must condition on the appropriate focus/selection context. A focus handoff is not game termination; bootstrap correctly across it. Keep collection/update versions controlled rather than changing the executor halfway through collecting manager data. Review this contract before code. The earlier lambda .95 is a comparison baseline, not settled by this proposal; determine traces and decision units before choosing lambda for either level.

Option-Critic provides primary conceptual support for policies over temporally extended options and learned termination without added rewards; this proposal is not an implementation of its algorithm. HIRO illustrates learned goal-conditioned lower control and the difficulty when lower-level behavior changes, but it uses an off-policy method in different domains and does not validate this PPO/focus design. SB3-Contrib documents invalid-action masking for ordinary PPO and does not supply this custom manager/worker training contract. Sources checked 16 November 2026:

- https://arxiv.org/abs/1609.05140
- https://arxiv.org/abs/1805.08296
- https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html

## How the proposal earns acceptance

First verify interface completeness: legal edits outside the focus remain available; target changes never create roads; wait and all native tool contexts work; every reward sums to the score change; goal boundaries do not silently terminate episodes; bounded zero-time behavior is diagnosed. These are future checks, not performed tests.

Then, only after separately authorized implementation/training, inspect frozen-checkpoint best/worst/near-average validation replays with focus overlays, complete actions and game time. Measure held-out scores, stalls, focus-switch frequency, time progress, and worker response to focus changes. In saved states compare action distributions under different focuses; this tests conditioning, not that every changed action is beneficial. Use matched-seed comparisons against constant/removed focus and review-interval variants, with uncertainty and repeated runs as feasible. Failure to improve held-out score, ignored focus or incessant switching argues for revising the hierarchy. Do not choose using the reserved final city or confuse a pretty focus overlay with effective strategy.

Outcome of this turn: documented proposal only. No new numerical experiment, model, training, engine patch, adoption or user-review mark. Current open decisions include user acceptance of focus semantics, cadence, weekly-head ownership, exact encodings, network dimensions, return/GAE contract, and deferred curriculum. No runnable new-trainer command exists.

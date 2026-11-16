# Maskable PPO — current decisions and detailed records

Updated 16 November 2026. **Start here on the other computer.**

The user approved publishing these detailed records on `Maskable-PPO`. We are preparing a fresh model; no new hierarchical trainer or training run exists yet. Older specifications and spreadsheets below preserve the complete reasoning and review history. **Later explicit decisions on this page and linked approvals take precedence over older snapshots.**

## Current decisions

| Topic | Choice and why | Status / detailed evidence |
| --- | --- | --- |
| Goal | Compete with Mohammad, then assess further progress; human-level performance is a goal, not a forecast | User direction; [original ledger](maskable-ppo-restart-decisions-2026-11-15.md) |
| Fresh source/model | Fresh weights; accepted simulator baseline `938b9f8`, version `2026-11-10.f34`; work on `Maskable-PPO` | User direction; source fixed, new training not implemented |
| Direct construction | Model chooses each neighboring road/bridge connection, including physically legal diagonals; allows bends, branches and shared roads | Approved; [ledger](maskable-ppo-restart-decisions-2026-11-15.md) |
| No route planner | No construction routes, candidate-route menu or automatic completion supplied by engineering; native vehicle routing is ordinary game logic | Strict user constraint; applies at every curriculum stage |
| Physical masks | Hide physically impossible actions only; do not prune legal choices for strategic reasons | Approved direction; pure masks still need implementation |
| Paused control | Multiple sequential edits, new observation after each; explicit one-second wait interrupted by native events | Approved; matches user's paused construction convention |
| Reward | Game score only; no goal, connection, wait or repair bonuses | Approved constraint; exact hierarchical return accounting still needs implementation |
| Observation | Structured visible board, buildings, infrastructure, demand/traffic, inventory, time and action context; no hidden future/RNG/engineered route answers | Approved contents; earlier numerical encodings are existing baselines requiring targeted hierarchy reconciliation |
| Hierarchy | Manager selects primary location and optional secondary; executor sees full board and may take any physically legal action, even outside focus | Adopted initial design; [full rationale, alternatives, termination and PPO risks](hierarchy-proposal-2026-11-16/README.md) |
| Focus cadence | Review after eight completed edits or one wait; executor can return control earlier; manager can keep the focus | Adopted provisional setting; coherent batches with opportunities to reprioritize, not a proven optimum |
| Curriculum | Basic connections → construction challenges → shared networks → growing cities → full games | Adopted direction; [rationale and approval sequence](curriculum-design-2026-11-16/README.md) |
| Stage 1 | One matching house/destination, short clear land gap, varied layouts, actual scored service | Approved concept; simplified scenario distribution, unchanged physical rules |
| Stage 1 gate | 180 simulated seconds; at least 90 of 100 held-out layouts each complete at least three scored trips | Explicitly approved starting rule; check native timing feasibility before applying it; not extra reward |
| Evaluation | Separate train/validation seeds; reserved final city; frozen-checkpoint best/worst/near-average replays | Existing directions preserved; [earlier exact protocol](maskable-ppo-spec-v1-2026-11-16/SPECIFICATION.md) requires only necessary curriculum/hierarchy reconciliation |
| Architecture/PPO | Existing observation, network, optimizer and credit topics were already discussed/reviewed; adapt their implementation to manager/executor rather than treating them as missing | [Historical exact specification](maskable-ppo-spec-v1-2026-11-16/SPECIFICATION.md); do not blindly adopt its flat-policy parameter count/config as a finished hierarchy |
| Linux hardware | Ryzen9 3950X, 16 cores/32 threads, nominal32GiB RAM, RTX2080Ti11264MiB; Ubuntu24.04.4 | [User-provided inventory and limits](linux-inventory-2026-11-16/README.md); supersedes uncertain Intel/2080Super inventory |
| Storage | User now reports30GBfree; calculated starting budget is20.680GiB plus rounding to25GiB(~27GB); request30GB,50GB comfortable | [Calculation and assumptions](linux-preflight-2026-11-16/STORAGE_BUDGET.md); package-payload measurement plus explicit allowances, not measured installed peak |
| Other Windows laptop | RTX5060-series prefix/about8GBVRAM; CPU/RAM/storage not verified; tools incomplete | [Separate partial inventory](alternative-laptop-2026-11-16/README.md); not selected as replacement |
| Roundabouts | Another person handles fidelity follow-up; do not expand our current task into a physics repair | Published comparison remains on `codex/driveway-physics`, commit `c37ce9a6eee1a5621bc40c1b546281a9ebc9f482` |

## Complete older details and spreadsheet history

- [Original restart checklist](maskable-ppo-restart-2026-11-15.md) and [chronological decision ledger](maskable-ppo-restart-decisions-2026-11-15.md): user statements, alternatives and reasons.
- [Full original v1 specification](maskable-ppo-spec-v1-2026-11-16/SPECIFICATION.md), [full decision JSON](maskable-ppo-spec-v1-2026-11-16/decisions.json), [configuration snapshot](maskable-ppo-spec-v1-2026-11-16/CONFIG.json), [city/seed manifest](maskable-ppo-spec-v1-2026-11-16/split_manifest.json): exact historical controls, inputs, architecture, PPO and evaluation proposals. No-hierarchy/no-curriculum and old device assumptions are superseded. These are not an executable current training configuration.
- [Reviewed workbook](review-row-confirmation-2026-11-16/Maskable_PPO_Decisions_Reviewed.xlsx) and [explicit review-row mapping](review-row-confirmation-2026-11-16/README.md):38Reviewed/13NotReviewed in the51-row sheet at that point. Later hierarchy/curriculum approvals are recorded separately, not silently written into the old workbook.
- [Earlier hierarchy/reopened-decision discussion](hierarchy-design-2026-11-16/README.md) and [dated 52-record JSON snapshot](hierarchy-design-2026-11-16/current_decisions.json). Its unresolved hierarchy wording is superseded by our later adopted focus hierarchy.
- [Migration provenance and file hashes](decision-record-migration-2026-11-16/README.md).

Approval, review, implementation and measured performance are separate. Initial choices are revisable engineering baselines; preserve user constraints and explain evidence-based changes. No long training run is authorized merely by publishing documents.

## Where we stopped / next

User reports Linux now has30GBfree and the branch clone succeeded at `~/mini_motorways`. Software environment setup is next. No new hierarchy model/trainer has been built. Confirm branch/path and create an isolated environment; choose compatible device/dependency versions deliberately. Sizing version snapshots are not adopted installation locks. No need to repeat settled design discussions.

Read [handoff](../../training/HANDOFF.md), [short progress overview](../../training/PLAN.md) and [chronological experiment history](../../training/EXPERIMENT_HISTORY.md). The old `mohammad` branch guidance is superseded for this restart by the user's explicit `Maskable-PPO` instruction. Do not modify/clean the separate dirty checkout while setting up this branch.

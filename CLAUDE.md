# Instructions for Claude Code in this repo

Active work (2026-11-14 to 2026-11-19): **gp-7 / cma-7** on branch `dynamic-gp`.
- **Before anything else, read `evolved_rules/HANDOFF.md`.** It has the setup, gates and progress checklist.
- Then read `evolved_rules/plans/2026-11-14-gp7-cma7-plan.md`, the operative plan.

Standing rules (full list in HANDOFF.md §1):
- Commit as the repo's existing author (`git log -1 --format='%an <%ae>'`). No Co-Authored-By line and no mention of Claude or AI in commits or files.
- Never push unless the user asks. When asked, push `dynamic-gp` to both `origin` and `upstream`, fast-forward only. Never touch `main`.
- Every evolution recap and table shows the population average next to the best (or mean).
- Validation maps are used only for the one pre-registered C\* pick (plan §2.2). Never tune or stop on validation. Never select, tune or stop on test maps, which are looked at once.
- Bump `CODE_VERSION` on any behaviour change. Never resume a run across code or simulator changes.
- Launch long runs detached, with the watchdog (HANDOFF.md §5), so they survive the agent session.
- Report failures and skipped steps plainly. Runs end as `budget`, not "converged".

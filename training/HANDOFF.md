# Continue here — Maskable PPO restart

Updated 16 November 2026. Read this before resuming. This is a handoff from a long design/setup chat, not evidence of implemented training.

## Exact stopping point

The user reports the Linux machine now has **30 GB free** and has just completed cloning:

```bash
git clone --branch Maskable-PPO --single-branch https://github.com/JoeJaffal/mini_motorways.git "$HOME/mini_motorways"
```

User said "done"; no clone output/revision or new df output supplied. No package installation, new model implementation or training has been completed in this chat. The next practical step is verify the Linux checkout/workspace and prepare an isolated Python environment, then install a deliberately chosen compatible stack and simulator build tooling. Do not mistake software setup for permission to launch long training. Before coding, reconcile old settings with the approved hierarchy; do not repeat settled design discussions.

The user will manually run Linux commands; no remote connection is configured or wanted. Give short, understandable commands in small useful batches and interpret results. They prefer simple explanations and a clear next step, not sprawling checklists or repeated approval of settled topics.

## Where work actually lives

- **Use this checkout:** `C:/Users/moham/mini_motorways-maskable-ppo`, branch **`Maskable-PPO`**. This explicitly supersedes AGENTS.md's old `mohammad` branch preference for this restart.
- Branch baseline/last checked remote: `938b9f80e67ca5341920a10e9e671164a474fc38`, simulator `2026-11-10.f34`. The clone initially received that baseline. Pull the documentation publication to obtain these decisions; simulator source baseline is unchanged.
- Original checkout `C:/Users/moham/mini_motorways` remains dirty on `codex/driveway-physics`. Do not switch, clean or stage its unrelated modifications. Older decision spreadsheets, ledger and dated decision JSON have now been copied byte-for-byte into this branch. See docs/training/DECISIONS.md for current precedence and migration provenance; original dirty checkout remains untouched.
- User now explicitly authorizes committing/pushing the detailed decision records on Maskable-PPO so the Linux clone can read them. This publication includes the new planning records and selected older archives. Update Linux with `git pull --ff-only origin Maskable-PPO` from `~/mini_motorways`; verify the pull result rather than assuming automatic sync.
- Root AGENTS.md documentation requirements apply: chronological `training/EXPERIMENT_HISTORY.md`, simulator/user decisions in `simulation/Docs/DESIGN_DECISIONS.md`, current status/index, durable small sources, no weights/binaries/private game material/secrets committed.

## Approved direction — preserve it

1. Fresh model aiming to compete with Mohammad, then see how far it can improve.
2. **No external road planner, generated routes, candidate-route menu or automatic completion.** Manager only selects focus; executor chooses every neighboring road/bridge connection, including legal diagonals. Ordinary native vehicle routing is still allowed.
3. Multiple sequential paused edits, each followed by observation. Explicit one-simulated-second wait, ending early at native weekly/game-over events. Physical game legality only in action masks, not strategic pruning.
4. Visible structured game state; game score only as reward. No connection/completion/congestion bonus or wait/edit reward manipulation.
5. **Adopted hierarchy:** manager selects primary tile and optional secondary tile; executor gets that focus plus full board and retains all physically legal edits, including outside the focus. Provisional review after eight completed edits or one wait; early executor handoff and native event interruption. Agent is responsible for backing this up and revising it against evidence. Detailed encodings/network dimensions/manager-executor PPO credit still need reconciliation, not a blank-slate redesign.
6. **Adopted curriculum:** basic connections → construction challenges → shared networks → growing cities → full games. Stage 1: one house and matching destination, short clear land gap, varied positions/orientations, model constructs and waits for real scored service. No generated construction path provided.
7. **Approved Stage 1 gate:** 180 simulated seconds per episode; at least 90 of 100 held-out practice layouts each complete at least 3 scored trips, evaluated with a frozen checkpoint. Paused building consumes no game time. Check native trip timing feasibility before using this initial gate. Exact inventory/event/scenario generator settings still need specification/reconciliation. Threshold is evaluation, not extra reward. Do not count operationally truncated episodes as completed passes.
8. Train/validation cities with distinct seeds and a reserved final city; retain best/worst/nearest-average replays for user evaluation. Prior exact full-game split/config proposals exist; do not pretend the topics have never been discussed. New practice distribution must be explicitly documented.
9. Roundabout comparison/fix belongs to another person; move on. Published report commit `c37ce9a6eee1a5621bc40c1b546281a9ebc9f482` on `codex/driveway-physics`, path `docs/training/roundabout-video-2026-11-16/REPORT.md`. No roundabout engine patch was applied by this work.

## Linux training machine — distinguish evidence from assumptions

User-supplied terminal output: Ubuntu24.04.4LTS, kernel6.8.0-149, Ryzen9 3950X (16physical cores/32threads), nominal32GiBRAM (31GiBreported), RTX2080Ti11264MiBVRAM, driver595.84. Python3.12.3, Git2.43.0; dotnet not found. Active Python had NumPy1.26.4, no torch/Gymnasium/SB3/Contrib. No benchmark or GPU-PyTorch validation.

Storage originally root/home476GiB,443GiBused,8.1GiBavailable,99%. Separate1.8TiBNTFS DATA `/dev/sda2` was unmounted; NVMe also has an unmounted469.8GiBNTFS partition. Mount command `udisksctl mount -b /dev/sda2 -o ro` required IT credentials; do not bypass/access other credentials or format/repartition. Unprivileged du only counted36GiB; exact discrepancy unresolved. User then reported30GBfree; accept as latest report, verify actual workspace during setup. No cleanup performed by agent.

Storage calculation now exists: [budget](../docs/training/linux-preflight-2026-11-16/STORAGE_BUDGET.md). Metadata/ZIP-directory measurements for candidate LinuxCPython3.12 stack: CPU16packages .760GiBunpacked/.209GiBdownloads; CUDA12.6 profile34packages6.159GiBunpacked/3.421GiBdownloads. Torch2.14.1 + current four requirements pins. With1GiBSDK/builds,.1GiBcode/git,5GiBinitial artifacts and5GiBsystem reserve, planned total20.680GiB; target25GiB(~27GB), rounded request30GB.50GBwas comfortable allowance, not a measured minimum. These are sizing scenarios, **not adopted/runtime-tested install locks**. Check RTX2080Ti binary support; do not install whatever CUDA nvidia-smi labels. Full dependency resolution/installed peak and artifact retention remain to verify. No Unity Editor or full CUDA toolkit included in budget.

Current headless project `simulation/Headless/TrafficHost.csproj` targets net8.0. Prior SDK8.0.427 used in source/analysis; official current .NET8page now says end-of-support. Reconcile support/version deliberately; no automatic simulator upgrade adopted. Build/run tooling may be user-local; do not presume admin access is necessary for training.

Alternative Windows laptop screenshots: RTX5060prefix, full suffix truncated,8151MiBVRAM, Python command missing/storealias, Git unrecognized, .NET host responds but noSDKfound. CPU20cores only user-reported; RAM/storage unknown. Not selected instead of Linux. Keep inventories separate.

## Read next, in this order

Start with [current decisions and detailed archive index](../docs/training/DECISIONS.md). This is the authoritative entry point for distinguishing later approvals from historical snapshots.

- [Short overview](PLAN.md)
- [Latest technical status](CURRENT_STATUS.md) — top entries supersede historical material below.
- [Hierarchy adoption and preserved proposal](../docs/training/hierarchy-proposal-2026-11-16/README.md)
- [Stage 1 approvals and earlier discussion](../docs/training/curriculum-design-2026-11-16/README.md)
- [Linux evidence/setup and storage data](../docs/training/linux-preflight-2026-11-16/README.md)
- [Chronological history](EXPERIMENT_HISTORY.md)

Migrated historical sources in this checkout (original copies also remain in the original checkout): `docs/training/hierarchy-design-2026-11-16/current_decisions.json`, `docs/training/maskable-ppo-spec-v1-2026-11-16/SPECIFICATION.md`, `docs/training/maskable-ppo-restart-decisions-2026-11-15.md`. They contain earlier flat-policy/default assumptions and stale no-hierarchy/no-curriculum/Intel-Windows descriptions. New explicit approvals above supersede those. Existing reviewed observations/network/PPO/evaluation topics should be kept where compatible, changed only with concrete reasons. Original workbook unreviewed Excel rows were20,28,47–49,51–58; review is not implementation, and later hierarchy/curriculum approvals update their own topics.

## Immediate next action

Continue Linux setup after the reported successful clone. Confirm the checkout path/branch and available writable space with simple commands if needed, then create/check an isolated environment. Do not issue a training command: the new hierarchy trainer is not implemented. Plan a complete compatible dependency installation before consuming the newly available30GB; avoid copying7.37GBWindows scratch/output/venv wholesale. Maintain this handoff/status/history with material progress. No need to ask user to explain the project again.

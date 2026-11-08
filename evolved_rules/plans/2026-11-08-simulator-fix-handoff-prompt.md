# Prompt for the simulator-fix session

Paste everything below the line into a new Claude Code session opened in `C:\Projects\490 - Project\mm-ppo`.
(Revised 2026-11-08, after Mohammad pushed `f7ce005`.)

---

I need you to continue and finish a simulator update that Mohammad stopped halfway, and remove the simulator's bugs. This is the C# Mini Motorways simulator in `simulation/`, plus its headless host.

**Where the work is**
- The repo is `mini_motorways`. Remotes: `upstream` = github.com/JoeJaffal/mini_motorways (Mohammad's) and `origin` = github.com/aya007kh/mini_motorways (mine).
- The update is on Mohammad's branch, `upstream/mohammad`. On 2026-11-08 the tip was **`f7ce005`**, "Save emergency replay fidelity checkpoint and continuation plan" (301 files). Run `git fetch upstream` first, and tell me if the tip has moved.
- Work in this folder, `C:\Projects\490 - Project\mm-ppo`. It is a git worktree, currently a detached HEAD at the old `a652042`, with an untracked `.venv-ppo/` (leave that alone). Start with `git switch -c mohammad --track upstream/mohammad`.
- **Do not touch** the other worktrees:
  - `C:\Projects\490 - Project\mini_motorways` is branch `gp4`, my Evolved Rules work. Another session continues there after you finish.
  - `C:\Projects\490 - Project\mm-revalidate`.

**Read these first**
1. `AGENTS.md`, the repo's documentation rules. Follow them.
2. **`docs/training/full-replay-review-2026-11-08/EMERGENCY_HANDOFF.md`**: Mohammad's continuation plan. Its "How to resume safely" steps are the plan.
3. `simulation/Docs/IMPLEMENTATION_STATUS.md`, `simulation/Docs/DESIGN_DECISIONS.md` and `training/CURRENT_STATUS.md`.

Then summarize back to me what you think is finished, what isn't, and what is blocked. Do that before changing anything.

**This machine is not Mohammad's machine.** The handoff assumes things that are missing here:
- There is no `tmp/` folder, so no `tmp/dotnet`, no local video boards, crops, camera, clock or house data, and no `trace-v20.json` working copy. Use the system .NET SDK 8.0.427 (`dotnet`) in place of `.\tmp\dotnet\dotnet.exe`.
- The source video (`C:/Users/moham/Downloads/screen-capture (2).webm`) is not here.
- Unity 6000.6.0f1 is at `C:\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe`.
- Mohammad's installed 74-suite player and its backups are probably not here either. Check `simulation/Builds/`.

So handoff steps 3–4 (the seven replay-input corrections and regenerating the candidate from the builder) probably can't be done fully here. Work out which steps can be done with what is in Git, and tell me. Ask me whether to get the missing files from Mohammad; don't work around them by guessing.

**Priority order**
1. **Verify the engine source.** The 77-suite source was never re-tested after the last `NativeDriveways.cs` dedup edit (handoff step 2). Build it and run `dotnet run --project simulation/Headless/TrafficHost.csproj -- --self-test`. Then run the 7-environment, 6-reward and 10-map checks (step 7). Fix any failures, with a test for each.
2. **Finish the engine repairs listed in the handoff, and find and fix the remaining gameplay bugs.** In particular, investigate the long 20–38 s queues near roundabout 19,9 (step 5). The handoff marks the future-junction/yield-cycle cause as a hypothesis: prove the cause before changing anything.
3. **Do the replay-fidelity work the local files allow.** Never tune traffic, materials or demand to hit the recorded 835 trips, and never relax tests or overwrite historical fixtures (the handoff's rules).
4. **Rebuild the Unity Original player only after the source is stable.** Use `ProjectSetup.BuildOriginalWindows` with `--traffic-build-root` into a new staging folder.

Ask me (the user) whether there are other bugs on my list. I'll tell you.

**Two programs depend on the headless host, so protect its interface**
- **Evolved Rules (my GP agent, on `gp4`)** loads `simulation/Headless/bin/Release/net8.0/TrafficHost.dll`, built with `dotnet build simulation/Headless -c Release`. It speaks the one-JSON-line protocol in `simulation/Headless/README.md`.
  - It reads car `stage`, `speed` and `waiting`, uses the `TrafficLight` and `Roundabout` build tools and makes package choices.
  - It replays recorded commands to verify games.
  - Read `git show gp4:evolved_rules/host.py`, `git show gp4:evolved_rules/state.py` and `git show gp4:evolved_rules/session.py` before changing any request or observation field.
  - Keep the protocol backward compatible where you can, and document anything you can't.
- **Mohammad's PPO** (`training/` on `mohammad`) uses the same host.
- **Please add a simulator version string** that the host reports, for example in the reset response. Our result caches can then key on it, so results from the old simulator are never reused by mistake.

**Simulator issues we noticed from the agent side** (check whether each is a bug, and fix it if so):
1. In `TrafficControl.cs` (around line 226 before `f7ce005`, which changed that file a lot), a car's `Waiting` is updated only for cars that get a movement proposal. Cars that are parked or at home seem to keep their last `Waiting` value, so observations show stale waits. Check `TotalWaiting` and the observation's `MeanWaiting` too.
2. Running 10 headless hosts in parallel crashed a .NET host with 0x800705AA (out of system resources). 8 are fine. This is probably the machine, not a bug, but note it if you see a cause.

**What "done" means**
- The engine source passes every suite (self-test, environment, reward and map checks), and each fix has a test that failed before it.
- `dotnet build simulation/Headless -c Release` and `python scripts/verify_five_maps.py` pass.
- The docs are updated as `AGENTS.md` requires:
  - the emergency handoff report (or a successor report);
  - `DESIGN_DECISIONS.md`, `IMPLEMENTATION_STATUS.md`, `training/CURRENT_STATUS.md` and `training/EXPERIMENT_HISTORY.md`;
  - a short note for the model re-evaluation session, `simulation/Docs/HANDOFF-2026-11-sim-fix.md`. It lists:
    - every commit;
    - every change to gameplay or scoring, which tells us which old results are now invalid;
    - every change to the headless protocol;
    - the simulator version string;
    - the exact build commands;
    - anything still unverified.

**Rules**
- Debug systematically: reproduce first, then a failing test, then the fix. Report test output faithfully, and never claim something is verified when it hasn't been run.
- Commit under the repo's configured identity (Aya <aya2007k@gmail.com>). **Never add Co-Authored-By or any Claude attribution.**
- **Never push, merge or open a PR without asking me first.** `mohammad` is Mohammad's branch. Never commit to `main`.
- **No training runs.** Ask me before any run of more than 20 games, and before changing gameplay rules that aren't bugs.
- Never commit private game files, the video, decompiled code, builds or binaries (`AGENTS.md`).
- When you finish, tell me:
  - the branch and its commits;
  - what changed in gameplay;
  - whether the protocol changed;
  - the version string;
  - where the handoff note is.

I will take that back to the Evolved Rules session.

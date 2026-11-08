# Prompt for the simulator-fix session

Paste everything below the line into a new Claude Code session opened in `C:\Projects\490 - Project\mm-ppo`.

---

I need you to finish an unfinished simulator update and remove its bugs. This is the C# Mini Motorways simulator in `simulation/`.

**Where the work is**
- The repo is `mini_motorways`. Remotes: `upstream` = github.com/JoeJaffal/mini_motorways (Mohammad's) and `origin` = github.com/aya007kh/mini_motorways (mine).
- The update is happening on Mohammad's branch, `upstream/mohammad`. On 2026-11-08 its tip was `a652042` (2026-11-02). Its last commit that touched `simulation/` was `a9dd107` (2026-10-28).
- **The unfinished update is not on GitHub yet.** Before anything else, ask me where it is: a newer push to `mohammad`, a patch, or files from Mohammad. Then fetch it (`git fetch upstream`).
- Work in this folder, `C:\Projects\490 - Project\mm-ppo`. It is a git worktree, currently a detached HEAD at `a652042`, with an untracked `.venv-ppo/` (leave that alone). Start a local branch with `git switch -c mohammad --track upstream/mohammad`, or base it on the newer commit once it is fetched.
- **Do not touch** the other worktrees:
  - `C:\Projects\490 - Project\mini_motorways` is branch `gp4`, my Evolved Rules work. Another session continues there after you finish.
  - `C:\Projects\490 - Project\mm-revalidate`.

**What "done" means**
1. The unfinished update is complete, and every bug I describe (ask me for the list) is fixed with a test that failed before the fix.
2. These all pass:
   - `dotnet build simulation/Headless -c Release`
   - `dotnet run --project simulation/Headless -- --self-test`
   - the shared simulation suites recorded in `simulation/Reports/simulation-checks.txt`
   - `python scripts/verify_five_maps.py` (after building the host)
   - If the Unity viewer needs rebuilding: Unity 6000.6.0f1, batch build `ProjectSetup.BuildOriginalWindows`.
3. The docs say what changed:
   - Update `simulation/Docs/IMPLEMENTATION_STATUS.md` and `DESIGN_DECISIONS.md`.
   - Write a handoff note, `simulation/Docs/HANDOFF-2026-11-sim-fix.md`, for the session that re-evaluates the AI models. It lists:
     - every commit;
     - every change to gameplay or scoring, which tells us which old results are now invalid;
     - every change to the headless JSON protocol (requests, observation fields, build tools);
     - the exact build commands.

**Two programs depend on the headless host, so protect its interface**
- **Evolved Rules (my GP agent, on `gp4`)** loads `simulation/Headless/bin/Release/net8.0/TrafficHost.dll`. It speaks the one-JSON-line protocol in `simulation/Headless/README.md`.
  - It reads car `stage`, `speed` and `waiting`, uses the `TrafficLight` and `Roundabout` build tools and makes package choices.
  - It replays recorded commands to verify games.
  - Read `git show gp4:evolved_rules/host.py`, `git show gp4:evolved_rules/state.py` and `git show gp4:evolved_rules/session.py` before changing any request or observation field.
  - Keep the protocol backward compatible where you can, and document anything you can't.
- **Mohammad's PPO** (`training/` on `mohammad`) uses the same host.
- **Please add a simulator version string** that the host reports, for example in the reset response. Our result caches can then key on it, so results from the old simulator are never reused by mistake.

**Simulator issues we noticed from the agent side** (check whether each is a bug, and fix it if so; ask me if you're unsure it's in scope):
1. `TrafficControl.cs:226` updates a car's `Waiting` only for cars that get a movement proposal. Cars that are parked or at home seem to keep their last `Waiting` value, so observations show stale waits. Check `TotalWaiting` and the observation's `MeanWaiting` too.
2. Running 10 headless hosts in parallel crashed a .NET host with 0x800705AA (out of system resources). 8 are fine. This is probably the machine, not a bug, but note it if you see a cause.

**Rules**
- Debug systematically: reproduce first, then a failing test, then the fix. Report test output faithfully.
- Commit under the repo's configured identity (Aya <aya2007k@gmail.com>). **Never add Co-Authored-By or any Claude attribution.**
- **Never push, merge or open a PR without asking me first.** `mohammad` is Mohammad's branch. Never commit to `main`.
- Ask me before any run of more than 20 games, and before changing gameplay rules that aren't bugs.
- When you finish, tell me:
  - the branch and its commits;
  - what changed in gameplay;
  - whether the protocol changed;
  - where the handoff note is.

I will take that back to the Evolved Rules session.

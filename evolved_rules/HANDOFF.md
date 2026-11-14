# HANDOFF: gp-7 / cma-7 on a new machine (written 2026-11-14)

You are an agent picking up the gp-7 / cma-7 work on a fresh machine. The old machine's memory and scratch files are not available. Everything you need is in this file, in **`evolved_rules/plans/2026-11-14-gp7-cma7-plan.md` (the operative plan)** and in the git history.
- The 2026-11-13 draft and `evolved_rules/plans/gp7-planning/` are background only.
- `evolved_rules/EXPERIMENTS.md` is the experiment log.
- If this file and the plan seem to conflict, the plan's pre-registered procedure wins; note it in the write-up.

**Deadline: everything (code, runs, validation, test, write-up, commit) done by 2026-11-19.**

## 1. Standing rules (from the user; follow them exactly)

1. **Commits.**
   - Commit as the repo's existing author (`git log -1 --format='%an <%ae>'`, currently Aya). Set it with `git config user.name` / `user.email` before your first commit.
   - **No Co-Authored-By line and no mention of Claude or AI** in commits or files. `.claude/settings.json` turns attribution off.
2. **Pushing.**
   - Never push unless the user asks. The user publishes this work on branch `dynamic-gp` on **both** `origin` (aya007kh) and `upstream` (JoeJaffal). When asked to push, push `dynamic-gp` to both, fast-forward only, never force.
   - Ask once, early, whether you may push at milestones.
   - Never touch `main`.
3. **Averages.** Every evolution recap and every EXPERIMENTS.md table shows the **population average next to the best (or mean)**, both labelled.
4. **Seed blocks.**
   - **Validation (1550-1749)** is used for exactly one thing: the pre-registered choice of C\* in plan §2.2 (`stats7.decide_headline`), plus the descriptive gp-7 vs cma-7 contrast (plan §2.4). Never tune, stop, calibrate, choose x0\* or promote a sample on validation.
   - **Test (6100-6999, 7000-7099):** never select, tune or stop on it; it is looked at once.
   - **Race probes (10000+)** are used once each.
5. **Version discipline.**
   - Bump `CODE_VERSION` on any behaviour change.
   - Never resume a run across a code or simulator change. A fork into a new run folder under a new CODE_VERSION is allowed (plan §3.4).
   - Long jobs run from frozen worktrees (plan §4).
6. **Run budgets.** The budget table you commit in §6 is pre-approved. Log every run's game count in `output/evolved_rules/ops/runs.log` and in §7.
7. **Worker count** comes from the measured sweep (§4).
8. **Simulator files.** If any file under `simulation/` changes (none should), `evolved_rules/verify.py`'s `VERIFIER_COMMIT` must move to a pushed commit.
9. **Honesty.** Say plainly when something failed or was skipped. Runs end with status `budget`.
10. **Detached runs.** Launch long runs detached (§5). An agent session can die; the runs must not die with it.

## 2. State of the world at handoff

**Code and simulator.**
- Simulator f34 (`2026-11-10.f34`), from upstream main 938b9f8 via commit `b96d98d` (= `VERIFIER_COMMIT`).
- **Tag `gp6-final` = commit `f7bf5f5efaee57e8cb68341952fa18dd531160bc` (`f7bf5f5`).** That is gp6's tip `dfd8532` plus documents and data only. **Its code is identical to `dfd8532`.**
- Branch **`dynamic-gp`** continues from it, merged with upstream main `938b9f8` (identical simulator; adds Mohammad's `training/` and `docs/training/`, untouched by this work). `simulation/` is unchanged since `b96d98d`.

**The previous version (gp-6 / cma-6).**
- Both runs stopped at 15 generations by the user's decision, with status `budget`. See EXPERIMENTS.md.
- **gp-6** never displaced its seed, cma-1, at 1027.7 on validation 1500-1549.
- **cma-6's** best sample showed 1037.0 on validation, best-of-10 (empirical Bayes about 1006).

**Close-out battery** on 200 never-played maps (LA 5100-5299, gp6-v1 code, old machine, 12 workers).
- Per-arm `games.jsonl` and `summary.json` are under `evolved_rules/closeout/gp6/<run>/`.
- Rule texts are in `evolved_rules/seeds/gp7/`.

| Arm | Rule | Games | Mean trips | Median | SD | Mean s/game | vs cma-1 3-tree |
|---|---|---|---|---|---|---|---|
| cma-1 3-tree | `fa7648c7` | 200 | 1021.2 | 1015.5 | 285.6 | 1431 | - |
| cma-1 5-tree (gp-6 incumbent) | `1d6a7017` | 200 | 1021.2 | 1015.5 | 285.6 | 1431 | +0.0 (identical games) |
| cma-6 final mean | `39954974` | 200 | 1013.0 | 996.0 | 264.4 | 1427 | -8.2 (paired SE 19.2, t -0.43) |
| cma-6 best sample | `3d999a2c` | 200 | 996.0 | 988.5 | 273.5 | 1415 | -25.3 (paired SE 18.9, t -1.34) |
| gp-6 tree | `7fa4b2ec` | 200 | 956.6 | 989.5 | 282.0 | 1384 | -64.7 (paired SE 27.6, t -2.34) |
| separated (built-in) | - | 200 | 865.2 | 890.5 | 266.9 | 1326 | -156.1 (paired SE 25.8, t -6.04) |
| hand (built-in) | - | 200 | 545.4 | 521.0 | 184.5 | 1095 | -475.8 (paired SE 24.6, t -19.36) |

Average over the 5 learned arms: 1001.6 trips (best 1021.2).

Corrected for 6 comparisons (Holm, paired t on 200 maps): only separated (−156.1) and hand (−475.8) differ significantly from cma-1 3-tree. cma-6 mean −8.2 (Holm p 1.0, BCa 95% CI [−45, 29]), cma-6 best −25.3 (Holm p 0.55, [−63, 10]), gp-6 `7fa4b2ec` −64.7 (raw p 0.020, Holm p 0.08, [−120, −12]).

**L = cma-1 3-tree** (rule text `evolved_rules/seeds/gp7/cma1_3tree.txt`, identical to `final/cma_final.txt`; close-out games `evolved_rules/closeout/gp6/c6-cma1-3tree/`). It has the highest mean of the learned arms, so the tie rule is not needed. L is played only by `gp6-final` code (plan §2.1).

**Seed scan.** No local worktree on the old machine has games on 1550-1749, 3300-3599, 5300-5399, 6100-6999 or 10000+.

**Old machine.**
- Throughput: about 207–292 games/h at x0 quality on 12 workers (i7-13620H, 16 threads, 15.6 GB). Per-game SD 265–285 trips. Per-game cost grows with score.
- Software: Python 3.12.5, numpy 2.5.4, scipy 1.18.1, deap 1.4.4, cma 4.5.0, .NET SDK 8.0.427 (runtime 8.0.33), Windows 11 x64.

## 3. Setup on the new machine (PowerShell; in order)

`<main>` means the absolute path of your clone.

1. **Install.** Windows x64, git, **Python 3.12.x**, and the **.NET 8 SDK** (runtime 8.0.33 if possible).
2. **Clone the right branch.** `git clone https://github.com/aya007kh/mini_motorways.git` (or the upstream JoeJaffal/mini_motorways; both have the branch), then `cd mini_motorways; git checkout dynamic-gp`. **Never work from `main`:** it has none of this code.
3. **Check the history:**
   - `git fetch origin --tags` (and `git fetch --unshallow` if the clone is shallow);
   - `git cat-file -t b96d98d` prints `commit`;
   - `git rev-parse gp6-final^{commit}` prints the hash in §2. If the tag is missing, run `git tag gp6-final <hash>`;
   - `git diff --quiet b96d98d HEAD -- simulation; $LASTEXITCODE` prints 0;
   - `git diff --quiet dfd8532 gp6-final -- simulation evolved_rules ':!evolved_rules/ops' ':!evolved_rules/closeout' ':!evolved_rules/seeds/gp7' ':!evolved_rules/plans' ':!evolved_rules/analysis/gp7' ':!evolved_rules/HANDOFF.md' ':!evolved_rules/EXPERIMENTS.md'; $LASTEXITCODE` prints 0.
4. **Add the upstream remote.** `git remote add upstream https://github.com/JoeJaffal/mini_motorways.git; git fetch upstream`. Some tests need `upstream/mohammad`.
5. **Git identity.** `git config user.name "Aya"; git config user.email (git log -1 --format=%ae)`.
6. **Python.** `py -3.12 -m venv .venv; .\.venv\Scripts\pip install -r evolved_rules\requirements.txt`.
7. **Build the host.** `dotnet build -c Release simulation\Headless\TrafficHost.csproj`, which produces `simulation\Headless\bin\Release\net8.0\TrafficHost.dll`.
8. **Carry-over zip.** Unzip it (`gp7-carryover.zip`, from the user) into `<main>`. It only adds history files under `output/`. Nothing depends on it; see its `CARRYOVER.md`.
9. **Tests.** `.\.venv\Scripts\python -m pytest evolved_rules\tests -rs`.
   - **Acceptable skips:** another simulator's fingerprint table, or slow tests gated on `EVOLVED_RULES_SLOW`.
   - **Must be fixed:** any skip that names a missing DLL, verifier or remote.
   - D1 (§4) is the real-game determinism check.
10. **Old-code worktree for L.** `git worktree add ..\mm-gp6-final gp6-final; cd ..\mm-gp6-final; dotnet build -c Release simulation\Headless\TrafficHost.csproj; cd <main>`.
    - Build it inside the worktree, because bin/ is gitignored. Leave `EVOLVED_RULES_HOST_DLL` unset everywhere.
    - L and hand always run **with their working folder set to `..\mm-gp6-final`** and the main clone's venv python. `python -m evolved_rules...` imports the code of the working folder.
11. **Power and updates.**
    - `powercfg /change standby-timeout-ac 0; powercfg /change hibernate-timeout-ac 0`. On a laptop, set lid action to "do nothing".
    - Pause Windows Update until 2026-11-20 (Settings → Windows Update → Pause).
    - Note that after a reboot nothing restarts until the user logs on. Either ask the user to set up auto-logon, or register the tasks with `-User/-Password` so they run whether or not anyone is logged on.
12. **Time zone.** Record the machine's **UTC offset** in §6. All plan times are this machine's local time.

## 4. Gates, throughput, L pre-play (plan Block A)

**Worker sweep, run first.**
- From `..\mm-gp6-final`, play L on **5200-5299** (close-out maps, already played) at W = physical cores, logical − 2 and logical − 1.
- Use the same 100 seeds for each W, with run names `sweep-W<w>`. Time each run:

  ```
  $env:PYTHONHASHSEED='0'
  $t = Measure-Command { & '<main>\.venv\Scripts\python.exe' -m evolved_rules.evaluate --policy tree:<main>\evolved_rules\seeds\gp7\<L file> --seeds 5200-5299 --workers <w> --run sweep-W<w> }
  ```

- Throughput = 100 / $t.TotalHours.
- Pick the fastest W whose peak RAM stays below 80%. **R0** = games/h at that W.

**D1, determinism against the old machine.**
- From `..\mm-gp6-final`: L on 5100-5159 at W, run `d1-L`.
- Compare trips, seconds and commands per seed with `<main>\evolved_rules\closeout\gp6\<L run>\games.jsonl`.
- **Pass:** identical.
- **Fail:** record it in §7 and never compare numbers across machines (the protocol re-plays every row here anyway). Continue.
- Also confirm that `d1-L`'s summary.json `config.commit` equals the gp6-final hash.

**D2, repeatability on the new machine.** Re-play 5100-5109 as `d2-L`; it must equal `d1-L` on those seeds. If not, **stop**: caching and pairing are invalid until fixed.

**Budget table.** Fill in §6 with the formulas from plan §6 (n_s, n_val, n_test, (λ, m), T_stop, ladder rung), then commit.

**L pre-play queue**, detached, from `..\mm-gp6-final`, using `<main>\evolved_rules\ops\battery7.py`. That script is chunked (100 seeds), restartable, single-instance, and never prints scores. Run in this order:
1. L on 3300-(3299+n_s), prefix `pre-L-screen`;
2. L on 6100-6999, prefix `pre-L-test`;
3. L on 1550-(1549+200), prefix `pre-L-val`;
4. hand on 6100-6999, prefix `pre-hand-test` (policy `hand`).

Put the four calls in one small `.ps1` under `<main>\output\evolved_rules\ops\` and launch it with WMI (`Invoke-CimMethod Win32_Process Create`, CurrentDirectory = `..\mm-gp6-final`).
- **Pausing for the screen:** create `<main>\output\evolved_rules\ops\queue.pause`; the queue finishes its current chunk and waits. Delete the file to resume.
- **After a crash or reboot,** rerun the .ps1 (finished chunks are skipped). You can register it as a second scheduled task (every 30 min plus at logon); the lock prevents double runs.
- **Results** are in `..\mm-gp6-final\output\evolved_rules\runs\pre-*`. Do not read scores until they are used. Check each chunk's `config.commit` equals the gp6-final hash.

## 5. Running things so they survive

**Watchdog for evolve7 runs** (`evolved_rules/ops/watchdog7.ps1`). It reads `<main>\output\evolved_rules\ops\runs7.json`, with one entry per run and its frozen worktree as `RepoDir` (format in the script header). Register it from an elevated PowerShell:

```
$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"<main>\evolved_rules\ops\watchdog7.ps1`""
$t1 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 30)
$t2 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName gp7-watchdog -Action $a -Trigger $t1,$t2 -Settings $s -Force
Start-ScheduledTask gp7-watchdog   # then check output\evolved_rules\ops\watchdog7.log got a line
```

If no elevated shell is available, drop `$t2` and say so.

**Frozen worktrees.** For each long job, `git worktree add ..\mm-<job> <tag or hash>` and build its DLL there (step 10's command), or run it with `EVOLVED_RULES_HOST_DLL` written into the launched command line. Code is edited only in `<main>`.

**When runs end,** remove their entries from runs7.json. At the end, run `Unregister-ScheduledTask gp7-watchdog -Confirm:$false`, plus the queue task if you made one.

## 6. Budget table (fill in at setup, then commit)

| Item | Value |
|---|---|
| Machine (CPU, cores/threads, RAM, OS) | |
| UTC offset | |
| W (workers) and sweep results | |
| R0 (games/h at W) | |
| Ladder rung | |
| n_s (screen maps per point) | |
| n_val | |
| n_test (target) | |
| (λ, m) | |
| Launch (actual) | |
| T_stop (initial) | |
| T_freeze | 2026-11-19 08:00 local |

## 7. Progress checklist (tick, add a note and commit at each milestone, so a fresh session can resume from git)

- [ ] Setup steps 1–12 done
- [ ] Worker sweep, R0; D1 (pass/fail: ____); D2 pass; budget table committed
- [ ] L pre-play queue started; alive or finished? (check at every milestone and after any reboot)
- [ ] Watchdog registered and tested
- [ ] C4-min + decision logging; identity tests (1), (3), edge-cost unit, text round trip: pass
- [ ] x0 calibration (pair-open ____%, evo-built ____%)
- [ ] Screen done (n_s ____); x0\* = ____; scales and θ frozen
- [ ] linear.py identity (4), evolve7, stats7, smoke: pass (or F2 at CL2a)
- [ ] Pre-registration committed (hash ____)
- [ ] cma-7 trunk launched from worktree `cma7-launch` (time ____, W ____, λ/m ____)
- [ ] gp-7-lite forked at gen ____ from `gp7-fork` (or dropped at CL3)
- [ ] Runs stopped at T_stop (status budget; gens: cma-7 ____, gp-7 ____)
- [ ] Challenger commit and text hashes frozen; validation played; C\* = ____
- [ ] Test played once (n = ____); result ____; headline = ____
- [ ] EXPERIMENTS.md entry (average next to best); results copied to `evolved_rules/final/gp7/`; committed
- [ ] Scheduled tasks removed

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
   - Answer (user, 2026-11-14): push at every HANDOFF §7 milestone **and at every gate** (identity gates, fork gate, cut-lines, trend guard, validation and test), pass or fail, once its record is committed.
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
11. **Seed counters.** Keep every seed counter below 49999 (user, 2026-11-14). The gp-7 race-probe counter runs 10000-49999 (`evolve7.PROBE_LAST`); an epoch that would pass it skips its race.
12. **Seed conflicts.** The user's other session StrokeQ (another model) reports seed conflicts. It was sent this project's seed blocks on 2026-11-14. Tell it about any new block. Check what it reports against plan §7 and tell the user before changing a run. StrokeQ confirmed no overlap on 2026-11-14: it uses LA 50000-61399 only, and its avoid list covers all of gp-7's blocks. Promised to StrokeQ: (a) a message before any change to `simulation/` or the simulator version (f34); (b) after T_stop, the champion's spec (text hash, commit) and its test mean, median, best and n, compared with cma-1's 1021.2 (a possible DAgger teacher).

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

**macOS (the machine actually used; added 2026-11-14).** `evolved_rules/ops/watchdog7_mac.py` replaces `watchdog7.ps1` and the separate queue task:
- **Same run list** (`output/evolved_rules/ops/runs7.json`, same evolve7 fields, `RepoDir` absolute) plus a `"Kind": "queue"` entry for restartable shell scripts such as the L pre-play queue (`Script`, `DoneFile`), so one agent supervises both. Optional `"Env"` per entry. Same rules: alive → leave; status converged/budget/stopped (or DoneFile present) → done; else start (ResumeArgs once checkpoint.pkl exists); hold after 8 starts in 2 h.
- **Detached and awake.** Each job starts in its own session (`start_new_session`) under `caffeinate -ims`, with `PYTHONHASHSEED=0`, `DOTNET_ROOT=~/.dotnet` first on PATH and `EVOLVED_RULES_HOST_DLL` removed unless the entry's Env sets it. On macOS `caffeinate <cmd>` runs the command under the original pid and forks a helper that holds the assertion, so the recorded pid (`<ops>/<Name>.pid`) is the job itself.
- **Scheduler.** A user LaunchAgent `com.minimotorways.gp7-watchdog` (every 600 s and at load; `AbandonProcessGroup` so a pass never kills its jobs): `.venv/bin/python evolved_rules/ops/watchdog7_mac.py --install` (or `--status`, `--uninstall`). No admin needed. A LaunchAgent runs only while the user is logged in; after a reboot nothing restarts until login (as on Windows).
- **Priority (fixed 2026-11-14 17:52).** The agent first used `ProcessType = Background`, which gives every job it starts (and their children) background QoS: priority 4, throttled onto the efficiency cores. The screen and the L pre-play ran at about 40% of the machine for 23 minutes until this was seen; both were stopped and restarted (`ProcessType = Interactive`, priority 31). Nothing was lost: the screen keeps its finished games in its cache and battery7 replays the interrupted chunk (`pre-L-screen-3300.failed-1`). Check with `ps -Ao pid,pri,command` (31 = normal).
- **At the end:** `.venv/bin/python evolved_rules/ops/watchdog7_mac.py --uninstall`.
- Tests: `evolved_rules/tests/test_watchdog7_mac.py` (macOS only).

## 6. Budget table (fill in at setup, then commit)

| Item | Value |
|---|---|
| Machine (CPU, cores/threads, RAM, OS) | Mac mini, Apple M4 (10 cores: 4 performance + 6 efficiency, no SMT), 16 GB, macOS 15.6 (24G84), arm64. **Not the Windows x64 machine this handoff was written for**: see the setup note in §7. |
| UTC offset | UTC+02:00 (EET), recorded 2026-11-14 15:39 local |
| W (workers) and sweep results | **W = 10.** L on 5200-5299 from `../mm-gp6-final`, 2026-11-14, each run under caffeinate, nothing else running: W=10 754 s → 477.4 games/h (min free RAM 60%); W=9 911 s → 395.1 (64%); W=8 881 s → 408.6 (64%); W=4 (performance cores only) 1344 s → 267.8 (65%; the last minutes overlapped light unit tests). The 9 < 8 inversion is likely tail noise (100 games; the last long games set the wall time). Peak RAM use ≤ 40%, far below the 80% cap. |
| R0 (games/h at W) | 477.4 (W=10). Planning rate for new code R = 0.85·R0/1.25 = 324.6 games/h; re-measure each generation. |
| Ladder rung | R0 > 250: **cma-7 trunk + gp-7 fork** |
| n_s (screen maps per point) | 300 (5·300/R = 4.6 h ≤ 7 h) |
| n_val | 200 (R ≥ 150) |
| n_test (target) | 900 (k = 3 challengers: G_post = 3·200 + 900 = 1,500 games, G_post/R = 4.6 h ≤ 14 h) |
| (λ, m) | (24, 12), the largest option: ≈ 277 games/gen for cma-7 (≈ 40.7 gens) and ≈ 301 for gp-7 (≈ 37.4 gens), both ≥ 25. Per arm ≈ 11,260 games = R × 14 h before the fork + R/2 × 41.4 h after, computed with launch at the latest allowed time (Nov 16 18:00); an earlier launch only adds generations. |
| Launch (actual) | not yet launched |
| T_stop (initial) | **2026-11-19 01:22 local (+02:00)** = T_freeze − G_post/R − 2 h = 08:00 − 4.62 h − 2 h. May only move earlier. |
| T_freeze | 2026-11-19 08:00 local |

Derived (2026-11-14): the L pre-play queue is n_s + n_val + 900 + 900 hand = 2,300 games, ≈ 4.8 h at R0 (old code, so no 1.25 factor); the screen is 5 points × 300 = 1,500 games ≈ 4.6 h at R. A 100-seed chunk of new code takes ≈ 18.5 min at R, so no chunk starts after T_freeze − 22 min (07:38 on Nov 19).

## 7. Progress checklist (tick, add a note and commit at each milestone, so a fresh session can resume from git)

- [x] Setup steps 1–12 done (2026-11-14: all done on the Mac; step 11: automatic macOS updates off, confirmed by the user, `AutomaticallyInstallMacOSUpdates = 0`; see note)

  **Setup note, 2026-11-14 (macOS port of §3).** The user decided the runs happen on this Mac mini (Apple M4, macOS 15.6), not on Windows. What was done, per step:
  1. .NET SDK 8.0.427 (runtime 8.0.33, the old machine's versions) from Microsoft's osx-arm64 tarball, sha512 checked against the 8.0 `releases.json`, unpacked to `~/.dotnet` (Homebrew's prefix is not writable by this user). It is not on the login PATH: every command sets `DOTNET_ROOT=$HOME/.dotnet` and puts it first on `PATH`. Python 3.12.11 from Homebrew (old machine: 3.12.5).
  2.–3. The clone is on `dynamic-gp`, fast-forwarded to `848d644`. All five history checks pass (not shallow; `b96d98d` is a commit; `gp6-final` = `f7bf5f5`; `simulation/` unchanged since `b96d98d`; gp6-final code = `dfd8532`).
  4. `upstream` added. On this clone `origin` is also JoeJaffal/mini_motorways; the aya007kh fork is not configured (matters only for pushing).
  5. Repo-local `user.name` set to `Aya` (the email already matched the history).
  6. `.venv` with the pinned requirements (numpy 2.5.4, scipy 1.18.1, deap 1.4.4, cma 4.5.0).
  7. Host builds; `--version` prints `2026-11-10.f34`.
  8. Carry-over zip unpacked into `output/` (its `CARRYOVER.md` readme left out).
  9. Tests: 801 passed, 23 skipped. None names a missing DLL, verifier or remote. 16 = no fingerprints for f34 and 1 = `EVOLVED_RULES_SLOW` (both acceptable per step 9); 5 = Windows-only paths (taskkill tree kill ×3, the Windows power API, a Windows rename refusal); 1 = `output/evolved_rules/gp2-best-noclean.txt` is not in the zip.
  10. `../mm-gp6-final` worktree at `gp6-final`, host built there, `--version` = f34.
  11. On mains power; system sleep, disk sleep and display sleep are already 0. `evolved_rules/power.py` keeps the machine awake on Windows only, so on macOS long runs must be wrapped in `caffeinate`. **Open:** macOS automatic update install is on (`AutomaticallyInstallMacOSUpdates=1`) and can restart the machine; turning it off needs the user (admin).
  12. UTC+02:00 (§6).

  Consequences still to handle: the PowerShell/Task Scheduler/WMI parts of §4–§5 (queue launch, `watchdog7.ps1`) need macOS equivalents before any detached run. D1 compares an arm64 Mac with the old x64 Windows machine, so it may fail; per §4 that is recorded and cross-machine numbers are then never compared.
- [x] Worker sweep, R0; D1 (pass/fail: **pass**); D2 pass; budget table committed (2026-11-14: W = 10, R0 = 477.4; D1 = L on 5100-5159 from `../mm-gp6-final` identical to the old machine's close-out games on all 60 seeds (trips, seconds, commands), `config.commit` = gp6-final; the sweep's own 100 games on 5200-5299 were also identical. D2 = 5100-5109 replayed: identical to D1 on all 10 seeds, pass)
- [x] L pre-play queue started; alive or finished? (check at every milestone and after any reboot) (2026-11-14 23:15: alive. L screen 3300-3599 done; L test 6100-6199 done; paused 19:07-23:13 so the screen ran on the whole machine, then resumed beside cma-7; still to play: L test 6200-6999, L val 1550-1749, hand test 6100-6999)
- [x] Watchdog registered and tested (2026-11-14, macOS: `watchdog7_mac.py` LaunchAgent installed; 11 unit tests pass; end-to-end under launchd: a queue job started from `../mm-gp6-final` with `PYTHONHASHSEED=0` and `~/.dotnet/dotnet`, finished, and was not restarted on the next pass; runs7.json then reset to `[]`)
- [x] C4-min + decision logging; identity tests (1), (3), edge-cost unit, text round trip: pass (2026-11-14, `4453544`: (1) and (3) 20/20 identical on 5100-5119, 0 rejected draws; `tests/test_gp7.py` 38 pass)
- [x] x0 calibration (pair-open **9.8%**, evo-built **3.0%**) (3 rounds × 8 games on 5300-5323: b_t −0.5 / −0.54 / −0.5667, is_evo weight 0; pooled 9.6% / 3.1%; θ = 0 s, Bypass c = 0.266; `output/evolved_rules/gp7/calibration/calibration_final.json`)
- [x] Screen done (n_s **300**); x0\* = **Fast** (as screened, lights off); scales and θ frozen (2026-11-14 23:06; eligible route points Fast and Bypass; scales from 233,029 logged decisions; θ = 0 s; space hash `fc79267c218669ba`, x0\* text hash `7bf3469481eb3fb9`. Bug gate: 1 rejected draw in 1,500 screen games (Fast, seed 3332), checked in about 40 min: a house spawned on a route between two of its draw commands (shared executor, also L's), no code change; `plans/gp7-launch/bug-check.md`)
- [x] linear.py identity (4), evolve7, stats7, smoke: pass (or F2 at CL2a) (2026-11-14: (4) 20/20 identical with unit scales, to repeat with the frozen scales; smoke λ 6, m 6, forced cuts, cap 300 s: killed in a 4-map phase and in a phase B, both resumed by the watchdog, 3 generations identical, mean and sigma equal)
- [x] Pre-registration committed (hash `6b80889`, tag `cma7-launch`; identity gate (4) with the frozen space: 20/20 identical, 0 rejected draws, run on a clean worktree of `fa7010c` = gp7-v1)
- [x] cma-7 trunk launched from worktree `cma7-launch` (time **2026-11-14 23:10**, W **10**, λ/m **24/12**; `../mm-cma7`, σ0 0.3, seed 1, `--log-gen0`, stop-at 2026-11-19 01:22; config commit 6b80889, dirty false, gp7-v1)
- [x] gp-7-lite forked at gen **17** from `gp7-fork` (or dropped at CL3) (2026-11-15 17:26, well before CL3: code gp7-v2 `0000650`, worktree `../mm-gp7arm`; full suite 866 passed, 23 skipped. Fork gate on the real trunk snapshot (`trunk-gen17`): the 24 ask() draws, the 12 seeds and the mean text are byte-identical between v1 and v2 through `fork()`, and 8 trunk games replayed by v2 are identical on trips/seconds/commands with 0 rejected draws (`plans/gp7-fork/`). The trunk was stopped by SIGTERM to its process group and resumed with `--workers 5`; gp-7 started with `--fork-from` on 5 workers; both arms are under the watchdog, with 5 hosts each)
- [x] Runs stopped at T_stop (status budget; gens: cma-7 **74** (0-73), gp-7 **54** (0-53)) (2026-11-19 00:06 and 00:07, before 01:22: no further generation could finish. Ledgers 22,128 and 16,976, 23% apart)
- [x] Challenger commit and text hashes frozen (**done** 00:12, 4982e73: commit 6b80889, `final/gp7/FREEZE.md`); validation played (00:13-01:55, 3×200, 0 failed chunks); C\* = **gp-7 final** `e8b8b4cad3d5b71c` (paired mean diff vs L: x0\* +147.5, cma-7 final +329.2, gp-7 final +352.8; `final/gp7/pick7.json`; its "reason" field is decide_headline's no-test placeholder)
- [x] Test played once (n = **900**, 01:55-05:07, 0 failed chunks); result **+256.5 vs L** (one-sided paired t p = 6.4e-60, BCa 90% [232.2, 280.5]; mean 1243.2 vs L 986.7 on the same maps); headline = **gp-7 final** `e8b8b4cad3d5b71c` (`final/gp7/headline7.json`)
- [x] EXPERIMENTS.md entry (average next to best); results copied to `evolved_rules/final/gp7/`; committed (secondaries: vs hand +673.6; gp-7 vs cma-7 on validation +23.7, two-sided p 0.458, Holm over 2)
- [x] Scheduled tasks removed (2026-11-19 05:09: LaunchAgent `com.minimotorways.gp7-watchdog` unloaded and deleted, plist kept in `output/evolved_rules/ops/`; no cron; no game processes left. StrokeQ sent the champion spec and test numbers)

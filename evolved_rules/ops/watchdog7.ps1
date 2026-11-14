# gp-7 / cma-7 watchdog: keeps long evolve7 runs alive, independent of any agent session.
#
# Run every 10 minutes by the scheduled task "gp7-watchdog" (HANDOFF.md section 5). Idempotent:
# - a run whose python process is alive is left alone;
# - a run whose status.json says converged/budget/stopped is done;
# - otherwise it is (re)started from its RepoDir: with ResumeArgs once checkpoint.pkl exists, else with Args.
# At most 8 restarts per run in any 2 hours, then it holds and logs "needs a look".
# Processes are created through WMI so they belong neither to the scheduled task nor to an agent session.
# Only for runs that write status.json/checkpoint.pkl (evolve7). Batteries use their own restartable scripts.
#
# The run list is a JSON file (default: <main clone>/output/evolved_rules/ops/runs7.json, gitignored):
# [ { "Name": "cma-7", "Module": "evolved_rules.evolve7",
#     "RepoDir": "C:\\work\\mm-cma7",                      <- frozen worktree the run executes from (absolute)
#     "Dir": "output/evolved_rules/evolve7/cma-7",          <- run folder, relative to RepoDir
#     "Args": "--run cma-7 --workers 12 ...", "ResumeArgs": "--run cma-7 --resume" } ]
# The python interpreter is always the main clone's .venv (shared by all worktrees). Edit the JSON, not this script.
param(
  [string]$RunsFile = ""
)
$ErrorActionPreference = "Stop"
$Main = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Py = Join-Path $Main ".venv\Scripts\python.exe"
$OpsOut = Join-Path $Main "output\evolved_rules\ops"
New-Item -ItemType Directory -Force -Path $OpsOut | Out-Null
if (-not $RunsFile) { $RunsFile = Join-Path $OpsOut "runs7.json" }
$Log = Join-Path $OpsOut "watchdog7.log"

function Say($msg) { Add-Content -Path $Log -Value ("{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg) }

if (-not (Test-Path $RunsFile)) { Say "no runs file $RunsFile"; exit 0 }
$Runs = @(Get-Content $RunsFile -Raw | ConvertFrom-Json)

foreach ($r in $Runs) {
  $repo = if ($r.RepoDir) { $r.RepoDir } else { $Main }
  $alive = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -match [regex]::Escape($r.Module) -and
                   $_.CommandLine -match ("--run " + [regex]::Escape($r.Name) + "(\s|$)") }
  if ($alive) { continue }
  $dir = Join-Path $repo $r.Dir
  $statusFile = Join-Path $dir "status.json"
  $status = $null
  if (Test-Path $statusFile) { $status = (Get-Content $statusFile -Raw | ConvertFrom-Json).status }
  if ($status -in @("converged", "budget", "stopped")) { continue }
  $recent = @(Get-Content $Log -ErrorAction SilentlyContinue | Where-Object { $_ -match ("start " + [regex]::Escape($r.Name) + " ") } |
    Where-Object { [datetime]::ParseExact($_.Substring(0, 19), "yyyy-MM-dd HH:mm:ss", $null) -gt (Get-Date).AddHours(-2) })
  if ($recent.Count -ge 8) { Say "hold $($r.Name): 8 restarts in 2 h, status $status; needs a look"; continue }
  $resume = Test-Path (Join-Path $dir "checkpoint.pkl")
  $args_ = if ($resume) { $r.ResumeArgs } else { $r.Args }
  $out = Join-Path $OpsOut "$($r.Name).log"; $err = Join-Path $OpsOut "$($r.Name).err"
  $cmd = "cmd.exe /c `"cd /d `"$repo`" && set PYTHONHASHSEED=0&& `"$Py`" -m $($r.Module) $args_ >> `"$out`" 2>> `"$err`"`""
  $res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $repo }
  Say ("start {0} in {1} (status {2}, {3}) pid {4} rc {5}" -f $r.Name, $repo, $status, $(if ($resume) { "resume" } else { "fresh" }), $res.ProcessId, $res.ReturnValue)
}

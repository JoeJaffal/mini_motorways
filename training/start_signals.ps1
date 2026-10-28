param(
    [ValidateRange(0.01,48)][double]$Hours = 8,
    [ValidateSet(1,2,4)][int]$Workers = 4,
    [string]$RunName = '',
    [string]$Resume = '',
    [double]$PriorTemperature = 2
)
$ErrorActionPreference = 'Stop'
$signalsRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $signalsRoot
$signalsPython = Join-Path $signalsRoot '.venv/Scripts/python.exe'
$signalsDotnet = Join-Path $signalsRoot 'tmp/dotnet/dotnet.exe'
if (-not (Test-Path -LiteralPath $signalsPython)) { throw 'Training Python is missing; see training/README.md.' }
if (-not (Test-Path -LiteralPath $signalsDotnet)) { $signalsDotnet = (Get-Command dotnet -ErrorAction Stop).Source }
if (-not $RunName) { $RunName = 'signals-night-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
$signalsOutput = Join-Path 'output/training' $RunName
if (Test-Path -LiteralPath $signalsOutput) { throw 'That run folder exists; choose a new RunName.' }
& $signalsDotnet build simulation/Headless
if ($LASTEXITCODE -ne 0) { throw 'Headless build failed; training was not started.' }
$signalsArguments = @('training/train_goal.py', '--output', $signalsOutput,
    '--minutes', ($Hours*60), '--steps', '10000000', '--workers', $Workers,
    '--traffic-lights', '--validation-minutes', '30')
if ($Resume) { $signalsArguments += @('--resume', $Resume) }
else { $signalsArguments += @('--reward-scale', '.01', '--prior-temperature', $PriorTemperature) }
Write-Host "Traffic-light experiment: $Hours learner hours, $Workers workers. Initial/final evaluation adds time."
Write-Host "Output: $signalsOutput | Ctrl+C saves and stops."
& $signalsPython @signalsArguments
if ($LASTEXITCODE -ne 0) { throw "Training exited with code $LASTEXITCODE; inspect saved checkpoints/logs." }

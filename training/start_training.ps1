param(
    [int]$EpisodesPerSeed = 100,
    [double]$Minutes = 30,
    [int]$StartSeed = 1000,
    [int]$SeedCount = 100,
    [int]$Steps = 10000000,
    [ValidateSet(1,2,4)][int]$Workers = 1,
    [string]$RunName = '',
    [string]$Resume = ''
)
$ErrorActionPreference = 'Stop'
$trainingRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $trainingRoot
$trainingPython = Join-Path $trainingRoot '.venv/Scripts/python.exe'
$trainingDotnet = Join-Path $trainingRoot 'tmp/dotnet/dotnet.exe'
if (-not (Test-Path -LiteralPath $trainingDotnet)) { $trainingDotnet = (Get-Command dotnet -ErrorAction Stop).Source }
if (-not (Test-Path -LiteralPath $trainingPython)) { throw 'Create .venv and install training dependencies first; see training/README.md.' }
if (-not $RunName) { $RunName = 'seed-blocks-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
& $trainingDotnet build simulation/Headless
if ($LASTEXITCODE -ne 0) { throw 'Headless build failed; training was not started.' }
$trainingArguments = @('training/train.py', '--dotnet', $trainingDotnet,
    '--episodes-per-seed', $EpisodesPerSeed, '--minutes', $Minutes,
    '--train-seed-start', $StartSeed, '--train-seed-count', $SeedCount,
    '--steps', $Steps, '--workers', $Workers, '--output', (Join-Path 'output/training' $RunName))
if ($Resume) { $trainingArguments += @('--resume', $Resume) }
& $trainingPython @trainingArguments
if ($LASTEXITCODE -ne 0) { throw 'Training exited with an error. Inspect the output above and saved checkpoints.' }

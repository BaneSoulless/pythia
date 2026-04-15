param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$PythonVersion = "3.11"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-CommandExists {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Test-PythonVersion {
    param([string]$Version)
    & py "-$Version" -c "import sys; print(sys.version)"
    if ($LASTEXITCODE -ne 0) {
        throw "Python $Version is not available via py launcher."
    }
}

$root = (Resolve-Path $ProjectRoot).Path
Set-Location $root

$venvDir = Join-Path $root ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$vscodeDir = Join-Path $root ".vscode"
$settingsPath = Join-Path $vscodeDir "settings.json"
$envPath = Join-Path $vscodeDir ".env"
$pyrightPath = Join-Path $root "pyrightconfig.json"
$pylintrcPath = Join-Path $root ".pylintrc"
$backendSrc = Join-Path $root "backend\src"
$backendRoot = Join-Path $root "backend"

Write-Step "Checking Python launcher"
Assert-CommandExists "py"
Test-PythonVersion -Version $PythonVersion

Write-Step "Creating local .venv if missing"
if (-not (Test-Path $venvPython)) {
    & py "-$PythonVersion" -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment at $venvDir"
    }
}

Write-Step "Pinning packaging tools safely"
& $venvPython -m pip install --upgrade "pip<27" "setuptools<82" "wheel<1"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install pinned packaging tools"
}

Write-Step "Best-effort editable install"
if (Test-Path (Join-Path $root "pyproject.toml")) {
    & $venvPython -m pip install -e $root
    if ($LASTEXITCODE -ne 0) {
        throw "Editable install failed from repo root"
    }
}
elseif (Test-Path (Join-Path $backendRoot "pyproject.toml")) {
    & $venvPython -m pip install -e $backendRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Editable install failed from backend root"
    }
}
else {
    Write-Warning "No pyproject.toml found at root or backend. Skipping editable install."
}

Write-Step "Creating VS Code workspace files"
New-Item -ItemType Directory -Force -Path $vscodeDir | Out-Null

$settings = [ordered]@{
    "python.defaultInterpreterPath"       = $venvPython
    "python.analysis.extraPaths"          = @(
        $backendSrc,
        $backendRoot
    )
    "python.analysis.autoSearchPaths"     = $true
    "python.terminal.activateEnvironment" = $true
    "python.envFile"                      = $envPath
}

$settings | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsPath -Encoding UTF8

@"
PYTHONPATH=$backendSrc;$backendRoot
"@ | Set-Content -Path $envPath -Encoding ASCII

$pyright = [ordered]@{
    venvPath      = "."
    venv          = ".venv"
    include       = @(
        "backend/src",
        "backend/tests"
    )
    extraPaths    = @(
        "backend/src",
        "backend"
    )
    pythonVersion = "3.11"
}
$pyright | ConvertTo-Json -Depth 10 | Set-Content -Path $pyrightPath -Encoding UTF8

Write-Step "Patching .pylintrc"
$initHookBlock = @"
[MASTER]
init-hook=
    import os, sys
    sys.path.insert(0, os.path.join(os.getcwd(), "backend", "src"))
    sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
"@

if (-not (Test-Path $pylintrcPath)) {
    $initHookBlock | Set-Content -Path $pylintrcPath -Encoding UTF8
}
else {
    $existing = Get-Content -Path $pylintrcPath -Raw
    if ($existing -notmatch 'init-hook\s*=') {
        if ($existing -match '(?ms)^\[MASTER\]') {
            $patched = [regex]::Replace(
                $existing,
                '(?ms)^\[MASTER\]\s*',
                "[MASTER]`r`ninit-hook=`r`n    import os, sys`r`n    sys.path.insert(0, os.path.join(os.getcwd(), ""backend"", ""src""))`r`n    sys.path.insert(0, os.path.join(os.getcwd(), ""backend""))`r`n",
                1
            )
        }
        else {
            $patched = $initHookBlock + "`r`n`r`n" + $existing
        }

        Copy-Item $pylintrcPath "$pylintrcPath.bak" -Force
        $patched | Set-Content -Path $pylintrcPath -Encoding UTF8
    }
}

Write-Step "Verifying interpreter and module resolution only"

$tempDir = Join-Path $env:TEMP "pythia-python-checks"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$checks = @(
    @{
        Name = "sys_executable"
        Code = @'
import sys
print(sys.executable)
'@
    },
    @{
        Name = "pythia"
        Code = @'
import importlib.util as u
s = u.find_spec("pythia")
print("OK pythia", bool(s), s.origin if s else None)
'@
    },
    @{
        Name = "structured_logging"
        Code = @'
import importlib.util as u
s = u.find_spec("pythia.core.structured_logging")
print("OK structured_logging", bool(s), s.origin if s else None)
'@
    },
    @{
        Name = "websocket_auth"
        Code = @'
import importlib.util as u
s = u.find_spec("pythia.core.websocket_auth")
print("OK websocket_auth", bool(s), s.origin if s else None)
'@
    },
    @{
        Name = "event_store_module"
        Code = @'
import importlib.util as u
s = u.find_spec("pythia.infrastructure.persistence.event_store")
print("OK event_store_module", bool(s), s.origin if s else None)
'@
    }
)

foreach ($check in $checks) {
    $scriptPath = Join-Path $tempDir ("check_" + $check.Name + ".py")
    $check.Code | Set-Content -Path $scriptPath -Encoding UTF8

    & $venvPython $scriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Verification failed for check: $($check.Name)"
    }
}

Write-Step "Auditing default shell python"
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    Write-Host "python command resolves to: $($pythonCmd.Source)" -ForegroundColor Yellow
}
else {
    Write-Host "python command not found in current shell PATH" -ForegroundColor Yellow
}

$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pyCmd) {
    Write-Host "py launcher resolves to: $($pyCmd.Source)" -ForegroundColor Yellow
}

Write-Step "Done"
Write-Host "Interpreter: $venvPython" -ForegroundColor Green
Write-Host "Settings:    $settingsPath" -ForegroundColor Green
Write-Host "Env file:    $envPath" -ForegroundColor Green
Write-Host "Pyright:     $pyrightPath" -ForegroundColor Green
Write-Host "Pylint rc:   $pylintrcPath" -ForegroundColor Green
Write-Host ""
Write-Host "FINAL ACTION: close VS Code completely, reopen the repo, then run 'Python: Select Interpreter' and choose .venv once." -ForegroundColor Yellow
<#
.SYNOPSIS
    Sets up a local virtual environment for the giveaway tracker.

.DESCRIPTION
    Creates .venv next to this script, installs the dependencies into it, and
    writes a run-gt.bat launcher. Nothing is installed system-wide and nothing
    outside this folder is touched, so removing the folder removes everything.

.PARAMETER Desktop
    Also place a shortcut to the launcher on the desktop.

.PARAMETER Build
    Also build the portable dist\gt.exe (installs PyInstaller into the venv).

.PARAMETER Force
    Delete an existing .venv and start over.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1 -Build -Desktop
#>
[CmdletBinding()]
param(
    [switch]$Desktop,
    [switch]$Build,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

function Write-Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }
function Write-Ok($text)   { Write-Host "    $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "    $text" -ForegroundColor Yellow }

Write-Host ""
Write-Host " Giveaway Tracker - installer" -ForegroundColor Cyan
Write-Host " $root"
Write-Host ""

# --- locate a usable Python -------------------------------------------------
Write-Step "Looking for Python 3.9+"
$launcher = $null
$launcherArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $launcher = 'py'
    $launcherArgs = @('-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $launcher = 'python'
}
if (-not $launcher) {
    Write-Host "    No Python found on PATH." -ForegroundColor Red
    Write-Host "    Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH')."
    exit 1
}

$version = & $launcher @launcherArgs -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ($LASTEXITCODE -ne 0) {
    Write-Host "    Could not run Python ($launcher)." -ForegroundColor Red
    exit 1
}
$parts = $version.Trim().Split('.')
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 9)) {
    Write-Host "    Python $version is too old, 3.9 or newer is required." -ForegroundColor Red
    exit 1
}
Write-Ok "Python $version"

# --- virtual environment ----------------------------------------------------
if ($Force -and (Test-Path $venv)) {
    Write-Step "Removing the existing .venv (-Force)"
    Remove-Item -Recurse -Force $venv
}

if (Test-Path $venvPython) {
    Write-Step "Reusing the existing virtual environment"
} else {
    Write-Step "Creating the virtual environment in .venv"
    & $launcher @launcherArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    venv creation failed." -ForegroundColor Red
        exit 1
    }
}
Write-Ok $venvPython

# --- dependencies -----------------------------------------------------------
Write-Step "Installing dependencies"
$reqFile = 'requirements.txt'
if ($Build) { $reqFile = 'requirements-build.txt' }
& $venvPython -m pip install --upgrade pip --quiet --disable-pip-version-check
& $venvPython -m pip install -r (Join-Path $root $reqFile) --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
    Write-Host "    Dependency installation failed." -ForegroundColor Red
    exit 1
}
Write-Ok "Installed from $reqFile"

# --- launcher ---------------------------------------------------------------
Write-Step "Writing run-gt.bat"
$launcherBat = @'
@echo off
rem Starts the giveaway tracker from the local virtual environment.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment missing. Run install.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "gt.py" %*
if errorlevel 1 pause
'@
$launcherPath = Join-Path $root 'run-gt.bat'
Set-Content -Path $launcherPath -Value $launcherBat -Encoding ascii
Write-Ok $launcherPath

# --- optional desktop shortcut ---------------------------------------------
if ($Desktop) {
    Write-Step "Creating a desktop shortcut"
    try {
        $shell = New-Object -ComObject WScript.Shell
        $link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Giveaway Tracker.lnk'))
        $link.TargetPath = $launcherPath
        $link.WorkingDirectory = $root
        $link.Description = 'War Thunder giveaway tracker'
        $link.Save()
        Write-Ok "Giveaway Tracker.lnk"
    } catch {
        Write-Warn "Could not create the shortcut: $($_.Exception.Message)"
    }
}

# --- optional portable build ------------------------------------------------
if ($Build) {
    Write-Step "Building the portable executable"
    & (Join-Path $root 'build.ps1')
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "The portable build failed, but the local install is fine."
    }
}

Write-Host ""
Write-Host " Done." -ForegroundColor Green
Write-Host " Start it with:  run-gt.bat"
Write-Host " Player lists are written to the textfiles folder."
Write-Host " Global hotkeys may need an elevated console on some systems."
Write-Host ""

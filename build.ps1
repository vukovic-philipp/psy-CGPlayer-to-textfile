<#
.SYNOPSIS
    Builds the portable dist\gt.exe with PyInstaller.

.DESCRIPTION
    Uses the local .venv when it exists (run install.ps1 first), otherwise falls
    back to the Python on PATH. PyInstaller is installed into whichever
    interpreter is used. The resulting gt.exe is self-contained and writes its
    textfiles folder next to itself, so it can be copied anywhere.

.PARAMETER Clean
    Remove build\ and dist\ before building.
#>
[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

function Write-Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }

if (Test-Path $venvPython) {
    $python = $venvPython
    Write-Step "Building with the local virtual environment"
} else {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        Write-Host "No Python found. Run install.bat first." -ForegroundColor Red
        exit 1
    }
    Write-Step "No .venv found, building with the Python on PATH"
}

Write-Step "Ensuring PyInstaller is available"
& $python -m pip install -r (Join-Path $root 'requirements-build.txt') --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not install the build dependencies." -ForegroundColor Red
    exit 1
}

if ($Clean) {
    Write-Step "Cleaning build and dist"
    foreach ($dir in @('build', 'dist')) {
        $path = Join-Path $root $dir
        if (Test-Path $path) { Remove-Item -Recurse -Force $path }
    }
}

Write-Step "Running PyInstaller"
Push-Location $root
try {
    & $python -m PyInstaller 'gt.spec' --noconfirm
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

$exe = Join-Path $root 'dist\gt.exe'
if ($code -ne 0 -or -not (Test-Path $exe)) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host " Portable build ready: $exe" -ForegroundColor Green
Write-Host " Copy it anywhere; it creates its own textfiles folder alongside itself."
Write-Host ""

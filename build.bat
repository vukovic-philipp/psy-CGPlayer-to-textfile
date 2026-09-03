@echo off
rem Builds the portable dist\gt.exe. Arguments are passed through,
rem e.g.  build.bat --clean
setlocal
cd /d "%~dp0"

rem Prefer the project virtual environment when install.bat has been run.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "build.py" %*
    goto :done
)

call :findpython
if not defined PYTHON goto :nopython
%PYTHON% "build.py" %*

:done
if errorlevel 1 (
    echo.
    echo Build failed.
)
pause
exit /b

:findpython
set "PYTHON="
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    exit /b
)
python --version >nul 2>&1
if not errorlevel 1 set "PYTHON=python"
exit /b

:nopython
echo.
echo No Python installation was found.
echo Install Python 3.9 or newer from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during setup, then run this again.
echo.
pause
exit /b 1

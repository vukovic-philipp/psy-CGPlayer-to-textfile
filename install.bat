@echo off
rem Double-click entry point for the installer. Any arguments are passed on,
rem e.g.  install.bat -Build -Desktop
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
pause

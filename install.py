"""Installer for the giveaway tracker.

Creates a virtual environment next to this file, installs the dependencies
into it and writes a launcher. Nothing is installed system-wide and nothing
outside this folder is touched, so deleting the folder removes everything.

Normally started through install.bat, but it can be run directly:

    python install.py [--build] [--desktop] [--force]

Uses only the standard library so it runs on a bare Python install.
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, '.venv')
MIN_PYTHON = (3, 9)

LAUNCHER_BAT = """@echo off
rem Starts the giveaway tracker from the local virtual environment.
cd /d "%~dp0"
if not exist ".venv\\Scripts\\python.exe" (
    echo Virtual environment missing. Run install.bat first.
    pause
    exit /b 1
)
".venv\\Scripts\\python.exe" "gt.py" %*
if errorlevel 1 pause
"""

LAUNCHER_SH = """#!/bin/sh
# Starts the giveaway tracker from the local virtual environment.
cd "$(dirname "$0")" || exit 1
if [ ! -x ".venv/bin/python" ]; then
    echo "Virtual environment missing. Run 'python3 install.py' first."
    exit 1
fi
exec ".venv/bin/python" "gt.py" "$@"
"""


def step(text):
    print(f"==> {text}")


def ok(text):
    print(f"    {text}")


def fail(text):
    print(f"    {text}", file=sys.stderr)
    sys.exit(1)


def venv_python():
    """Path to the interpreter inside the virtual environment."""
    if os.name == 'nt':
        return os.path.join(VENV, 'Scripts', 'python.exe')
    return os.path.join(VENV, 'bin', 'python')


def run(args, what):
    result = subprocess.run(args)
    if result.returncode != 0:
        fail(f"{what} failed (exit code {result.returncode}).")


def create_venv(force):
    if force and os.path.isdir(VENV):
        step("Removing the existing .venv (--force)")
        shutil.rmtree(VENV)

    if os.path.exists(venv_python()):
        step("Reusing the existing virtual environment")
    else:
        step("Creating the virtual environment in .venv")
        run([sys.executable, '-m', 'venv', VENV], "Creating the virtual environment")
    ok(venv_python())


def install_dependencies(build):
    step("Installing dependencies")
    requirements = 'requirements-build.txt' if build else 'requirements.txt'
    python = venv_python()
    subprocess.run([python, '-m', 'pip', 'install', '--upgrade', 'pip',
                    '--quiet', '--disable-pip-version-check'])
    run([python, '-m', 'pip', 'install', '-r', os.path.join(ROOT, requirements),
         '--disable-pip-version-check'], "Dependency installation")
    ok(f"installed from {requirements}")


def write_launcher():
    step("Writing the launcher")
    if os.name == 'nt':
        path = os.path.join(ROOT, 'run-gt.bat')
        with open(path, 'w', encoding='ascii', newline='\r\n') as f:
            f.write(LAUNCHER_BAT)
    else:
        path = os.path.join(ROOT, 'run-gt.sh')
        with open(path, 'w', encoding='ascii', newline='\n') as f:
            f.write(LAUNCHER_SH)
        os.chmod(path, 0o755)
    ok(path)
    return path


def make_desktop_entry(launcher):
    """Drop a small forwarding script on the desktop.

    A plain script is used instead of a .lnk shortcut so that no COM or
    PowerShell call is needed.
    """
    step("Creating the desktop entry")
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    if not os.path.isdir(desktop):
        print("    No Desktop folder found, skipping.")
        return
    try:
        if os.name == 'nt':
            path = os.path.join(desktop, 'Giveaway Tracker.bat')
            with open(path, 'w', encoding='ascii', newline='\r\n') as f:
                f.write('@echo off\r\ncall "%s"\r\n' % launcher)
        else:
            path = os.path.join(desktop, 'giveaway-tracker.sh')
            with open(path, 'w', encoding='ascii', newline='\n') as f:
                f.write('#!/bin/sh\nexec "%s" "$@"\n' % launcher)
            os.chmod(path, 0o755)
    except OSError as exc:
        print(f"    Could not create the desktop entry: {exc}")
        return
    ok(path)


def main():
    parser = argparse.ArgumentParser(description="Set up the giveaway tracker locally.")
    parser.add_argument('--build', action='store_true',
                        help="also build the portable executable")
    parser.add_argument('--desktop', action='store_true',
                        help="also place a launcher on the desktop")
    parser.add_argument('--force', action='store_true',
                        help="delete an existing .venv and start over")
    args = parser.parse_args()

    print()
    print(" Giveaway Tracker - installer")
    print(f" {ROOT}")
    print()

    if sys.version_info < MIN_PYTHON:
        fail("Python %d.%d or newer is required, this is %d.%d."
             % (MIN_PYTHON + sys.version_info[:2]))
    step(f"Using Python {sys.version_info.major}.{sys.version_info.minor}")
    ok(sys.executable)

    create_venv(args.force)
    install_dependencies(args.build)
    launcher = write_launcher()

    if args.desktop:
        make_desktop_entry(launcher)

    if args.build:
        step("Building the portable executable")
        import build  # local module, imported here so a build is opt-in
        if not build.build():
            print("    The portable build failed, but the local install is fine.")

    print()
    print(" Done.")
    print(f" Start it with:  {os.path.basename(launcher)}")
    print(" Player lists are written to the textfiles folder.")
    if os.name == 'nt':
        print(" Global hotkeys may need an elevated console on some systems.")
    print()


if __name__ == '__main__':
    main()

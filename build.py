"""Builds the portable dist/gt.exe with PyInstaller.

Uses the local .venv when it exists (run install.py first), otherwise the
Python that is running this script. PyInstaller is installed into whichever
interpreter is used. The resulting executable is self-contained and writes its
textfiles folder next to itself, so it can be copied anywhere.

Normally started through build.bat, but it can be run directly:

    python build.py [--clean]
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def step(text):
    print(f"==> {text}")


def build_python():
    """The interpreter to build with: the project venv when it exists."""
    if os.name == 'nt':
        candidate = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
    else:
        candidate = os.path.join(ROOT, '.venv', 'bin', 'python')
    if os.path.exists(candidate):
        step("Building with the local virtual environment")
        return candidate
    step("No .venv found, building with the current Python")
    return sys.executable


def exe_path():
    name = 'gt.exe' if os.name == 'nt' else 'gt'
    return os.path.join(ROOT, 'dist', name)


def build(clean=False):
    """Run PyInstaller. Returns True when the executable was produced."""
    python = build_python()

    step("Ensuring PyInstaller is available")
    result = subprocess.run([python, '-m', 'pip', 'install', '-r',
                             os.path.join(ROOT, 'requirements-build.txt'),
                             '--quiet', '--disable-pip-version-check'])
    if result.returncode != 0:
        print("    Could not install the build dependencies.", file=sys.stderr)
        return False

    if clean:
        step("Cleaning build and dist")
        for name in ('build', 'dist'):
            path = os.path.join(ROOT, name)
            if os.path.isdir(path):
                shutil.rmtree(path)

    step("Running PyInstaller")
    result = subprocess.run([python, '-m', 'PyInstaller', 'gt.spec', '--noconfirm'],
                            cwd=ROOT)
    if result.returncode != 0 or not os.path.exists(exe_path()):
        print("    Build failed.", file=sys.stderr)
        return False

    print()
    print(f" Portable build ready: {exe_path()}")
    print(" Copy it anywhere; it creates its own textfiles folder alongside itself.")
    print()
    return True


def main():
    parser = argparse.ArgumentParser(description="Build the portable executable.")
    parser.add_argument('--clean', action='store_true',
                        help="remove build/ and dist/ before building")
    args = parser.parse_args()
    sys.exit(0 if build(args.clean) else 1)


if __name__ == '__main__':
    main()

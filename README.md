Script to make the Players list from WT custom games to a .txt file.

Reads player names live from War Thunder's localhost telemetry API
(`http://localhost:8111`, see the
[WarThunder-localhost-documentation](https://github.com/lucasvmx/WarThunder-localhost-documentation))
instead of screenshots/OCR/AI. War Thunder does not expose a full match
roster over this API, so names are collected from the kill-feed
(`/hudmsg`) and game chat (`/gamechat`) while a match is being tracked.

## Install

Double-click `install.bat`, or from a terminal:

```bash
powershell -ExecutionPolicy Bypass -File install.ps1
```

This creates a `.venv` folder next to the script, installs `keyboard` and
`requests` into it, and writes a `run-gt.bat` launcher. Nothing is installed
system-wide — deleting the project folder removes everything.

Options (combine as needed):

- `-Desktop` — also put a "Giveaway Tracker" shortcut on the desktop
- `-Build` — also build the portable `dist\gt.exe`
- `-Force` — delete and recreate an existing `.venv`

```bash
powershell -ExecutionPolicy Bypass -File install.ps1 -Build -Desktop
```

## Portable executable

The standalone build is still supported and is produced by `build.ps1`:

```bash
powershell -ExecutionPolicy Bypass -File build.ps1 -Clean
```

It uses the local `.venv` when one exists and otherwise the Python on `PATH`.
The result is `dist\gt.exe`, which needs no Python installation and writes its
`textfiles` folder next to itself, so the exe can be copied anywhere.

## Usage

Start it with `run-gt.bat` (or `dist\gt.exe`, or `python gt.py`) while War
Thunder is running. A live terminal view shows:

- whether a tracking session is **active** or **idle**, and how long it has run
- whether the War Thunder API is reachable and if you are in a match or the hangar
- every player name detected so far
- the analysis files already saved, with their player counts and timestamps

Hotkeys work globally, so they still fire while War Thunder has focus:

- `Alt+Ctrl+1` — start tracking a match (clears the previous player list)
- `Alt+Ctrl+2` — stop tracking and save the collected players to `textfiles/analysis_N.txt`
- `Alt+Ctrl+4` — open the `textfiles` folder
- `Alt+Ctrl+Esc` — exit (an active session is saved on the way out)

If the footer reports that hotkeys are unavailable, start the program from an
elevated console — the `keyboard` library needs those rights on some systems.

Everything runs locally; no external API keys or internet access are required.

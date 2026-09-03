Script to make the Players list from WT custom games to a .txt file.

Reads player names live from War Thunder's localhost telemetry API
(`http://localhost:8111`, see the
[WarThunder-localhost-documentation](https://github.com/lucasvmx/WarThunder-localhost-documentation))
instead of screenshots/OCR/AI. War Thunder does not expose a full match
roster over this API, so names are collected from the kill-feed
(`/hudmsg`) and game chat (`/gamechat`) while a match is being tracked.

## Install

Double-click `install.bat`. It finds your Python, creates a `.venv` folder next
to the script, installs `keyboard` and `requests` into it, and writes a
`run-gt.bat` launcher. Nothing is installed system-wide — deleting the project
folder removes everything.

Options (combine as needed):

- `--desktop` — also place a launcher on the desktop
- `--build` — also build the portable `dist\gt.exe`
- `--force` — delete and recreate an existing `.venv`

```bash
install.bat --build --desktop
```

The installer is plain Python, so no scripts need to be enabled and it also
works on Linux/macOS:

```bash
python3 install.py
```

## Portable executable

The standalone build is still supported. Double-click `build.bat`, or:

```bash
build.bat --clean
```

It uses the local `.venv` when one exists and otherwise the Python on `PATH`,
installing PyInstaller as needed. The result is `dist\gt.exe`, which needs no
Python installation and writes its `textfiles` folder next to itself, so the exe
can be copied anywhere.

## Usage

Start it with `run-gt.bat` (or `dist\gt.exe`, or `python gt.py`) while War
Thunder is running. A live terminal view shows:

- whether a tracking session is **active** or **idle**, and how long it has run
- whether the War Thunder API is reachable and if you are in a match or the hangar
- every player name detected so far
- the analysis files already saved, with their player counts and timestamps
- the raffle entry list, once you have built one

Hotkeys work globally, so they still fire while War Thunder has focus:

- `Alt+Ctrl+1` — start tracking a match (clears the previous player list)
- `Alt+Ctrl+2` — stop tracking and save the collected players to `textfiles/analysis_N.txt`
- `Alt+Ctrl+3` — build the weighted raffle entry list from every saved match
- `Alt+Ctrl+4` — open the `textfiles` folder
- `Alt+Ctrl+Esc` — exit (an active session is saved on the way out)

## Raffle entries

`Alt+Ctrl+3` reads every `textfiles/analysis_*.txt`, counts how many matches
each player attended, and gives them `count - 2` entries in the draw:

| Matches attended | Entries |
|---|---|
| 1 | none |
| 2 | none |
| 3 | 1 |
| 4 | 2 |
| 5 | 3 |

The result is written to `textfiles/raffle_entries.txt` with each name repeated
once per entry, one per line, ready to paste into any random picker. The TUI
shows the top of that list with each player's match count. Names are matched
case-insensitively and only count once per match file, so the number really is
"games attended". Run it again at any time to rebuild it from the current files.

If the footer reports that hotkeys are unavailable, start the program from an
elevated console — the `keyboard` library needs those rights on some systems.

Everything runs locally; no external API keys or internet access are required.

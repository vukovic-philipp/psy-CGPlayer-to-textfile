Script to make the Players list from WT custom games to a .txt file.

Reads player names live from War Thunder's localhost telemetry API
(`http://localhost:8111`, see the
[WarThunder-localhost-documentation](https://github.com/lucasvmx/WarThunder-localhost-documentation))
instead of screenshots/OCR/AI. War Thunder does not expose a full match
roster over this API, so names are collected from the kill-feed
(`/hudmsg`) and game chat (`/gamechat`) while a match is being tracked.

## Usage

Run `gt.py` (or `gt.exe`) while War Thunder is running, then use these hotkeys:

- `Alt+Ctrl+1` — start tracking a match (clears the previous player list)
- `Alt+Ctrl+2` — stop tracking and save the collected players to `textfiles/analysis_N.txt`
- `Alt+Ctrl+3` — print the currently collected player list without stopping
- `Alt+Ctrl+Esc` — exit the program

Everything runs locally; no external API keys or internet access are required.
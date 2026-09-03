"""Giveaway tracker - collects War Thunder player names from the localhost API.

Runs a small terminal UI that shows whether a match is being tracked, which
player names have been detected so far, and which analysis files have been
saved. Everything is driven by global hotkeys so it keeps working while War
Thunder has focus.
"""

#import stuff
import glob
import os
import re
import shutil
import sys
import threading
import time
from datetime import datetime

import keyboard  # type: ignore
import requests  # type: ignore

#variables and setup
WT_HOST = "http://localhost:8111"
POLL_INTERVAL = 2  # seconds between polls of the WT localhost API
REQUEST_TIMEOUT = 2  # seconds
UI_INTERVAL = 0.25  # seconds between TUI redraws
MAX_MESSAGES = 5  # recent status lines kept in the log pane


def base_dir():
    """Directory the app writes to: next to the .exe when frozen, else the script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


TEXTFILES_DIR = os.path.join(base_dir(), 'textfiles')
os.makedirs(TEXTFILES_DIR, exist_ok=True)

tracking = False
tracking_lock = threading.Lock()
poll_thread = None
players = set()
last_evt_id = 0
last_dmg_id = 0
last_chat_id = 0

running = True
track_started_at = None
last_saved_file = None
api_online = False
in_match = False
messages = []
hotkeys_ok = True

# Matches "Name (Vehicle)" style tokens found in hudmsg/gamechat text,
# which is the only place War Thunder's localhost API exposes player names.
NAME_TOKEN_RE = re.compile(r'\*?([A-Za-z0-9_\-\.\[\]=]{2,})\s*\(')
CLAN_TAG_RE = re.compile(r'^(=[^=]+=|\[[^\]]+\])')


def log(text):
    """Record a status line for the message pane of the TUI."""
    messages.append(f"{datetime.now():%H:%M:%S}  {text}")
    del messages[:-MAX_MESSAGES]


def clean_name(raw_name):
    name = raw_name.strip().lstrip('*')
    name = CLAN_TAG_RE.sub('', name).strip()
    return name


def extract_names(text):
    if not text:
        return []
    found = []
    for match in NAME_TOKEN_RE.findall(text):
        name = clean_name(match)
        if name:
            found.append(name)
    return found


def fetch_json(path, params=None):
    global api_online
    try:
        response = requests.get(f"{WT_HOST}{path}", params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        api_online = False
        return None
    api_online = True
    return data


def poll_once():
    """Poll hudmsg and gamechat once, adding any newly seen player names."""
    global last_evt_id, last_dmg_id, last_chat_id, in_match

    indicators = fetch_json("/indicators")
    in_match = bool(indicators.get("valid")) if indicators else False

    hudmsg = fetch_json("/hudmsg", {"lastEvt": last_evt_id, "lastDmg": last_dmg_id})
    if hudmsg:
        for dmg in hudmsg.get("damage", []):
            players.update(extract_names(dmg.get("msg", "")))
            last_dmg_id = max(last_dmg_id, dmg.get("id", last_dmg_id))
        for evt in hudmsg.get("events", []):
            players.update(extract_names(evt.get("msg", "")))
            last_evt_id = max(last_evt_id, evt.get("id", last_evt_id))

    gamechat = fetch_json("/gamechat", {"lastId": last_chat_id})
    if gamechat:
        for msg in gamechat:
            sender = clean_name(msg.get("sender", ""))
            if sender:
                players.add(sender)
            last_chat_id = max(last_chat_id, msg.get("id", last_chat_id))


def poll_loop():
    while True:
        with tracking_lock:
            if not tracking:
                return
        poll_once()
        time.sleep(POLL_INTERVAL)


def start_tracking():
    global tracking, poll_thread, players, last_evt_id, last_dmg_id, last_chat_id
    global track_started_at, last_saved_file
    with tracking_lock:
        if tracking:
            log("Session already active.")
            return
        tracking = True
        players = set()
        last_evt_id = 0
        last_dmg_id = 0
        last_chat_id = 0
    track_started_at = time.time()
    last_saved_file = None
    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()
    log("Session started - collecting player names.")


def next_analysis_number():
    existing = glob.glob(os.path.join(TEXTFILES_DIR, 'analysis_*.txt'))
    numbers = []
    for path in existing:
        match = re.search(r'analysis_(\d+)\.txt$', path)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def stop_tracking():
    global tracking, track_started_at, last_saved_file, in_match
    with tracking_lock:
        if not tracking:
            log("No session is active.")
            return
        tracking = False

    if poll_thread:
        poll_thread.join(timeout=REQUEST_TIMEOUT + 1)
    track_started_at = None
    in_match = False

    if not players:
        log("Session stopped - no players recorded, nothing saved.")
        return

    analysis_number = next_analysis_number()
    analysis_filepath = os.path.join(TEXTFILES_DIR, f"analysis_{analysis_number}.txt")
    with open(analysis_filepath, 'w', encoding='utf-8') as f:
        for name in sorted(players, key=str.lower):
            f.write(f"{name}\n")

    last_saved_file = analysis_filepath
    log(f"Saved {len(players)} players to analysis_{analysis_number}.txt")


def open_textfiles():
    """Open the output folder in the system file browser."""
    try:
        if sys.platform == 'win32':
            os.startfile(TEXTFILES_DIR)  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            os.system(f'open "{TEXTFILES_DIR}"')
        else:
            os.system(f'xdg-open "{TEXTFILES_DIR}"')
        log("Opened the textfiles folder.")
    except OSError as exc:
        log(f"Could not open folder: {exc}")


def exit_program():
    """Ask the main loop to shut down; it saves any active session on the way out."""
    global running
    running = False


#saved file listing
def saved_files(limit=6):
    """Most recently modified analysis files, newest first."""
    entries = []
    for path in glob.glob(os.path.join(TEXTFILES_DIR, 'analysis_*.txt')):
        try:
            stat = os.stat(path)
            with open(path, encoding='utf-8') as f:
                count = sum(1 for line in f if line.strip())
        except OSError:
            continue
        entries.append((stat.st_mtime, os.path.basename(path), count))
    entries.sort(reverse=True)
    return entries[:limit], len(entries)


#terminal rendering
RESET = '\x1b[0m'
BOLD = '\x1b[1m'
DIM = '\x1b[2m'
GREEN = '\x1b[32m'
RED = '\x1b[31m'
YELLOW = '\x1b[33m'
CYAN = '\x1b[36m'
GREY = '\x1b[90m'
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def enable_ansi():
    """Turn on virtual terminal processing so escape codes work in cmd.exe."""
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


COLOR = enable_ansi() and not os.environ.get('NO_COLOR')


def c(text, *codes):
    if not COLOR:
        return text
    return ''.join(codes) + text + RESET


def visible_len(text):
    return len(ANSI_RE.sub('', text))


def clip(text, width):
    """Trim a possibly coloured line so its visible length fits the terminal."""
    if visible_len(text) <= width:
        return text
    out = []
    shown = 0
    index = 0
    while index < len(text) and shown < width:
        match = ANSI_RE.match(text, index)
        if match:
            out.append(match.group())
            index = match.end()
            continue
        out.append(text[index])
        shown += 1
        index += 1
    out.append(RESET if COLOR else '')
    return ''.join(out)


def rule(width, title=''):
    if not title:
        return c('-' * width, GREY)
    head = f"-- {title} "
    return c(head + '-' * max(0, width - len(head)), GREY)


def elapsed_text(start):
    if not start:
        return "--:--"
    seconds = int(time.time() - start)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def name_columns(names, width, max_lines):
    """Lay the player names out in as many columns as the terminal allows."""
    if not names:
        return [c("  (no names detected yet)", DIM)]
    col_width = min(max(len(n) for n in names) + 3, max(16, width - 4))
    columns = max(1, (width - 2) // col_width)
    shown = names
    truncated = 0
    if len(names) > columns * max_lines:
        shown = names[:columns * max_lines]
        truncated = len(names) - len(shown)
    rows = -(-len(shown) // columns)
    lines = []
    for row in range(rows):
        cells = []
        for col in range(columns):
            index = col * rows + row
            if index < len(shown):
                cells.append(shown[index].ljust(col_width))
        lines.append('  ' + ''.join(cells).rstrip())
    if truncated:
        lines.append(c(f"  ... and {truncated} more (all of them go into the saved file)", DIM))
    return lines


def build_frame(width, height):
    with tracking_lock:
        is_tracking = tracking
    names = sorted(players, key=str.lower)
    files, total_files = saved_files()

    lines = []
    lines.append(c(" GIVEAWAY TRACKER ", BOLD, CYAN) + c(f" {WT_HOST}", DIM))
    lines.append(rule(width))

    if is_tracking:
        session = c("[ACTIVE]", BOLD, GREEN) + c(f"  running for {elapsed_text(track_started_at)}", DIM)
    else:
        session = c("[IDLE]", BOLD, GREY) + c("  press Alt+Ctrl+1 to start", DIM)
    lines.append("  Session:      " + session)

    if not is_tracking:
        api = c("not polling", GREY)
    elif not api_online:
        api = c("unreachable - is War Thunder running?", RED)
    elif in_match:
        api = c("connected - in match", GREEN)
    else:
        api = c("connected - hangar / menu", YELLOW)
    lines.append("  War Thunder:  " + api)
    lines.append("  Players:      " + c(str(len(names)) + " detected", BOLD))
    lines.append("")

    # Everything except the player list has a fixed height; give it the rest.
    fixed = 14 + max(1, len(files))
    lines.append(rule(width, f"DETECTED PLAYERS ({len(names)})"))
    lines.extend(name_columns(names, width, max(2, height - fixed)))
    lines.append("")

    lines.append(rule(width, f"SAVED FILES ({total_files})"))
    if not files:
        lines.append(c("  (nothing saved yet)", DIM))
    for mtime, name, count in files:
        stamp = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        latest = last_saved_file and os.path.basename(last_saved_file) == name
        marker = c('  <- just saved', GREEN) if latest else ''
        lines.append(f"  {name.ljust(20)}{c(str(count).rjust(4) + ' players', DIM)}   {c(stamp, GREY)}{marker}")
    lines.append(c(f"  folder: {TEXTFILES_DIR}", DIM))
    lines.append("")

    lines.append(rule(width, "LOG"))
    if not messages:
        lines.append(c("  (no activity yet)", DIM))
    for message in messages[-MAX_MESSAGES:]:
        lines.append("  " + c(message, DIM))
    lines.append("")

    lines.append(rule(width))
    if hotkeys_ok:
        lines.append("  " + c("Alt+Ctrl+1", BOLD) + " start    "
                     + c("Alt+Ctrl+2", BOLD) + " stop & save    "
                     + c("Alt+Ctrl+4", BOLD) + " open folder    "
                     + c("Alt+Ctrl+Esc", BOLD) + " quit")
    else:
        lines.append("  " + c("Hotkeys unavailable - try running as administrator.", RED))
    return lines


def render():
    size = shutil.get_terminal_size((100, 30))
    width = max(60, size.columns - 1)
    out = ['\x1b[H']
    for line in build_frame(width, size.lines):
        out.append(clip(line, width))
        out.append('\x1b[K\n')
    out.append('\x1b[J')
    sys.stdout.write(''.join(out))
    sys.stdout.flush()


def register_hotkeys():
    global hotkeys_ok
    try:
        keyboard.add_hotkey('alt+ctrl+1', start_tracking)
        keyboard.add_hotkey('alt+ctrl+2', stop_tracking)
        keyboard.add_hotkey('alt+ctrl+4', open_textfiles)
        keyboard.add_hotkey('alt+ctrl+esc', exit_program)
    except Exception as exc:  # keyboard needs elevated rights on some systems
        hotkeys_ok = False
        log(f"Hotkey setup failed: {exc}")


#main loop and listener
def main():
    register_hotkeys()
    log("Ready. Press Alt+Ctrl+1 to start a session.")
    sys.stdout.write('\x1b[2J\x1b[?25l')  # clear screen, hide cursor
    try:
        while running:
            render()
            time.sleep(UI_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        with tracking_lock:
            active = tracking
        if active:
            stop_tracking()
        sys.stdout.write('\x1b[?25h\n')  # show the cursor again
        sys.stdout.flush()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        if last_saved_file:
            print(f"Saved: {last_saved_file}")
        print("Exited.")


if __name__ == '__main__':
    main()

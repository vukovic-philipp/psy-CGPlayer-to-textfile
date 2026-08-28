#import stuff
import keyboard  # type: ignore
import time
import glob
import os
import re
import sys
import threading
import requests  # type: ignore

#variables and setup
WT_HOST = "http://localhost:8111"
POLL_INTERVAL = 2  # seconds between polls of the WT localhost API
REQUEST_TIMEOUT = 2  # seconds

os.makedirs('textfiles', exist_ok=True)

tracking = False
tracking_lock = threading.Lock()
poll_thread = None
players = set()
last_evt_id = 0
last_dmg_id = 0
last_chat_id = 0

# Matches "Name (Vehicle)" style tokens found in hudmsg/gamechat text,
# which is the only place War Thunder's localhost API exposes player names.
NAME_TOKEN_RE = re.compile(r'\*?([A-Za-z0-9_\-\.\[\]=]{2,})\s*\(')
CLAN_TAG_RE = re.compile(r'^(=[^=]+=|\[[^\]]+\])')


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
    try:
        response = requests.get(f"{WT_HOST}{path}", params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def poll_once():
    """Poll hudmsg and gamechat once, adding any newly seen player names."""
    global last_evt_id, last_dmg_id, last_chat_id

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
    with tracking_lock:
        if tracking:
            print("Match tracking is already running.")
            return
        tracking = True
        players = set()
        last_evt_id = 0
        last_dmg_id = 0
        last_chat_id = 0
    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()
    print("Match tracking started. Make sure War Thunder is running with 'Show player HUD msgs' enabled.")


def next_analysis_number():
    existing = glob.glob(os.path.join('textfiles', 'analysis_*.txt'))
    numbers = []
    for path in existing:
        match = re.search(r'analysis_(\d+)\.txt$', path)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def stop_tracking():
    global tracking
    with tracking_lock:
        if not tracking:
            print("Match tracking is not running.")
            return
        tracking = False

    if poll_thread:
        poll_thread.join(timeout=REQUEST_TIMEOUT + 1)

    if not players:
        print("No players were recorded for this match.")
        return

    analysis_number = next_analysis_number()
    analysis_filepath = os.path.join('textfiles', f"analysis_{analysis_number}.txt")
    with open(analysis_filepath, 'w', encoding='utf-8') as f:
        for name in sorted(players, key=str.lower):
            f.write(f"{name}\n")

    print(f"Match ended. {len(players)} players saved to: {analysis_filepath}")


def show_current():
    with tracking_lock:
        is_tracking = tracking
    if not is_tracking:
        print("Match tracking is not running.")
        return
    if not players:
        print("No players recorded yet.")
        return
    print("=" * 40)
    for name in sorted(players, key=str.lower):
        print(name)
    print("=" * 40)


def exit_program():
    print("Exiting...")
    global tracking
    with tracking_lock:
        tracking = False
    keyboard.unhook_all()
    sys.exit()


#main loop and listener
keyboard.add_hotkey('alt+ctrl+1', start_tracking)
keyboard.add_hotkey('alt+ctrl+2', stop_tracking)
keyboard.add_hotkey('alt+ctrl+3', show_current)
keyboard.add_hotkey('alt+ctrl+esc', exit_program)

try:
    print("Giveaway tracker running.")
    print("Alt+Ctrl+1: start tracking a match  |  Alt+Ctrl+2: stop and save  |  Alt+Ctrl+3: show current list  |  Alt+Ctrl+Esc: exit")
    print(f"Player names are read from the War Thunder localhost API at {WT_HOST} (no screenshots, no AI).")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Program interrupted by user.")
    exit_program()

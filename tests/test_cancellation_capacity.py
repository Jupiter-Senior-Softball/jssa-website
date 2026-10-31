"""The main Gmail account only has ~100 sends a day, and each message also
spends one on the sender's own copy. These checks cover: filling the main
account only as far as it can really go, sending the rest from the backup,
handing people to the backup when the main account refuses, and ignoring a
backup address that is not a real web address."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()

def team(n, c):
    return {"team": n, "division": "RED", "manager": n + " Mgr",
            "players": [{"name": "%s P%03d" % (n, i)} for i in range(c)]
                       + [{"name": n + " Mgr"}]}
A, B = team("Aces", 64), team("Bolts", 64)          # 130 players
sheets.league_season = lambda: {"schedule": [{"division": "RED",
    "date": TODAY.strftime("%m/%d/%Y"), "time": "9:00 AM", "field": "JCP",
    "home": "Aces", "away": "Bolts", "status": ""}],
    "rosters": {"RED": [A, B], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [{"name": p["name"], "div": "RED",
    "email": p["name"].replace(" ", ".").lower() + "@e.com", "phone": ""}
    for t in (A, B) for p in t["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []
sheets.add_notice = lambda *a, **k: None
sheets._mark_league_games_cancelled = lambda d: 1
sheets._log_cancellation = lambda *a: None

REAL_SETTINGS = sheets.cancellation_settings
MAIN = "https://script.google.com/macros/s/MAIN/exec?key=k"
BACKUP = "https://script.google.com/macros/s/BACKUP/exec?key=k"
def settings(backup=BACKUP):
    return {"sender_url": MAIN, "overflow_url": backup, "cap": 100,
            "emails_enabled": True, "test_mode": False, "test_address": ""}

def run(remaining, post, backup=BACKUP):
    sheets._capacity_cache.clear()
    sheets.cancellation_settings = lambda: settings(backup)
    sheets._sender_remaining = lambda url: remaining[url]
    sheets._post_to_sender = post
    return sheets.send_cancellation("rain", "", "Tom")

# ---- the arithmetic ---------------------------------------------------------
assert sheets._people_that_fit(100) == 97       # 97 people + 3 self-copies
assert sheets._sends_needed(97) == 100
assert sheets._people_that_fit(0) == 0
assert sheets._people_that_fit(20) == 19
assert sheets._people_that_fit(1500) == 150     # never more than one call allows

# ---- 1. fresh day: 100-send main account takes 97, backup takes 33 ---------
sent = {}
def ok_post(url, subject, body, rec, test_to=""):
    sent[url] = list(rec); return {"ok": True, "sent": len(rec), "missed": []}
res = run({MAIN: 100, BACKUP: 100}, ok_post)
assert len(sent[MAIN]) == 97 and len(sent[BACKUP]) == 33, {k: len(v) for k, v in sent.items()}
assert res["emailed"] == 130 and res["missed"] == [], res
print("fresh day        : main 97 + backup 33 = 130, nobody missed")

# ---- 2. main already used 60 earlier today: backup takes up the slack ------
sent.clear()
res = run({MAIN: 40, BACKUP: 100}, ok_post)
assert len(sent[MAIN]) == 39 and len(sent[BACKUP]) == 91, {k: len(v) for k, v in sent.items()}
assert res["emailed"] == 130 and res["missed"] == []
print("main half used   : main 39 + backup 91 = 130, nobody missed")

# ---- 3. main account refuses everything: backup picks those people up ------
sent.clear()
def main_dead(url, subject, body, rec, test_to=""):
    if url == MAIN:
        return {"ok": False, "sent": 0, "error": "daily email limit too low"}
    sent[url] = list(rec); return {"ok": True, "sent": len(rec), "missed": []}
res = run({MAIN: 100, BACKUP: 100}, main_dead)
assert len(sent[BACKUP]) == 97, len(sent[BACKUP])      # all the backup can hold
assert res["emailed"] == 97 and len(res["missed"]) == 33, (res["emailed"], len(res["missed"]))
# captains/managers (sorted first) were among those rerouted
assert not any(n.endswith("Mgr") for n in res["missed"]), "managers must be emailed first"
print("main refuses     : backup takes over 97, the 33 it cannot hold are named")

# ---- 4. the backup row holds an email address, not a web address ------------
# Uses the REAL settings reader, fed the values exactly as they sit in the sheet.
sent.clear()
sheets.cancellation_settings = REAL_SETTINGS
sheets.CONTROL_SHEET_ID, sheets._SA_JSON = "x", "x"
sheets._control_tab_rows = lambda *a: [["Setting", "Value", "Notes"],
    ["Sender URL", MAIN, ""], ["Emails enabled", "Yes", ""],
    ["Email cap", "100", ""], ["Overflow sender URL", "jssaadmin@gmail.com", ""],
    ["Test mode", "No", ""], ["Test address", "t@e.com", ""]]
sheets._cancel_settings_cache.update(data=None, ts=0.0)
sheets._capacity_cache.clear()
sheets._sender_remaining = lambda url: 100
sheets._post_to_sender = ok_post
res = sheets.send_cancellation("rain", "", "Tom")
assert list(sent) == [MAIN], list(sent)
assert len(sent[MAIN]) == 97 and res["emailed"] == 97
assert len(res["missed"]) == 33, "the 33 left over must be named, not dropped"
assert "not a valid sender address" in res["note"], res["note"]
print("bad backup value : ignored, main takes 97, other 33 named, note explains")

# ---- 6. quota can't be read: fall back to a full day's cap -----------------
sent.clear()
sheets._capacity_cache.clear()
sheets.cancellation_settings = lambda: settings()
sheets._sender_remaining = lambda url: None
sheets._post_to_sender = ok_post
res = sheets.send_cancellation("rain", "", "Tom")
assert len(sent[MAIN]) == 97 and res["emailed"] == 130
print("quota unreadable : assumes a full day, still 97 + 33")

print("\nCAPACITY CHECKS PASSED")

"""The "Always CC" address on every cancellation email.

Checks: the setting is read from the Cancellation Settings tab (default
jssagames@gmail.com when the row is missing, blank = no copy, a bad value is
ignored and reported), the address is handed to each sender account only when
there is one, and the daily-limit arithmetic counts the extra send the CC costs
the backup account but not the main one (which is the CC address itself)."""
import os, sys, json, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

# ---- 1. the setting ---------------------------------------------------------
assert sheets.DEFAULT_CANCEL_CC == "jssagames@gmail.com"
assert any(r[0] == "Always CC" and r[1] == "jssagames@gmail.com"
           for r in sheets.CANCEL_SETTINGS_SEED), "new tabs are seeded with it"

REAL_SETTINGS = sheets.cancellation_settings
HEAD = [["Setting", "Value", "Notes"], ["Sender URL", "https://x/exec?key=k", ""]]

def read(extra_rows):
    sheets.CONTROL_SHEET_ID, sheets._SA_JSON = "x", "x"
    sheets._control_tab_rows = lambda *a: HEAD + extra_rows
    sheets._cancel_settings_cache.update(data=None, ts=0.0)
    return REAL_SETTINGS()

s = read([])
assert s["cc"] == "jssagames@gmail.com", "an older tab with no row still copies jssagames@"
s = read([["Always CC", "jssagames@gmail.com", ""]])
assert s["cc"] == "jssagames@gmail.com"
s = read([["Always CC", "board@e.com", ""]])
assert s["cc"] == "board@e.com", "the sheet can change it"
s = read([["Always CC", "", ""]])
assert s["cc"] == "" and "cc_problem" not in s, "a blank row switches the copy off"
s = read([["Always CC", "a@e.com, b@e.com", ""]])
assert s["cc"] == "" and s["cc_problem"] == "a@e.com, b@e.com", s
s = read([["Always CC", "not an address", ""]])
assert s["cc"] == "" and s.get("cc_problem"), s
print("setting          : default, changed, blank = off, bad value ignored and reported")

# ---- 2. what is handed to the sender script ---------------------------------
import urllib.request
seen = []
class FakeReply:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return b'{"ok": true, "sent": 1}'
def fake_urlopen(req, timeout=0):
    seen.append(json.loads(req.data.decode("utf-8"))); return FakeReply()
real_urlopen = urllib.request.urlopen
urllib.request.urlopen = fake_urlopen
try:
    sheets._post_to_sender("https://x/exec?key=k", "s", "b", ["p@e.com"], "", cc="jssagames@gmail.com")
    sheets._post_to_sender("https://x/exec?key=k", "s", "b", ["p@e.com"])
finally:
    urllib.request.urlopen = real_urlopen
assert seen[0]["cc"] == "jssagames@gmail.com"
assert "cc" not in seen[1], "no CC set -> nothing extra in the message to the sender"
print("hand-over        : cc is sent only when there is one")

# ---- 3. the daily-limit arithmetic -----------------------------------------
assert sheets._sends_needed(97) == 100                    # unchanged without a CC
assert sheets._sends_needed(97, cc_extra=1) == 103        # 97 + 3 self-copies + 3 CCs
assert sheets._people_that_fit(100) == 97
assert sheets._people_that_fit(100, cc_extra=1) == 94
assert sheets._people_that_fit(0, cc_extra=1) == 0
ACCOUNTS = {}
sheets._sender_account = lambda url: ACCOUNTS.get(url, "")
MAIN, BACKUP = "https://s/MAIN/exec?key=k", "https://s/BACKUP/exec?key=k"
ACCOUNTS.update({MAIN: "jssagames@gmail.com", BACKUP: "jssaadmin@gmail.com"})
assert sheets._cc_extra(MAIN, "jssagames@gmail.com") == 0, "copying itself costs nothing"
assert sheets._cc_extra(MAIN, "JSSAGames@Gmail.com ") == 0, "capitals and spaces do not matter"
assert sheets._cc_extra(BACKUP, "jssagames@gmail.com") == 1, "the backup pays one per message"
assert sheets._cc_extra("https://s/UNKNOWN/exec", "jssagames@gmail.com") == 1, "unsure -> assume it is sent"
assert sheets._cc_extra(BACKUP, "") == 0, "no CC, no cost"
sheets._sender_remaining = lambda url: 100
sheets._capacity_cache.clear()
assert sheets.sender_capacity(MAIN, 100, fresh=True, cc="jssagames@gmail.com") == 97
assert sheets.sender_capacity(BACKUP, 100, fresh=True, cc="jssagames@gmail.com") == 94
assert sheets.sender_capacity(BACKUP, 100, fresh=True) == 97
print("daily limit      : main 97 (copies itself), backup 94 (pays for the CC), no CC = 97")

# ---- 4. a real cancellation: both accounts are told about the CC ------------
TODAY = datetime.datetime.now(sheets._EASTERN).date()
def team(n, c):
    return {"team": n, "division": "RED", "manager": n + " Mgr",
            "players": [{"name": "%s P%03d" % (n, i)} for i in range(c)]
                       + [{"name": n + " Mgr"}]}
A, B = team("Aces", 64), team("Bolts", 64)                     # 130 players
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

def settings(cc):
    d = {"sender_url": MAIN, "overflow_url": BACKUP, "cap": 100,
         "emails_enabled": True, "test_mode": False, "test_address": ""}
    if cc is not None: d["cc"] = cc
    return d

def run(cc, problem=False):
    sheets._capacity_cache.clear()
    st = settings(cc)
    if problem: st["cc_problem"] = "a@e.com, b@e.com"
    sheets.cancellation_settings = lambda: st
    posts = {}
    def post(url, subject, body, rec, test_to="", cc=""):
        posts[url] = {"n": len(rec), "cc": cc}; return {"ok": True, "sent": len(rec), "missed": []}
    sheets._post_to_sender = post
    res = sheets.send_cancellation("rain", "", "Tom")
    return res, posts

res, posts = run("jssagames@gmail.com")
assert posts[MAIN]["cc"] == "jssagames@gmail.com" and posts[BACKUP]["cc"] == "jssagames@gmail.com", posts
assert posts[MAIN]["n"] == 97, "the main account still takes 97"
assert posts[BACKUP]["n"] == 33 and res["emailed"] == 130 and res["missed"] == [], (posts, res)
print("real send        : both accounts told to CC jssagames@, everyone still reached")

res, posts = run("")
assert posts[MAIN]["cc"] == "" and posts[BACKUP]["cc"] == "", posts
res, posts = run(None)
assert posts[MAIN]["cc"] == "" , "a settings dict with no cc behaves exactly as before"
print("no CC            : nothing extra is sent")

res, posts = run("", problem=True)
assert "Always CC" in res["note"], res["note"]
print("bad value        : the note says no copy was sent, and the cancellation still went out")

print("\nCC CHECKS PASSED")

"""Every reason an email might not arrive must be distinguishable in the log.

"0 emailed" on its own is useless when nothing turns up: it can't tell the
board whether a box was ticked, the sender was never set up, or the send
actually failed. Each case below must write a line that says which."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()
DSTR = TODAY.strftime("%m/%d/%Y")
T = {"team": "Aces", "division": "RED", "manager": "Aces Mgr",
     "players": [{"name": "Aces P%d" % i} for i in range(9)] + [{"name": "Aces Mgr"}]}

sheets.league_season = lambda: {
    "schedule": [{"division": "RED", "date": DSTR, "time": "9:00 AM",
                  "field": "Jupiter Community Park", "home": "Aces",
                  "away": "Aces", "status": ""}],
    "rosters": {"RED": [T], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [
    {"name": p["name"], "div": "RED",
     "email": p["name"].replace(" ", ".").lower() + "@e.com", "phone": ""}
    for p in T["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []
sheets.add_notice = lambda *a, **k: None
sheets._mark_league_games_cancelled = lambda d: 0

BASE = {"sender_url": "https://games.test/exec?key=k", "overflow_url": "",
        "cap": 100, "emails_enabled": True, "test_mode": True,
        "test_address": "tom@example.com"}

logged = []
sheets._log_cancellation = lambda *a: logged.append(a[-1])

def run(settings, sender_result=None, **kw):
    logged.clear()
    sheets.cancellation_settings = lambda: settings
    sheets._post_to_sender = (lambda *a, **k: sender_result) if sender_result \
        else (lambda *a, **k: {"ok": True, "sent": 0, "test": True})
    sheets.send_cancellation("Fields flooded", "", "Tom", **kw)
    return logged[0]

cases = [
    ('"Website notice only" was ticked',
     run(BASE, banner_only=True), "Banner only"),
    ("the sender was never set up",
     run(dict(BASE, sender_url="")), "No sender address"),
    ("emails switched off in the sheet",
     run(dict(BASE, emails_enabled=False)), "switched off"),
    ("the send failed",
     run(BASE, sender_result={"ok": False, "sent": 0, "error": "unauthorized"}),
     "Email problem: unauthorized"),
    ("it worked — practice run",
     run(BASE), "TEST MODE — everything went to tom@example.com"),
]

print("What the log now says in each case:\n")
for label, line, must in cases:
    print("  %-34s %s" % (label + ":", line))
    assert must in line, "%s -> %r" % (label, line)

# every case must read differently from every other
lines = [c[1] for c in cases]
assert len(set(lines)) == len(lines), "two cases log the same thing"
print("\nall five read differently: YES")

# and the real send names the count, not a test address
real = run(dict(BASE, test_mode=False, test_address=""),
           sender_result={"ok": True, "sent": 10})
print("\n  %-34s %s" % ("a real send:", real))
assert "10 emailed" in real and "TEST" not in real
assert "no email step ran" not in real, "a successful send must not claim it never ran"

print("\nLOGGING CHECKS PASSED")

"""A practice run must report what the REAL send would do.

Practice mode used to take a different route through the sender than the real
send, so a green practice proved less than it appeared to. Now it rehearses
the same route and reports the real headcount and whether today's remaining
quota covers it."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()
T = {"team": "Aces", "division": "RED", "manager": "Aces Mgr",
     "players": [{"name": "Aces P%02d" % i} for i in range(54)] + [{"name": "Aces Mgr"}]}
sheets.league_season = lambda: {"schedule": [{"division": "RED",
    "date": TODAY.strftime("%m/%d/%Y"), "time": "9:00 AM",
    "field": "Jupiter Community Park", "home": "Aces", "away": "Aces",
    "status": ""}], "rosters": {"RED": [T], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [{"name": p["name"], "div": "RED",
    "email": p["name"].replace(" ", ".").lower() + "@e.com", "phone": ""}
    for p in T["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []
sheets.add_notice = lambda *a, **k: None
sheets._mark_league_games_cancelled = lambda d: 0
logged = []
sheets._log_cancellation = lambda *a: logged.append(a[-1])
sheets.cancellation_settings = lambda: {
    "sender_url": "https://script.google.com/macros/s/A/exec?key=k",
    "overflow_url": "", "cap": 100, "emails_enabled": True,
    "test_mode": True, "test_address": "tom@example.com"}

plan = sheets.todays_cancellation_plan()
print("scheduled today:", len(plan["recipients"]), "players\n")
assert len(plan["recipients"]) == 55

def practice(remaining):
    """Simulate the updated sender script's practice-mode reply."""
    def fake(url, subject, body, recipients, test_to=""):
        assert test_to, "practice must pass a test address"
        n = len(recipients)
        warning = ""
        if remaining < n:
            warning = ("The REAL send would be blocked right now: it needs %d "
                       "sends but only %d are left today." % (n, remaining))
        return {"ok": True, "sent": 0, "test": True, "would_send": n,
                "remaining": remaining, "warning": warning}
    sheets._post_to_sender = fake
    logged.clear()
    return sheets.send_cancellation("Fields flooded", "", "Tom")

# --- plenty of quota left --------------------------------------------------
res = practice(78)
print("With 78 sends left:")
print("  " + res["note"])
assert "Rehearsed the real route for 55 players." in res["note"]
assert "78 sends left today — enough for all 55." in res["note"]
assert res["emailed"] == 0, "no player may be emailed by a practice run"

# --- not enough quota: the practice must warn BEFORE the real send ---------
res = practice(20)
print("\nWith only 20 sends left:")
print("  " + res["note"])
assert "would be blocked" in res["note"] and "⚠" in res["note"]
assert "enough for all" not in res["note"]
assert res["emailed"] == 0

print("\nthe warning is recorded in the log too:")
print("  " + logged[0][-120:])
assert "blocked" in logged[0]

print("\nREHEARSAL CHECKS PASSED")

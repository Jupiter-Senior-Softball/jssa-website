"""Practice (test) mode: emails go to one address, the banner is real, the
schedule is untouched, and practising never blocks the real cancellation."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()
DSTR = TODAY.strftime("%m/%d/%Y")

T = {"team": "Aces", "division": "RED", "manager": "Aces Mgr",
     "players": [{"name": "Aces P%d" % i} for i in range(10)] + [{"name": "Aces Mgr"}]}
U = {"team": "Bolts", "division": "RED", "manager": "Bolts Mgr",
     "players": [{"name": "Bolts P%d" % i} for i in range(10)] + [{"name": "Bolts Mgr"}]}

sheets.league_season = lambda: {
    "schedule": [{"division": "RED", "date": DSTR, "time": "9:00 AM",
                  "field": "Jupiter Community Park", "home": "Aces",
                  "away": "Bolts", "status": ""}],
    "rosters": {"RED": [T, U], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [
    {"name": p["name"], "div": "RED",
     "email": p["name"].replace(" ", ".").lower() + "@e.com", "phone": ""}
    for t in (T, U) for p in t["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""

PRACTICE = {"sender_url": "https://games.test/exec?key=k", "overflow_url": "",
            "cap": 100, "emails_enabled": True, "test_mode": True,
            "test_address": "tom@example.com"}
LIVE = dict(PRACTICE, test_mode=False, test_address="")

posts, banners, marked, log = [], [], [], []
def fake_post(url, subject, body, recipients, test_to=""):
    posts.append({"n": len(recipients), "test_to": test_to})
    # mirrors the real sender: in practice mode it reports 0 players emailed
    return {"ok": True, "sent": 0 if test_to else len(recipients)}
sheets._post_to_sender = fake_post
sheets.add_notice = lambda t, m, by, url="", lt="": banners.append(m)
sheets._mark_league_games_cancelled = lambda d: marked.append(d) or 1
sheets._log_cancellation = lambda *a: log.append(a)

# ---- a practice run -------------------------------------------------------
sheets.cancellation_settings = lambda: PRACTICE
sheets._cancel_log_rows = lambda: []
res = sheets.send_cancellation("Testing", "", "Tom")
print("practice run:")
print("  players emailed :", res["emailed"], "(must be 0)")
print("  sent instead to :", posts[0]["test_to"])
print("  banner posted   :", bool(banners), "->", banners[0])
print("  schedule touched:", bool(marked), "(must be False)")
print("  log result      :", log[0][-1])
assert res["emailed"] == 0
assert posts[0]["test_to"] == "tom@example.com"
assert posts[0]["n"] == 22, posts[0]["n"]
assert banners and "CANCELLED" in banners[0]
assert not marked, "a practice run must never mark the real schedule"
assert log[0][-1].startswith("TEST RUN")

# ---- practising twice is allowed -----------------------------------------
sheets._cancel_log_rows = lambda: [sheets.CANCEL_LOG_HEADERS,
    [TODAY.isoformat(), "6:40 AM", "Tom", "LEAGUE", "JCP", "Testing", "0", "",
     "TEST RUN — Banner posted · 0 emailed"]]
res2 = sheets.send_cancellation("Testing again", "", "Tom")
print("\nsecond practice run allowed:", res2["ok"])
assert res2["ok"], "a practice run must not block another practice run"

# ---- and the real one still goes through ---------------------------------
sheets.cancellation_settings = lambda: LIVE
posts.clear(); marked.clear()
real = sheets.send_cancellation("Fields flooded", "", "Tom")
print("\nreal run after practising:")
print("  players emailed :", real["emailed"])
print("  schedule marked :", bool(marked))
assert real["emailed"] == 22, real["emailed"]
assert not posts[0]["test_to"]
assert marked, "the real run must mark the schedule"

# ---- but a real one blocks a second real one -----------------------------
sheets._cancel_log_rows = lambda: [sheets.CANCEL_LOG_HEADERS,
    [TODAY.isoformat(), "6:52 AM", "Tom", "LEAGUE", "JCP", "Fields flooded",
     "22", "", "Banner posted · 22 emailed"]]
blocked = sheets.send_cancellation("again", "", "Someone else")
print("\nsecond real run blocked:", not blocked["ok"], "->", blocked["note"])
assert not blocked["ok"]

print("\nPRACTICE-MODE CHECKS PASSED")

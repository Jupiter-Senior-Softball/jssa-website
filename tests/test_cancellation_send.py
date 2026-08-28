import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()
DSTR = TODAY.strftime("%m/%d/%Y")

# 130 scheduled players — a busy winter league day
def team(n, c):
    return {"team": n, "division": "RED", "manager": n + " Mgr",
            "players": [{"name": "%s P%03d" % (n, i)} for i in range(c)]
                       + [{"name": n + " Mgr"}]}
A, B = team("Aces", 64), team("Bolts", 64)

sheets.league_season = lambda: {
    "schedule": [{"division": "RED", "date": DSTR, "time": "9:00 AM",
                  "field": "Jupiter Community Park", "home": "Aces",
                  "away": "Bolts", "status": ""}],
    "rosters": {"RED": [A, B], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [
    {"name": p["name"], "div": "RED",
     "email": p["name"].replace(" ", ".").lower() + "@e.com", "phone": ""}
    for t in (A, B) for p in t["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []
sheets.cancellation_settings = lambda: {
    "sender_url": "https://games.test/exec?key=k",
    "overflow_url": "https://admin.test/exec?key=k",
    "cap": 100, "emails_enabled": True, "test_mode": False, "test_address": ""}

calls = []
def fake_post(url, subject, body, recipients, test_to=""):
    calls.append({"url": url, "n": len(recipients)})
    return {"ok": True, "sent": len(recipients)}
sheets._post_to_sender = fake_post

banners = []
sheets.add_notice = lambda t, m, by, url="", lt="": banners.append((t, m, by))
sheets._mark_league_games_cancelled = lambda d: 1
logged = []
sheets._log_cancellation = lambda *a: logged.append(a)

plan = sheets.todays_cancellation_plan()
print("scheduled today :", len(plan["people"]))
print("cap (2 accounts):", plan["cap"])
res = sheets.send_cancellation("Fields flooded", "", "Tom", plan=plan)

print("\nemail batches sent:")
for c in calls:
    who = "jssagames (main)" if "games.test" in c["url"] else "jssaadmin (backup)"
    print("   %-20s %d people" % (who, c["n"]))
print("\ntotal emailed   :", res["emailed"])
print("not reached     :", len(res["missed"]))
print("banner posted   :", res["banner"])
print("banner text     :", banners[0][1])

assert len(calls) == 2
assert calls[0]["n"] == 100 and "games.test" in calls[0]["url"]
assert calls[1]["n"] == 30 and "admin.test" in calls[1]["url"]
assert res["emailed"] == 130 and len(res["missed"]) == 0
assert banners[0][0] == "weather"

# duplicate guard
sheets._cancel_log_rows = lambda: [sheets.CANCEL_LOG_HEADERS,
    [TODAY.isoformat(), "6:52 AM", "Tom", "LEAGUE", "JCP", "rain", "130", "", "ok"]]
again = sheets.send_cancellation("rain again", "", "Someone else")
print("\nsecond attempt  :", again["note"])
assert not again["ok"] and again["emailed"] == 0
assert len(calls) == 2, "no extra email may be sent"

print("\nSEND CHECKS PASSED")

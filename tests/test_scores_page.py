"""Admin Scores page: only played-but-unscored games are offered; Cancelled/
Postponed and future games are hidden; a cancelled game can't be given a score.
Fake data only."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["ADMIN_PASSWORD"] = "adminpw"
os.environ["SECRET_KEY"] = "test"
import sheets

TODAY = datetime.date(2026, 11, 9)
def g(row, date, time, status, sh="", sa="", div="RED", home="Aces", away="Bolts"):
    return {"row": row, "division": div, "date": date, "time": time, "field": "JCP - Field 1",
            "home": home, "away": away, "score_home": sh, "score_away": sa, "status": status}

games = [
    g(2, "10/26/2026", "9:00 AM", "Cancelled"),
    g(3, "11/4/2026", "9:00 AM", "Postponed"),
    g(4, "11/6/2026", "9:00 AM", "Final", "4", "7"),
    g(5, "11/6/2026", "10:30 AM", "Scheduled"),            # played, no score yet
    g(6, "11/9/2026", "9:00 AM", "Scheduled"),             # today
    g(7, "11/11/2026", "9:00 AM", "Scheduled"),            # future
    g(8, "11/12/2026", "9:00 AM", "Cancelled", "0", "0"),  # cancelled with 0-0
    g(9, "not a date", "9:00 AM", "Scheduled"),            # unreadable date: never hidden
]
r = sheets.split_games_for_scoring(games, TODAY)
rows = lambda k: [x["row"] for x in r[k]]
assert rows("needs_score") == [6, 5, 9], rows("needs_score")   # newest first, odd date last
assert rows("played") == [4], rows("played")
assert sorted(rows("off")) == [2, 3, 8], rows("off")
assert rows("upcoming") == [7], rows("upcoming")

import app as appmod
sheets.schedule_games_for_scoring = lambda: games
saved = []
sheets.set_game_score = lambda row, h, a, status="Final": saved.append(row) or True
c = appmod.app.test_client()
with c.session_transaction() as s:
    s["admin"] = True

# Division page: only the games that need a score are offered
html = c.get("/admin/scores?division=RED").get_data(as_text=True)
assert html.count("Needs score") == 3, html.count("Needs score")
assert html.count("Update score") == 1
assert "10/26/2026" not in html and "11/12/2026" not in html and "11/11/2026" not in html
assert "3 </b> cancelled" in html.replace("</b>", " </b>") or "<b>3</b> cancelled" in html
assert "<b>1</b> future game is hidden" in html

# Picker counts only games that need a score
pick = c.get("/admin/scores").get_data(as_text=True)
assert '<span class="num ">3</span>' in pick, "RED should show 3 to score"

# Cancelled game: save is refused, nothing is written
resp = c.post("/admin/scores/save", data={"row": "2", "score_home": "5", "score_away": "3", "division": "RED"})
assert "saved=2" in resp.headers["Location"], resp.headers["Location"]
assert saved == [], "a cancelled game was scored"
assert "no score was saved" in c.get("/admin/scores?division=RED&saved=2").get_data(as_text=True)

# A game that really needs a score still saves
resp = c.post("/admin/scores/save", data={"row": "5", "score_home": "5", "score_away": "3", "division": "RED"})
assert "saved=1" in resp.headers["Location"] and saved == [5]
print("ok")

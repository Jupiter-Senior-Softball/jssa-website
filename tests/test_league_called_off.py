"""A Cancelled/Postponed game is never 'Final' and never counts in standings,
even if its score cells hold 0-0. Fake data only."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["ADMIN_PASSWORD"] = "adminpw"
os.environ["SECRET_KEY"] = "test"
import sheets

assert sheets._game_called_off("Cancelled") and sheets._game_called_off("canceled")
assert sheets._game_called_off("Postponed") and sheets._game_called_off(" Rained out ")
assert not sheets._game_called_off("Final") and not sheets._game_called_off("Scheduled")
assert not sheets._game_called_off("")

# standings ignore a game whose scores were blanked because it was called off
sched = [
    {"division": "RED", "home": "A", "away": "B", "score_home": "", "score_away": "", "status": "Cancelled"},
    {"division": "RED", "home": "A", "away": "B", "score_home": "5", "score_away": "3", "status": "Final"},
]
st = {t["team"]: t for t in sheets._standings_from_schedule(sched)["RED"]}
assert st["A"]["wins"] == 1 and st["B"]["losses"] == 1 and st["A"]["ties"] == 0

import app as appmod
season = {"standings": {"RED": [], "WHITE": [], "BLUE": []}, "umpires_enabled": False,
          "schedule": [
  {"division": "RED", "date": "10/19/2026", "dow": "Monday", "time": "10:30 AM", "field": "Field 1",
   "home": "Bad Moon Rising", "away": "Knee'd To Win", "score_home": "", "score_away": "",
   "status": "Cancelled", "called_off": True, "umpires": []},
  {"division": "RED", "date": "10/21/2026", "dow": "Wednesday", "time": "9:00 AM", "field": "Field 1",
   "home": "Jackals", "away": "Mick's Picks", "score_home": "19", "score_away": "27",
   "status": "Final", "called_off": False, "umpires": []}],
  "results": [], "rosters": {"RED": [], "WHITE": [], "BLUE": []}, "teams": {"RED": [], "WHITE": [], "BLUE": []}}
sheets.league_season = lambda: season
html = appmod.app.test_client().get("/league/schedules").get_data(as_text=True)
assert 'class="gstatus off">Cancelled' in html, "cancelled badge missing"
assert html.count(">Final<") == 1
print("ok")

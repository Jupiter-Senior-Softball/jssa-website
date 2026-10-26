"""Schedule page: upcoming games first, completed games (final score, or cancelled and
past) at the bottom newest first, winner ticked. Fake data; never touches Google."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import datetime, sheets, app as appmod

def g(date, time_, home, away, sh="", sa="", off=False, div="RED"):
    return {"division": div, "date": date, "dow": "", "time": time_, "field": "Field 1",
            "home": home, "away": away, "score_home": sh, "score_away": sa,
            "status": "Cancelled" if off else "Scheduled", "called_off": off, "umpires": []}

SCHED = [g("10/19/2026", "10:30 AM", "H1030", "A", "5", "3"), g("10/21/2026", "9:00 AM", "H21a", "A", "2", "6"),
         g("10/19/2026", "9:00 AM", "H0900", "A", "1", "1"), g("11/2/2026", "9:00 AM", "H112a", "A", "7", "0"),
         g("10/20/2026", "9:00 AM", "Hcancel", "A", off=True), g("12/30/2099", "9:00 AM", "Hfuture", "A"),
         g("12/30/2099", "9:00 AM", "Hfuturecancel", "A", off=True)]
DATA = {"standings": {"RED": [], "WHITE": [], "BLUE": []}, "schedule": list(SCHED), "results": [],
        "rosters": {"RED": [], "WHITE": [], "BLUE": []}, "teams": {"RED": [], "WHITE": [], "BLUE": []}}
sheets.league_season = lambda: DATA
fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

html = appmod.app.test_client().get("/league/schedules").get_data(as_text=True)
up, done = html.split("Completed &amp; cancelled games</h2>", 1)
names = lambda part: re.findall(r'class="tn">(H\w+)', part)
check("upcoming holds only games still to be played (even a future cancelled game moves down)", names(up) == ["Hfuture"], names(up))
check("completed: newest day first, 9:00 before 10:30, cancelled games included",
      names(done) == ["Hfuturecancel", "H112a", "H21a", "Hcancel", "H0900", "H1030"], names(done))
check("the winner gets a tick, a tie gets none",
      "H112a ✓" in done and "H21a ✓" not in done and "H0900 ✓" not in done and "A ✓" in done)
check("the sheet's own order is left untouched", DATA["schedule"] == SCHED)
print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

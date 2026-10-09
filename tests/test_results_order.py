"""The Results page: newest day first, and within a day the earlier game first
(9:00 AM above 10:30 AM), whatever order the sheet rows are in. Fake data."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets, app as appmod

def r(date, time_, home, away, div="RED"):
    return {"division": div, "date": date, "dow": "", "time": time_, "field": "Field 1",
            "home": home, "away": away, "home_score": "5", "away_score": "3", "result": "Final"}

RES = [r("10/19/2026", "10:30 AM", "H1030", "A"), r("10/21/2026", "9:00 AM", "H21a", "A"),
       r("10/19/2026", "9:00 AM", "H0900", "A"), r("11/2/2026", "10:30 AM", "H112b", "A"),
       r("10/21/2026", "10:30 AM", "H21b", "A"), r("11/2/2026", "9:00 AM", "H112a", "A"),
       r("9/30/2026", "9:00 AM", "Hsep", "A"), r("??", "9:00 AM", "Hodd", "A")]
DATA = {"standings": {"RED": [], "WHITE": [], "BLUE": []}, "schedule": [], "results": list(RES),
        "rosters": {"RED": [], "WHITE": [], "BLUE": []}, "teams": {"RED": [], "WHITE": [], "BLUE": []}}
sheets.league_season = lambda: DATA

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

html = appmod.app.test_client().get("/league/results").get_data(as_text=True)
order = re.findall(r'class="rteam">(H[\w]+)', html)
check("newest day first; 9:00 AM above 10:30 AM within each day", order ==
      ["H112a", "H112b", "H21a", "H21b", "H0900", "H1030", "Hsep", "Hodd"], order)
check("a result with an unreadable date goes last, not lost", order[-1] == "Hodd")
check("the sheet's own order is left untouched", DATA["results"] == RES)

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

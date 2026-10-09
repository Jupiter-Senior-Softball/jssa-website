"""The public schedule lists games by date, then time of day, no matter how the
rows are ordered on the sheet. Fake data; never touches Google."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets, app as appmod

def g(date, time_, home, away, div="RED"):
    return {"division": div, "date": date, "dow": "", "time": time_, "field": "Field 1",
            "home": home, "away": away, "score_home": "", "score_away": "", "status": "Scheduled"}

# Deliberately scrambled — the order the site was wrongly showing, plus extras.
SCHED = [g("10/21/2026", "10:30 AM", "Jackals", "Bad Moon Rising"),
         g("10/19/2026", "10:30 AM", "Bad Moon Rising", "Knee'd To Win"),
         g("12/2/2026", "9:00 AM", "Mick's Picks", "Knee'd To Win"),
         g("10/21/2026", "9:00 AM", "Mick's Picks", "Knee'd To Win"),
         g("10/19/2026", "9:00 AM", "Mick's Picks", "Jackals"),
         g("11/2/2026", "9:00 AM", "Jackals", "Bad Moon Rising"),
         g("9/30/2026", "1:00 PM", "A", "B"),
         g("??", "9:00 AM", "Odd", "Date")]
DATA = {"standings": {"RED": [], "WHITE": [], "BLUE": []}, "schedule": list(SCHED), "results": [],
        "rosters": {"RED": [], "WHITE": [], "BLUE": []}, "teams": {"RED": [], "WHITE": [], "BLUE": []}}
sheets.league_season = lambda: DATA

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

html = appmod.app.test_client().get("/league/schedules").get_data(as_text=True)
dates = re.findall(r'(\d{1,2}/\d{1,2}/\d{4}|\?\?)\s*</div>\s*<div class="t">([^<·]*)', html)
order = [(d, t.strip()) for d, t in dates]
expect = [("9/30/2026", "1:00 PM"), ("10/19/2026", "9:00 AM"), ("10/19/2026", "10:30 AM"),
          ("10/21/2026", "9:00 AM"), ("10/21/2026", "10:30 AM"), ("11/2/2026", "9:00 AM"),
          ("12/2/2026", "9:00 AM"), ("??", "9:00 AM")]
check("games appear by date, then 9:00 before 10:30", order == expect, order)
check("dates sort as dates, not text (9/30 before 10/19, 11/2 before 12/2)", order[0][0] == "9/30/2026")
check("a game with an unreadable date goes last, not lost", order[-1][0] == "??")
check("the sheet's own row order is left untouched", DATA["schedule"] == SCHED)

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

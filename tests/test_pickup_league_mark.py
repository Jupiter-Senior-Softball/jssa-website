"""A player marked "League" on the pickup schedule (in a league game that day)
is NOT counted as signed up for pickup on the website. Fake grid; no Google."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

HDR = ["Email", "First Name", "Last Name", "Division", "Position", "Mon, October 12", "Wed, October 14"]
ROWS = [
    ["", "", "", "", "", "Game Date", "Game Date"],
    ["Start Time", "", "", "", "", "9:00 AM", "9:00 AM"],
    ["Game Field", "", "", "", "", "Field 1", "Field 1"],
    HDR,
    ["a@x.com", "Ann", "Able", "RED", "SS", "X", ""],
    ["b@x.com", "Bob", "Baker", "WHITE", "OF", "League", "X"],
    ["c@x.com", "Cal", "Cole", "BLUE", "P", "League", ""],
    ["d@x.com", "Dee", "Dunn", "BLUE", "1B", "x", "League"],
    ["e@x.com", "Eli", "Epps", "RED", "IF", "", ""],
]
REF = dt.datetime(2026, 10, 10, 9, 0, tzinfo=sheets._EASTERN)

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

g = sheets._parse_schedule_grid(ROWS, REF)
check("next game is Mon Oct 12", g and g["date_label"].startswith("Mon"), g and g["date_label"])
names = sorted(p["name"] for d in g["players"].values() for p in d)
check("only the real sign-ups are listed (League-marked players are not)", names == ["Ann Able", "Dee Dunn"], names)
check("counts exclude League-marked players", g["counts"] == {"RED": 1, "WHITE": 0, "BLUE": 1, "TOTAL": 2}, g["counts"])
g2 = sheets._parse_schedule_grid(ROWS, dt.datetime(2026, 10, 13, 9, 0, tzinfo=sheets._EASTERN))
names2 = sorted(p["name"] for d in g2["players"].values() for p in d)
check("same rule on the next date column", names2 == ["Bob Baker"], names2)
ROWS2 = [r[:5] + ["League" if r[5] == "League" else r[5], r[6]] for r in ROWS]
check("'LEAGUE' in any capitals is also ignored", sheets._parse_schedule_grid([r[:5] + [r[5].upper() if r[5] == "League" else r[5], r[6]] for r in ROWS], REF)["counts"]["TOTAL"] == 2)

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

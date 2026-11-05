"""Each field on the Game Day Teams page carries its own start time.

The board can publish a time per field (a "Game Time" row in the roster block);
a field with no time shows the pickup schedule's Start Time for that date; and a
roster with neither shows no time at all. Built from the real schedule layout.
Run:  python tests/test_game_time.py   (needs Flask, like the other page tests)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets, app as webapp

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % (extra,)))
    if not cond: fails.append(label)

# ---- the time reader --------------------------------------------------------
for raw, want in [("9:00 AM", "9:00 AM"), ("9:00am", "9:00 AM"), ("9am", "9:00 AM"),
                  ("10:30 AM", "10:30 AM"), ("10:30AM", "10:30 AM"), ("1 pm", "1:00 PM"),
                  ("9:00:00 AM", "9:00 AM"), ("  9:00 a.m. ", "9:00 AM"),
                  ("", ""), ("TBD", ""), ("9", ""), ("25:00 AM", ""), ("9:75 AM", "")]:
    check("time %-12r -> %r" % (raw, want), sheets._clean_time(raw) == want, sheets._clean_time(raw))

# ---- the pickup schedule tab, laid out like the real one ---------------------
D = ["Fri, November 6", "Mon, November 9", "Wed, November 11", "Fri, November 13"]
T = ["9:00 AM", "9:00 AM", "10:30 AM", "9:00 AM"]
GRID = [
    ["", "JSSA PICK UP GAME SCHEDULE"],
    ["", "Game Date", "", "", ""] + D,
    ["", " Start Time   ", "", "", ""] + T,
    ["", "Game Field", "", "", ""] + ["Jupiter Community Park"] * 4,
    ["Email", "First Name", "Last Name", "Division", "Position"] + D,
    ["a@x.com", "Ann", "Able", "RED", "SS"] + [""] * 4,
]
sheets._schedule_worksheet = lambda: type("W", (), {"get_all_values": lambda self: GRID})()
check("Fri Nov 6  -> 9:00 AM", sheets.pickup_game_time("Friday, November 6, 2026") == "9:00 AM")
check("Wed Nov 11 -> 10:30 AM", sheets.pickup_game_time("Wednesday, November 11, 2026") == "10:30 AM")
check("a date not on the schedule gives NO time",
      sheets.pickup_game_time("Monday, January 4, 2027") == "")
check("venue still works", sheets.pickup_game_venue("Wednesday, November 11, 2026") == "Jupiter Community Park")
check("venue still falls back to the first game",
      sheets.pickup_game_venue("Monday, January 4, 2027") == "Jupiter Community Park")

# ---- the published roster block ---------------------------------------------
def block(time_row=None, date="Wednesday, November 11, 2026"):
    rows = [["JSSA Game Day Teams"], [date], ["Jupiter Community Park"]]
    if time_row is not None:
        rows.append(time_row)
    rows.append(["Today's Players", "Preferred Positions", "Field 1", "Field 3"])
    rows.append(["Ann Able", "SS", "H Captain", ""])
    rows.append(["Bob Baker", "P", "V Captain", ""])
    rows.append(["Cal Cole", "OF", "", "H Captain"])
    rows.append(["Dee Dunn", "1B", "", "V Captain"])
    return rows

def times(data): return [(f["name"], f["time"]) for f in data["fields"]]

d = sheets._parse_teams_block(block(["", "Game Time", "9:00 AM", "10:30 AM"]), enforce_date_window=False)
check("each field keeps the time the board set",
      times(d) == [("Field 1", "9:00 AM"), ("Field 3", "10:30 AM")], times(d))
check("the time row is not shown as an info pill", d["info"] == "", d["info"])

d = sheets._parse_teams_block(block(["", "Game Time", "9am", "10:30am"]), enforce_date_window=False)
check("a time typed loosely is shown tidily",
      times(d) == [("Field 1", "9:00 AM"), ("Field 3", "10:30 AM")], times(d))

d = sheets._parse_teams_block(block(["", "Game Time", "9:00 AM", ""]), enforce_date_window=False)
check("a field left blank uses the schedule's time for that date (Wed = 10:30)",
      times(d) == [("Field 1", "9:00 AM"), ("Field 3", "10:30 AM")], times(d))

d = sheets._parse_teams_block(block(None), enforce_date_window=False)
check("no time row at all: every field uses the schedule (Wed = 10:30)",
      times(d) == [("Field 1", "10:30 AM"), ("Field 3", "10:30 AM")], times(d))

d = sheets._parse_teams_block(block(None, date="Friday, November 6, 2026"), enforce_date_window=False)
check("Friday's roster with no time row shows 9:00 AM",
      times(d) == [("Field 1", "9:00 AM"), ("Field 3", "9:00 AM")], times(d))

d = sheets._parse_teams_block(block(["", "Game Time", "TBD", "soon"]), enforce_date_window=False)
check("unreadable times fall back to the schedule, never shown as typed",
      times(d) == [("Field 1", "10:30 AM"), ("Field 3", "10:30 AM")], times(d))

sheets._schedule_worksheet = lambda: (_ for _ in ()).throw(RuntimeError("sheet down"))
d = sheets._parse_teams_block(block(None), enforce_date_window=False)
check("schedule unreachable and nothing published: no time shown, page still works",
      times(d) == [("Field 1", ""), ("Field 3", "")] and d["total_players"] == 4, times(d))

# ---- an older roster block (no time row) still reads exactly as before ------
sheets._schedule_worksheet = lambda: type("W", (), {"get_all_values": lambda self: GRID})()
d = sheets._parse_teams_block(block(None), enforce_date_window=False)
check("players, captains and sides are unchanged",
      d["total_players"] == 4 and [p["name"] for p in d["fields"][0]["home"]] == ["Ann Able"]
      and [p["name"] for p in d["fields"][1]["visitor"]] == ["Dee Dunn"])

# ---- the page itself --------------------------------------------------------
d = sheets._parse_teams_block(block(["", "Game Time", "9:00 AM", "10:30 AM"]), enforce_date_window=False)
with webapp.app.test_request_context("/teams"):
    html = webapp.render_template("teams.html", teams=d, card_slugs=set(), cards={})
i1, i3 = html.index("Field 1"), html.index("Field 3")
check("the page shows 9:00 AM beside Field 1", "9:00 AM" in html[i1:i1 + 400], html[i1:i1 + 200])
check("the page shows 10:30 AM beside Field 3", "10:30 AM" in html[i3:i3 + 400], html[i3:i3 + 200])
d = sheets._parse_teams_block(block(["", "Game Time", "", ""]), enforce_date_window=False)
sheets._schedule_worksheet = lambda: (_ for _ in ()).throw(RuntimeError("down"))
d = sheets._parse_teams_block(block(None), enforce_date_window=False)
with webapp.app.test_request_context("/teams"):
    html = webapp.render_template("teams.html", teams=d, card_slugs=set(), cards={})
check("with no time at all the page shows no time box", 'class="ftime"' not in html.split("</style>")[-1])

print("\n" + ("ALL GAME TIME CHECKS PASSED" if not fails else "%d FAILED" % len(fails)))
sys.exit(1 if fails else 0)

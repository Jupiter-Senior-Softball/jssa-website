"""A player can put their team's league games into their own calendar (Google, Apple,
Yahoo, Outlook). Checks the calendar file and the button on the Schedule page.
Fake data; never touches Google."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets, calendar_feed, app as appmod

def g(date, time_, home, away, div="RED", **kw):
    d = {"division": div, "date": date, "dow": "", "time": time_, "field": "Maplewood Park - East Field",
         "home": home, "away": away, "score_home": "", "score_away": "", "status": "Scheduled",
         "called_off": False, "umpires": []}
    d.update(kw); return d

SCHED = [g("10/19/2026", "9:00 AM", "Mick's Picks", "Jackals", umpires=["Al Smith", "Bo Jones"]),
         g("10/19/2026", "10:30 AM", "Bad Moon Rising", "Knee'd To Win"),
         g("10/21/2026", "10:30 AM", "Jackals", "Bad Moon Rising", status="Cancelled", called_off=True),
         g("11/2/2026", "", "Jackals", "Knee'd To Win"),
         g("10/14/2026", "9:00 AM", "Jackals", "Mick's Picks", score_home="12", score_away="8", status="Final"),
         g("soon", "9:00 AM", "Jackals", "Mick's Picks"),
         g("10/19/2026", "9:00 AM", "Jackals", "Sluggers", div="BLUE")]
DATA = {"standings": {"RED": [], "WHITE": [], "BLUE": []}, "schedule": list(SCHED), "results": [],
        "rosters": {"RED": [], "WHITE": [], "BLUE": []}, "teams": {"RED": [], "WHITE": [], "BLUE": []}}
sheets.league_season = lambda: DATA

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

c = appmod.app.test_client()
r = c.get("/league/calendar/RED/jackals.ics")
ics = r.get_data(as_text=True)
flat = ics.replace("\r\n ", "")          # undo line folding to read it
check("the calendar address works and is a calendar file", r.status_code == 200 and r.mimetype == "text/calendar", (r.status_code, r.mimetype))
check("starts and ends as a calendar", ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n"))
check("only this team's games in this division (4 readable RED Jackals games)", flat.count("BEGIN:VEVENT") == 4, flat.count("BEGIN:VEVENT"))
check("another team's game is left out", "Knee'd To Win at Bad Moon Rising" not in flat)
check("the same-named team in another division is left out", "Sluggers" not in flat)
check("game time is Eastern, 90 minutes long",
      "DTSTART;TZID=America/New_York:20261019T090000" in flat and "DTEND;TZID=America/New_York:20261019T103000" in flat)
check("title reads visitor at home", "SUMMARY:JSSA Softball: Jackals at Mick's Picks" in flat)
check("field is the location", "LOCATION:Maplewood Park - East Field" in flat)
check("umpires are listed", "Umpires: Al Smith & Bo Jones" in flat)
check("a cancelled game stays, shouting CANCELLED", "SUMMARY:JSSA Softball: CANCELLED: Bad Moon Rising at Jackals" in flat)
check("...and is not silently dropped by the calendar app", "STATUS:CANCELLED" not in flat)
check("a game with no time becomes an all-day entry", "DTSTART;VALUE=DATE:20261102" in flat and "DTEND;VALUE=DATE:20261103" in flat)
check("a finished game shows its score", "Final score: Mick's Picks 8\\, Jackals 12" in flat, flat)
check("no line is longer than calendars allow", all(len(l.encode()) <= 75 for l in ics.split("\r\n")))
check("normally opens in the calendar; ?download=1 saves a file",
      r.headers["Content-Disposition"].startswith("inline") and
      c.get("/league/calendar/RED/jackals.ics?download=1").headers["Content-Disposition"] == 'attachment; filename="jssa-jackals.ics"')
check("apostrophes in a team name work", c.get("/league/calendar/red/mick-s-picks.ics").status_code == 200)
check("unknown team or division is a plain 404",
      c.get("/league/calendar/RED/nobody.ics").status_code == 404 and c.get("/league/calendar/GREEN/jackals.ics").status_code == 404
      and c.get("/league/calendar/WHITE/jackals.ics").status_code == 404)

# Moving a game keeps its identity, so a subscribed calendar moves it rather than doubling it.
def uids(text): return sorted(l for l in text.split("\r\n") if l.startswith("UID:"))
moved = [dict(x) for x in SCHED]; moved[0]["date"] = "10/20/2026"; moved[0]["time"] = "10:30 AM"; moved[0]["field"] = "West"
a = calendar_feed.team_calendar(SCHED, "RED", "Jackals"); b = calendar_feed.team_calendar(moved, "RED", "Jackals")
check("changing a game's date/time/field keeps the same entry", uids(a) == uids(b) and "20261020T103000" in b)
check("every game has its own ID", len(set(uids(a))) == 4)

html = c.get("/league/schedules").get_data(as_text=True)
check("the Schedule page has the calendar button and all three choices",
      all(x in html for x in ('id="calopen"', 'id="cal-google"', 'id="cal-apple"', 'id="cal-file"')))

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

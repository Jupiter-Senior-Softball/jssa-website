"""The schedule editor: its own password, validation, writing only the cells that
changed, refusing stale/scored games, spare-row adds, and the change log.
Fake Schedule tab; never touches Google."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import gspread
import sheets

HEAD = ["Division", "Date", "Time", "Field", "Home Team", "Away Team", "Score Home", "Score Away", "Status"]
COLS = {h.lower(): i for i, h in enumerate(HEAD)}
ROWS = [list(HEAD),
        ["RED", "10/19/2026", "9:00 AM", "Field 1", "Mick's Picks", "Jackals", "", "", "Scheduled"],
        ["RED", "10/19/2026", "10:30 AM", "Field 1", "Bad Moon Rising", "Knee'd To Win", "", "", "Scheduled"],
        ["RED", "10/14/2026", "9:00 AM", "Field 1", "Jackals", "Mick's Picks", "7", "3", "Final"],
        ["", "", "", "", "", "", "", "", "Scheduled"],
        ["", "", "", "", "", "", "", "", "Scheduled"]]

class FakeWS:
    def __init__(self): self.writes = []; self.raw = None
    def batch_update(self, data, raw=True, **kw):
        self.raw = raw
        for d in data:
            a1 = d["range"]; col = ord(re.match(r"[A-Z]+", a1).group(0)) - 65; row = int(re.search(r"\d+", a1).group(0))
            ROWS[row - 1][col] = d["values"][0][0]; self.writes.append((a1, d["values"][0][0]))
WS = FakeWS()
sheets._schedule_tab = lambda: (WS, 0, COLS, ROWS)
sheets.CONTROL_SHEET_ID, sheets._SA_JSON = "x", "{}"
sheets.game_field_options = lambda: ["Field 1", "Field 2", "Field 3", "Field 4",
                                     "Maplewood Park - East Field", "Maplewood Park - West Field"]
sheets.schedule_team_options = lambda: {"RED": ["Bad Moon Rising", "Jackals", "Knee'd To Win", "Mick's Picks"], "WHITE": ["Aces"], "BLUE": []}
LOG = []
sheets._log_schedule_change = lambda *a: LOG.append(a)

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

WAS = {"date": "10/19/2026", "time": "9:00 AM", "home": "Mick's Picks", "away": "Jackals"}
def form(**kw):
    f = {"division": "RED", "date": "10/19/2026", "time": "9:00 AM", "field": "Field 1",
         "home": "Mick's Picks", "away": "Jackals", "status": "Scheduled"}; f.update(kw); return f

# ---- normalising ----------------------------------------------------------
check("dates normalise", sheets._norm_game_date("10/09/26") == "10/9/2026" and sheets._norm_game_date("2026-10-19") == "10/19/2026")
check("times normalise", [sheets._norm_game_time(t) for t in ("9am", "9:00 am", "13:30", "10:30AM")] == ["9:00 AM", "9:00 AM", "1:30 PM", "10:30 AM"])
check("junk date/time rejected", sheets._norm_game_date("soon") is None and sheets._norm_game_time("noonish") is None)

# ---- moving a game to Maplewood: only the changed cells are written -------
ok, msg = sheets.update_schedule_game(2, WAS, form(field="Maplewood Park - East Field", time="9am"), "Tom")
check("move to Maplewood East saves", ok, msg)
check("only the Field cell was written (time '9am' is the same as 9:00 AM)", WS.writes == [("D2", "Maplewood Park - East Field")], WS.writes)
check("written the way a person types, so dates stay real dates", WS.raw is False)
check("the change was logged: what, from, to", len(LOG) == 1 and LOG[0][2:5] == ("Field", "Field 1", "Maplewood Park - East Field") and LOG[0][1] == "Jackals vs Mick's Picks (10/19/2026)", LOG)

WS.writes.clear(); LOG.clear()
WAS2 = dict(WAS)
ok, msg = sheets.update_schedule_game(2, WAS2, form(date="10/20/2026", time="10:30 AM", field="Maplewood Park - East Field", away="Knee'd To Win"), "Tom")
check("date, time and team change together", ok and {w[0] for w in WS.writes} == {"B2", "C2", "F2"}, (msg, WS.writes))
check("row now holds the new values", ROWS[1][1:6] == ["10/20/2026", "10:30 AM", "Maplewood Park - East Field", "Mick's Picks", "Knee'd To Win"], ROWS[1])
check("one log line per change", len(LOG) == 3)

# ---- refusals leave the sheet untouched -----------------------------------
snap = [list(r) for r in ROWS]
WS.writes.clear()
def refused(label, *a, **k):
    ok, msg = sheets.update_schedule_game(*a, **k)
    check(label, (not ok) and ROWS == snap and not WS.writes, (ok, msg, WS.writes))
    return msg
refused("stale page (someone changed the game) is refused", 3, dict(WAS, home="Someone Else"), form(), "Tom")
refused("a game with a final score is refused", 4, {"date": "10/14/2026", "time": "9:00 AM", "home": "Jackals", "away": "Mick's Picks"}, form(date="10/14/2026", home="Jackals", away="Mick's Picks"), "Tom")
refused("a team can't play itself", 3, {"date": "10/19/2026", "time": "10:30 AM", "home": "Bad Moon Rising", "away": "Knee'd To Win"}, form(date="10/19/2026", time="10:30 AM", home="Jackals", away="Jackals"), "Tom")
refused("a team from another division / a typo is refused", 3, {"date": "10/19/2026", "time": "10:30 AM", "home": "Bad Moon Rising", "away": "Knee'd To Win"}, form(date="10/19/2026", time="10:30 AM", home="Aces", away="Jackals"), "Tom")
refused("a place not on the Game Fields list is refused", 3, {"date": "10/19/2026", "time": "10:30 AM", "home": "Bad Moon Rising", "away": "Knee'd To Win"}, form(date="10/19/2026", time="10:30 AM", field="Parking Lot", home="Bad Moon Rising", away="Knee'd To Win"), "Tom")
refused("an unreadable date is refused", 3, {"date": "10/19/2026", "time": "10:30 AM", "home": "Bad Moon Rising", "away": "Knee'd To Win"}, form(date="soon", time="10:30 AM"), "Tom")
refused("a header row / missing row is refused", 1, WAS, form(), "Tom")
ok, msg = sheets.update_schedule_game(3, {"date": "10/19/2026", "time": "10:30 AM", "home": "Bad Moon Rising", "away": "Knee'd To Win"}, form(date="10/19/2026", time="10:30 AM", home="Bad Moon Rising", away="Knee'd To Win"), "Tom")
check("saving with nothing changed writes nothing", ok and not WS.writes)

# ---- adding a game uses the first spare row -------------------------------
ok, msg = sheets.add_schedule_game(form(date="11/2/2026", time="10:30 AM", field="Maplewood Park - West Field", home="Jackals", away="Mick's Picks"), "Tom")
check("add goes into the first empty row (row 5)", ok and ROWS[4][:6] == ["RED", "11/2/2026", "10:30 AM", "Maplewood Park - West Field", "Jackals", "Mick's Picks"], (msg, ROWS[4]))
check("the next add uses the next spare row", sheets.add_schedule_game(form(date="11/4/2026", home="Jackals", away="Mick's Picks"), "Tom")[0] and ROWS[5][1] == "11/4/2026")
ok, msg = sheets.add_schedule_game(form(date="11/9/2026"), "Tom")
check("no spare rows left: refused with a plain explanation", (not ok) and "spare rows" in msg, msg)

# ---- password and pages ---------------------------------------------------
import app as appmod
PW = ["sunshine"]
sheets.schedule_password = lambda: PW[0]
sheets.schedule_editor_games = lambda: [dict(row=i + 1, division=ROWS[i][0], date=ROWS[i][1], time=ROWS[i][2], field=ROWS[i][3],
    home=ROWS[i][4], away=ROWS[i][5], score_home=ROWS[i][6], score_away=ROWS[i][7], status=ROWS[i][8],
    played=bool(ROWS[i][6] != "" and ROWS[i][7] != "")) for i in range(1, len(ROWS)) if ROWS[i][4]]
sheets.schedule_change_log = lambda limit=25: [{"date": "2026-10-09", "time": "1:00 PM", "division": "RED", "game": "x", "what": "Field", "from": "Field 1", "to": "Maplewood Park - East Field", "by": "Tom"}]
c = appmod.app.test_client()
check("not signed in -> sent to login", c.get("/admin/schedule").status_code == 302 and "/admin/login" in c.get("/admin/schedule").headers["Location"])
with c.session_transaction() as s: s["admin"] = True
r = c.get("/admin/schedule")
check("portal sign-in alone is not enough: asks for the Schedule Password", r.status_code == 302 and "/admin/schedule/unlock" in r.headers["Location"])
for path in ("/admin/schedule/save", "/admin/schedule/add"):
    check("POST %s is locked too" % path, c.post(path, data={}).status_code == 302 and "unlock" in c.post(path, data={}).headers["Location"])
check("wrong password refused", "Incorrect password" in c.post("/admin/schedule/unlock", data={"password": "nope"}).get_data(as_text=True))
PW[0] = ""
check("no Schedule Password set: stays locked and explains how to set one", "Schedule Password" in c.get("/admin/schedule/unlock").get_data(as_text=True) and c.post("/admin/schedule/unlock", data={"password": ""}).status_code == 200)
PW[0] = "sunshine"
r = c.post("/admin/schedule/unlock?next=https://evil.example/x", data={"password": " Sunshine "})
check("right password unlocks; an outside 'next' address is ignored", r.status_code == 302 and r.headers["Location"].endswith("/admin/schedule"), r.headers.get("Location"))
page = c.get("/admin/schedule?division=RED").get_data(as_text=True)
check("page lists the games, the four fields and both Maplewood fields", all(t in page for t in ("Field 4", "Maplewood Park - East Field", "Maplewood Park - West Field", "Mick&#39;s Picks")))
check("a scored game is shown read-only", "Final" in page and "can't be edited here" in page)
check("recent changes are shown", "Recent schedule changes" in page and "Tom" in page)
check("add-a-game box is there", "Add a game" in page)
sent = {}
sheets.update_schedule_game = lambda row, exp, f, by: sent.update(row=row, exp=exp, by=by, f=dict(f)) or (True, "Saved.")
r = c.post("/admin/schedule/save", data=dict(form(field="Maplewood Park - East Field"), row="2", changed_by="Tom", was_date="10/19/2026", was_time="9:00 AM", was_home="Mick's Picks", was_away="Jackals"))
check("save passes the row, what the page showed, and who changed it", sent.get("row") == "2" and sent["exp"]["home"] == "Mick's Picks" and sent["by"] == "Tom", sent)
check("save redirects back to the same division with a message", r.status_code == 302 and "division=RED" in r.headers["Location"] and "saved=" in r.headers["Location"])
check("the editor remembers the name for next time", "value=\"Tom\"" in c.get("/admin/schedule").get_data(as_text=True))
sheets.is_configured = lambda: True; sheets.list_notices = lambda: []; sheets.get_portal_links = lambda: []
check("dashboard links to the editor", "Edit Schedule" in c.get("/admin").get_data(as_text=True))

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

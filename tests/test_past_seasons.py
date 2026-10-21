"""Past Seasons archive: saving, refreshing, keeping seasons apart, rebuilding
standings, the public page and the admin page. Fake sheet; never touches Google."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import gspread
import sheets

class FakeWS:
    def __init__(self, title, ncols):
        self.title, self.rows, self.row_count, self.col_count = title, [], 200, ncols
        self.updates = 0
    def get_all_values(self): return [list(r) for r in self.rows]
    def resize(self, rows=None, cols=None):
        self.row_count = rows or self.row_count; self.col_count = cols or self.col_count
    def update(self, values, rng, value_input_option=None):
        assert rng == "A1" and len(values) <= self.row_count
        self.updates += 1
        self.rows = [list(r) for r in values]

class FakeSheet:
    def __init__(self): self.tabs = {}
    def worksheet(self, t):
        if t not in self.tabs: raise gspread.WorksheetNotFound(t)
        return self.tabs[t]
    def add_worksheet(self, title, rows, cols):
        self.tabs[title] = FakeWS(title, cols); return self.tabs[title]

SH = FakeSheet()
sheets.CONTROL_SHEET_ID, sheets._SA_JSON = "x", "{}"
sheets._control_sheet = lambda readonly=True: SH

def game(date, time_, home, away, sh="", sa=""):
    return {"division": "RED", "date": date, "dow": "", "time": time_, "field": "Field 1",
            "home": home, "away": away, "score_home": sh, "score_away": sa,
            "status": "Final" if sh != "" else "Scheduled"}

LIVE = {"schedule": [
    game("10/19/2026", "10:30 AM", "Bad Moon Rising", "Knee'd To Win", "7", "3"),
    game("10/19/2026", "9:00 AM", "Mick's Picks", "Jackals", "4", "9"),
    game("10/21/2026", "9:00 AM", "Mick's Picks", "Knee'd To Win"),
    game("9/30/2026", "9:00 AM", "Jackals", "Bad Moon Rising", "5", "5")],
    "rosters": {"RED": [{"team": "Jackals", "players": [
        {"name": "Zed Young", "position": "SS", "is_manager": False},
        {"name": "Al Baker", "position": "", "is_manager": True}]}],
        "WHITE": [], "BLUE": []}}

def fake_live():
    sheets._season_cache["ts"] = time.time()
    LIVE.setdefault("results", []); LIVE.setdefault("standings", {}); LIVE.setdefault("teams", {})
    return LIVE
sheets.league_season = fake_live

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

# ---- saving ---------------------------------------------------------------
r = sheets.archive_current_season("  Fall   2026 ")
check("counts reported", r == {"games": 4, "scored": 3, "players": 2, "teams": 1}, r)
sch = SH.tabs["Archive Schedule"].rows
check("headers written first", sch[0] == sheets.ARCHIVE_SCHEDULE_HEADERS)
check("season name tidied and stamped", all(x[0] == "Fall 2026" for x in sch[1:]) and len(sch) == 5)
check("scores kept as typed", ["7", "3"] == sch[1][7:9])

# ---- refresh does not duplicate; other seasons survive -------------------
LIVE2 = dict(LIVE)
sheets.archive_current_season("Winter 2027")
LIVE["schedule"][2]["score_home"], LIVE["schedule"][2]["score_away"] = "6", "2"
sheets.archive_current_season("fall 2026")           # different case, same season
sch = SH.tabs["Archive Schedule"].rows
check("refresh leaves one copy per game", len([x for x in sch[1:] if x[0].lower() == "fall 2026"]) == 4, len(sch))
check("other season untouched", len([x for x in sch[1:] if x[0] == "Winter 2027"]) == 4)
check("refreshed score picked up", any(x[0] == "Fall 2026" and x[7:9] == ["6", "2"] for x in sch))

# ---- reading back ---------------------------------------------------------
sheets._archive_invalidate()
names = [s["name"] for s in sheets.archived_seasons()]
check("newest season first", names == ["Winter 2027", "Fall 2026"], names)
fall = sheets.archived_season("FALL 2026")
check("lookup ignores case", fall and fall["name"] == "Fall 2026")
check("games in date/time order", [g["date"] + " " + g["time"] for g in fall["schedule"]][:3] ==
      ["9/30/2026 9:00 AM", "10/19/2026 9:00 AM", "10/19/2026 10:30 AM"], [g["date"] for g in fall["schedule"]])
st = {t["team"]: t for t in fall["standings"]["RED"]}
check("standings rebuilt from archived scores", st["Jackals"]["wins"] == 1 and st["Jackals"]["losses"] == 0
      and st["Bad Moon Rising"]["wins"] == 1, st)
roster = fall["rosters"]["RED"][0]
check("roster + manager preserved", roster["team"] == "Jackals" and roster["manager"] == "Al Baker"
      and [p["name"] for p in roster["players"]] == ["Al Baker", "Zed Young"], roster)
check("unknown season is None", sheets.archived_season("Spring 1999") is None)

# ---- the live pages can never mistake an archive tab for a live one ------
tabs = [(t, w.get_all_values()) for t, w in SH.tabs.items()]
for need in (["home team", "away team", "status"], ["team name", "player first name", "player last name"],
             ["team", "wins", "losses"], ["result"]):
    check("live lookup ignores archive tabs %s" % need[0], sheets._match_tab(tabs, need)[0] is None)

# ---- guards ---------------------------------------------------------------
for bad, why in (("", "blank name"), ("x" * 41, "long name")):
    try: sheets.archive_current_season(bad); ok = False
    except ValueError: ok = True
    check("refuses " + why, ok)
LIVE_BACKUP = dict(LIVE)
LIVE.update(schedule=[], rosters={"RED": [], "WHITE": [], "BLUE": []})
before = [list(r) for r in SH.tabs["Archive Schedule"].rows]
try: sheets.archive_current_season("Empty"); ok = False
except ValueError: ok = True
check("refuses to save an empty sheet, writes nothing", ok and SH.tabs["Archive Schedule"].rows == before)
LIVE.update(LIVE_BACKUP)
sheets.league_season = lambda: LIVE          # cache not refreshed => read failed
sheets._season_cache["ts"] = 0.0
try: sheets.archive_current_season("Stale"); ok = False
except ValueError: ok = True
check("refuses when the live read silently failed", ok)
sheets.league_season = fake_live

# ---- delete ---------------------------------------------------------------
sheets.delete_archived_season("Winter 2027")
sheets._archive_invalidate()
check("delete removes only that season", [s["name"] for s in sheets.archived_seasons()] == ["Fall 2026"])
check("deleted rows are blanked, not left behind",
      all(not any(r) or r[0] == "Fall 2026" for r in SH.tabs["Archive Schedule"].rows[1:]))

# ---- web pages ------------------------------------------------------------
import app as appmod
c = appmod.app.test_client()
check("past seasons page is public", c.get("/league/past-seasons").status_code == 200)
html = c.get("/league/past-seasons?season=Fall%202026").get_data(as_text=True)
check("refresh keeps the original spelling", "fall 2026" not in [s["name"] for s in sheets.archived_seasons()])
check("page shows teams, scores and manager", all(t in html for t in
      ("Fall 2026", "Bad Moon Rising", "Final Standings", "Al Baker", "Manager")))
check("unknown season is a 404", c.get("/league/past-seasons?season=Nope").status_code == 404)
check("menu links to it", "/league/past-seasons" in c.get("/league/schedules").get_data(as_text=True))
check("admin page needs login", c.get("/admin/archive").status_code == 302)
check("admin save needs login", c.post("/admin/archive/save", data={"season": "X"}).status_code == 302)
with c.session_transaction() as s: s["admin"] = True
a = c.get("/admin/archive").get_data(as_text=True)
check("admin page lists saved season", "Fall 2026" in a and "Save this season" in a)
resp = c.post("/admin/archive/save", data={"season": "Winter 2027"})
check("admin save redirects with a success message", resp.status_code == 302 and "saved" in resp.headers["Location"], resp.headers.get("Location"))
sheets._archive_invalidate()
check("saved from the admin page", "Winter 2027" in [s["name"] for s in sheets.archived_seasons()])
resp = c.post("/admin/archive/save", data={"season": ""})
check("blank name explains itself", "problem=" in resp.headers["Location"])

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

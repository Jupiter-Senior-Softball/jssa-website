"""Correcting / clearing a final score: writes the right cells, logs old -> new
with who did it, and the pages offer the buttons. Fake sheet; never touches Google."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

HEAD = ["Division", "Date", "Time", "Field", "Home Team", "Away Team", "Score Home", "Score Away", "Status"]
ROWS = [list(HEAD),
        ["RED", "10/14/2026", "9:00 AM", "Field 1", "Jackals", "Mick's Picks", "7", "3", "Final"],
        ["RED", "10/19/2026", "9:00 AM", "Field 1", "Mick's Picks", "Jackals", "", "", "Scheduled"]]
class WS:
    def batch_update(self, data, **kw):
        for d in data:
            a1 = d["range"]; col = ord(re.match(r"[A-Z]+", a1).group(0)) - 65; row = int(re.search(r"\d+", a1).group(0))
            ROWS[row - 1][col] = d["values"][0][0]
class SH:
    def worksheet(self, t): return WS()
sheets._control_sheet = lambda readonly=True: SH()
sheets._control_tabs = lambda sh: [("Schedule", ROWS)]
sheets.CONTROL_SHEET_ID, sheets._SA_JSON = "x", "{}"
LOG = []
sheets._log_schedule_change = lambda *a: LOG.append(a)

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

check("correcting a score writes it", sheets.set_game_score(2, "8", "3", changed_by="Tom") and ROWS[1][6:9] == ["8", "3", "Final"], ROWS[1])
check("the correction is logged old -> new with who", LOG[-1][2:] == ("Score (home–away)", "7–3", "8–3", "Tom") and "Mick's Picks at Jackals" in LOG[-1][1], LOG)
n = len(LOG)
sheets.set_game_score(2, "8", "3", changed_by="Tom")
check("saving the same score again logs nothing", len(LOG) == n)
sheets.set_game_score(3, "5", "4", changed_by="")
check("a first-time score is logged too (name falls back)", LOG[-1][3:] == ("no score", "5–4", "Board member"), LOG[-1])
check("clearing blanks both scores and resets to Scheduled", sheets.clear_game_score(2, "Tom") and ROWS[1][6:9] == ["", "", "Scheduled"], ROWS[1])
check("clearing is logged", LOG[-1][2:] == ("Score cleared", "8–3", "no score", "Tom"), LOG[-1])
n = len(LOG)
sheets.set_game_score(3, "5", "4", status="Cancelled")
check("callers that pass no name (game-day cancel) log nothing", len(LOG) == n)

import app as appmod
c = appmod.app.test_client()
calls = []
sheets.set_game_score = lambda row, h, a, status="Final", changed_by=None: calls.append(("set", row, h, a, changed_by)) or True
sheets.clear_game_score = lambda row, by: calls.append(("clear", row, by)) or True
sheets.schedule_games_for_scoring = lambda: [
    dict(row=2, division="RED", date="10/14/2026", time="9:00 AM", field="Field 1", home="Jackals", away="Mick's Picks", score_home="7", score_away="3", status="Final"),
    dict(row=3, division="RED", date="10/19/2026", time="9:00 AM", field="Field 1", home="Mick's Picks", away="Jackals", score_home="", score_away="", status="Scheduled")]
check("scores save needs sign-in", c.post("/admin/scores/clear", data={"row": "2"}).status_code == 302 and "/admin/login" in c.post("/admin/scores/clear", data={"row": "2"}).headers["Location"])
with c.session_transaction() as s: s["admin"] = True
page = c.get("/admin/scores?division=RED").get_data(as_text=True)
check("finished game offers Update and Clear score; unscored game only Save", page.count("Clear score</button>") == 1 and "Update" in page and "Save score" in page)
c.post("/admin/scores/save", data={"row": "2", "division": "RED", "score_home": "8", "score_away": "3", "changed_by": "Tom"})
check("save passes the name", calls[-1] == ("set", 2, "8", "3", "Tom"), calls)
r = c.post("/admin/scores/clear", data={"row": "2", "division": "RED", "changed_by": "Tom"})
check("clear calls clear_game_score and shows the cleared message", calls[-1] == ("clear", 2, "Tom") and "saved=2" in r.headers["Location"], calls)
check("cleared message displays", "Score cleared" in c.get("/admin/scores?division=RED&saved=2").get_data(as_text=True))
check("name is remembered for next time", 'value="Tom"' in c.get("/admin/scores?division=RED").get_data(as_text=True))
sheets.schedule_editor_games = lambda: [dict(sheets.schedule_games_for_scoring()[0], played=True, umpire1="", umpire2="")]
sheets.schedule_team_options = lambda: {"RED": ["Jackals"], "WHITE": [], "BLUE": []}
sheets.umpire_options = lambda: {"RED": [], "WHITE": [], "BLUE": []}
sheets.game_field_options = lambda: ["Field 1"]; sheets.schedule_change_log = lambda limit=25: []
check("Edit Schedule links finished games to the score correction page", "Correct this score" in c.get("/admin/schedule?division=RED").get_data(as_text=True))
print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

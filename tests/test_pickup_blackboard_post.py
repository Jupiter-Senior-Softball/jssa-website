"""The pickup-games sign-up card is an ordinary Blackboard post the board can
switch off and on. Fake sheet; never touches Google."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

H = sheets.BB_HEADERS
class WS:
    def __init__(self, rows=(), broken=False):
        self.rows = [list(r) for r in rows]; self.broken = broken
    def get_all_records(self, expected_headers=None):
        return [dict(zip(H, r)) for r in self.rows]
    def append_row(self, row, value_input_option=None):
        if self.broken: raise RuntimeError("sheet is read-only right now")
        self.rows.append(list(row))
    def update_cell(self, r, c, v): self.rows[r - 2][c - 1] = v
    def delete_rows(self, r): del self.rows[r - 2]

sheets.is_configured = lambda: True
def use(ws):
    sheets._bb_worksheet = lambda: ws
    sheets._bb_cache.update(data=None, ts=0.0)
    return ws
def live():
    sheets._bb_cache.update(data=None, ts=0.0)
    return [p["title"] for p in sheets.blackboard_posts()]

PICKUP = "Sign up for the legendary pickup games"
OTHER = ["ab12", "", "Baseball cards", "Upload your photo", "", "", "", "", "left", "TRUE", 3]

ws = use(WS([OTHER]))
check("first read adds the pickup post, below the board's own posts",
      live() == ["Baseball cards", PICKUP], live())
check("it is written to the sheet once, not on every read",
      live() and [r[0] for r in ws.rows] == ["ab12", sheets.PICKUP_POST_ID], ws.rows)
p = [x for x in sheets.blackboard_posts() if x["title"] == PICKUP][0]
check("it keeps its photo, side, label and sign-up link",
      p["image"] == "/static/pickup-games-signup.jpg" and p["side"] == "right"
      and p["when"].startswith("Pickup Games") and p["link_text"] == "Sign up now"
      and p["link_url"].startswith("https://script.google.com/"), p)
check("the photo file is really there",
      os.path.exists(os.path.join(os.path.dirname(os.path.abspath(sheets.__file__)), "static", "pickup-games-signup.jpg")))

sheets.set_bb_active(sheets.PICKUP_POST_ID, False)
check("Turn off hides it and it stays hidden", live() == ["Baseball cards"] and live() == ["Baseball cards"], live())
check("...without adding a second row", len(ws.rows) == 2, ws.rows)
sheets.set_bb_active(sheets.PICKUP_POST_ID, True)
check("Turn on brings it back", live() == ["Baseball cards", PICKUP], live())

sheets.update_bb_post(sheets.PICKUP_POST_ID, {"title": "Pickup is back!", "body": "See you there", "side": "right"})
check("the board can edit its wording", live() == ["Baseball cards", "Pickup is back!"], live())

sheets.delete_bb_post(sheets.PICKUP_POST_ID)
check("Delete only turns it off (so it can't spring back on)",
      len(ws.rows) == 2 and live() == ["Baseball cards"], (ws.rows, live()))
sheets.delete_bb_post("ab12")
check("other posts still delete normally", [r[0] for r in ws.rows] == [sheets.PICKUP_POST_ID], ws.rows)

ws = use(WS([], broken=True))
check("if the row can't be written yet, the card still shows", live() == [PICKUP], live())
check("the admin list shows it too", [r["id"] for r in sheets.list_bb_posts()] == [sheets.PICKUP_POST_ID])

dup = [sheets.PICKUP_POST[h] for h in H]
off = list(dup); off[H.index("active")] = "FALSE"
use(WS([off, dup]))
check("a doubled-up row never overrules the switch", live() == [], live())

# The pages themselves
os.environ.setdefault("ADMIN_PASSWORD", "test-pw")
import app as site
use(WS([OTHER]))
c = site.app.test_client()
html = c.get("/").get_data(as_text=True)
check("homepage carries the pickup post and no built-in copy",
      html.count(PICKUP) == 1 and 'id="jssa-blackboard"' in html, html.count(PICKUP))
check("homepage no longer embeds the photo", "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBAUEBAYFBQUG" not in html)
ws = use(WS([[sheets.PICKUP_POST[h] if h != "active" else "FALSE" for h in H]]))
html = c.get("/").get_data(as_text=True)
check("with every post off, the Blackboard section is left out", 'id="bb-grid"' not in html and PICKUP not in html)

print("\n%d failed" % len(fails) if fails else "\nAll passed")
sys.exit(1 if fails else 0)

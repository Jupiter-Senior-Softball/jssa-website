"""Blackboard posts are reordered with Move up / Move down in the admin, and the
admin list is in the same order as the homepage. Fake sheet; never touches Google."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % (extra,)))
    if not cond: fails.append(label)

H = sheets.BB_HEADERS
class WS:
    def __init__(self, rows): self.rows = [list(r) for r in rows]; self.writes = 0
    def get_all_records(self, expected_headers=None): return [dict(zip(H, r)) for r in self.rows]
    def append_row(self, row, value_input_option=None): self.rows.append(list(row))
    def update_cell(self, r, c, v): self.rows[r - 2][c - 1] = v; self.writes += 1
    def delete_rows(self, r): del self.rows[r - 2]

def post(pid, title, order, active="TRUE"):
    return [pid, "", title, "text", "", "", "", "", "left", active, order]
PK = sheets.PICKUP_POST_ID
sheets.is_configured = lambda: True
def use(rows):
    ws = WS(rows); sheets._bb_worksheet = lambda: ws
    sheets._bb_cache.update(data=None, ts=0.0); return ws
def home():
    sheets._bb_cache.update(data=None, ts=0.0)
    return [p["title"] for p in sheets.blackboard_posts() if p["title"] != AUTO]
def admin(): return [p["title"] for p in sheets.list_bb_posts() if p["title"] != AUTO]
AUTO = sheets.PICKUP_POST["title"]   # the site adds this post itself when it's missing

# The sheet as it is today: pickup 0, cards 1, membership 3.
ws = use([post(PK, "Pickup", 0), post("c", "Cards", 1), post("m", "Membership", 3)])
check("admin list is in homepage order", admin() == home() == ["Membership", "Cards", "Pickup"], (admin(), home()))

check("move up reports it moved", sheets.move_bb_post(PK, "up") is True)
check("pickup moved up one place", home() == ["Membership", "Pickup", "Cards"] == admin(), home())
sheets.move_bb_post(PK, "up")
check("...and again, to the top", home() == ["Pickup", "Membership", "Cards"], home())
check("orders are now a clean 3-2-1", sorted(r[-1] for r in ws.rows) == [1, 2, 3], ws.rows)
n = ws.writes
check("moving the top post up does nothing", sheets.move_bb_post(PK, "up") is False and ws.writes == n)
check("moving the bottom post down does nothing", sheets.move_bb_post("c", "down") is False and ws.writes == n)
check("an unknown post does nothing", sheets.move_bb_post("nope", "up") is False and ws.writes == n)
sheets.move_bb_post(PK, "down")
check("move down works", home() == ["Membership", "Pickup", "Cards"], home())
check("a swap of neighbours writes just the two rows", ws.writes == n + 2, ws.writes - n)

ws = use([post("a", "A", 5), post("b", "B", 5), post("c", "C", 5)])
check("posts sharing a number: list and homepage still agree", admin() == home() == ["A", "B", "C"], (admin(), home()))
sheets.move_bb_post("c", "up")
check("...and can be moved apart", home() == ["A", "C", "B"] == admin(), home())

ws = use([post("a", "A", 3), post("off", "Hidden", 2, "FALSE"), post("b", "B", 1)])
sheets.move_bb_post("b", "up")
check("a turned-off post keeps a place in the list", admin() == ["A", "B", "Hidden"] and home() == ["A", "B"], (admin(), home()))
sheets.add_bb_post({"title": "Brand new", "body": "x"})
check("a new post starts at the top", admin()[0] == "Brand new" == home()[0], admin())

# The page
import app as site
site.app.before_request(lambda: site.session.__setitem__("admin", True))
c = site.app.test_client()
ws = use([post(PK, "Pickup", 0), post("c", "Cards", 1), post("m", "Membership", 3)])
html = c.get("/admin/blackboard").get_data(as_text=True)
check("page lists posts in homepage order", html.index("Membership") < html.index("Cards") < html.index(">Pickup<"))
check("top post has no Move up, bottom has no Move down",
      html.count("Move up</button>") == 2 and html.count("Move down</button>") == 2,
      (html.count("Move up</button>"), html.count("Move down</button>")))
check("the wrong 'lowest first' note is gone", "lowest first" not in html)
r = c.post("/admin/blackboard/%s/move" % PK, data={"direction": "up"})
check("the Move up button works and returns to the list",
      r.status_code == 302 and r.headers["Location"].endswith("/admin/blackboard#posts")
      and home() == ["Membership", "Pickup", "Cards"], (r.status_code, home()))
site.app.before_request_funcs[None].clear()
r = site.app.test_client().post("/admin/blackboard/%s/move" % PK, data={"direction": "up"})
check("moving needs a sign-in", r.status_code == 302 and "login" in r.headers["Location"]
      and home() == ["Membership", "Pickup", "Cards"], r.headers.get("Location"))

print("\n%d failed" % len(fails) if fails else "\nAll passed")
sys.exit(1 if fails else 0)

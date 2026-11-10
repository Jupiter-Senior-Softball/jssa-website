"""Announcements turn themselves off after a number of hours: the default comes
from the Site Settings tab, and the poster can change it. Fake sheet only."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "t"; os.environ["ADMIN_PASSWORD"] = "t"
import sheets

UTC = dt.timezone.utc
fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % (extra,)))
    if not cond: fails.append(label)

SETTINGS = {}
sheets._site_settings = lambda: dict(SETTINGS)
sheets._website_controls = lambda: {}
NOW = dt.datetime(2026, 11, 10, 15, 0, tzinfo=UTC)

# ---- the default -----------------------------------------------------------
check("no setting row: 48 hours", sheets.default_announcement_hours() == 48)
SETTINGS["announcementhours"] = "72"
check("Site Settings row wins", sheets.default_announcement_hours() == 72)
SETTINGS["announcementhours"] = "36 hours"
check("'36 hours' reads as 36", sheets.default_announcement_hours() == 36)
for bad in ("soon", "0", "-5", "999999"):
    SETTINGS["announcementhours"] = bad
    check("bad setting %r falls back to 48" % bad, sheets.default_announcement_hours() == 48)
SETTINGS["announcementhours"] = "72"

# ---- the turn-off time -----------------------------------------------------
check("blank hours = the default", sheets.announcement_expiry("", now=NOW) == "2026-11-13T15:00:00Z")
check("poster's own hours are used", sheets.announcement_expiry("6", now=NOW) == "2026-11-10T21:00:00Z")
check("half hours work", sheets.announcement_expiry("1.5", now=NOW) == "2026-11-10T16:30:00Z")
check("garbage hours = the default", sheets.announcement_expiry("lots", now=NOW) == "2026-11-13T15:00:00Z")
rec = {"expires_at": sheets.announcement_expiry("6", now=NOW)}
check("still up before the time", not sheets.notice_expired(rec, now=NOW + dt.timedelta(hours=5, minutes=59)))
check("off once the hours are up", sheets.notice_expired(rec, now=NOW + dt.timedelta(hours=6)))
check("label carries the date", sheets.notice_shutoff_info(
      {"expires_at": "2026-11-13T15:00:00Z"})["when"] == "Fri, Nov 13 at 10:00 AM")

# ---- changing it afterwards / turning back on ------------------------------
class FakeWS:
    def __init__(self): self.cells = {}
    def get_all_records(self, expected_headers=None): return [dict(r) for r in ROWS]
    def update_cell(self, row, col, val): self.cells[(row, col)] = val
ROWS = [{"id": "w", "type": "weather", "active": "FALSE", "expires_at": "2026-10-23T17:00:00Z"},
        {"id": "a", "type": "announcement", "active": "FALSE", "expires_at": "2026-11-01T00:00:00Z"}]
ws = FakeWS(); sheets._worksheet = lambda: ws
col = sheets.HEADERS.index("expires_at") + 1
check("new hours restart the countdown from now",
      sheets.set_announcement_hours("a", "12", now=NOW) and ws.cells == {(3, col): "2026-11-11T03:00:00Z"}, ws.cells)
ws.cells.clear()
check("bad hours are refused and write nothing",
      not sheets.set_announcement_hours("a", "never", now=NOW) and ws.cells == {})
sheets.set_active("a", True)
exp = sheets._parse_expiry(ws.cells.get((3, col)))
left = (exp - dt.datetime.now(UTC)).total_seconds() / 3600 if exp else 0
check("an announcement turned back on gets a fresh default countdown", 71.9 < left <= 72, left)
ws.cells.clear(); sheets.set_active("w", True)
check("a weather banner turned back on is unchanged (shutoff cleared)", ws.cells.get((2, col)) == "")

# ---- admin page ------------------------------------------------------------
import app as appmod
sheets.is_configured = lambda: True
sheets.list_notices = lambda: [
    {"id": "a", "type": "announcement", "message": "Picnic", "active": "TRUE",
     "created_by": "Tom", "expires_at": "2099-01-02T15:00:00Z"},
    {"id": "old", "type": "announcement", "message": "Old one", "active": "TRUE",
     "created_by": "Tom", "expires_at": ""}]
sheets.get_portal_links = lambda: []
sheets.home_view_count = lambda: 0
c = appmod.app.test_client()
with c.session_transaction() as s: s["admin"] = True
page = c.get("/admin").get_data(as_text=True)
check("form shows the hours box filled with the default", 'name="hours" value="72"' in page)
check("list says when it turns itself off", "It turns itself off on" in page and "Jan 2 at 10:00 AM" in page)
check("older posts with no time say so", "No automatic turn-off" in page)
added = []
sheets.add_notice = lambda *a, **k: added.append((a, k))
c.post("/admin/notices/add", data={"message": "Banquet Friday", "hours": "6"})
exp = sheets._parse_expiry(added[0][1]["expires_at"])
left = (exp - dt.datetime.now(UTC)).total_seconds() / 3600
check("posting uses the hours typed on the form", 5.9 < left <= 6, left)
added.clear()
c.post("/admin/notices/add", data={"message": "Banquet Friday"})
exp = sheets._parse_expiry(added[0][1]["expires_at"])
left = (exp - dt.datetime.now(UTC)).total_seconds() / 3600
check("posting with no hours still turns off, at the default", 71.9 < left <= 72, left)
calls = []
sheets.set_announcement_hours = lambda nid, h: calls.append((nid, h)) or True
r = c.post("/admin/notices/a/hours", data={"hours": "24"})
check("change-hours route works", r.status_code == 302 and calls == [("a", "24")])
check("change-hours route needs login",
      appmod.app.test_client().post("/admin/notices/a/hours", data={"hours": "1"}).status_code == 302
      and len(calls) == 1)

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

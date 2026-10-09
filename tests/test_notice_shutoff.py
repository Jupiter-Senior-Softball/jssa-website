"""Weather banners come down by themselves at a set time (default 1:00 PM
Eastern), and the poster can change that time. Fake sheet; never touches Google."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

UTC = dt.timezone.utc
def at(y, mo, d, h, mi):      # a New York wall-clock time as an aware datetime
    return dt.datetime(y, mo, d, h, mi, tzinfo=sheets._notice_tz())

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

# ---- shutoff time for a new post -----------------------------------------
iso, fb = sheets.shutoff_for_new_post("", now=at(2026, 10, 23, 7, 30))
check("default is 1:00 PM Eastern same day", sheets.notice_shutoff_info({"expires_at": iso})["label"] == "1:00 PM" and not fb, iso)
iso, fb = sheets.shutoff_for_new_post("15:30", now=at(2026, 10, 23, 7, 30))
check("poster's own time is used", sheets.notice_shutoff_info({"expires_at": iso})["label"] == "3:30 PM")
iso, fb = sheets.shutoff_for_new_post("13:00", now=at(2026, 10, 23, 14, 0))
check("posted after the shutoff: stays up until 11:59 PM tonight", fb and
      sheets.notice_shutoff_info({"expires_at": iso})["label"] == "11:59 PM")
iso, fb = sheets.shutoff_for_new_post("garbage", now=at(2026, 10, 23, 7, 0))
check("unreadable time falls back to the default", sheets.notice_shutoff_info({"expires_at": iso})["label"] == "1:00 PM")
iso, _ = sheets.shutoff_for_new_post("", now=at(2026, 12, 1, 7, 0))      # standard time
check("correct in winter (EST) too", sheets.notice_shutoff_info({"expires_at": iso})["label"] == "1:00 PM")
check("1:00 PM EDT is 17:00 UTC", sheets.shutoff_for_new_post("", now=at(2026, 10, 23, 7, 0))[0] == "2026-10-23T17:00:00Z")

# ---- expiry ---------------------------------------------------------------
rec = {"expires_at": "2026-10-23T17:00:00Z"}
check("before the time: still showing", not sheets.notice_expired(rec, now=dt.datetime(2026, 10, 23, 16, 59, tzinfo=UTC)))
check("at the time: gone", sheets.notice_expired(rec, now=dt.datetime(2026, 10, 23, 17, 0, tzinfo=UTC)))
check("no expiry (older posts) never expires", not sheets.notice_expired({"expires_at": ""}) and not sheets.notice_expired({}))
check("garbage expiry never hides a notice", not sheets.notice_expired({"expires_at": "soon"}))

# ---- what the site shows --------------------------------------------------
NOW = [dt.datetime(2026, 10, 23, 12, 0, tzinfo=UTC)]
class FakeDT(dt.datetime):
    @classmethod
    def now(cls, tz=None): return NOW[0]
sheets.datetime = type("M", (), {"datetime": FakeDT, "timezone": dt.timezone, "timedelta": dt.timedelta, "date": dt.date})
sheets.is_configured = lambda: True
RECS = [
    {"id": "a", "type": "announcement", "message": "Picnic Saturday", "active": "TRUE", "expires_at": ""},
    {"id": "w", "type": "weather", "message": "CANCELLED — no games today", "active": "TRUE", "expires_at": "2026-10-23T17:00:00Z"},
]
sheets.list_notices = lambda: list(reversed(RECS))
def shown():
    sheets._cache.update(notice=None, ts=0.0)
    n = sheets.active_notice()
    return n["message"] if n else None
check("morning: the cancellation shows", shown() == "CANCELLED — no games today")
NOW[0] = dt.datetime(2026, 10, 23, 17, 5, tzinfo=UTC)
sheets._cache["ts"] = 10**12   # cache still 'fresh': must still drop at the shutoff
sheets._cache["notice"] = {"message": "CANCELLED — no games today", "expires_at": "2026-10-23T17:00:00Z"}
check("a cached cancellation disappears at the shutoff without waiting for a refresh", sheets.active_notice() is None)
check("after 1 PM the normal announcement returns", shown() == "Picnic Saturday")
RECS[1]["active"] = "FALSE"
NOW[0] = dt.datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
check("turned off by hand still works", shown() == "Picnic Saturday")

# ---- editing / turning back on -------------------------------------------
class FakeWS:
    def __init__(self): self.cells = {}
    def get_all_records(self, expected_headers=None): return [dict(r) for r in ROWS]
    def update_cell(self, row, col, val): self.cells[(row, col)] = val
ROWS = [{"id": "w", "type": "weather", "active": "TRUE", "created_at": "2026-10-23T11:30:00Z",
         "expires_at": "2026-10-23T17:00:00Z"}]
ws = FakeWS(); sheets._worksheet = lambda: ws
col = sheets.HEADERS.index("expires_at") + 1
check("change time writes the new UTC time", sheets.set_notice_shutoff("w", "15:00") and ws.cells[(2, col)] == "2026-10-23T19:00:00Z", ws.cells)
check("blank removes the automatic shutoff", sheets.set_notice_shutoff("w", "") and ws.cells[(2, col)] == "")
check("a bad time is refused and writes nothing", not sheets.set_notice_shutoff("w", "tea time") and ws.cells[(2, col)] == "")
ws.cells.clear()
sheets.set_active("w", True)
check("turning a notice back on clears its old shutoff", ws.cells.get((2, col)) == "")
check("expires_at is the LAST column (existing rows stay aligned)", sheets.HEADERS[-1] == "expires_at")

# ---- admin pages ----------------------------------------------------------
import importlib; importlib.reload  # noqa
import app as appmod
c = appmod.app.test_client()
with c.session_transaction() as s: s["admin"] = True
page = c.get("/admin/cancel").get_data(as_text=True)
check("cancel form has the shutoff box defaulting to 13:00", 'name="shutoff"' in page and 'value="13:00"' in page)
seen = {}
sheets.send_cancellation = lambda *a, **k: seen.update(k) or {"ok": True, "emailed": 0, "missed": [], "banner": True, "note": ""}
c.post("/admin/cancel/send", data={"confirm": "CANCEL", "reason": "rain", "shutoff": "14:15"})
check("the chosen time reaches the sender", seen.get("shutoff") == "14:15", seen)
set_calls = []
sheets.set_notice_shutoff = lambda nid, t: set_calls.append((nid, t)) or True
r = c.post("/admin/notices/w/shutoff", data={"shutoff": "12:00"})
check("dashboard change-time route works", r.status_code == 302 and set_calls == [("w", "12:00")])
check("change-time route needs login", appmod.app.test_client().post("/admin/notices/w/shutoff", data={}).status_code == 302)

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

"""The homepage banner can slide through several notices. Fake sheet; never touches Google."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

sheets.is_configured = lambda: True
RECS = [  # list_notices() is newest first
    {"id": "3", "type": "announcement", "message": "Newest note", "active": "TRUE", "expires_at": ""},
    {"id": "2", "type": "weather", "message": "CANCELLED today", "active": "TRUE", "expires_at": ""},
    {"id": "1", "type": "announcement", "message": "Older note", "active": "TRUE", "expires_at": ""},
    {"id": "0", "type": "announcement", "message": "Switched off", "active": "FALSE", "expires_at": ""},
    {"id": "x", "type": "announcement", "message": "   ", "active": "TRUE", "expires_at": ""},
]
sheets.list_notices = lambda: list(RECS)
def fresh():
    sheets._cache.update(notices=[], ts=0.0)
    return [n["message"] for n in sheets.active_notices()]

check("weather first, then newest announcements; off/blank skipped",
      fresh() == ["CANCELLED today", "Newest note", "Older note"], fresh())
check("active_notice() is still the most important one", sheets.active_notice()["message"] == "CANCELLED today")
RECS.extend({"id": str(i), "type": "announcement", "message": "n%d" % i,
            "active": "TRUE", "expires_at": ""} for i in range(20))
check("at most MAX_SLIDES notices", len(fresh()) == sheets.MAX_SLIDES)
RECS[:] = []
check("nothing posted -> empty list, active_notice() None", fresh() == [] and sheets.active_notice() is None)

import app as appmod
sheets.active_notices = lambda: [{"type": "announcement", "message": "A", "url": "", "link_text": "", "expires_at": ""},
                                 {"type": "announcement", "message": "B", "url": "", "link_text": "", "expires_at": ""}]
sheets.game_day_teams = lambda: None
html = appmod.app.test_client().get("/").get_data(as_text=True)
check("homepage carries every notice to the banner", '"message": "A"' in html and '"message": "B"' in html)
check("banner has slide controls", "bprev" in html and "bpause" in html)
print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

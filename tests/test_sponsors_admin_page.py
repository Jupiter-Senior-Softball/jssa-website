"""The admin Sponsors page is now just a pointer to the 'Sponsor Form
Responses' tab - no editing form, and the old edit routes are gone.
Fake sheet data; never touches Google."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets
import app as appmod

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

class _WS:  id = 12345
class _SH:
    def worksheet(self, name):
        assert name == "Sponsor Form Responses"
        return _WS()

sheets.CONTROL_SHEET_ID = "FAKE_SHEET"
sheets._SA_JSON = "{}"
sheets._control_sheet = lambda readonly=True: _SH()
check("link opens the Sponsor Form Responses tab",
      sheets.sponsor_sheet_url() == "https://docs.google.com/spreadsheets/d/FAKE_SHEET/edit#gid=12345",
      sheets.sponsor_sheet_url())

def boom(readonly=True): raise RuntimeError("Google is down")
sheets._control_sheet = boom
check("falls back to the spreadsheet when the tab can't be looked up",
      sheets.sponsor_sheet_url() == "https://docs.google.com/spreadsheets/d/FAKE_SHEET/edit")

c = appmod.app.test_client()
check("page needs a sign-in", c.get("/admin/sponsors").status_code in (301, 302))
with c.session_transaction() as s: s["admin"] = True
r = c.get("/admin/sponsors")
html = r.get_data(as_text=True)
check("page loads", r.status_code == 200, r.status_code)
check("page links to the sheet", "docs.google.com/spreadsheets/d/FAKE_SHEET/edit" in html)
check("page names the tab and the checkbox",
      "Sponsor Form Responses" in html and "Website Enabled" in html)
check("no editing form left on the page", "<form" not in html.split('class="adminbar"')[1])
check("old edit routes are gone", c.post("/admin/sponsors/add").status_code == 404)

sys.exit(1 if fails else 0)

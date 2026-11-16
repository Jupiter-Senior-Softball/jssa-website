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
    """A sheet whose patron tab has the given name (old or new)."""
    def __init__(self, tab): self.tab = tab
    def worksheet(self, name):
        if name != self.tab: raise KeyError(name)
        return _WS()

sheets.CONTROL_SHEET_ID = "FAKE_SHEET"
sheets._SA_JSON = "{}"
URL = "https://docs.google.com/spreadsheets/d/FAKE_SHEET/edit#gid=12345"
sheets._control_sheet = lambda readonly=True: _SH("Sponsor Form Responses")
check("before the rename: finds the old tab name",
      sheets.sponsor_sheet_link() == (URL, "Sponsor Form Responses"), sheets.sponsor_sheet_link())
sheets._control_sheet = lambda readonly=True: _SH("Patron Form Responses")
check("after the rename: finds the new tab name",
      sheets.sponsor_sheet_link() == (URL, "Patron Form Responses"), sheets.sponsor_sheet_link())

def boom(readonly=True): raise RuntimeError("Google is down")
sheets._control_sheet = boom
check("falls back to the spreadsheet when the tab can't be looked up",
      sheets.sponsor_sheet_url() == "https://docs.google.com/spreadsheets/d/FAKE_SHEET/edit")

sheets._control_sheet = lambda readonly=True: _SH("Sponsor Form Responses")
c0 = appmod.app.test_client()
with c0.session_transaction() as s0: s0["admin"] = True
check("before the rename: page shows the old tab name",
      "Sponsor Form Responses" in c0.get("/admin/sponsors").get_data(as_text=True))
sheets._control_sheet = lambda readonly=True: _SH("Patron Form Responses")

c = appmod.app.test_client()
check("page needs a sign-in", c.get("/admin/sponsors").status_code in (301, 302))
with c.session_transaction() as s: s["admin"] = True
r = c.get("/admin/sponsors")
html = r.get_data(as_text=True)
check("page loads", r.status_code == 200, r.status_code)
check("page links to the sheet", "docs.google.com/spreadsheets/d/FAKE_SHEET/edit" in html)
check("page names the tab and the checkbox",
      "Patron Form Responses" in html and "Sponsor Form Responses" not in html
      and "Website Enabled" in html)
check("no editing form left on the page", "<form" not in html.split('class="adminbar"')[1])
check("old edit routes are gone", c.post("/admin/sponsors/add").status_code == 404)

sys.exit(1 if fails else 0)

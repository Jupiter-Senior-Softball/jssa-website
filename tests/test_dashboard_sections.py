"""Board portal layout: the old "Seasons" section is gone, and its two buttons
(Edit Schedule & Umpires, Save / Manage Past Seasons) live in "Fall and Winter
League Management" - the section the board builds from the "Board Portal Links"
sheet tab. Fake sheet data; never touches Google."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets
import app as appmod

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else "  -- %s" % extra))
    if not cond: fails.append(label)

sheets.is_configured = lambda: True
sheets.list_notices = lambda: []
sheets.home_view_count = lambda: 1

SEASON_BUTTONS = ("Edit Schedule &amp; Umpires", "Save / Manage Past Seasons")

def page(groups):
    sheets.get_portal_links = lambda: groups
    c = appmod.app.test_client()
    with c.session_transaction() as s: s["admin"] = True
    r = c.get("/admin")
    return r.status_code, r.get_data(as_text=True)

def sections(html):
    """{heading: html of the buttons under it} for each portal section."""
    parts = re.split(r'<div class="manage-sub"[^>]*>(.*?)</div>', html)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}

SHEET_GROUPS = [
    {"section": "Fall and Winter League Management", "links": [
        {"name": "How to Create Game Schedules and Team Rosters", "url": "https://example.com/a"},
        {"name": "Posting Fall/Winter League Game Scores", "url": "https://example.com/b"}]},
    {"section": "Pickup Game Management", "links": [{"name": "JSSA Pickup Game Manager", "url": "https://example.com/c"}]},
]

# ---- the normal case: the section exists in the sheet ----------------------
code, html = page(SHEET_GROUPS)
sec = sections(html)
check("dashboard loads", code == 200, code)
check("the old 'Seasons' section is gone", "Seasons" not in sec and ">Seasons<" not in html, list(sec))
fw = sec.get("Fall and Winter League Management", "")
check("both season buttons are inside Fall and Winter League Management", all(b in fw for b in SEASON_BUTTONS), fw[:200])
check("the sheet's own two buttons are still there", "How to Create Game Schedules" in fw and "Posting Fall/Winter League Game Scores" in fw)
check("the season buttons come first in that section", fw.index("Edit Schedule") < fw.index("How to Create"))
check("the buttons still go to the right pages", "/admin/schedule" in fw and "/admin/archive" in fw)
check("each season button appears exactly once on the page", all(html.count(b) == 1 for b in SEASON_BUTTONS), [html.count(b) for b in SEASON_BUTTONS])
check("the season buttons are NOT in any other section", all(b not in v for k, v in sec.items() if k != "Fall and Winter League Management" for b in SEASON_BUTTONS))
check("the sheet's buttons still open in a new tab", 'target="_blank"' in fw)
check("other sections are unchanged", "JSSA Pickup Game Manager" in sec.get("Pickup Game Management", "") and "Division Playing Rules" in sec.get("League Documents", ""))

# ---- the sheet section name is typed by people: case / spacing don't matter -
code, html = page([{"section": "  FALL and winter league management ", "links": [{"name": "X", "url": "https://example.com"}]}])
check("matches the section name however it is capitalised or spaced",
      all(b in html for b in SEASON_BUTTONS) and html.count("Edit Schedule") == 1 and html.count("manage-sub") == html.count("manage-sub"))

# ---- no such section in the sheet (or sheet unreadable): never lose the buttons
for label, groups in (("sheet has no Fall and Winter section", [{"section": "Board Links", "links": [{"name": "Y", "url": "https://example.com"}]}]),
                      ("sheet could not be read (no groups)", [])):
    code, html = page(groups)
    sec = sections(html)
    fw = sec.get("Fall and Winter League Management", "")
    check("%s: the section still appears with both buttons" % label, code == 200 and all(b in fw for b in SEASON_BUTTONS), list(sec))
    check("%s: still exactly once, and no 'Seasons'" % label, all(html.count(b) == 1 for b in SEASON_BUTTONS) and "Seasons" not in sec)

# ---- sign-in is still required ---------------------------------------------
sheets.get_portal_links = lambda: SHEET_GROUPS
r = appmod.app.test_client().get("/admin")
check("not signed in -> sent to login", r.status_code == 302 and "/admin/login" in r.headers["Location"])

print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

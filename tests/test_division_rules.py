"""The division rules portal, end to end: the portal gate, writing and editing
a division's rules, the season rollover, and what members see. Fake sheet data
— never touches Google."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["ADMIN_PASSWORD"] = "adminpw"
os.environ["SECRET_KEY"] = "test"

import sheets

# In-memory stand-in for the DivisionRules tab.
ROWS = []
ROWS.append({"id": "seed1", "division": "Red", "season": "Winter 2026",
             "status": "current", "source": "written", "url": "",
             "body": sheets._seed_rules_text(), "updated_at": "2026-09-21",
             "updated_by": "JSSA website"})

sheets.is_configured = lambda: True
sheets.list_division_rules = lambda: [dict(r) for r in ROWS]

def _add(fields):
    v = sheets._rules_values(fields, "new%d" % len(ROWS))
    if v["status"] == "current":
        for r in ROWS:
            if r["division"] == v["division"]:
                r["status"] = "archived"
    ROWS.append(v); sheets._rules_invalidate(); return v["id"]

def _update(rid, fields):
    for i, r in enumerate(ROWS):
        if r["id"] == str(rid):
            ROWS[i] = sheets._rules_values(fields, str(rid), r)
    sheets._rules_invalidate()

def _status(rid, status):
    status = "current" if status == "current" else "archived"
    for r in ROWS:
        if r["id"] == str(rid):
            if status == "current":
                for o in ROWS:
                    if o["division"] == r["division"]:
                        o["status"] = "archived"
            r["status"] = status
    sheets._rules_invalidate()

def _new_season(rid, season, updated_by=""):
    src = next((r for r in ROWS if r["id"] == str(rid)), None)
    if not src or not season.strip():
        return None
    for r in ROWS:
        if r["division"] == src["division"]:
            r["status"] = "archived"
    nid = "copy%d" % len(ROWS)
    ROWS.append(dict(src, id=nid, season=season.strip(), status="current",
                     updated_by=updated_by))
    sheets._rules_invalidate(); return nid

def _delete(rid):
    ROWS[:] = [r for r in ROWS if r["id"] != str(rid)]; sheets._rules_invalidate()

sheets.add_division_rules = _add
sheets.update_division_rules = _update
sheets.set_division_rules_status = _status
sheets.start_new_season = _new_season
sheets.delete_division_rules = _delete

import app as appmod
appmod.ADMIN_PASSWORD = "adminpw"
c = appmod.app.test_client()

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label +
          (("  -- " + str(extra)[:300]) if (not cond and extra) else ""))
    if not cond:
        fails.append(label)

# --- what members see ------------------------------------------------------
r = c.get("/playing-rules")
check("hub loads", r.status_code == 200, r.status_code)
html = r.get_data(as_text=True)
check("hub shows Red card with season", "Red Division" in html and "Winter 2026" in html)
check("hub shows White coming soon", "White Division" in html and "Rules coming soon" in html)
check("no league-wide rules sheet link", "spreadsheets/d/1ZDVIqbP" not in html)
check("SSUSA named as the backstop", "Senior Softball USA" in html)

r = c.get("/playing-rules/red")
check("red rules page loads", r.status_code == 200, r.status_code)
body = r.get_data(as_text=True)
check("heading rendered from ##", "<h2>SECTION I" in body, body[:200])
check("mercy rule text present", "MERCY RULE" in body)
check("## markers not shown raw", "## SECTION" not in body)
check("bad division 404s", c.get("/playing-rules/green").status_code == 404)

# --- the portal gate -------------------------------------------------------
r = c.get("/admin/rules")
check("editor needs the portal login", r.status_code == 302 and "/admin/login" in r.headers["Location"],
      r.headers.get("Location"))
check("no separate division login page", c.get("/rules-login").status_code == 404)

r = c.post("/admin/login", data={"password": "wrong"})
check("wrong portal password rejected", "Incorrect password" in r.get_data(as_text=True))
check("and grants nothing", c.get("/admin/rules").status_code == 302)

c.post("/admin/login", data={"password": "ADMIN PW"})
page = c.get("/admin/rules").get_data(as_text=True)
check("portal password opens the editor (case/space insensitive)", "Division Rules" in page)
check("every division is editable", all(('<option value="%s"' % d) in page
                                        for d in ("Red", "White", "Blue")), )
check("links back to Admin home", "Admin home" in page)
check("seeded rules are in the textarea", "SECTION I" in page)

# --- the dashboard reaches it ---------------------------------------------
dash = c.get("/admin").get_data(as_text=True)
check("Board Portal has a Division Rules button", "/admin/rules" in dash)

# --- posting and editing ---------------------------------------------------
r = c.post("/admin/rules/save", data={"division": "Blue", "season": "Fall 2026",
                                      "source": "written", "body": "## BLUE\n\nBlue rules.",
                                      "updated_by": "Paul"})
check("a board member can post for any division", any(x["division"] == "Blue" for x in ROWS))
check("blue card goes live", "Blue Division" in c.get("/playing-rules").get_data(as_text=True))
check("blue page renders", "Blue rules." in c.get("/playing-rules/blue").get_data(as_text=True))

blue = [x for x in ROWS if x["division"] == "Blue"][0]
c.post("/admin/rules/save", data={"id": blue["id"], "division": "Blue", "season": "Fall 2026",
                                  "status": "current", "source": "written",
                                  "body": "## BLUE\n\nAmended blue rules.", "updated_by": "Paul"})
check("edit saved", "Amended blue rules." in c.get("/playing-rules/blue").get_data(as_text=True))

# --- the form's guard rails ------------------------------------------------
r = c.post("/admin/rules/save", data={"division": "Purple", "season": "Fall 2026",
                                      "source": "written", "body": "x"})
check("made-up division refused", "choose+a+division" in r.headers["Location"]
      or "choose a division" in r.headers["Location"], r.headers.get("Location"))
check("nothing created for it", not any(x["division"] == "Purple" for x in ROWS))

r = c.post("/admin/rules/save", data={"division": "Red", "season": "",
                                      "source": "written", "body": "x"})
check("season required", "season" in r.headers["Location"])

r = c.post("/admin/rules/save", data={"division": "Red", "season": "Fall 2026",
                                      "source": "link", "url": "not-a-url"})
check("bad link rejected", "https" in r.headers["Location"])

r = c.post("/admin/rules/save", data={"division": "Red", "season": "Fall 2026",
                                      "source": "written", "body": "x" * 50000})
check("oversized rules rejected", "too+long" in r.headers["Location"]
      or "too long" in r.headers["Location"])

# --- the season workflow ---------------------------------------------------
before = len(ROWS)
r = c.post("/admin/rules/seed1/new-season", data={"season": "Fall 2026", "updated_by": "Gary"})
check("start-new-season opens the copy for editing", "edit=" in r.headers["Location"],
      r.headers.get("Location"))
check("copy created", len(ROWS) == before + 1)
new = [x for x in ROWS if x["division"] == "Red" and x["season"] == "Fall 2026"][0]
old = [x for x in ROWS if x["division"] == "Red" and x["season"] == "Winter 2026"][0]
check("copy carries the rules text", "MERCY RULE" in new["body"])
check("copy is current", new["status"] == "current")
check("winter archived automatically", old["status"] == "archived")

hub = c.get("/playing-rules").get_data(as_text=True)
check("hub now shows Fall 2026", "Fall 2026" in hub)
check("hub lists the past season", "Past seasons" in hub and "Winter 2026" in hub)
r = c.get("/playing-rules/red/seed1")
check("archived season still readable", r.status_code == 200 and "MERCY RULE" in r.get_data(as_text=True))
check("archived page flagged as past", "past-season rules" in r.get_data(as_text=True))

# --- archive / restore / delete -------------------------------------------
c.post("/admin/rules/seed1/status", data={"status": "current"})
reds = [x for x in ROWS if x["division"] == "Red"]
check("restoring keeps one current season",
      len([x for x in reds if x["status"] == "current"]) == 1)
check("restored season is Winter 2026",
      [x for x in reds if x["status"] == "current"][0]["season"] == "Winter 2026")

c.post("/admin/rules/%s/delete" % new["id"])
check("delete removes the row", not any(x["id"] == new["id"] for x in ROWS))

# --- the Google Doc route still works --------------------------------------
c.post("/admin/rules/save", data={"id": "seed1", "division": "Red", "season": "Winter 2026",
                                  "status": "current", "source": "link",
                                  "url": "https://docs.google.com/document/d/abc/edit"})
r = c.get("/playing-rules/red")
check("link mode sends the reader to the doc",
      r.status_code == 302 and "docs.google.com" in r.headers["Location"], r.status_code)
check("hub links straight to the doc",
      "docs.google.com/document/d/abc" in c.get("/playing-rules").get_data(as_text=True))
check("switching to a link clears the old text",
      not [x for x in ROWS if x["id"] == "seed1"][0]["body"])

# --- signing out -----------------------------------------------------------
c.get("/admin/logout")
check("signed out, editor closed again", c.get("/admin/rules").status_code == 302)

print()
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)

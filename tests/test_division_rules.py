"""The division rules portal, end to end: who may edit what, the season
rollover, and what members see. Fake sheet data — never touches Google."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["ADMIN_PASSWORD"] = "adminpw"
os.environ["RULES_CODE_RED"] = "red 2026"
os.environ["SECRET_KEY"] = "test"

import sheets

# In-memory stand-in for the DivisionRules tab.
ROWS = []
def _seed():
    del ROWS[:]
    ROWS.append({"id": "seed1", "division": "Red", "season": "Winter 2026",
                 "status": "current", "source": "written", "url": "",
                 "body": sheets._seed_rules_text(), "updated_at": "2026-09-21",
                 "updated_by": "JSSA website"})
_seed()

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
            div = r["division"]
            if status == "current":
                for o in ROWS:
                    if o["division"] == div:
                        o["status"] = "archived"
            r["status"] = status
    sheets._rules_invalidate()
def _new_season(rid, season, updated_by=""):
    src = next((r for r in ROWS if r["id"] == str(rid)), None)
    if not src or not season.strip(): return None
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
    print(("PASS  " if cond else "FAIL  ") + label + (("  -- " + str(extra)[:300]) if (not cond and extra) else ""))
    if not cond: fails.append(label)

# --- public side -----------------------------------------------------------
r = c.get("/playing-rules")
check("hub loads", r.status_code == 200, r.status_code)
html = r.get_data(as_text=True)
check("hub shows Red card with season", "Red Division" in html and "Winter 2026" in html)
check("hub shows White coming soon", "White Division" in html and "Rules coming soon" in html)

r = c.get("/playing-rules/red")
check("red rules page loads", r.status_code == 200, r.status_code)
body = r.get_data(as_text=True)
check("heading rendered from ##", "<h2>SECTION I" in body.replace("&#8212;","—"), body[:200])
check("mercy rule text present", "MERCY RULE" in body)
check("## markers not shown raw", "## SECTION" not in body)
check("no stray hash before heading", ">## " not in body)

check("bad division 404s", c.get("/playing-rules/green").status_code == 404)

# --- login gate ------------------------------------------------------------
r = c.get("/admin/rules")
check("editor requires sign-in", r.status_code == 302 and "/rules-login" in r.headers["Location"], r.headers.get("Location"))
r = c.post("/rules-login", data={"password": "wrong"})
page = r.get_data(as_text=True)
check("wrong code rejected", r.status_code == 200 and "match any division" in page, r.status_code)
check("wrong code grants nothing", c.get("/admin/rules").status_code == 302)
r = c.post("/rules-login", data={"password": "RED2026"}, follow_redirects=True)
check("division code accepted (case/space insensitive)", "Division Rules" in r.get_data(as_text=True))

r = c.get("/admin/rules")
page = r.get_data(as_text=True)
check("editor loads for division manager", r.status_code == 200)
check("shows only own division (no White/Blue option)", "<option value=\"White\"" not in page)
check("seeded rules are in the textarea", "SECTION I" in page)
check("no admin-home link for division manager", "Admin home" not in page)

# --- guard rails -----------------------------------------------------------
r = c.post("/admin/rules/save", data={"division": "Blue", "season": "Fall 2026",
                                      "source": "written", "body": "## X\n\nhi"})
check("cannot edit another division", "only edit your own" in r.headers["Location"] or "problem" in r.headers["Location"], r.headers.get("Location"))
check("Blue not created", not any(x["division"] == "Blue" for x in ROWS))

r = c.post("/admin/rules/save", data={"division": "Red", "season": "",
                                      "source": "written", "body": "x"})
check("season required", "season+name" in r.headers["Location"] or "season" in r.headers["Location"])

r = c.post("/admin/rules/save", data={"division": "Red", "season": "Fall 2026",
                                      "source": "link", "url": "not-a-url"})
check("bad link rejected", "https" in r.headers["Location"])

r = c.post("/admin/rules/save", data={"division": "Red", "season": "Fall 2026",
                                      "source": "written", "body": "x" * 50000})
check("oversized rules rejected", "too+long" in r.headers["Location"] or "too long" in r.headers["Location"])

# --- the season workflow Tom described -------------------------------------
before = len(ROWS)
r = c.post("/admin/rules/seed1/new-season", data={"season": "Fall 2026", "updated_by": "Gary"})
check("start-new-season redirects to edit the copy", "edit=" in r.headers["Location"], r.headers.get("Location"))
check("copy created", len(ROWS) == before + 1)
new = [x for x in ROWS if x["season"] == "Fall 2026"][0]
old = [x for x in ROWS if x["season"] == "Winter 2026"][0]
check("copy carries the rules text", "MERCY RULE" in new["body"])
check("copy is current", new["status"] == "current")
check("winter archived automatically", old["status"] == "archived")

hub = c.get("/playing-rules").get_data(as_text=True)
check("hub now shows Fall 2026", "Fall 2026" in hub)
check("hub lists past season", "Past seasons" in hub and "Winter 2026" in hub)
r = c.get("/playing-rules/red/seed1")
check("archived season still readable", r.status_code == 200 and "MERCY RULE" in r.get_data(as_text=True))
check("archived page flagged as past", "past-season rules" in r.get_data(as_text=True))
check("current page shows new season", "Fall 2026" in c.get("/playing-rules/red").get_data(as_text=True))

# --- editing + the link mode ----------------------------------------------
c.post("/admin/rules/save", data={"id": new["id"], "division": "Red", "season": "Fall 2026",
                                  "status": "current", "source": "written",
                                  "body": "## NEW SECTION\n\nOne new rule.", "updated_by": "Gary"})
check("edit saved", "One new rule." in c.get("/playing-rules/red").get_data(as_text=True))

c.post("/admin/rules/save", data={"id": new["id"], "division": "Red", "season": "Fall 2026",
                                  "status": "current", "source": "link",
                                  "url": "https://docs.google.com/document/d/abc/edit"})
r = c.get("/playing-rules/red")
check("link mode redirects to the doc", r.status_code == 302 and "docs.google.com" in r.headers["Location"], r.status_code)
hub = c.get("/playing-rules").get_data(as_text=True)
check("hub links straight to the doc", "docs.google.com/document/d/abc" in hub)
check("switching to link clears the old body", not [x for x in ROWS if x["id"] == new["id"]][0]["body"])

# --- admin sees everything -------------------------------------------------
c.get("/admin/logout")
c.post("/rules-login", data={"password": "adminpw"})
page = c.get("/admin/rules").get_data(as_text=True)
check("admin sees all three divisions", '<option value="White"' in page and '<option value="Blue"' in page)
check("admin gets the dashboard link", "Admin home" in page)
r = c.post("/admin/rules/save", data={"division": "Blue", "season": "Fall 2026",
                                      "source": "written", "body": "## BLUE\n\nBlue rules."},
           follow_redirects=True)
check("admin can post for Blue", any(x["division"] == "Blue" for x in ROWS))
check("blue card now live", "Blue Division" in c.get("/playing-rules").get_data(as_text=True))
check("blue page renders", "Blue rules." in c.get("/playing-rules/blue").get_data(as_text=True))


# --- a division manager must not be able to touch another division's row ----
c.get("/admin/logout")
c.post("/rules-login", data={"password": "red 2026"})
blue = [x for x in ROWS if x["division"] == "Blue"][0]
snapshot = dict(blue)
r = c.post("/admin/rules/save", data={"id": blue["id"], "division": "Red",
                                      "season": "Hijacked", "source": "written",
                                      "body": "## X\n\nmine now"})
after = [x for x in ROWS if x["id"] == snapshot["id"]][0]
check("cannot relabel another division's row", after["division"] == "Blue" and after["season"] == snapshot["season"], after)
r = c.post("/admin/rules/%s/status" % blue["id"], data={"status": "archived"})
check("cannot archive another division's row",
      [x for x in ROWS if x["id"] == snapshot["id"]][0]["status"] == snapshot["status"])
r = c.post("/admin/rules/%s/delete" % blue["id"])
check("cannot delete another division's row", any(x["id"] == snapshot["id"] for x in ROWS))
r = c.post("/admin/rules/%s/new-season" % blue["id"], data={"season": "Fall 2026"})
check("cannot roll over another division's season",
      len([x for x in ROWS if x["division"] == "Blue"]) == 1)

print()
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)

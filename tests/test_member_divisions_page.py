"""The Member Division Assignments page in the admin portal.

Checks that the page is behind the password, shows the members and the log,
and that saving passes the right details through to sheets.set_member_division.
Nothing here touches Google.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "test-only-not-a-real-secret"
os.environ["ADMIN_PASSWORD"] = "test-only"
import sheets
import app as webapp

COUNTS = {"RED": 76, "WHITE": 80, "BLUE": 70, "none": 2, "total": 228}

sheets.member_divisions = lambda: {"players": [
    {"name": "Jim Kowalski", "last": "kowalski", "email": "jim@e.com",
     "div": "RED", "row": 2},
    {"name": "Bob Marsh", "last": "marsh", "email": "bob@e.com",
     "div": "WHITE", "row": 3},
], "counts": dict(COUNTS), "error": ""}
sheets.board_members = lambda: [
    {"name": "Tom Cosentino", "role": "Commissioner", "division": "",
     "initials": "TC", "order": 1},
    {"name": "Jeff McCrave", "role": "Director", "division": "",
     "initials": "JM", "order": 2},
]
sheets.division_change_log = lambda limit=25: [
    {"date": "2026-09-27", "time": "10:14 AM", "player": "Bob Marsh",
     "email": "bob@e.com", "from": "RED", "to": "WHITE", "by": "Tom Cosentino"},
]

webapp.app.config["TESTING"] = True
c = webapp.app.test_client()

failures = []


def check(label, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + label + (("  -> " + detail) if detail else ""))
    if not condition:
        failures.append(label)


# ------------------------------------------------------------ password required
r = c.get("/admin/divisions")
check("signed out, the page redirects to the login",
      r.status_code in (301, 302) and "login" in (r.headers.get("Location") or ""),
      str(r.status_code) + " -> " + str(r.headers.get("Location")))

saved = []
sheets.set_member_division = lambda *a: (saved.append(a) or (True, "Moved."))

r = c.post("/admin/divisions/save",
           data={"member": "2|jim@e.com", "division": "WHITE", "changed_by": "Tom"})
check("signed out, a save is refused and changes nothing",
      r.status_code in (301, 302) and not saved, str(saved))

with c.session_transaction() as s:
    s["admin"] = True

# ------------------------------------------------------------------- the page
r = c.get("/admin/divisions")
html = r.get_data(as_text=True)
check("signed in, the page loads", r.status_code == 200, str(r.status_code))

for must in ["Member Division Assignments", "Jim Kowalski", "Bob Marsh",
             "Tom Cosentino", "Jeff McCrave", "RED", "WHITE", "BLUE",
             "2|jim@e.com", "Recent division changes"]:
    check("the page shows " + repr(must), must in html)

check("the page warns that a change affects game-day emails",
      "emails" in html.lower() and "15 minutes" in html)

# ----------------------------------------------------- the division head counts
for n in ("76", "80", "70", "228"):
    check("the summary shows the count " + n, ">" + n + "<" in html)
check("the 'no division' tile shows when someone has none",
      ">2<" in html and "No division" in html)

# ------------------------------------------------------------------ saving
del saved[:]
r = c.post("/admin/divisions/save",
           data={"member": "2|jim@e.com", "division": "WHITE",
                 "changed_by": "Tom Cosentino"})
check("saving redirects back to the page", r.status_code in (301, 302),
      str(r.status_code))
check("the row and email are split out of the picker value",
      saved and saved[0][0] == "2" and saved[0][1] == "jim@e.com", str(saved))
check("the division and the board member's name are passed through",
      saved and saved[0][3] == "WHITE" and saved[0][4] == "Tom Cosentino", str(saved))

# the result message is shown once, then cleared
r = c.get("/admin/divisions")
check("the result message appears after saving", "Moved." in r.get_data(as_text=True))
r = c.get("/admin/divisions")
check("it does not appear again on the next visit",
      "Moved." not in r.get_data(as_text=True))

# ------------------------------------------------- a member with no email on file
sheets.member_divisions = lambda: {"players": [
    {"name": "Newguy Nodiv", "last": "nodiv", "email": "", "div": "", "row": 5},
], "counts": {"RED": 0, "WHITE": 0, "BLUE": 0, "none": 1, "total": 1}, "error": ""}
r = c.get("/admin/divisions")
html = r.get_data(as_text=True)
check("a member with no email still appears", "Newguy Nodiv" in html)
check("and is labelled as having no division yet", "no division yet" in html)

# ------------------------------------------------------ the sheet being unreachable
sheets.member_divisions = lambda: {
    "players": [],
    "counts": {"RED": 0, "WHITE": 0, "BLUE": 0, "none": 0, "total": 0},
    "error": "quota exceeded"}
r = c.get("/admin/divisions")
html = r.get_data(as_text=True)
check("if the roster can't be read, the page still loads", r.status_code == 200)
check("and it says why", "quota exceeded" in html)

print()
if failures:
    print("FAILURES: " + ", ".join(failures))
    sys.exit(1)
print("DIVISION PAGE CHECKS PASSED")

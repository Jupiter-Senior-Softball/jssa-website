"""In Memoriam: tributes, and a name typed twice must not become two men."""
import os, re, sys
from urllib.parse import quote
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "t"; os.environ["ADMIN_PASSWORD"] = "t"
import sheets, app as webapp

webapp.app.config["TESTING"] = True
c = webapp.app.test_client()

def page(entries):
    sheets.in_memoriam_entries = lambda: entries
    return c.get("/in-memoriam").get_data(as_text=True)


# --- the page still stands on its own when the sheet gives us nothing -------
html = page([])
missing = [m["name"] for m in webapp.IN_MEMORIAM_ROSTER if m["name"] not in html]
print("all 13 brothers on the page with an empty sheet:", not missing)
assert not missing, missing

def sheet_is_down():
    raise RuntimeError("Google is having a day")
sheets.in_memoriam_entries = sheet_is_down
html = c.get("/in-memoriam").get_data(as_text=True)
print("and still there when the sheet errors out :", "Vinnie Lombardo" in html)
assert "Vinnie Lombardo" in html


# --- a tribute for a man already on the page attaches to him ---------------
TRIBUTE = "Played third base for eleven years. Never missed a Tuesday."
html = page([{"name": "Ron Seely", "when": "", "image": "", "tribute": TRIBUTE}])
print("his tribute shows                        :", TRIBUTE in html)
assert TRIBUTE in html
print("and he is still listed exactly once      :", html.count(">Ron Seely<") == 1)
assert html.count(">Ron Seely<") == 1, html.count(">Ron Seely<")

# matched forgivingly — spacing and capitals shouldn't split a man in two
for typed in ["ron seely", "  Ron   Seely  ", "RON SEELY"]:
    rows = webapp.memoriam_years([{"name": typed, "tribute": TRIBUTE}])
    names = [m["name"] for year, men in rows for m in men]
    assert names.count("Ron Seely") == 1, typed
    assert len(names) == len(webapp.IN_MEMORIAM_ROSTER), typed
print("typed as %r or %r, still one man         : True" % ("ron seely", "RON SEELY"))


# --- an admin entry can also fill in a photo or a date --------------------
rows = webapp.memoriam_years([{"name": "Rick Hendee", "image": "/static/x.jpg"}])
rick = [m for _, men in rows for m in men if m["name"] == "Rick Hendee"][0]
print("photo added to a built-in brother        :", rick["image"] == "/static/x.jpg")
assert rick["image"] == "/static/x.jpg"
print("and his existing date is left alone      :", rick["when"] == "May 2022")
assert rick["when"] == "May 2022"


# --- a genuinely new name is added, in the right year ---------------------
rows = webapp.memoriam_years([{"name": "New Brother", "when": "March 2026"}])
print("newest year leads                        :", rows[0][0] == "2026")
assert rows[0][0] == "2026"
assert [m["name"] for m in rows[0][1]] == ["New Brother"]
years = [y for y, _ in rows if y != "Remembered"]
print("years run newest to oldest               :", years == sorted(years, reverse=True))
assert years == sorted(years, reverse=True)


# --- a man entered with no date is kept, not dropped ----------------------
rows = webapp.memoriam_years([{"name": "No Date Given", "when": ""}])
print("undated brother collected at the end     :", rows[-1][0] == "Remembered")
assert rows[-1][0] == "Remembered"
assert [m["name"] for m in rows[-1][1]] == ["No Date Given"]
names = [m["name"] for _, men in rows for m in men]
assert "No Date Given" in names and len(names) == len(webapp.IN_MEMORIAM_ROSTER) + 1

# a blank name is not a man
assert webapp.memoriam_years([{"name": "   "}]) == webapp.memoriam_years([])
print("a blank name adds nobody                 : True")



# --- the sheet side: an older sheet must grow the new column on its own ----
class FakeSheet:
    """Stands in for a Google worksheet, remembering what we did to it."""
    def __init__(self, header, rows=None):
        self.rows = [list(header)] + [list(r) for r in (rows or [])]
        self.appended, self.cells = [], []
    def row_values(self, n):
        return list(self.rows[n - 1])
    def update(self, values, rng):
        self.rows[0] = list(values[0])
    def get_all_records(self, expected_headers=None):
        head = self.rows[0]
        missing = [h for h in (expected_headers or []) if h not in head]
        assert not missing, "gspread would refuse: no %s column" % missing
        return [dict(zip(head, r + [""] * (len(head) - len(r))))
                for r in self.rows[1:]]
    def append_row(self, values, value_input_option=None):
        self.appended.append(values)
    def update_cell(self, row, col, value):
        self.cells.append((row, col, value))

OLD_HEADER = ["id", "name", "when", "image", "order", "active"]   # before tributes
sheet = FakeSheet(OLD_HEADER, [["a1", "Ron Seely", "September 2025", "", 1, "TRUE"]])
sheets._ensure_headers(sheet, sheets.MEM_HEADERS)
print("\nolder sheet grows a tribute column       :", sheet.rows[0] == sheets.MEM_HEADERS)
assert sheet.rows[0] == sheets.MEM_HEADERS, sheet.rows[0]
print("the columns Tom already had stay put     :", sheet.rows[0][:6] == OLD_HEADER)
assert sheet.rows[0][:6] == OLD_HEADER
# and the row already in the sheet still reads back
rec = sheet.get_all_records(expected_headers=sheets.MEM_HEADERS)[0]
assert rec["name"] == "Ron Seely" and rec["tribute"] == ""

# --- adding writes the tribute into the right column -----------------------
sheets._simple_worksheet = lambda tab, headers: sheet
sheets.add_mem_entry({"name": "New Man", "when": "March 2026",
                      "image": "", "tribute": "A gentleman at first base."})
written = dict(zip(sheets.MEM_HEADERS, sheet.appended[0]))
print("a new entry's tribute lands in its column:",
      written["tribute"] == "A gentleman at first base.")
assert written["tribute"] == "A gentleman at first base."
assert written["name"] == "New Man" and written["active"] == "TRUE"
assert len(sheet.appended[0]) == len(sheets.MEM_HEADERS)

# --- editing an existing man saves his tribute ----------------------------
sheets.update_mem_entry("a1", {"name": "Ron Seely", "when": "September 2025",
                               "image": "", "tribute": "Never missed a Tuesday."})
col = sheets.MEM_HEADERS.index("tribute") + 1
saved = [c for c in sheet.cells if c[0] == 2 and c[1] == col]
print("editing saves the tribute to his row     :", saved == [(2, col, "Never missed a Tuesday.")])
assert saved == [(2, col, "Never missed a Tuesday.")], sheet.cells


# --- the admin panel lists the 13 with a link each --------------------------
sheets.is_configured = lambda: True
SAVED = [
    {"id": "a1", "name": "Ron Seely", "when": "", "image": "", "order": 1,
     "active": "TRUE", "tribute": "Never missed a Tuesday."},
    {"id": "c3", "name": "  walter   SPARKS ", "when": "", "image": "http://x/p.jpg",
     "order": 3, "active": "TRUE", "tribute": "Played until he was eighty-one."},
]
sheets.list_mem_entries = lambda: [dict(r) for r in SAVED]
c.post("/admin/login", data={"password": "t"})
html = c.get("/admin/memoriam").get_data(as_text=True)

absent = [m["name"] for m in webapp.IN_MEMORIAM_ROSTER if m["name"] not in html]
print("\nall 13 listed in the admin panel         :", not absent)
assert not absent, absent

# a man with nothing saved gets a "write" link that fills his name in
assert "add=Rick+Hendee" in html or "add=Rick%20Hendee" in html, "no prefill link"
# a man who already has a row is sent to that row instead
assert "edit=a1" in html, "should edit Ron Seely's saved row"
print("no-tribute man gets a prefill link       : True")
print("man with one gets an edit link to his row: True")

# the prefill form knows his name, and adds rather than updates
form = c.get("/admin/memoriam?add=Rick+Hendee").get_data(as_text=True)
assert 'value="Rick Hendee"' in form, "name not filled in"
assert 'action="/admin/memoriam/add"' in form, "prefill must add, not update"
print("prefill form carries his name            : True")
# his date is left blank so the built-in one survives the merge
assert re.search(r'id="when"[^>]*value=""', form), "date should start blank"
print("and leaves his date blank to keep it     : True")

# asking to "add" a man who already has a row edits that row instead
r = c.get("/admin/memoriam?add=Ron+Seely")
assert r.status_code == 302 and "edit=a1" in r.headers["Location"], r.headers.get("Location")
# even typed sloppily
r = c.get("/admin/memoriam?add=" + quote("  ron   seely "))
assert r.status_code == 302 and "edit=a1" in r.headers["Location"], r.headers.get("Location")
print("never offers a second row for one man    : True")

# a saved row that fills in a built-in man says so
assert "fills in the card for Ron Seely" in html
assert "fills in the card for Walter Sparks" in html   # matched despite the sloppy casing
print("saved rows say which card they fill in   : True")


print("\nIN MEMORIAM CHECKS PASSED")

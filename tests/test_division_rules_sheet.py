"""The division rules sheet layer against a fake worksheet, so row indexing,
header order and the A1 range math are actually checked. Never touches Google."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

class FakeWS:
    def __init__(self, headers):
        self.rows = [list(headers)]
    def get_all_records(self, expected_headers=None):
        hdr = self.rows[0]
        return [dict(zip(hdr, r + [""] * (len(hdr) - len(r)))) for r in self.rows[1:]]
    def append_row(self, vals, value_input_option=None):
        self.rows.append(list(vals))
    def update_cell(self, row, col, val):
        self.rows[row - 1][col - 1] = val
    def update(self, values, rng, value_input_option=None):
        m = re.match(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$", rng)
        assert m, "bad range %r" % rng
        c1, r1, c2, r2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        assert r1 == r2, "range must be one row"
        width = ord(c2) - ord(c1) + 1
        assert width == len(sheets.RULES_HEADERS), (
            "range covers %d columns, need %d" % (width, len(sheets.RULES_HEADERS)))
        assert len(values[0]) == width
        self.rows[r1 - 1] = list(values[0])
    def delete_rows(self, row):
        del self.rows[row - 1]

WS = FakeWS(sheets.RULES_HEADERS)
sheets._rules_worksheet = lambda: WS
sheets.is_configured = lambda: True

fails = []
def check(label, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + label + (("  -- " + str(extra)[:200]) if (not cond and extra) else ""))
    if not cond: fails.append(label)

def rows():
    return sheets.list_division_rules()

# add
rid = sheets.add_division_rules({"division": "Red", "season": "Winter 2026",
                                 "source": "written", "body": "## A\n\nfirst",
                                 "updated_by": "Tom"})
check("row appended with all columns", len(WS.rows[1]) == len(sheets.RULES_HEADERS), WS.rows[1])
check("values land in the right columns",
      dict(zip(sheets.RULES_HEADERS, WS.rows[1]))["division"] == "Red")
check("updated_at stamped", bool(rows()[0]["updated_at"]))

# second division
sheets.add_division_rules({"division": "Blue", "season": "Winter 2026",
                           "source": "link", "url": "https://x/doc"})
check("link row keeps no body", rows()[1]["body"] == "" if rows()[1]["division"] == "Blue" else True)
check("two divisions both current",
      len([r for r in rows() if r["status"] == "current"]) == 2)

# update in place — the A1 range path
sheets.update_division_rules(rid, {"division": "Red", "season": "Winter 2026",
                                   "status": "current", "source": "written",
                                   "body": "## A\n\nedited", "updated_by": "Gary"})
red = [r for r in rows() if r["division"] == "Red"][0]
check("edit saved to the right row", red["body"].endswith("edited"), red["body"])
check("edit did not disturb the other division",
      [r for r in rows() if r["division"] == "Blue"][0]["url"] == "https://x/doc")
check("sheet still has header + 2 rows", len(WS.rows) == 3, len(WS.rows))

# new season: copies, archives the old, keeps one current per division
new_id = sheets.start_new_season(rid, "Fall 2026", "Gary")
reds = [r for r in rows() if r["division"] == "Red"]
check("copy added", len(reds) == 2)
check("exactly one current Red", len([r for r in reds if r["status"] == "current"]) == 1)
check("new season is the current one",
      [r for r in reds if r["status"] == "current"][0]["season"] == "Fall 2026")
check("old season kept, archived",
      [r for r in reds if r["status"] == "archived"][0]["season"] == "Winter 2026")
check("copy carries the text",
      [r for r in reds if r["status"] == "current"][0]["body"].endswith("edited"))
check("Blue untouched by Red's rollover",
      [r for r in rows() if r["division"] == "Blue"][0]["status"] == "current")

# bring an old season back
sheets.set_division_rules_status(rid, "current")
reds = [r for r in rows() if r["division"] == "Red"]
check("still only one current after restore",
      len([r for r in reds if r["status"] == "current"]) == 1)
check("restored season is Winter 2026",
      [r for r in reds if r["status"] == "current"][0]["season"] == "Winter 2026")

# delete
sheets.delete_division_rules(new_id)
check("row deleted", not any(r["id"] == new_id for r in rows()))
check("other rows intact", len(rows()) == 2, rows())

# blank season is refused rather than creating a nameless row
before = len(rows())
check("blank season refused", sheets.start_new_season(rid, "   ") is None)
check("nothing added", len(rows()) == before)

# formatting helper
b = sheets.rules_blocks("## HEAD\n\nline one\nline two\n\n#### deep\n\nlast")
check("heading parsed", b[0] == {"h": "HEAD"}, b[0])
check("wrapped lines joined into one paragraph", b[1] == {"p": "line one line two"}, b[1])
check("extra hashes stripped", b[2] == {"h": "deep"}, b[2])
check("plain text kept", b[3] == {"p": "last"}, b[3])
check("empty body is no blocks", sheets.rules_blocks("") == [])

# the seed file the portal ships with
seed = sheets._seed_rules_text()
check("seed file found", len(seed) > 10000, len(seed))
sb = sheets.rules_blocks(seed)
check("seed has the five section headings", len([x for x in sb if "h" in x]) == 5,
      [x["h"] for x in sb if "h" in x])
check("seed keeps every lettered item A-M",
      all(any(x.get("p", "").startswith(L + ".") for x in sb)
          for L in "ABCDEFGHIJKLM"))

# an empty sheet that read fine must stay empty, not resurrect the built-in
# rules a division deliberately deleted
sheets.delete_division_rules([r for r in rows()][0]["id"])
sheets.delete_division_rules([r for r in rows()][0]["id"])
check("sheet is now empty", rows() == [])
sheets._rules_invalidate()
check("no zombie fallback rules", sheets.division_rules() == [], sheets.division_rules())

# but an unreadable sheet still shows the built-in rules
def boom():
    raise RuntimeError("Google is down")
sheets._rules_worksheet = boom
sheets._rules_invalidate()
fb = sheets.division_rules()
check("falls back when the sheet can't be read", len(fb) == 1 and fb[0]["division"] == "Red", fb)
sheets._rules_worksheet = lambda: WS

print()
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)

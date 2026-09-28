"""Moving a member between divisions.

The real write lands in the "JSSA Players" tab of the Pickup Game Management
workbook — a sheet full of protected tabs and Apps Script. These checks use a
fake worksheet, so nothing here ever touches Google. What they prove is the
part that matters: exactly ONE cell is written, it is always the Division
column, and every guard refuses rather than writing the wrong row.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

# Keep the real tab finder — the stubs below replace it, and the last section
# of this file puts it back to check which tab it picks.
_real_players_worksheet = sheets._players_worksheet

HEADERS = ["Email", "First Name", "Last Name", "Division", "Active"]
COLS = {"email": 0, "first name": 1, "last name": 2, "division": 3, "active": 4}
HEADER_ROW = 1          # headers sit on row 1, so players start on row 2


class FakeWorksheet:
    """Just enough of a gspread worksheet for these checks, and it records
    every write so we can prove how many there were."""

    def __init__(self, rows):
        self.rows = rows
        self.writes = []

    def row_values(self, row):
        return list(self.rows[row - 1])

    def update_acell(self, a1, value):
        self.writes.append((a1, value))


def build(rows=None):
    rows = rows or [
        HEADERS,
        ["jim@e.com", "Jim", "Kowalski", "RED", "TRUE"],
        ["bob@e.com", "Bob", "Marsh", "WHITE", "TRUE"],
        ["gone@e.com", "Gus", "Retired", "BLUE", "FALSE"],
        ["", "Nodiv", "Newguy", "", "TRUE"],
    ]
    ws = FakeWorksheet(rows)
    sheets.ROSTER_SHEET_ID = "fake-roster-id"
    sheets._SA_JSON = "{}"
    sheets._roster_sheet = lambda readonly=True: object()
    sheets._players_worksheet = lambda sh: (ws, HEADER_ROW, COLS)
    return ws


logged = []
sheets._log_division_change = lambda *a: logged.append(a)
sheets._roster_invalidate = lambda: None

failures = []


def check(label, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + label + (("  -> " + detail) if detail else ""))
    if not condition:
        failures.append(label)


# ---------------------------------------------------------------- the happy path
ws = build()
del logged[:]
ok, msg = sheets.set_member_division(2, "jim@e.com", "Jim Kowalski", "WHITE", "Tom")
check("a normal move reports success", ok, msg)
check("exactly one cell is written", len(ws.writes) == 1, str(ws.writes))
check("it is the Division cell on that player's row", ws.writes == [("D2", "WHITE")],
      str(ws.writes))
check("the change is logged with the old and new division",
      logged == [("Jim Kowalski", "jim@e.com", "RED", "WHITE", "Tom")], str(logged))

# lower case from the form is accepted and stored upper case
ws = build()
ok, msg = sheets.set_member_division(2, "jim@e.com", "Jim Kowalski", "white", "Tom")
check("a lower-case division still saves as WHITE", ws.writes == [("D2", "WHITE")],
      str(ws.writes))

# a player with no division yet
ws = build()
del logged[:]
ok, msg = sheets.set_member_division(5, "", "Nodiv Newguy", "BLUE", "Tom")
check("a player with no division can be given one", ok and ws.writes == [("D5", "BLUE")],
      str(ws.writes))
check("the log shows they came from no division",
      logged and logged[0][2] == "", str(logged))

# ------------------------------------------------------------------- the guards
ws = build()
ok, msg = sheets.set_member_division(2, "jim@e.com", "Jim Kowalski", "RED", "Tom")
check("moving someone to the division they are already in writes nothing",
      ok and not ws.writes and "already" in msg, msg)

ws = build()
ok, msg = sheets.set_member_division(2, "jim@e.com", "Jim Kowalski", "GREEN", "Tom")
check("a division that isn't RED/WHITE/BLUE is refused", not ok and not ws.writes, msg)

ws = build()
ok, msg = sheets.set_member_division(2, "jim@e.com", "Jim Kowalski", "WHITE", "")
check("a change with no name attached is refused", not ok and not ws.writes, msg)

ws = build()
ok, msg = sheets.set_member_division(2, "jim@e.com", "Jim Kowalski", "WHITE", "   ")
check("a name of only spaces is refused too", not ok and not ws.writes, msg)

# The sheet was re-sorted while the page sat open: row 2 is now someone else.
ws = build()
ok, msg = sheets.set_member_division(2, "bob@e.com", "Bob Marsh", "BLUE", "Tom")
check("a row holding a different member is refused, not guessed at",
      not ok and not ws.writes, msg)

ws = build()
ok, msg = sheets.set_member_division(1, "", "", "WHITE", "Tom")
check("the header row can never be written to", not ok and not ws.writes, msg)

ws = build()
ok, msg = sheets.set_member_division("not-a-row", "jim@e.com", "Jim", "WHITE", "Tom")
check("a junk row number is refused", not ok and not ws.writes, msg)

# A player with no email on file is matched by name instead.
ws = build()
ok, msg = sheets.set_member_division(5, "", "Someone Else", "BLUE", "Tom")
check("with no email on file, a mismatched name is still caught",
      not ok and not ws.writes, msg)


# ------------------------------------------------- reading the list for the page
ws = build()
sheets._dir_cache = {"data": None, "ts": 0.0}


class FakeReadWorksheet(FakeWorksheet):
    def get_all_values(self):
        return self.rows


read_ws = FakeReadWorksheet(ws.rows)
sheets._players_worksheet = lambda sh: (read_ws, HEADER_ROW, COLS)

listing = sheets.member_divisions()
names = [p["name"] for p in listing["players"]]
check("the list leaves out members who are not Active",
      "Gus Retired" not in names, str(names))
check("the list is sorted by last name", names == sorted(names, key=lambda n: n.split()[-1].lower()),
      str(names))
check("each member carries the row number we write back to",
      all(p["row"] >= 2 for p in listing["players"]),
      str([(p["name"], p["row"]) for p in listing["players"]]))
jim = next(p for p in listing["players"] if p["name"] == "Jim Kowalski")
check("Jim is on row 2 with his current division", jim["row"] == 2 and jim["div"] == "RED",
      str(jim))

# ------------------------------------------------------- the division head counts
counts = listing["counts"]
check("each division is counted",
      counts["RED"] == 1 and counts["WHITE"] == 1 and counts["BLUE"] == 0, str(counts))
check("a member with no division is counted separately", counts["none"] == 1, str(counts))
check("the inactive member is left out of the counts too",
      counts["total"] == 3, str(counts))
check("the divisions plus 'none' add up to the total",
      counts["RED"] + counts["WHITE"] + counts["BLUE"] + counts["none"] == counts["total"],
      str(counts))

# counts must be present even when the sheet can't be read, so the page still draws
saved_id = sheets.ROSTER_SHEET_ID
sheets.ROSTER_SHEET_ID = ""
blank = sheets.member_divisions()
sheets.ROSTER_SHEET_ID = saved_id
check("counts are still there when the roster can't be read",
      blank["counts"]["total"] == 0 and blank["counts"]["RED"] == 0, str(blank))

# ------------------------------------------- picking the right tab to write to
# The real workbook has FOUR tabs carrying First Name / Last Name / Division:
# JSSA Players, Master_Backend, Schedule and Master_Backend Archive. Only the
# first is safe to write to — the others are rebuilt by the pickup app's sync,
# so a change written there would silently disappear.
import gspread


class FakeTab(FakeReadWorksheet):
    def __init__(self, title, rows):
        FakeReadWorksheet.__init__(self, rows)
        self.title = title


BACKEND_ROWS = [
    ["Email", "First Name", "Last Name", "Division", "Position"],
    ["jim@e.com", "Jim", "Kowalski", "RED", "SS"],
]
PLAYERS_ROWS = [
    HEADERS,
    ["jim@e.com", "Jim", "Kowalski", "RED", "TRUE"],
]


class FakeSpreadsheet:
    """Tabs in workbook order — Master_Backend deliberately sits first, the way
    it would if somebody dragged a tab in Google Sheets."""

    def __init__(self):
        self.tabs = [FakeTab("Master_Backend", BACKEND_ROWS),
                     FakeTab("Schedule", BACKEND_ROWS),
                     FakeTab(sheets.PLAYERS_TAB, PLAYERS_ROWS)]

    def worksheets(self):
        return self.tabs

    def worksheet(self, title):
        for t in self.tabs:
            if t.title == title:
                return t
        raise gspread.WorksheetNotFound(title)


# restore the real finder for this part
sheets._players_worksheet = _real_players_worksheet

ws, header_row, cols = sheets._players_worksheet(FakeSpreadsheet())
check("the JSSA Players tab is chosen even when another matching tab is first",
      ws is not None and ws.title == sheets.PLAYERS_TAB,
      ws.title if ws is not None else "none")
check("and its Active column is found (the backend tabs have none)",
      cols is not None and "active" in cols, str(cols))


class NoPlayersTab(FakeSpreadsheet):
    def __init__(self):
        FakeSpreadsheet.__init__(self)
        self.tabs = [FakeTab("Renamed Roster", PLAYERS_ROWS)]


ws, header_row, cols = sheets._players_worksheet(NoPlayersTab())
check("a renamed tab is still found by its headers",
      ws is not None and ws.title == "Renamed Roster",
      ws.title if ws is not None else "none")


class NothingMatching(FakeSpreadsheet):
    def __init__(self):
        FakeSpreadsheet.__init__(self)
        self.tabs = [FakeTab("Settings", [["Setting", "Value"]])]


ws, header_row, cols = sheets._players_worksheet(NothingMatching())
check("a workbook with no player list returns nothing rather than guessing",
      ws is None and cols is None)

print()
if failures:
    print("FAILURES: " + ", ".join(failures))
    sys.exit(1)
print("DIVISION CHANGE CHECKS PASSED")

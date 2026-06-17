"""
sheets.py — read/write the website's content sheet via a Google service account.

Design notes
------------
* Points at a DEDICATED "JSSA Website Content" spreadsheet (SHEET_ID), NOT the
  league's member sheet. The service account therefore never has access to
  member emails or passwords — only website content.
* All website notices live on one tab (WebsiteNotices), auto-created if missing.
* The homepage's active-notice lookup is cached briefly so we don't hit the
  Google API on every page view.
* Everything degrades gracefully: if the service account / sheet id aren't
  configured yet, is_configured() returns False and the public site runs
  normally with no dynamic banner.

Required environment variables (set in Render):
    GOOGLE_SERVICE_ACCOUNT_JSON  — full JSON of the service-account key
    SHEET_ID                     — id of the "JSSA Website Content" spreadsheet
"""

import os
import json
import time
import uuid
import datetime
import threading

SHEET_ID = os.environ.get("SHEET_ID", "").strip()
_SA_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

NOTICES_TAB = "WebsiteNotices"
HEADERS = ["id", "type", "message", "active", "created_by", "created_at"]

_CACHE_TTL = 30  # seconds
_cache = {"notice": None, "ts": 0.0}
_lock = threading.Lock()


def is_configured():
    """True only when both the service account and sheet id are present."""
    return bool(SHEET_ID and _SA_JSON)


def _worksheet():
    """Return the WebsiteNotices worksheet, creating it (with headers) if needed."""
    import gspread
    from google.oauth2.service_account import Credentials

    info = json.loads(_SA_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    try:
        ws = sh.worksheet(NOTICES_TAB)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=NOTICES_TAB, rows=200, cols=len(HEADERS))
        ws.update([HEADERS], "A1")
    return ws


def _is_true(value):
    return str(value).strip().upper() in ("TRUE", "1", "YES", "Y")


def list_notices():
    """All notices, newest first. Returns a list of dicts."""
    if not is_configured():
        return []
    ws = _worksheet()
    records = ws.get_all_records(expected_headers=HEADERS)
    return list(reversed(records))


def active_notice():
    """
    The single notice to show in the site banner, or None.
    Weather/cancellation notices take priority over announcements.
    Cached for _CACHE_TTL seconds; last good value is kept on error.
    """
    now = time.time()
    with _lock:
        if now - _cache["ts"] < _CACHE_TTL:
            return _cache["notice"]

    notice = None
    try:
        if is_configured():
            actives = [r for r in list_notices() if _is_true(r.get("active"))]
            weather = [r for r in actives if str(r.get("type")) == "weather"]
            chosen = (weather or actives)[0] if actives else None
            if chosen:
                notice = {
                    "type": str(chosen.get("type") or "announcement"),
                    "message": str(chosen.get("message") or ""),
                }
        with _lock:
            _cache["notice"] = notice
            _cache["ts"] = now
        return notice
    except Exception:
        # On any API hiccup, keep showing the last known value rather than break.
        return _cache["notice"]


def _invalidate():
    with _lock:
        _cache["ts"] = 0.0


def add_notice(ntype, message, created_by):
    ntype = "weather" if ntype == "weather" else "announcement"
    row = [
        uuid.uuid4().hex[:8],
        ntype,
        message,
        "TRUE",
        created_by or "Admin",
        datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    ]
    ws = _worksheet()
    ws.append_row(row, value_input_option="USER_ENTERED")
    _invalidate()


def set_active(notice_id, active):
    ws = _worksheet()
    records = ws.get_all_records(expected_headers=HEADERS)
    col = HEADERS.index("active") + 1
    for i, rec in enumerate(records):
        if str(rec.get("id")) == str(notice_id):
            ws.update_cell(i + 2, col, "TRUE" if active else "FALSE")
            break
    _invalidate()


def delete_notice(notice_id):
    ws = _worksheet()
    records = ws.get_all_records(expected_headers=HEADERS)
    for i, rec in enumerate(records):
        if str(rec.get("id")) == str(notice_id):
            ws.delete_rows(i + 2)
            break
    _invalidate()


# ----------------------------------------------------------------------------
# Game Day Teams — read-only display of the league's PUBLIC teams sheet.
#
# Points at a SEPARATE, already-public spreadsheet ("JSSA Public Member View —
# Schedule & Teams"). We only ever read the roster block (names, positions,
# Home/Visitor, captain flags). We never read or display emails — the public
# sheet has none next to players, and member emails live in Tom's private
# back-end sheets that this app never touches.
# ----------------------------------------------------------------------------
TEAMS_SHEET_ID = os.environ.get(
    "TEAMS_SHEET_ID", "1oHgGae0aXVVsr7t9hmDmoLxZWO5p9rLFPebSsXoFfAA"
).strip()
TEAMS_TAB = os.environ.get("TEAMS_TAB", "Game_Day_Teams").strip()

_teams_cache = {"data": None, "ts": 0.0}
_TEAMS_TTL = 120  # seconds


def teams_is_configured():
    return bool(TEAMS_SHEET_ID and _SA_JSON)


def _teams_worksheet():
    import gspread
    from google.oauth2.service_account import Credentials

    info = json.loads(_SA_JSON)
    # Read-only scope is all we need for the public teams sheet.
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(TEAMS_SHEET_ID)
    try:
        return sh.worksheet(TEAMS_TAB)
    except Exception:
        # Fall back to the first tab if the name ever changes.
        return sh.get_worksheet(0)


def _clean(s):
    return str(s or "").strip()


def _is_field_label(text):
    """A column header that names a playing field/venue slot."""
    t = _clean(text).lower()
    return t.startswith("field") or "maplewood" in t


def _parse_marker(cell):
    """
    Turn a field-column cell into (side, is_captain) or None.
    Examples: 'H' -> ('Home', False); 'V Captain' -> ('Visitor', True).
    """
    t = _clean(cell)
    if not t:
        return None
    up = t.upper()
    side = None
    if up.startswith("H"):
        side = "Home"
    elif up.startswith("V"):
        side = "Visitor"
    if side is None:
        return None
    is_captain = "CAPTAIN" in up
    return side, is_captain


def _parse_teams_block(rows):
    """
    Parse the topmost game-day block from the worksheet's raw rows.
    Returns a structured dict or None.
    """
    # 1) Find the title row ("JSSA Game Day Teams").
    start = None
    for i, row in enumerate(rows):
        if row and "game day teams" in _clean(row[0]).lower():
            start = i
            break
    if start is None:
        return None

    # 2) Pull the human-readable date / park / info lines that follow the title,
    #    up until the counts row or the column-header row.
    date_str, park_str, info_str = "", "", ""
    header_idx = None
    field_cols = []  # (col_index, label)

    j = start + 1
    info_lines = []
    while j < len(rows):
        row = rows[j]
        first = _clean(row[0]) if row else ""
        low = first.lower()

        # Column header row: "Today's Players | Preferred Positions | Field ..."
        if low.startswith("today's player") or low.startswith("todays player"):
            header_idx = j
            for ci, cell in enumerate(row):
                if _is_field_label(cell):
                    field_cols.append((ci, _clean(cell)))
            break

        # Counts row like "48,16,0,16,16" — skip it.
        digits = [c for c in row if _clean(c)]
        if first and first.replace(",", "").isdigit():
            j += 1
            continue

        if first:
            info_lines.append(first)
        j += 1

    if header_idx is None or not field_cols:
        return None

    # Assign date / park / extra info from the collected lines.
    if len(info_lines) >= 1:
        date_str = info_lines[0]
    if len(info_lines) >= 2:
        park_str = info_lines[1]
    extras = [ln for ln in info_lines[2:] if ln]
    # Drop the prediction-game promo & "emails discontinued" reminder lines.
    extras = [
        e for e in extras
        if "prediction" not in e.lower() and "email" not in e.lower()
    ]
    info_str = " · ".join(extras)

    # 3) Build a field container per field column.
    fields = []
    col_to_field = {}
    for ci, label in field_cols:
        f = {"name": label, "home": [], "visitor": []}
        col_to_field[ci] = f
        fields.append(f)

    # 4) Walk player rows until a blank/terminating row.
    k = header_idx + 1
    while k < len(rows):
        row = rows[k]
        name = _clean(row[0]) if row else ""
        if not name:
            break
        # Stop if we hit the next block's title (shouldn't happen for topmost).
        if "game day teams" in name.lower():
            break

        positions = _clean(row[1]) if len(row) > 1 else ""

        placed = False
        for ci, fld in col_to_field.items():
            cell = row[ci] if len(row) > ci else ""
            parsed = _parse_marker(cell)
            if parsed:
                side, is_captain = parsed
                entry = {
                    "name": name,
                    "pos": positions,
                    "captain": is_captain,
                }
                (fld["home"] if side == "Home" else fld["visitor"]).append(entry)
                placed = True
                break
        k += 1
        if not placed:
            # Row had a name but no recognizable side marker; skip quietly.
            continue

    # Sort each side so captains come first, then alphabetical.
    for f in fields:
        for key in ("home", "visitor"):
            f[key].sort(key=lambda e: (not e["captain"], e["name"].lower()))

    total = sum(len(f["home"]) + len(f["visitor"]) for f in fields)

    return {
        "date": date_str,
        "park": park_str,
        "info": info_str,
        "fields": fields,
        "total_players": total,
    }


def game_day_teams():
    """
    Structured current-game roster, or None if unavailable.
    Cached briefly so we don't hit the Google API on every page view.
    """
    now = time.time()
    with _lock:
        if _teams_cache["data"] is not None and now - _teams_cache["ts"] < _TEAMS_TTL:
            return _teams_cache["data"]

    data = None
    try:
        if teams_is_configured():
            ws = _teams_worksheet()
            rows = ws.get_all_values()
            data = _parse_teams_block(rows)
        with _lock:
            _teams_cache["data"] = data
            _teams_cache["ts"] = now
        return data
    except Exception:
        # On any hiccup, return the last good value (may be None).
        return _teams_cache["data"]

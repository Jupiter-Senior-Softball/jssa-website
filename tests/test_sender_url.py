"""The sender address must be checked BEFORE the button is pressed.

Pasting the address the browser lands on after testing the script (a
googleusercontent "/macros/echo" address) reads fine but refuses to accept a
message with "405 Method Not Allowed" — so email silently never goes out.
That cost a live morning to diagnose; it must announce itself now."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "t"; os.environ["ADMIN_PASSWORD"] = "t"
import sheets, app as webapp

GOOD = "https://script.google.com/macros/s/AKfycbAAA/exec?key=secret"
ECHO = "https://script.googleusercontent.com/macros/echo?user_content_key=AUkAhnQ9"

cases = [
    (GOOD, "", "a correct /exec address"),
    (ECHO, "browser landed on", "the browser's echo address"),
    ("https://script.google.com/macros/s/AKfycbAAA/exec", "missing the ?key=",
     "no secret on the end"),
    ("https://script.google.com/macros/s/AKfycbAAA/dev?key=s", "private test address",
     "the /dev address"),
    ("https://example.com/hook?key=s", "does not look like an Apps Script",
     "some other website"),
    ("script.google.com/macros/s/AAA/exec?key=s", "should start with https://",
     "no https"),
    ("", "", "blank — nothing to complain about yet"),
]
print("Checking the address:\n")
for url, must, label in cases:
    got = sheets.sender_url_problem(url)
    print("  %-32s %s" % (label + ":", got[:64] + "..." if got else "OK"))
    if must:
        assert must in got, "%s -> %r" % (label, got)
    else:
        assert got == "", "%s -> %r" % (label, got)

# --- the warning must reach the page, before anything is sent ---------------
TODAY = datetime.datetime.now(sheets._EASTERN).date()
T = {"team": "Aces", "division": "RED", "manager": "Aces Mgr",
     "players": [{"name": "Aces P1"}, {"name": "Aces Mgr"}]}
sheets.league_season = lambda: {"schedule": [{"division": "RED",
    "date": TODAY.strftime("%m/%d/%Y"), "time": "9:00 AM", "field": "JCP",
    "home": "Aces", "away": "Aces", "status": ""}], "rosters": {"RED": [T], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [{"name": p["name"], "div": "RED",
    "email": p["name"].replace(" ", ".") + "@e.com", "phone": ""} for p in T["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []

def page(url):
    sheets.cancellation_settings = lambda: {"sender_url": url, "overflow_url": "",
        "cap": 100, "emails_enabled": True, "test_mode": True, "test_address": "t@e.com"}
    webapp.app.config["TESTING"] = True
    c = webapp.app.test_client()
    with c.session_transaction() as s: s["admin"] = True
    return c.get("/admin/cancel").get_data(as_text=True)

warn = "The sender address looks wrong"
assert warn in page(ECHO), "the page must warn about the echo address"
assert warn not in page(GOOD), "a good address must not be flagged"
print("\npage warns on the bad address, stays quiet on the good one: YES")

# --- a 405 failure must explain itself -------------------------------------
import urllib.request
def boom(*a, **k):
    raise urllib.error.HTTPError(ECHO, 405, "Method Not Allowed", {}, None)
urllib.request.urlopen = boom
res = sheets._post_to_sender(ECHO, "s", "b", ["a@b.com"])
print("\n405 on the echo address reports:\n  " + res["error"][:120] + "...")
assert not res["ok"] and "browser landed on" in res["error"]

res2 = sheets._post_to_sender(GOOD, "s", "b", ["a@b.com"])
assert "refused to accept a message" in res2["error"], res2["error"]
print("\n405 on a good-looking address reports:\n  " + res2["error"][:120] + "...")

print("\nSENDER URL CHECKS PASSED")

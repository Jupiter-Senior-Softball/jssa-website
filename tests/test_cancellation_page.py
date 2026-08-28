import os, sys, datetime, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "test-only-not-a-real-secret"
os.environ["ADMIN_PASSWORD"] = "test-only"
import sheets, app as webapp

TODAY = datetime.datetime.now(sheets._EASTERN).date()
DSTR = TODAY.strftime("%m/%d/%Y")

team = lambda n, d, c: {"team": n, "division": d, "manager": n + " Mgr",
    "players": [{"name": "%s P%02d" % (n, i)} for i in range(c)] + [{"name": n + " Mgr"}]}
A, B = team("Aces", "RED", 11), team("Bolts", "RED", 11)

sheets.league_season = lambda: {
    "schedule": [{"division": "RED", "date": DSTR, "time": "9:00 AM",
                  "field": "Jupiter Community Park", "home": "Aces",
                  "away": "Bolts", "status": ""}],
    "rosters": {"RED": [A, B], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [
    {"name": p["name"], "div": "RED",
     "email": p["name"].replace(" ", ".").lower() + "@e.com", "phone": ""}
    for t in (A, B) for p in t["players"] if p["name"] != "Aces P05"]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []
sheets.cancellation_settings = lambda: {
    "sender_url": "", "overflow_url": "", "cap": 100, "emails_enabled": True,
    "test_mode": False, "test_address": ""}

webapp.app.config["TESTING"] = True
c = webapp.app.test_client()

# not signed in -> must be turned away
r = c.get("/admin/cancel")
print("signed out  :", r.status_code, "->", r.headers.get("Location"))
assert r.status_code in (301, 302) and "login" in (r.headers.get("Location") or "")

with c.session_transaction() as s:
    s["admin"] = True

r = c.get("/admin/cancel")
html = r.get_data(as_text=True)
print("signed in   :", r.status_code, "| bytes:", len(html))
assert r.status_code == 200

for must in ["Cancel today's games", "Aces", "Bolts", "Jupiter Community Park",
             "Type <strong>CANCEL</strong>", "Aces P05", "Email isn't switched on yet"]:
    assert must in html, "MISSING FROM PAGE: " + must
print("page shows  : the game, the venue, the confirm box, the unreachable player,")
print("              and the 'email not set up yet' warning")

n = re.search(r'class="who">(\d+)', html)
print("headline    :", n.group(1), "would be emailed (24 scheduled, 1 has no email)")
assert n.group(1) == "23", n.group(1)

# posting without typing CANCEL must send nothing
sent = []
sheets.send_cancellation = lambda *a, **k: sent.append(a) or {"ok": True}
r = c.post("/admin/cancel/send", data={"reason": "rain", "confirm": ""})
print("no CANCEL   :", r.status_code, "-> redirected, sent nothing:", not sent)
assert not sent

r = c.post("/admin/cancel/send",
           data={"reason": "Fields flooded", "location": "Jupiter Community Park",
                 "sent_by": "Tom", "confirm": "cancel"})
print("typed CANCEL:", r.status_code, "-> send_cancellation called:", bool(sent))
assert sent and sent[0][0] == "Fields flooded" and sent[0][2] == "Tom"

print("\nPAGE CHECKS PASSED")

"""Exercise the cancellation planner with fake sheet data — no Google needed."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_JSON", "")
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()
DSTR = TODAY.strftime("%m/%d/%Y")

# --- fake league data -------------------------------------------------------
def make_team(team, div, n, start):
    return {"team": team, "division": div, "manager": "%s Manager" % team,
            "players": [{"name": "%s Player%02d" % (team, i)}
                        for i in range(start, start + n)]
                       + [{"name": "%s Manager" % team}]}

RED_A, RED_B = make_team("Aces", "RED", 12, 1), make_team("Bolts", "RED", 12, 1)
WHT_A, WHT_B = make_team("Comets", "WHITE", 12, 1), make_team("Ducks", "WHITE", 12, 1)

SEASON = {
    "schedule": [
        {"division": "RED", "date": DSTR, "time": "9:00 AM",
         "field": "Jupiter Community Park", "home": "Aces", "away": "Bolts",
         "status": ""},
        {"division": "WHITE", "date": DSTR, "time": "11:00 AM",
         "field": "Maplewood Park", "home": "Comets", "away": "Ducks",
         "status": ""},
        # yesterday's game must be ignored
        {"division": "BLUE", "date": (TODAY - datetime.timedelta(days=1)).strftime("%m/%d/%Y"),
         "time": "9:00 AM", "field": "X", "home": "Eagles", "away": "Falcons",
         "status": "Final"},
    ],
    "rosters": {"RED": [RED_A, RED_B], "WHITE": [WHT_A, WHT_B], "BLUE": []},
}

def fake_directory():
    players = []
    for t in (RED_A, RED_B, WHT_A, WHT_B):
        for p in t["players"]:
            # leave two people off the directory entirely
            if p["name"] in ("Aces Player03", "Ducks Player07"):
                continue
            players.append({"name": p["name"], "div": t["division"],
                            "email": p["name"].replace(" ", ".").lower() + "@example.com",
                            "phone": ""})
    # a "Bob"/"Robert" style mismatch the loose matcher should still catch
    players.append({"name": "Robert Smith", "div": "RED",
                    "email": "rsmith@example.com", "phone": ""})
    return {"players": players}

sheets.league_season = lambda: SEASON
sheets.player_directory = fake_directory
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []
sheets.cancellation_settings = lambda: {
    "sender_url": "https://example.test/exec?key=x", "overflow_url": "",
    "cap": 100, "emails_enabled": True, "test_mode": False, "test_address": ""}

plan = sheets.todays_cancellation_plan()
print("kind         :", plan["kind"])
print("date_label   :", plan["date_label"])
print("location     :", plan["location"])
print("games        :", len(plan["games"]), "(yesterday's excluded)")
print("scheduled    :", len(plan["people"]))
print("will email   :", len(plan["recipients"]))
print("unmatched    :", [p["name"] for p in plan["unmatched"]])
print("first 4 (leads first):")
for p in plan["recipients"][:4]:
    print("   ", p["name"], "| lead:", p["is_lead"])

assert plan["kind"] == "LEAGUE"
assert len(plan["games"]) == 2, plan["games"]
assert len(plan["people"]) == 52, len(plan["people"])
assert sorted(p["name"] for p in plan["unmatched"]) == ["Aces Player03", "Ducks Player07"]
assert all(p["is_lead"] for p in plan["recipients"][:4]), "managers must come first"
assert "Jupiter Community Park" in plan["location"] and "Maplewood" in plan["location"]

# --- the cap ---------------------------------------------------------------
sheets.cancellation_settings = lambda: {
    "sender_url": "u", "overflow_url": "", "cap": 20, "emails_enabled": True,
    "test_mode": False, "test_address": ""}
capped = sheets.todays_cancellation_plan()
assert len(capped["recipients"]) == 20
assert len(capped["over_cap"]) == 30, len(capped["over_cap"])
leads = [p["name"] for p in capped["recipients"] if p["is_lead"]]
assert len(leads) == 4, leads
print("\ncap 20       : %d emailed, %d over cap, all %d managers included"
      % (len(capped["recipients"]), len(capped["over_cap"]), len(leads)))

# --- overflow account doubles the reach ------------------------------------
sheets.cancellation_settings = lambda: {
    "sender_url": "u", "overflow_url": "u2", "cap": 20, "emails_enabled": True,
    "test_mode": False, "test_address": ""}
over = sheets.todays_cancellation_plan()
assert over["cap"] == 40 and len(over["recipients"]) == 40, over["cap"]
print("with backup  : cap %d, %d emailed, %d over cap"
      % (over["cap"], len(over["recipients"]), len(over["over_cap"])))

# --- the message -----------------------------------------------------------
subj, body = sheets._cancellation_message(plan, "Fields are flooded.",
                                          plan["location"])
print("\n--- subject ---\n" + subj)
print("--- body ---\n" + body)
assert "CANCELLED" in subj and "do not travel" in body.lower()
print("\nALL CHECKS PASSED")

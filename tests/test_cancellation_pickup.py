import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()

BLOCK = {
    "date": TODAY.strftime("%A, %B %d, %Y"),
    "park": "Jupiter Community Park",
    "fields": [
        {"name": "Field 1",
         "home":    [{"name": "Al Adams", "captain": True}] +
                    [{"name": "P%02d Home1" % i, "captain": False} for i in range(9)],
         "visitor": [{"name": "Bo Baker", "captain": True}] +
                    [{"name": "P%02d Vis1" % i, "captain": False} for i in range(9)]},
        {"name": "Field 2",
         "home":    [{"name": "Cy Clark", "captain": True}] +
                    [{"name": "P%02d Home2" % i, "captain": False} for i in range(9)],
         "visitor": [{"name": "Dy Davis", "captain": True}] +
                    [{"name": "P%02d Vis2" % i, "captain": False} for i in range(9)]},
    ],
}

def directory():
    out = []
    for f in BLOCK["fields"]:
        for side in ("home", "visitor"):
            for p in f[side]:
                out.append({"name": p["name"], "div": "RED",
                            "email": p["name"].replace(" ", ".").lower() + "@e.com",
                            "phone": ""})
    return {"players": out}

sheets.league_season = lambda: {"schedule": [], "rosters": {"RED": [], "WHITE": [], "BLUE": []}}
sheets.player_directory = directory
sheets.game_day_teams = lambda enforce_date_window=True: BLOCK
sheets.pickup_game_venue = lambda date_str=None: "Jupiter Community Park"
sheets._cancel_log_rows = lambda: []
sheets.cancellation_settings = lambda: {
    "sender_url": "u", "overflow_url": "", "cap": 100, "emails_enabled": True,
    "test_mode": False, "test_address": ""}

plan = sheets.todays_cancellation_plan()
print("kind      :", plan["kind"])
print("location  :", plan["location"])
print("scheduled :", len(plan["people"]), "| emailing:", len(plan["recipients"]))
print("captains first:", [p["name"] for p in plan["recipients"][:4]])
assert plan["kind"] == "PICKUP"
assert len(plan["people"]) == 40
assert all(p["is_lead"] for p in plan["recipients"][:4])
assert plan["location"] == "Jupiter Community Park"

subj, _ = sheets._cancellation_message(plan, "", plan["location"])
print("subject   :", subj)
assert "pickup games" in subj

# a roster published for YESTERDAY must not count as today
BLOCK["date"] = (TODAY - datetime.timedelta(days=1)).strftime("%A, %B %d, %Y")
stale = sheets.todays_cancellation_plan()
print("\nyesterday's roster -> kind:", stale["kind"], "| recipients:", len(stale["recipients"]))
assert stale["kind"] == "NONE" and not stale["recipients"]

print("\nPICKUP CHECKS PASSED")

"""Teams by Division page: teams named on the Teams tab or Schedule appear even
before they have players. Fake data only — never touches Google."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["ADMIN_PASSWORD"] = "adminpw"
os.environ["SECRET_KEY"] = "test"

import sheets

rosters = {"RED": [{"team": "Team Red", "players": [{"name": "A B"}] * 73, "manager": "", "count": 73}],
           "WHITE": [{"team": "Team White", "players": [{"name": "C D"}], "manager": "", "count": 1}],
           "BLUE": []}
extra = [("RED", "Team Red"), ("RED", "JACKALS"), ("RED", "Mick’s Picks"),
         ("RED", "Mick's Picks"), ("RED", "  jackals "), ("BLUE", "Team Blue"),
         ("", "Nowhere"), ("RED", "")]
out = sheets._league_team_list(rosters, extra)
names = {d: [t["team"] for t in out[d]] for d in out}
assert names["RED"] == ["Team Red", "JACKALS", "Mick’s Picks"], names   # no duplicates
assert names["BLUE"] == ["Team Blue"] and names["WHITE"] == ["Team White"], names
assert out["RED"][0]["count"] == 73 and out["RED"][1]["count"] == 0
assert len(rosters["RED"]) == 1            # inputs untouched

import app as appmod
season = {"standings": {"RED": [], "WHITE": [], "BLUE": []}, "schedule": [], "results": [],
          "rosters": rosters, "teams": out}
sheets.league_season = lambda: season
c = appmod.app.test_client()
html = c.get("/league/teams").get_data(as_text=True)
assert "JACKALS" in html and "Team Red" in html and "Team Blue" in html
assert "0 players" in html and "73 players" in html
assert html.count("View Team Photo") == 2          # only teams WITH players link to photos
print("ok")

"""League Schedule / Results / Rosters: every card carries its team names so the
team picker (templates/_teampicker.html) can show just one team. Server-side markup
only: the buttons themselves are built in the browser. Fake data, never touches Google."""
import os, sys, re, html as htmllib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["ADMIN_PASSWORD"] = "adminpw"
os.environ["SECRET_KEY"] = "test"

import sheets
import app as appmod

def game(div, away, home, ump=()):
    return {"division": div, "dow": "Monday", "date": "10/19/2026", "time": "9:00 AM", "field": "Field 1",
            "away": away, "home": home, "umpires": list(ump), "score_home": "", "score_away": "", "status": ""}

def result(div, away, home):
    return {"division": div, "dow": "Friday", "date": "10/16/2026", "time": "9:00 AM", "field": "Field 1",
            "away": away, "home": home, "home_score": "7", "away_score": "5", "result": ""}

def team(name):
    return {"team": name, "manager": "", "count": 1,
            "players": [{"slug": "p-" + str(abs(hash(name)) % 999), "name": "A B", "is_manager": True}]}

rosters = {"RED": [team("Mick's Picks"), team('Quote "Q" & Co')], "WHITE": [team("Hawks")], "BLUE": []}
season = {"standings": {"RED": [], "WHITE": [], "BLUE": []},
          "schedule": [game("RED", "Knee'd To Win", "Bad Moon Rising", ["Mick's Picks"]),
                       game("RED", 'Quote "Q" & Co', "Mick’s Picks", ["Ron Nolan", "Pat Smith"]),
                       game("WHITE", "Hawks", "Owls")],
          "results": [result("RED", "Jackals", "Mick's Picks")],
          "rosters": rosters, "teams": rosters, "umpires_enabled": True}
sheets.league_season = lambda: season
sheets.player_cards = lambda: {}
c = appmod.app.test_client()

def attrs(page, name):
    # attribute values as the BROWSER will read them (entities decoded)
    return [htmllib.unescape(v) for v in re.findall(name + r'="([^"]*)"', page)]

# ---- schedule: teams on each card, umpiring teams in data-also
page = c.get("/league/schedules").get_data(as_text=True)
assert '{% include' not in page and "jssaPickDivision" in page and 'id="teampick"' in page
teams = attrs(page, "data-teams")
assert "Knee'd To Win||Bad Moon Rising" in teams, teams
assert 'Quote "Q" & Co||Mick’s Picks' in teams, teams          # quotes/ampersand survive
assert "Hawks||Owls" in teams
also = attrs(page, "data-also")
assert "Mick's Picks" in also and "Ron Nolan||Pat Smith" in also and "" in also, also
assert page.count('class="gcard') == 3

# ---- results
page = c.get("/league/results").get_data(as_text=True)
assert attrs(page, "data-teams") == ["Jackals||Mick's Picks"], attrs(page, "data-teams")
assert 'id="teampick"' in page

# ---- rosters: one tag per team card
page = c.get("/league/rosters").get_data(as_text=True)
assert sorted(attrs(page, "data-teams")) == sorted(["Mick's Picks", 'Quote "Q" & Co', "Hawks"]), attrs(page, "data-teams")
assert page.count('class="tcard') == 3 and 'id="teampick"' in page

# ---- the division picker still announces its picks and can be driven by the team picker
dp = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "_divpicker.html"),
          encoding="utf-8").read()
assert "divpicked" in dp and "window.jssaPickDivision" in dp

# ---- other league pages (standings, teams) are untouched: no team picker
season["standings"] = {"RED": [{"team": "X", "wins": "1", "losses": "0", "pct": ".1000", "gb": "-",
                                "rf": "5", "ra": "2", "diff": "3"}], "WHITE": [], "BLUE": []}
resp = c.get("/league/standings")
assert resp.status_code == 200, resp.status_code      # a real page, not an error page
assert "X" in resp.get_data(as_text=True) and 'id="teampick"' not in resp.get_data(as_text=True)
print("ok")

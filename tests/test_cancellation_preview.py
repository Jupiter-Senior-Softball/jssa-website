import os, sys, datetime, re, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"]="t"; os.environ["ADMIN_PASSWORD"]="t"
import sheets, app as webapp

TODAY = datetime.datetime.now(sheets._EASTERN).date()
DSTR = TODAY.strftime("%m/%d/%Y")
T = {"team":"Aces","division":"RED","manager":"Aces Mgr",
     "players":[{"name":"Aces P1"},{"name":"Aces Mgr"}]}
U = {"team":"Bolts","division":"RED","manager":"Bolts Mgr",
     "players":[{"name":"Bolts P1"},{"name":"Bolts Mgr"}]}
sheets.league_season = lambda: {"schedule":[{"division":"RED","date":DSTR,"time":"9:00 AM",
    "field":"Jupiter Community Park","home":"Aces","away":"Bolts","status":""}],
    "rosters":{"RED":[T,U],"WHITE":[],"BLUE":[]}}
sheets.player_directory = lambda: {"players":[{"name":p["name"],"div":"RED",
    "email":p["name"].replace(" ",".").lower()+"@e.com","phone":""}
    for t in (T,U) for p in t["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets._cancel_log_rows = lambda: []
sheets.cancellation_settings = lambda: {"sender_url":"u","overflow_url":"","cap":100,
    "emails_enabled":True,"test_mode":True,"test_address":"tom@example.com"}

webapp.app.config["TESTING"]=True
c = webapp.app.test_client()
with c.session_transaction() as s: s["admin"]=True
html = c.get("/admin/cancel").get_data(as_text=True)
assert "Practice mode is ON" in html
assert "not one of the 4 scheduled players will be emailed" in html
assert "The schedule is not touched" in html
print("practice-mode notice: shown, with the right player count")

tpl = json.loads(re.search(r'var TPL = (\{.*?\});', html, re.S).group(1))

def fill(s, r, l):
    s = s.replace("__LOCATION__", l) if l else s.replace(" at __LOCATION__", "")
    if r:
        s = s.replace("__REASON__", r)
    else:
        s = re.sub(r'\n*Reason: __REASON__\n?', '\n', s)
        s = s.replace(" __REASON__", "").replace("__REASON__", "")
    return re.sub(r'[ \t]+\n', '\n', s).strip()

print("\n--- banner, as a visitor sees it ---")
print(fill(tpl["headline"], "Fields are flooded.", "Jupiter Community Park"))
print("\n--- email ---")
print("Subject:", fill(tpl["subject"], "Fields are flooded.", "Jupiter Community Park"))
print(fill(tpl["body"], "Fields are flooded.", "Jupiter Community Park"))

# what it looks like before anything is typed
bare = fill(tpl["headline"], "", "")
print("\n--- banner with nothing typed yet ---")
print(bare)
assert "__" not in bare and "  " not in bare, bare
body_bare = fill(tpl["body"], "", "Jupiter Community Park")
assert "__" not in body_bare and "Reason:" not in body_bare

# the preview must equal what the real send produces
plan = sheets.todays_cancellation_plan()
real_subj, real_body = sheets._cancellation_message(plan, "Fields are flooded.",
                                                    "Jupiter Community Park")
assert fill(tpl["subject"], "Fields are flooded.", "Jupiter Community Park") == real_subj.strip()
assert fill(tpl["body"], "Fields are flooded.", "Jupiter Community Park") == real_body.strip()
print("\npreview matches the real email exactly: YES")
print("\nPREVIEW CHECKS PASSED")

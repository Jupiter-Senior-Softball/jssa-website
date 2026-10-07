"""Site Settings tab: new tab wins, old tabs are the fallback. No Google calls."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "t"; os.environ["ADMIN_PASSWORD"] = "t"
import sheets

fails = []
def check(name, got, want):
    if got != want:
        fails.append("%s: got %r, wanted %r" % (name, got, want))

def setup(settings, controls, passwords):
    sheets._site_settings = lambda: dict(settings)
    sheets._website_controls = lambda: dict(controls)
    sheets._site_passwords = lambda: dict(passwords)

setup({}, {}, {})
check("defaults: season", sheets.season_mode(), "PICKUP")
check("defaults: members", sheets.members_page_on(), False)
check("defaults: gallery on", sheets.photo_gallery_on(), True)
check("defaults: name", sheets.season_name(), "League Season")
check("defaults: no password", sheets.admin_password(), "")

setup({"seasonmode": "League", "seasonname": "Fall 2026 Season",
       "memberspage": "ON", "photogallery": "OFF",
       "adminpassword": "new", "divisionspassword": "div"},
      {"season mode": "Pickup", "members page": "OFF"},
      {"admin password": "old"})
check("new tab wins: season", sheets.season_mode(), "LEAGUE")
check("new tab: name", sheets.season_name(), "Fall 2026 Season")
check("new tab: members", sheets.members_page_on(), True)
check("new tab: gallery off", sheets.photo_gallery_on(), False)
check("new tab: admin pw", sheets.admin_password(), "new")
check("new tab: divisions pw", sheets.divisions_password(), "div")

setup({}, {"season mode": "LEAGUE", "members page": "ON"},
      {"admin password": "old", "divisions password": "d"})
check("fallback: season", sheets.season_mode(), "LEAGUE")
check("fallback: members", sheets.members_page_on(), True)
check("fallback: admin pw", sheets.admin_password(), "old")
check("fallback: divisions pw", sheets.divisions_password(), "d")

setup({"photogalleryenabled": "FALSE"}, {}, {})
check("gallery 'Enabled' label", sheets.photo_gallery_on(), False)

# the homepage really hides / shows the photo section
import app as webapp
sheets.game_day_teams = lambda enforce_date_window=True: {"fields": []}
sheets.roster_button_mode = lambda: "AUTO"
sheets.blackboard_posts = lambda: []; sheets.board_members = lambda: []
sheets.sponsors = lambda: []; sheets.record_home_view = lambda: None
sheets.home_view_count = lambda: 1; sheets.active_notice = lambda: None
webapp.app.config["TESTING"] = True
c = webapp.app.test_client()
setup({"photogallery": "OFF"}, {}, {})
check("home hides photos", 'id="highlights"' in c.get("/").get_data(as_text=True), False)
setup({}, {}, {})
check("home shows photos", 'id="highlights"' in c.get("/").get_data(as_text=True), True)

print("\n".join(fails) if fails else "ALL PASS")
sys.exit(1 if fails else 0)

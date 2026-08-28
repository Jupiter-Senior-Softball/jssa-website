"""The homepage must not advertise "rosters are posted" under a cancellation."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "t"; os.environ["ADMIN_PASSWORD"] = "t"
import sheets, app as webapp

BTN = 'id="rosterBtn"'  # the real hero link; the button text also appears in a CSS comment

sheets.game_day_teams = lambda enforce_date_window=True: {"fields": []}
sheets.roster_button_mode = lambda: "AUTO"
sheets.blackboard_posts = lambda: []
sheets.board_members = lambda: []
sheets.sponsors = lambda: []
sheets.record_home_view = lambda: None
sheets.home_view_count = lambda: 1
webapp.app.config["TESTING"] = True
c = webapp.app.test_client()

def page(notice):
    sheets.active_notice = lambda: notice
    return c.get("/").get_data(as_text=True)

cases = [
    ("no notice at all", None, True),
    ("an ordinary announcement", {"type": "announcement",
        "message": "Picnic Saturday!", "url": "", "link_text": ""}, True),
    ("an ordinary weather note", {"type": "weather",
        "message": "Heavy rain expected later today.", "url": "", "link_text": ""}, True),
    ("the cancel button's notice", {"type": "weather",
        "message": "CANCELLED — no games today, Friday at Jupiter Community Park. Fields flooded.",
        "url": "", "link_text": ""}, False),
    ("a hand-typed cancellation", {"type": "weather",
        "message": "Games are cancelled today, fields are under water",
        "url": "", "link_text": ""}, False),
    ("American spelling", {"type": "weather",
        "message": "Today's games have been canceled.", "url": "", "link_text": ""}, False),
]

for label, notice, expect_button in cases:
    html = page(notice)
    shown = BTN in html
    print("%-28s button shown: %-5s (want %s)" % (label, shown, expect_button))
    assert shown == expect_button, label

# the manual ON override must not resurrect it during a cancellation
sheets.roster_button_mode = lambda: "ON"
html = page({"type": "weather", "message": "CANCELLED — no games today.",
             "url": "", "link_text": ""})
print("%-28s button shown: %-5s (want False)" % ("forced ON + cancellation", BTN in html))
assert BTN not in html, "a cancellation must beat the manual ON switch"

# and it comes straight back once the notice is switched off
sheets.roster_button_mode = lambda: "AUTO"
assert BTN in page(None)
print("\nbutton returns as soon as the notice is off: YES")
print("\nROSTER BUTTON CHECKS PASSED")

"""The cancellation email wording, now editable from the control sheet.

Proves four things that matter at 7am on a wet morning:

  1. With no tab (or an unreachable sheet) the wording that goes out is
     exactly what it is today, character for character.
  2. Whatever the board types into the "Cancellation Email" tab is what
     players receive, and an edit applies to the very next cancellation.
  3. The page can always tell you WHICH of those two is in use.
  4. The optional pieces — the reason, the location, the list of league
     games — vanish cleanly when there is nothing to put there, instead of
     leaving an empty heading or a dangling " at " behind.

Nothing here touches Google.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

failures = []


def check(label, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + label +
          (("  -> " + detail) if detail and not condition else ""))
    if not condition:
        failures.append(label)


DAY = datetime.date(2026, 10, 30)

GAMES = [
    {"time": "9:00 AM", "division": "RED", "home": "Aces", "away": "Bolts",
     "field": "Field 1"},
    {"time": "9:00 AM", "division": "BLUE", "home": "Cubs", "away": "Ducks",
     "field": "Field 3"},
]


def plan(kind="BOTH", games=None):
    return {"kind": kind, "date": DAY, "date_label": "Friday, October 30",
            "games": GAMES if games is None else games}


def no_tab():
    """No control sheet at all — the fallback path."""
    sheets.CONTROL_SHEET_ID = ""
    sheets._cancel_email_cache["data"] = None
    sheets._cancel_email_cache["ts"] = 0.0


def tab_says(subject, body):
    """Pretend the Cancellation Email tab holds this wording."""
    sheets.CONTROL_SHEET_ID = "fake-control-sheet"
    sheets._SA_JSON = "{}"
    sheets._control_tab_rows = lambda tab, headers, seed: [
        headers, ["Subject", subject, ""], ["Body", body, ""]]
    sheets._cancel_email_cache["data"] = None
    sheets._cancel_email_cache["ts"] = 0.0


# ----------------------------------------- 1. today's wording, unchanged
no_tab()
subject, body = sheets._cancellation_message(
    plan(), "Fields are flooded", "Jupiter Community Park")

EXPECTED = """TODAY'S JSSA GAMES HAVE BEEN CANCELLED.

The JSSA games scheduled for Friday, October 30 at Jupiter Community Park \
have been cancelled.

Please do not travel to the field.

Reason: Fields are flooded

This notice has also been posted on our website at: \
https://jupiterseniorsoftball.com

Jupiter Senior Softball Association"""

check("with no tab, the email is exactly the wording it is today",
      body == EXPECTED, repr(body))
check("and the subject is unchanged",
      subject == "CANCELLED — today's JSSA league and pickup games (Fri, Oct 30)",
      subject)
check("the fallback reports itself as built-in",
      sheets.cancellation_email_template()["source"] == "built-in")

# A sheet that throws must not take the email down with it.
sheets.CONTROL_SHEET_ID = "fake-control-sheet"
sheets._SA_JSON = "{}"


def boom(*a, **k):
    raise RuntimeError("Google is having a bad morning")


sheets._control_tab_rows = boom
sheets._cancel_email_cache["data"] = None
sheets._cancel_email_cache["ts"] = 0.0
subject, body = sheets._cancellation_message(plan(), "Flooded", "JCP")
check("an unreachable control sheet falls back instead of failing",
      body == EXPECTED.replace("Fields are flooded", "Flooded")
                      .replace("Jupiter Community Park", "JCP"),
      repr(body))

# ------------------------------------- 2. the board's own wording wins
tab_says(
    "No JSSA {games} today ({date})",
    "Good morning.\n\n"
    "Today's {games} at {location} are OFF.\n"
    "{reason_block}"
    "Please stay home — do not drive to the fields.\n\n"
    "See {website}")

subject, body = sheets._cancellation_message(
    plan(), "Fields are flooded", "Jupiter Community Park")

check("the subject comes from the sheet",
      subject == "No JSSA league and pickup games today (Fri, Oct 30)", subject)
check("the body comes from the sheet",
      body.startswith("Good morning.") and "do not drive to the fields" in body,
      repr(body))
check("{location} is filled in", "at Jupiter Community Park are OFF" in body,
      repr(body))
check("{reason_block} brings the reason with it",
      "Reason: Fields are flooded" in body, repr(body))
check("{website} is filled in",
      body.rstrip().endswith("https://jupiterseniorsoftball.com"), repr(body))
check("the board's wording replaces the built-in wording completely",
      "TODAY'S JSSA GAMES HAVE BEEN CANCELLED." not in body, repr(body))

# ------------------------------------- 3. which one is in use is knowable
check("the sheet's wording reports itself as coming from the sheet",
      sheets.cancellation_email_template()["source"] == "sheet")

# An edit must apply to the NEXT cancellation, not the one after that.
tab_says("Changed subject {date}", "Changed body for {games}.")
subject, body = sheets._cancellation_message(plan(), "", "")
check("editing the tab changes the very next cancellation",
      subject == "Changed subject Fri, Oct 30" and
      body == "Changed body for league and pickup games.",
      subject + " | " + repr(body))

# A blank Value falls back rather than sending an empty email.
tab_says("", "")
subject, body = sheets._cancellation_message(plan(), "Flooded", "JCP")
check("a cleared cell falls back to the built-in wording",
      "TODAY'S JSSA GAMES HAVE BEEN CANCELLED." in body, repr(body[:50]))
check("and says so, so nobody wonders why their edit vanished",
      sheets.cancellation_email_template()["source"] == "built-in")

# A misspelled placeholder is left visible rather than crashing.
tab_says("S", "Reason was {resaon} and {games} today.")
subject, body = sheets._cancellation_message(plan(), "Flooded", "JCP")
check("a misspelled placeholder shows up instead of breaking the send",
      "{resaon}" in body and "league and pickup games" in body, repr(body))

# The games list is available to the board even though the default drops it.
tab_says("S", "Off today.{games_block}")
subject, body = sheets._cancellation_message(plan(), "", "")
check("the board can put the list of games back if they want it",
      "Cancelled games:" in body and "Aces vs Bolts" in body, repr(body))

# ------------------------------------- 4. the optional pieces vanish
no_tab()

subject, body = sheets._cancellation_message(plan(kind="PICKUP", games=[]), "", "")
check("no reason typed leaves no empty 'Reason:' heading",
      "Reason" not in body, repr(body))
check("no location leaves no dangling ' at '",
      "scheduled for Friday, October 30 have been cancelled" in body, repr(body))
check("there are never two blank lines in a row",
      "\n\n\n" not in body, repr(body))
check("it still says the thing that matters",
      body.startswith("TODAY'S JSSA GAMES HAVE BEEN CANCELLED.") and
      "do not travel" in body.lower(), repr(body[:80]))
check("a pickup-only day still says pickup games in the subject",
      "pickup games" in subject and "league" not in subject, subject)

subject, body = sheets._cancellation_message(plan(games=[]), "Lightning", "JCP")
check("a reason with no games still reads properly",
      "Reason: Lightning" in body and "\n\n\n" not in body, repr(body))

print()
if failures:
    print("FAILURES: " + ", ".join(failures))
    sys.exit(1)
print("CANCELLATION WORDING CHECKS PASSED")

"""Calling off TOMORROW's games, the afternoon before.

Pickup sign-ups close at 3 PM the day before, so once that deadline passes
the list of who is actually playing tomorrow is final — and a washout can be
called then rather than at 6am the next morning.

What this has to get right, and what these checks cover:

  * the right day's players are emailed, not today's
  * the email and the banner say "tomorrow", never "today"
  * the banner stays up THROUGH tomorrow morning instead of coming down
    tonight, which is the trap: the default shutoff is 1 PM, and 1 PM today
    has already gone by the time anyone calls a game off in the afternoon
  * cancelling tomorrow does not count as cancelling today, and vice versa

Nothing here touches Google and nothing can send an email.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "t"
import sheets
import app as webapp

failures = []


def check(label, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + label +
          (("  -> " + detail) if detail and not condition else ""))
    if not condition:
        failures.append(label)


TODAY = datetime.datetime.now(sheets._EASTERN).date()
TOMORROW = TODAY + datetime.timedelta(days=1)

# Who is on each day's list — deliberately different, so a mix-up shows up.
PEOPLE = {
    TODAY: [{"name": "Sunday Sam", "email": "sam@e.com"}],
    TOMORROW: [{"name": "Monday Mike", "email": "mike@e.com"},
               {"name": "Monday Moe", "email": "moe@e.com"}],
}

SETTINGS = {"sender_url": "https://script.google.com/x/exec", "overflow_url": "",
            "cap": 100, "emails_enabled": True, "test_mode": False,
            "test_address": ""}


def plan_for(day=None):
    day = day or TODAY
    return {"date": day, "date_label": day.strftime("%A, %B %-d"),
            "kind": "BOTH", "games": [], "location": "Jupiter Community Park",
            "people": PEOPLE[day], "recipients": PEOPLE[day],
            "unmatched": [], "over_cap": [], "cap": 100,
            "settings": dict(SETTINGS), "already_sent": None}


sheets.todays_cancellation_plan = plan_for
sheets.is_configured = lambda: True
sheets.admin_password = lambda: "t"
sheets.CONTROL_SHEET_ID = ""          # use the built-in wording
sheets._cancel_email_cache["data"] = None
sheets._cancel_email_cache["ts"] = 0.0

# ------------------------------------------------------------ the wording
subj_today, body_today = sheets._cancellation_message(
    plan_for(TODAY), "Fields are flooded", "Jupiter Community Park")
subj_tom, body_tom = sheets._cancellation_message(
    plan_for(TOMORROW), "Fields are flooded", "Jupiter Community Park")

check("today's email still says today",
      subj_today.startswith("CANCELLED — today's") and
      body_today.startswith("TODAY'S JSSA GAMES"), subj_today)
check("tomorrow's email says tomorrow, not today",
      subj_tom.startswith("CANCELLED — tomorrow's") and
      body_tom.startswith("TOMORROW'S JSSA GAMES"), subj_tom)
check("tomorrow's email names tomorrow's date",
      TOMORROW.strftime("%A, %B %-d") in body_tom and
      TODAY.strftime("%A, %B %-d") not in body_tom, repr(body_tom))
check("the word 'today' appears nowhere in tomorrow's email",
      "today" not in body_tom.lower() and "today" not in subj_tom.lower(),
      repr(body_tom))

# ------------------------------------------------- the banner's shutoff time
# This is the trap. Posted at, say, 4 PM, the 1 PM default has already gone,
# so a same-day banner falls back to 11:59 tonight. A banner about TOMORROW
# must not do that — it has to still be up in the morning.
afternoon = datetime.datetime.combine(
    TODAY, datetime.time(16, 0), tzinfo=sheets._notice_tz()
).astimezone(datetime.timezone.utc)

exp_today, fell_today = sheets.shutoff_for_new_post("", now=afternoon,
                                                    on_date=TODAY)
exp_tom, fell_tom = sheets.shutoff_for_new_post("", now=afternoon,
                                                on_date=TOMORROW)


def as_local(iso):
    return (datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
            .astimezone(sheets._notice_tz()))


check("a banner about today posted at 4 PM lasts until tonight",
      as_local(exp_today).date() == TODAY and fell_today,
      exp_today)
check("a banner about tomorrow survives tonight",
      as_local(exp_tom).date() == TOMORROW, exp_tom)
check("and comes down at 1 PM tomorrow, after the games would have finished",
      as_local(exp_tom).hour == 13 and not fell_tom, exp_tom)

# ------------------------------------------------------- the right day's list
sent = {}


def fake_post(url, subject, body, recipients, test_to=""):
    sent["subject"] = subject
    sent["recipients"] = list(recipients)
    return {"ok": True, "sent": len(recipients)}


sheets._post_to_sender = fake_post
sheets.cancellation_already_sent = lambda day=None: None
sheets.add_notice = lambda *a, **k: sent.__setitem__("headline", a[1])
sheets._mark_league_games_cancelled = lambda d: 0
sheets._log_cancellation = lambda *a: sent.__setitem__("logged", a[0]["date"])
sheets._invalidate = lambda: None

res = sheets.send_cancellation("Fields are flooded", "", "Tom",
                               plan=plan_for(TOMORROW))
check("tomorrow's players are the ones emailed",
      sorted(sent["recipients"]) == ["mike@e.com", "moe@e.com"],
      str(sent.get("recipients")))
check("today's player is NOT emailed",
      "sam@e.com" not in sent["recipients"], str(sent.get("recipients")))
check("the banner headline says tomorrow",
      "no games tomorrow" in sent["headline"], sent.get("headline"))
check("the log records tomorrow's date, not today's",
      sent.get("logged") == TOMORROW, str(sent.get("logged")))
check("it reports what it did", res.get("emailed") == 2, str(res))

# --------------------------------------- the two days don't block each other
sheets.cancellation_already_sent = lambda day=None: (
    {"sent_at": "4:10 PM", "sent_by": "Tom"} if day == TOMORROW else None)

blocked = sheets.send_cancellation("again", "", "Tom", plan=plan_for(TOMORROW))
check("sending twice for tomorrow is refused",
      not blocked["ok"] and "Already sent" in blocked["note"], str(blocked))
check("and the refusal names the day so it isn't confusing",
      TOMORROW.strftime("%A, %B %-d") in blocked["note"], blocked["note"])

sent.clear()
ok_today = sheets.send_cancellation("rain", "", "Tom", plan=plan_for(TODAY))
check("cancelling tomorrow does not block cancelling today",
      ok_today.get("emailed") == 1 and sent["recipients"] == ["sam@e.com"],
      str(ok_today))

# ------------------------------------------------------------- the page
webapp.app.config["TESTING"] = True
c = webapp.app.test_client()
c.post("/admin/login", data={"password": "t"})

r = c.get("/admin/cancel?day=tomorrow")
html = r.get_data(as_text=True)
check("the page opens on tomorrow when asked", r.status_code == 200,
      str(r.status_code))
check("it is titled for tomorrow", "Cancel Tomorrow" in html)
check("it warns loudly which day this is", "calling off TOMORROW" in html)
check("it shows tomorrow's date", TOMORROW.strftime("%A, %B %-d") in html)
check("it reminds you about the 3 PM sign-up deadline", "3 PM" in html)
check("the form carries the day so the send can't drift back to today",
      'name="day" value="tomorrow"' in html)

r = c.get("/admin/cancel")
html = r.get_data(as_text=True)
check("with no day given it is still today", "Cancel Today" in html and
      'name="day" value="today"' in html)

# A send with no CANCEL typed must stay on the day you were looking at.
posted = {}
sheets.send_cancellation = lambda *a, **k: posted.setdefault("called", True)
r = c.post("/admin/cancel/send", data={"day": "tomorrow", "confirm": ""})
check("a send without typing CANCEL sends nothing and stays on tomorrow",
      not posted and "day=tomorrow" in (r.headers.get("Location") or ""),
      str(r.headers.get("Location")))


# ------------------------------------------------------------------------
# The wording guard: the Cancellation Email tab is seeded once and edited by
# hand, so wording written for a same-day call-off sits there until someone
# changes it. On 2 November it went out saying "TODAY'S" for tomorrow's games.
# ------------------------------------------------------------------------
print()

warn = sheets.cancellation_wording_warning(
    "CANCELLED — today's JSSA league games (Mon, Nov 2)",
    "TODAY'S JSSA GAMES HAVE BEEN CANCELLED.\n\nPlease do not travel.",
    "tomorrow")
check("stale 'today' wording is caught when calling off tomorrow",
      bool(warn) and "today" in warn, repr(warn))
check("the warning says exactly how to fix it",
      "{when}" in warn and "{WHEN}" in warn and "Cancellation Email" in warn,
      repr(warn))

check("correct tomorrow wording raises no warning",
      sheets.cancellation_wording_warning(
          "CANCELLED — tomorrow's JSSA league games (Mon, Nov 2)",
          "TOMORROW'S JSSA GAMES HAVE BEEN CANCELLED.", "tomorrow") == "")

check("correct today wording raises no warning",
      sheets.cancellation_wording_warning(
          "CANCELLED — today's JSSA league games",
          "TODAY'S JSSA GAMES HAVE BEEN CANCELLED.", "today") == "")

check("wording that says tomorrow on a same-day call-off is caught too",
      bool(sheets.cancellation_wording_warning(
          "CANCELLED — tomorrow's games", "TOMORROW'S GAMES ARE OFF.", "today")))

check("wording that names neither day is left alone",
      sheets.cancellation_wording_warning(
          "JSSA games cancelled", "The games are off.", "tomorrow") == "")

# And it reaches the page, next to the send button.
sheets.cancellation_email_template = lambda: {
    "subject": "CANCELLED — today's JSSA {games} ({date})",
    "body": "TODAY'S JSSA GAMES HAVE BEEN CANCELLED.\n\n{reason_block}",
    "source": "sheet"}

r = c.get("/admin/cancel?day=tomorrow")
html = r.get_data(as_text=True)
check("the page warns about stale wording before you can send",
      "Check the wording before you send" in html, str(r.status_code))

r = c.get("/admin/cancel?day=today")
check("and stays quiet when the wording matches the day",
      "Check the wording before you send" not in r.get_data(as_text=True))

print()
if failures:
    print("FAILURES: " + ", ".join(failures))
    sys.exit(1)
print("CANCEL TOMORROW CHECKS PASSED")

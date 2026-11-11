"""Turns a team's league games into a calendar file (the standard ".ics" format).

Google Calendar, Apple Calendar (iPhone / iPad / Mac), Outlook and Yahoo all read
this format, either as a one-time download or as a calendar they "subscribe" to
and re-check on their own every so often.

Nothing here talks to Google Sheets: it is handed the games that the public
schedule page already shows, so the calendar can never contain anything that is
not already public on the website.
"""
import datetime
import hashlib
import re

GAME_MINUTES = 90          # games are played in 9:00 and 10:30 slots
TZID = "America/New_York"

# Tells the calendar app what "Eastern time" means, daylight saving included.
_VTIMEZONE = [
    "BEGIN:VTIMEZONE",
    "TZID:" + TZID,
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:-0500",
    "TZOFFSETTO:-0400",
    "TZNAME:EDT",
    "DTSTART:19700308T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:-0400",
    "TZOFFSETTO:-0500",
    "TZNAME:EST",
    "DTSTART:19701101T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
]


def slug(name):
    """'Mick's Picks' -> 'mick-s-picks' (the team's name as used in the address)."""
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().lower()).strip("-")


def _parse_date(text):
    t = str(text or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    return None


def _parse_time(text):
    t = re.sub(r"\s+", " ", str(text or "").strip().upper().replace(".", ""))
    t = re.sub(r"(\d)(AM|PM)$", r"\1 \2", t)
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.datetime.strptime(t, fmt).time()
        except ValueError:
            pass
    return None


def _esc(text):
    """Escape text the way the calendar format requires."""
    return (str(text or "").replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r", "").replace("\n", "\\n"))


def _fold(line):
    """Calendar files may not have lines longer than 75 bytes; long ones are
    continued on the next line, which starts with a space."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return [line]
    out, cur, size = [], "", 0
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > (75 if not out else 74):
            out.append(cur)
            cur, size = "", 0
        cur += ch
        size += n
    out.append(cur)
    return [out[0]] + [" " + part for part in out[1:]]


def find_team(games, division, team_slug):
    """The team's name as spelled on the schedule, or None if that division has
    no such team."""
    for g in games:
        if g.get("division") != division:
            continue
        for name in (g.get("away"), g.get("home")):
            if name and slug(name) == team_slug:
                return name
    return None


def team_calendar(games, division, team, schedule_url="", now=None):
    """The calendar file (text) holding every game `team` plays in `division`.

    `games` is the league schedule in the sheet's own row order. A game whose
    date can't be read is left out; a game with no readable time becomes an
    all-day entry. A called-off game stays on the calendar with the reason in
    capitals at the front of its title, so nobody shows up to an empty field.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    want = slug(team)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//Jupiter Senior Softball Association//League Schedule//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:" + _esc("JSSA Softball - " + team),
             "X-WR-CALDESC:" + _esc("%s (%s Division) league games, Jupiter Senior "
                                    "Softball Association" % (team, division.title())),
             "X-WR-TIMEZONE:" + TZID,
             "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    lines += _VTIMEZONE
    meetings = {}   # how many times these two teams have met so far (keeps IDs steady)
    for g in games:
        if g.get("division") != division:
            continue
        away, home = g.get("away") or "", g.get("home") or ""
        pair = (slug(away), slug(home))
        meetings[pair] = meetings.get(pair, 0) + 1
        if want not in pair:
            continue
        day = _parse_date(g.get("date"))
        if not day:
            continue
        # The same game keeps the same ID when its date, time or field changes, so
        # a subscribed calendar moves the entry instead of showing it twice.
        uid = hashlib.sha1(("%s|%s|%s|%d|%d" % (division, pair[0], pair[1], meetings[pair],
                                               day.year)).encode("utf-8")).hexdigest()[:24]
        title = "%s at %s" % (away or "TBD", home or "TBD")
        status = str(g.get("status") or "").strip()
        sh, sa = str(g.get("score_home", "")), str(g.get("score_away", ""))
        final = sh != "" and sa != ""
        if g.get("called_off") and not final:
            title = "%s: %s" % (status.upper(), title)
        desc = ["%s Division league game" % division.title(),
                "Visitor: %s" % (away or "TBD"), "Home: %s" % (home or "TBD")]
        if g.get("field"):
            desc.append("Field: %s" % g["field"])
        if g.get("umpires"):
            desc.append("Umpires: %s" % " & ".join(g["umpires"]))
        if final:
            desc.append("Final score: %s %s, %s %s" % (away, sa, home, sh))
        elif g.get("called_off"):
            desc.append("Status: %s" % status)
        if schedule_url:
            desc.append("")
            desc.append("Latest schedule: %s" % schedule_url)
        ev = ["BEGIN:VEVENT", "UID:%s@jupiterseniorsoftball.com" % uid, "DTSTAMP:" + stamp]
        start = _parse_time(g.get("time"))
        if start:
            begin = datetime.datetime.combine(day, start)
            end = begin + datetime.timedelta(minutes=GAME_MINUTES)
            ev.append("DTSTART;TZID=%s:%s" % (TZID, begin.strftime("%Y%m%dT%H%M%S")))
            ev.append("DTEND;TZID=%s:%s" % (TZID, end.strftime("%Y%m%dT%H%M%S")))
        else:
            ev.append("DTSTART;VALUE=DATE:" + day.strftime("%Y%m%d"))
            ev.append("DTEND;VALUE=DATE:" + (day + datetime.timedelta(days=1)).strftime("%Y%m%d"))
        ev.append("SUMMARY:" + _esc("JSSA Softball: " + title))
        if g.get("field"):
            ev.append("LOCATION:" + _esc(g["field"]))
        ev.append("DESCRIPTION:" + _esc("\n".join(desc)))
        ev += ["STATUS:CONFIRMED", "TRANSP:OPAQUE", "END:VEVENT"]
        lines += ev
    lines.append("END:VCALENDAR")
    folded = []
    for ln in lines:
        folded += _fold(ln)
    return "\r\n".join(folded) + "\r\n"

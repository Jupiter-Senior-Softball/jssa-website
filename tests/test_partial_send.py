"""A failed send must not strand the board, and must name who was missed.

Two live failures drove this: (1) 55 recipients on one message tripped Gmail's
50-per-message limit, so nobody was emailed, and (2) that failed run then
locked out the day, leaving no way to retry after fixing the cause."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sheets

TODAY = datetime.datetime.now(sheets._EASTERN).date()
T = {"team": "Aces", "division": "RED", "manager": "Aces Mgr",
     "players": [{"name": "Player %02d" % i} for i in range(54)] + [{"name": "Aces Mgr"}]}
sheets.league_season = lambda: {"schedule": [{"division": "RED",
    "date": TODAY.strftime("%m/%d/%Y"), "time": "9:00 AM", "field": "JCP",
    "home": "Aces", "away": "Aces", "status": ""}],
    "rosters": {"RED": [T], "WHITE": [], "BLUE": []}}
sheets.player_directory = lambda: {"players": [{"name": p["name"], "div": "RED",
    "email": p["name"].replace(" ", "").lower() + "@e.com", "phone": ""}
    for p in T["players"]]}
sheets.game_day_teams = lambda enforce_date_window=True: None
sheets.pickup_game_venue = lambda date_str=None: ""
sheets.add_notice = lambda *a, **k: None
sheets._mark_league_games_cancelled = lambda d: 0
logged = []
sheets._log_cancellation = lambda *a: logged.append(a)
LIVE = {"sender_url": "https://script.google.com/macros/s/A/exec?key=k",
        "overflow_url": "", "cap": 100, "emails_enabled": True,
        "test_mode": False, "test_address": ""}
sheets.cancellation_settings = lambda: LIVE

# ---- 1. the whole send fails: nobody is emailed, everyone is named ---------
sheets._cancel_log_rows = lambda: []
sheets._post_to_sender = lambda *a, **k: {
    "ok": False, "sent": 0,
    "error": "Exception: Limit Exceeded: Email Recipients Per Message."}
res = sheets.send_cancellation("Fields flooded", "", "Tom")
print("Whole send fails:")
print("  emailed:", res["emailed"], "| named as not reached:", len(res["missed"]))
assert res["emailed"] == 0 and len(res["missed"]) == 55, len(res["missed"])
print("  -> all 55 are named so they can be phoned")

# ---- 2. that failure must NOT lock out the day ----------------------------
failed_row = [TODAY.isoformat(), "10:54 AM", "JSSAAdmin", "LEAGUE", "JCP",
              "Fields flooded", "0", "", "Banner posted · 0 emailed — Email problem: …"]
sheets._cancel_log_rows = lambda: [sheets.CANCEL_LOG_HEADERS, failed_row]
sheets._post_to_sender = lambda *a, **k: {"ok": True, "sent": 55, "missed": []}
retry = sheets.send_cancellation("Fields flooded", "", "Tom")
print("\nRetry after a failed send:")
print("  allowed:", retry["ok"], "| emailed:", retry["emailed"])
assert retry["ok"] and retry["emailed"] == 55, retry
print("  -> the board can fix the cause and try again")

# ---- 3. but a SUCCESSFUL send still locks the day -------------------------
good_row = [TODAY.isoformat(), "10:54 AM", "Tom", "LEAGUE", "JCP",
            "Fields flooded", "55", "", "Banner posted · 55 emailed"]
sheets._cancel_log_rows = lambda: [sheets.CANCEL_LOG_HEADERS, good_row]
blocked = sheets.send_cancellation("again", "", "Someone else")
print("\nRetry after a successful send:")
print("  allowed:", blocked["ok"], "->", blocked["note"])
assert not blocked["ok"], "a successful send must still block a second one"
print("  -> nobody gets emailed twice")

# ---- 4. a partial send: some heard, the rest are named --------------------
sheets._cancel_log_rows = lambda: []
sheets._post_to_sender = lambda *a, **k: {
    "ok": False, "sent": 45, "missed": ["player50@e.com", "player51@e.com"],
    "error": "one batch failed"}
part = sheets.send_cancellation("Fields flooded", "", "Tom")
print("\nOne batch of a multi-message send fails:")
print("  emailed:", part["emailed"], "| not reached:", part["missed"])
assert part["emailed"] == 45
assert part["missed"] == ["Player 50", "Player 51"], part["missed"]
print("  -> the two who missed out are named, not silently dropped")

print("\nPARTIAL SEND CHECKS PASSED")

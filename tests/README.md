# Tests

Plain Python scripts — no test framework needed. They feed fake sheet data to
`sheets.py`, so they never touch Google and never send an email.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
for t in tests/test_*.py; do .venv/bin/python "$t" || break; done

# The Apps Scripts, run under Node with a fake MailApp:
node tests/sender/test_sender_script.js
node tests/sender/test_email_counter.js
```

What they cover:

| File | Checks |
|---|---|
| `test_cancellation_league.py` | League game day: who's scheduled, the email cap, managers first, the backup account, the wording |
| `test_cancellation_pickup.py` | Pickup game day, and that yesterday's roster is never mistaken for today's |
| `test_cancellation_send.py` | The 100-then-backup split, the website banner, and the no-sending-twice guard |
| `test_cancellation_page.py` | The `/admin/cancel` page: sign-in required, correct counts, and that nothing sends unless CANCEL is typed |
| `test_cancellation_practice.py` | Practice mode: email goes to one address, banner is real, schedule untouched, practising never blocks the real send |
| `test_cancellation_preview.py` | The on-page preview matches the real email exactly, and reads correctly before anything is typed |
| `test_cancellation_logging.py` | Every reason an email didn't go out writes a different, readable line to the log |
| `test_sender_url.py` | A wrong sender address is caught before the button is pressed, and a 405 explains itself |
| `test_roster_button.py` | The "rosters are posted" button hides under a cancellation banner |
| `test_rehearsal.py` | A practice run reports the real headcount and warns when the quota wouldn't cover it |
| `test_partial_send.py` | A failed send names everyone missed and does not lock out the day; a successful one still does |
| `sender/test_sender_script.js` | The Apps Script itself: batching under Gmail's 50-per-message limit, partial failure, quota refusal |
| `sender/test_email_counter.js` | The Email Send Counter reports Gmail's own remaining quota, not a Sent-folder tally that hides BCC |

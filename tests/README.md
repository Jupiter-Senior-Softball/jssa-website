# Tests

Plain Python scripts — no test framework needed. They feed fake sheet data to
`sheets.py`, so they never touch Google and never send an email.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
for t in tests/test_*.py; do .venv/bin/python "$t" || break; done
```

What they cover:

| File | Checks |
|---|---|
| `test_cancellation_league.py` | League game day: who's scheduled, the email cap, managers first, the backup account, the wording |
| `test_cancellation_pickup.py` | Pickup game day, and that yesterday's roster is never mistaken for today's |
| `test_cancellation_send.py` | The 100-then-backup split, the website banner, and the no-sending-twice guard |
| `test_cancellation_page.py` | The `/admin/cancel` page: sign-in required, correct counts, and that nothing sends unless CANCEL is typed |

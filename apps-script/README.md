# Email Send Counter — setup (one-time)

This powers the **Email Send Counter** page in the admin dashboard, which shows —
live — how many emails each league Gmail account has sent today and how many
sends are left before Gmail's ~100-a-day limit.

Because only code running *inside* a Gmail account can read that account's Sent
mail, each account gets its own tiny copy of the same script.

## Accounts watched
- `jssagames@gmail.com`
- `jssaadmin@gmail.com`
- `cosentinoteam@gmail.com`

## Steps

### 1. Deploy the script in each account
For **each** of the three accounts, signed in as that account:
1. Open <https://script.google.com> → **New project**.
2. Delete the sample code, paste all of [`email-usage.gs`](./email-usage.gs), Save.
3. Set `SECRET` to a long random phrase — **the same phrase in all three**.
4. **Run the `authorizeNow` function once** to grant Gmail access: pick it in
   the editor's function dropdown, click **Run**, choose the account, and on the
   "unverified app" screen click **Advanced → Go to … → Allow**. (Skipping this
   makes the web app return a "does not have permission" error.)
5. **Deploy → New deployment → Web app**:
   - **Execute as:** Me
   - **Who has access:** Anyone
6. Deploy and copy the **Web app URL** (ends in `/exec`).
7. Add `?key=YOUR_SECRET` to the end of that URL.

You'll end up with three URLs like:
```
https://script.google.com/macros/s/AAAA.../exec?key=YOUR_SECRET
https://script.google.com/macros/s/BBBB.../exec?key=YOUR_SECRET
https://script.google.com/macros/s/CCCC.../exec?key=YOUR_SECRET
```

### 2. Tell the website about them (Google Sheet — no Render needed)
Open the **control sheet** ("JSSA website control sheet_live", the same one with
the *Board Portal Links* tab) and find the **"Email Accounts"** tab. The website
creates it automatically the first time the counter page is opened, pre-filled
with the headers and one hidden example row:

| Account | Reporter URL | Show? |
|---|---|---|
| jssagames@gmail.com | `https://.../exec?key=YOUR_SECRET` | Yes |
| jssaadmin@gmail.com | `https://.../exec?key=YOUR_SECRET` | Yes |
| cosentinoteam@gmail.com | `https://.../exec?key=YOUR_SECRET` | Yes |

Fill in one row per account, paste each account's URL into **Reporter URL**, and
set **Show?** to **Yes**. That's it — the counter picks it up within a minute.

## Watch an account privately (not on the website)
To monitor an account for your own eyes only — never shown on the site — deploy
the reporter in that account exactly as above, but **do not** add it to the
"Email Accounts" tab. Instead, in a Google Sheet that only you can see, put:

```
=IMPORTDATA("https://.../exec?key=YOUR_SECRET&format=csv")
```

That fills a small two-column table (emails sent today, people reached, sends
left, etc.). The site never knows about it because it isn't on the "Email
Accounts" tab. Note: `IMPORTDATA` refreshes about once an hour on its own; for
an instant read, open the same URL (without `&format=csv`) in a browser.

### Auto-updating private log (no hourly wait)
For a private view that refreshes on its own every few minutes — and keeps a
dated history — use the built-in logger instead of `IMPORTDATA`:
1. Create a Google Sheet only you can see. Copy its ID from the URL (the long
   code between `/d/` and `/edit`).
2. In the account's reporter script, set `LOG_SHEET_ID` to that ID and Save.
3. Pick **`startAutoUpdates`** in the function dropdown → **Run** once, and
   approve the extra permissions. It writes an **"Email Usage"** tab immediately
   and updates it every 5 minutes (one row per day). Run **`stopAutoUpdates`**
   to turn it off. Change `everyMinutes(5)` if you want a different cadence.

To also log **other** accounts in the same tab (e.g. see the league games
account alongside your own, without opening the website), add their reporter
URLs — the full `…/exec?key=…` links — to the `ALSO_LOG_URLS` list. Each account
gets its own row per day.

## Notes
- The page labels each account automatically from what its script reports; the
  **Account** column is just a friendly label for you in the sheet.
- Add, hide, or remove an account anytime by editing the tab — set **Show?** to
  **No** to hide one. No code change, no Render access.
- A BCC blast to 80 people counts as **1** message but **80** recipients. The
  "sends left today" number uses recipients, since that's what Gmail limits.
- To change the daily limit, edit `DAILY_LIMIT` at the top of the script in each
  account.

---

# Cancel Today's Games — setup (one-time)

This powers the **Cancel Today's Games** button in the admin panel. One switch
posts the website notice, emails everyone who was scheduled to play today, marks
the games cancelled on the schedule, and writes a log row.

The website works out *who* to email. The sending is done by a small script
inside a league Gmail account — [`game-cancellation-sender.gs`](./game-cancellation-sender.gs) —
because only code running in an account can send mail as that account. **The
website never holds a mail password.**

## Accounts

| Account | Role |
|---|---|
| `jssagames@gmail.com` | **Main sender** — the first 100 people |
| `jssaadmin@gmail.com` | **Backup** — anyone past the first 100 |

Gmail stops a free account at about **100 recipients a day**, so a busy winter
day with 130 league players needs the backup. With both installed the button
reaches 200. Anyone still past that is **named on screen** after sending so a
captain can phone them — nobody is dropped silently.

## Steps

### 1. Install the script in both accounts
Follow the instructions at the top of
[`game-cancellation-sender.gs`](./game-cancellation-sender.gs). Do it once
signed in as `jssagames@`, then again as `jssaadmin@`. Use the **same secret
phrase** both times. You'll end up with two URLs like:

```
https://script.google.com/macros/s/AAAA.../exec?key=YOUR_SECRET     <- jssagames@
https://script.google.com/macros/s/BBBB.../exec?key=YOUR_SECRET     <- jssaadmin@
```

To check one is working, paste its URL into a browser. A healthy script replies
with its account name and how many sends it has left today.

> ⚠️ **Copy the address from the Deploy screen, not from the browser bar.**
> When you test the URL, the browser bounces you to a long
> `script.googleusercontent.com/macros/echo?user_content_key=...` address. That
> is the *answer*, not the script. Pasting it into the settings tab looks fine
> — it even passes the browser test — but the website gets
> **"405 Method Not Allowed"** and no email ever goes out.
>
> The address you want ends in **`/exec`**. If you lose it: in the script,
> **Deploy → Manage deployments** shows the Web app URL.

### 2. Tell the website about them (Google Sheet — no Render needed)
Open the **control sheet** ("JSSA website control sheet_live") and find the
**"Cancellation Settings"** tab. The website creates it automatically the first
time the page is opened, pre-filled:

| Setting | What to put |
|---|---|
| **Sender URL** | the `jssagames@` URL |
| **Overflow sender URL** | the `jssaadmin@` URL |
| **Emails enabled** | `Yes` |
| **Email cap** | `100` |
| **Test mode** | `Yes` while testing, then `No` |
| **Test address** | your own email, for testing |

### 3. Try it safely — the practice run

Set **Test mode** to `Yes` and put your own address in **Test address**. Then
open **Admin → Cancel Today's Games** and press the button.

In practice mode:

| | What happens |
|---|---|
| **The email** | Goes **only to you**. Not one scheduled player is emailed. |
| **The website banner** | Goes up **for real**, exactly as visitors see it — that's the point, so you can check how it looks. Switch it off on the admin panel when you're done. |
| **The schedule** | **Not touched.** No game is marked cancelled during a practice run. |
| **Doing it again** | Allowed, as often as you like. A practice run never blocks the real one. |

You don't have to send anything to see how it reads: the page has a **live
preview** showing the banner and the full email, updating as you type. It's
built by the same code that does the real send, so it can't differ from what
actually goes out.

When you're happy, set **Test mode** back to `No`.

## Day-to-day

Open the admin panel on your phone, tap **Cancel Today's Games**, check the
count, type the reason, type `CANCEL`, and press the button.

- The page figures out by itself whether today is a **league** day, a **pickup**
  day, or both — you don't have to tell it.
- The **location** is filled in from today's schedule; type over it if the games
  were somewhere else.
- **Captains and managers are always emailed first**, so if the cap ever bites,
  every team still has someone who knows.
- It **won't send twice** in one day. If another board member already made the
  call, the page says who and when, and sends nothing.
- Tick **"Website notice only"** to post the banner without emailing anyone.

Every cancellation is recorded on the **"Cancellation Log"** tab of the control
sheet: date, time, who sent it, the reason, how many were emailed, and the names
of anyone not reached.

## Undoing it
The emails can't be unsent. Everything else is reversible:
- **The banner** — switch it off on the admin panel, same as any other notice.
- **The schedule** — the cancelled games are marked `Cancelled` in the Status
  column of the Schedule tab; clear that cell to put a game back.
- **To send again the same day** (say the reason changed) — delete that day's
  row from the "Cancellation Log" tab and the button unlocks.

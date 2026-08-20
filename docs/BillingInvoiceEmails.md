# Billing invoice emails — setup and use

This adds an **Invoices** menu to the billing spreadsheet. Click a row, click a
menu item, and the invoice email is written for you and parked in Gmail Drafts
so you can read it and press Send.

The script never sends anything on its own. It only ever creates a draft.

---

## One-time setup (about two minutes)

1. Open the billing spreadsheet.
2. **Extensions → Apps Script.**
3. Delete the sample code in the editor, paste in all of
   [`apps-script/billing-invoice.gs`](../apps-script/billing-invoice.gs), click
   **Save** (the disk icon).
4. Close the Apps Script tab and **reload the spreadsheet**.
5. A new **Invoices** menu appears up top, next to Help.

The first time you use the menu, Google asks for permission. It shows a scary
"Google hasn't verified this app" screen — that is Google warning you about
*your own* script. Click **Advanced → Go to (project name) → Allow**.

A tab called **Email Template** appears the first time too. That is where the
wording lives.

---

## Using it each month

1. Click any cell on the invoice row you want to bill.
2. **Invoices → Draft invoice email for selected row.**
3. Open Gmail → **Drafts**, read it over, press **Send**.
4. Back in the sheet: **Invoices → Mark selected row as sent today.**
5. When the money arrives: **Invoices → Record payment on selected row.**

**Invoices → Draft next unpaid invoice** skips step 1 — it finds the oldest row
that is not marked PAID and drafts that one.

If the row has no amount on it yet (the future months are blank), the script
asks whether to use your monthly rate and fill it in for you.

---

## Changing the wording

**Invoices → Edit the email wording**, or just open the **Email Template** tab.

- **B1** is the subject line.
- **B2** is the body. Press **Alt+Enter** to add a new line inside the cell.

Anything in double curly braces gets swapped for the real value:

| Placeholder | Becomes |
|---|---|
| `{{InvoiceNo}}` | The invoice number on the row, e.g. 2026-08 |
| `{{Period}}` | The billing period, e.g. August 2026 |
| `{{Amount}}` | Amount Billed on that row |
| `{{DateSent}}` | Date Sent on the row, or today if blank |
| `{{Today}}` | Today's date |
| `{{PaymentMethod}}` | The Payment Method line from the top of the sheet |
| `{{MonthlyRate}}` | The Monthly Rate from the top of the sheet |
| `{{Notes}}` | Notes on that row |
| `{{Status}}` | PAID or UNPAID |
| `{{Client}}` | The Client name from the top of the sheet |
| `{{BalanceDue}}` | Balance Due from the top of the sheet |
| `{{TotalBilled}}` / `{{TotalReceived}}` | The totals from the top of the sheet |

**A handy trick:** if every placeholder on a line comes out blank, the whole
line is dropped from the email. That is why a row with no notes does not leave
a stray `Note:` sitting there. The flip side: don't mix a blank placeholder into
a line you always want to keep, or that line disappears too.

---

## How it finds things

The script works off **labels**, not row numbers, so you can add rows or move
the table without breaking it:

- The invoice table is found by looking for a row whose first cell says
  **`Invoice #`**. The headings on that row (Period, Date Sent, Amount Billed,
  Status, Date Paid, Amount Received, Notes) are matched by name.
- The settings above the table are read as label/value pairs from the first two
  columns — **Client**, **Client Email**, **Monthly Rate**, **Payment Method**,
  **Balance Due**, and so on.

So keep those labels spelled the way they are and everything keeps working.
Nothing personal is stored in the code itself — the client's address and your
payment details are read from the sheet at the moment you draft.

---

## Undoing things

- **Don't want a drafted email?** Delete the draft in Gmail. Nothing was sent.
- **Marked a row sent by mistake?** Clear the Date Sent cell yourself.
- **Recorded a payment by mistake?** Clear Date Paid and Amount Received, and
  set Status back to UNPAID.
- **Want the whole thing gone?** Extensions → Apps Script → delete the code and
  save, then delete the Email Template tab. The menu disappears on the next
  reload. The billing log itself is untouched either way.

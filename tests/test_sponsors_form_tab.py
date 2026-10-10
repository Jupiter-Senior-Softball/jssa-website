"""Homepage sponsors follow the 'Sponsor Form Responses' tab: a sponsor shows
only when 'Website Enabled' is checked."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["SECRET_KEY"] = "t"; os.environ["ADMIN_PASSWORD"] = "t"
import sheets

H = ["Timestamp", "Business or Individual Name", "BusinessTag Line", "Contact person:",
     "JSSA Referral Contact", "Address (#, street, city and zip)", "Phone", "Email Address",
     "Website URL", "Logo URL", "Patron Support Level", "Payment Method Selection",
     "Signature", "Date", "Other Amount", "Sponsor ID", "Approved", "Active", "Paid",
     "Amount Paid", "Expiration Date", "Renewal Sent", "Website Enabled", "Sort Order",
     "Background Color", "Text Color", "Display Seconds", "Website Logo URL", "Notes",
     "Last Updated", "Renewal Month"]
I = {h: n for n, h in enumerate(H)}

def row(name, on, tag="", url="", logo="", wlogo="", phone="", order=""):
    r = [""] * len(H)
    r[I["Business or Individual Name"]] = name
    r[I["BusinessTag Line"]] = tag
    r[I["Website URL"]] = url
    r[I["Logo URL"]] = logo
    r[I["Website Logo URL"]] = wlogo
    r[I["Phone"]] = phone
    r[I["Sort Order"]] = order
    r[I["Website Enabled"]] = on
    r[I["Approved"]] = "TRUE"
    return r

rows = [H,
    row("VILLAGE SCOOP SHACK", "TRUE", "ICECREAM", "villagescoopshack.com", wlogo="https://lh3.googleusercontent.com/d/1xza0JCWClLBISuFTRjSjbPTDFC-RY6n8"),
    row("American Sr Health Services of the Treasure Coast\n", "TRUE", "Health", "http://www.healthyseniorstc.com/"),
    row("Turned Off Co", "FALSE", "x", "http://off.example/"),
    row("TEMP TECH SERVICES\n", "TRUE", "AC", "https://docs.google.com/spreadsheets/d/1Bpb1PGs2/edit#"),
    row("Bradley Molineux", "TRUE", "LPL", phone="772-221-3100"),
    row("Insure Options", "TRUE", "Licensed agent",  "https://www.insureoptions.health/",
        logo="https://drive.google.com/open?id=1DnaLYBgXNDNIugY8qBtoBJdQi2cQycru"),
    row("Pinned First", "TRUE", "", "", order="1"),
    [""] * len(H),                                   # the ~1,100 blank rows
    [""] * 15 + [""] * 7 + ["FALSE"],                # blank row with an unchecked box
]
out = sheets._form_sponsors(rows)
names = [s["n"] for s in out]
for s in out:
    print("%-48s link=%-38s logo=%s" % (s["n"], s["u"] or "-", (s["l"] or "-")[:50]))

assert "Turned Off Co" not in names, "Website Enabled=FALSE must hide a sponsor"
assert names[0] == "Pinned First", "Sort Order number goes first"
assert names[1:] == ["VILLAGE SCOOP SHACK", "American Sr Health Services of the Treasure Coast",
                     "TEMP TECH SERVICES", "Bradley Molineux", "Insure Options"], names
by = {s["n"]: s for s in out}
assert by["VILLAGE SCOOP SHACK"]["u"] == "https://villagescoopshack.com", "bare domain gets https://"
assert by["TEMP TECH SERVICES"]["u"] == "", "a private Google Sheet link must never be shown"
assert by["Bradley Molineux"]["p"] == "772-221-3100"
assert by["Insure Options"]["l"].startswith("https://lh3.googleusercontent.com/d/1DnaLYBg"), "falls back to raw logo"
assert by["VILLAGE SCOOP SHACK"]["l"].startswith("https://lh3.googleusercontent.com/d/1xza0")
assert sheets._form_sponsors([]) == [] and sheets._form_sponsors([["Nope"]]) == []

# sponsors(): form tab wins; if it can't be read, the older list is used
class _WS:
    def get_all_values(self): return rows
class _SH:
    def worksheet(self, n):
        assert n == "Sponsor Form Responses"; return _WS()
sheets.CONTROL_SHEET_ID = "x"; sheets._SA_JSON = "{}"
sheets._control_sheet = lambda readonly=True: _SH()
sheets._sponsor_cache.update(data=None, ts=0.0)
assert [s["n"] for s in sheets.sponsors()][0] == "Pinned First"

def boom(readonly=True): raise RuntimeError("google down")
sheets._control_sheet = boom
sheets._admin_sponsors = lambda: ["OLD"]
sheets._sponsor_cache.update(data=None, ts=0.0)
assert sheets.sponsors() == ["OLD"], "falls back when the tab can't be read"
print("\nSPONSOR FORM TAB CHECKS PASSED")

/**
 * JSSA — New Sponsor Alert
 * ---------------------------------------------------------------------------
 * Emails the league the moment someone submits the "JSSA Advertising Patron
 * Registration" form, and sends a daily reminder about any sponsor who has
 * applied but has not been approved yet.
 *
 * WHY: the form only drops a new row into the "Sponsor Form Responses" tab of
 * the "JSSA Website Control Sheet _ LIVE". Nothing told anyone a row had been
 * added, so a new sponsor could sit there unnoticed.
 *
 * This is an ADD-ON. It does not touch the Sponsor ID / Approved / Active
 * columns or any existing script.
 *
 * HOW TO SET UP (one time, ~5 minutes — see apps-script/README.md too):
 *   1. Open the Control Sheet -> Extensions -> Apps Script.
 *   2. Click  +  next to "Files" -> Script -> name it  SponsorAlert.
 *      Paste ALL of this file and Save.
 *   3. Edit ALERT_EMAILS below (add the board members who should be told).
 *   4. Pick  testAlert  in the function dropdown and click Run. Approve the
 *      permissions. You should get a sample email within a minute.
 *   5. Pick  installSponsorAlerts  and click Run once. That turns on both the
 *      instant alert and the daily reminder.
 *   To turn it all off: run  removeSponsorAlerts.
 */

// Who gets the alerts. Add more addresses inside the brackets, in quotes,
// separated by commas.
var ALERT_EMAILS = ['cosentinoteam@gmail.com'];

// The tab the sponsor form writes to.
var SPONSOR_TAB = 'Sponsor Form Responses';

// Remind about unapproved applications once they are this many days old.
var REMIND_AFTER_DAYS = 1;

// Hour of day (0-23, sheet's time zone) for the daily reminder.
var REMINDER_HOUR = 8;


/** Runs automatically each time ANY form feeding this spreadsheet is submitted. */
function onSponsorFormSubmit(e) {
  try {
    var sheet = e && e.range && e.range.getSheet();
    if (!sheet || sheet.getName() !== SPONSOR_TAB) return;   // some other form

    fixSponsorTimestamps();            // keep the Timestamp column a real date
    var row = e.range.getRow();
    var info = readRow_(sheet, row);
    var link = sheetLink_(sheet, row);

    var lines = [
      'A new sponsor application just came in.',
      '',
      'Business / person: ' + info.business,
      'Contact person:    ' + info.contact,
      'Phone:             ' + info.phone,
      'Email:             ' + info.email,
      'Website:           ' + info.website,
      'Patron level:      ' + info.level,
      'Payment method:    ' + info.payment,
      'Referred by:       ' + info.referral,
      'Sponsor ID:        ' + (info.id || '(not assigned yet)'),
      '',
      'WHAT TO DO NEXT',
      '1. Open the row:  ' + link,
      '2. Confirm payment was received.',
      '3. In the yellow columns, set Approved, Active, Paid, the expiration',
      '   date and Website Enable. The sponsor then shows on the site.',
      '',
      'Full steps: "2 How to Add, Remove and Manage Sponsors" in Google Drive.'
    ];
    MailApp.sendEmail({
      to: ALERT_EMAILS.join(','),
      subject: 'NEW JSSA SPONSOR APPLICATION: ' + info.business,
      body: lines.join('\n'),
      name: 'JSSA Website'
    });
  } catch (err) {
    // Never let an alert problem break the form. Tell the admin instead.
    try {
      MailApp.sendEmail(ALERT_EMAILS[0], 'JSSA sponsor alert had a problem',
        'The new-sponsor alert hit an error:\n\n' + err +
        '\n\nCheck the "Sponsor Form Responses" tab for a new row.');
    } catch (ignore) {}
  }
}


/** Daily: lists applications that are still waiting for approval. */
function remindPendingSponsors() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(SPONSOR_TAB);
  if (!sheet) return;
  var values = sheet.getDataRange().getValues();
  if (values.length < 2) return;

  var h = headerIndex_(values[0]);
  var cutoff = Date.now() - REMIND_AFTER_DAYS * 24 * 3600 * 1000;
  var pending = [];

  for (var r = 1; r < values.length; r++) {
    var name = String(values[r][h.business] || '').trim();
    if (!name) continue;
    var approved = values[r][h.approved];
    if (approved === true || String(approved).toUpperCase() === 'TRUE') continue;
    var when = toDate_(values[r][h.timestamp]);
    if (!when || when.getTime() > cutoff) continue;
    pending.push('- ' + name + ' (applied ' +
      Utilities.formatDate(when, Session.getScriptTimeZone(), 'MMM d, yyyy') +
      ')  ' + sheetLink_(sheet, r + 1));
  }
  if (!pending.length) return;

  MailApp.sendEmail({
    to: ALERT_EMAILS.join(','),
    subject: 'JSSA sponsors waiting for approval (' + pending.length + ')',
    body: 'These sponsor applications have not been approved yet:\n\n' +
          pending.join('\n') +
          '\n\nOpen each row, confirm payment, and set Approved / Active / ' +
          'Website Enable. You will keep getting this reminder daily until ' +
          'Approved is checked.',
    name: 'JSSA Website'
  });
}


/** Sends a sample alert so you can see it works. */
function testAlert() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(SPONSOR_TAB);
  var row = sheet ? lastSponsorRow_(sheet) : 2;
  var info = sheet ? readRow_(sheet, row) : {};
  MailApp.sendEmail({
    to: ALERT_EMAILS.join(','),
    subject: 'TEST - JSSA sponsor alert',
    body: 'This is only a test. When a real application arrives you will ' +
          'get an email like this with the sponsor details.\n\n' +
          'Most recent row in the tab: ' + (info.business || '(none)') +
          '\n' + (sheet ? sheetLink_(sheet, row) : ''),
    name: 'JSSA Website'
  });
}


/** Run ONCE. Safe to run again — it clears its own old triggers first. */
function installSponsorAlerts() {
  removeSponsorAlerts();
  ScriptApp.newTrigger('onSponsorFormSubmit')
    .forSpreadsheet(SpreadsheetApp.getActive()).onFormSubmit().create();
  ScriptApp.newTrigger('remindPendingSponsors')
    .timeBased().everyDays(1).atHour(REMINDER_HOUR).create();
}

function removeSponsorAlerts() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var fn = t.getHandlerFunction();
    if (fn === 'onSponsorFormSubmit' || fn === 'remindPendingSponsors') {
      ScriptApp.deleteTrigger(t);
    }
  });
}


/**
 * Fixes the Timestamp column (column A) of the Sponsor Form Responses tab.
 *
 * PROBLEM: some rows show a raw number like 46304.68456 instead of a date.
 * That number IS the date (46304.68456 = Oct 9, 2026 4:25 PM) but it was saved
 * as TEXT, so the Format menu cannot turn it into a date.
 *
 * This turns those into real dates and formats the whole column as
 * "m/d/yyyy h:mm:ss". Run it once by hand; it also runs automatically with
 * every new application. Safe to run any number of times.
 */
function fixSponsorTimestamps() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(SPONSOR_TAB);
  if (!sheet) return;
  var last = sheet.getMaxRows();
  if (last < 2) return;
  var range = sheet.getRange(2, 1, last - 1, 1);
  var vals = range.getValues();
  var changed = false;
  for (var i = 0; i < vals.length; i++) {
    var v = vals[i][0];
    if (v instanceof Date || v === '' || v === null) continue;
    var d = toDate_(v);
    if (d) { vals[i][0] = d; changed = true; }
  }
  range.setNumberFormat('m/d/yyyy h:mm:ss');   // format first, then write dates
  if (changed) range.setValues(vals);
}


// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

/** Finds each column by the START of its header, so small wording changes
 *  in the form (or the sheet truncating a long header) don't break it. */
function headerIndex_(headers) {
  function find(prefix) {
    prefix = prefix.toLowerCase();
    for (var i = 0; i < headers.length; i++) {
      if (String(headers[i]).toLowerCase().indexOf(prefix) === 0) return i;
    }
    return -1;
  }
  return {
    timestamp: find('timestamp'),
    business: find('business or individual'),
    contact: find('contact p'),
    referral: find('jssa referral'),
    phone: find('phone'),
    email: find('email'),
    website: find('website url'),
    level: find('patron su'),
    payment: find('payment m'),
    id: find('sponsor id'),
    approved: find('approved')
  };
}

function readRow_(sheet, row) {
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var vals = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
  var h = headerIndex_(headers);
  function get(i) { return i >= 0 ? String(vals[i] || '').trim() : ''; }
  return {
    business: get(h.business) || '(no name given)',
    contact: get(h.contact), referral: get(h.referral), phone: get(h.phone),
    email: get(h.email), website: get(h.website), level: get(h.level),
    payment: get(h.payment), id: get(h.id)
  };
}

function sheetLink_(sheet, row) {
  return SpreadsheetApp.getActive().getUrl().replace(/\/edit.*$/, '') +
         '/edit#gid=' + sheet.getSheetId() + '&range=A' + row;
}

/** Real dates pass through; "46304.68456" (number or text) becomes a Date;
 *  anything else (blank, "5/22") returns null. */
function toDate_(v) {
  if (v instanceof Date) return v;
  var n = (typeof v === 'number') ? v : (/^\d{5}(\.\d+)?$/.test(String(v).trim()) ? parseFloat(v) : NaN);
  if (isNaN(n) || n < 40000 || n > 60000) return null;
  // Sheets day-count -> wall-clock time -> a Date in the script's time zone.
  var u = new Date(Math.round((n - 25569) * 86400000));
  return new Date(u.getUTCFullYear(), u.getUTCMonth(), u.getUTCDate(),
                  u.getUTCHours(), u.getUTCMinutes(), u.getUTCSeconds());
}

/** Last row that actually has a business name (the tab has ~1,100 pre-filled
 *  checkbox rows, so getLastRow() would point at an empty one). */
function lastSponsorRow_(sheet) {
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var col = headerIndex_(headers).business + 1;
  var names = sheet.getRange(1, col, sheet.getMaxRows(), 1).getValues();
  for (var r = names.length - 1; r >= 1; r--) {
    if (String(names[r][0]).trim()) return r + 1;
  }
  return 2;
}

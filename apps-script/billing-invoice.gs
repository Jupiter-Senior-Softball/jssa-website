/**
 * JSSA — Billing Invoice Emails
 * ---------------------------------------------------------------------------
 * Adds an "Invoices" menu to the billing spreadsheet. Pick an invoice row,
 * click a menu item, and it writes the invoice email for you as a Gmail DRAFT.
 * Nothing is ever sent automatically — you always read it and press Send
 * yourself.
 *
 * The wording of the email is NOT in this code. It lives in a tab called
 * "Email Template" that the script creates for you, so you can reword the
 * email any time without touching code.
 *
 * HOW TO INSTALL (about two minutes, one time):
 *   1. Open the billing spreadsheet.
 *   2. Extensions > Apps Script.
 *   3. Delete the sample code, paste ALL of this file, click Save.
 *   4. Close the Apps Script tab and RELOAD the spreadsheet.
 *   5. A new "Invoices" menu appears next to Help. The first time you use it,
 *      Google asks for permission — click Advanced > Go to ... > Allow. That is
 *      Google warning you about your own script; it is expected.
 *
 * HOW TO USE:
 *   - Click any cell in the invoice row you want to bill.
 *   - Invoices > Draft invoice email for selected row.
 *   - Open Gmail > Drafts, read it, press Send.
 *   - Come back and click Invoices > Mark selected row as sent today.
 *
 * The script finds everything by LABEL, not by row number, so you can add rows
 * or move the table around and it keeps working. What it looks for:
 *   - the invoice table   — a row whose first column says "Invoice #"
 *   - the settings above  — first-column labels like "Client Email",
 *                           "Monthly Rate", "Payment Method", "Balance Due"
 * ---------------------------------------------------------------------------
 */

// Name of the tab holding the email wording. Created automatically if missing.
var TEMPLATE_TAB = 'Email Template';

// Leave true so the script only ever creates a draft for you to review.
// Setting this to false makes the menu send mail immediately - not recommended.
var DRAFT_ONLY = true;


function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Invoices')
    .addItem('Draft invoice email for selected row', 'draftSelectedInvoice')
    .addItem('Draft next unpaid invoice', 'draftNextUnpaidInvoice')
    .addSeparator()
    .addItem('Mark selected row as sent today', 'markSelectedSent')
    .addItem('Record payment on selected row', 'recordSelectedPayment')
    .addSeparator()
    .addItem('Edit the email wording', 'openTemplateTab')
    .addToUi();
}


/* ========================================================================
   MENU ACTIONS
   ======================================================================== */

function draftSelectedInvoice() {
  var ui = SpreadsheetApp.getUi();
  var table = _findTable();
  var row = SpreadsheetApp.getActiveRange().getRow();

  if (row <= table.headerRow) {
    ui.alert('Pick an invoice first',
      'Click any cell on the invoice row you want to bill (one of the rows '
      + 'below the "Invoice #" headings), then try again.', ui.ButtonSet.OK);
    return;
  }
  _draftInvoiceRow(table, row);
}


function draftNextUnpaidInvoice() {
  var ui = SpreadsheetApp.getUi();
  var table = _findTable();
  var sheet = table.sheet;
  var last = sheet.getLastRow();

  for (var r = table.headerRow + 1; r <= last; r++) {
    var invoiceNo = _text(sheet.getRange(r, table.col['invoice #']).getValue());
    if (!invoiceNo) continue;
    var status = _text(sheet.getRange(r, table.col['status']).getValue()).toUpperCase();
    if (status === 'PAID') continue;
    sheet.setActiveRange(sheet.getRange(r, 1));
    _draftInvoiceRow(table, r);
    return;
  }
  ui.alert('Nothing to bill',
    'Every invoice row with a number on it is already marked PAID.',
    ui.ButtonSet.OK);
}


function markSelectedSent() {
  var ui = SpreadsheetApp.getUi();
  var table = _findTable();
  var row = SpreadsheetApp.getActiveRange().getRow();
  if (row <= table.headerRow) {
    ui.alert('Pick an invoice row first.');
    return;
  }
  var sheet = table.sheet;
  var period = _text(sheet.getRange(row, table.col['period']).getValue());
  var today = new Date();

  sheet.getRange(row, table.col['date sent']).setValue(today);
  var statusCell = sheet.getRange(row, table.col['status']);
  if (!_text(statusCell.getValue())) statusCell.setValue('UNPAID');

  ui.alert('Marked as sent',
    period + ' is now stamped ' + _dateText(today) + ' and marked UNPAID.\n\n'
    + 'To undo, just clear the Date Sent cell yourself.', ui.ButtonSet.OK);
}


function recordSelectedPayment() {
  var ui = SpreadsheetApp.getUi();
  var table = _findTable();
  var row = SpreadsheetApp.getActiveRange().getRow();
  if (row <= table.headerRow) {
    ui.alert('Pick an invoice row first.');
    return;
  }
  var sheet = table.sheet;
  var billed = sheet.getRange(row, table.col['amount billed']).getValue();
  var period = _text(sheet.getRange(row, table.col['period']).getValue());

  var answer = ui.prompt('Record a payment',
    'How much came in for ' + period + '?\n\n'
    + 'Press OK with the box empty to use the amount billed ('
    + _money(billed) + ').', ui.ButtonSet.OK_CANCEL);
  if (answer.getSelectedButton() !== ui.Button.OK) return;

  var typed = _text(answer.getResponseText()).replace(/[$,\s]/g, '');
  var amount = typed ? Number(typed) : Number(billed);
  if (!amount || isNaN(amount)) {
    ui.alert('That did not look like an amount. Nothing was changed.');
    return;
  }

  sheet.getRange(row, table.col['date paid']).setValue(new Date());
  sheet.getRange(row, table.col['amount received']).setValue(amount);
  sheet.getRange(row, table.col['status']).setValue('PAID');
  ui.alert('Payment recorded',
    period + ' marked PAID for ' + _money(amount) + '.\n\n'
    + 'To undo, clear the Date Paid and Amount Received cells and set Status '
    + 'back to UNPAID.', ui.ButtonSet.OK);
}


function openTemplateTab() {
  var sheet = _templateSheet();
  SpreadsheetApp.getActiveSpreadsheet().setActiveSheet(sheet);
  SpreadsheetApp.getUi().alert('Edit the wording here',
    'Change the Subject and Body however you like. Anything in {{double '
    + 'curly braces}} gets swapped for the real value when you draft an '
    + 'email.\n\nA line whose only placeholder comes out blank (like Notes on '
    + 'a row with no notes) is dropped from the email automatically.',
    SpreadsheetApp.getUi().ButtonSet.OK);
}


/* ========================================================================
   BUILDING THE EMAIL
   ======================================================================== */

function _draftInvoiceRow(table, row) {
  var ui = SpreadsheetApp.getUi();
  var sheet = table.sheet;
  var cfg = _readSettings(table);

  var invoiceNo = _text(sheet.getRange(row, table.col['invoice #']).getValue());
  var period = _text(sheet.getRange(row, table.col['period']).getValue());
  if (!invoiceNo && !period) {
    ui.alert('That row is empty',
      'Click a row that has an invoice number or a period on it.',
      ui.ButtonSet.OK);
    return;
  }

  var to = cfg['client email'];
  if (!to) {
    ui.alert('No client email',
      'Add a row near the top of the sheet with "Client Email" in the first '
      + 'column and the address next to it.', ui.ButtonSet.OK);
    return;
  }

  // Future months are blank until billed - offer to fill in the monthly rate.
  var billedCell = sheet.getRange(row, table.col['amount billed']);
  var amount = billedCell.getValue();
  if (amount === '' || amount === null) {
    var rate = cfg['monthly rate'];
    if (!rate) {
      ui.alert('No amount on that row',
        'Type the amount into the Amount Billed cell, then try again.',
        ui.ButtonSet.OK);
      return;
    }
    var fill = ui.alert('Amount Billed is blank',
      period + ' has no amount yet. Use the monthly rate of ' + _money(rate)
      + ' and write it into the row?', ui.ButtonSet.YES_NO);
    if (fill !== ui.Button.YES) return;
    billedCell.setValue(rate);
    amount = rate;
  }

  var tpl = _readTemplate();
  var values = {
    'Client': cfg['client'],
    'ClientEmail': to,
    'InvoiceNo': invoiceNo,
    'Period': period,
    'Amount': _money(amount),
    'MonthlyRate': _money(cfg['monthly rate']),
    'PaymentMethod': cfg['payment method'],
    'Status': _text(sheet.getRange(row, table.col['status']).getValue()),
    'Notes': _text(sheet.getRange(row, table.col['notes']).getValue()),
    'DateSent': _dateText(sheet.getRange(row, table.col['date sent']).getValue() || new Date()),
    'Today': _dateText(new Date()),
    'TotalBilled': _money(cfg['total billed']),
    'TotalReceived': _money(cfg['total received']),
    'BalanceDue': _money(cfg['balance due'])
  };

  var subject = _fill(tpl.subject, values);
  var body = _fill(tpl.body, values);

  if (DRAFT_ONLY) {
    GmailApp.createDraft(to, subject, body);
    ui.alert('Draft ready',
      'An invoice email for ' + period + ' is waiting in your Gmail Drafts.\n\n'
      + 'To: ' + to + '\nSubject: ' + subject + '\n\n'
      + 'Open Gmail, go to Drafts, read it over, and press Send. Nothing has '
      + 'been sent yet. If you do not want it, just delete the draft.',
      ui.ButtonSet.OK);
  } else {
    GmailApp.sendEmail(to, subject, body);
    ui.alert('Sent to ' + to + '.');
  }
}


// Swap {{Placeholders}} for real values. Any line whose placeholder resolves to
// nothing is removed, so an empty Notes field does not leave a stray "Notes:".
function _fill(text, values) {
  var lines = String(text).split('\n');
  var kept = [];

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var tags = line.match(/\{\{\s*\w+\s*\}\}/g);
    if (tags) {
      var allBlank = true;
      for (var t = 0; t < tags.length; t++) {
        var key = tags[t].replace(/[{}\s]/g, '');
        if (_text(values[key])) { allBlank = false; break; }
      }
      // Every placeholder on this line came out blank, so drop the whole
      // line. That is what keeps an empty Notes cell from leaving a stray
      // "Note:" sitting in the email.
      if (allBlank) continue;
    }
    kept.push(line);
  }

  var out = kept.join('\n').replace(/\{\{\s*(\w+)\s*\}\}/g, function (whole, key) {
    return values.hasOwnProperty(key) ? _text(values[key]) : whole;
  });

  // Dropping a line can leave a double gap behind it - close that back up.
  return out.replace(/\n{3,}/g, '\n\n');
}


/* ========================================================================
   READING THE SHEET
   ======================================================================== */

// Find the tab and the header row of the invoice table by looking for the
// "Invoice #" heading, so nothing breaks if rows shift around.
function _findTable() {
  var sheets = SpreadsheetApp.getActiveSpreadsheet().getSheets();
  for (var s = 0; s < sheets.length; s++) {
    var sheet = sheets[s];
    var data = sheet.getDataRange().getValues();
    for (var r = 0; r < data.length; r++) {
      if (_text(data[r][0]).toLowerCase() === 'invoice #') {
        var col = {};
        for (var c = 0; c < data[r].length; c++) {
          var head = _text(data[r][c]).toLowerCase();
          if (head) col[head] = c + 1;
        }
        return { sheet: sheet, headerRow: r + 1, col: col, data: data };
      }
    }
  }
  throw new Error('Could not find the invoice table. It needs a heading row '
    + 'whose first cell says "Invoice #".');
}


// Read the label/value pairs above the table (Client Email, Monthly Rate, etc).
function _readSettings(table) {
  var cfg = {};
  for (var r = 0; r < table.headerRow - 1; r++) {
    var label = _text(table.data[r][0]).toLowerCase();
    if (label && table.data[r].length > 1) cfg[label] = table.data[r][1];
  }
  return cfg;
}


function _readTemplate() {
  var sheet = _templateSheet();
  var subject = _text(sheet.getRange('B1').getValue());
  var body = _text(sheet.getRange('B2').getValue());
  if (!subject && !body) {
    throw new Error('The "' + TEMPLATE_TAB + '" tab is empty. Delete the tab '
      + 'and use the Invoices menu again to rebuild it.');
  }
  return { subject: subject, body: body };
}


// The wording tab, created with sensible starter text the first time.
function _templateSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(TEMPLATE_TAB);
  if (sheet) return sheet;

  sheet = ss.insertSheet(TEMPLATE_TAB);
  sheet.getRange('A1').setValue('Subject').setFontWeight('bold');
  sheet.getRange('A2').setValue('Body').setFontWeight('bold');
  sheet.getRange('A4').setValue('Placeholders you can use').setFontWeight('bold');

  sheet.getRange('B1').setValue(
    'JSSA Website Services - Invoice {{InvoiceNo}} ({{Period}})');

  sheet.getRange('B2').setValue(
    'Hello,\n'
    + '\n'
    + 'Here is the invoice for JSSA website services for {{Period}}.\n'
    + '\n'
    + 'Invoice #:   {{InvoiceNo}}\n'
    + 'Period:      {{Period}}\n'
    + 'Amount due:  {{Amount}}\n'
    + 'Date sent:   {{DateSent}}\n'
    + '\n'
    + 'Payment: {{PaymentMethod}}\n'
    + '\n'
    + 'Note: {{Notes}}\n'
    + '\n'
    + 'Thanks very much,\n'
    + 'Tom\n'
    + 'Jupiter Senior Softball Association');

  var help = [
    ['{{InvoiceNo}}', 'The invoice number on the row, e.g. 2026-08'],
    ['{{Period}}', 'The billing period, e.g. August 2026'],
    ['{{Amount}}', 'Amount Billed on that row'],
    ['{{DateSent}}', 'Date Sent on the row, or today if blank'],
    ['{{Today}}', "Today's date"],
    ['{{PaymentMethod}}', 'The Payment Method line from the top of the sheet'],
    ['{{MonthlyRate}}', 'The Monthly Rate from the top of the sheet'],
    ['{{Notes}}', 'Notes on that row (line vanishes if empty)'],
    ['{{Status}}', 'PAID or UNPAID'],
    ['{{Client}}', 'The Client name from the top of the sheet'],
    ['{{BalanceDue}}', 'Balance Due from the top of the sheet'],
    ['{{TotalBilled}}', 'Total Billed from the top of the sheet'],
    ['{{TotalReceived}}', 'Total Received from the top of the sheet']
  ];
  sheet.getRange(5, 1, help.length, 2).setValues(help);

  sheet.getRange('A1:A2').setVerticalAlignment('top');
  sheet.getRange('B2').setWrap(true);
  sheet.setColumnWidth(1, 190);
  sheet.setColumnWidth(2, 520);
  sheet.setRowHeight(2, 300);
  return sheet;
}


/* ========================================================================
   SMALL HELPERS
   ======================================================================== */

function _text(v) {
  return (v === null || v === undefined) ? '' : String(v).trim();
}


// Show money as $1,234.56 whether the cell holds a number or already-typed text.
function _money(v) {
  if (v === null || v === undefined || v === '') return '';
  if (typeof v === 'number') return Utilities.formatString('$%,.2f', v);
  var n = Number(String(v).replace(/[$,\s]/g, ''));
  return isNaN(n) ? _text(v) : Utilities.formatString('$%,.2f', n);
}


function _dateText(v) {
  if (!v) return '';
  if (Object.prototype.toString.call(v) === '[object Date]') {
    var tz = SpreadsheetApp.getActiveSpreadsheet().getSpreadsheetTimeZone();
    return Utilities.formatDate(v, tz, 'MMMM d, yyyy');
  }
  return _text(v);
}

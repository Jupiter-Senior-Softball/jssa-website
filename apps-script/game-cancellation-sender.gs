/**
 * JSSA — Game Cancellation Sender
 * ---------------------------------------------------------------------------
 * This is the piece that actually sends the "today's games are cancelled"
 * email. It runs inside a league Gmail account, because only code running in
 * an account can send mail as that account.
 *
 * Install it TWICE:
 *   1. jssagames@gmail.com   — the main sender (the first 100 people)
 *   2. jssaadmin@gmail.com   — the backup, for anyone past the first 100
 * Both copies are identical apart from the account you install them in. Use
 * the SAME secret in both.
 *
 * The website never sends mail itself and never holds a mail password. It just
 * hands this script a finished message and a list of addresses.
 *
 * HOW TO INSTALL (do this signed in as the account, for each of the two):
 *   1. Go to  https://script.google.com  and click  New project.
 *   2. Delete the sample code, paste ALL of this file, and Save.
 *   3. Change SECRET below to a long random phrase — the SAME phrase in both
 *      accounts.
 *   4. Pick  authorizeNow  in the function dropdown and click Run once, then
 *      approve the permissions (on the "unverified app" screen choose
 *      Advanced -> Go to ... -> Allow). Skipping this makes the web app fail.
 *   5. Deploy > New deployment > (gear) Web app.
 *        Execute as:      Me
 *        Who has access:  Anyone
 *      Deploy, then COPY the Web app URL (it ends in /exec).
 *   6. Add  ?key=YOUR_SECRET  on the end of that URL.
 *   7. Paste it into the control sheet's "Cancellation Settings" tab:
 *        jssagames@  URL -> the  Sender URL  row
 *        jssaadmin@  URL -> the  Overflow sender URL  row
 * ---------------------------------------------------------------------------
 */

// Use a long random phrase. The SAME phrase in both accounts, and in each URL
// you paste into the settings tab (the ?key=... part).
var SECRET = 'PUT_A_LONG_RANDOM_PHRASE_HERE';

// Never email more than this many people in one call, whatever is asked for.
// A backstop against a mistake somewhere else emailing the whole league.
var MAX_PER_CALL = 150;


// Run this ONCE from the editor to grant permission. Harmless to leave here.
function authorizeNow() {
  Logger.log('Remaining sends today: ' + MailApp.getRemainingDailyQuota());
}


function doPost(e) {
  try {
    var key = (e && e.parameter && e.parameter.key) || '';
    if (key !== SECRET) {
      return _json({ ok: false, sent: 0, error: 'unauthorized' });
    }

    var body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var subject = String(body.subject || '').trim();
    var text = String(body.body || '').trim();
    var testTo = String(body.test_to || '').trim();
    var list = body.recipients || [];

    if (!subject || !text) {
      return _json({ ok: false, sent: 0, error: 'missing subject or body' });
    }

    // Clean the list: real-looking addresses only, no duplicates.
    var seen = {};
    var to = [];
    for (var i = 0; i < list.length; i++) {
      var a = String(list[i] || '').trim();
      if (!a || a.indexOf('@') < 1) continue;
      var k = a.toLowerCase();
      if (seen[k]) continue;
      seen[k] = true;
      to.push(a);
    }
    if (to.length > MAX_PER_CALL) {
      to = to.slice(0, MAX_PER_CALL);
    }

    // Test mode: everything goes to one address instead of the players.
    if (testTo) {
      MailApp.sendEmail({
        to: testTo,
        subject: '[TEST] ' + subject,
        body: 'TEST — this would have gone to ' + to.length + ' players.\n\n' + text
      });
      return _json({ ok: true, sent: 0, test: true, would_send: to.length });
    }

    if (!to.length) {
      return _json({ ok: true, sent: 0, error: 'no valid addresses' });
    }

    // Gmail counts PEOPLE, not messages, so check before starting.
    var remaining = MailApp.getRemainingDailyQuota();
    if (remaining < to.length) {
      return _json({
        ok: false, sent: 0, remaining: remaining,
        error: 'daily email limit too low — needed ' + to.length +
               ', only ' + remaining + ' left on this account'
      });
    }

    // One BCC message: nobody sees anyone else's address, and it counts as a
    // single send against the account's message count.
    MailApp.sendEmail({
      to: Session.getEffectiveUser().getEmail(),
      bcc: to.join(','),
      subject: subject,
      body: text
    });

    return _json({
      ok: true,
      sent: to.length,
      remaining: MailApp.getRemainingDailyQuota()
    });

  } catch (err) {
    return _json({ ok: false, sent: 0, error: String(err) });
  }
}


// A plain GET is only ever used to check the script is alive and authorized.
function doGet(e) {
  var key = (e && e.parameter && e.parameter.key) || '';
  if (key !== SECRET) {
    return _json({ ok: false, error: 'unauthorized' });
  }
  return _json({
    ok: true,
    ready: true,
    account: Session.getEffectiveUser().getEmail(),
    remaining_today: MailApp.getRemainingDailyQuota()
  });
}


function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

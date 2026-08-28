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

// Gmail refuses a message addressed to more than 50 people (a separate limit
// from the ~100-a-day one) and answers "Limit Exceeded: Email Recipients Per
// Message". So a big roster goes out as several messages of this size. 45
// leaves room for the copy the account sends itself.
var BATCH_SIZE = 45;


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

    // How many real players this message is for. Kept even in test mode, so a
    // practice run can report what the real send would do.
    var realCount = to.length;

    if (!realCount) {
      return _json({ ok: true, sent: 0, error: 'no valid addresses' });
    }

    // Gmail counts PEOPLE, not messages, so check before starting.
    var remaining = MailApp.getRemainingDailyQuota();

    // TEST MODE. Deliberately takes the SAME route as the real send below -
    // same quota check, same BCC assembly, same call - so a practice run is a
    // true rehearsal rather than a different code path that happens to work.
    // Only the recipient list is swapped for the single test address.
    if (testTo) {
      var warning = '';
      if (remaining < realCount + Math.ceil(realCount / BATCH_SIZE)) {
        warning = 'The REAL send would be blocked right now: it needs ' +
                  (realCount + Math.ceil(realCount / BATCH_SIZE)) +
                  ' sends but only ' + remaining +
                  ' are left today on ' + Session.getEffectiveUser().getEmail() +
                  '. Set up the backup account, or wait until tomorrow.';
      }

      var testBatches = Math.ceil(realCount / BATCH_SIZE);
      MailApp.sendEmail({
        to: Session.getEffectiveUser().getEmail(),
        bcc: testTo,
        subject: '[TEST] ' + subject,
        body: 'TEST — this is exactly the message that would go by BCC to ' +
              realCount + ' player' + (realCount === 1 ? '' : 's') +
              ', from this account, in ' + testBatches + ' message' +
              (testBatches === 1 ? '' : 's') + ' of up to ' + BATCH_SIZE +
              ' (Gmail refuses more than 50 on one message).\n' +
              (warning ? '\n*** ' + warning + ' ***\n' : '') +
              '\n----------------------------------------\n\n' + text
      });

      return _json({
        ok: true, sent: 0, test: true,
        would_send: realCount,
        batches: testBatches,
        remaining: remaining,
        warning: warning
      });
    }

    // Each message also costs one recipient for the copy sent to this account.
    var batches = Math.ceil(realCount / BATCH_SIZE);
    if (remaining < realCount + batches) {
      return _json({
        ok: false, sent: 0, remaining: remaining,
        error: 'daily email limit too low — needed ' + (realCount + batches) +
               ', only ' + remaining + ' left on this account'
      });
    }

    // BCC, so nobody sees anyone else's address, in batches of BATCH_SIZE so
    // no single message trips Gmail's recipients-per-message limit. A batch
    // that fails does not stop the rest: better that most people hear than
    // nobody does, and the ones missed are reported back by name.
    var sent = 0;
    var missed = [];
    var firstError = '';

    for (var start = 0; start < to.length; start += BATCH_SIZE) {
      var batch = to.slice(start, start + BATCH_SIZE);
      try {
        MailApp.sendEmail({
          to: Session.getEffectiveUser().getEmail(),
          bcc: batch.join(','),
          subject: subject,
          body: text
        });
        sent += batch.length;
      } catch (err) {
        missed = missed.concat(batch);
        if (!firstError) firstError = String(err);
      }
      Utilities.sleep(200);
    }

    return _json({
      ok: sent > 0 && missed.length === 0,
      sent: sent,
      missed: missed,
      batches: batches,
      error: firstError,
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

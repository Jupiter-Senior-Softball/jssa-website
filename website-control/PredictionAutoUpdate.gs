/**
 * PredictionAutoUpdate.gs — "watchdog" for the JSSA prediction contest.
 *
 * WHY THIS EXISTS
 * ---------------
 * When a score is entered from the WEBSITE / board portal, the winner is
 * written into the Prediction Games tab through the Sheets API (a "behind the
 * scenes" write). The sheet's simple onEdit trigger only fires on values a
 * person types BY HAND — it is blind to API/programmatic writes — so the full
 * update chain (score → analytics → leaderboard → champions → metrics) never
 * runs, and the homepage "Season insights" / leaderboard go stale. The website
 * tries to compensate with a fire-and-forget ping, but that is unreliable.
 *
 * This watchdog runs on a TIME trigger every few minutes. It does nothing when
 * there is nothing new; when it sees a winner that has not been scored yet, it
 * runs the exact same chain onEdit would have run. Because scorePredictions()
 * marks each game "Scored = true", each game is processed once and then the
 * watchdog goes idle again — no matter how the score was entered.
 *
 * INSTALL (one time):
 *   In the Website Control Apps Script editor, add this as a new file, Save,
 *   then run installPredictionAutoUpdateTrigger_() once (pick it in the
 *   function dropdown → Run, and approve permissions if asked).
 *
 * UNDO:
 *   Run removePredictionAutoUpdateTrigger_() once. That stops all future
 *   automatic runs. Deleting this file removes the code entirely. Nothing else
 *   in the contest is touched.
 */

// How often the watchdog checks for freshly-entered scores.
// Allowed values for everyMinutes(): 1, 5, 10, 15, 30.
var PRED_AUTOUPDATE_EVERY_MINUTES = 5;

var PRED_AUTOUPDATE_HANDLER = 'predictionAutoUpdate_';


/**
 * The watchdog itself. Safe to run any time: it only does work when a winner
 * has been entered that has not been scored yet.
 */
function predictionAutoUpdate_() {
  // Guard against overlapping runs (e.g. a hand-edit's onEdit firing at the
  // same time). If another run holds the lock, skip this cycle — the next one
  // will catch anything still pending.
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName('Prediction Games');
    if (!sheet) return;

    var data = sheet.getDataRange().getValues();
    if (data.length < 2) return;

    var headers = data[0];
    var winnerCol = headers.indexOf('Winner');
    var scoredCol = headers.indexOf('Scored');
    if (winnerCol < 0 || scoredCol < 0) return;

    var hasPending = false;
    for (var r = 1; r < data.length; r++) {
      var winner = String(data[r][winnerCol] || '').trim().toUpperCase();
      var scored = data[r][scoredCol] === true ||
                   String(data[r][scoredCol]).trim().toUpperCase() === 'TRUE';
      if ((winner === 'H' || winner === 'V' || winner === 'T') && !scored) {
        hasPending = true;
        break;
      }
    }
    if (!hasPending) return;   // nothing new — stay idle, do no work

    // A result was entered that the sheet's own onEdit never saw. Run the same
    // chain onEdit / the website "score" button would have run. scorePredictions()
    // marks each game Scored = true, so these games won't be reprocessed.
    scorePredictions();
    updatePredictionAnalytics();
    updatePredictionLeaderboard();
    updatePredictionChampions();
    updatePredictionMetrics();
  } finally {
    lock.releaseLock();
  }
}


/**
 * Run ONCE to turn the watchdog on. Removes any existing copy first so it can
 * be re-run safely without stacking duplicate triggers.
 */
function installPredictionAutoUpdateTrigger_() {
  removePredictionAutoUpdateTrigger_();

  ScriptApp.newTrigger(PRED_AUTOUPDATE_HANDLER)
    .timeBased()
    .everyMinutes(PRED_AUTOUPDATE_EVERY_MINUTES)
    .create();

  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Prediction auto-update watchdog is ON (checks every ' +
    PRED_AUTOUPDATE_EVERY_MINUTES + ' minutes).');
}


/**
 * Run ONCE to turn the watchdog off (undo). Safe to run even if it isn't
 * installed.
 */
function removePredictionAutoUpdateTrigger_() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === PRED_AUTOUPDATE_HANDLER) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Prediction auto-update watchdog is OFF.');
}

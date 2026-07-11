/**
 * PhotoAlbumSweep.gs — keep ALL uploaded game photos in ONE flat album.
 *
 * THE PROBLEM
 * -----------
 * The photo-upload Google Form drops every upload into its own auto-created
 * "(File responses)" folder — a SEPARATE, nested folder from the album the
 * website shows. Google won't let a Form save uploads into an existing folder,
 * and simply moving that folder inside the album would leave a sub-folder that
 * people have to click into. Neither gives you one clean, flat album.
 *
 * WHAT THIS DOES
 * --------------
 * Every few minutes it moves each uploaded file OUT of the form's folder and
 * straight INTO the single flat album ("JSSA Game Photos"). Result:
 *   • Anyone who opens the album sees every photo in ONE place (no sub-folders).
 *   • The homepage (which reads that album) shows every new upload.
 *   • Moved uploads inherit the album's "anyone with the link can view" sharing.
 * Moving files does NOT affect the form, and each file keeps its web address,
 * so nothing that already links to a photo breaks.
 *
 * YOU ARE IN CONTROL: the two folders it touches are the constants below.
 *
 * SETUP (one time): Website Control sheet -> Extensions -> Apps Script -> add
 * this as a new file -> Save -> run installPhotoSweep once and approve the
 * permission prompt (it needs permission to move your Drive files).
 *
 * UNDO: run removePhotoSweep once. That stops the automatic moves. Nothing is
 * ever deleted.
 */

// The ONE flat album the website shows and players browse ("JSSA Game Photos").
var PHOTO_ALBUM_FOLDER_ID =
  "1bxCZ2BXHqZzNYS92CChaQEsQQY5unV0WvNQsdFpraDKOX_GdY4crTg1lpAcuHtEb5xxKGApZ";

// The upload form's auto-created folder(s) to pull photos FROM. If you ever
// rebuild the form and Google makes a new "(File responses)" folder, add its id
// to this list (comma-separated) and the sweep will pull from it too.
var PHOTO_UPLOAD_SOURCE_FOLDER_IDS = [
  // "Upload Your Photos and Videos Here (File responses)"
  "1N7Ltd_ekwZhJH46jUhalto2YxZD3v3hevYuA0mcEsLTCOH-0D3kPxPrjVRTcf0aneR3w-SIe"
];

// How often the sweep runs. Allowed: 1, 5, 10, 15, 30.
var PHOTO_SWEEP_EVERY_MINUTES = 5;

var PHOTO_SWEEP_HANDLER = "sweepPhotoUploadsIntoAlbum";


/**
 * Move every file out of the form's upload folder(s) into the flat album.
 * Safe to run any time; when the source folders are empty it does nothing.
 */
function sweepPhotoUploadsIntoAlbum() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return 0;   // another run is busy; skip this cycle

  try {
    var album = DriveApp.getFolderById(PHOTO_ALBUM_FOLDER_ID);
    var moved = 0;

    for (var i = 0; i < PHOTO_UPLOAD_SOURCE_FOLDER_IDS.length; i++) {
      var srcId = String(PHOTO_UPLOAD_SOURCE_FOLDER_IDS[i] || "").trim();
      if (!srcId || srcId === PHOTO_ALBUM_FOLDER_ID) continue;

      var src;
      try { src = DriveApp.getFolderById(srcId); } catch (e) { continue; }

      var files = src.getFiles();
      while (files.hasNext()) {
        var f = files.next();
        // moveTo() flattens the file directly into the album (one parent only).
        try { f.moveTo(album); moved++; } catch (e) { /* skip a locked file */ }
      }
    }

    Logger.log("sweepPhotoUploadsIntoAlbum moved " + moved + " file(s).");
    return moved;
  } finally {
    lock.releaseLock();
  }
}


/** Run ONCE to turn the automatic sweep on (and move whatever is waiting now). */
function installPhotoSweep() {
  removePhotoSweep();
  ScriptApp.newTrigger(PHOTO_SWEEP_HANDLER)
    .timeBased()
    .everyMinutes(PHOTO_SWEEP_EVERY_MINUTES)
    .create();

  var n = sweepPhotoUploadsIntoAlbum();
  try {
    SpreadsheetApp.getActive().toast(
      "Photo sweep is ON (every " + PHOTO_SWEEP_EVERY_MINUTES +
      " min). Moved " + (n || 0) + " waiting photo(s) into the album.");
  } catch (e) {}
  Logger.log("Photo sweep installed. Moved " + (n || 0) + " waiting file(s).");
}


/** Run ONCE to turn the automatic sweep off (undo). Safe even if not installed. */
function removePhotoSweep() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === PHOTO_SWEEP_HANDLER) ScriptApp.deleteTrigger(t);
  });
  try { SpreadsheetApp.getActive().toast("Photo sweep is OFF."); } catch (e) {}
}

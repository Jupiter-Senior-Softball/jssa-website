/**
 * Website Control — Apps Script source (captured copy).
 *
 * This is the prediction-contest "brain" bound to the Website Control Google
 * Sheet (Extensions -> Apps Script). It is NOT deployed by Render; it runs
 * inside Google. This file is a faithful capture kept in version control so the
 * logic is reviewable (see website-control/README.md for why that matters).
 *
 * IMPORTANT: editing this file does NOT change the live script. To apply a
 * change, paste the updated function into the Apps Script editor and deploy a
 * NEW VERSION of the EXISTING deployment (never a new deployment — that changes
 * the /exec URL and breaks the hard-coded links).
 */

function getPredictionControlValue_(settingName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Prediction Control');
  const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, 2).getValues();

  for (const row of values) {
    if (String(row[0]).trim() === settingName) {
      return row[1];
    }
  }

  return '';
}

function getOpenPredictionGamesForTest_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Prediction Games');
  const values = sheet.getDataRange().getValues();

  const headers = values[0];
  const rows = values.slice(1);

  const gameDateCol = headers.indexOf('Game Date');
  const fieldCol = headers.indexOf('Field');
  const homeCaptainCol = headers.indexOf('Home Captain');
  const visitorCaptainCol = headers.indexOf('Visitor Captain');
  const statusCol = headers.indexOf('Status');
  const visibleTestCol = headers.indexOf('Visible In Test');

  return rows
    .filter(row =>
      String(row[statusCol]).trim() === 'Open' &&
      row[visibleTestCol] === true
    )
    .map(row => ({
      gameDate: row[gameDateCol],
      field: row[fieldCol],
      homeCaptain: row[homeCaptainCol],
      visitorCaptain: row[visitorCaptainCol]
    }));
}

function testGetOpenPredictionGames() {
  const games = getOpenPredictionGamesForTest_();
  Logger.log(JSON.stringify(games, null, 2));
}

function savePredictionSubmission(payload) {
  return savePredictionTestSubmission_(
    payload.picks,
    payload.player
  );
}

function savePredictionTestSubmission_(picks, player) {
  const ss = SpreadsheetApp.openById("1Bpb1PGs2-egEql9rgIsNzFWlRKSrBYLxWdy1NeFkmaM");
  const sheet = ss.getSheetByName('Prediction Picks');
  if (!sheet) {
  throw new Error(
    'Prediction Picks sheet was not found in this spreadsheet: ' +
    ss.getName()
  );
}

  const email = String(player.email || '').trim().toLowerCase();
const name = String(player.name || '').trim();
  const now = new Date();

  const lastRow = sheet.getLastRow();
  const existingValues = lastRow > 1
    ? sheet.getRange(2, 1, lastRow - 1, 11).getValues()
    : [];

  picks.forEach(pick => {
    const gameDate = normalizePredictionDateKey_(pick.gameDate);
    const field = String(pick.field || '').trim();
    const predictedWinner = String(pick.predictedWinner || '').trim();

    let existingRowNumber = null;

    for (let i = 0; i < existingValues.length; i++) {
      const row = existingValues[i];

      const rowEmail = String(row[1] || '').trim();
      const rowGameDate = normalizePredictionDateKey_(row[3]);
      const rowField = String(row[4] || '').trim();

      if (
        rowEmail === email &&
        rowGameDate === gameDate &&
        rowField === field
      ) {
        existingRowNumber = i + 2;
        break;
      }
    }

    if (existingRowNumber) {
      sheet.getRange(existingRowNumber, 3).setValue(name);
      sheet.getRange(existingRowNumber, 6).setValue(predictedWinner);
      sheet.getRange(existingRowNumber, 11).setValue(now);
      sheet.getRange(existingRowNumber, 12).setValue(getPredictionMonthKey_(pick.gameDate));
    } else {
      sheet.appendRow([
        now,
        email,
        name,
        gameDate,
        field,
        predictedWinner,
        '',
        '',
        '',
        false,
now,
getPredictionMonthKey_(pick.gameDate)
      ]);
    }
  });

  return {
    success: true,
    message: 'Your prediction has been submitted.'
  };
}

function testFindGameDayHeaderRow() {
  const ss = SpreadsheetApp.openById(
    '1oHgGae0aXVVsr7t9hmDmoLxZWO5p9rLFPebSsXoFfAA'
  );

  const sheet = ss.getSheetByName('Game_Day_Teams');
  const values = sheet.getDataRange().getDisplayValues();

  for (let r = 0; r < values.length; r++) {
    const rowText = values[r].join('|');
    if (rowText.includes('Today') || rowText.includes('Field 1')) {
      Logger.log((r + 1) + ': ' + rowText);
    }
  }
}

function testGetPredictionGamesFromGameDayTeams() {
  const games = getPredictionGamesFromGameDayTeams_();

  Logger.log(
    JSON.stringify(games, null, 2)
  );
}

function getPredictionGamesForBallot() {
  closeExpiredPredictionGames_();

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Prediction Games');

  if (!sheet) {
    return {
      open: false,
      message: 'Prediction Games sheet was not found.',
      games: []
    };
  }

  const data = sheet.getDataRange().getDisplayValues();

  if (data.length < 2) {
    return {
      open: false,
      message: 'No prediction games are currently available.',
      games: []
    };
  }

  const games = [];

  for (let r = 1; r < data.length; r++) {
    const row = data[r];

    const gameDate = String(row[0] || '').trim();
    const field = String(row[1] || '').trim();
    const homeCaptain = String(row[2] || '').trim();
    const visitorCaptain = String(row[3] || '').trim();
    const status = String(row[4] || '').trim();
    const visibleInTest = String(row[5] || '').trim().toUpperCase();

    if (!gameDate || !field || !homeCaptain || !visitorCaptain) continue;
    if (status !== 'Open') continue;
    if (visibleInTest !== 'TRUE') continue;

    games.push({
      gameDate: gameDate,
      field: field,
      homeCaptain: homeCaptain,
      visitorCaptain: visitorCaptain
    });
  }

  if (!games.length) {
    return {
      open: false,
      message: 'No prediction games are currently available.',
      games: []
    };
  }

  const openGames = games.filter(game => arePredictionsOpenForGameDate_(game.gameDate).open);

if (!openGames.length) {
  return {
    open: false,
    message: 'Predictions are now closed but new ballots will be released with the posting of the teams for the next scheduled JSSA pickup games.',
    games: []
  };
}

return {
  open: true,
  message: 'Predictions are open.',
  gameDate: openGames[0].gameDate,
  gameLocation: getPredictionGameLocation_(),
  games: openGames
};

  return {
    open: status.open,
    message: status.message,
    gameDate: games[0].gameDate,
    gameLocation: getPredictionGameLocation_(),
    games: games
  };
}

function getPredictionPlayerNameByEmail_(email) {
  const lookup = {
    'cosentinoteam@gmail.com': 'Tom Cosentino'
  };

  return lookup[email] || email;
}

function testPredictionRowMatching() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Prediction Picks');

  const email = 'cosentinoteam@gmail.com';
  const gameDate = 'Wednesday, June 3, 2026';
  const field = 'Field 1';

  const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, 11).getValues();

  values.forEach((row, i) => {
    Logger.log('Row ' + (i + 2));
    Logger.log('Email: [' + row[1] + ']');
    Logger.log('Game Date: [' + row[3] + ']');
    Logger.log('Field: [' + row[4] + ']');

    Logger.log(
      'MATCH = ' +
      (
        String(row[1]).trim() === email &&
        String(row[3]).trim() === gameDate &&
        String(row[4]).trim() === field
      )
    );
  });
}

function normalizePredictionDateKey_(value) {
  if (!value) return '';

  const date = new Date(value);

  if (!isNaN(date)) {
    return Utilities.formatDate(
      date,
      Session.getScriptTimeZone(),
      'yyyy-MM-dd'
    );
  }

  return String(value).trim();
}

function arePredictionsOpenForGameDate_(gameDateValue) {
  const closeHour = Number(getPredictionControlValue_('Prediction Close Hour')) || 8;

  const gameDate = new Date(gameDateValue);

  if (isNaN(gameDate)) {
    return {
      open: false,
      message: 'Prediction deadline could not be determined.'
    };
  }

  const deadline = new Date(gameDate);
  deadline.setHours(closeHour, 0, 0, 0);

  const now = new Date();

  if (now > deadline) {
    return {
      open: false,
      message: 'Predictions are now closed but new ballots will be released with the posting of the teams for the next scheduled JSSA pickup games.'
    };
  }

  return {
    open: true,
    message: 'Predictions are open.'
  };
}

function scorePredictions() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const picksSheet = ss.getSheetByName('Prediction Picks');
  const gamesSheet = ss.getSheetByName('Prediction Games');

  const picksData = picksSheet.getDataRange().getValues();
  const gamesData = gamesSheet.getDataRange().getValues();

  const picksHeaders = picksData[0];
  const gamesHeaders = gamesData[0];

  const pGameDate = picksHeaders.indexOf('Game Date');
  const pField = picksHeaders.indexOf('Field');
  const pPredictedWinner = picksHeaders.indexOf('Predicted Winner');
  const pActualWinner = picksHeaders.indexOf('Actual Winner');
  const pCorrect = picksHeaders.indexOf('Correct');
  const pPoints = picksHeaders.indexOf('Points');
  const pScored = picksHeaders.indexOf('Scored');

  const gGameDate = gamesHeaders.indexOf('Game Date');
  const gField = gamesHeaders.indexOf('Field');
  const gWinner = gamesHeaders.indexOf('Winner');
  const gScored = gamesHeaders.indexOf('Scored');

  for (let g = 1; g < gamesData.length; g++) {
    const gameRow = gamesData[g];

    const gameDateKey = normalizePredictionDateKey_(gameRow[gGameDate]);
    const field = String(gameRow[gField] || '').trim();
    const winner = String(gameRow[gWinner] || '').trim().toUpperCase();
    const alreadyScored = gameRow[gScored] === true;

    if (!gameDateKey || !field || !winner || alreadyScored) continue;

    for (let p = 1; p < picksData.length; p++) {
      const pickRow = picksData[p];

      const pickDateKey = normalizePredictionDateKey_(pickRow[pGameDate]);
      const pickField = String(pickRow[pField] || '').trim();
      const predictedWinner = String(pickRow[pPredictedWinner] || '').trim().toUpperCase();

      if (pickDateKey === gameDateKey && pickField === field) {
        const correct = predictedWinner === winner;

        picksSheet.getRange(p + 1, pActualWinner + 1).setValue(winner);
        picksSheet.getRange(p + 1, pCorrect + 1).setValue(correct);
        picksSheet.getRange(p + 1, pPoints + 1).setValue(correct ? 1 : 0);
        picksSheet.getRange(p + 1, pScored + 1).setValue(true);
      }
    }

    gamesSheet.getRange(g + 1, gScored + 1).setValue(true);
  }

  updatePredictionAnalytics();
  SpreadsheetApp.getActiveSpreadsheet().toast('Predictions scored.');
}

function updatePredictionLeaderboard() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const picksSheet = ss.getSheetByName('Prediction Picks');
  const leaderboardSheet = ss.getSheetByName('Prediction Leaderboard');

  const minimumPredictions =
    Number(getPredictionControlValue_('Minimum Monthly Predictions')) || 4;

  const data = picksSheet.getDataRange().getValues();
  const headers = data[0];
  const rows = data.slice(1);

  const emailCol = headers.indexOf('Email');
  const nameCol = headers.indexOf('Name');
  const correctCol = headers.indexOf('Correct');
  const pointsCol = headers.indexOf('Points');
  const scoredCol = headers.indexOf('Scored');

  const totals = {};

  rows.forEach(row => {
    if (row[scoredCol] !== true) return;

    const email = String(row[emailCol] || '').trim();
    const name = String(row[nameCol] || '').trim();

    if (!email) return;

    if (!totals[email]) {
      totals[email] = {
        email,
        name,
        predictions: 0,
        correct: 0,
        points: 0
      };
    }

    totals[email].predictions += 1;

    if (row[correctCol] === true) {
      totals[email].correct += 1;
    }

    totals[email].points += Number(row[pointsCol]) || 0;
  });

  const players = Object.values(totals).sort((a, b) => {
    const aAccuracy = a.predictions ? a.correct / a.predictions : 0;
    const bAccuracy = b.predictions ? b.correct / b.predictions : 0;

    if (bAccuracy !== aAccuracy) return bAccuracy - aAccuracy;
    if (b.points !== a.points) return b.points - a.points;

    return a.name.localeCompare(b.name);
  });

  const output = [
    ['Rank', 'Player Name', 'Player Email', 'Predictions', 'Correct', 'Incorrect', 'Points', 'Accuracy %', 'Qualified']
  ];

  players.forEach((player, index) => {
    const incorrect = player.predictions - player.correct;
    const accuracy = player.predictions
      ? player.correct / player.predictions
      : 0;

    output.push([
      index + 1,
      player.name,
      player.email,
      player.predictions,
      player.correct,
      incorrect,
      player.points,
      accuracy,
      player.predictions >= minimumPredictions ? 'YES' : 'NO'
    ]);
  });

  leaderboardSheet.clearContents();

  leaderboardSheet
    .getRange(1, 1, output.length, output[0].length)
    .setValues(output);

  leaderboardSheet
    .getRange(1, 1, 1, output[0].length)
    .setFontWeight('bold');

  if (output.length > 1) {
    leaderboardSheet
      .getRange(2, 8, output.length - 1, 1)
      .setNumberFormat('0.0%');
  }

  SpreadsheetApp.getActiveSpreadsheet().toast('Prediction leaderboard updated.');
}

function createPredictionGamesFromGameDayTeams() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const gamesSheet = ss.getSheetByName('Prediction Games');

  const games = getPredictionGamesFromGameDayTeams_();

  if (!games.length) {
    SpreadsheetApp.getActiveSpreadsheet().toast('No games found on Game_Day_Teams.');
    return;
  }

  const existingData = gamesSheet.getDataRange().getValues();
  const headers = existingData[0];

  const gameDateCol = headers.indexOf('Game Date');
  const fieldCol = headers.indexOf('Field');

  const existingKeys = {};

  for (let i = 1; i < existingData.length; i++) {
    const row = existingData[i];

    const dateKey = normalizePredictionDateKey_(row[gameDateCol]);
    const field = String(row[fieldCol] || '').trim();

    if (dateKey && field) {
      existingKeys[dateKey + '|' + field] = true;
    }
  }

  const rowsToAdd = [];

  games.forEach(game => {
    const dateKey = normalizePredictionDateKey_(game.gameDate);
    const key = dateKey + '|' + game.field;

    if (existingKeys[key]) return;

    rowsToAdd.push([
      game.gameDate,
      game.field,
      game.homeCaptain,
      game.visitorCaptain,
      'Open',
      true,
      '',
      false
    ]);
  });

  if (rowsToAdd.length) {
    gamesSheet
      .getRange(gamesSheet.getLastRow() + 1, 1, rowsToAdd.length, rowsToAdd[0].length)
      .setValues(rowsToAdd);
  }

  SpreadsheetApp.getActiveSpreadsheet().toast(
    rowsToAdd.length + ' prediction game(s) created.'
  );
}

function getPredictionMonthKey_(gameDateValue) {
  const date = new Date(gameDateValue);

  if (isNaN(date)) return '';

  return Utilities.formatDate(
    date,
    Session.getScriptTimeZone(),
    'yyyy-MM'
  );
}

function populatePredictionMonths() {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName('Prediction Picks');

  const data = sheet.getDataRange().getValues();

  const headers = data[0];

  const gameDateCol = headers.indexOf('Game Date');
  const monthCol = headers.indexOf('Prediction Month');

  for (let r = 1; r < data.length; r++) {
    const gameDate = data[r][gameDateCol];

    if (!gameDate) continue;

    sheet
      .getRange(r + 1, monthCol + 1)
      .setValue(getPredictionMonthKey_(gameDate));
  }

  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Prediction months populated.'
  );
}

function updatePredictionChampions() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const picksSheet = ss.getSheetByName('Prediction Picks');
  const championsSheet = ss.getSheetByName('Prediction Champions');

  const minimumPredictions =
    Number(getPredictionControlValue_('Minimum Monthly Predictions')) || 4;

  const data = picksSheet.getDataRange().getValues();
  const headers = data[0];
  const rows = data.slice(1);

  const emailCol = headers.indexOf('Email');
  const nameCol = headers.indexOf('Name');
  const correctCol = headers.indexOf('Correct');
  const pointsCol = headers.indexOf('Points');
  const scoredCol = headers.indexOf('Scored');
  const monthCol = headers.indexOf('Prediction Month');

  const monthlyTotals = {};

  rows.forEach(row => {
    if (row[scoredCol] !== true) return;

    const month = String(row[monthCol] || '').trim();
    const email = String(row[emailCol] || '').trim();
    const name = String(row[nameCol] || '').trim();

    if (!month || !email) return;

    const key = month + '|' + email;

    if (!monthlyTotals[key]) {
      monthlyTotals[key] = {
        month,
        email,
        name,
        predictions: 0,
        correct: 0,
        points: 0
      };
    }

    monthlyTotals[key].predictions += 1;

    if (row[correctCol] === true) {
      monthlyTotals[key].correct += 1;
    }

    monthlyTotals[key].points += Number(row[pointsCol]) || 0;
  });

  const byMonth = {};

  Object.values(monthlyTotals).forEach(player => {
    if (player.predictions < minimumPredictions) return;

    if (!byMonth[player.month]) {
      byMonth[player.month] = [];
    }

    byMonth[player.month].push(player);
  });

  const output = [
  ['Month', 'Champion', 'Predictions', 'Correct', 'Incorrect', 'Points', 'Accuracy %']
];

  Object.keys(byMonth)
    .sort()
    .forEach(month => {
      Logger.log('MONTH KEY = [' + month + ']');
      const players = byMonth[month];

      players.sort((a, b) => {
        const aAccuracy = a.predictions ? a.correct / a.predictions : 0;
        const bAccuracy = b.predictions ? b.correct / b.predictions : 0;

        if (bAccuracy !== aAccuracy) return bAccuracy - aAccuracy;
        if (b.points !== a.points) return b.points - a.points;

        return a.name.localeCompare(b.name);
      });

      const champ = players[0];
      const accuracy = champ.predictions
        ? champ.correct / champ.predictions
        : 0;


      const monthDisplay = Utilities.formatDate(
  new Date(month),
  Session.getScriptTimeZone(),
  'MMMM yyyy'
);

output.push([
  monthDisplay,
  champ.name,
  champ.predictions,
  champ.correct,
  champ.predictions - champ.correct,
  champ.points,
  accuracy
]);
    });

  championsSheet.clearContents();

  championsSheet
    .getRange(1, 1, output.length, output[0].length)
    .setValues(output);

  championsSheet
    .getRange(1, 1, 1, output[0].length)
    .setFontWeight('bold');

  if (output.length > 1) {
    championsSheet
      .getRange(2, 7, output.length - 1, 1)
      .setNumberFormat('0.0%');
  }

  SpreadsheetApp.getActiveSpreadsheet().toast('Prediction champions updated.');
}

function getPredictionLeaderboardForWebsite() {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName('Prediction Leaderboard');

  const values = sheet.getDataRange().getDisplayValues()
    .filter(row => row.some(cell => String(cell).trim() !== ''));

  // Remove Player Email column for public website display.
  return values.map(row => [
    row[0], // Rank
    row[1], // Player Name
    row[3], // Predictions
    row[4], // Correct
    row[5], // Incorrect
    row[6], // Points
    row[7], // Accuracy %
    row[8]  // Qualified
  ]);
}

function getPredictionChampionsForWebsite() {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName('Prediction Champions');

  const values = sheet.getDataRange().getDisplayValues();

  return values.filter(row =>
    row.some(cell => String(cell).trim() !== '')
  );
}

function validatePredictionPlayerByEmail(email) {
  const PICKUP_GAME_SPREADSHEET_ID = '1YHKk8GLM9kqzSoWFxuUtFCH-B6crZ7SP5m4vogJVBwg';

  const normalizedEmail = String(email || '').trim().toLowerCase();

  if (!normalizedEmail) {
    return {
      valid: false,
      message: 'Please enter your email address.'
    };
  }

  const ss = SpreadsheetApp.openById(PICKUP_GAME_SPREADSHEET_ID);
  const sheet = ss.getSheetByName('JSSA Players');

  if (!sheet) {
    return {
      valid: false,
      message: 'JSSA player list was not found.'
    };
  }

  const data = sheet.getDataRange().getValues();
  const headers = data[0].map(h => String(h).trim());

  const emailCol = headers.indexOf('Email');
  const firstNameCol = headers.indexOf('First Name');
  const lastNameCol = headers.indexOf('Last Name');
  const activeCol = headers.indexOf('Active');

  for (let r = 1; r < data.length; r++) {
    const rowEmail = String(data[r][emailCol] || '').trim().toLowerCase();
    const active = data[r][activeCol] === true;

    if (rowEmail === normalizedEmail && active) {
      return {
        valid: true,
        email: rowEmail,
        name: String(data[r][firstNameCol] || '').trim() + ' ' +
              String(data[r][lastNameCol] || '').trim()
      };
    }
  }

  return {
    valid: false,
    message: 'Email address not found as an active JSSA member.'
  };
}

function getPredictionGameLocation_() {
  const ss = SpreadsheetApp.openById(
    '1oHgGae0aXVVsr7t9hmDmoLxZWO5p9rLFPebSsXoFfAA'
  );

  const sheet = ss.getSheetByName('Game_Day_Teams');

  if (!sheet) return '';

  return String(sheet.getRange('A3').getDisplayValue() || '').trim();
}

function closeExpiredPredictionGames_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Prediction Games');
  if (!sheet) return;

  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return;

  const headers = data[0];

  const gameDateCol = headers.indexOf('Game Date');
  const statusCol = headers.indexOf('Status');

  if (gameDateCol === -1 || statusCol === -1) {
    throw new Error('Prediction Games is missing Game Date or Status column.');
  }

  for (let r = 1; r < data.length; r++) {
    const gameDate = data[r][gameDateCol];
    const status = String(data[r][statusCol] || '').trim();

    if (status !== 'Open') continue;

    const openStatus = arePredictionsOpenForGameDate_(gameDate);

    if (!openStatus.open) {
      sheet.getRange(r + 1, statusCol + 1).setValue('Closed');
    }
  }
}

function getPredictionGamesFromGameDayTeams_() {
  const ss = SpreadsheetApp.openById('1oHgGae0aXVVsr7t9hmDmoLxZWO5p9rLFPebSsXoFfAA');
  const sheet = ss.getSheetByName('Game_Day_Teams');
  if (!sheet) throw new Error('Game_Day_Teams sheet not found.');

  const values = sheet.getDataRange().getDisplayValues();
  const displayDate = String(sheet.getRange('A2').getDisplayValue() || '').trim();

  let headerRowIndex = -1;
  for (let r = 0; r < values.length; r++) {
    if (String(values[r][0] || '').trim() === "Today's Players") { headerRowIndex = r; break; }
  }
  if (headerRowIndex === -1) throw new Error('Could not find Game_Day_Teams header row.');

  const headerRow = values[headerRowIndex];

  // Any column after the player-name column with a non-blank header is a
  // candidate field — whatever it's named this season ("Field 1", "Maplewood
  // East", etc.). We confirm it's a real game by finding both an H CAPTAIN and a
  // V CAPTAIN below it, so stray columns are ignored automatically.
  const fieldColumns = [];
  for (let c = 1; c < headerRow.length; c++) {
    const header = String(headerRow[c] || '').trim();
    if (header) fieldColumns.push({ field: header, col: c });
  }

  const games = [];
  fieldColumns.forEach(fieldInfo => {
    let homeCaptain = '', visitorCaptain = '';
    for (let r = headerRowIndex + 1; r < values.length; r++) {
      const playerName = String(values[r][0] || '').trim();
      const mark = String(values[r][fieldInfo.col] || '').trim().toUpperCase();
      if (!playerName) continue;
      if (mark === 'H CAPTAIN') homeCaptain = playerName;
      if (mark === 'V CAPTAIN') visitorCaptain = playerName;
    }
    if (homeCaptain && visitorCaptain) {
      games.push({ gameDate: displayDate, field: fieldInfo.field,
                   homeCaptain: homeCaptain, visitorCaptain: visitorCaptain });
    }
  });

  return games;
}

function syncPredictionGamesFromGameAssignment_() {
  const liveSS = SpreadsheetApp.openById("1YHKk8GLM9kqzSoWFxuUtFCH-B6crZ7SP5m4vogJVBwg");
const predictionSS = SpreadsheetApp.getActiveSpreadsheet();

  const assignmentSheet =
  liveSS.getSheetByName("Game Assignment Sheet") ||
  liveSS.getSheetByName("Game Assignment Tab");

  const predictionSheet =
  predictionSS.getSheetByName("Prediction Games") ||
  predictionSS.getSheetByName("Prediction Game") ||
  predictionSS.getSheetByName("Prediction Games Tab");

  if (!assignmentSheet) throw new Error("Game Assignment sheet not found.");
  if (!predictionSheet) throw new Error("Prediction Games sheet not found.");

  const gameDate = assignmentSheet.getRange("A2").getValue();
  if (!gameDate) throw new Error("Game date missing from A2.");

  const startRow = 10;
  const lastRow = assignmentSheet.getLastRow();
  if (lastRow < startRow) return;

  const fieldNames = assignmentSheet.getRange(9, 6, 1, 4).getDisplayValues()[0];

  const values = assignmentSheet
    .getRange(startRow, 1, lastRow - startRow + 1, 9)
    .getDisplayValues();

  const games = {};

  values.forEach(row => {
    const player = String(row[1] || "").trim();
    if (!player) return;

    for (let i = 0; i < 4; i++) {
      const fieldName = String(fieldNames[i] || "").trim();
      const mark = String(row[5 + i] || "").trim().toUpperCase();

      if (!fieldName || !mark.includes("CAPTAIN")) continue;

      if (!games[fieldName]) {
        games[fieldName] = {
          field: fieldName,
          homeCaptain: "",
          visitorCaptain: ""
        };
      }

      if (mark.startsWith("H")) games[fieldName].homeCaptain = player;
      if (mark.startsWith("V")) games[fieldName].visitorCaptain = player;
    }
  });

  const output = Object.values(games)
    .filter(g => g.homeCaptain && g.visitorCaptain)
    .map(g => [
      gameDate,
      g.field,
      g.homeCaptain,
      g.visitorCaptain,
      "Open",
      true,
      "",
      false
    ]);

  if (!output.length) {
    throw new Error("No complete Home/Visitor captain pairs found.");
  }

  const predValues = predictionSheet.getDataRange().getValues();

  for (let r = predValues.length; r >= 2; r--) {
    const rowDate = predValues[r - 1][0];
    const scored = predValues[r - 1][7];

    if (
      rowDate instanceof Date &&
      gameDate instanceof Date &&
      rowDate.toDateString() === gameDate.toDateString() &&
      scored !== true
    ) {
      predictionSheet.deleteRow(r);
    }
  }

  predictionSheet
    .getRange(predictionSheet.getLastRow() + 1, 1, output.length, 8)
    .setValues(output);
}

function testPredictionSync() {
  syncPredictionGamesFromGameAssignment_();
}

function updatePredictionAnalytics() {
  const ss = SpreadsheetApp.openById("1Bpb1PGs2-egEql9rgIsNzFWlRKSrBYLxWdy1NeFkmaM");

  const gamesSheet = ss.getSheetByName("Prediction Games");
  const picksSheet = ss.getSheetByName("Prediction Picks");
  const analyticsSheet = ss.getSheetByName("Prediction Analytics");

  if (!gamesSheet) throw new Error("Prediction Games sheet not found.");
  if (!picksSheet) throw new Error("Prediction Picks sheet not found.");
  if (!analyticsSheet) throw new Error("Prediction Analytics sheet not found.");

  const gamesData = gamesSheet.getDataRange().getValues();
  const picksData = picksSheet.getDataRange().getValues();

  const output = [[
    "Game Date", "Field", "Home Captain", "Visitor Captain",
    "Home Picks", "Visitor Picks", "Home %", "Visitor %",
    "Actual Winner", "Crowd Correct?", "Winning Side", "Margin %", "Total Picks"
  ]];

  for (let g = 1; g < gamesData.length; g++) {
    const gameDate = gamesData[g][0];
    const field = String(gamesData[g][1] || "").trim();
    const homeCaptain = gamesData[g][2];
    const visitorCaptain = gamesData[g][3];
    const winner = String(gamesData[g][6] || "").trim().toUpperCase();

    if (!gameDate || !field || !winner) continue;

    const gameDateKey = normalizePredictionDateKey_(gameDate);

    let homePicks = 0;
    let visitorPicks = 0;

    for (let p = 1; p < picksData.length; p++) {
      const pickDateKey = normalizePredictionDateKey_(picksData[p][3]);
      const pickField = String(picksData[p][4] || "").trim();
      const predictedWinner = String(picksData[p][5] || "").trim().toUpperCase();

      if (pickDateKey !== gameDateKey || pickField !== field) continue;

      if (predictedWinner === "H") homePicks++;
      if (predictedWinner === "V") visitorPicks++;
    }

    const totalPicks = homePicks + visitorPicks;
    if (!totalPicks) continue;

    const homePct = homePicks / totalPicks;
    const visitorPct = visitorPicks / totalPicks;

    const majority =
      homePicks > visitorPicks ? "H" :
      visitorPicks > homePicks ? "V" :
      "TIE";

    const crowdCorrect =
      majority === "TIE" ? "TIE" :
      majority === winner ? "YES" : "NO";

    const winningSide =
      winner === "H" ? "Home" :
      winner === "V" ? "Visitor" :
      winner;

    const marginPct = Math.abs(homePct - visitorPct);

    output.push([
      gameDate,
      field,
      homeCaptain,
      visitorCaptain,
      homePicks,
      visitorPicks,
      homePct,
      visitorPct,
      winningSide,
      crowdCorrect,
      winningSide,
      marginPct,
      totalPicks
    ]);
  }

  analyticsSheet.clearContents();

  analyticsSheet
    .getRange(1, 1, output.length, output[0].length)
    .setValues(output);

  analyticsSheet.getRange(1, 1, 1, output[0].length).setFontWeight("bold");

  if (output.length > 1) {
    analyticsSheet.getRange(2, 7, output.length - 1, 2).setNumberFormat("0.0%");
    analyticsSheet.getRange(2, 12, output.length - 1, 1).setNumberFormat("0.0%");

    analyticsSheet
      .getRange(2, 1, output.length - 1, output[0].length)
      .sort([
        { column: 1, ascending: false },
        { column: 2, ascending: true }
      ]);
  }

  SpreadsheetApp.getActiveSpreadsheet().toast("Prediction Analytics updated.");
}

function sendPredictionResultsEmails_TEST() {
  sendPredictionResultsEmails_(new Date(2026, 5, 12), true);
}

function sendPredictionResultsEmails_(targetDateString, testMode) {
  const ss = SpreadsheetApp.openById("1Bpb1PGs2-egEql9rgIsNzFWlRKSrBYLxWdy1NeFkmaM");

  const picksSheet = ss.getSheetByName("Prediction Picks");
  const analyticsSheet = ss.getSheetByName("Prediction Analytics");

  if (!picksSheet) throw new Error("Prediction Picks sheet not found.");
  if (!analyticsSheet) throw new Error("Prediction Analytics sheet not found.");

  const leaderboardUrl =
    "https://script.google.com/macros/s/AKfycbwqXbN6B6WNa7Dye3NJcUWzmNrMETCZWjW2F8JrjmhKb7F3idebOxiBeRm1Fpzpx1ij/exec?view=prediction_leaderboard";
  const dashboard = getPredictionDashboardForWebsite();

const dailyChampion = dashboard.dailyChampion || {};
const dailyLeague = dashboard.dailyLeague || {};
const monthlyLeader = dashboard.monthlyLeader || {};
const monthlyLeague = dashboard.monthlyLeague || {};
const yearlyLeague = dashboard.yearlyLeague || {};
  const picksData = picksSheet.getDataRange().getValues();
  const analyticsData = analyticsSheet.getDataRange().getValues();

  const targetDateKey = normalizePredictionDateKey_(targetDateString);

  const picksHeaders = picksData[0];
  const emailCol = picksHeaders.indexOf("Email");
  const nameCol = picksHeaders.indexOf("Name");
  const gameDateCol = picksHeaders.indexOf("Game Date");
  const fieldCol = picksHeaders.indexOf("Field");
  const predictedCol = picksHeaders.indexOf("Predicted Winner");
  const actualCol = picksHeaders.indexOf("Actual Winner");
  const correctCol = picksHeaders.indexOf("Correct");
  const scoredCol = picksHeaders.indexOf("Scored");

  const participants = {};

  for (let r = 1; r < picksData.length; r++) {
    const row = picksData[r];

    const rowDateKey = normalizePredictionDateKey_(row[gameDateCol]);
    const scored =
  row[scoredCol] === true ||
  String(row[scoredCol]).trim().toUpperCase() === "TRUE";

    if (rowDateKey !== targetDateKey || !scored) continue;

    const email = String(row[emailCol] || "").trim().toLowerCase();
    const name = String(row[nameCol] || "").trim() || email;

    if (!email) continue;

    if (!participants[email]) {
      participants[email] = {
        email,
        name,
        picks: [],
        correct: 0,
        total: 0
      };
    }

    const field = String(row[fieldCol] || "").trim();
    const predicted = String(row[predictedCol] || "").trim().toUpperCase();
    const actual = String(row[actualCol] || "").trim().toUpperCase();
    const correct = row[correctCol] === true;

    participants[email].picks.push({
      field,
      predicted,
      actual,
      correct
    });

    participants[email].total++;
    if (correct) participants[email].correct++;
  }

  if (!Object.keys(participants).length) {
    throw new Error("No scored prediction picks found for " + targetDateString);
  }

  let leagueCorrect = 0;
  let leagueTotal = 0;

  Object.values(participants).forEach(player => {
    leagueCorrect += player.correct;
    leagueTotal += player.total;
  });

  const leagueAccuracy = leagueTotal ? leagueCorrect / leagueTotal : 0;

  let analyticsRowsForDate = [];

  const analyticsHeaders = analyticsData[0];
  const aDateCol = analyticsHeaders.indexOf("Game Date");
  const aFieldCol = analyticsHeaders.indexOf("Field");
  const aHomePctCol = analyticsHeaders.indexOf("Home %");
  const aVisitorPctCol = analyticsHeaders.indexOf("Visitor %");
  const aCrowdCorrectCol = analyticsHeaders.indexOf("Crowd Correct?");
  const aTotalPicksCol = analyticsHeaders.indexOf("Total Picks");

  for (let r = 1; r < analyticsData.length; r++) {
    const row = analyticsData[r];
    const rowDateKey = normalizePredictionDateKey_(row[aDateCol]);

    if (rowDateKey === targetDateKey) {
      analyticsRowsForDate.push({
        field: row[aFieldCol],
        homePct: row[aHomePctCol],
        visitorPct: row[aVisitorPctCol],
        crowdCorrect: row[aCrowdCorrectCol],
        totalPicks: row[aTotalPicksCol]
      });
    }
  }

  const avgSplit = analyticsRowsForDate.length
    ? analyticsRowsForDate.reduce((sum, row) => sum + Math.max(Number(row.homePct) || 0, Number(row.visitorPct) || 0), 0) / analyticsRowsForDate.length
    : 0;

  Object.values(participants).forEach(player => {
    const playerAccuracy = player.total ? player.correct / player.total : 0;

    const comparison =
      playerAccuracy > leagueAccuracy ? "Above League Average" :
      playerAccuracy < leagueAccuracy ? "Below League Average" :
      "Equal to League Average";

    const resultRowsHtml = player.picks.map(pick => {
      const bg = pick.correct ? "#e6f4ea" : "#fce8e6";
      const icon = pick.correct ? "✅" : "❌";
      const text = pick.correct ? "Correct" : "Incorrect";

      return `
        <div style="padding:12px;background:${bg};border-bottom:1px solid #ddd;">
          ${icon} <strong>${pick.field}</strong> — ${text}
          <br>
          <span style="font-size:13px;color:#555;">
            Your pick: ${pick.predicted === "H" ? "Home" : "Visitor"} |
            Winner: ${pick.actual === "H" ? "Home" : "Visitor"}
          </span>
        </div>
      `;
    }).join("");

    const htmlBody = `
      <div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;background:#f6f7f9;padding:18px;">
        <div style="background:#1f4e79;color:white;padding:18px;border-radius:10px 10px 0 0;text-align:center;">
          <h2 style="margin:0;">JSSA Prediction Results</h2>
          <p style="margin:6px 0 0;">${targetDateString} Game Day Recap</p>
        </div>

        <div style="background:white;padding:20px;border-radius:0 0 10px 10px;">
          <h3 style="margin-top:0;">${player.name}, your results are in.</h3>

          <div style="display:flex;gap:10px;margin:18px 0;">
            <div style="flex:1;background:#e6f4ea;padding:14px;border-radius:8px;text-align:center;">
              <div style="font-size:28px;font-weight:bold;">${player.correct} / ${player.total}</div>
              <div>Today</div>
            </div>
            <div style="flex:1;background:#e8f0fe;padding:14px;border-radius:8px;text-align:center;">
              <div style="font-size:28px;font-weight:bold;">${formatPercent_(playerAccuracy)}</div>
              <div>Your Accuracy</div>
            </div>
            <div style="flex:1;background:#fff2cc;padding:14px;border-radius:8px;text-align:center;">
              <div style="font-size:20px;font-weight:bold;">${comparison}</div>
              <div>League Comparison</div>
            </div>
          </div>

          <h3>Game Results</h3>

                   <div style="border:1px solid #ddd;border-radius:8px;overflow:hidden;">
            ${resultRowsHtml}
          </div>

          <h3>Prediction Contest Snapshot</h3>

          <div style="background:#f1f3f4;padding:14px;border-radius:8px;">
            <p>
              <strong>Today's Champion:</strong>
              ${dailyChampion.name || '-'}
              (${dailyChampion.correct || 0} of ${dailyChampion.predictions || 0}, ${dailyChampion.accuracy || '0.0%'})
            </p>

            <p>
              <strong>League Accuracy Today:</strong>
              ${dailyLeague.accuracy || '0.0%'}
              (${dailyLeague.correct || 0} correct of ${dailyLeague.predictions || 0})
            </p>

            <hr>

            <p>
              <strong>Current Monthly Leader:</strong>
              ${monthlyLeader.name || '-'}
              (${monthlyLeader.correct || 0} of ${monthlyLeader.predictions || 0}, ${monthlyLeader.accuracy || '0.0%'})
            </p>

            <p>
              <strong>Monthly League Accuracy:</strong>
              ${monthlyLeague.accuracy || '0.0%'}
              (${monthlyLeague.correct || 0} correct of ${monthlyLeague.predictions || 0})
            </p>

            <hr>

            <p style="margin-bottom:0;">
              <strong>Year-to-Date League Accuracy:</strong>
              ${yearlyLeague.accuracy || '0.0%'}
              (${yearlyLeague.correct || 0} correct of ${yearlyLeague.predictions || 0})
            </p>
          </div>

          <p style="text-align:center;margin-top:22px;">
            <a href="${leaderboardUrl}"
               style="background:#1f4e79;color:white;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:bold;">
              View Prediction Leaderboard
            </a>
          </p>
        </div>
      </div>
    `;

    const plainBody =
      "JSSA Prediction Results\n\n" +
      player.name + ", your results are in.\n\n" +
      "Today: " + player.correct + " of " + player.total + "\n" +
      "Your Accuracy: " + formatPercent_(playerAccuracy) + "\n" +
      "League Accuracy: " + formatPercent_(leagueAccuracy) + "\n\n" +
      "View Leaderboard: " + leaderboardUrl;

    const sendTo = testMode ? "cosentinoteam@gmail.com" : player.email;

    const formattedDate = Utilities.formatDate(
      new Date(targetDateString),
      Session.getScriptTimeZone(),
      "EEEE, MMMM d, yyyy"
    );

    queueEmail_({
      to: sendTo,
      subject: "JSSA Prediction Results - " + formattedDate,
      body: plainBody,
      htmlBody: htmlBody
    });
  });
}

function formatPercent_(value) {
  return Utilities.formatString("%.1f%%", Number(value || 0) * 100);
}

function testPredictionEmailForJune12() {
  sendPredictionResultsEmails_(new Date(2026,5,12), true);
}

function updatePredictionMetrics() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const analyticsSheet = ss.getSheetByName("Prediction Analytics");
  const metricsSheet = ss.getSheetByName("Prediction Metrics");

  if (!analyticsSheet) throw new Error("Prediction Analytics sheet not found.");
  if (!metricsSheet) throw new Error("Prediction Metrics sheet not found.");

  const data = analyticsSheet.getDataRange().getValues();
  if (data.length < 2) return;

  const headers = data[0];

  const gameDateCol = headers.indexOf("Game Date");
  const fieldCol = headers.indexOf("Field");
  const homeCaptainCol = headers.indexOf("Home Captain");
  const visitorCaptainCol = headers.indexOf("Visitor Captain");
  const homePicksCol = headers.indexOf("Home Picks");
  const visitorPicksCol = headers.indexOf("Visitor Picks");
  const homePctCol = headers.indexOf("Home %");
  const visitorPctCol = headers.indexOf("Visitor %");
  const crowdCorrectCol = headers.indexOf("Crowd Correct?");
  const winningSideCol = headers.indexOf("Winning Side");
  const marginPctCol = headers.indexOf("Margin %");
  const totalPicksCol = headers.indexOf("Total Picks");

  const rows = data.slice(1).filter(row => row[gameDateCol]);

  let totalGames = 0;
  let totalPredictions = 0;
  let crowdCorrectGames = 0;
  let upsetGames = 0;
  let splitTotal = 0;

  let closestGame = null;
  let mostLopsidedGame = null;

  const captainStats = {};

  rows.forEach(row => {
    const gameDate = row[gameDateCol];
    const field = row[fieldCol];
    const homeCaptain = row[homeCaptainCol];
    const visitorCaptain = row[visitorCaptainCol];

    const homePicks = Number(row[homePicksCol]) || 0;
    const visitorPicks = Number(row[visitorPicksCol]) || 0;
    const homePct = Number(row[homePctCol]) || 0;
    const visitorPct = Number(row[visitorPctCol]) || 0;
    const marginPct = Number(row[marginPctCol]) || 0;
    const totalPicks = Number(row[totalPicksCol]) || 0;

    const crowdCorrect = String(row[crowdCorrectCol] || "").trim().toUpperCase();
    const winningSide = String(row[winningSideCol] || "").trim();

    if (!totalPicks) return;

    totalGames++;
    totalPredictions += totalPicks;
    splitTotal += Math.max(homePct, visitorPct);

    if (crowdCorrect === "YES") crowdCorrectGames++;
    if (crowdCorrect === "NO") upsetGames++;

    const gameLabel =
      Utilities.formatDate(new Date(gameDate), Session.getScriptTimeZone(), "M/d/yyyy") +
      " - " + field +
      " (" + homeCaptain + " vs " + visitorCaptain + ")";

    const splitText =
  homePicks + " picked Home • " +
  visitorPicks + " picked Visitor";

if (!closestGame || marginPct < closestGame.marginPct) {
  closestGame = {
    label: gameLabel,
    marginPct,
    splitText
  };
}

if (!mostLopsidedGame || marginPct > mostLopsidedGame.marginPct) {
  mostLopsidedGame = {
    label: gameLabel,
    marginPct,
    splitText
  };
}

    if (!captainStats[homeCaptain]) {
      captainStats[homeCaptain] = {
        captain: homeCaptain,
        games: 0,
        pickedFor: 0,
        wins: 0,
        underdogWins: 0
      };
    }

    if (!captainStats[visitorCaptain]) {
      captainStats[visitorCaptain] = {
        captain: visitorCaptain,
        games: 0,
        pickedFor: 0,
        wins: 0,
        underdogWins: 0
      };
    }

    captainStats[homeCaptain].games++;
    captainStats[visitorCaptain].games++;

    captainStats[homeCaptain].pickedFor += homePicks;
    captainStats[visitorCaptain].pickedFor += visitorPicks;

    if (winningSide === "Home") {
      captainStats[homeCaptain].wins++;
      if (homePicks < visitorPicks) captainStats[homeCaptain].underdogWins++;
    }

    if (winningSide === "Visitor") {
      captainStats[visitorCaptain].wins++;
      if (visitorPicks < homePicks) captainStats[visitorCaptain].underdogWins++;
    }
  });

  const leagueAccuracy = totalGames ? crowdCorrectGames / totalGames : 0;
  const averageSplit = totalGames ? splitTotal / totalGames : 0;
  const upsetRate = totalGames ? upsetGames / totalGames : 0;

  const captains = Object.values(captainStats);

  captains.forEach(c => {
    c.trustRate = totalPredictions ? c.pickedFor / totalPredictions : 0;
    c.winRate = c.games ? c.wins / c.games : 0;
  });

  const mostTrusted = captains
    .slice()
    .sort((a, b) => b.pickedFor - a.pickedFor)[0];

  const mostUnderrated = captains
    .slice()
    .sort((a, b) => b.underdogWins - a.underdogWins || b.winRate - a.winRate)[0];

  const output = [
    ["Metric", "Value", "Notes"],
    ["Total Games Scored", totalGames, "Games included in Prediction Analytics."],
    ["Total Predictions", totalPredictions, "Total member picks across scored games."],
    ["League Prediction Accuracy %", leagueAccuracy, "Percent of games where the crowd majority picked the winner."],
    ["Average Prediction Split", averageSplit, "Average majority confidence. Lower is better for balance."],
    ["Upset Rate %", upsetRate, "Percent of games where the crowd majority was wrong."],
   ["Closest Predicted Game", closestGame ? closestGame.label : "", closestGame ? closestGame.splitText : ""],
["Most Lopsided Predicted Game", mostLopsidedGame ? mostLopsidedGame.label : "", mostLopsidedGame ? mostLopsidedGame.splitText : ""],
    ["Most Trusted Captain", mostTrusted ? mostTrusted.captain : "", mostTrusted ? mostTrusted.pickedFor + " total picks for that captain's teams." : ""],
    ["Most Underrated Captain", mostUnderrated ? mostUnderrated.captain : "", mostUnderrated ? mostUnderrated.underdogWins + " underdog win(s)." : ""]
  ];

  const maxRowsToClear = Math.max(metricsSheet.getLastRow(), output.length);

if (maxRowsToClear > 0) {
  metricsSheet
    .getRange(1, 1, maxRowsToClear, 3)
    .clearContent();
}

metricsSheet
  .getRange(1, 1, output.length, output[0].length)
  .setValues(output);

  SpreadsheetApp.getActiveSpreadsheet().toast("Prediction Metrics updated.");
}

function getPredictionDashboardForWebsite() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const picksSheet = ss.getSheetByName("Prediction Picks");
  const metricsSheet = ss.getSheetByName("Prediction Metrics");

  if (!picksSheet) throw new Error("Prediction Picks sheet not found.");
  if (!metricsSheet) throw new Error("Prediction Metrics sheet not found.");

  const leaderboard = getPredictionLeaderboardForWebsite();

  // Minimum monthly picks needed to be "qualified" (Prediction Control tab).
  const minimumPredictions =
    Number(getPredictionControlValue_('Minimum Monthly Predictions')) || 4;

  const metricsValues = metricsSheet.getDataRange().getDisplayValues();
  const metrics = {};

  for (let r = 1; r < metricsValues.length; r++) {
    const metric = String(metricsValues[r][0] || "").trim();
    if (!metric) continue;

    metrics[metric] = {
      value: String(metricsValues[r][1] || "").trim(),
      notes: String(metricsValues[r][2] || "").trim()
    };
  }

  const picksData = picksSheet.getDataRange().getValues();
  const picksHeaders = picksData[0];

  const emailCol = picksHeaders.indexOf("Email");
  const nameCol = picksHeaders.indexOf("Name");
  const gameDateCol = picksHeaders.indexOf("Game Date");
  const correctCol = picksHeaders.indexOf("Correct");
  const scoredCol = picksHeaders.indexOf("Scored");
  const monthCol = picksHeaders.indexOf("Prediction Month");

  let latestDateKey = "";
  let latestMonthKey = "";
  let latestYearKey = "";

  for (let r = 1; r < picksData.length; r++) {
    const scored =
      picksData[r][scoredCol] === true ||
      String(picksData[r][scoredCol]).trim().toUpperCase() === "TRUE";

    if (!scored) continue;

    const dateKey = normalizePredictionDateKey_(picksData[r][gameDateCol]);
    if (!dateKey) continue;

    if (dateKey > latestDateKey) latestDateKey = dateKey;
  }

  latestMonthKey = latestDateKey ? latestDateKey.slice(0, 7) : "";
  latestYearKey = latestDateKey ? latestDateKey.slice(0, 4) : "";

  const dailyTotals = {};
  let dailyCorrect = 0;
  let dailyPredictions = 0;

  // Per-player totals for the current (latest) month, so the "Current Monthly
  // Leader" reflects THIS month only — not the all-time leaderboard.
  const monthlyTotals = {};
  let monthlyCorrect = 0;
  let monthlyPredictions = 0;

  let yearlyCorrect = 0;
  let yearlyPredictions = 0;

  for (let r = 1; r < picksData.length; r++) {
    const scored =
      picksData[r][scoredCol] === true ||
      String(picksData[r][scoredCol]).trim().toUpperCase() === "TRUE";

    if (!scored) continue;

    const dateKey = normalizePredictionDateKey_(picksData[r][gameDateCol]);
    if (!dateKey) continue;

   const monthKey = dateKey.slice(0, 7);

    const yearKey = dateKey.slice(0, 4);

    const correct = picksData[r][correctCol] === true;

    if (dateKey === latestDateKey) {
      const email = String(picksData[r][emailCol] || "").trim().toLowerCase();
      const name = String(picksData[r][nameCol] || "").trim();

      if (email) {
        if (!dailyTotals[email]) {
          dailyTotals[email] = {
            name: name || email,
            predictions: 0,
            correct: 0
          };
        }

        dailyTotals[email].predictions++;

        if (correct) {
          dailyTotals[email].correct++;
        }
      }

      dailyPredictions++;
      if (correct) dailyCorrect++;
    }

    if (monthKey === latestMonthKey) {
      const email = String(picksData[r][emailCol] || "").trim().toLowerCase();
      const name = String(picksData[r][nameCol] || "").trim();

      if (email) {
        if (!monthlyTotals[email]) {
          monthlyTotals[email] = {
            name: name || email,
            predictions: 0,
            correct: 0
          };
        }

        monthlyTotals[email].predictions++;

        if (correct) {
          monthlyTotals[email].correct++;
        }
      }

      monthlyPredictions++;
      if (correct) monthlyCorrect++;
    }

    if (yearKey === latestYearKey) {
      yearlyPredictions++;
      if (correct) yearlyCorrect++;
    }
  }

  const dailyPlayers = Object.values(dailyTotals).sort((a, b) => {
    const aAcc = a.predictions ? a.correct / a.predictions : 0;
    const bAcc = b.predictions ? b.correct / b.predictions : 0;

    if (bAcc !== aAcc) return bAcc - aAcc;
    if (b.correct !== a.correct) return b.correct - a.correct;
    return a.name.localeCompare(b.name);
  });

  const dailyChampion = dailyPlayers.length ? {
    name: dailyPlayers[0].name,
    predictions: dailyPlayers[0].predictions,
    correct: dailyPlayers[0].correct,
    accuracy: formatPercent_(dailyPlayers[0].correct / dailyPlayers[0].predictions)
  } : null;

  const dailyLeague = {
    dateKey: latestDateKey,
    predictions: dailyPredictions,
    correct: dailyCorrect,
    accuracy: dailyPredictions ? formatPercent_(dailyCorrect / dailyPredictions) : "0.0%"
  };

  const monthlyLeague = {
    monthKey: latestMonthKey,
    predictions: monthlyPredictions,
    correct: monthlyCorrect,
    accuracy: monthlyPredictions ? formatPercent_(monthlyCorrect / monthlyPredictions) : "0.0%"
  };

  const yearlyLeague = {
    yearKey: latestYearKey,
    predictions: yearlyPredictions,
    correct: yearlyCorrect,
    accuracy: yearlyPredictions ? formatPercent_(yearlyCorrect / yearlyPredictions) : "0.0%"
  };

  // Current Monthly Leader — the best player in the CURRENT month only.
  // Prefer players who have met the monthly minimum ("qualified"); if nobody has
  // yet (e.g. the first game day of a new month), fall back to the current
  // front-runner so the card still shows this month's leader instead of last
  // month's. Ties: higher accuracy, then more correct, then name.
  let monthlyLeader = null;

  const monthlyPlayers = Object.values(monthlyTotals).sort((a, b) => {
    const aAcc = a.predictions ? a.correct / a.predictions : 0;
    const bAcc = b.predictions ? b.correct / b.predictions : 0;

    if (bAcc !== aAcc) return bAcc - aAcc;
    if (b.correct !== a.correct) return b.correct - a.correct;
    return a.name.localeCompare(b.name);
  });

  const qualifiedMonthly = monthlyPlayers.filter(
    p => p.predictions >= minimumPredictions
  );

  const topMonthly = qualifiedMonthly.length
    ? qualifiedMonthly[0]
    : (monthlyPlayers.length ? monthlyPlayers[0] : null);

  if (topMonthly) {
    monthlyLeader = {
      name: topMonthly.name,
      predictions: topMonthly.predictions,
      correct: topMonthly.correct,
      accuracy: formatPercent_(topMonthly.correct / topMonthly.predictions),
      qualified: topMonthly.predictions >= minimumPredictions ? "YES" : "NO"
    };
  }

  return {
    dailyChampion: dailyChampion,
    dailyLeague: dailyLeague,
    monthlyLeader: monthlyLeader,
    monthlyLeague: monthlyLeague,
    yearlyLeague: yearlyLeague,
    metrics: metrics,
    leaderboard: leaderboard
  };
}

function testPredictionDashboardForWebsite() {
  const data = getPredictionDashboardForWebsite();
  Logger.log(JSON.stringify(data, null, 2));
}

function finalizePredictionResultsForLatestScoredDate() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const gamesSheet = ss.getSheetByName("Prediction Games");

  const data = gamesSheet.getDataRange().getValues();
  const headers = data[0];

  const gameDateCol = headers.indexOf("Game Date");
  const winnerCol = headers.indexOf("Winner");
  const scoredCol = headers.indexOf("Scored");

  let latestDate = null;

  for (let r = 1; r < data.length; r++) {
    const gameDate = data[r][gameDateCol];
    const winner = String(data[r][winnerCol] || "").trim().toUpperCase();
    const scored =
      data[r][scoredCol] === true ||
      String(data[r][scoredCol]).trim().toUpperCase() === "TRUE";

    if (!gameDate || !scored || (winner !== "H" && winner !== "V")) continue;

    const dateObj = new Date(gameDate);
    if (!latestDate || dateObj > latestDate) {
      latestDate = dateObj;
    }
  }

  if (!latestDate) {
    throw new Error("No scored prediction game date found.");
  }

  scorePredictions();
  updatePredictionAnalytics();
  updatePredictionLeaderboard();
  updatePredictionChampions();
  updatePredictionMetrics();

  SpreadsheetApp.flush();

  sendPredictionResultsEmailsOnce_(latestDate);

  SpreadsheetApp.getActiveSpreadsheet().toast(
    "Prediction results finalized and emails sent."
  );
}

function sendPredictionResultsEmailsOnce_(gameDate) {
  const dateKey = normalizePredictionDateKey_(gameDate);
  const propertyKey = "prediction_results_email_sent_" + dateKey;
  const props = PropertiesService.getScriptProperties();

  if (props.getProperty(propertyKey) === "TRUE") {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      "Emails were already sent for " + dateKey
    );
    return;
  }

  sendPredictionResultsEmails_(gameDate, false);
  props.setProperty(propertyKey, "TRUE");
}

function testDashboard() {
  const result = getPredictionDashboardForWebsite();
  Logger.log(JSON.stringify(result, null, 2));
}

function testPredictionEmailForJune15() {
  sendPredictionResultsEmails_(new Date(2026, 5, 15), true);
}

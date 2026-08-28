// Reproduce today's real numbers against the old and new counter logic.
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', '..', 'apps-script', 'email-usage.gs'), 'utf8');

// Today on jssagames@: 6 messages in Sent. Four of them are ours and carry
// their recipients in BCC, which getBcc() hides for script-sent mail.
const sent = [
  { to: 'cosentinoteam@gmail.com', cc: '', bcc: '' },                    // 10:41 test (old script)
  { to: 'jssagames@gmail.com',     cc: '', bcc: '' },                    // 10:52 test  (bcc hidden)
  { to: 'jssagames@gmail.com',     cc: '', bcc: '' },                    // 11:03 batch 1 (45 hidden)
  { to: 'jssagames@gmail.com',     cc: '', bcc: '' },                    // 11:03 batch 2 (10 hidden)
  { to: 'a@x.com,b@x.com,c@x.com,d@x.com,e@x.com', cc: '', bcc: '' },    // registration mail
  { to: 'f@x.com,g@x.com,h@x.com,i@x.com,j@x.com', cc: '', bcc: '' },
];
const REAL_REMAINING = 17;   // what Gmail actually reports

const now = new Date();
const env = {
  Session: { getScriptTimeZone: () => 'America/New_York',
             getEffectiveUser: () => ({ getEmail: () => 'jssagames@gmail.com' }) },
  MailApp: { getRemainingDailyQuota: () => REAL_REMAINING, sendEmail: () => {} },
  GmailApp: { search: () => sent.map(m => ({ getMessages: () => [{
      getDate: () => now, getFrom: () => 'jssagames@gmail.com',
      getTo: () => m.to, getCc: () => m.cc, getBcc: () => m.bcc }] })) },
  Utilities: { formatDate: () => 'Aug 28, 11:12 AM', sleep: () => {} },
  Logger: { log: () => {} },
  ContentService: { MimeType: { JSON: 'json' },
    createTextOutput: t => ({ setMimeType: () => ({ body: t }) }) },
  SpreadsheetApp: {}, PropertiesService: {}, ScriptApp: {},
};
const api = new Function('Session','MailApp','GmailApp','Utilities','Logger',
  'ContentService','SpreadsheetApp','PropertiesService','ScriptApp',
  src + '\nreturn {_usage:_usage};')(env.Session, env.MailApp, env.GmailApp,
  env.Utilities, env.Logger, env.ContentService, env.SpreadsheetApp,
  env.PropertiesService, env.ScriptApp);

const u = api._usage();
console.log('What the page will now show for jssagames@:');
console.log('  Emails sent today :', u.messages_today);
console.log('  People reached    :', u.recipients_today);
console.log('  Sends left today  :', u.remaining_today, 'of', u.daily_limit);
console.log('  (visible in Sent  :', u.recipients_visible, '- hidden BCC detected:', u.hidden_bcc + ')');

const oldRemaining = 100 - u.recipients_visible;
console.log('\nThe old logic would have said: ' + oldRemaining + ' sends left');
console.log('Gmail actually says          : ' + REAL_REMAINING);
console.log('Overstated by                : ' + (oldRemaining - REAL_REMAINING));

if (u.remaining_today !== REAL_REMAINING) throw new Error('FAIL: not using Gmail\'s figure');
if (u.recipients_today !== 100 - REAL_REMAINING) throw new Error('FAIL: people reached wrong');
if (!u.hidden_bcc) throw new Error('FAIL: hidden BCC not detected');
console.log('\nCOUNTER CHECKS PASSED');

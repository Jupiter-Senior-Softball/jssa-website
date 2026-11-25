const fs = require('fs');
const src = fs.readFileSync(require('path').join(__dirname, '..', '..', 'apps-script', 'game-cancellation-sender.gs'), 'utf8');

function makeEnv(opts) {
  const sends = [];
  const env = {
    sends,
    Session: { getEffectiveUser: () => ({ getEmail: () => 'jssagames@gmail.com' }) },
    Utilities: { sleep: () => {} },
    Logger: { log: () => {} },
    MailApp: {
      getRemainingDailyQuota: () => opts.quota,
      sendEmail: (m) => {
        const n = (m.bcc ? m.bcc.split(',').length : 0) + (m.to ? 1 : 0) + (m.cc ? m.cc.split(',').length : 0);
        if (opts.failBatch !== undefined && sends.length === opts.failBatch) {
          throw new Error('Exception: Limit Exceeded: Email Recipients Per Message.');
        }
        if (n > 50) throw new Error('Exception: Limit Exceeded: Email Recipients Per Message.');
        sends.push({ recipients: n, bcc: m.bcc ? m.bcc.split(',') : [], subject: m.subject,
                     to: m.to, cc: m.cc, body: m.body });
      },
    },
    ContentService: {
      MimeType: { JSON: 'json' },
      createTextOutput: (t) => ({ setMimeType: () => ({ body: t }) }),
    },
  };
  return env;
}

function load(env) {
  const fn = new Function('Session','Utilities','Logger','MailApp','ContentService',
    src + '\nreturn {doPost:doPost, doGet:doGet, SECRET:SECRET};');
  return fn(env.Session, env.Utilities, env.Logger, env.MailApp, env.ContentService);
}

function call(env, api, body) {
  const r = api.doPost({ parameter: { key: 'PUT_A_LONG_RANDOM_PHRASE_HERE' },
                         postData: { contents: JSON.stringify(body) } });
  return JSON.parse(r.body);
}

const players = n => Array.from({length: n}, (_, i) => `p${i}@e.com`);

// ---- 55 players, plenty of quota -----------------------------------------
let env = makeEnv({ quota: 200 }), api = load(env);
let out = call(env, api, { subject: 'CANCELLED', body: 'no games', recipients: players(55) });
console.log('55 players, quota 200');
console.log('  ok:', out.ok, '| sent:', out.sent, '| batches:', out.batches);
console.log('  messages:', env.sends.map(s => s.recipients).join(' + '),
            '=', env.sends.reduce((a,s)=>a+s.recipients,0), 'recipients');
if (!(out.ok && out.sent === 55 && env.sends.length === 2)) throw new Error('FAIL 55');
if (env.sends.some(s => s.recipients > 50)) throw new Error('FAIL: a message exceeded 50');

// ---- the old failing case: exactly the size that broke live ---------------
console.log('\nevery message stays under Gmail\'s 50 limit: YES');

// ---- a large roster -------------------------------------------------------
env = makeEnv({ quota: 400 }); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(130) });
console.log('\n130 players:', 'sent', out.sent, 'in', env.sends.length, 'messages of',
            env.sends.map(s=>s.recipients).join('/'));
if (out.sent !== 130 || env.sends.some(s => s.recipients > 50)) throw new Error('FAIL 130');

// ---- one batch fails: the rest must still go ------------------------------
env = makeEnv({ quota: 200, failBatch: 1 }); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(55) });
console.log('\nsecond message fails:');
console.log('  ok:', out.ok, '| sent:', out.sent, '| missed:', out.missed.length);
console.log('  error:', out.error.slice(0, 60));
if (out.ok !== false || out.sent !== 45 || out.missed.length !== 10) throw new Error('FAIL partial');
console.log('  -> 45 people still heard, and the 10 who did not are named back');

// ---- not enough quota -----------------------------------------------------
env = makeEnv({ quota: 20 }); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(55) });
console.log('\nquota only 20:', out.ok, '|', out.error.slice(0, 70));
if (out.ok !== false || out.sent !== 0) throw new Error('FAIL quota');

// ---- rehearsal ------------------------------------------------------------
env = makeEnv({ quota: 200 }); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(55), test_to: 'tom@e.com' });
console.log('\nrehearsal: sent', out.sent, '| would_send', out.would_send,
            '| batches', out.batches, '| test email went to', env.sends[0].bcc.join(','));
if (out.sent !== 0 || out.would_send !== 55 || env.sends.length !== 1) throw new Error('FAIL rehearsal');
if (!env.sends[0].bcc.includes('tom@e.com')) throw new Error('FAIL rehearsal recipient');
console.log('  -> no player emailed, and it used the same BCC route');


// ---- the always-CC address ------------------------------------------------
// This account is jssagames@gmail.com (see makeEnv). Copying it to itself would
// be pointless, so the CC is skipped there; any other account adds it.
function asAccount(env, email) { env.Session = { getEffectiveUser: () => ({ getEmail: () => email }) }; return env; }

env = asAccount(makeEnv({ quota: 200 }), 'jssaadmin@gmail.com'); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(55), cc: 'jssagames@gmail.com' });
console.log('\nbackup account, 55 players, cc jssagames@:');
console.log('  messages:', env.sends.map(s => s.recipients + ' (cc ' + s.cc + ')').join(' + '));
if (!(out.ok && out.sent === 55 && env.sends.length === 2)) throw new Error('FAIL cc backup send');
if (env.sends.some(s => s.cc !== 'jssagames@gmail.com')) throw new Error('FAIL: every message must carry the CC');
if (env.sends.some(s => s.recipients > 50)) throw new Error('FAIL: a message exceeded 50 with the CC');
if (env.sends.some(s => s.bcc.includes('jssagames@gmail.com'))) throw new Error('FAIL: the CC must not be a BCC');

env = makeEnv({ quota: 200 }); api = load(env);                 // the main account itself
out = call(env, api, { subject: 's', body: 'b', recipients: players(55), cc: 'jssagames@gmail.com' });
console.log('main account, cc is itself  :', env.sends.map(s => 'cc=' + s.cc).join(' '));
if (!out.ok || env.sends.some(s => s.cc !== undefined)) throw new Error('FAIL: no CC to itself');
if (env.sends.some(s => s.to !== 'jssagames@gmail.com')) throw new Error('FAIL: To must still be this account');

env = makeEnv({ quota: 200 }); api = load(env);                 // no cc given: exactly as before
out = call(env, api, { subject: 's', body: 'b', recipients: players(55) });
if (!out.ok || env.sends.some(s => s.cc !== undefined)) throw new Error('FAIL: no cc requested, none sent');
console.log('no cc requested             : none sent');

for (const bad of ['a@e.com, b@e.com', 'not an address', 'x@y']) {
  env = asAccount(makeEnv({ quota: 200 }), 'jssaadmin@gmail.com'); api = load(env);
  out = call(env, api, { subject: 's', body: 'b', recipients: players(5), cc: bad });
  if (!out.ok || env.sends.some(s => s.cc !== undefined)) throw new Error('FAIL: bad cc must be ignored: ' + bad);
}
console.log('bad cc values               : ignored, the message still goes out');

// The CC costs one more send per message on the backup account.
env = asAccount(makeEnv({ quota: 58 }), 'jssaadmin@gmail.com'); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(55), cc: 'jssagames@gmail.com' });
console.log('\nbackup, quota 58, 55 players + 2 copies + 2 CCs = 59:', out.ok, '|', (out.error || '').slice(0, 60));
if (out.ok !== false || out.sent !== 0 || env.sends.length !== 0) throw new Error('FAIL: CC must count against the limit');
env = asAccount(makeEnv({ quota: 59 }), 'jssaadmin@gmail.com'); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(55), cc: 'jssagames@gmail.com' });
if (!out.ok || out.sent !== 55) throw new Error('FAIL: exactly enough quota should send');
env = makeEnv({ quota: 57 }); api = load(env);                  // main account: 55 + 2 copies, no CC cost
out = call(env, api, { subject: 's', body: 'b', recipients: players(55), cc: 'jssagames@gmail.com' });
if (!out.ok) throw new Error('FAIL: the main account pays nothing for copying itself');
console.log('  -> counted against the limit on the backup, free on the main account');

// A practice run never CCs anyone, but says it would.
env = asAccount(makeEnv({ quota: 200 }), 'jssaadmin@gmail.com'); api = load(env);
out = call(env, api, { subject: 's', body: 'b', recipients: players(55), cc: 'jssagames@gmail.com', test_to: 'tom@e.com' });
if (out.sent !== 0 || env.sends.length !== 1 || env.sends[0].cc !== undefined) throw new Error('FAIL: practice must not CC');
if (!/would also CC jssagames@gmail.com/.test(env.sends[0].body)) throw new Error('FAIL: practice should mention the CC');
console.log('practice run                : no CC sent, the test email says it would');

console.log('\nSENDER SCRIPT CHECKS PASSED');

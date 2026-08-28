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
        const n = (m.bcc ? m.bcc.split(',').length : 0) + (m.to ? 1 : 0);
        if (opts.failBatch !== undefined && sends.length === opts.failBatch) {
          throw new Error('Exception: Limit Exceeded: Email Recipients Per Message.');
        }
        if (n > 50) throw new Error('Exception: Limit Exceeded: Email Recipients Per Message.');
        sends.push({ recipients: n, bcc: m.bcc ? m.bcc.split(',') : [], subject: m.subject });
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

console.log('\nSENDER SCRIPT CHECKS PASSED');

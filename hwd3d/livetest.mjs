// Test harness for the Hayward Live 3D app (hwd3d Phase 2, P4). Forked from sfo3d/livetest.mjs @ a967f9b. Kept: one
// static server for the app, a relay behind /api/*, headless Chromium, `node livetest.mjs <job.mjs>` where the job exports
// default async ({page, shot, base, W, H, OUT, ...}), the env switches W / H / DPR / MOBILE / SWS / RELAY / PREFIX.
// Changed (fork map 2.10):
//  - the relay is P1's hwd_live_server.py in REPLAY mode, spawned on a free port in 8700-8799 (RELAY unset or 'spawn'):
//    --replay rec_pack --from $REPLAY_FROM (default 2026-11-08T20:00Z, P1's weekend window) --until +1 h --loop
//    --no-adsbfi --quiet; /api/* of the static server is proxied to it (SSE included). RELAY=http://host:port proxies to
//    a relay that is already running; RELAY=mock serves a small mock from P1's pack (out/replay/pack.json.gz): /api/ping
//    {hwdlive: 1, mock: true, mode: 'replay'}, /api/adsb and /api/stream (full payloads at real speed from the window start
//    + lookahead_s, history first) and /api/metar (the pack's KHWD reports up to the replay time); RELAY=none: no /api
//    (the app then falls back to the pack through P1's shim);
//  - SwiftShader is the default GPU (this machine has none; SWS=0 lets Chromium choose); MOBILE=1 = 390 x 844 phone
//    viewport with touch and an iPhone UA (deviceScaleFactor from DPR, default 1 for the checks);
//  - console errors / warnings and page errors are collected (job receives `errors`) and written to
//    OUT/app_console_<PREFIX>.json; screenshots go to OUT/app_<name>.png (OUT default out/phase2, gitignored);
//  - the static server serves hwd3d/ only, never refs/cache/local/ (per-aircraft identities, D1).
// Dropped: data/snapshot.js (not forked) and the SFO routeset mock.
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import net from 'node:net'; import zlib from 'node:zlib';
import { spawn } from 'node:child_process'; import { fileURLToPath } from 'node:url'; import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); }
catch (e) { console.error('Playwright not found: npm i -D playwright (or set PLAYWRIGHT_MODULE)'); process.exit(1); }

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.ROOT || HERE;
const OUT = process.env.OUT || path.join(HERE, 'out', 'phase2');
fs.mkdirSync(OUT, { recursive: true });
const PREFIX = process.env.PREFIX || 'run';
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.gz': 'application/gzip', '.svg': 'image/svg+xml' };
const log = (...a) => console.log('[livetest]', ...a);

async function freePort(lo = 8700, hi = 8799, skip = new Set()) {
  for (let p = lo; p <= hi; p++) {
    if (skip.has(p)) continue;
    const ok = await new Promise(r => { const s = net.createServer(); s.once('error', () => r(false)); s.listen(p, '127.0.0.1', () => s.close(() => r(true))); });
    if (ok) return p;
  }
  throw new Error('no free port in ' + lo + '-' + hi);
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// ---------------------------------------------------------------- relay
let relayProc = null, relayURL = null, mock = null;
const RELAY = process.env.RELAY || 'spawn';
const used = new Set();
if (RELAY === 'spawn') {
  const port = await freePort(+(process.env.RELAY_PORT_LO || 8760), 8799); used.add(port);
  const from = process.env.REPLAY_FROM || '2026-11-08T20:00Z';
  const until = process.env.REPLAY_UNTIL || new Date(Date.parse(from.replace(/Z?$/, 'Z')) + 3600e3).toISOString().slice(0, 16) + 'Z';
  const args = ['hwd_live_server.py', '--port', String(port), '--replay', process.env.REPLAY_SRC || 'rec_pack', '--from', from, '--until', until, '--loop', '--no-adsbfi', '--quiet', ...(process.env.RELAY_ARGS ? process.env.RELAY_ARGS.split(' ') : [])];
  log('spawn relay: python3', args.join(' '));
  relayProc = spawn('python3', args, { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  let rlog = ''; relayProc.stdout.on('data', d => { rlog += d; }); relayProc.stderr.on('data', d => { rlog += d; });
  relayProc.on('exit', (c) => { if (c) log('relay exited', c, rlog.slice(-1500)); });
  relayURL = new URL(`http://127.0.0.1:${port}`);
  let ok = false;
  for (let i = 0; i < 120 && !ok; i++) { await sleep(500); try { const j = await (await fetch(relayURL + 'api/ping')).json(); ok = j.hwdlive === 1; if (ok) log('relay up:', JSON.stringify({ mode: j.mode, replay: j.features && j.features.replay, ident: j.features && j.features.ident, d1_mode: j.features && j.features.d1_mode })); } catch (e) { } }
  if (!ok) { log('relay did not answer', rlog.slice(-2000)); process.exit(1); }
} else if (/^https?:/.test(RELAY)) relayURL = new URL(RELAY);
else if (RELAY === 'mock') {
  const buf = fs.readFileSync(path.join(ROOT, process.env.PACK || 'out/replay/pack.json.gz'));
  const pack = JSON.parse((buf[0] === 0x1f ? zlib.gunzipSync(buf) : buf).toString('utf8'));
  const L = pack.lookahead_s || 60, st = {}, frames = pack.events.map(e => { const ac = e.p.d.map(r => { const a = st[r[0]] || (st[r[0]] = { hex: r[0] }); Object.assign(a, r[1]); if (r[2]) for (const k of r[2]) delete a[k]; return { ...a }; }); return { T: e.T, p: { now: e.p.now, dataNow: e.p.dataNow, seq: e.p.seq, _source: e.p._source, msg: 'No error', ac } }; });
  const off = Date.now() / 1000 - (pack.from + L);   // the mock clock starts lookahead_s into the window (as P1's shim)
  const shift = (f) => ({ ...f.p, now: Math.round((f.T + off) * 1000), ac: f.p.ac.map(a => typeof a._pt === 'number' ? { ...a, _pt: a._pt + off } : a) });
  const at = () => Date.now() / 1000 - off;
  const latest = () => { let k = -1; const t = at(); for (let i = 0; i < frames.length && frames[i].T <= t; i++) k = i; return k; };
  mock = { pack, frames, shift, at, latest, L };
  log('mock relay from the pack:', pack.name || '', frames.length, 'payloads');
}

// ---------------------------------------------------------------- static server (+ /api proxy or mock)
function proxy(req, res) {
  const p = http.request({ host: relayURL.hostname, port: relayURL.port, path: req.url, method: req.method, headers: { ...req.headers, host: relayURL.host } },
    (r) => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
  p.on('error', (e) => { res.statusCode = 502; res.end(String(e)); });
  req.pipe(p); res.on('close', () => p.destroy());
}
function mockApi(url, req, res) {
  const M = mock, J = (o, c = 200) => { res.writeHead(c, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(o)); };
  if (url.pathname === '/api/ping') return J({ hwdlive: 1, mock: true, v: 'mock', mode: 'replay', stream: true, delta: false, dataNow: Math.round(M.at() * 1000), features: { metar: 'KHWD', taf: null, ident: null, d1: 'dbFlags & 12', d1_mode: M.pack.d1 && M.pack.d1.ident, replay: { src: 'mock:' + (M.pack.name || 'pack'), from: M.pack.from * 1000, until: M.pack.until * 1000, speed: 1, loop: false, lookahead_s: M.L } }, providers: ['adsb.lol'] });
  if (url.pathname === '/api/adsb') { const k = M.latest(); return J(k >= 0 ? M.shift(M.frames[k]) : { ac: [], now: Date.now(), msg: 'waiting' }); }
  if (url.pathname === '/api/metar') { const t = M.at(); const L = (M.pack.metar || []).filter(m => m.obsTime <= t && m.obsTime >= t - 3 * 3600).sort((a, b) => b.obsTime - a.obsTime); if (!L.length) return J({ error: 'no report' }, 502); return url.searchParams.get('format') === 'json' ? J(L) : (res.writeHead(200, { 'Content-Type': 'text/plain' }), res.end(L.map(m => m.rawOb).join('\n'))); }
  if (url.pathname === '/api/stream') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-store', Connection: 'keep-alive' }); res.write('retry: 2000\n\n');
    const hist = Math.min(120, +(url.searchParams.get('history') || 0)); let k = M.latest(), i = k;
    if (hist > 0) { const t = M.at() - hist; i = M.frames.findIndex(f => f.T >= t) - 1; if (i < -1) i = k; }
    const send = () => { const kk = M.latest(); while (i < kk) { i++; res.write('event: adsb\ndata: ' + JSON.stringify(M.shift(M.frames[i])) + '\n\n'); } };
    send(); const iv = setInterval(send, 500); req.on('close', () => clearInterval(iv)); return;
  }
  return J({ error: 'not in the mock' }, 404);
}
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname.startsWith('/api/')) { if (relayURL) return proxy(req, res); if (mock) return mockApi(url, req, res); res.statusCode = 404; return res.end(); }
  const rel = url.pathname === '/' ? 'live.html' : decodeURIComponent(url.pathname).replace(/^\/+/, '');
  const f = path.resolve(ROOT, rel);
  if (!f.startsWith(ROOT + path.sep) || /(^|[\/\\])refs[\/\\]cache[\/\\]local([\/\\]|$)/.test(path.relative(ROOT, f)) || /(^|[\/\\])\./.test(path.relative(ROOT, f))) { res.statusCode = 403; return res.end(); }
  fs.readFile(f, (e, d) => { if (e) { res.statusCode = 404; return res.end(); } res.setHeader('Content-Type', TYPES[path.extname(f)] || 'application/octet-stream'); res.setHeader('Cache-Control', 'no-store'); res.end(d); });
});
const PORT = +(process.env.PORT || await freePort(8740, 8799, used));
await new Promise(r => server.listen(PORT, '127.0.0.1', r));
const base = `http://127.0.0.1:${PORT}/`;
log('static server', base, 'relay', relayURL ? relayURL.href : mock ? 'mock' : 'none');

// ---------------------------------------------------------------- browser
const SWS = process.env.SWS !== '0';
const gpuArgs = SWS ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : [];
const browser = await chromium.launch({ args: [...gpuArgs, '--ignore-gpu-blocklist', '--js-flags=--max-old-space-size=3000', '--disable-gpu-watchdog', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'] });
const MOBILE = !!process.env.MOBILE && process.env.MOBILE !== '0';
const W = +(process.env.W || (MOBILE ? 390 : 1280)), H = +(process.env.H || (MOBILE ? 844 : 720));
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1), isMobile: MOBILE, hasTouch: MOBILE,
  userAgent: MOBILE ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' : undefined });
const page = await ctx.newPage();
page.setDefaultTimeout(0);
const errors = [];
page.on('console', m => { const t = m.text(); const ty = m.type(); if (/GPU stall|GL Driver|Automatic fallback|swiftshader/i.test(t)) return; if (ty === 'error' || ty === 'warning') errors.push({ type: ty, text: t.slice(0, 500) }); if (process.env.VERBOSE || ty === 'error' || ty === 'warning' || /^(world|snapshot|note|NAIP)/.test(t)) console.log('[page ' + ty + ']', t.slice(0, 400)); });
page.on('pageerror', e => { errors.push({ type: 'pageerror', text: String(e.message).slice(0, 500) }); console.log('[pageerror]', e.message, e.stack && e.stack.split('\n').slice(0, 4).join(' | ')); });
page.on('requestfailed', r => { const u = r.url(); if (!/\/api\/stream/.test(u)) errors.push({ type: 'requestfailed', text: u.replace(base, '/') + ' ' + (r.failure() && r.failure().errorText) }); });
const DEV = MOBILE ? 'phone' : 'desktop';
const shot = async (name, opts = {}) => {
  const f = path.join(OUT, 'app_' + name + '.png');
  // fast path: the renderer's own framebuffer (HWD.qa.shot -> PNG data URL), which avoids recompositing the SwiftShader
  // scene; falls back to page.screenshot (e.g. to capture the DOM HUD). FULLPAGE=1 or opts.dom forces page.screenshot.
  if (!opts.dom && !process.env.FULLPAGE) {
    const url = await page.evaluate(() => (window.HWD && HWD.qa.shot) ? HWD.qa.shot() : null).catch(() => null);
    if (url) { fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64')); log('shot', path.relative(HERE, f)); return f; }
  }
  await page.screenshot({ path: f, ...opts }); log('shot', path.relative(HERE, f)); return f;
};
const script = await import(path.resolve(process.argv[2]));
const t0 = Date.now();
try { await script.default({ page, shot, base, W, H, OUT, DEV, MOBILE, errors, log, relayURL }); } catch (e) { log('JOB FAILED', e && e.stack || e); process.exitCode = 1; }
fs.writeFileSync(path.join(OUT, `app_console_${PREFIX}_${DEV}.json`), JSON.stringify({ job: path.basename(process.argv[2]), dev: DEV, W, H, errors }, null, 1));
log(`console errors/warnings: ${errors.length}` + (errors.length ? ' -> ' + errors.slice(0, 6).map(e => e.type + ': ' + e.text.slice(0, 120)).join(' || ') : ''));
log('done in', ((Date.now() - t0) / 1000).toFixed(1), 's');
await browser.close(); server.close(); if (relayProc) relayProc.kill('SIGTERM');
process.exit();

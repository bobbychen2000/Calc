// forked from sfo3d@e3218d6 livetest.mjs
// Test harness for SHA Live 3D: static server, optional mock relay, headless Chromium, screenshots.
// Usage (from sha3d/ or anywhere):  [SOFTGL=1] node livetest.mjs jobs/views.mjs
//   the script exports default async ({page, shot, base, W, H, OUT}) => {}
// sha3d changes: the server root is the repository root (sfo3d's aircraft models are loaded by URL from ../sfo3d/data/
// models/, PLAN: not copied yet) and the page is /sha3d/live.html (`base` points at /sha3d/); the mock relay is OFF unless
// MOCK_RELAY=1 and then serves only /api/ping {shalive: 1} and a ZSSS METAR (no ADS-B: there is no traffic engine yet;
// sfo3d's SFO snapshot / routeset mock and its cos(37.6188) motion are gone); RELAY=http://host:port proxies /api/* to a
// running sha_live_server.py instead. The harness itself never contacts a provider (no OpenSky, no adsb.lol).
// Environment: SOFTGL=1 Mesa llvmpipe via ANGLE/EGL (this sandbox has no GPU), SWS=1 SwiftShader; W, H, DPR (default 1),
// MOBILE=1 (iPhone UA + touch), OUT (default sha3d/out/live), METAR (mock relay report; observed 10 min before T if T is
// set, else before now - the app's ?t= environment time only uses reports at or before it).
// P2e: DEVICE='iPhone 15' uses that Playwright device descriptor (viewport, UA, touch) with deviceScaleFactor DPR (default 1);
// the mock relay also answers /api/taf and (MOCK_ADSB=1) /api/adsb with one observed record.
// Phase 3 (package P3-E; docs/phase3/design.md §3, §6.3, review H5 / M14; docs/phase3/gates_time.md):
//  - TRAFFIC: off by default - window.SHA_TRAFFIC_DEFAULT = false is set before the page's scripts run, so every Phase 2 job
//    renders as before without being edited; TRAFFIC=1 leaves the app's default (on) and ?traffic= in a job's URL wins.
//  - IDENTITY gate (OD4): /api/observed_elsewhere answers {"available": false} unless IDENTITY=1 - for the mock relay AND
//    through RELAY= (the request never reaches the real relay), and /api/ping's features.identity is emptied likewise.
//    IDENTITY=1 is refused (exit 2) unless OUT is under sha3d/out/ or sha3d/refs/cache/, and always when OUT is under a docs/
//    directory: identities observed elsewhere are shown only locally and never written into a file that could be committed.
//    Static paths under any refs/ directory are never served (as the relay's allow-list: the page never reads refs/).
//  - MOCK_OVERLAY=1 (with MOCK_RELAY=1): a SYNTHETIC overlay for OVERLAY_DAY (default 2026-11-12) - fabricated records with
//    obviously fake tokens (callsigns SYNTHnn, flight numbers XX00nn, registrations TEST-nn, operator 'SYNTHETIC TEST
//    RECORD'), never a real record; refused (exit 2) for output under docs/. Served without IDENTITY=1 (it holds no identity).
//  - MOCK_METAR_HOURS=26 (with MOCK_RELAY=1): /api/metar answers a half-hourly list over that many hours, newest first, in
//    the relay's AWC JSON shape (icaoId, metarType, obsTime, reportTime, receiptTime = obs + 330 s, rawOb), the newest 10 min
//    before T (or now), each the METAR text with its own day-time group; MOCK_METAR_SHIFT='<ISO>:<wind group>' (e.g.
//    '2026-11-12T06:00:00Z:16008MPS') puts that wind into the reports from then on (a runway-direction switch). Default 0:
//    the single Phase 2 report, unchanged.
//  - the job gets {page, shot, base, W, H, OUT, IDENTITY, TRAFFIC}; the page window.SHA_HARNESS = {traffic, identity}.
import http from 'http'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url'; import { createRequire } from 'module';
let chromium;
try { ({ chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || 'playwright')); }
catch (e) { console.error('Playwright not found (require("playwright") with NODE_PATH, or set PLAYWRIGHT_MODULE=/path/to/playwright)'); process.exit(1); }

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.ROOT || path.resolve(HERE, '..');   // repository root: serves /sha3d/... and /sfo3d/data/models/...
const APP = '/' + path.relative(ROOT, HERE).split(path.sep).join('/') + '/';
const OUT = process.env.OUT || path.join(HERE, 'out', 'live');
fs.mkdirSync(OUT, { recursive: true });
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.webp': 'image/webp', '.sfom': 'application/octet-stream', '.bin': 'application/octet-stream' };
const MOCK = !!process.env.MOCK_RELAY;
const RELAY = process.env.RELAY ? new URL(process.env.RELAY) : null;
// ---- Phase 3 (P3-E): traffic default, identity gate, synthetic overlay, 26 h METAR list
const TRAFFIC = process.env.TRAFFIC === '1';
const IDENTITY = process.env.IDENTITY === '1';
const MOCK_OVERLAY = !!process.env.MOCK_OVERLAY;
{
  const outAbs = path.resolve(OUT); const segs = outAbs.split(path.sep);
  const inside = (d) => { const r = path.relative(d, outAbs); return r === '' || (!r.startsWith('..') && !path.isAbsolute(r)); };
  const underDocs = segs.includes('docs');
  if (IDENTITY && (underDocs || !(inside(path.join(HERE, 'out')) || inside(path.join(HERE, 'refs', 'cache'))))) {
    console.error(`IDENTITY=1 refused: OUT ${outAbs} is ${underDocs ? 'under docs/' : 'outside sha3d/out/ and sha3d/refs/cache/'} - identities observed elsewhere are shown only locally and never written into a file that could be committed (OD4)`);
    process.exit(2);
  }
  if (MOCK_OVERLAY && underDocs) { console.error('MOCK_OVERLAY=1 refused for output under docs/ (fabricated identities must not land in committed renders)'); process.exit(2); }
  if (IDENTITY) console.log('[harness] IDENTITY=1: /api/observed_elsewhere is passed through (local output only: ' + outAbs + ')');
}
const NO_IDENTITY = JSON.stringify({ available: false, reason: 'harness: IDENTITY=1 not set (OD4)' });
const OVERLAY_DAY = process.env.OVERLAY_DAY || '2026-11-12';
// fabricated, obviously fake records (never a real flight): the overlay shape of tools/sim/observed_overlay.py / js/sim/identity.js
function syntheticOverlay(day) {
  const d0 = Date.parse(day + 'T00:00:00Z') / 1000;   // 08:00 local on the operating day
  const types = ['A320', 'A321', 'B738', 'A333', 'A20N', 'B789'], airlines = ['CES', 'CSH', 'CSN', 'CCA', 'CES', 'CXA'];
  const records = [];
  for (let i = 0; i < 8; i++) records.push({ uid: 'synthetic-' + String(i + 1).padStart(2, '0'), role: i % 2 ? 'dep' : 'arr', airline: airlines[i % 6],
    cs: 'SYNTH' + String(i + 1).padStart(2, '0'), flight: 'XX' + String(i + 1).padStart(4, '0'), reg: 'TEST-' + String(i + 1).padStart(2, '0'), type: types[i % 6],
    operator: 'SYNTHETIC TEST RECORD (not a real flight)', far: 'ZZZZ', t_sha: d0 + 3600 * (1 + 1.5 * i) | 0, sigma_s: 300 });
  return { v: 1, day, tier: 'oe', note: 'SYNTHETIC harness overlay (livetest.mjs MOCK_OVERLAY=1): fabricated records, not observed', licence: 'none (fabricated test data)', records, available: true, synthetic: true };
}
// the mock relay's METAR list: one report (Phase 2) or MOCK_METAR_HOURS of half-hourly reports, newest first
function metarList() {
  const raw = process.env.METAR || 'METAR ZSSS 140300Z 34004MPS 9999 FEW020 SCT040 17/09 Q1022 NOSIG';
  const tNow = Math.floor((process.env.T ? Date.parse(process.env.T) : Date.now()) / 1000) - 600;
  const hours = +(process.env.MOCK_METAR_HOURS || 0);
  if (!(hours > 0)) return [{ rawOb: raw, obsTime: tNow }];
  const [shiftIso, shiftWind] = (process.env.MOCK_METAR_SHIFT || '').split(/:(?=[0-9VRB]{3}\d{2,3}(?:G\d{2,3})?(?:MPS|KT)$)/);
  const tShift = shiftIso ? Date.parse(shiftIso) / 1000 : null;
  const last = tNow - (tNow % 1800); const out = [];
  for (let t = last; t > last - hours * 3600; t -= 1800) {
    const d = new Date(t * 1000); const grp = String(d.getUTCDate()).padStart(2, '0') + String(d.getUTCHours()).padStart(2, '0') + String(d.getUTCMinutes()).padStart(2, '0') + 'Z';
    let r = raw.replace(/\b\d{6}Z\b/, grp); if (tShift != null && shiftWind && t >= tShift) r = r.replace(/\b(\d{3}|VRB)\d{2,3}(G\d{2,3})?(MPS|KT)\b/, shiftWind);
    out.push({ icaoId: 'ZSSS', metarType: 'METAR', obsTime: t, reportTime: d.toISOString(), receiptTime: new Date((t + 330) * 1000).toISOString(), rawOb: r });
  }
  return out;
}
function proxy(req, res, p) {
  const r2 = http.request({ host: RELAY.hostname, port: RELAY.port, path: p, method: req.method, headers: { ...req.headers, host: RELAY.host } }, (r) => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
  r2.on('error', (e) => { res.statusCode = 502; res.end(String(e)); }); req.pipe(r2); res.on('close', () => r2.destroy());
}
// /api/ping through RELAY= without IDENTITY=1: the relay's list of local identity days is emptied (the page then never asks)
function proxyPing(req, res, p) {
  const r2 = http.request({ host: RELAY.hostname, port: RELAY.port, path: p, method: req.method, headers: { ...req.headers, host: RELAY.host, 'accept-encoding': 'identity' } }, (r) => {
    const parts = []; r.on('data', (c) => parts.push(c)); r.on('end', () => { let body = Buffer.concat(parts).toString('utf8');
      try { const j = JSON.parse(body); if (j && j.features && 'identity' in j.features) { j.features.identity = []; body = JSON.stringify(j); } } catch (e) { }
      const h = { ...r.headers }; delete h['content-length']; delete h['content-encoding']; res.writeHead(r.statusCode, h); res.end(body); }); });
  r2.on('error', (e) => { res.statusCode = 502; res.end(String(e)); }); req.pipe(r2); res.on('close', () => r2.destroy());
}
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  const api = url.pathname.startsWith(APP + 'api/') ? url.pathname.slice(APP.length - 1) : null;   // '/api/...'
  // (P3-E identity gate: never forwarded to RELAY= without IDENTITY=1; the synthetic overlay only from the mock relay)
  if (api === '/api/observed_elsewhere' && !IDENTITY && !(MOCK && MOCK_OVERLAY && !RELAY)) { res.setHeader('Content-Type', 'application/json'); return res.end(NO_IDENTITY); }
  if (api === '/api/ping' && RELAY && !IDENTITY) return proxyPing(req, res, api + url.search);
  if (api && RELAY) return proxy(req, res, api + url.search);
  if (api && MOCK) {
    res.setHeader('Content-Type', 'application/json');
    if (api === '/api/ping') return res.end(JSON.stringify({ shalive: 1, mock: true, mode: 'live', features: { metar: true, taf: true, adsb: !!process.env.MOCK_ADSB, ...(MOCK_OVERLAY ? { identity: [OVERLAY_DAY] } : {}) } }));
    if (api === '/api/observed_elsewhere') { const day = url.searchParams.get('day') || ''; if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) { res.statusCode = 400; return res.end(JSON.stringify({ available: false, error: 'day must be YYYY-MM-DD' })); }
      return res.end(JSON.stringify(day === OVERLAY_DAY ? syntheticOverlay(day) : { available: false, reason: 'harness: no synthetic overlay for this day' })); }
    if (api === '/api/taf') return res.end(JSON.stringify([{ rawTAF: process.env.TAF || 'TAF ZSSS 140306Z 1406/1512 35004MPS 6000 BKN015 TX20/1406Z TN16/1421Z', issueTime: '2026-11-14T03:06:00.000Z' }]));
    if (api === '/api/adsb') return res.end(JSON.stringify({ enabled: !!process.env.MOCK_ADSB, ac: process.env.MOCK_ADSB ? [{ hex: 'mock01', type: 'adsb_icao', src: 'obs', lat: 31.6, lon: 122.0, alt_baro: 35000 }] : [], excluded: {} }));
    if (api === '/api/metar') return res.end(JSON.stringify(metarList()));
    res.statusCode = 404; return res.end('[]');
  }
  if (api) { res.statusCode = 404; return res.end(); }
  if (/(^|\/)refs\//.test(url.pathname)) { res.statusCode = 403; return res.end(); }   // (P3-E: never refs/, as the relay)
  const f = path.join(ROOT, decodeURIComponent(url.pathname === '/' ? APP + 'live.html' : url.pathname));
  if (!f.startsWith(ROOT)) { res.statusCode = 403; return res.end(); }
  fs.readFile(f, (e, d) => { if (e) { res.statusCode = 404; return res.end(); } res.setHeader('Content-Type', TYPES[path.extname(f)] || 'application/octet-stream'); res.setHeader('Cache-Control', 'no-store'); res.end(d); });
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}${APP}`;
// GPU: default = Chromium's own choice. SWS=1: SwiftShader. SOFTGL=1: Mesa llvmpipe via ANGLE/EGL (sfo3d livetest.mjs).
const gpuArgs = process.env.SWS ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : process.env.SOFTGL ? ['--use-gl=angle', '--use-angle=gl-egl'] : [];
const browser = await chromium.launch({ args: [...gpuArgs, '--ignore-gpu-blocklist', '--js-flags=--max-old-space-size=4000', '--disable-gpu-watchdog', '--disable-renderer-backgrounding', '--disable-background-timer-throttling', '--disable-gpu-process-crash-limit'],
  env: process.env.SOFTGL ? { ...process.env, LIBGL_ALWAYS_SOFTWARE: '1', GALLIUM_DRIVER: 'llvmpipe', LP_NUM_THREADS: process.env.LP_NUM_THREADS || '4' } : process.env });
const { devices } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || 'playwright');
const DEV = process.env.DEVICE ? devices[process.env.DEVICE] : null; if (process.env.DEVICE && !DEV) { console.error('unknown DEVICE', process.env.DEVICE); process.exit(1); }
const W = +(process.env.W || (DEV ? DEV.viewport.width : 1280)), H = +(process.env.H || (DEV ? DEV.viewport.height : 720));
const ctx = DEV ? await browser.newContext({ ...DEV, defaultBrowserType: undefined, viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1) }) : await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1), isMobile: !!process.env.MOBILE, hasTouch: !!process.env.MOBILE,
  userAgent: process.env.MOBILE ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' : undefined });
const page = await ctx.newPage();
page.setDefaultTimeout(0);
// (P3-E) simulated traffic off unless TRAFFIC=1 (design §6.3: the app's default is window.SHA_TRAFFIC_DEFAULT ?? true)
await page.addInitScript(([traffic, identity]) => { if (!traffic) window.SHA_TRAFFIC_DEFAULT = false; window.SHA_HARNESS = { traffic, identity }; }, [TRAFFIC, IDENTITY]);
page.on('console', m => { const t = m.text(); if (!/GPU stall|GL Driver|Automatic fallback|fonts.g/.test(t)) console.log('[page]', t.slice(0, 400)); });
page.on('pageerror', e => console.log('[pageerror]', e.message, e.stack && e.stack.split('\n').slice(0, 4).join(' | ')));
// the sandbox has no route to Google Fonts: answer them locally (system fonts are used)
await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
const shot = async (name, opts = {}) => { const f = path.join(OUT, name + '.png'); await page.screenshot({ path: f, ...opts }); console.log('shot', f); return f; };
const script = await import(path.resolve(process.argv[2]));
const t0 = Date.now();
try { await script.default({ page, shot, base, W, H, OUT, IDENTITY, TRAFFIC }); } catch (e) { console.log('SCRIPT FAILED', e); process.exitCode = 1; }
console.log('done in', ((Date.now() - t0) / 1000).toFixed(1), 's');
await browser.close(); server.close(); process.exit();

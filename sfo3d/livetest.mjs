// Test harness for the live app: static server + mock ADS-B relay (synthetic motion from the recorded snapshot),
// headless Chromium, screenshots. Usage: node livetest.mjs <script.mjs>   (script exports default async ({page, shot, base}) => {})
// RELAY=http://host:port: proxy /api/* to a running sfo_live_server.py (live or --replay) instead of the mock.
import http from 'http'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
// Playwright: `npm i -D playwright && npx playwright install chromium` (or point PLAYWRIGHT_MODULE at an install)
let chromium;
try { ({ chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')); }
catch (e) { console.error('Playwright not found: run `npm i -D playwright && npx playwright install chromium`, or set PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs'); process.exit(1); }

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.ROOT || HERE;
const OUT = process.env.OUT || path.join(HERE, 'out', 'live');
fs.mkdirSync(OUT, { recursive: true });
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.sfom': 'application/octet-stream', '.bin': 'application/octet-stream' };

// ---- mock relay: recorded snapshot with simple kinematics so aircraft move
const snapSrc = fs.readFileSync(path.join(ROOT, 'data', 'snapshot.js'), 'utf8');
const SNAP = JSON.parse(/SNAPSHOT = (\{.*?\});\n/s.exec(snapSrc)[1]);
const T0 = Date.now();
function mockFeed() {
  const t = (Date.now() - T0) / 1000; const out = [];
  for (const a0 of SNAP.ac) {
    const a = { ...a0 };
    const moving = a.gs && a.gs > 3;
    if (moving && a.track != null) {
      const k = a.alt_baro === 'ground' ? 0.35 : 1; // taxiing aircraft slow down in the mock
      const d = a.gs * 0.514444 * t * k; const tr = a.track * Math.PI / 180;
      a.lat += d * Math.cos(tr) / 110990; a.lon += d * Math.sin(tr) / (111320 * Math.cos(37.6188 * Math.PI / 180));
      if (a.alt_baro !== 'ground' && a.baro_rate) a.alt_baro = Math.max(100, Math.round((a.alt_baro + a.baro_rate * t / 60) / 25) * 25);
    }
    a.seen = 0.5; a.seen_pos = 0.8; a.nav_qnh = a.alt_baro !== 'ground' && a.alt_baro < 10000 ? 1014.6 : undefined;
    out.push(a);
  }
  return { ac: out, now: Date.now(), msg: 'No error', total: out.length, _source: 'mock relay (test)' };
}
// RELAY=http://127.0.0.1:18731 proxies every /api/* request (including the SSE stream) to a running
// sfo_live_server.py instead of the mock, e.g. `python3 sfo_live_server.py --port 18731 --replay refs/cache/rec
// --from 2026-09-24T14:00Z` to test the app on real recorded traffic.
const RELAY = process.env.RELAY ? new URL(process.env.RELAY) : null;
function proxy(req, res) {
  const p = http.request({ host: RELAY.hostname, port: RELAY.port, path: req.url, method: req.method,
    headers: { ...req.headers, host: RELAY.host } }, (r) => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
  p.on('error', (e) => { res.statusCode = 502; res.end(String(e)); });
  req.pipe(p);
  res.on('close', () => p.destroy());
}
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (RELAY && url.pathname.startsWith('/api/')) return proxy(req, res);
  if (url.pathname === '/api/ping') { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ sfolive: 1, mock: true })); }
  if (url.pathname === '/api/adsb') { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(mockFeed())); }
  if (url.pathname === '/api/metar') { res.setHeader('Content-Type', 'text/plain'); return res.end(process.env.METAR || 'METAR KSFO 231756Z 29012KT 10SM FEW008 18/13 A2996'); }
  if (url.pathname === '/api/routeset') {
    let body = ''; req.on('data', d => body += d); req.on('end', () => {
      const j = JSON.parse(body || '{}'); const R = { UAL893: 'SFO-TPE', UAL1164: 'SFO-ORD', SKW3305: 'LAX-SFO', SWA3228: 'LAS-SFO', UAL323: 'SFO-LAX', DAL1715: 'SLC-SFO', CPA870: 'SFO-HKG', SKW249R: 'SFO-PDX' };
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify((j.planes || []).map(p => R[p.callsign] ? { callsign: p.callsign, _airport_codes_iata: R[p.callsign], _airports: R[p.callsign].split('-').map(c => ({ iata: c, icao: 'K' + c, name: c + ' airport', location: { SFO: 'San Francisco', TPE: 'Taipei', ORD: 'Chicago', LAX: 'Los Angeles', LAS: 'Las Vegas', SLC: 'Salt Lake City', HKG: 'Hong Kong', PDX: 'Portland' }[c], countryiso2: 'US' })), plausible: true } : { callsign: p.callsign, _airport_codes_iata: 'unknown', _airports: [] })));
    });
    return;
  }
  if (process.env.NORELAY && url.pathname.startsWith('/api/')) { res.statusCode = 404; return res.end(); }
  const f = path.join(ROOT, url.pathname === '/' ? 'live.html' : decodeURIComponent(url.pathname));
  fs.readFile(f, (e, d) => { if (e) { res.statusCode = 404; return res.end(); } res.setHeader('Content-Type', TYPES[path.extname(f)] || 'application/octet-stream'); res.setHeader('Cache-Control', 'no-store'); res.end(d); });
});
await new Promise(r => server.listen(0, r));
const base = `http://localhost:${server.address().port}/`;
// GPU: default = Chromium's own choice (real GPU where available). SWS=1: SwiftShader. SOFTGL=1: Mesa llvmpipe via
// ANGLE/EGL (what the original Linux sandbox used; much faster than SwiftShader there).
const gpuArgs = process.env.SWS ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : process.env.SOFTGL ? ['--use-gl=angle', '--use-angle=gl-egl'] : [];
const browser = await chromium.launch({ args: [...gpuArgs, '--ignore-gpu-blocklist', '--js-flags=--max-old-space-size=4000', '--disable-gpu-watchdog', '--disable-renderer-backgrounding', '--disable-background-timer-throttling', '--disable-gpu-process-crash-limit'],
  env: process.env.SOFTGL ? { ...process.env, LIBGL_ALWAYS_SOFTWARE: '1', GALLIUM_DRIVER: 'llvmpipe', LP_NUM_THREADS: process.env.LP_NUM_THREADS || '4' } : process.env });
const W = +(process.env.W || 1280), H = +(process.env.H || 720);
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1), isMobile: !!process.env.MOBILE, hasTouch: !!process.env.MOBILE,
  userAgent: process.env.MOBILE ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' : undefined });
const page = await ctx.newPage();
page.setDefaultTimeout(0);
page.on('console', m => { const t = m.text(); if (!/GPU stall|GL Driver|Automatic fallback/.test(t)) console.log('[page]', t.slice(0, 400)); });
page.on('pageerror', e => console.log('[pageerror]', e.message, e.stack && e.stack.split('\n').slice(0, 4).join(' | ')));
const shot = async (name, opts = {}) => { const f = path.join(OUT, name + '.png'); await page.screenshot({ path: f, ...opts }); console.log('shot', f); return f; };
const script = await import(path.resolve(process.argv[2]));
const t0 = Date.now();
try { await script.default({ page, shot, base, W, H, OUT }); } catch (e) { console.log('SCRIPT FAILED', e); process.exitCode = 1; }
console.log('done in', ((Date.now() - t0) / 1000).toFixed(1), 's');
await browser.close(); server.close(); process.exit();

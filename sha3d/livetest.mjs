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
function proxy(req, res, p) {
  const r2 = http.request({ host: RELAY.hostname, port: RELAY.port, path: p, method: req.method, headers: { ...req.headers, host: RELAY.host } }, (r) => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
  r2.on('error', (e) => { res.statusCode = 502; res.end(String(e)); }); req.pipe(r2); res.on('close', () => r2.destroy());
}
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  const api = url.pathname.startsWith(APP + 'api/') ? url.pathname.slice(APP.length - 1) : null;   // '/api/...'
  if (api && RELAY) return proxy(req, res, api + url.search);
  if (api && MOCK) {
    res.setHeader('Content-Type', 'application/json');
    if (api === '/api/ping') return res.end(JSON.stringify({ shalive: 1, mock: true, mode: 'live', features: { metar: true, taf: true, adsb: !!process.env.MOCK_ADSB } }));
    if (api === '/api/taf') return res.end(JSON.stringify([{ rawTAF: process.env.TAF || 'TAF ZSSS 140306Z 1406/1512 35004MPS 6000 BKN015 TX20/1406Z TN16/1421Z', issueTime: '2026-11-14T03:06:00.000Z' }]));
    if (api === '/api/adsb') return res.end(JSON.stringify({ enabled: !!process.env.MOCK_ADSB, ac: process.env.MOCK_ADSB ? [{ hex: 'mock01', type: 'adsb_icao', src: 'obs', lat: 31.6, lon: 122.0, alt_baro: 35000 }] : [], excluded: {} }));
    if (api === '/api/metar') { const raw = process.env.METAR || 'METAR ZSSS 140300Z 34004MPS 9999 FEW020 SCT040 17/09 Q1022 NOSIG'; return res.end(JSON.stringify([{ rawOb: raw, obsTime: Math.floor((process.env.T ? Date.parse(process.env.T) : Date.now()) / 1000) - 600 }])); }
    res.statusCode = 404; return res.end('[]');
  }
  if (api) { res.statusCode = 404; return res.end(); }
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
page.on('console', m => { const t = m.text(); if (!/GPU stall|GL Driver|Automatic fallback|fonts.g/.test(t)) console.log('[page]', t.slice(0, 400)); });
page.on('pageerror', e => console.log('[pageerror]', e.message, e.stack && e.stack.split('\n').slice(0, 4).join(' | ')));
// the sandbox has no route to Google Fonts: answer them locally (system fonts are used)
await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
const shot = async (name, opts = {}) => { const f = path.join(OUT, name + '.png'); await page.screenshot({ path: f, ...opts }); console.log('shot', f); return f; };
const script = await import(path.resolve(process.argv[2]));
const t0 = Date.now();
try { await script.default({ page, shot, base, W, H, OUT }); } catch (e) { console.log('SCRIPT FAILED', e); process.exitCode = 1; }
console.log('done in', ((Date.now() - t0) / 1000).toFixed(1), 's');
await browser.close(); server.close(); process.exit();

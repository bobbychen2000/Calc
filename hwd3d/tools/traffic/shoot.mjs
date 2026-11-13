// Headless renders of the P3 traffic test page (tools/traffic/view.html) into out/traffic/render_*.png.
//   node tools/traffic/shoot.mjs [--pack weekend] [--min 20] [--port 8763] [--phone]
// Static server on 127.0.0.1:<port> over hwd3d/ (serves out/replay/ for the pack), Chromium with SwiftShader (no GPU here),
// 1280x720 (or 390x844 @2 phone). Views: a line-up of every placeholder class on the Green Ramp, then views framed on
// drawn traffic of the replay at --min minutes (parked aircraft, an aircraft taxiing, one on a runway, a helicopter).
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import net from 'node:net'; import { fileURLToPath } from 'node:url'; import { createRequire } from 'node:module';
const require = createRequire(import.meta.url); const { chromium } = require('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..'); const OUT = path.join(ROOT, 'out', 'traffic'); fs.mkdirSync(OUT, { recursive: true });
const args = process.argv.slice(2); const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const port = +opt('port', 8763), pack = opt('pack', 'weekend'), min = +opt('min', 20), phone = args.includes('--phone');
await new Promise((res, rej) => { const s = net.createServer().once('error', rej).once('listening', () => s.close(res)).listen(port, '127.0.0.1'); });
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.gz': 'application/octet-stream' };
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname)); if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': TYPES[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(port, '127.0.0.1', r));
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-watchdog'] });
try {
  const ctx = await browser.newContext(phone ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true } : { viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage(); page.on('pageerror', e => console.log('PAGEERROR', e.message)); page.on('console', m => { if (/error/i.test(m.text())) console.log('console', m.text().slice(0, 300)); });
  await page.goto(`http://127.0.0.1:${port}/tools/traffic/view.html`);
  await page.waitForFunction(() => window.__trafficReady || window.__trafficError, null, { timeout: 180000 });
  const err = await page.evaluate(() => window.__trafficError); if (err) throw new Error(err);
  const save = async (name, v) => { const url = await page.evaluate((v) => window.HWDT.shot(v), v); const f = path.join(OUT, `render_${name}${phone ? '_phone' : ''}.png`); fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64')); console.log('->', path.relative(ROOT, f)); };
  // 1. line-up
  const L = await page.evaluate(() => window.HWDT.showLineup(true));
  const gy = await page.evaluate((c) => window.HWDT.gy(c[0], c[1]), L.centre);
  await save('lineup', { target: [L.centre[0], gy + 1.5, L.centre[1]], yaw: 300, pitch: 22, dist: L.len * 0.75, fov: 40 });
  await save('lineup_close', { target: [L.centre[0], gy + 1.5, L.centre[1]], yaw: 330, pitch: 14, dist: L.len * 0.4, fov: 40 });
  for (const e of L.each) if (['C172', 'P28A', 'BE55', 'PC12', 'SF50', 'C56X', 'R44', 'CH7A'].includes(e.type)) await save('type_' + e.type, { target: [e.pos[0], e.pos[1] + 1.2, e.pos[2]], yaw: 75, pitch: 16, dist: Math.max(e.L, e.span) * 1.6, fov: 40 });
  await page.evaluate(() => window.HWDT.showLineup(false));
  // 2. traffic at `min` minutes
  await page.evaluate(async ([p, m]) => { const P = await window.HWDT.loadPack('../../out/replay/pack_' + p + '.json.gz'); await window.HWDT.runTo(P, m); }, [pack, min]);
  const T = await page.evaluate(() => window.HWDT.tracks());
  console.log('drawn', T.length, JSON.stringify(T.map(t => [t.type, t.phase, t.x, t.z, t.ground, t.spot])).slice(0, 1500));
  fs.writeFileSync(path.join(OUT, `render_tracks_${pack}_${min}.json`), JSON.stringify(T, null, 1));
  const pick = (f) => T.find(f);
  const shots = [['parked', pick(t => t.phase === 'parked' && t.spot) || pick(t => t.phase === 'parked')], ['taxi', pick(t => t.phase === 'taxi' && t.gs > 1)], ['runway', pick(t => ['takeoff_roll', 'landing_roll', 'touch_and_go', 'line_up', 'runway_taxi'].includes(t.phase))],
    ['heli', pick(t => t.cls === 'heli')], ['air', pick(t => !t.ground && t.cls !== 'heli' && Math.hypot(t.x, t.z) < 4000)]];
  for (const [n, t] of shots) { if (!t) { console.log('no', n); continue; } const d = t.ground ? 70 : 140; await save(`${pack}_${min}_${n}`, { target: [t.x, t.y + 1, t.z], yaw: (t.hdg + 140) % 360, pitch: t.ground ? 24 : 12, dist: d, fov: 40 }); }
  await save(`${pack}_${min}_green`, { target: [-60, 12, -330], yaw: 20, pitch: 40, dist: 260, fov: 45 });
} finally { await browser.close(); server.close(); }

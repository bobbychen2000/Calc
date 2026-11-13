// Headless stills of the dev model viewer (dev/model.html) - hwd3d Phase 3, M2.
//   node dev/model_shot.mjs [--model=PC12] [--set=standard|<name,...>] [--out=docs/phase3] [--prefix=pc12] [--world=0]
//                           [--size=1920x1080] [--max-kb=600] [--port=8800..8899] [--t=<ISO>] [--jobs=<file.json>]
//                           [--viewer=desktop|phone --cam=front34 --wait=15000]   (screenshot of the interactive viewer)
// A static server on 127.0.0.1 (first free port in 8800-8899) serves hwd3d/; Chromium (SwiftShader: no GPU here) loads
// the viewer ONCE per model and every shot is posed with window.HWDM.set() (no reload), rendered by the page and read
// back from the renderer's final framebuffer, then saved as JPEG at the highest quality that fits --max-kb.
// Provenance (fix round 1 of Phase 3a): every image written into docs/phase3 gets its caption in docs/phase3/SOURCES.json
// (pose, time, the model file's sha256, the OSM / NAIP notices of the HWD world), so a still of a superseded model build is
// detectable (tools/models/test_models.mjs compares the recorded hash with the model file). A job may carry `desc`.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import crypto from 'node:crypto';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2); const opt = (k, d) => { const a = args.find(x => x.startsWith('--' + k + '=')); return a ? a.slice(k.length + 3) : d; };
const MODEL = opt('model', 'PC12').toUpperCase(), OUT = path.resolve(ROOT, opt('out', 'docs/phase3')), PREFIX = opt('prefix', MODEL.toLowerCase());
const [VW, VH] = opt('size', '1920x1080').split('x').map(Number), MAXKB = +opt('max-kb', 600);
fs.mkdirSync(OUT, { recursive: true });
// the standard set (task M2-5): front 3/4, rear 3/4, side, low chase-cam, gear half-retracted (airborne), flaps 40
export const STANDARD = {
  front34: { cam: 'front34', gear: 1, flaps: 0, rpm: 0, alt: 0, desc: 'front 3/4 on the Green Ramp (overall shape, livery, glazing, shadow)' },
  rear34: { cam: 'rear34', gear: 1, flaps: 0, rpm: 0, alt: 0, desc: 'rear 3/4 on the Green Ramp (tail, wing tips, nacelle / bullet fairing)' },
  side: { cam: 'side', gear: 1, flaps: 0, rpm: 0, alt: 0, desc: 'starboard side on the Green Ramp (profile, windows, gear)' },
  chase: { cam: 'chase', gear: 1, flaps: 15, rpm: 1700, alt: 0, at: 'rwy28L', hdg: null, lights: 'nav,beacon,strobe,landing', desc: 'low chase camera on runway 28L, 300 m past the threshold' },
  gear_half: { cam: 'under', gear: 0.5, flaps: 15, rpm: 1700, alt: 9, apitch: 6, at: 'rwy28L', hdg: null, lights: 'nav,beacon,strobe,landing', desc: 'from below, 9 m up over 28L, gear half way (doors, legs, braces)' },
  flaps40: { cam: 'rear34', gear: 1, flaps: 40, rpm: 0, alt: 0, at: 'ramp', hdg: 135, apitch: 0, lights: null, desc: 'rear 3/4 on the Green Ramp, flaps fully down (the pivot clamps 40 to the type maximum)' },
};
// every job starts from BASE (set() merges parameters: anything a job does not name is reset here)
export const BASE = { eye: null, tgt: null, fov: null, gear: 1, flaps: 0, rpm: 0, rotor: null, bpitch: null, alt: 0, apitch: 0, aroll: 0, ctl: null, trim: null, doors: null, lights: null, at: 'ramp', hdg: 135, alpha: null };
const sets = opt('set', opt('jobs') ? '' : 'standard');
const JOBS = sets === 'standard' ? { ...STANDARD } : Object.fromEntries(sets.split(',').filter(Boolean).map(n => [n, STANDARD[n] || { cam: n }]));
if (opt('jobs')) Object.assign(JOBS, JSON.parse(fs.readFileSync(opt('jobs'), 'utf8')));

// the model file this run renders (its hash goes into every caption)
const MODEL_FILE = path.join(ROOT, 'js/aircraft/models', MODEL.toLowerCase() + '.glb');
const MODEL_SHA = fs.existsSync(MODEL_FILE) ? crypto.createHash('sha256').update(fs.readFileSync(MODEL_FILE)).digest('hex') : null;
const NOTICE_WORLD = 'HWD world of this repository: airfield geometry from data/hwd_airport.json (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright), and FAA NASR (public domain); ground texture USDA NAIP 2024 (USDA FPAC Business Center, Geospatial Enterprise Operations), public domain.';
const LICENCE = (world) => 'Own render of the hwd3d dev model viewer (dev/model.html, this repository) of an own aircraft model (original neutral livery; no manufacturer logo, no registration: D1). ' +
  (world ? 'Base: ' + NOTICE_WORLD + ' A Produced Work under ODbL 4.3: the notice is in this caption.' : 'Neutral concrete pad (no third-party content).');
function writeCaptions(entries) {
  if (path.relative(path.join(ROOT, 'docs/phase3'), OUT) !== '') return;   // captions only for the committed docs folder
  const f = path.join(OUT, 'SOURCES.json'); const S = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : {};
  for (const [k, v] of Object.entries(entries)) S[k] = v;
  const keys = Object.keys(S).sort((a, b) => (a === '_note' ? -1 : b === '_note' ? 1 : a.localeCompare(b)));
  fs.writeFileSync(f, JSON.stringify(Object.fromEntries(keys.map(k => [k, S[k]])), null, 1) + '\n');
}

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.glb': 'model/gltf-binary', '.bin': 'application/octet-stream' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});
let port = +opt('port', 0);
for (const p of port ? [port] : Array.from({ length: 100 }, (_, i) => 8800 + i)) {
  const ok = await new Promise(r => { server.once('error', () => r(false)); server.listen(p, '127.0.0.1', () => r(true)); });
  if (ok) { port = p; break; }
}
if (!server.listening) throw new Error('no free port in 8800-8899');
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-watchdog', '--js-flags=--max-old-space-size=3500'] });
const report = [];
try {
  const ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { const t = m.text(); if (m.type() === 'error' || /error|warn|fail/i.test(t)) { errors.push(t.slice(0, 300)); console.log('[page]', t.slice(0, 300)); } });
  page.on('pageerror', e => { errors.push('PAGEERROR ' + e.message); console.log('[page] PAGEERROR', e.message); });
  // --viewer=desktop|phone: a page screenshot of the interactive viewer (HUD + controls) instead of the shot set
  const VIEWER = opt('viewer');
  if (VIEWER) {
    const phone = VIEWER === 'phone';
    const vctx = await browser.newContext(phone ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' } : { viewport: { width: VW, height: VH }, deviceScaleFactor: 1 });
    const vp = await vctx.newPage(); vp.on('pageerror', e => console.log('[viewer] PAGEERROR', e.message));
    const vq = new URLSearchParams({ model: MODEL, cam: opt('cam', 'front34') }); for (const k of ['gear', 'flaps', 'rpm', 'world', 'at', 'hdg']) if (opt(k)) vq.set(k, opt(k));
    await vp.goto(`http://127.0.0.1:${port}/dev/model.html?${vq}`);
    await vp.waitForFunction(() => window.__modelReady || window.__modelError, null, { timeout: 300000 });
    await vp.waitForTimeout(+opt('wait', 15000));
    // SwiftShader takes seconds per frame: stop the render loop, draw one frame, then let the compositor take the picture
    await vp.evaluate(() => { window.HWDM.pause(true); window.HWDM.render(); window.HWDM.hud(); });
    await vp.waitForTimeout(1500);
    const file = path.join(OUT, `${opt('prefix', 'viewer')}_${VIEWER}.jpg`);
    let q = 90, buf; do { buf = await vp.screenshot({ type: 'jpeg', quality: q, timeout: 180000 }); q -= 6; } while (buf.length > MAXKB * 1024 && q > 40);
    fs.writeFileSync(file, buf); console.log(`viewer ${VIEWER} -> ${path.relative(ROOT, file)} ${Math.round(buf.length / 1024)} kB`);
    const worldV = opt('world') !== '0';
    writeCaptions({ [path.basename(file)]: { caption: `Dev model viewer (dev/model.html) with its HUD and controls, ${phone ? 'phone 390x844 @2 with an iPhone user agent (layout / touch, OD2)' : `desktop ${VW}x${VH}`}: ${MODEL}, camera preset ${opt('cam', 'front34')}.`,
      model: MODEL, model_sha256: MODEL_SHA, rendered_utc: new Date().toISOString(), made_by: 'dev/model_shot.mjs --viewer=' + VIEWER, licence: LICENCE(worldV) } });
    await vctx.close(); await browser.close(); server.close(); process.exit(0);
  }
  const qs = new URLSearchParams({ shot: '1', model: MODEL, scale: '1' }); if (opt('world')) qs.set('world', opt('world')); if (opt('t')) qs.set('t', opt('t'));
  const t0 = Date.now();
  await page.goto(`http://127.0.0.1:${port}/dev/model.html?${qs}`);
  await page.waitForFunction(() => window.__modelReady || window.__modelError, null, { timeout: 300000 });
  const err = await page.evaluate(() => window.__modelError); if (err) throw new Error(err);
  const info = await page.evaluate(() => ({ info: window.HWDM.info, error: window.HWDM.error, world: window.HWDM.worldMode(), items: window.HWDM.itemProgs() }));
  console.log(`${MODEL} ready in ${Date.now() - t0} ms on port ${port}: world ${info.world}, ${info.error ? 'ERROR ' + info.error : (info.info.tris + ' tris')}, draw items ${JSON.stringify(info.items)}`);
  for (const [name, params] of Object.entries(JOBS)) {
    const t1 = Date.now();
    const st = await page.evaluate((p) => window.HWDM.set(p), { ...BASE, ...params });
    let url = await page.evaluate(() => window.HWDM.shot({ n: 3, jq: 0.92 }));
    let jq = 0.92; while (Buffer.byteLength(url.split(',')[1], 'base64') > MAXKB * 1024 && jq > 0.4) { jq -= 0.06; url = await page.evaluate((j) => window.HWDM.reencode(j), jq); }
    const buf = Buffer.from(url.split(',')[1], 'base64'); const file = path.join(OUT, `${PREFIX}_${name}.jpg`); fs.writeFileSync(file, buf);
    report.push({ name, file: path.relative(ROOT, file), kb: Math.round(buf.length / 1024), jpeg_q: Math.round(jq * 100) / 100, ms: Date.now() - t1, params, state: st, model_sha256: MODEL_SHA });
    const P = { ...BASE, ...params }; const worldS = opt('world') !== '0';
    const pose = ['gear ' + P.gear, 'flaps ' + P.flaps, P.rpm ? P.rpm + ' rpm' : 'rotor stopped', P.alt ? `${P.alt} m up` : 'on the ground', P.apitch ? `pitch ${P.apitch} deg` : null, P.ctl ? 'controls ' + P.ctl : null, P.lights ? 'lights ' + P.lights : null, P.alpha != null && P.alpha !== 1 ? 'fade alpha ' + P.alpha : null].filter(Boolean).join(', ');
    writeCaptions({ [path.basename(file)]: { caption: `${MODEL} in the hwd3d renderer (SwiftShader, ${VW}x${VH}, MSAA 4, 4096 shadow cascades), ${params.desc || 'camera ' + (P.cam || 'custom')}; ${pose}; at ${P.at}${P.hdg != null ? ', heading ' + P.hdg : ''}; time ${opt('t', '2026-11-13T20:30Z (default, 12:30 PST)')}.`,
      model: MODEL, model_sha256: MODEL_SHA, rendered_utc: new Date().toISOString(), made_by: 'dev/model_shot.mjs', params: P, licence: LICENCE(worldS) } });
    console.log(`  ${name} -> ${path.relative(ROOT, file)} ${Math.round(buf.length / 1024)} kB q${jq.toFixed(2)} (${Date.now() - t1} ms)`);
  }
  fs.writeFileSync(path.join(ROOT, 'out', `model_shot_${PREFIX}.json`), JSON.stringify({ model: MODEL, port, info, errors, report }, null, 1));
  await ctx.close();
} finally { await browser.close(); server.close(); }

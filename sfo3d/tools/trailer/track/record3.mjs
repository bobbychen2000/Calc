// one shot of the tracking films (spec in SHOTS_JSON, id argv[2]): Full build on :8771, Xvfb + Mesa llvmpipe, virtual clock +
// manual rAF, replay pack trimmed to start `off` s into the 8 Nov 20:46Z recording (make_replays.py), canvas capture into ffmpeg.
// Unlike record2.mjs (which waits for an event), a shot follows ONE aircraft (sh.hex) from a given recording time sh.start
// (s after the original pack's first event, F0) for sh.n frames, at sh.speed recorded seconds per video second (time-lapse).
// Cameras: chase (behind/beside the smoothed heading), orbit (world yaw around the aircraft), spot (fixed position, panning to
// follow the aircraft). PREVIEW=1 renders only 5 stills (u = 0, .25, .5, .75, 1) at 960x540, stepping the clock in between.
import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
import { spawn } from 'child_process'; import fs from 'fs';
const ID = process.argv[2], OUT = process.env.OUT, FPS = 24, PREVIEW = !!process.env.PREVIEW;
const W = PREVIEW ? 960 : +(process.env.W || 1920), H = PREVIEW ? 540 : +(process.env.H || 1080), Q = process.env.Q || 'high';
const F0 = 1794170758.662;   // first event of data/replay.wasm (2026-11-08T20:45:58.662Z)
const sh = JSON.parse(fs.readFileSync(process.env.SHOTS_JSON, 'utf8')).find(s => s.id === ID); if (!sh) { console.log('unknown shot', ID); process.exit(2); }
const N = sh.n, SPEED = sh.speed || 1, dt = SPEED * 1000 / FPS;
const lin = (a, b, u) => a + (b - a) * u, ease = u => u * u * (3 - 2 * u);
const L = (r, u, e = true) => Array.isArray(r) ? lin(r[0], r[1], e ? ease(u) : u) : r;
const C = sh.cam;
const cam = (u) => ({ type: C.type, hex: sh.hex, up: C.up ?? 2, tau: C.tau ?? 2.5, dts: SPEED / FPS, yawOff: L(C.yawOff, u), yaw: L(C.yaw, u), pitch: L(C.pitch, u), dist: L(C.dist, u), fov: L(C.fov || 40, u), frame: C.frame ? L(C.frame, u) : 0, pos: C.pos, lead: C.lead || 0 });
const browser = await chromium.launch({ headless: !process.env.XGL, args: [...(process.env.XGL ? ['--use-gl=angle', '--use-angle=gl'] : ['--use-gl=angle', '--use-angle=gl-egl']), '--ignore-gpu-blocklist', '--disable-gpu-watchdog', '--js-flags=--max-old-space-size=5000', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'],
  env: { ...process.env, LIBGL_ALWAYS_SOFTWARE: '1', GALLIUM_DRIVER: 'llvmpipe', LP_NUM_THREADS: '4' } });
const page = await browser.newPage({ viewport: { width: 640, height: 360 }, deviceScaleFactor: 1 });
await page.addInitScript({ content: `window.SFO_LIVERY_RES = ${JSON.stringify(process.env.LIV || 'auto')};` });
page.on('pageerror', e => console.log('PAGEERR', String(e).slice(0, 200)));
if (sh.off) await page.route('**/replay.wasm', r => r.fulfill({ path: `${process.env.REPLAYS}/replay_${sh.off}.gz`, contentType: 'application/wasm' }));
await page.clock.install();
const t0 = Date.now();
await page.goto(`http://127.0.0.1:8771/sfo_phone_test.html?quality=${sh.q || Q}&fixedres=1&t=${sh.t}` + (sh.metar ? `&metar=${encodeURIComponent(sh.metar)}` : '') + (sh.expo ? `&expo=${sh.expo}` : ''));
await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0, polling: 500 });
const err = await page.evaluate(() => window.__sfoError || null); if (err) { console.log('APPERR', err.slice(0, 300)); process.exit(3); }
await page.waitForFunction(() => !document.getElementById('loading') && ![...document.querySelectorAll('.msg')].some(m => document.body.contains(m) && /Baking|Compiling|Drawing the first/.test(m.textContent)), null, { timeout: 0, polling: 1000 });
await page.evaluate(F0 => {
  SFO.qa.hideUI(true);
  const hide = el => { if (el) el.style.setProperty('display', 'none', 'important'); };
  hide(document.getElementById('replay-banner'));
  const g = document.getElementById('pt-gpu'); if (g) { let e = g; while (e.parentElement && e.parentElement !== document.body) e = e.parentElement; hide(e); }
  window.__sm = {};
  // recording time (s after F0) of what the app DRAWS now: display time (the app's shifted clock, minus the display delay)
  // moved back by the replay shim's offset (payload now - dataNow)
  window.__simT = async () => { const j = await (await fetch('api/adsb')).json(); const off = j.now - j.dataNow; return (SFO.traffic.displayTime(Date.now()) - off) / 1000 - F0; };
  window.__cam = (c) => {
    const tr = SFO.traffic.tracks.get(c.hex); const D = tr && tr.disp; if (!D) return 'nodisp';
    const T = [D.x, D.y + c.up, D.z]; const s = window.__sm;
    const h = D.hdg * 57.29578; if (s.h == null) s.h = h; const dh = ((h - s.h + 540) % 360) - 180; s.h += dh * (1 - Math.exp(-c.dts / c.tau));
    if (c.type === 'chase') SFO.qa.look(T, s.h + c.yawOff, c.pitch, c.dist, c.fov);
    else if (c.type === 'orbit') SFO.qa.look(T, c.yaw, c.pitch, c.dist, c.fov);
    else if (c.type === 'spot') { const P = c.pos; const d = [P[0] - T[0], P[1] - T[1], P[2] - T[2]]; const dist = Math.hypot(d[0], d[1], d[2]);
      // (frame: metres of view height at the aircraft -- a spotter's zoom lens; else the fixed fov)
      const fov = c.frame ? Math.min(60, Math.max(1.5, 2 * Math.atan(c.frame / 2 / dist) * 57.29578)) : c.fov;
      SFO.qa.look(T, Math.atan2(d[0], -d[2]) * 57.29578, Math.asin(d[1] / dist) * 57.29578, dist, fov); }
    return [tr.phase, Math.round(D.x), Math.round(D.y), Math.round(D.z), tr.gate ? tr.gate.name : '-'].join(' ');
  };
}, F0);
console.log('ready', ((Date.now() - t0) / 1000).toFixed(1), 's');
console.log('fx', JSON.stringify(await page.evaluate(() => { const R = window.SFO && SFO.R; if (!R) return null; const Q = R.Q || {}; const e = R.engine || {};
  return { tier: R.tier, backend: e.backend, ao: Q.ao, traa: Q.traa, bloom: Q.bloom, shadow: Q.shadow, spotMap: Q.spotMap, lod: Q.lod, gb: R.qsGB, canvas: R.canvas && (R.canvas.width + 'x' + R.canvas.height) }; })));
// real-time warm-up until the drawn aircraft is ~24 s short of the shot's start
let simT = await page.evaluate(() => window.__simT()); console.log('simT at ready', simT.toFixed(1), 'start', sh.start);
if (simT > sh.start - 2) { console.log('LATE', simT.toFixed(1)); await browser.close(); process.exit(6); }
// (stop 24 s short: pausing the virtual clock needs a 4-16 s margin (pauseAt retries below) during which the replay runs on;
// with the old 6 s every shot began 0-16 s late (d_climb 16, a_taxi 12: 13 Nov 2026); the 250-ms step loop then lands on start)
while (simT < sh.start - 24) { await page.waitForTimeout(Math.min(4000, Math.max(300, (sh.start - 24 - simT) * 800))); simT = await page.evaluate(() => window.__simT()); }
const flush = c => page.evaluate(c => { const r = window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t); return r; }, c);
await page.evaluate(() => { window.__q = []; window.requestAnimationFrame = cb => { window.__q.push(cb); return window.__q.length; }; window.cancelAnimationFrame = () => {}; });
await page.waitForFunction(() => window.__q.length > 0, null, { timeout: 0, polling: 200 });
for (let m = 4000; ; m *= 2) { try { await page.clock.pauseAt(await page.evaluate(() => Date.now()) + m); break; } catch (e) { if (m > 60000) throw e; console.log('pauseAt retry', m); } }
await page.setViewportSize({ width: W, height: H });
for (let i = 0; i < 4; i++) { await flush(cam(0)); await page.clock.runFor(250); }
const busy = () => page.evaluate(() => !!document.getElementById('loading') || [...document.querySelectorAll('.msg')].some(m => document.body.contains(m) && !m.closest('.done') && /Baking|Compiling|Drawing the first/.test(m.textContent)));
for (let k = 0; k < 90 && await busy(); k++) { await page.waitForTimeout(800); await page.clock.runFor(40); await flush(cam(0)); }
console.log('overlay', (await busy()) ? 'STILL UP' : 'clear');
// step (250 ms) to the exact start, then settle the temporal filters with a few frames at the shot's own rate
simT = await page.evaluate(() => window.__simT());
for (let k = 0; k < 200 && simT < sh.start - 8 * SPEED / FPS; k++) { await page.clock.runFor(250); await flush(cam(0)); simT = await page.evaluate(() => window.__simT()); }
for (let k = 0; k < 8; k++) { await page.clock.runFor(dt); await flush(cam(0)); }
console.log('start at simT', (await page.evaluate(() => window.__simT())).toFixed(2), 'state', await flush(cam(0)));
const grab = (c) => page.evaluate(c => { const r = window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t);
  if (/graphics device was lost/i.test(document.body.innerText)) return 'LOST';
  const cv = [...document.querySelectorAll('canvas')].sort((x, y) => y.width * y.height - x.width * x.height)[0];
  return r + '|' + cv.width + 'x' + cv.height + '|' + cv.toDataURL(window.__png ? 'image/png' : 'image/png'); }, c);
if (PREVIEW) {
  const us = [0, 0.25, 0.5, 0.75, 1]; let iPrev = 0;
  for (const u of us) { const i = Math.round(u * (N - 1)); for (let k = iPrev; k < i; k++) { await page.clock.runFor(dt); if ((k - iPrev) % 6 === 5) await flush(cam(k / (N - 1))); } iPrev = i;
    const d = await grab(cam(u)); if (d === 'LOST') { console.log('LOST in preview'); break; }
    const [st, sz, durl] = d.split('|'); fs.writeFileSync(`${OUT}/prev_${ID}_${Math.round(u * 100)}.png`, Buffer.from(durl.slice(durl.indexOf(',') + 1), 'base64'));
    console.log('preview', ID, u, 'simT', (await page.evaluate(() => window.__simT())).toFixed(1), st); }
  await browser.close(); process.exit(0);
}
const part = `${OUT}/shot_${ID}.part.mp4`;
const ff = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', part], { stdio: ['pipe', 'inherit', 'inherit'] });
const tr0 = Date.now(); let N_DONE = N;
for (let i = 0; i < N; i++) {
  const u = N > 1 ? i / (N - 1) : 0;
  await page.clock.runFor(dt);
  const d = await grab(cam(u));
  if (d === 'LOST' && i >= 96) { console.log('PARTIAL', ID, 'context lost at frame', i, '- keeping', i, 'frames'); N_DONE = i; break; }
  if (d === 'LOST') throw new Error('WebGL context lost at frame ' + i);
  const [st, sz, durl] = d.split('|'); if (sz !== `${W}x${H}`) throw new Error('canvas size ' + sz);
  const buf = Buffer.from(durl.slice(durl.indexOf(',') + 1), 'base64');
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i === 0 || i === Math.floor(N / 2) || i === N - 1) fs.writeFileSync(`${OUT}/still_${ID}_${i === 0 ? 'a' : i === N - 1 ? 'c' : 'b'}.jpg`, buf);
  if (i % 48 === 0) console.log(ID, 'frame', i, '/', N, ((Date.now() - tr0) / 1000 / (i + 1)).toFixed(1), 's/frame', st);
}
ff.stdin.end(); await new Promise(r => ff.on('close', r));
fs.renameSync(part, `${OUT}/shot_${ID}.mp4`);
fs.writeFileSync(`${OUT}/shot_${ID}.json`, JSON.stringify({ id: ID, frames: N_DONE, start: sh.start, speed: SPEED }));
console.log('DONE', ID, N_DONE, 'frames', ((Date.now() - tr0) / 1000).toFixed(0), 's');
await browser.close();

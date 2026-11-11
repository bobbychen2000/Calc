// one shot of the long video (spec in SHOTS_JSON): Full build on :8771, Xvfb + Mesa llvmpipe, virtual clock + manual rAF,
// replay start trimmed per shot (route data/replay.wasm), canvas capture into ffmpeg, atomic output
import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
import { spawn } from 'child_process'; import fs from 'fs';
const ID = process.argv[2], OUT = process.env.OUT, FPS = 24, W = +(process.env.W || 1920), H = +(process.env.H || 1080), Q = process.env.Q || 'ultra';
const sh = JSON.parse(fs.readFileSync(process.env.SHOTS_JSON, 'utf8')).find(s => s.id === ID); if (!sh) { console.log('unknown shot', ID); process.exit(2); }
const N = process.env.NF ? +process.env.NF : (sh.n || 168);
const lin = (a, b, u) => a + (b - a) * u, ease = u => u * u * (3 - 2 * u);
const L = (r, u, e = true) => Array.isArray(r) ? lin(r[0], r[1], e ? ease(u) : u) : r;
const RW = { '28L': { thr: [1426.1, 744.5], dir: [-0.885, -0.466] }, '28R': { thr: [1532.7, 542.3], dir: [-0.885, -0.466] },
  '1L': { thr: [-572.3, 1037.8], dir: [0.466, -0.885] }, '1R': { thr: [-417.0, 1233.7], dir: [0.466, -0.885] } };
function cam(u, S) {
  if (sh.kind === 'orbit') return { type: 'orbit', t: S.T, yaw: L(sh.yaw, u), pitch: L(sh.pitch, u, false), dist: L(sh.dist, u), fov: sh.fov || 48 };
  if (sh.kind === 'gate') return { type: 'orbit', t: S.g.t, yaw: S.g.yaw + L([-12, 10], u), pitch: S.g.pitch + 13, dist: S.g.dist * L([1.95, 1.6], u), fov: 50 };
  return { type: 'chase', hex: S.hex, yawOff: L(sh.yawOff, u), pitch: L(sh.pitch, u, false), dist: L(sh.dist, u), up: 3, fov: sh.fov || 40 };
}
const browser = await chromium.launch({ headless: !process.env.XGL, args: [...(process.env.XGL ? ['--use-gl=angle', '--use-angle=gl'] : ['--use-gl=angle', '--use-angle=gl-egl']), '--ignore-gpu-blocklist', '--disable-gpu-watchdog', '--js-flags=--max-old-space-size=5000', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'],
  env: { ...process.env, LIBGL_ALWAYS_SOFTWARE: '1', GALLIUM_DRIVER: 'llvmpipe', LP_NUM_THREADS: '4' } });
const page = await browser.newPage({ viewport: { width: 640, height: 360 }, deviceScaleFactor: 1 });
// liveries at the high tier's 'auto' resolution (1024 px; 2048 only where a model needs it): the 2048 px set on every
// aircraft pushes Chromium's software-GL GPU process past the session's 14.3 GB memory cap (OOM-killed mid-shot)
await page.addInitScript({ content: `window.SFO_LIVERY_RES = ${JSON.stringify(process.env.LIV || 'auto')};` });
page.on('pageerror', e => console.log('PAGEERR', String(e).slice(0, 200)));
if (sh.off) await page.route('**/replay.wasm', r => r.fulfill({ path: `${process.env.REPLAYS}/replay_${sh.off}.gz`, contentType: 'application/wasm' }));
await page.clock.install();
const t0 = Date.now();
await page.goto(`http://127.0.0.1:8771/sfo_phone_test.html?quality=${sh.q || Q}&fixedres=1` + (sh.t ? `&t=${sh.t}` : '') + (sh.metar ? `&metar=${encodeURIComponent(sh.metar)}` : '') + (sh.expo ? `&expo=${sh.expo}` : ''));
await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0, polling: 500 });
const err = await page.evaluate(() => window.__sfoError || null); if (err) { console.log('APPERR', err.slice(0, 300)); process.exit(3); }
await page.waitForFunction(() => !document.getElementById('loading') && ![...document.querySelectorAll('.msg')].some(m => document.body.contains(m) && /Baking|Compiling|Drawing the first/.test(m.textContent)), null, { timeout: 0, polling: 1000 });
await page.evaluate(RWs => {
  SFO.qa.hideUI(true);
  const hide = el => { if (el) el.style.setProperty('display', 'none', 'important'); };
  hide(document.getElementById('replay-banner'));
  const g = document.getElementById('pt-gpu'); if (g) { let e = g; while (e.parentElement && e.parentElement !== document.body) e = e.parentElement; hide(e); }
  window.__RW = RWs; window.__sm = {};
  window.__cam = (c) => {
    if (c.type === 'orbit') return SFO.qa.look(c.t, c.yaw, c.pitch, c.dist, c.fov);
    const tr = SFO.traffic.tracks.get(c.hex); const D = tr && tr.disp; if (!D) return;
    const T = [D.x, D.y + (c.up || 0), D.z];
    const h = D.hdg * 57.29578; const s = window.__sm; if (s.h == null) s.h = h; const dh = ((h - s.h + 540) % 360) - 180; s.h += dh * 0.08;
    return SFO.qa.look(T, s.h + c.yawOff, c.pitch, c.dist, c.fov);
  };
  window.__target = (tg, ty) => {
    const tw = SFO.world.towerPos; const y = ty == null ? 3 : ty;
    if (Array.isArray(tg)) return tg;
    if (tg === 'tower') return [tw[0], y, tw[2]];
    if (tg === 'rw28t') { const a = RWs['28L'], b = RWs['28R']; return [(a.thr[0] + b.thr[0]) / 2, y, (a.thr[1] + b.thr[1]) / 2]; }
    if (tg === 'rw28') { const a = RWs['28L'], b = RWs['28R']; return [(a.thr[0] + b.thr[0]) / 2 + a.dir[0] * 1400, y, (a.thr[1] + b.thr[1]) / 2 + a.dir[1] * 1400]; }
    const re = tg === 'hub' ? /^[A-G]\d/ : new RegExp('^(' + tg.slice(6) + ')\\d');
    const pts = []; for (const g of SFO.world.gates) if (re.test(g.name) && SFO.qa.gate(g.name, 60, 1, 10)) pts.push(SFO.rig.target.slice());
    if (!pts.length) return [tw[0], y, tw[2]];
    const c = [0, 0, 0]; for (const p of pts) for (let i = 0; i < 3; i++) c[i] += p[i] / pts.length; c[1] = y; return c;
  };
  window.__find = (kind) => {
    const trs = [...SFO.traffic.tracks.values()].filter(t => t.disp && t.phase !== 'vehicle');
    const prev = window.__prevPos || {}; const now = Date.now(); const out = []; window.__prevPos = {};
    for (const t of trs) { const D = t.disp; window.__prevPos[t.hex] = [D.x, D.z, now];
      const p = prev[t.hex]; const spd = p && now > p[2] ? Math.hypot(D.x - p[0], D.z - p[1]) / ((now - p[2]) / 1000) : null;
      if (kind === 'arrival' && !D.ground) for (const k of ['28L', '28R']) { const r = RWs[k]; const v = [D.x - r.thr[0], D.z - r.thr[1]];
        const along = -(v[0] * r.dir[0] + v[1] * r.dir[1]), lat = Math.abs(v[0] * r.dir[1] - v[1] * r.dir[0]);
        if (along > 500 && along < 1100 && lat < 90 && D.y < 140) out.push({ hex: t.hex, rw: k, along: Math.round(along), f: t.info.flight, icao: t.info.icao }); }
      if (kind === 'taxi' && D.ground && t.phase === 'taxi' && t.info.icao && spd != null && spd > 6 && spd < 18) out.push({ hex: t.hex, spd: +spd.toFixed(1), f: t.info.flight, icao: t.info.icao });
      if (kind === 'takeoff' && D.ground && t.phase === 'takeoff' && spd != null && spd > 8 && spd < 40) for (const k of ['1L', '1R']) { const r = RWs[k]; const v = [D.x - r.thr[0], D.z - r.thr[1]];
        const along = v[0] * r.dir[0] + v[1] * r.dir[1], lat = Math.abs(v[0] * r.dir[1] - v[1] * r.dir[0]); if (lat < 40 && along > -50 && along < 600) out.push({ hex: t.hex, rw: k, spd: +spd.toFixed(1), f: t.info.flight, icao: t.info.icao }); }
    }
    return out;
  };
}, RW);
const S = {};
console.log('ready', ((Date.now() - t0) / 1000).toFixed(1), 's');
console.log('fx', JSON.stringify(await page.evaluate(() => { const R = window.SFO && SFO.R; if (!R) return null; const Q = R.Q || {}; const e = R.engine || {};
  return { tier: R.tier, backend: e.backend, ao: Q.ao, traa: Q.traa, bloom: Q.bloom, shadow: Q.shadow, cascades: Q.cascades, spotMap: Q.spotMap, floodSpots: Q.floodSpots, aniso: Q.aniso, lod: Q.lod, ssrOff: new URLSearchParams(location.search).get('ssr') === '0', gb: R.qsGB, ae: R.aeMode, lite: !!R.lite, canvas: R.canvas && (R.canvas.width + 'x' + R.canvas.height), dpr: devicePixelRatio }; })));
await page.waitForTimeout(12000);
const wide = /B77|B78|A35|A33|B74|A38|B76|MD11|A34/;
if (sh.kind === 'chase') {
  const t1 = Date.now(); let hit = null;
  while (!hit && (Date.now() - t1) / 1000 < 480) { await page.waitForTimeout(700); const c = await page.evaluate(k => window.__find(k), sh.wait); if (c.length) hit = c.find(x => wide.test(x.icao || '')) || c.find(x => /^(B7|A3|A2|B3|E7|E1|BCS|CRJ|MD)/.test(x.icao || '')) || null; }
  if (!hit) { console.log('NOEVENT', sh.wait); await browser.close(); process.exit(4); }
  Object.assign(S, hit); console.log('event', JSON.stringify(hit), 'after', ((Date.now() - t1) / 1000).toFixed(0), 's');
} else if (sh.kind === 'gate') {
  const occ = await page.evaluate(() => [...SFO.traffic.tracks.values()].filter(t => t.phase === 'gate' && t.gate).map(t => ({ g: t.gate.name, icao: t.info.icao || '', f: t.info.flight })));
  const re = new RegExp('^(' + sh.gate + ')\\d'); const mine = occ.filter(o => re.test(o.g));
  const pick = (sh.heavy && mine.find(o => wide.test(o.icao))) || mine.find(o => /B7|A3|B3|A2|E7|BCS/.test(o.icao)) || mine[0] || occ[0];
  if (!pick) { console.log('NOGATE'); process.exit(5); }
  S.g = await page.evaluate(n => { SFO.qa.gate(n, 60, 1, 10); const r = SFO.rig; return { t: r.target.slice(), yaw: r.yaw * 57.29578, pitch: r.pitch * 57.29578, dist: r.dist }; }, pick.g);
  console.log('gate', JSON.stringify(pick));
} else { S.T = await page.evaluate(([tg, ty]) => window.__target(tg, ty), [sh.target, sh.ty]); console.log('target', JSON.stringify(S.T.map(v => Math.round(v)))); }
const flush = c => page.evaluate(c => { window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t); }, c);
await page.evaluate(() => { window.__q = []; window.requestAnimationFrame = cb => { window.__q.push(cb); return window.__q.length; }; window.cancelAnimationFrame = () => {}; });
await page.waitForFunction(() => window.__q.length > 0, null, { timeout: 0, polling: 200 });
await page.clock.pauseAt(await page.evaluate(() => Date.now()) + 3000);
await page.setViewportSize({ width: W, height: H });
const dt = 1000 / FPS;
for (let i = 0; i < 4; i++) { await flush(cam(0, S)); await page.clock.runFor(dt); }
const busy = () => page.evaluate(() => !!document.getElementById('loading') || [...document.querySelectorAll('.msg')].some(m => document.body.contains(m) && !m.closest('.done') && /Baking|Compiling|Drawing the first/.test(m.textContent)));
for (let k = 0; k < 90 && await busy(); k++) { await page.waitForTimeout(800); await page.clock.runFor(dt); await flush(cam(0, S)); }
console.log('overlay', (await busy()) ? 'STILL UP' : 'clear');
for (let k = 0; k < 2; k++) { await page.clock.runFor(dt); await flush(cam(0, S)); }
const part = `${OUT}/shot_${ID}.part.mp4`;
const ff = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', part], { stdio: ['pipe', 'inherit', 'inherit'] });
const tr0 = Date.now(); let N_DONE = N;
for (let i = 0; i < N; i++) {
  const u = N > 1 ? i / (N - 1) : 0;
  await page.clock.runFor(dt);
  const d = await page.evaluate(c => { window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t);
    if (/graphics device was lost/i.test(document.body.innerText)) return 'LOST';
    const cv = [...document.querySelectorAll('canvas')].sort((x, y) => y.width * y.height - x.width * x.height)[0];
    return cv.width + 'x' + cv.height + '|' + cv.toDataURL('image/png'); }, cam(u, S));
  if (d === 'LOST' && i >= 72) { console.log('PARTIAL', ID, 'context lost at frame', i, '- keeping', i, 'frames'); N_DONE = i; break; }
  if (d === 'LOST') throw new Error('WebGL context lost at frame ' + i);
  const [sz, durl] = d.split('|'); if (sz !== `${W}x${H}` && !process.env.NF) throw new Error('canvas size ' + sz);
  const buf = Buffer.from(durl.slice(durl.indexOf(',') + 1), 'base64');
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i === 0 || i === Math.floor(N / 2) || i === N - 1) fs.writeFileSync(`${OUT}/still_${ID}_${i === 0 ? 'a' : i === N - 1 ? 'c' : 'b'}.jpg`, buf);
  if (i % 24 === 0) console.log(ID, 'frame', i, '/', N, ((Date.now() - tr0) / 1000 / (i + 1)).toFixed(1), 's/frame');
}
ff.stdin.end(); await new Promise(r => ff.on('close', r));
fs.renameSync(part, `${OUT}/shot_${ID}.mp4`);
console.log('DONE', ID, N_DONE, 'frames', ((Date.now() - tr0) / 1000).toFixed(0), 's');
await browser.close();

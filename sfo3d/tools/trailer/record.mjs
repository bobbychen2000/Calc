// one trailer shot: load the Full build, wait (natural time) for the shot's event, freeze time, step frames into ffmpeg
import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
import { spawn } from 'child_process'; import fs from 'fs';
const SHOT = process.argv[2], OUT = process.env.OUT, FPS = +(process.env.FPS || 24), W = +(process.env.W || 1920), H = +(process.env.H || 1080), Q = process.env.Q || 'high';
const NF = process.env.NF ? +process.env.NF : null;   // frame-count override (tests)
const T_GOLD = '2026-11-09T00:30:00Z', T_LATE = '2026-11-09T00:48:00Z', T_NIGHT = '2026-11-09T03:20:00Z';
const lin = (a, b, u) => a + (b - a) * u, ease = u => u * u * (3 - 2 * u);
// runway geometry (world, from qa.threshold: target = thr + dir*80)
const RW = { '28L': { thr: [1426.1, 744.5], dir: [-0.885, -0.466], side: 1 }, '28R': { thr: [1532.7, 542.3], dir: [-0.885, -0.466], side: -1 },
  '1L': { thr: [-572.3, 1037.8], dir: [0.466, -0.885], side: -1 }, '1R': { thr: [-417.0, 1233.7], dir: [0.466, -0.885], side: 1 } };
const SHOTS = {
  aerial: { t: T_GOLD, n: 156, cam: (u, S) => ({ type: 'orbit', t: [S.tower[0], 3, S.tower[2]], yaw: lin(212, 238, ease(u)), pitch: lin(23, 19, u), dist: lin(1750, 1420, ease(u)), fov: 50 }) },
  arrival: { t: T_GOLD, n: 156, wait: { kind: 'arrival', maxS: 420 }, cam: (u, S) => ({ type: 'chase', hex: S.hex, yawOff: lin(78, 112, ease(u)), pitch: lin(3, 6, u), dist: lin(95, 82, ease(u)), up: 3, fov: 40 }) },
  gates: { t: T_GOLD, n: 144, setup: 'gate', cam: (u, S) => ({ type: 'orbit', t: S.g.t, yaw: S.g.yaw + lin(-12, 10, ease(u)), pitch: S.g.pitch + 13, dist: lin(S.g.dist * 1.95, S.g.dist * 1.6, ease(u)), fov: 50 }) },
  taxi: { t: T_GOLD, n: 144, wait: { kind: 'taxi', maxS: 240 }, cam: (u, S) => ({ type: 'chase', hex: S.hex, yawOff: lin(140, 160, u), pitch: 9, dist: 85, up: 4, fov: 42 }) },
  tower: { t: T_LATE, n: 144, cam: (u, S) => ({ type: 'orbit', t: [S.tower[0], 44, S.tower[2]], yaw: lin(198, 238, ease(u)), pitch: lin(3, 8, u), dist: lin(150, 115, ease(u)), fov: 42 }) },
  night: { t: '2026-11-09T01:32:00Z', n: 156, cam: (u, S) => ({ type: 'orbit', t: [S.tower[0] - 150, 3, S.tower[2] + 120], yaw: lin(208, 232, ease(u)), pitch: lin(21, 17, u), dist: lin(950, 760, ease(u)), fov: 48 }) },
  takeoff: { t: T_LATE, n: 168, wait: { kind: 'takeoff', maxS: 600 }, cam: (u, S) => ({ type: 'chase', hex: S.hex, yawOff: lin(105, 150, ease(u)), pitch: lin(4, 7, u), dist: lin(105, 135, ease(u)), up: 3, fov: 40 }) },
};
const sh = SHOTS[SHOT]; if (!sh) { console.log('unknown shot'); process.exit(2); }
const browser = await chromium.launch({ headless: !process.env.XGL, args: [...(process.env.XGL ? ['--use-gl=angle', '--use-angle=gl'] : ['--use-gl=angle', '--use-angle=gl-egl']), '--ignore-gpu-blocklist', '--disable-gpu-watchdog', '--js-flags=--max-old-space-size=5000', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'],
  env: { ...process.env, LIBGL_ALWAYS_SOFTWARE: '1', GALLIUM_DRIVER: 'llvmpipe', LP_NUM_THREADS: '4' } });
const page = await browser.newPage({ viewport: { width: 640, height: 360 }, deviceScaleFactor: 1 });   // small while waiting: faster natural frames
page.on('pageerror', e => console.log('PAGEERR', String(e).slice(0, 200)));
await page.clock.install();
const t0 = Date.now();
await page.goto(`http://127.0.0.1:8771/sfo_phone_test.html?quality=${Q}&fixedres=1&t=${sh.t}`);
await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0, polling: 500 });
const err = await page.evaluate(() => window.__sfoError || null); if (err) { console.log('APPERR', err); process.exit(3); }
await page.waitForFunction(() => !document.getElementById('loading') && ![...document.querySelectorAll('.msg')].some(m => document.body.contains(m) && /Baking|Compiling|Drawing the first/.test(m.textContent)), null, { timeout: 0, polling: 1000 });
await page.evaluate(RWs => {
  SFO.qa.hideUI(true);
  const hide = el => { if (el) el.style.setProperty('display', 'none', 'important'); };
  hide(document.getElementById('replay-banner'));
  const g = document.getElementById('pt-gpu'); if (g) { let e = g; while (e.parentElement && e.parentElement !== document.body) e = e.parentElement; hide(e); }
  window.__RW = RWs; window.__sm = {};
  window.__cam = (c) => {
    const tr = c.hex ? SFO.traffic.tracks.get(c.hex) : null; const D = tr && tr.disp;
    if (c.type === 'orbit') return SFO.qa.look(c.t, c.yaw, c.pitch, c.dist, c.fov);
    if (!D) return;
    const T = [D.x, D.y + (c.up || 0), D.z];
    if (c.type === 'from') { const d = [c.C[0] - T[0], c.C[1] - T[1], c.C[2] - T[2]]; const L = Math.hypot(...d);
      return SFO.qa.look(T, Math.atan2(d[0], -d[2]) * 57.29578, Math.asin(d[1] / L) * 57.29578, L, c.fov); }
    if (c.type === 'chase') { const h = D.hdg * 57.29578; const s = window.__sm; if (s.h == null) s.h = h; let dh = ((h - s.h + 540) % 360) - 180; s.h += dh * 0.08;
      return SFO.qa.look(T, s.h + c.yawOff, c.pitch, c.dist, c.fov); }
  };
  // event finders (world coords; z = south, x = east)
  window.__find = (kind) => {
    const trs = [...SFO.traffic.tracks.values()].filter(t => t.disp && t.phase !== 'vehicle');
    const prev = window.__prevPos || {}; const now = Date.now(); const out = []; window.__prevPos = {};
    for (const t of trs) { const D = t.disp; window.__prevPos[t.hex] = [D.x, D.z, now];
      const p = prev[t.hex]; const spd = p && now > p[2] ? Math.hypot(D.x - p[0], D.z - p[1]) / ((now - p[2]) / 1000) : null;
      if (kind === 'arrival' && !D.ground) for (const k of ['28L', '28R']) { const r = window.__RW[k]; const v = [D.x - r.thr[0], D.z - r.thr[1]];
        const along = -(v[0] * r.dir[0] + v[1] * r.dir[1]), lat = Math.abs(v[0] * r.dir[1] - v[1] * r.dir[0]);
        if (along > 500 && along < 1100 && lat < 90 && D.y < 140) out.push({ hex: t.hex, rw: k, along: Math.round(along), f: t.info.flight, icao: t.info.icao }); }
      if (kind === 'taxi' && D.ground && t.phase === 'taxi' && t.info.icao && spd != null && spd > 6 && spd < 18) out.push({ hex: t.hex, spd: +spd.toFixed(1), f: t.info.flight, icao: t.info.icao });
      if (kind === 'takeoff' && D.ground && t.phase === 'takeoff' && spd != null && spd > 8 && spd < 40) for (const k of ['1L', '1R']) { const r = window.__RW[k]; const v = [D.x - r.thr[0], D.z - r.thr[1]];
        const along = v[0] * r.dir[0] + v[1] * r.dir[1], lat = Math.abs(v[0] * r.dir[1] - v[1] * r.dir[0]); if (lat < 40 && along > -50 && along < 600) out.push({ hex: t.hex, rw: k, spd: +spd.toFixed(1), f: t.info.flight, icao: t.info.icao }); }
    }
    return out;
  };
}, RW);
const S = { tower: await page.evaluate(() => SFO.world.towerPos) };
console.log('ready', ((Date.now() - t0) / 1000).toFixed(1), 's');
await page.waitForTimeout(15000);
if (sh.wait) {
  const t1 = Date.now(); let hit = null; const wide = /B77|B78|A35|A33|B74|A38|B76|MD11|A34/;
  while (!hit && (Date.now() - t1) / 1000 < sh.wait.maxS) {
    await page.waitForTimeout(700); const c = await page.evaluate(k => window.__find(k), sh.wait.kind);
    if (c.length) hit = c.find(x => wide.test(x.icao || '')) || c[0];
  }
  if (!hit) { console.log('NOEVENT', sh.wait.kind); await browser.close(); process.exit(4); }
  Object.assign(S, hit); console.log('event', JSON.stringify(hit), 'after', ((Date.now() - t1) / 1000).toFixed(0), 's');
}
if (sh.setup === 'gate') {
  const occ = await page.evaluate(() => [...SFO.traffic.tracks.values()].filter(t => t.phase === 'gate' && t.gate).map(t => ({ g: t.gate.name, icao: t.info.icao, f: t.info.flight })));
  const pick = occ.find(o => /^G|^A/.test(o.g) && /B77|B78|A35|A33|B74|A38/.test(o.icao || '')) || occ.find(o => /B77|B78|A35|A33|B74|A38|B75|B76|A32|B73|B3/.test(o.icao || '')) || occ[0];
  if (!pick) { console.log('NOGATE'); process.exit(5); }
  S.g = await page.evaluate(n => { SFO.qa.gate(n, 60, 1, 10); const r = SFO.rig; return { t: r.target.slice(), yaw: r.yaw * 57.29578, pitch: r.pitch * 57.29578, dist: r.dist }; }, pick.g);
  console.log('gate', JSON.stringify(pick), JSON.stringify(S.g));
}
// freeze: our rAF queue, then pause the virtual clock; full-size viewport for recording
await page.evaluate(() => { window.__q = []; window.requestAnimationFrame = cb => { window.__q.push(cb); return window.__q.length; }; window.cancelAnimationFrame = () => {}; });
await page.waitForFunction(() => window.__q.length > 0, null, { timeout: 0, polling: 200 });
await page.clock.pauseAt(await page.evaluate(() => Date.now()) + 3000);
await page.setViewportSize({ width: W, height: H });
const N = NF || sh.n; const dt = 1000 / FPS;
// two settle frames at the first camera (resize, shadow/AO history)
for (let i = 0; i < 4; i++) { await page.evaluate(c => { window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t); }, sh.cam(0, S)); await page.clock.runFor(dt); }
// the renderer re-shows its progress overlay after the resize: keep stepping (virtual time) until it is gone
const busy = () => page.evaluate(() => !!document.getElementById('loading') || [...document.querySelectorAll('.msg')].some(m => document.body.contains(m) && !m.closest('.done') && /Baking|Compiling|Drawing the first/.test(m.textContent)));
for (let k = 0; k < 90 && await busy(); k++) { await page.waitForTimeout(800); await page.clock.runFor(dt); await page.evaluate(c => { window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t); }, sh.cam(0, S)); }
console.log('overlay', (await busy()) ? 'STILL UP' : 'clear');
for (let k = 0; k < 2; k++) { await page.clock.runFor(dt); await page.evaluate(c => { window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t); }, sh.cam(0, S)); }
const ff = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', `${OUT}/shot_${SHOT}.part.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
const tr0 = Date.now();
for (let i = 0; i < N; i++) {
  const u = N > 1 ? i / (N - 1) : 0;
  await page.clock.runFor(dt);
  // render one frame and read the WebGL canvas in the same task (no compositor screenshot: less GPU-process growth)
  const d = await page.evaluate(c => { window.__cam(c); const q = window.__q; window.__q = []; const t = performance.now(); for (const cb of q) cb(t);
    if (/graphics device was lost/i.test(document.body.innerText)) return 'LOST';
    const cv = [...document.querySelectorAll('canvas')].sort((x, y) => y.width * y.height - x.width * x.height)[0];
    return cv.width + 'x' + cv.height + '|' + cv.toDataURL('image/png'); }, sh.cam(u, S));
  if (d === 'LOST') throw new Error('WebGL context lost at frame ' + i);
  const [sz, durl] = d.split('|'); if (sz !== `${W}x${H}`) throw new Error('canvas size ' + sz + ' at frame ' + i);
  const buf = Buffer.from(durl.slice(durl.indexOf(',') + 1), 'base64');
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i === 0 || i === Math.floor(N / 2) || i === N - 1) fs.writeFileSync(`${OUT}/still_${SHOT}_${i}.png`, buf);
  if (i % 12 === 0) console.log(SHOT, 'frame', i, '/', N, ((Date.now() - tr0) / 1000 / (i + 1)).toFixed(1), 's/frame');
}
ff.stdin.end(); await new Promise(r => ff.on('close', r));
fs.renameSync(`${OUT}/shot_${SHOT}.part.mp4`, `${OUT}/shot_${SHOT}.mp4`);
console.log('DONE', SHOT, N, 'frames', ((Date.now() - tr0) / 1000).toFixed(0), 's');
await browser.close();

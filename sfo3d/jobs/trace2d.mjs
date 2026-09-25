// Time series of the aircraft poses the app displays, for the moving-traffic physics audit (tools/drawing/trace_audit.py).
// Loads live.html in LIVE mode, so the harness's mock relay (livetest.mjs) feeds the recorded snapshot with simple
// kinematics (aircraft with ground speed move along their track; taxiing ones at 0.35 x speed), and samples every
// aircraft's displayed pose (the render matrix, model placement) every TRACE_DT seconds for TRACE_N samples.
// Run: SOFTGL=1 W=320 H=200 node livetest.mjs jobs/trace2d.mjs     -> out/draw/trace.json
import fs from 'fs'; import path from 'path';

export default async ({ page, base }) => {
  const OUTD = path.resolve(process.env.DRAW_OUT || 'out/draw'); fs.mkdirSync(OUTD, { recursive: true });
  const N = +(process.env.TRACE_N || 40), DT = +(process.env.TRACE_DT || 3);
  // the harness mock relay serves /api/adsb only; js/live/feed.js StreamFeed opens /api/stream (SSE) first and falls
  // back to polling only after 3 stream errors, but a 404 closes an EventSource after ONE error, so against the mock
  // live mode would receive no traffic at all. Hide EventSource so the app polls /api/adsb (what this trace tests is
  // the traffic engine + GroundPhysics, not the transport).
  await page.addInitScript(() => { try { delete window.EventSource; window.EventSource = undefined; } catch (e) { } });
  await page.goto(base + 'live.html?mode=live');
  // a module that 404s while another process rewrites the tree leaves the page waiting forever: name it, time out
  page.on('response', r => { if (r.status() >= 400 && r.url().startsWith(base)) console.log('HTTP', r.status(), r.url()); });
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: +(process.env.LOAD_TIMEOUT_MS || 1500000) });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.evaluate(async () => { const t0 = performance.now(); while (!SFO.traffic.tracks.size && performance.now() - t0 < 60000) await new Promise(r => setTimeout(r, 500)); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  const frames = [];
  for (let i = 0; i < N; i++) {
    await page.waitForTimeout(DT * 1000);
    const f = await page.evaluate(async () => {
      await Promise.all(SFO.scene.aircraft.map(a => a.ready));
      const out = [];
      for (const tr of SFO.traffic.tracks.values()) {
        const D = tr.disp; if (!D.valid || !D.ground) continue;
        const ac = SFO.scene.aircraft.find(a => a.id === tr.hex) || null;
        out.push({ hex: tr.hex, flight: tr.info.flight || null, icao: tr.info.icao || null, typeKey: tr.model ? tr.model.t : null, phase: tr.phase, gs: D.gs, stale: !!tr.stale, gate: tr.gate ? tr.gate.name : null,
          pos: [D.x, D.y, D.z], hdg: D.hdg, phys: tr.phys ? { key: tr.phys.key || null, off: tr.phys.off || null, cur: tr.phys.cur || null, ok: tr.phys.ok ?? null } : null,
          W: ac ? Array.from(ac.matrix()) : null, modelKeyUsed: ac ? ac.modelKey || null : null, stretch: ac ? ac.stretch || null : null, placement: ac && ac.model ? Array.from(ac.placement()) : null, rendered: ac ? (ac.model ? 'model' : 'procedural') : 'marker' });
      }
      return { t: Date.now(), physFrame: SFO.physics.frame, stats: SFO.physics.stats, aircraft: out };
    });
    frames.push(f);
    console.log('trace', i + 1, '/', N, 'ground aircraft', f.aircraft.length, 'physics frame', f.physFrame, JSON.stringify(f.stats));
  }
  const frameId = await page.evaluate(async () => (await import(new URL('js/geo.js', location.href).href)).FRAME_ID || 'equirect-v1');
  let git = null; try { git = (await import('child_process')).execSync('git rev-parse --short HEAD', { cwd: path.dirname(new URL(import.meta.url).pathname) }).toString().trim(); } catch (e) { }
  fs.writeFileSync(path.join(OUTD, 'trace.json'), JSON.stringify({ mode: 'live (mock relay polled at /api/adsb: recorded snapshot + straight-line kinematics)', frameId, git, generated: new Date().toISOString(), dt: DT, frames }));
  if (!frames.some(f => f.aircraft.length)) console.log('WARNING: no ground aircraft in any frame - the feed delivered nothing');
  console.log('trace.json:', frames.length, 'frames');
};

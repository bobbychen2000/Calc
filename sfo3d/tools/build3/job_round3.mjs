// livetest.mjs job: review-round-3 verification of live3.html in ONE page load (llvmpipe minutes per frame: keep it to
// one load). Same views as the round-3 reviewer (gate B20 130/1/24, UAL B39M a12a82 at D10 38 m / pitch 6, overview),
// plus: the close-up after 8 and 32 frames and during a 3 deg/frame orbit (AO grain), the light sprites without their
// occlusion test (nav lights), night with and without the floodlight spots (spot A/B), dusk.
//   SOFTGL=1 LP_NUM_THREADS=3 W=960 H=540 OUT=out/engine_r3 PAGE="live3.html?tier=high" node livetest.mjs tools/build3/job_round3.mjs
// Writes OUT/round3.json (start-up, console errors, debugInfo per view, mast layer check, nav-light probe).
// SHORT=1: day gate + close-up and night gate only (e.g. PAGE="live3.html?tier=low").
import fs from 'fs'; import path from 'path';
export default async ({ page, shot, base, OUT }) => {
  const res = { err: [], pageerr: [], views: {} }; const save = () => fs.writeFileSync(path.join(OUT, 'round3.json'), JSON.stringify(res, null, 1));
  page.on('console', m => { const s = m.text().slice(0, 300); if (/GPU stall|GL Driver|Automatic fallback/.test(s)) return; if (m.type() === 'error') res.err.push(s); });
  page.on('pageerror', e => res.pageerr.push(String(e.message).slice(0, 300)));
  const pg = process.env.PAGE || 'live3.html'; const P = process.env.PREFIX || 'r3'; const t0 = Date.now();
  await page.goto(base + pg + (pg.includes('?') ? '&' : '?') + (process.env.QS || 'mode=snapshot&res=1'));
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0, polling: 1000 });
  const fatal = await page.evaluate(() => window.__sfoError); if (fatal) { res.fatal = fatal; save(); return; }
  await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2, null, { timeout: 0, polling: 1000 });
  res.readyS = (Date.now() - t0) / 1000;
  res.start = await page.evaluate(() => {
    const R = SFO.R, E = R.engine; let mastMeshes = 0, mastLayerMeshes = 0;
    E.scene.traverse(o => { if (o.isMesh && o.layers.mask === (1 << 2)) mastLayerMeshes++; });
    const spotMasks = E.spots.map(s => s.shadow.camera.layers.mask);
    return { backend: E.backend, tier: R.tier, aoDenoise: !!E.aoDen, mastLayerMeshes, spotMasks, debug: R.debugInfo(),
      tracks: SFO.traffic.tracks.size, aircraft: SFO.scene.aircraft.length, occupied: SFO.qa.gatesOccupied().length };
  });
  console.log('ready', res.readyS, JSON.stringify(res.start)); save();
  const frames = async (n) => { const f0 = await page.evaluate(() => SFO.R.frames); await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 300 }); };
  const view = async (v) => page.evaluate((v) => {
    const q = SFO.qa;
    if (v[0] === 'overview') { SFO.view('overview'); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); return true; }
    if (v[0] === 'gate') return q.gate(v[1], v[2], v[3], v[4]);
    if (v[0] === 'ac') return q.aircraft(v[1], v[2], v[3], v[4]);
    return false;
  }, v);
  const snap = async (name, n = 8) => { const tv = Date.now(); await frames(n); res.views[name] = { s: (Date.now() - tv) / 1000, debug: await page.evaluate(() => SFO.R.debugInfo()) }; await shot(`${P}_${name}`); save(); console.log(name, res.views[name].s, 's'); };
  // nav-light probe: the close-up aircraft's sprites projected to the screen (which ones fall inside the frame)
  const probe = async (hex) => page.evaluate((hex) => {
    const ac = SFO.scene.aircraft.find(a => a.id === hex || (a.track && a.track.hex === hex)); if (!ac) return { found: false, ids: SFO.scene.aircraft.slice(0, 5).map(a => a.id) };
    const E = SFO.R.engine, cam = E.camera; const sp = ac.lightSprites(performance.now() / 1000) || [];
    const W = SFO.R.W, H = SFO.R.H; const out = [];
    for (const s of sp) { const v = cam.position.clone(); v.set(s.p[0], s.p[1], s.p[2]); v.project(cam); out.push({ p: s.p.map(x => +x.toFixed(2)), c: s.c, i: s.i, s: s.s, k: s.k, px: [Math.round((v.x * 0.5 + 0.5) * W), Math.round((0.5 - v.y * 0.5) * H)], inView: Math.abs(v.x) < 1 && Math.abs(v.y) < 1 && v.z < 1 }); }
    return { found: true, n: sp.length, sprites: out };
  }, hex);
  // ---------------------------------------------------------------- day
  const SHORT = !!process.env.SHORT;
  if (!SHORT) { await view(['overview']); await snap('day_overview'); }
  await view(['gate', 'B20', 130, 1, 24]); await snap('day_gate_B20');
  await view(['ac', 'a12a82', 38, null, 6]); await snap('day_ac8', 8);
  if (SHORT) { await page.evaluate(() => SFO.setLight('night')); await page.waitForFunction(() => !SFO.R.bakes || !SFO.R.bakes.pending, null, { timeout: 0, polling: 500 }); await frames(2);
    await view(['gate', 'B20', 130, 1, 24]); await snap('night_gate_B20'); res.totalS = (Date.now() - t0) / 1000; save(); return; }
  await snap('day_ac32', 24);
  res.navDay = await probe('a12a82'); save();
  await page.evaluate(() => { SFO.R.sprites.depthOn.value = 0; }); await snap('day_ac_nodepth', 4); await page.evaluate(() => { SFO.R.sprites.depthOn.value = 1; });
  { // orbit 3 deg/frame (TRAA history resets: shimmer)
    const t = await page.evaluate(() => { const t = SFO.traffic.tracks.get('a12a82'); return t ? t.disp.hdg * 180 / Math.PI : null; });
    if (t != null) {
      for (let i = 1; i <= 12; i++) { await page.evaluate((y) => SFO.qa.aircraft('a12a82', 38, y, 6), t + 60 + 3 * i); await frames(1); }
      await shot(`${P}_day_ac_orbit`); res.views.day_ac_orbit = { yaw0: t + 60 }; save();
    }
  }
  // ---------------------------------------------------------------- dusk
  await page.evaluate(() => SFO.setLight('dusk')); await page.waitForFunction(() => !SFO.R.bakes || !SFO.R.bakes.pending, null, { timeout: 0, polling: 500 }); await frames(2);
  await view(['gate', 'B20', 130, 1, 24]); await snap('dusk_gate_B20');
  // ---------------------------------------------------------------- night: spot A/B
  await page.evaluate(() => SFO.setLight('night')); await page.waitForFunction(() => !SFO.R.bakes || !SFO.R.bakes.pending, null, { timeout: 0, polling: 500 }); await frames(2);
  await view(['gate', 'B20', 130, 1, 24]); await snap('night_gate_B20');
  await page.evaluate(() => { const R = SFO.R; R._fsSave = R._floodSpots; R._floodSpots = function () { this.engine.setFloodSpots([], 0, this.floodScale || 1); }; });
  await snap('night_gate_B20_nospots');
  await page.evaluate(() => { const R = SFO.R; R._floodSpots = R._fsSave; });
  await view(['ac', 'a12a82', 38, null, 6]); await snap('night_ac', 8);
  res.navNight = await probe('a12a82'); save();
  await page.evaluate(() => { SFO.R.sprites.depthOn.value = 0; }); await snap('night_ac_nodepth', 4); await page.evaluate(() => { SFO.R.sprites.depthOn.value = 1; });
  res.totalS = (Date.now() - t0) / 1000; save();
};

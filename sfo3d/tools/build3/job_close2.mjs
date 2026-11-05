// livetest.mjs job: engine close-out round 2 (5 Nov 2026) in ONE page load of live3.html (llvmpipe: minutes per load).
//   SOFTGL=1 LP_NUM_THREADS=3 W=960 H=540 OUT=out/engine_r3/close2 PAGE="live3.html?tier=high&glassab=1" \
//     node livetest.mjs tools/build3/job_close2.mjs
// 1. Curtain-wall glass at the reviewer's gate:B20,130,1,24 with the ?glassab=1 switches (renderer3 glassAB: x 1 = the
//    round-3 inputs, y / z / w = reflection / interior / frame weights; glassABOld = the round-3 hall illuminance):
//    old, old with the IBL ground set to the review's paved mean (the requested cause A/B), new, new per term.
//    Then a low view of the same facade (reflection crossing the horizon) and the overview.
// 2. Day close-up of the UAL B39M (a12a82, D10, 38 m, pitch 6): position lights by day (engine-v3).
// 3. Night gate B20 (night glass, spots), errors throughout. ULTRA=1 (PAGE ...tier=ultra): only steps 1 (old/new) + 2.
// Writes OUT/close2.json (debugInfo per view incl. groundAlb / apronAlb / kG / shadeK / hallLux, sun, errors).
import fs from 'fs'; import path from 'path';
export default async ({ page, shot, base, OUT }) => {
  const res = { err: [], pageerr: [], views: {} }; const save = () => fs.writeFileSync(path.join(OUT, 'close2.json'), JSON.stringify(res, null, 1));
  page.on('console', m => { const s = m.text().slice(0, 400); if (/GPU stall|GL Driver|Automatic fallback/.test(s)) return; if (m.type() === 'error') res.err.push(s); if (/three\.js r186|IBL ground|concrete mean/.test(s)) console.log('[page]', s); });
  page.on('pageerror', e => res.pageerr.push(String(e.message).slice(0, 400)));
  const pg = process.env.PAGE || 'live3.html?tier=high&glassab=1'; const P = process.env.PREFIX || 'c2'; const ULTRA = !!process.env.ULTRA; const t0 = Date.now();
  await page.goto(base + pg + (pg.includes('?') ? '&' : '?') + 'mode=snapshot&res=1');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0, polling: 1000 });
  const fatal = await page.evaluate(() => window.__sfoError); if (fatal) { res.fatal = fatal; save(); return; }
  await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2 && SFO.R.apronAlb, null, { timeout: 0, polling: 1000 });
  res.readyS = (Date.now() - t0) / 1000;
  res.start = await page.evaluate(() => { const R = SFO.R, E = R.engine; return { backend: E.backend, tier: R.tier, sunDir: R.light.sunDir, glassAB: !!R.glassAB, debug: R.debugInfo(), spotMap: E.spots.map(s => s.shadow.mapSize.x), sunMap: E.sun.shadow.mapSize.x, dpr: E.renderer.getPixelRatio() }; });
  console.log('ready', res.readyS, JSON.stringify(res.start).slice(0, 900)); save();
  const frames = async (n) => { const f0 = await page.evaluate(() => SFO.R.frames); await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 300 }); };
  const snap = async (name, n = 10) => { const tv = Date.now(); await frames(n); res.views[name] = { s: (Date.now() - tv) / 1000, debug: await page.evaluate(() => SFO.R.debugInfo()), nErr: res.err.length + res.pageerr.length }; await shot(`${P}_${name}`); save(); console.log(name, res.views[name].s, 's'); };
  const setAB = (ab, old, ground) => page.evaluate(([ab, old, ground]) => { const R = SFO.R; if (!R.glassAB) return false; R.glassAB.value.set(...ab); R.glassABOld = old; if (ground !== undefined) R.setIBLGround(ground); return true; }, [ab, old, ground]);
  const setLight = async (k) => { await page.evaluate((k) => SFO.setLight(k), k); await page.waitForFunction(() => !SFO.R.bakes || !SFO.R.bakes.pending, null, { timeout: 0, polling: 500 }); await frames(2); };
  // 1. glass
  await page.evaluate(() => SFO.qa.gate('B20', 130, 1, 24));
  const PAVED = [0.38, 0.37, 0.345];
  const glassSet = ULTRA ? [['old', [1, 1, 1, 1], true, null], ['new', [0, 1, 1, 1], false, null]] : [
    ['old', [1, 1, 1, 1], true, null], ['old_paved', [1, 1, 1, 1], true, PAVED], ['new_paved', [0, 1, 1, 1], false, PAVED],
    ['new', [0, 1, 1, 1], false, null], ['new_refl', [0, 1, 0, 0], false, null], ['new_hall', [0, 0, 1, 0], false, null], ['new_frame', [0, 0, 0, 1], false, null],
    ['old_refl', [1, 1, 0, 0], true, null], ['old_frame', [1, 0, 0, 1], true, null]];
  for (const [name, ab, old, ground] of glassSet) { if (!res.start.glassAB && name !== 'new') continue; await setAB(ab, old, ground); await snap('gate_B20_' + name); }
  await setAB([0, 1, 1, 1], false, null);
  if (!ULTRA) {
    await page.evaluate(() => SFO.qa.gate('B20', 70, 1, 6)); await snap('gate_B20_low_new');
    await setAB([1, 1, 1, 1], true); await snap('gate_B20_low_old'); await setAB([0, 1, 1, 1], false);
  }
  // 2. close-up, position lights by day
  await page.evaluate(() => SFO.qa.aircraft('a12a82', 38, null, 6)); await snap('day_ac8', 10);
  res.navProbe = await page.evaluate(() => { const ac = SFO.scene.aircraft.find(a => a.id === 'a12a82'); const E = SFO.R.engine, cam = E.camera; const out = [];
    for (const s of (ac ? ac.lightSprites(performance.now() / 1000) : [])) { const v = cam.position.clone().set(s.p[0], s.p[1], s.p[2]).project(cam); out.push({ c: s.c, i: s.i, s: s.s, dir: !!s.dir, pos: SFO.R.sprites.constructor.isPositionLight(s), px: [Math.round((v.x * 0.5 + 0.5) * SFO.R.W), Math.round((0.5 - v.y * 0.5) * SFO.R.H)] }); }
    return { fixedK: SFO.R.sprites.fixedK, sprites: out }; });
  save();
  if (!ULTRA) {
    await page.evaluate(() => SFO.qa.gate('B20', 130, 1, 24)); await snap('overview_pre', 2); // (keeps the view jump out of the next one)
    await page.evaluate(() => { SFO.view('overview'); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); }); await snap('overview', 8);
    // 3. night
    await setLight('night');
    await page.evaluate(() => SFO.qa.gate('B20', 130, 1, 24)); await snap('night_gate_B20', 8);
    await setLight('day');
  }
  res.mem = await page.evaluate(() => { const I = SFO.R.engine.renderer.info; return { texMB: +((I.memory.texturesSize || 0) / 1048576).toFixed(1), textures: I.memory.textures, renderTargets: I.memory.renderTargets }; });
  res.totalS = (Date.now() - t0) / 1000; save();
};

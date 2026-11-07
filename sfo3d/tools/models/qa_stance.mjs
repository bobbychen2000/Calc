// aircraft track QA (4 Nov 2026 close-out; the 737 family's oleo-compressed stance since close-out round 3 of 7 Nov 2026):
// stance of the gear-carrying models (737 / 777) and the L1 bridge at a docked 737. Prints, per parked aircraft on its own
// gear, the pitch and the world height of the nose / main tyre bottoms MEASURED ON THE MESH the app draws: the model's
// vertices are decoded with the aircraft's own stretch (js/live/models.js modelPositions: the stretch, nose-leg change and
// oleo compression included) and put through the app's own matrix() x placement(); the nose tyre is the lowest gear vertex
// (zone 3) ahead of 0.3 L, the main tyre the lowest behind it (close-out round 3, aircraft-3: the old check computed the nose
// tyre from MODEL_FEATURES.contact minus noseExt.e, i.e. assumed what it should test). Then renders a side view of a 737's
// nose gear and the docked bridge at B13.
// Usage: SOFTGL=1 W=800 H=450 PREFIX=stance node livetest.mjs tools/models/qa_stance.mjs
export default async ({ page, shot, base }) => {
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  await page.evaluate(async () => { SFO.qa.hideUI(true); await new Promise(r => setTimeout(r, 2500)); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  const rep = await page.evaluate(async () => {
    const { modelPositions } = await import('./js/live/models.js');
    const { m4 } = await import('./js/math.js');
    const out = [];
    for (const ac of SFO.scene.aircraft) {
      if (!ac.model || !ac.model.dims.hasGear) continue;
      const M = await modelPositions(ac.modelKey, ac.stretch);
      const P = m4.mul(ac.matrix(), ac.placement()); const g = ac.pos[1], xs = -0.3 * M.dims.L;
      let nose = null, main = null, nosePos = null;
      for (let i = 0; i < M.nv; i++) {
        if (M.zone[i] !== 3) continue;
        const v = m4.xform(P, [M.pos[i * 3], M.pos[i * 3 + 1], M.pos[i * 3 + 2]]);
        if (M.pos[i * 3] > xs) { if (nose == null || v[1] < nose) { nose = v[1]; nosePos = v; } }
        else if (main == null || v[1] < main) main = v[1];
      }
      const p = ac.T.fit.pitch;
      out.push({ id: ac.id, type: ac.type, model: ac.modelKey, pitchDeg: p ? +(p.a * 180 / Math.PI).toFixed(2) : 0, seat: ac.T.fit.seat,
        noseTyre: nose != null ? +(nose - g).toFixed(3) : null, mainTyre: main != null ? +(main - g).toFixed(3) : null, nosePos, hdg: ac.fwd });
    }
    const gs = SFO.gateSys; const docked = [];
    for (const gg of gs.gates) if (gg.acType) for (const b of gs.bridgesOf(gg)) if (gs.docks(gg, b)) { const T = SFO.scene.aircraft.find(a => a.type === gg.acType); docked.push({ gate: gg.name, type: gg.acType, door: b.door || 1, sill: (b.door === 2 ? T && T.T.dockSill2 : T && T.T.dockSill), hw: (b.door === 2 ? T && T.T.dockHW2 : T && T.T.dockHW) }); }
    return { out, docked };
  });
  console.log('STANCE', JSON.stringify(rep.out));
  const bad = rep.out.filter(r => r.noseTyre == null || r.mainTyre == null || Math.abs(r.noseTyre) > 0.02 || Math.abs(r.mainTyre) > 0.02);
  console.log('STANCE_CHECK', bad.length ? 'FAIL ' + JSON.stringify(bad.map(r => [r.id, r.type, r.noseTyre, r.mainTyre])) : 'ok: ' + rep.out.length + ' aircraft on their own gear, both tyres within 0.02 m of the apron');
  console.log('DOCKED', JSON.stringify(rep.docked));
  const a = rep.out.find(r => /^b73|^b38|^b39/.test(r.type)) || rep.out[0];
  if (a && a.nosePos) {
    const n = a.nosePos; const h = Math.atan2(a.hdg[0], -a.hdg[2]) * 180 / Math.PI;   // heading of the nose (hdgVec convention)
    await page.evaluate(([n, yaw]) => SFO.qa.look([n[0], n[1] + 0.6, n[2]], yaw, 2, 11, 40), [n, h + 90]);
    await page.waitForTimeout(2500); await shot((process.env.PREFIX || 'stance') + '_nose_' + a.id);
  }
  if (await page.evaluate(() => SFO.qa.gate('B13', 26, 1, 8))) { await page.waitForTimeout(2500); await shot((process.env.PREFIX || 'stance') + '_gate_B13'); }
};

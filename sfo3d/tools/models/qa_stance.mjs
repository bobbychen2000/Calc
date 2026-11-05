// aircraft track QA (4 Nov 2026 close-out; 737 MAX nose-up stance on an extended nose leg since round 2 of 5 Nov): nose-down stance of the gear-carrying models (737 / 777) and the L1 bridge at
// a docked 737. Prints, per parked aircraft on its own gear, the pitch and the world height of the nose / main tyre bottom
// (model tyre contacts from data/models/manifest.js MODEL_FEATURES.contact through the app's own placement() matrix), then
// renders a side view of a 737's nose gear and the docked bridge at B13.
// Usage: SOFTGL=1 W=800 H=450 PREFIX=stance node livetest.mjs tools/models/qa_stance.mjs
export default async ({ page, shot, base }) => {
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  await page.evaluate(async () => { SFO.qa.hideUI(true); await new Promise(r => setTimeout(r, 2500)); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  const rep = await page.evaluate(async () => {
    const { MODEL_FEATURES } = await import('./data/models/manifest.js');
    const { m4 } = await import('./js/math.js');
    const out = [];
    for (const ac of SFO.scene.aircraft) {
      if (!ac.model || !ac.model.dims.hasGear) continue;
      const C = MODEL_FEATURES[ac.modelKey] && MODEL_FEATURES[ac.modelKey].contact; if (!C) continue;
      const st = ac.T.fit.stretch;   // (the nose gear is ahead of the fuselage plugs; the main contact after the plugs is pitch.x0)
      const P = m4.mul(ac.matrix(), ac.placement());
      const p = ac.T.fit.pitch; const mainX = p ? p.x0 : -C.main.st;
      const nose = m4.xform(P, [-C.nose.st, C.nose.y + ((st && st.gearUp) || 0) - ((st && st.noseExt && st.noseExt.e) || 0), 0]),   // (737 MAX: nose leg extended by noseExt.e)
            main = m4.xform(P, [mainX, C.main.y + ((st && st.gearUp) || 0), 0]);
      const g = ac.pos[1];
      out.push({ id: ac.id, type: ac.type, model: ac.modelKey, pitchDeg: p ? +(p.a * 180 / Math.PI).toFixed(2) : 0, noseTyre: +(nose[1] - g).toFixed(3), mainTyre: +(main[1] - g).toFixed(3), nosePos: nose, hdg: ac.fwd });
    }
    const gs = SFO.gateSys; const docked = [];
    for (const gg of gs.gates) if (gg.acType) for (const b of gs.bridgesOf(gg)) if (gs.docks(gg, b)) { const T = SFO.scene.aircraft.find(a => a.type === gg.acType); docked.push({ gate: gg.name, type: gg.acType, door: b.door || 1, sill: (b.door === 2 ? T && T.T.dockSill2 : T && T.T.dockSill), hw: (b.door === 2 ? T && T.T.dockHW2 : T && T.T.dockHW) }); }
    return { out, docked };
  });
  console.log('STANCE', JSON.stringify(rep.out));
  console.log('DOCKED', JSON.stringify(rep.docked));
  const a = rep.out.find(r => /^b73|^b38|^b39/.test(r.type)) || rep.out[0];
  if (a) {
    const n = a.nosePos; const h = Math.atan2(a.hdg[0], -a.hdg[2]) * 180 / Math.PI;   // heading of the nose (hdgVec convention)
    await page.evaluate(([n, yaw]) => SFO.qa.look([n[0], n[1] + 0.6, n[2]], yaw, 2, 11, 40), [n, h + 90]);
    await page.waitForTimeout(2500); await shot((process.env.PREFIX || 'stance') + '_nose_' + a.id);
  }
  if (await page.evaluate(() => SFO.qa.gate('B13', 26, 1, 8))) { await page.waitForTimeout(2500); await shot((process.env.PREFIX || 'stance') + '_gate_B13'); }
};

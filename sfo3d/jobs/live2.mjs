// Screenshots of several views after models load
export default async ({ page, shot, base }) => {
  const mode = process.env.MODE || 'snapshot';
  await page.goto(base + 'live.html?mode=' + mode);
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.evaluate(async () => { await new Promise(r => setTimeout(r, 1500)); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  const info = await page.evaluate(() => { const T = SFO.traffic; return { tracks: T.tracks.size, phases: [...T.tracks.values()].reduce((m, t) => (m[t.phase] = (m[t.phase] || 0) + 1, m), {}), gates: [...T.tracks.values()].filter(t => t.gate).map(t => t.info.flight + '@' + t.gate.name + ':' + Math.round(t.gateScore)), models: SFO.scene.aircraft.filter(a => a.model).length }; });
  console.log(JSON.stringify(info));
  const views = (process.env.VIEWS || 'overview,terminal,topB,topD,topG').split(',');
  const V = {
    topB: { target: [-880, 3, 720], dist: 700, yaw: 180, pitch: 89 }, topD: { target: [-620, 3, 220], dist: 650, yaw: 180, pitch: 89 }, topG: { target: [-1350, 3, 60], dist: 700, yaw: 180, pitch: 89 },
    topF: { target: [-1120, 3, -60], dist: 700, yaw: 180, pitch: 89 },
    hold1: { target: [-1575, 4, -1194], dist: 70, yaw: 200, pitch: 12 }, hold1top: { target: [-1575, 3, -1180], dist: 160, yaw: 180, pitch: 70 },
    rampB2: { target: [-860, 5, 700], dist: 380, yaw: 115, pitch: 22 },
    pierClose: { target: [-905, 9, 640], dist: 160, yaw: 100, pitch: 9 }, towerV: { target: [-740, 35, 331], dist: 190, yaw: 60, pitch: 10 },
    itb: { target: [-1214, 18, 359], dist: 520, yaw: 250, pitch: 18 }, gatesD: { target: [-600, 6, 215], dist: 150, yaw: 60, pitch: 14 }, twyA: { target: [-420, 4, 60], dist: 420, yaw: 60, pitch: 25 }, lowB: { target: [-900, 8, 650], dist: 260, yaw: 120, pitch: 16 }, lowD: { target: [-610, 8, 230], dist: 220, yaw: 70, pitch: 14 },
  };
  for (const v of views) {
    if (V[v]) await page.evaluate((c) => { const r = SFO.rig; r.stopFollow(); r.leaveTower(); r.anim = null; r.target = c.target; r.dist = c.dist; r.yaw = c.yaw * Math.PI / 180; r.pitch = c.pitch * Math.PI / 180; }, V[v]);
    else await page.evaluate((n) => { SFO.view(n); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); }, v);
    await page.waitForTimeout(+(process.env.SETTLE || 2500));
    await shot('v_' + v);
  }
};

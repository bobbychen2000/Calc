export default async ({ page, shot, base }) => {
  const mode = process.env.MODE || 'snapshot';
  await page.goto(base + 'live.html?mode=' + mode);
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.waitForTimeout(+(process.env.WAIT || 6000));
  const info = await page.evaluate(() => { const T = SFO.traffic; return { tracks: T.tracks.size, phases: [...T.tracks.values()].reduce((m, t) => (m[t.phase] = (m[t.phase] || 0) + 1, m), {}), gates: [...T.tracks.values()].filter(t => t.gate).map(t => t.info.flight + '@' + t.gate.name), aircraft: SFO.scene.aircraft.length, models: SFO.scene.aircraft.filter(a => a.model).length }; });
  console.log(JSON.stringify(info));
  await shot('overview');
};

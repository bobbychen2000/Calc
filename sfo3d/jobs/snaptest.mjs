// Headless check of snapshot mode (the Claude artifact build uses it: no relay, no network): the page loads, the traffic
// engine shows the recorded snapshot, and nothing throws. No screenshots.
//   SOFTGL=1 WAIT=60000 node livetest.mjs jobs/snaptest.mjs
export default async ({ page, base }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e && e.message || e)));
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  const until = Date.now() + +(process.env.WAIT || 60000);
  while (Date.now() < until) {
    await page.waitForTimeout(15000);
    const info = await page.evaluate(() => {
      const T = SFO.traffic; const tr = [...T.tracks.values()];
      return { tracks: tr.length, valid: tr.filter(t => t.disp.valid).length, phases: tr.reduce((m, t) => (m[t.phase] = (m[t.phase] || 0) + 1, m), {}),
        gates: tr.filter(t => t.gate).length, vehicles: tr.filter(t => t.vehicle).length, delay: T.delay, physics: SFO.physics.stats,
        status: document.querySelector('#status .txt')?.textContent || null };
    });
    console.log(JSON.stringify(info));
  }
  console.log('page errors:', errors.length ? errors.slice(0, 5) : 'none');
};

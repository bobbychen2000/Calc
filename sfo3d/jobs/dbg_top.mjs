export default async ({ page, shot, base }) => {
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  await page.evaluate(async () => { SFO.qa.hideUI(true); await new Promise(r => setTimeout(r, 2500)); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  const [x, z, dist, yaw, pitch] = (process.env.TOP || '-517,241,160,0,89').split(',').map(Number);
  await page.evaluate(([x, z, dist, yaw, pitch]) => SFO.qa.look([x, 3, z], yaw, pitch, dist, 50), [x, z, dist, yaw, pitch]);
  await page.waitForTimeout(2500);
  await shot(process.env.PREFIX || 'top');
  const r = await page.evaluate(() => SFO.scene.aircraft.map(a => [a.id || (a.opts && a.opts.id), a.pos && a.pos.map(v => v.toFixed(0)).join(','), a.fwd && a.fwd.map(v => v.toFixed(2)).join(',')]).slice(0, 80));
  console.log(JSON.stringify(r));
};

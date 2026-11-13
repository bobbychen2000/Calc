// Smoke test: load the app, wait for traffic, print the D1-safe counts and one overview screenshot.
//   node livetest.mjs jobs/smoke.mjs        (QS='mode=snapshot' etc. adds query parameters)
export default async ({ page, shot, base, DEV, log }) => {
  const t0 = Date.now();
  await page.goto(base + 'live.html?fixedres=1&' + (process.env.QS || ''));
  await page.waitForFunction(() => window.__hwdReady || window.__hwdError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__hwdError); if (err) throw new Error(err);
  log('ready in', Date.now() - t0, 'ms');
  await page.waitForTimeout(+(process.env.WAIT || 15000));
  log('counts', JSON.stringify(await page.evaluate(() => HWD.qa.counts())));
  log('status', await page.evaluate(() => document.querySelector('#status').innerText + ' | ' + document.querySelector('#phaseline').innerText + ' | ' + document.querySelector('#rwystats').innerText));
  await shot('smoke_' + DEV);
};

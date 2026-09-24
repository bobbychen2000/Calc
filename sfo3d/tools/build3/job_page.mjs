// livetest.mjs job: open an arbitrary page (PAGE=path?query), wait for window.__probe, screenshot it.
export default async ({ page, shot, base }) => {
  await page.goto(base + (process.env.PAGE || 'js/three/dev/probe.html'));
  await page.waitForFunction(() => window.__probe || window.__sfoError, null, { timeout: +(process.env.TIMEOUT || 120000) });
  console.log('result', JSON.stringify(await page.evaluate(() => window.__probe || window.__sfoError)));
  await page.waitForTimeout(+(process.env.SETTLE || 300));
  await shot(process.env.NAME || 'page');
};

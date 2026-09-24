// livetest.mjs job: open several dev pages in turn (DEV="js/three/dev/a.html?x=1;js/three/dev/b.html"), wait for
// window.__probe, print it and screenshot each (<OUT>/dev_<n>.png).
export default async ({ page, shot, base }) => {
  const list = (process.env.DEV || 'js/three/dev/probe.html').split(';').filter(Boolean);
  let n = 0;
  for (const p of list) {
    const t0 = Date.now();
    await page.goto(base + p);
    await page.waitForFunction(() => window.__probe || window.__sfoError, null, { timeout: 0, polling: 500 });
    console.log('probe', p, ((Date.now() - t0) / 1000).toFixed(1) + ' s', JSON.stringify(await page.evaluate(() => window.__probe || window.__sfoError)).slice(0, 1500));
    await page.waitForTimeout(300);
    await shot('dev_' + (n++) + '_' + p.replace(/^.*\//, '').replace(/[^a-z0-9]+/gi, '_').slice(0, 40));
  }
};

// Headless screenshots of the dev viewer (software GL).  Needs `python3 -m http.server 8777 --directory house`.
//   node tools/shot.cjs OUT.png "view=cam:frames/seg002_043.jpg&mode=white" [WIDTH] [OUT2.png "query2" ...]
// The canvas takes the aspect of a photo-matched camera when the view names one; WIDTH (default 1280) sets its width.
// Add hq=N to the query for a refined still (N passes: soft shadows, sky-light shading, antialiasing; slow in software GL).
const { chromium } = require('playwright');

(async () => {

const args = process.argv.slice(2);
const jobs = [];
for (let i = 0; i < args.length;) {
  const out = args[i++], q = args[i++];
  let w = 1280;
  if (i < args.length && /^\d+$/.test(args[i])) w = +args[i++];
  jobs.push({ out, q, w });
}
const port = process.env.HOUSE_PORT || 8777;
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const logs = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') logs.push(m.type() + ': ' + m.text()); });
page.on('pageerror', (e) => logs.push('pageerror: ' + e));
for (const j of jobs) {
  const url = `http://localhost:${port}/web/index.html?ui=0&${j.q}`;
  // the aspect of a photo camera is in the meta file: read it first
  let aspect = 16 / 9;
  const view = new URLSearchParams(j.q).get('view');
  const metaName = new URLSearchParams(j.q).get('meta') || 'house_meta.json';
  try {
    const meta = await (await fetch(`http://localhost:${port}/out/${metaName}`)).json();
    const c = (meta.cameras || {})[view];
    if (c) aspect = c.w / c.h;
  } catch (e) { logs.push('meta: ' + e); }
  await page.setViewportSize({ width: j.w, height: Math.round(j.w / aspect) });
  await page.goto(url);
  const info = await page.evaluate(async () => {
    const t0 = performance.now();
    while (!window.viewer && performance.now() - t0 < 30000) await new Promise((r) => setTimeout(r, 50));
    const r = await window.viewer.ready;
    await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
    window.viewer.renderNow();
    const passes = await window.viewer.settle();
    return Object.assign({ passes }, r);
  }).catch((e) => ({ error: String(e) }));
  await page.screenshot({ path: j.out });
  console.log(j.out, JSON.stringify(info));
}
for (const l of logs.slice(0, 12)) console.log(l);
await browser.close();
})();

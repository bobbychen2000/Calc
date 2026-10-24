// Monument review cameras (wave 3, m01-m19), rendered like test/qa.js. Usage:
//   CABIN_PAGE=/tmp/b/test.html node review/qa/monuments_views.js <outdir> [w h] [names...]
// yaw 0 looks forward (-z), PI aft (+z), +PI/2 left (-x), -PI/2 right (+x)
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const path = require('path'), fs = require('fs');
const out = process.argv[2], W = +(process.argv[3] || 800), H = +(process.argv[4] || 560), only = process.argv.slice(5);
const page0 = process.env.CABIN_PAGE || path.resolve(__dirname, '../../dist/test.html');
const V = (x, y, z, yaw, pitch = -0.1) => [[x, y, z], yaw, pitch];
const VIEWS = {
  m01_d1galley: V(0.3, 1.62, 5.6, 0), m02_fFront: V(-1.35, 1.62, 9.6, 0.05), m03_welcome: V(0.3, 1.62, 17.25, 0),
  m04_d2aft: V(0.0, 1.62, 16.35, Math.PI), m05_bar: V(0.3, 1.62, 32.2, Math.PI), m06_barObl: V(1.5, 1.62, 32.3, Math.PI - 0.55),
  m07_fjJ: V(1.35, 1.62, 13.6, 0.1, -0.15), m08_jpyPY: V(1.35, 1.62, 41.6, 0.1, -0.15), m09_d4fwd: V(0.3, 1.62, 44.45, 0),
  m10_pyAft: V(-1.35, 1.62, 40.4, Math.PI - 0.08, -0.15), m11_rearCurt: V(1.2, 1.62, 53.0, Math.PI, -0.12),
  m12_rearGalley: V(0.0, 1.62, 59.45, Math.PI, -0.15), m13_d2aftR: V(1.0, 1.62, 16.4, Math.PI + 0.6),
  m14_d2back: V(1.35, 1.62, 19.9, 0.08, -0.12), m15_d3back: V(1.35, 1.62, 36.0, 0.08, -0.12),
  m16_welcomeObl: V(1.0, 1.62, 17.0, 0.65), m17_d3jump: V(-1.2, 1.5, 32.4, Math.PI - 0.95), m18_doorL2: V(0.0, 1.55, 16.8, Math.PI / 2, -0.05),
  m19_cockpit: V(-0.75, 1.62, 5.6, 0.05),
};
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1) });
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + page0);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  await page.evaluate(() => { for (const id of ['top', 'bottom', 'hint', 'loading']) { const e = document.getElementById(id); if (e) e.style.visibility = 'hidden'; } });
  for (const n of (only.length ? only : Object.keys(VIEWS))) {
    await page.evaluate((v) => { __app.setView(...v); __app.renderNow(); __app.renderNow(); }, VIEWS[n]);
    await page.screenshot({ path: path.join(out, n + '.png'), timeout: 240000 });
    console.log(n);
  }
  await browser.close();
})();

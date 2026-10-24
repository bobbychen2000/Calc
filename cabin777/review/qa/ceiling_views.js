// Ceiling / bins review cameras (wave 3c, w11+), rendered like test/qa.js. Usage:
//   CABIN_PAGE=/tmp/b/test.html node review/qa/ceiling_views.js <outdir> [w h] [names...]
// yaw 0 looks forward (-z), PI aft (+z), +PI/2 left (-x), -PI/2 right (+x); pitch > 0 looks up
// v*: aisle ceilings, bins and PSUs (as in w5-w10); d*: the door cross-aisle ceilings (doors 1-5)
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const path = require('path'), fs = require('fs');
const out = process.argv[2], W = +(process.argv[3] || 800), H = +(process.argv[4] || 560), only = process.argv.slice(5);
const page0 = process.env.CABIN_PAGE || path.resolve(__dirname, '../../dist/test.html');
const V = (x, y, z, yaw, pitch = -0.1) => [[x, y, z], yaw, pitch];
const PI = Math.PI;
const VIEWS = {
  v1_yCentreFwd: V(1.2, 1.62, 54.0, 0.08, 0.18), v2_jAisleFwdUp: V(1.15, 1.62, 27.5, 0.05, 0.3),
  v3_door3Up: V(-1.2, 1.62, 31.2, PI + 0.1, 0.32), v4_jPsuUp: V(1.15, 1.5, 24.0, -0.5, 0.55),
  v5_yCbin: V(1.2, 1.62, 50.0, 0.35, 0.3), v6_y34Eup: V(0.5, 1.2, 49.6, 0.0, 0.9),
  v7_door4Fwd: V(1.2, 1.62, 47.5, 0.0, 0.15), v8_cbinSide: V(1.6, 1.55, 25.0, 0.9, 0.35),
  v9_obinPsu: V(0.9, 1.5, 51.0, -0.9, 0.45), v12_cPlacardClose: V(1.25, 1.7, 50.6, 0.55, 0.46),
  v13_oPlacardClose: V(1.25, 1.7, 50.6, -0.79, 0.35),
  v14_oPlacardFace: V(0.95, 1.75, 49.75, -PI / 2, 0.5), v15_cPlacardFace: V(1.4, 1.8, 49.75, PI / 2, 0.55),
  d1_door1Cross: V(0.3, 1.62, 5.4, PI / 2, 0.35), d1b_door1Up: V(-0.8, 1.55, 6.6, 0.15, 0.5),
  d2_door2Fwd: V(1.25, 1.62, 19.2, 0.05, 0.22), d2b_door2Cross: V(0.6, 1.62, 16.8, -PI / 2, 0.4),
  d4_door4Aft: V(-1.25, 1.62, 41.2, PI - 0.05, 0.18), d4b_door4Cross: V(0.6, 1.62, 44.3, PI / 2, 0.4),
  d5_door5Aft: V(1.2, 1.62, 55.8, PI, 0.18), d5b_door5Cross: V(0.3, 1.62, 58.7, -PI / 2, 0.4),
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

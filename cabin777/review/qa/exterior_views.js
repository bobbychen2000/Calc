// Exterior review cameras (wave 3b, w8+): window views from seats (lookOut), rendered like test/qa.js. Usage:
//   CABIN_PAGE=/tmp/b/test.html node review/qa/exterior_views.js <outdir> [w h] [names...]
// name prefix: w = day, s = sunset, n = night; then the seat id
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const path = require('path'), fs = require('fs');
const out = process.argv[2], W = +(process.argv[3] || 930), H = +(process.argv[4] || 575), only = process.argv.slice(5);
const page0 = process.env.CABIN_PAGE || path.resolve(__dirname, '../../dist/test.html');
const VIEWS = { w11A: ['11A', 'day'], w13A: ['13A', 'day'], w17A: ['17A', 'day'], w19A: ['19A', 'day'], w17K: ['17K', 'day'],
  w26K: ['26K', 'day'], w30K: ['30K', 'day'], w11K: ['11K', 'day'], s13A: ['13A', 'sunset'], n19A: ['19A', 'night'] };
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1) });
  page.on('pageerror', (e) => console.log('pageerror ' + e.message));
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + page0);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  await page.evaluate(() => { for (const id of ['top', 'bottom', 'hint', 'loading']) { const e = document.getElementById(id); if (e) e.style.visibility = 'hidden'; } });
  for (const n of (only.length ? only : Object.keys(VIEWS))) {
    const [id, sky, dp] = VIEWS[n];   // dp: [pitch, outboard, down] offsets (w12: the alv 26K photos are taken with the phone at the glass, under the shade rail)
    await page.evaluate(([id, sky, dp]) => {
      __app.applySky(sky); if (sky === 'night') __app.applyMood('sleep');
      const s = __app.L.seats.find((q) => q.id === id); __app.sit(s, { instant: true }); __app.lookOut(s);
      const a = __app.anim; if (a && a.to) { __app.cam.pos = [...a.to.pos]; __app.cam.yaw = a.to.yaw; __app.cam.pitch = a.to.pitch; } __app.anim = null; if (dp) { __app.cam.pitch += dp[0]; __app.cam.pos[0] += Math.sign(__app.cam.pos[0]) * dp[1]; __app.cam.pos[1] += dp[2]; }
      __app.renderNow(); __app.renderNow();
    }, [id, sky, dp || 0]);
    await page.screenshot({ path: path.join(out, n + '.png'), timeout: 240000 });
    await page.evaluate(() => { if (__app.seated) { __app.setBed(false); __app.seated = null; __app.hideSeatBar(); } __app.mode = 'walk'; __app.applyMood('boarding'); __app.applySky('day'); });
    console.log('shot', n);
  }
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });

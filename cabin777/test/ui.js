// UI QA at phone and desktop sizes. Usage: node test/ui.js <outdir> <w> <h> [prefix]
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/home/claude/.npm-global/lib/node_modules/playwright')); }
const path = require('path');
const out = process.argv[2], W = +process.argv[3], H = +process.argv[4], pre = process.argv[5] || 'ui';
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, hasTouch: W < 600, isMobile: W < 600 });
  const page = await ctx.newPage();
  const logs = [];
  page.on('pageerror', (e) => logs.push('pageerror ' + e.message));
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + path.resolve(__dirname, '../dist/test.html'));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  const snap = async (n) => { await page.evaluate(() => __app.renderNow()); await page.waitForTimeout(250); await page.screenshot({ path: path.join(out, `${pre}_${n}.png`) }); console.log('shot', n); };
  await snap('1_start');
  await page.evaluate(() => { __app.interrupt(); const s = __app.L.seats.find((q) => q.id === '3L'); __app.selectSeat(s); });
  await snap('2_card');
  await page.evaluate(() => { const s = __app.L.seats.find((q) => q.id === '3L'); __app.sit(s, { instant: true }); __app.anim = null; });
  await snap('3_seated');
  await page.evaluate(() => { __app.toggleBed(); const a = __app.anim; if (a) { __app.cam.pos = [...a.to.pos]; __app.cam.yaw = a.to.yaw; __app.cam.pitch = a.to.pitch; __app.anim = null; } });
  await snap('4_bed');
  await page.evaluate(() => { __app.setBed(false); __app.standUp(); __app.anim = null; document.getElementById('settingsBtn').click(); });
  await snap('5_settings');
  await page.evaluate(() => { document.getElementById('settingsClose').click(); __app.setMode('xray'); });
  await snap('6_xray');
  await page.evaluate(() => { __app.setMode('walk'); __app.startTour(); __app.anim = null; });
  await page.waitForTimeout(300);
  await page.evaluate(() => { if (__app.anim) { const a = __app.anim; __app.cam.pos = [...a.to.pos]; __app.cam.yaw = a.to.yaw; __app.cam.pitch = a.to.pitch; __app.anim = null; } });
  await snap('7_tour');
  console.log(logs.join('\n'));
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });

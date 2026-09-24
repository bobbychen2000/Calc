// Render review sheets of individual units. Usage: node test/studio.js <outdir> <spec.json>
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/home/claude/.npm-global/lib/node_modules/playwright')); }
const path = require('path');
const out = process.argv[2];
const spec = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: spec.w || 520, height: spec.h || 400 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.log('pageerror', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.log('console', m.text()); });
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + path.resolve(__dirname, '../dist/test.html'));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  await page.evaluate(() => { for (const id of ['top', 'bottom', 'hint', 'loading']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; } __app.loop = () => {}; });
  for (const shot of spec.shots) {
    await page.evaluate((s) => {
      const f = (typeof UNITS !== 'undefined' && UNITS[s.unit]) || STUDIO_UNITS[s.unit];
      const geo = f();
      studioRender(__app, geo, s.opts || {});
    }, shot);
    await page.screenshot({ path: path.join(out, shot.name + '.png') });
    console.log('shot', shot.name);
  }
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });

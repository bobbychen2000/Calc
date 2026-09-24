// WebGL counterparts of the Blender review shots (same spec, same camera) for side-by-side comparison.
// Usage: node test/blender/webgl_ref.js <outdir> <spec.json>   -> <outdir>/<name>_webgl.png
// Units use studioRender(opts); slices place the walk camera at opts.eye looking at opts.look (the engine's walk
// fovY is clamp(2 atan(tan 32deg / aspect), 58, 92) deg, so give the slice shot that fov in the spec).
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const path = require('path');
const out = process.argv[2];
const spec = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: spec.w || 800, height: spec.h || 600 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.log('pageerror', e.message));
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + (process.env.CABIN_PAGE || path.resolve(__dirname, '../../dist/test.html')));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 240000 });
  await page.evaluate(() => { for (const id of ['top', 'bottom', 'hint', 'loading']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; } __app.loop = () => {}; });
  for (const shot of spec.shots) {
    await page.evaluate((s) => {
      if (s.unit) {
        const f = (typeof UNITS !== 'undefined' && UNITS[s.unit]) || STUDIO_UNITS[s.unit];
        studioRender(__app, f(), s.opts || {});
      } else {
        const e = s.opts.eye, l = s.opts.look, d = [l[0] - e[0], l[1] - e[1], l[2] - e[2]], n = Math.hypot(...d);
        __app.setView(e, Math.atan2(-d[0], -d[2]), Math.asin(d[1] / n));
        __app.renderNow();
      }
    }, shot);
    await page.screenshot({ path: path.join(out, shot.name + '_webgl.png') });
    console.log('webgl', shot.name);
  }
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });

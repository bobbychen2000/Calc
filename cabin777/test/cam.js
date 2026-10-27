// node test/cam.js <page.html> <outdir> name:x,y,z,yaw,pitch ...   (930x575 shots at given cameras; add moods with your own __app.applyMood call)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const [page0, out, ...cams] = process.argv.slice(2);
  require('fs').mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 930, height: 575 } });
  await p.addInitScript(() => { window.__TEST__ = true; });
  await p.goto('file://' + page0);
  await p.waitForFunction(() => window.__ready === true, null, { timeout: 240000 });
  await p.evaluate(() => { for (const id of ['top', 'bottom', 'hint', 'loading']) { const e = document.getElementById(id); if (e) e.style.visibility = 'hidden'; } __app.loop = () => {}; });
  for (const c of cams) {
    const [name, v] = c.split(':'); const [x, y, z, yaw, pitch] = v.split(',').map(Number);
    await p.evaluate(([x, y, z, yaw, pitch]) => { __app.setView([x, y, z], yaw, pitch); __app.renderNow(); __app.renderNow(); }, [x, y, z, yaw, pitch]);
    await p.screenshot({ path: `${out}/${name}.png`, timeout: 240000 }); console.log('shot', name);
  }
  await b.close();
})();

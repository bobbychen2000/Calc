// node test/perf.js <test.html>: draw calls / frame triangles at three cameras (mid, econ, room), contact AO on (Sharp) vs off (Balanced)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 640, height: 400 } });
  await p.addInitScript(() => { window.__TEST__ = true; });
  await p.goto('file://' + process.argv[2]);
  await p.waitForFunction(() => window.__ready === true, null, { timeout: 240000 });
  const r = await p.evaluate(() => {
    const G = __app.G, gl = G.gl; const out = {};
    const views = { mid: [[0, 1.62, 24], 0, -0.1], econ: [[0, 1.62, 47], 0, -0.1], room: [[0, 1.62, 14], 0, -0.1] };
    for (const [n, v] of Object.entries(views)) {
      __app.setView(...v);
      for (const s of [0.7, 0]) {
        __app.scene.ssaoOn = !!s; __app.renderNow(); __app.renderNow(); gl.finish();
        const st = { ...G.stats }; const t0 = performance.now(); for (let i = 0; i < 3; i++) { __app.renderNow(); gl.finish(); } 
        out[n + (s ? '_ssao' : '_off')] = { ...st, ms: Math.round((performance.now() - t0) / 3) };
      }
      LIGHT_TUNE.ssao[1] = 0.7;
    }
    return out;
  });
  console.log(JSON.stringify(r, null, 1)); await b.close();
})();

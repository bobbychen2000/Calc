const { chromium, devices } = require('playwright');
(async () => {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const ctx = await browser.newContext({ ...devices['iPhone 13'] });
  const page = await ctx.newPage();
  page.setDefaultTimeout(400000);
  const logs = [];
  page.on('console', (m) => logs.push(m.type() + ': ' + m.text().slice(0, 300)));
  page.on('pageerror', (e) => logs.push('pageerror: ' + e));
  page.on('requestfailed', (r) => logs.push('failed: ' + r.url()));
  await page.goto('http://localhost:8777/dist/_local.html?' + (process.argv[3] || ''));
  const info = await page.evaluate(async () => {
    const t0 = performance.now();
    while (!window.viewer && performance.now() - t0 < 60000) await new Promise((r) => setTimeout(r, 50));
    const r = await window.viewer.ready.catch((e) => ({ err: String(e) }));
    await new Promise((res) => setTimeout(res, 3000));
    const st = window.viewer.stage;
    return Object.assign({ errors: window.viewer.errors, dpr: devicePixelRatio, size: [innerWidth, innerHeight],
      canvas: [st.canvas.width, st.canvas.height], frames: st.frames, info: st.renderer.info.render, programs: st.renderer.info.programs.length,
      status: document.getElementById('status').textContent }, r);
  }).catch((e) => ({ error: String(e) }));
  await page.screenshot({ path: process.argv[2] });
  console.log(JSON.stringify(info));
  for (const l of logs.filter((l) => !/GL Driver|GPU stall/.test(l)).slice(0, 25)) console.log(l);
  await browser.close();
})();

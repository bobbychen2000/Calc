// Phone smoke test: opens the page as a phone (coarse pointer, so the app starts on Balanced), then for each quality level
// sits in a few seats and fails on any WebGL error or warning, or on a frame that shows no cabin (sky only).
// qa.js runs as a desktop (Sharp), so it cannot see bugs that live only in the phone quality levels.
// usage: node test/mobile_smoke.js [page.html]     (default dist/test.html; exit code 1 on failure)
const path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const PAGE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'dist', 'test.html'));
const SEATS = ['5F', '1A', '11A', '26A', '35C'];

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1' });
  const p = await ctx.newPage();
  let msgs = [];
  p.on('pageerror', (e) => msgs.push('pageerror: ' + e));
  p.on('console', (m) => { if (m.type() === 'error' || (m.type() === 'warning' && /WebGL|GL_/.test(m.text()))) msgs.push(m.text().slice(0, 200)); });
  await p.addInitScript(() => { window.__TEST__ = true; });
  await p.goto('file://' + PAGE);
  await p.waitForFunction(() => window.__ready === true, null, { timeout: 240000 });
  const startQ = await p.evaluate(() => __app.quality);
  const fails = [];
  if (startQ !== 'balanced') fails.push(`phone start quality is ${startQ}, expected balanced`);
  for (const q of ['balanced', 'low', 'high']) {
    await p.evaluate((k) => document.querySelector(`[data-quality="${k}"]`).click(), q);
    for (const id of SEATS) {
      msgs = [];
      const r = await p.evaluate((sid) => {
        const a = __app, gl = a.G.gl;
        a.sit(a.L.seats.find((s) => s.id === sid), { instant: true });
        while (gl.getError()) {}
        a.renderNow();
        const errs = []; let e; while ((e = gl.getError())) errs.push(e);
        // a sky-only frame is a smooth gradient; a cabin view is full of edges: share of sampled pixels in the middle of the
        // frame whose luma differs from the pixel 3 px right or 3 px up by more than 12
        const W = gl.drawingBufferWidth, H = gl.drawingBufferHeight, px = new Uint8Array(W * H * 4);
        gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
        const L = (x, y) => { const i = (y * W + x) * 4; return 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]; };
        let edges = 0, n = 0;
        for (let y = Math.floor(H * 0.15); y < H * 0.85; y += 3) for (let x = Math.floor(W * 0.1); x < W * 0.9 - 3; x += 3) {
          n++;
          if (Math.abs(L(x, y) - L(x + 3, y)) > 12 || Math.abs(L(x, y) - L(x, y + 3)) > 12) edges++;
        }
        return { errs, nonSky: edges / Math.max(1, n) };
      }, id);
      const tag = `${q} ${id}`;
      if (r.errs.length) fails.push(`${tag}: GL errors ${r.errs.join(',')}`);
      if (msgs.length) fails.push(`${tag}: ${[...new Set(msgs)].slice(0, 2).join(' | ')}`);
      if (r.nonSky < 0.02) fails.push(`${tag}: only ${(r.nonSky * 100).toFixed(1)} % edge pixels: the view is a smooth gradient (sky only, no cabin drawn?)`);
      console.log(`${tag}: gl errors ${r.errs.length}, edge pixels ${(r.nonSky * 100).toFixed(1)} %`);
    }
  }
  await b.close();
  if (fails.length) { console.log('FAIL\n  ' + fails.join('\n  ')); process.exit(1); }
  console.log(`OK (phone start quality ${startQ}; ${SEATS.length} seats x 3 quality levels, no WebGL errors, cabin drawn)`);
})().catch((e) => { console.log('FAIL', String(e)); process.exit(1); });

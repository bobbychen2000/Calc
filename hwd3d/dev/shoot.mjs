// Headless renders of the HWD world dev page (dev/world.html) into out/phase2/world_*.png.
//   node dev/shoot.mjs [views=overview,thr10R,thr28L,green,west,tower] [--phone] [--desktop] [--ground=naip|procedural]
//                      [--prefix=world] [--port=8731] [--q=high|low]
// A tiny static server on 127.0.0.1:<port> serves hwd3d/; Chromium runs with SwiftShader (no GPU here) at 1280x720
// (desktop) and 390x844 CSS px at DPR 2 with a phone UA (phone). Each view is rendered by the page itself
// (window.HWDW.shot -> PNG data URL from the renderer's final framebuffer), so compositing does not matter.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'out', 'phase2'); fs.mkdirSync(OUT, { recursive: true });
const args = process.argv.slice(2); const opt = (k, d) => { const a = args.find(x => x.startsWith('--' + k + '=')); return a ? a.split('=')[1] : d; };
const views = (args.find(a => !a.startsWith('--')) || 'overview,thr10R,thr28L,green,west,tower').split(',');
const port = +opt('port', 8731), prefix = opt('prefix', 'world'), ground = opt('ground', 'naip');
const modes = args.includes('--phone') && !args.includes('--desktop') ? ['phone'] : args.includes('--desktop') && !args.includes('--phone') ? ['desktop'] : ['desktop', 'phone'];
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(port, '127.0.0.1', r));
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-watchdog', '--js-flags=--max-old-space-size=3000'] });
try {
  for (const mode of modes) {
    const phone = mode === 'phone';
    const ctx = await browser.newContext(phone ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' }
      : { viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.on('console', m => { const t = m.text(); if (/error|warn|NAIP|world /i.test(t)) console.log(`[${mode}] ${t.slice(0, 400)}`); });
    page.on('pageerror', e => console.log(`[${mode}] PAGEERROR ${e.message}`));
    const q = new URLSearchParams({ shot: '1', ground, view: views[0] }); if (opt('q')) q.set('q', opt('q')); if (opt('t')) q.set('t', opt('t'));
    const t0 = Date.now();
    await page.goto(`http://127.0.0.1:${port}/dev/world.html?${q}`);
    await page.waitForFunction(() => window.__worldReady || window.__worldError, null, { timeout: 180000 });
    const err = await page.evaluate(() => window.__worldError); if (err) throw new Error(err);
    console.log(`[${mode}] ready in ${Date.now() - t0} ms; stats ${JSON.stringify(await page.evaluate(() => window.HWDW.stats()))}`);
    for (const v of views) {
      const t1 = Date.now();
      const url = await page.evaluate((v) => window.HWDW.shot(v), v);
      const file = path.join(OUT, `${prefix}_${v}_${mode}.png`);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
      console.log(`[${mode}] ${v} -> ${path.relative(ROOT, file)} (${Date.now() - t1} ms)`);
    }
    await ctx.close();
  }
} finally { await browser.close(); server.close(); }

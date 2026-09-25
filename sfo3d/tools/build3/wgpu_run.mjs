// WebGPU test harness for the three.js renderer: the same job interface as livetest.mjs ({page, shot, base}) but
// Chromium is started with a WebGPU adapter. On a machine without a GPU that is SwiftShader's Vulkan implementation
// (--use-webgpu-adapter=swiftshader), which is slow but runs three's WebGPU backend end to end (WGSL from TSL, reversed
// depth, compute-free render pipelines, copyExternalImageToTexture, readbacks): the path the owner's iPhone (Safari 26
// ships WebGPU) and desktop Chrome take, which the WebGL 2 runs of livetest.mjs never exercise.
//   node tools/build3/wgpu_run.mjs <job.mjs>          env: W, H, OUT (default out/wgpu), GPU=1 (use the machine's GPU)
//   node tools/build3/wgpu_run.mjs --probe            prints what adapter Chromium gets
// Serves the repository root statically (snapshot mode needs no relay).
import { chromium } from 'playwright';
import http from 'http'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const OUT = process.env.OUT || path.join(ROOT, 'out', 'wgpu'); fs.mkdirSync(OUT, { recursive: true });
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.css': 'text/css', '.sfom': 'application/octet-stream', '.bin': 'application/octet-stream' };
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x'); if (url.pathname.startsWith('/api/')) { res.statusCode = 404; return res.end(); }
  const f = path.join(ROOT, url.pathname === '/' ? 'live3.html' : decodeURIComponent(url.pathname));
  fs.readFile(f, (e, d) => { if (e) { res.statusCode = 404; return res.end(); } res.setHeader('Content-Type', TYPES[path.extname(f)] || 'application/octet-stream'); res.setHeader('Cache-Control', 'no-store'); res.end(d); });
});
await new Promise(r => server.listen(0, r));
const base = `http://localhost:${server.address().port}/`;
const args = ['--enable-unsafe-webgpu', '--ignore-gpu-blocklist', '--js-flags=--max-old-space-size=4000', '--disable-gpu-watchdog', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'];
if (!process.env.GPU) args.push('--use-webgpu-adapter=swiftshader', '--enable-unsafe-swiftshader');
if (process.env.CHROME_ARGS) args.push(...process.env.CHROME_ARGS.split(' ').filter(Boolean)); // e.g. CHROME_ARGS="--use-angle=swiftshader"
const browser = await chromium.launch({ args });
const W = +(process.env.W || 960), H = +(process.env.H || 540);
const page = await (await browser.newContext({ viewport: { width: W, height: H } })).newPage();
page.setDefaultTimeout(0);
page.on('console', m => { const t = m.text(); if (!/GPU stall|Automatic fallback/.test(t)) console.log('[page]', t.slice(0, 400)); });
page.on('pageerror', e => console.log('[pageerror]', e.message, e.stack && e.stack.split('\n').slice(0, 4).join(' | ')));
const shot = async (name, opts = {}) => { const f = path.join(OUT, name + '.png'); await page.screenshot({ path: f, ...opts }); console.log('shot', f); return f; };
const t0 = Date.now();
try {
  if (process.argv[2] === '--probe') {
    await page.goto(base + 'js/three/dev/probe.html');
    console.log(await page.evaluate(async () => { const a = navigator.gpu && await navigator.gpu.requestAdapter(); return a ? JSON.stringify({ vendor: a.info && a.info.vendor, arch: a.info && a.info.architecture }) : 'no adapter'; }));
  } else { const script = await import(path.resolve(process.argv[2])); await script.default({ page, shot, base, W, H, OUT }); }
} catch (e) { console.log('SCRIPT FAILED', e); process.exitCode = 1; }
console.log('done in', ((Date.now() - t0) / 1000).toFixed(1), 's');
await browser.close(); server.close(); process.exit();

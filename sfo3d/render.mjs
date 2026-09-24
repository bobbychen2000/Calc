// Harness: serves the renderer, launches headless Chromium (SwiftShader), receives raw frames -> ffmpeg
import http from 'http'; import fs from 'fs'; import path from 'path'; import { spawn } from 'child_process';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');

const ROOT = process.env.ROOT || new URL('.', import.meta.url).pathname.replace(/\/$/, '');
const OUT = process.env.OUT || path.join(ROOT, 'out');
fs.mkdirSync(OUT, { recursive: true });
const sessions = {};
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png' };

function stillToPng(buf, w, h, file) {
  return new Promise((res, rej) => {
    const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${w}x${h}`, '-i', '-', '-vf', 'vflip', file]);
    p.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))); p.stdin.end(buf);
  });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  const parts = url.pathname.split('/').filter(Boolean);
  if (req.method === 'POST' && parts[0] === 'frame') {
    const sv = sessions[parts[1]];
    if (sv && sv.ff) { // stream straight into the encoder (no per-frame buffering; frames arrive strictly one at a time)
      req.pipe(sv.ff.stdin, { end: false });
      req.on('end', () => { sv.n++; res.end('ok'); if (global.gc) setImmediate(() => { global.gc(); if (process.env.MEMLOG) { const m = process.memoryUsage(); console.log('[mem]', sv.n, 'rss', m.rss >> 20, 'heap', m.heapUsed >> 20, 'ext', m.external >> 20, 'ab', m.arrayBuffers >> 20); } }); });
      req.on('error', e => { res.statusCode = 500; res.end(String(e)); });
      return;
    }
    const chunks = []; req.on('data', d => chunks.push(d));
    req.on('end', async () => {
      const buf = Buffer.concat(chunks); const s = sessions[parts[1]];
      try {
        if (s && s.ff) { if (!s.ff.stdin.write(buf)) await new Promise(r => s.ff.stdin.once('drain', r)); s.n++; }
        else { const w = s ? s.w : +url.searchParams.get('w'), h = s ? s.h : +url.searchParams.get('h'); await stillToPng(buf, w || globalThis.W, h || globalThis.H, path.join(OUT, `${parts[1]}_${parts[2]}.png`)); }
        res.end('ok');
      } catch (e) { res.statusCode = 500; res.end(String(e)); }
    });
    return;
  }
  const f = path.join(ROOT, url.pathname === '/' ? 'index.html' : url.pathname);
  fs.readFile(f, (e, d) => { if (e) { res.statusCode = 404; return res.end(); } res.setHeader('Content-Type', types[path.extname(f)] || 'application/octet-stream'); res.setHeader('Cache-Control', 'no-store'); res.end(d); });
});

export async function startVideo(name, w, h, fps, file, crf = 16, preset = 'medium') {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-thread_queue_size', '2', '-pix_fmt', 'rgba', '-s', `${w}x${h}`, '-r', String(fps), '-i', '-',
    '-vf', 'vflip', '-c:v', 'libx264', '-preset', preset, '-crf', String(crf), '-threads', '2', '-x264-params', 'rc-lookahead=12:lookahead-threads=1', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', file], { stdio: ['pipe', 'inherit', 'inherit'] });
  sessions[name] = { ff, w, h, n: 0, done: new Promise(r => ff.on('close', r)) };
}
export async function endVideo(name) { const s = sessions[name]; s.ff.stdin.end(); await s.done; delete sessions[name]; }
export function registerStill(name, w, h) { sessions[name] = { w, h }; }

export async function launch(cfg) {
  await new Promise(r => server.listen(0, r));
  const port = server.address().port;
  const gpuArgs = process.env.SWS ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : ['--use-gl=angle', '--use-angle=gl-egl'];
  const browser = await chromium.launch({ args: [...gpuArgs, '--ignore-gpu-blocklist', '--js-flags=--max-old-space-size=6000 --expose-gc', '--disable-gpu-watchdog', '--disable-renderer-backgrounding', '--disable-gpu-process-crash-limit'],
    env: { ...process.env, LIBGL_ALWAYS_SOFTWARE: '1', GALLIUM_DRIVER: 'llvmpipe', LP_NUM_THREADS: process.env.LP_NUM_THREADS || '2' } });
  const page = await browser.newPage();
  page.setDefaultTimeout(0);
  page.on('console', m => { const t = m.text(); if (!/GPU stall|GL Driver/.test(t)) console.log('[page]', t); });
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.goto(`http://localhost:${port}/index.html`);
  await page.waitForFunction(() => window.__ready === true);
  globalThis.W = cfg.W; globalThis.H = cfg.H;
  const r = await page.evaluate((c) => window.initApp(c), cfg);
  console.log('init:', r);
  return { page, browser, close: async () => { await browser.close(); server.close(); } };
}

// CLI: node render.mjs job.mjs
if (process.argv[2]) {
  const job = await import(path.resolve(process.argv[2]));
  const t0 = Date.now();
  try { await job.default({ launch, startVideo, endVideo, registerStill, OUT }); }
  catch (e) { console.error('JOB FAILED', e); process.exitCode = 1; }
  console.log('job done in', ((Date.now() - t0) / 1000).toFixed(1), 's');
  process.exit();
}

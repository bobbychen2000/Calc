// Shared pieces of the OD3 video driver (hwd3d Phase 3, video): the FROZEN APP SNAPSHOT (a copy of the app, its data and
// models taken once per case and verified by sha256 before every run), a static server for that snapshot on 127.0.0.1 (a
// free port in 8700-8749) that logs and hashes everything it serves and refuses anything outside it, headless Chromium with
// SwiftShader (no GPU on this machine), the virtual-clock init script (js/video/vclock.js, from the snapshot) and the boot
// of the UNMODIFIED app (live.html?mode=replay) on a type-only replay pack.
// Nothing here prints or writes a track key or an identity (D1): the pack is type-only and keys stay inside the page.
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import net from 'node:net'; import zlib from 'node:zlib';
import crypto from 'node:crypto'; import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url'; import { createRequire } from 'node:module';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const require = createRequire(import.meta.url);
export function playwright() {
  try { return require(process.env.PLAYWRIGHT_MODULE || 'playwright'); }
  catch (e) { console.error('Playwright not found (npm i -D playwright, or set PLAYWRIGHT_MODULE)'); process.exit(1); }
}
export const log = (...a) => console.log('[video]', ...a);
export const sleep = (ms) => new Promise(r => setTimeout(r, ms));
/** the PRNG seed of the virtual clock (Math.random): a neutral constant - it is no date, time or identity */
export const VIDEO_SEED = 0x5eed;
export const sha256 = (buf) => crypto.createHash('sha256').update(buf).digest('hex');

export async function freePort(lo = 8700, hi = 8749) {
  for (let p = lo; p <= hi; p++) {
    const ok = await new Promise(r => { const s = net.createServer(); s.once('error', () => r(false)); s.listen(p, '127.0.0.1', () => s.close(() => r(true))); });
    if (ok) return p;
  }
  throw new Error('no free port in ' + lo + '-' + hi);
}
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.gz': 'application/gzip', '.svg': 'image/svg+xml', '.glb': 'model/gltf-binary', '.bin': 'application/octet-stream', '.webp': 'image/webp', '.ktx2': 'image/ktx2' };
/** static server for `root` (the frozen snapshot; ROOT only for the snapshot probe). 127.0.0.1 only; never refs/cache/local/
 *  or dot files; /api/* is not served (the in-page replay shim answers it, so a request that reaches the server is a bug).
 *  Every request is logged: `served` (path -> sha256 of the bytes sent; `manifest` given: a byte mismatch is a `bad` entry)
 *  and `missed` (404s): the driver aborts a run with a miss or a mismatch, so a page never falls back to anything that is
 *  not in the snapshot. */
export async function startServer({ root = ROOT, manifest = null, lo = 8700, hi = 8749 } = {}) {
  const served = new Map(), missed = [], bad = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://x');
    if (url.pathname === '/favicon.ico') { res.statusCode = 204; return res.end(); }   // the browser's own request: not the app's
    if (url.pathname.startsWith('/api/')) { missed.push(url.pathname); res.statusCode = 404; return res.end(); }
    const rel = url.pathname === '/' ? 'live.html' : decodeURIComponent(url.pathname).replace(/^\/+/, '');
    const f = path.resolve(root, rel), r = path.relative(root, f);
    if (!f.startsWith(root + path.sep) || /(^|[\/\\])refs[\/\\]cache[\/\\]local([\/\\]|$)/.test(r) || /(^|[\/\\])\./.test(r)) { missed.push('403 ' + rel); res.statusCode = 403; return res.end(); }
    fs.readFile(f, (e, d) => {
      if (e) { missed.push(r.split(path.sep).join('/')); res.statusCode = 404; return res.end(); }
      const key = r.split(path.sep).join('/'), h = sha256(d); served.set(key, h);
      if (manifest && manifest.files[key] !== h) bad.push(key);
      res.setHeader('Content-Type', TYPES[path.extname(f)] || 'application/octet-stream'); res.setHeader('Cache-Control', 'no-store'); res.end(d);
    });
  });
  for (let i = 0; i < 5; i++) {
    const port = await freePort(lo, hi);
    const ok = await new Promise(r => { server.once('error', () => r(false)); server.listen(port, '127.0.0.1', () => r(true)); });
    if (ok) return { server, port, base: `http://127.0.0.1:${port}/`, served, missed, bad };
  }
  throw new Error('could not bind a port in ' + lo + '-' + hi);
}
export function readPack(file, root = ROOT) {
  const buf = fs.readFileSync(path.resolve(root, file));
  const pack = JSON.parse((buf[0] === 0x1f && buf[1] === 0x8b ? zlib.gunzipSync(buf) : buf).toString('utf8'));
  if (pack.v !== 'hwd-pack/1') throw new Error('not an hwd-pack/1 file');
  return pack;
}
/** the virtual epoch: the shim starts its head lookahead_s into the window at Date.now(); with t0 = (from + L) s the
 *  shim's offset is ~0, so the virtual wall clock IS the recording clock (+ lookahead) */
export const epochOf = (pack) => Math.round((pack.from + (pack.lookahead_s || 60)) * 1000);

export async function launch({ W = 1920, H = 1080, sws = process.env.SWS !== '0' } = {}) {
  const { chromium } = playwright();
  const gpuArgs = sws ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : [];
  const browser = await chromium.launch({ args: [...gpuArgs, '--ignore-gpu-blocklist', '--js-flags=--max-old-space-size=3500', '--disable-gpu-watchdog',
    '--disable-renderer-backgrounding', '--disable-background-timer-throttling', '--disable-backgrounding-occluded-windows', '--font-render-hinting=none'] });
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const page = await ctx.newPage(); page.setDefaultTimeout(0);
  const errors = [];
  page.on('console', m => { const t = m.text(), ty = m.type(); if (/GPU stall|GL Driver|Automatic fallback|swiftshader/i.test(t)) return;
    if (ty === 'error' || ty === 'warning') { errors.push({ type: ty, text: t.slice(0, 400) }); console.log('[page ' + ty + ']', t.slice(0, 300)); }
    else if (process.env.VERBOSE || /^(world|note|NAIP|video)/.test(t)) console.log('[page]', t.slice(0, 300)); });
  page.on('pageerror', e => { errors.push({ type: 'pageerror', text: String(e.message).slice(0, 400) }); console.log('[pageerror]', e.message); });
  return { browser, ctx, page, errors };
}
/** boot live.html in replay mode on `packUrl` under the virtual clock (js/video/vclock.js read from `root`, the snapshot);
 *  resolves when window.__hwdReady */
export async function bootApp(page, { base, packUrl, t0, seed = VIDEO_SEED, root = ROOT, extraQuery = '' }) {
  const vclock = fs.readFileSync(path.join(root, 'js/video/vclock.js'), 'utf8');
  await page.addInitScript({ content: vclock + `\ninstallVClock(${JSON.stringify({ t0, perf0: 1000, seed })});\n` });
  const url = `${base}live.html?mode=replay&fixedres=1&pack=${encodeURIComponent(packUrl)}${extraQuery}`;
  const tb = Date.now();
  await page.goto(url);
  // polled from Node (page.waitForFunction would poll with the page's timers / rAF, which the virtual clock owns)
  for (let i = 0; ; i++) {
    const st = await page.evaluate(() => ({ ok: !!window.__hwdReady, err: window.__hwdError || null }));
    if (st.err) throw new Error('app failed: ' + st.err);
    if (st.ok) break;
    if (Date.now() - tb > 240000) throw new Error('app did not become ready in 240 s');
    await sleep(250);
  }
  return { bootMs: Date.now() - tb, url };
}

// ---------------------------------------------------------------- the frozen app snapshot
// out/video/<case>/app/ = a byte copy of live.html, live.css, js/**, data/**, the replay shim, the job's pack and every other
// file the app requested in the snapshot probe, plus MANIFEST.json (rel path -> sha256) and `tree` = sha256 of the sorted
// "path sha" lines. Every stage serves and imports ONLY the snapshot; the tree hash is part of every stamp (trace, plan,
// frames), so a render can never mix engine, renderer or model versions, whatever the fix rounds change in the working tree.
export const SNAP_BASE = ['live.html', 'live.css', 'js', 'data', 'out/replay/replay_shim.js'];
const SKIP = (rel) => /(^|\/)(\.|__pycache__)/.test(rel) || /^refs\/cache\/local(\/|$)/.test(rel);
export function listFiles(root, rel) {
  const abs = path.join(root, rel); if (!fs.existsSync(abs)) return [];
  const st = fs.statSync(abs); if (st.isFile()) return SKIP(rel) ? [] : [rel];
  const out = []; for (const e of fs.readdirSync(abs).sort()) { const r = rel + '/' + e; if (SKIP(r)) continue; out.push(...listFiles(root, r)); }
  return out;
}
export const treeOf = (files) => sha256(Object.keys(files).sort().map(k => k + ' ' + files[k]).join('\n'));
/** copy `rels` from ROOT into `dir` (fresh) and write the manifest; returns it */
export function makeSnapshot(dir, rels, info = {}) {
  if (fs.existsSync(dir)) fs.rmSync(dir, { recursive: true, force: true });
  const files = {};
  for (const rel of [...new Set(rels)].sort()) {
    const src = path.join(ROOT, rel), dst = path.join(dir, rel); const buf = fs.readFileSync(src);
    fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, buf); files[rel] = sha256(buf);
  }
  // Node resolves the snapshot's .js as ES modules from this package.json (the plan stage imports camera / site from here)
  fs.writeFileSync(path.join(dir, 'package.json'), '{ "type": "module", "private": true }\n');
  const git = spawnSync('git', ['-C', ROOT, 'rev-parse', 'HEAD']).stdout.toString().trim();
  const dirty = spawnSync('git', ['-C', ROOT, 'status', '--porcelain', '--', ...SNAP_BASE.filter(p => !p.startsWith('out/'))]).stdout.toString().split('\n').filter(Boolean).length;
  const M = { v: 1, made: new Date().toISOString(), from: 'the working tree of hwd3d/', git_head: git, git_modified_paths: dirty, ...info, n: Object.keys(files).length, tree: treeOf(files), files };
  fs.writeFileSync(path.join(dir, 'MANIFEST.json'), JSON.stringify(M, null, 1));
  return M;
}
/** replace ONE subtree of an existing snapshot (e.g. 'js/video': a fix of the video pipeline itself) by the working tree's
 *  copy, keeping every other file - the engine, renderer, data and models - exactly as frozen; the manifest records the base
 *  snapshot it came from. The tree hash changes, so scout and plan must run again (the stamps chain refuses old ones). */
export function refreshSnapshot(dir, rel) {
  const M0 = verifySnapshot(dir); const keep = {}, files = {};
  for (const [k, h] of Object.entries(M0.files)) if (k === rel || k.startsWith(rel + '/')) fs.rmSync(path.join(dir, k)); else keep[k] = h;
  for (const r of listFiles(ROOT, rel)) { const buf = fs.readFileSync(path.join(ROOT, r)); fs.mkdirSync(path.dirname(path.join(dir, r)), { recursive: true }); fs.writeFileSync(path.join(dir, r), buf); files[r] = sha256(buf); }
  Object.assign(files, keep);
  const sorted = Object.fromEntries(Object.keys(files).sort().map(k => [k, files[k]]));
  const M = { ...M0, made: new Date().toISOString(), base: { tree: M0.tree, made: M0.made, git_head: M0.git_head, base: M0.base || null }, refreshed: rel,
    refreshed_git_head: spawnSync('git', ['-C', ROOT, 'rev-parse', 'HEAD']).stdout.toString().trim(), n: Object.keys(sorted).length, tree: treeOf(sorted), files: sorted };
  fs.writeFileSync(path.join(dir, 'MANIFEST.json'), JSON.stringify(M, null, 1));
  return M;
}
/** re-hash every file of the snapshot against its manifest; throws on any difference (a missing, changed or added file) */
export function verifySnapshot(dir) {
  const mf = path.join(dir, 'MANIFEST.json');
  if (!fs.existsSync(mf)) throw new Error(`no app snapshot in ${path.relative(ROOT, dir)}: run the 'snapshot' stage first`);
  const M = JSON.parse(fs.readFileSync(mf, 'utf8')); const bad = [];
  for (const [rel, h] of Object.entries(M.files)) { const f = path.join(dir, rel); if (!fs.existsSync(f)) bad.push('missing ' + rel); else if (sha256(fs.readFileSync(f)) !== h) bad.push('changed ' + rel); }
  const have = new Set(Object.keys(M.files));
  for (const rel of listFiles(dir, 'js').concat(listFiles(dir, 'data'))) if (!have.has(rel)) bad.push('added ' + rel);
  if (treeOf(M.files) !== M.tree) bad.push('tree hash');
  if (bad.length) throw new Error(`app snapshot ${path.relative(ROOT, dir)} does not match its manifest (${bad.slice(0, 5).join(', ')}${bad.length > 5 ? ', ...' : ''}): make a new snapshot (then scout and plan again)`);
  return M;
}

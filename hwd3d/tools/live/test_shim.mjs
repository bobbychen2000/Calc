// Headless test of the in-page replay relay (tools/live/replay_shim.js, copied to out/replay/ by build_replay.py) in
// Chromium (Playwright). No server: requests to http://hwd.test/ are answered from disk by page.route. No WebGL.
//
//   node tools/live/test_shim.mjs [--secs 6] [--pack out/replay/pack.json.gz]
//
// Checks (contract docs/phase2_fork_map.md 2.2): installReplay() resolves and the fake ping says hwdlive 1 / replay /
// lookahead_s; a new EventSource gets the last lookahead_s + 5 s of payloads at once (first frame does not wait); the
// stream head runs at wall speed; `now` and `_pt` are shifted to wall time, `dataNow` keeps the recording clock; for an
// app that displays lookahead_s behind the head, aircraft have real fixes on both sides of the display time (the
// recorder's 46-s holes are bracketed); D1 in the pack (type-only: every key x+8hex, no identity fields); METAR only up
// to the replay time; ident answers type only; the soft loop on a 12-s synthetic pack. Prints counts only.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
import { fileURLToPath } from 'url';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const SECS = +arg('--secs', 6);
const PACK = path.resolve(ROOT, arg('--pack', 'out/replay/pack.json.gz'));
const SHIM = path.join(ROOT, 'tools', 'live', 'replay_shim.js');
let fails = 0;
const check = (ok, what) => { console.log((ok ? '  ok   ' : '  FAIL ') + what); if (!ok) fails++; };

if (!fs.existsSync(PACK)) { console.log('no pack at', PACK, '- run python3 tools/live/build_replay.py first'); process.exit(1); }

// a 12-s synthetic pack (the real pack's first events, re-timed) for the loop test
function miniPack() {
  const P = JSON.parse(zlib.gunzipSync(fs.readFileSync(PACK)).toString());
  const ev = P.events.slice(0, 8).map((e, i) => ({ T: P.from + i * 1.5, p: e.p }));
  return zlib.gzipSync(JSON.stringify(Object.assign({}, P, { events: ev, from: ev[0].T, until: ev[ev.length - 1].T, lookahead_s: 2, name: 'mini' })));
}

const PAGE = `<!doctype html><meta charset="utf-8"><title>shim test</title><script type="module">
import { installReplay } from './out/replay/replay_shim.js';
const q = new URLSearchParams(location.search);
const R = window.__res = { t0: Date.now(), events: [] };
try {
  R.info = await installReplay({ url: q.get('pack'), loop: true });
  R.t_install = Date.now() - R.t0;
  R.ping = await (await fetch('api/ping')).json();
  const es = new EventSource('api/stream?delta=1');
  es.addEventListener('adsb', e => { const j = JSON.parse(e.data); R.events.push({ w: Date.now(), now: j.now, dataNow: j.dataNow, seq: j.seq,
    msg: j.msg, ac: j.ac.map(a => ({ hex: a.hex, pt: a._pt, masked: a._masked, keys: Object.keys(a) })) }); });
  R.adsb = await (await fetch('api/adsb')).json();
  const m = await fetch('api/metar?ids=KHWD&format=json'); R.metar = { status: m.status, body: await m.json() };
  R.metarOther = (await fetch('api/metar?ids=KOAK')).status;
  const k = R.adsb.ac.length ? R.adsb.ac[0].hex : 'x00000000';
  const id = await fetch('api/ident?key=' + k); R.ident = { status: id.status, body: await id.json() };
  R.identMissing = (await fetch('api/ident?key=abcdef')).status;
  R.unknown = (await fetch('api/gates')).status;
} catch (e) { R.error = String(e && e.stack || e); }
R.ready = true;
</script>`;

async function run(page, packUrl) {
  await page.goto('http://hwd.test/index.html?pack=' + encodeURIComponent(packUrl));
  await page.waitForFunction(() => window.__res && window.__res.ready, null, { timeout: 30000 });
}

const browser = await chromium.launch();
try {
  const ctx = await browser.newContext();
  const mini = miniPack();
  await ctx.route('http://hwd.test/**', route => {
    const u = new URL(route.request().url());
    if (u.pathname === '/index.html') return route.fulfill({ body: PAGE, contentType: 'text/html' });
    if (u.pathname === '/out/replay/replay_shim.js') return route.fulfill({ body: fs.readFileSync(SHIM), contentType: 'text/javascript' });
    if (u.pathname === '/out/replay/pack.json.gz') return route.fulfill({ body: fs.readFileSync(PACK), contentType: 'application/gzip' });
    if (u.pathname === '/out/replay/mini.json.gz') return route.fulfill({ body: mini, contentType: 'application/gzip' });
    return route.fulfill({ status: 404, body: 'not found' });
  });
  const page = await ctx.newPage();
  page.on('pageerror', e => { console.log('pageerror', e.message); fails++; });

  console.log('real pack:', path.relative(ROOT, PACK));
  await run(page, 'out/replay/pack.json.gz');
  await page.waitForTimeout(SECS * 1000);
  const R = await page.evaluate(() => window.__res);
  check(!R.error, 'no exception' + (R.error ? ': ' + R.error : ''));
  check(R.t_install < 10000, `installReplay resolved in ${R.t_install} ms`);
  const L = R.info.lookahead_s;
  check(R.ping.hwdlive === 1 && R.ping.mode === 'replay' && R.ping.features.replay.lookahead_s === L && L === 60,
        `ping: hwdlive ${R.ping.hwdlive}, mode ${R.ping.mode}, lookahead_s ${L}`);
  check(R.ping.features.metar === 'KHWD' && R.ping.features.taf === null, 'ping features metar KHWD, taf null');
  const ev = R.events, first = ev.filter(e => e.w - ev[0].w < 500);
  const P = JSON.parse(zlib.gunzipSync(fs.readFileSync(PACK)).toString());
  const want = P.events.filter(e => e.T <= P.from + L);
  check(ev.length > 0 && ev[0].w - R.t0 < 5000, `first stream payload ${ev.length ? ev[0].w - R.t0 : '-'} ms after load`);
  // the recorder is bursty (~14 s observed, ~46 s hole), so the first lookahead_s hold one or two bursts: all of them
  // must arrive at once, starting with the pack's first event
  check(first.length >= want.length && first[0].dataNow === want[0].p.dataNow,
        `first burst: ${first.length} payloads at once = every pack event of the first ${L} s (${want.length})`);
  const last = ev[ev.length - 1];
  check(last.now <= Date.now() + 1000 && Date.now() - last.now < 60000, `head 'now' is wall time (${((Date.now() - last.now) / 1000).toFixed(1)} s old)`);
  const off = last.now - last.dataNow;
  check(ev.every(e => Math.abs((e.now - e.dataNow) - off) < 50), 'now - dataNow constant (dataNow = recording clock)');
  const pts = last.ac.map(a => a.pt).filter(x => typeof x === 'number');
  check(pts.length && Math.max(...pts) <= last.now / 1000 + 1 && Math.max(...pts) > last.now / 1000 - 70, '_pt shifted to wall time');
  // bracketing: the app shows D = now - L; an aircraft needs a fix at or before D and one after it
  const D = Date.now() / 1000 - L, fixes = {};
  for (const e of ev) for (const a of e.ac) if (typeof a.pt === 'number') (fixes[a.hex] = fixes[a.hex] || new Set()).add(a.pt);
  let both = 0, n = 0;
  for (const [k, s] of Object.entries(fixes)) {
    const arr = [...s]; if (Math.max(...arr) < D - 30) continue;      // gone before the display time
    n++; if (arr.some(t => t <= D) && arr.some(t => t > D)) both++;
  }
  check(n > 5 && both / n >= 0.8, `display time head-${L}s bracketed by real fixes for ${both}/${n} aircraft`);
  const keys = new Set(ev.flatMap(e => e.ac.map(a => a.hex)));
  const ident = ['flight', 'r', 'ownOp', 'year', 'squawk', 'dbFlags', '_mx'];
  if (R.info.d1 && R.info.d1.ident === 'type-only') {
    check([...keys].every(k => /^x[0-9a-f]{8}$/.test(k)), `type-only pack: all ${keys.size} keys x+8hex`);
    check(ev.every(e => e.ac.every(a => !a.keys.some(f => ident.includes(f)))), 'type-only pack: no identity field');
  }
  check(R.metar.status === 200 && R.metar.body.length > 0 &&
        R.metar.body.every(m => m.obsTime * 1000 <= last.dataNow + 1000), `metar: ${R.metar.body.length} reports, none after the replay time`);
  check(R.metarOther === 400, 'metar of another station: 400');
  check(R.ident.status === 200 && (R.ident.body.masked ? Object.keys(R.ident.body).every(k => ['key', 'masked', 't', 'desc', 'category'].includes(k)) : true),
        `ident: ${R.ident.status}, masked ${R.ident.body.masked}`);
  check(R.identMissing === 404 && R.unknown === 404, 'ident of a key not in the picture 404; api/gates 404');
  const sq = ev.map(e => e.seq);
  check(sq.every((s, i) => i === 0 || s > sq[i - 1]), 'seq increases');

  console.log('loop (12-s synthetic pack, lookahead 2 s):');
  const p2 = await ctx.newPage();
  await run(p2, 'out/replay/mini.json.gz');
  await p2.waitForTimeout(18000);
  const M = await p2.evaluate(() => window.__res);
  const restarts = M.events.filter(e => e.msg === 'replay restarts').length;
  const after = M.events.filter((e, i) => i > 0 && M.events[i - 1].msg === 'replay restarts');
  check(!M.error && restarts >= 1, `loop: ${restarts} restart(s) in 18 s`);
  check(after.length >= 1 && after.every(e => e.ac.length > 0), 'loop: traffic again after the restart');
  check(M.events.map(e => e.seq).every((s, i, a) => i === 0 || s > a[i - 1]), 'loop: seq keeps increasing across restarts');
} finally {
  await browser.close();
}
console.log('\nRESULT:', fails ? `FAIL (${fails})` : 'PASS');
process.exit(fails ? 1 : 0);

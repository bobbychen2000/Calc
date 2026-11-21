// Integration checks of SHA Live 3D (P2f): every extension loads together, the browser console stays clean, the modes
// work (snapshot, live through a relay, relay requested but offline), and the frame time per quality tier. Run through
// the harness:
//   SOFTGL=1 node livetest.mjs jobs/integration.mjs                                   # snapshot + offline scenes
//   SOFTGL=1 RELAY=http://127.0.0.1:8792 SCENES=snapshot,live,offline node livetest.mjs jobs/integration.mjs
//   SOFTGL=1 SCENES=perf TIERS=low,medium,high,ultra node livetest.mjs jobs/integration.mjs   # frame time per tier
// SCENES (','-separated): snapshot | live (needs RELAY= or MOCK_RELAY=1) | offline (?relay=1 with the API answering 503) |
//   standalone (live, but the page and all static files served by the relay at RELAY, i.e. its allow-list) |
//   park (snapshot + ?park=<PARK list>: debug-parked aircraft, docked bridges) | perf (frame time per tier, TIERS).
// Every console message is recorded with its type; 'error' and 'warning' messages, page errors, HTTP >= 400 answers and
// failed requests count as problems (Google Fonts are answered locally by the harness; the GPU-stall notices of Mesa are
// ignored as in livetest.mjs). Exit code 1 if any scene has a problem. Never contacts a provider: the live scene goes
// through the relay given in RELAY (which itself rate-limits aviationweather.gov), never adsb.lol or OpenSky.
const IGNORE = /GPU stall due to ReadPixels|GL Driver Message|Automatic fallback to software WebGL|fonts\.g/;
export default async ({ page, base }) => {
  const scenes = (process.env.SCENES || 'snapshot,offline').split(',').filter(Boolean);
  const T = process.env.T ? '&t=' + encodeURIComponent(process.env.T) : '';
  const log = { console: [], errors: [], http: [], failed: [] }; let OFFLINE = false;
  page.on('console', m => { const t = m.text(); if (IGNORE.test(t)) return;
    // the browser's own network log line for the deliberate 503 of the offline scene is expected, not a problem
    const url = (m.location() && m.location().url) || ''; const expected = OFFLINE && /Failed to load resource/.test(t) && /\/api\//.test(url);
    log.console.push({ type: expected ? 'expected' : m.type(), text: (expected ? '(expected in the offline scene) ' : '') + t.slice(0, 600) + (url && /Failed to load/.test(t) ? ' <' + url + '>' : '') }); });
  page.on('pageerror', e => log.errors.push(String(e.message || e).slice(0, 600)));
  // (in the offline scene the harness answers /api/* with 503 on purpose: those are expected, not problems)
  page.on('response', r => { if (r.status() >= 400 && !(OFFLINE && /\/api\//.test(r.url()))) log.http.push(r.status() + ' ' + r.url()); });
  page.on('requestfailed', r => { if (!/fonts\.g/.test(r.url())) log.failed.push((r.failure() && r.failure().errorText) + ' ' + r.url()); });
  const reset = () => { log.console.length = 0; log.errors.length = 0; log.http.length = 0; log.failed.length = 0; };
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  const ready = async () => { await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 }); return page.evaluate(() => window.__shaError || null); };
  let bad = 0;
  const report = (name, extra) => {
    const probs = log.console.filter(m => m.type === 'error' || m.type === 'warning');
    const n = probs.length + log.errors.length + log.http.length + log.failed.length;
    console.log(`scene ${name}: console ${log.console.length} messages (${log.console.filter(m => m.type === 'error').length} error, ${log.console.filter(m => m.type === 'warning').length} warning), page errors ${log.errors.length}, HTTP>=400 ${log.http.length}, failed requests ${log.failed.length} -> ${n ? 'PROBLEMS' : 'clean'}`);
    for (const m of log.console) console.log(`  [${m.type}] ${m.text}`);
    for (const e of log.errors) console.log('  [pageerror]', e);
    for (const e of log.http) console.log('  [http]', e);
    for (const e of log.failed) console.log('  [failed]', e);
    if (extra) console.log('  ' + JSON.stringify(extra));
    if (n) bad++;
  };
  // a short tour through the views every scene visits (the extensions' frame / lights hooks and the stand labels run)
  const tour = async () => {
    for (const v of ['overview', 't2', 't1', 'runways', 'tower', 'top']) { await page.evaluate((v) => SHA.qa.view(v), v); await frames(3); }
    await page.evaluate(() => SHA.qa.stand('233')); await frames(3);
    await page.evaluate(() => SHA.qa.view('overview')); await frames(2);
  };
  const sceneInfo = () => page.evaluate(() => {
    const i = SHA.qa.info(); const w = i.world || {};
    const ext = {}; for (const k of i.extensions) ext[k] = w[k] === undefined ? '(no buildWorld)' : typeof w[k] === 'string' ? w[k] : 'ok';
    return { quality: i.quality, extensions: i.extensions, ext, mode: SHA.qa.mode ? SHA.qa.mode() : null, status: (document.querySelector('#status') || {}).textContent || null,
      note: (SHA.ui.el.note && SHA.ui.el.note.textContent) || null, runway: SHA.runwayMode ? (({ dir, flow, arr, dep, rule }) => ({ dir, flow, arr, dep, rule }))(SHA.runwayMode() || {}) : null,
      items: SHA.world.items.length, gates: SHA.qa.gates ? (({ stands, contact, remote, bridges, vdgs, refTypeDocks }) => ({ stands, contact, remote, bridges, vdgs, refTypeDocks }))((SHA.qa.gates() || {}).summary || {}) : null };
  });
  for (const sc of scenes) {
    if (sc === 'perf') continue;
    reset(); OFFLINE = sc === 'offline';
    if (OFFLINE) await page.route(/\/api\//, r => r.fulfill({ status: 503, contentType: 'application/json', body: '{"error":"offline (harness)"}' }));
    const q = sc === 'live' || sc === 'standalone' ? '?relay=1' : sc === 'offline' ? '?relay=1' : sc === 'park' ? '?park=' + encodeURIComponent(process.env.PARK || '233,230,113,404') : '?';
    // standalone: the page and every static file come from the relay itself (sha_live_server.py's allow-list), as a user
    // running the relay sees it; the other scenes are served by the harness (repository root) with /api/* proxied
    if (sc === 'standalone' && !process.env.RELAY) { console.log('scene standalone needs RELAY=http://host:port'); continue; }
    const B = sc === 'standalone' ? process.env.RELAY.replace(/\/$/, '') + '/sha3d/' : base;
    const t0 = Date.now();
    await page.goto(B + 'live.html' + q + '&fixedres=1&quality=' + (process.env.QUALITY || 'high') + T);
    const err = await ready(); const tBoot = (Date.now() - t0) / 1000;
    if (err) { console.log('APP ERROR', err); log.errors.push('APP ERROR ' + err); report(sc); if (OFFLINE) await page.unroute(/\/api\//); continue; }
    await tour();
    if (sc === 'live' || sc === 'standalone') await page.waitForTimeout(2500);   // the TAF / ADS-B polls of the shell
    const info = await sceneInfo(); info.bootS = +tBoot.toFixed(1);
    if (sc === 'park') info.parked = await page.evaluate(() => SHA.qa.parked());
    report(sc, info);
    if (OFFLINE) { await page.unroute(/\/api\//); OFFLINE = false; }
  }
  if (scenes.includes('perf')) {
    // frame time per tier: fixed resolution (no dynamic scaling), the same three views, 40 frames after 10 warm-up frames;
    // the time between requestAnimationFrame callbacks (CPU + llvmpipe raster: this sandbox has no GPU - reference only)
    const tiers = (process.env.TIERS || 'low,medium,high,ultra').split(',');
    const rows = [];
    for (const tier of tiers) {
      reset();
      await page.goto(base + 'live.html?mode=snapshot&fixedres=1&quality=' + tier + T);
      const err = await ready(); if (err) { console.log('APP ERROR', tier, err); continue; }
      await page.evaluate(() => SHA.qa.hideUI(true));
      // counters: main-thread JS time in scene.frame + R.render + R.present, and WebGL draw calls / triangles per frame
      await page.evaluate(() => {
        const P = window.__perf = { js: 0, draws: 0, tris: 0 };
        const wrap = (o, k) => { const f = o[k].bind(o); o[k] = (...a) => { const t = performance.now(); try { return f(...a); } finally { P.js += performance.now() - t; } }; };
        wrap(SHA.scene, 'frame'); wrap(SHA.R, 'render'); wrap(SHA.R, 'present');
        const g = document.getElementById('gl').getContext('webgl2'); const TRI = g.TRIANGLES;
        const cnt = (mode, n, inst = 1) => { P.draws++; if (mode === TRI) P.tris += n / 3 * inst; };
        for (const [k, fn] of [['drawElements', (a) => cnt(a[0], a[1])], ['drawArrays', (a) => cnt(a[0], a[2])], ['drawElementsInstanced', (a) => cnt(a[0], a[1], a[4])], ['drawArraysInstanced', (a) => cnt(a[0], a[2], a[3])]]) {
          const o = g[k].bind(g); g[k] = (...a) => { fn(a); return o(...a); }; }
      });
      const row = { tier, px: await page.evaluate(() => [SHA.R.W, SHA.R.H]) };
      for (const v of ['overview', 't2', 'stand:233']) {
        await page.evaluate((v) => v.startsWith('stand:') ? SHA.qa.stand(v.slice(6)) : SHA.qa.view(v), v);
        await frames(10);
        row[v] = await page.evaluate(() => new Promise(r => { const P = window.__perf; P.js = 0; P.draws = 0; P.tris = 0; const ts = []; let k = 0; const N = 40;
          const f = (t) => { ts.push(t); if (++k > N) { const d = ts.slice(1).map((x, i) => x - ts[i]).sort((a, b) => a - b);
            r({ median: +d[d.length >> 1].toFixed(1), p90: +d[Math.floor(d.length * 0.9)].toFixed(1), jsMs: +(P.js / N).toFixed(1), draws: Math.round(P.draws / N), ktris: Math.round(P.tris / N / 1000) }); } else requestAnimationFrame(f); };
          requestAnimationFrame(f); }));
      }
      rows.push(row); console.log('perf', JSON.stringify(row));
      const probs = log.console.filter(m => m.type === 'error' || m.type === 'warning').length + log.errors.length;
      if (probs) report('perf ' + tier);
    }
    console.log('perf table (ms per frame, median / p90):');
    for (const r of rows) console.log(`  ${r.tier.padEnd(7)} ${r.px.join('x').padEnd(10)} ` + ['overview', 't2', 'stand:233'].map(v => `${v} ${r[v].median}/${r[v].p90} (js ${r[v].jsMs}, ${r[v].draws} draws, ${r[v].ktris}k tris)`).join('  '));
  }
  console.log(bad ? `INTEGRATION: ${bad} scene(s) with problems` : 'INTEGRATION: all scenes clean');
  if (bad) process.exitCode = 1;
};

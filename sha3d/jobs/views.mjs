// Named views of the SHA Live 3D scene (renders for QA). Run through the harness:
//   SOFTGL=1 OUT=docs/phase2 PREFIX=core node livetest.mjs jobs/views.mjs
//   SOFTGL=1 OUT=docs/phase2 PREFIX=view T=snapshot VIEWS=@full node livetest.mjs jobs/views.mjs     (the P2f named set)
// VIEWS (';'-separated, default below; '@full' = the P2f integration set FULL below):
//   overview | top | runways | t1 | t2      the app's named views (js/live/app.js VIEWS)
//   rwy:<end>                              threshold view (18L 36R 18R 36L): behind the landing threshold, looking along it
//   tower                                  orbit view of the control tower; towercab = the app's tower view (from the cab)
//   stand:<name>[,<icao>|-][,<dist>,<side>,<pitch>]   the app's stand view; with <icao> a QA-only model is placed there
//                                          (SHA.qa.placeModel, cleared before the next view)
//   bridge:<name>[,<dist>,<pitch>,<side>]  the stand's jet bridge from the apron (gates package SHA.qa.bridgeView)
//   hold:<taxiway ref>|hold:<n>[,<dist>,<pitch>,<side deg>]   a runway-holding position (markings SHA.markings.holds())
//   look:x,y,z,yaw,pitch,dist[,fov]
//   park:<stand>[:<ICAO>][+<stand>[:<ICAO>]...]   DEBUG: park static aircraft (gates SHA.qa.park; the class reference
//                                          type unless <ICAO>), dock the bridges; they stay until 'unpark'. No render.
//   unpark                                 remove every debug-parked aircraft. No render.
//   ui:<state>                             (needs SHOWUI=1) legend | card:<stand> | fly:<stand> | nocard | about | close - no render
//   <view>@<name>                          render <view> under the file name <PREFIX>_<name>.png
// Other env: T (ISO time for the sun, default 2026-11-14T03:00:00Z = 11:00 local; T=snapshot = no ?t=, i.e. the app's
// default snapshot instant and its recorded weather), QUERY (extra URL query), WAIT_MS, SHOWUI=1 (keep the HUD),
// QUALITY (default high; MOBILE / DEVICE runs usually pass low), CLOCK=<ISO> (integration fix round 3, review V7: the page's
// wall clock is pinned with Playwright page.clock.setFixedTime - Date.now / new Date return that instant, timers and frames
// run normally - so live-mode UI views (pill, clock) are the same in every round; use it with MOCK_RELAY=1 and T=<ISO>).
// Writes <OUT>/<PREFIX>_<view>.png and prints the scene info (orientation checks: T2 west, T1 east, runways N-S) and, for
// park, which bridges docked.
const DEFAULT = 'overview;top;runways;rwy:18L;rwy:36R;rwy:18R;rwy:36L;t1;t2;tower;towercab;stand:233,A320';
// P2f integration set: the named views with class-correct debug-parked aircraft (bridges docked) at a T2 pier, T1 and a
// remote stand (T2 north pier 229 E / 230 EL / 231 C / 233 C / 234 C, T1 113 C / 102 EL, west remote 403 C / 404 C)
const FULL = 'overview;rwy:18L;rwy:36R;rwy:18R;rwy:36L;t1;t2;tower;towercab;' +
  'park:229+230+231+233+234+113+115+102+403+404;' +
  'stand:233,-,70,1,24;look:-860,2.5,-180,60,22,140@bridge_230;stand:113,-,75,1,22;stand:102,-,110,1,20;stand:404,-,75,1,22;hold:H1;t2pier';
export default async ({ page, shot, base }) => {
  const t = process.env.T || '2026-11-14T03:00:00Z';
  const q = `?fixedres=1&quality=${process.env.QUALITY || 'high'}${t === 'snapshot' ? '' : '&t=' + encodeURIComponent(t)}${process.env.MOCK_RELAY || process.env.RELAY ? '&relay=1' : ''}${process.env.QUERY ? '&' + process.env.QUERY : ''}`;
  if (process.env.CLOCK) { await page.clock.setFixedTime(new Date(process.env.CLOCK)); console.log('clock pinned', new Date(process.env.CLOCK).toISOString()); }
  await page.goto(base + 'live.html' + q);
  await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__shaError || null); if (err) { console.log('APP ERROR', err); throw new Error(err); }
  const info = await page.evaluate(() => SHA.qa.info());
  console.log('info', JSON.stringify({ ...info, world: Object.fromEntries(Object.entries(info.world || {}).map(([k, v]) => [k, typeof v === 'object' && v && JSON.stringify(v).length > 400 ? '(' + Object.keys(v).length + ' keys)' : v])) }));
  // orientation checks from the data the app uses (not from the renders)
  const a = info.anchors; const rw = info.runways;
  const xr = await page.evaluate(() => SHA.geo.RUNWAYS.map(r => [r.a[0], r.b[0]]).flat());
  console.log('check: T2 x', a.t2 && a.t2.pos[0].toFixed(0), '< runway x min', Math.min(...xr).toFixed(0), '->', a.t2 && a.t2.pos[0] < Math.min(...xr) ? 'T2 WEST ok' : 'FAIL');
  console.log('check: T1 x', a.t1 && a.t1.pos[0].toFixed(0), '> runway x max', Math.max(...xr).toFixed(0), '->', a.t1 && a.t1.pos[0] > Math.max(...xr) ? 'T1 EAST ok' : 'FAIL');
  console.log('check: runway headings', rw.map(r => r.id + ' ' + r.hdg.toFixed(2)).join(', '), rw.every(r => Math.abs(((r.hdg % 180) + 180) % 180 - 177.3) < 1) ? 'N-S ok' : 'FAIL');
  if (!process.env.SHOWUI) await page.evaluate(() => SHA.qa.hideUI(true));   // SHOWUI=1 keeps the HUD (phone / laptop layout checks)
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  const wait = +(process.env.WAIT_MS || 0);
  const list = (process.env.VIEWS === '@full' ? FULL : process.env.VIEWS || DEFAULT).split(';').filter(Boolean);
  for (const v0 of list) {
    const [v, nameAs] = v0.includes('@') ? v0.split('@') : [v0, null];   // '<view>@<name>': render under that file name
    const [kind, arg] = v.includes(':') ? [v.slice(0, v.indexOf(':')), v.slice(v.indexOf(':') + 1)] : [v, null];
    const A = arg ? arg.split(',') : [];
    let ok = true;
    await page.evaluate(() => SHA.qa.clearModels());
    if (kind === 'park') {
      for (const it of arg.split('+')) {
        const [n, icao] = it.split(':');
        const r = await page.evaluate(([n, i]) => SHA.qa.park ? SHA.qa.park(n, i || null, false) : { ok: false, why: 'no gates package' }, [n, icao || null]);
        console.log('park', n, JSON.stringify(r));
      }
      await frames(3); continue;
    }
    if (kind === 'unpark') { await page.evaluate(() => SHA.qa.unparkAll && SHA.qa.unparkAll()); await frames(2); continue; }
    if (kind === 'ui') {
      const r = await page.evaluate((a) => {
        if (a === 'legend') return SHA.qa.openLegend(true);
        if (a.startsWith('card:')) return SHA.qa.selectStand(a.slice(5), false);   // card as opened from a label (camera stays)
        if (a.startsWith('fly:')) return SHA.qa.selectStand(a.slice(4), true);     // card + "Fly to stand" (phone: compact card)
        if (a === 'nocard') return SHA.qa.closeCard();
        if (a === 'about') return SHA.qa.openAbout(true);
        if (a === 'close') { SHA.qa.openAbout(false); SHA.qa.openSettings(false); SHA.qa.openLegend(false); return true; }
        return false;
      }, arg);
      console.log('ui', arg, r); await frames(2); continue;
    }
    if (kind === 'rwy') ok = await page.evaluate((e) => SHA.qa.threshold(e), arg);
    else if (kind === 'tower') ok = await page.evaluate(() => SHA.qa.tower());
    else if (kind === 'towercab') ok = await page.evaluate(() => SHA.qa.view('tower'));
    else if (kind === 'stand') {
      const [name, icao] = A; const d = A.slice(2).map(Number);
      ok = await page.evaluate(([n, d]) => SHA.qa.stand(n, d[0] || undefined, d[1] || undefined, d[2] || undefined), [name, d]);
      if (ok && icao && icao !== '-') { const r = await page.evaluate(([n, i]) => SHA.qa.placeModel(n, i), [name, icao]); console.log('qa model', JSON.stringify(r)); }
    }
    else if (kind === 'bridge') ok = await page.evaluate(([n, d]) => SHA.qa.bridgeView ? SHA.qa.bridgeView(n, d[0] || undefined, d[1] || undefined, d[2] || undefined) : false, [A[0], A.slice(1).map(Number)]);
    else if (kind === 'hold') ok = await page.evaluate((a) => {
      if (!SHA.markings) return false; const H = SHA.markings.holds(); const DEG = Math.PI / 180; const vh = (x, z) => Math.atan2(x, -z) / DEG;
      const h = /^\d+$/.test(a[0]) ? H[+a[0]] : H.find(x => x.ref === a[0] && x.kind === 'A' && !x.exitOnly) || H.find(x => x.ref === a[0]);
      if (!h) return false; const side = (+(a[3] || 20)) * DEG; const c = Math.cos(side), s = Math.sin(side);
      const d = [-(h.u[0] * c - h.u[1] * s), -(h.u[0] * s + h.u[1] * c)];   // camera on the holding side, turned by `side`
      SHA.qa.look([h.p[0] + h.u[0] * 4, SHA.geo.GROUND_Y, h.p[1] + h.u[1] * 4], vh(d[0], d[1]), +(a[2] || 30), +(a[1] || 48), 50); return true;
    }, A);
    else if (kind === 't2pier') ok = await page.evaluate(() => {   // the T2 north pier tip from the north-east (centre of stands 229-234)
      const S = (SHA.data.stands.stands || []).filter(x => ['229', '230', '231', '233', '234'].includes(x.name)); if (!S.length) return false;
      const c = [0, 1].map(k => S.reduce((a, s) => a + s.nose[k], 0) / S.length); SHA.qa.look([c[0], SHA.geo.GROUND_Y + 5, c[1]], 45, 24, 250, 50); return true; });
    else if (kind === 'look') { const p = A.map(Number); ok = await page.evaluate((p) => { SHA.qa.look([p[0], p[1], p[2]], p[3], p[4], p[5], p[6] || 50); return true; }, p); }
    else ok = await page.evaluate((n) => SHA.qa.view(n), kind);
    if (!ok) { console.log('view not available:', v); continue; }
    await frames(4); if (wait) await page.waitForTimeout(wait); await frames(2);
    const cam = await page.evaluate(() => { const c = SHA.rig.camera(); return { pos: c.pos.map(x => +x.toFixed(1)), target: c.target ? c.target.map(x => +x.toFixed(1)) : null }; });
    console.log('view', v, JSON.stringify(cam));
    // file name: the view without its camera numbers (stand:233,A320 -> stand_233_A320; stand:233,-,70,1,24 -> stand_233)
    const nm = nameAs ? nameAs : kind === 'stand' ? `stand_${A[0]}${A[1] && A[1] !== '-' ? '_' + A[1] : ''}` : ['rwy', 'bridge', 'hold'].includes(kind) ? `${kind}_${A[0]}` : v.replace(/[:,]/g, '_');
    await shot((process.env.PREFIX || 'view') + '_' + nm);
  }
};

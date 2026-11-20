// Named views of the SHA Live 3D scene (renders for QA). Run through the harness:
//   SOFTGL=1 OUT=docs/phase2 PREFIX=core node livetest.mjs jobs/views.mjs
// VIEWS (';'-separated, default below): overview | top | runways | rwy:<end> (threshold view: 18L 36R 18R 36L) | t1 | t2 |
//   tower (orbit view of the tower) | towercab (the app's tower view: from the cab) | stand:<name>[,<icao>] (stand view;
//   with <icao> a QA-only model of that type is parked there for scale, e.g. stand:233,A320) |
//   look:x,y,z,yaw,pitch,dist[,fov]
// Other env: T (ISO time for the sun, default 2026-11-14T03:00:00Z = 11:00 local), QUERY (extra URL query), WAIT_MS,
// SHOWUI=1 (keep the HUD), QUALITY (default high).
// Writes <OUT>/<PREFIX>_<view>.png and prints the scene info (orientation checks: T2 west, T1 east, runways N-S).
const DEFAULT = 'overview;top;runways;rwy:18L;rwy:36R;rwy:18R;rwy:36L;t1;t2;tower;towercab;stand:233,A320';
export default async ({ page, shot, base }) => {
  const t = process.env.T || '2026-11-14T03:00:00Z';
  const q = `?fixedres=1&quality=${process.env.QUALITY || 'high'}&t=${encodeURIComponent(t)}${process.env.MOCK_RELAY ? '&relay=1' : ''}${process.env.QUERY ? '&' + process.env.QUERY : ''}`;
  await page.goto(base + 'live.html' + q);
  await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__shaError || null); if (err) { console.log('APP ERROR', err); throw new Error(err); }
  const info = await page.evaluate(() => SHA.qa.info());
  console.log('info', JSON.stringify(info));
  // orientation checks from the data the app uses (not from the renders)
  const a = info.anchors; const rw = info.runways;
  const xr = await page.evaluate(() => SHA.geo.RUNWAYS.map(r => [r.a[0], r.b[0]]).flat());
  console.log('check: T2 x', a.t2 && a.t2.pos[0].toFixed(0), '< runway x min', Math.min(...xr).toFixed(0), '->', a.t2 && a.t2.pos[0] < Math.min(...xr) ? 'T2 WEST ok' : 'FAIL');
  console.log('check: T1 x', a.t1 && a.t1.pos[0].toFixed(0), '> runway x max', Math.max(...xr).toFixed(0), '->', a.t1 && a.t1.pos[0] > Math.max(...xr) ? 'T1 EAST ok' : 'FAIL');
  console.log('check: runway headings', rw.map(r => r.id + ' ' + r.hdg.toFixed(2)).join(', '), rw.every(r => Math.abs(((r.hdg % 180) + 180) % 180 - 177.3) < 1) ? 'N-S ok' : 'FAIL');
  if (!process.env.SHOWUI) await page.evaluate(() => SHA.qa.hideUI(true));   // SHOWUI=1 keeps the HUD (phone / laptop layout checks)
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  const wait = +(process.env.WAIT_MS || 0);
  for (const v of (process.env.VIEWS || DEFAULT).split(';').filter(Boolean)) {
    const [kind, arg] = v.includes(':') ? [v.slice(0, v.indexOf(':')), v.slice(v.indexOf(':') + 1)] : [v, null];
    let ok = true;
    await page.evaluate(() => SHA.qa.clearModels());
    if (kind === 'rwy') ok = await page.evaluate((e) => SHA.qa.threshold(e), arg);
    else if (kind === 'tower') ok = await page.evaluate(() => SHA.qa.tower());
    else if (kind === 'towercab') ok = await page.evaluate(() => SHA.qa.view('tower'));
    else if (kind === 'stand') { const [name, icao] = arg.split(','); ok = await page.evaluate((n) => SHA.qa.stand(n), name);
      if (ok && icao) { const r = await page.evaluate(([n, i]) => SHA.qa.placeModel(n, i), [name, icao]); console.log('qa model', JSON.stringify(r)); } }
    else if (kind === 'look') { const p = arg.split(',').map(Number); ok = await page.evaluate((p) => { SHA.qa.look([p[0], p[1], p[2]], p[3], p[4], p[5], p[6] || 50); return true; }, p); }
    else ok = await page.evaluate((n) => SHA.qa.view(n), kind);
    if (!ok) { console.log('view not available:', v); continue; }
    await frames(4); if (wait) await page.waitForTimeout(wait); await frames(2);
    const cam = await page.evaluate(() => { const c = SHA.rig.camera(); return { pos: c.pos.map(x => +x.toFixed(1)), target: c.target ? c.target.map(x => +x.toFixed(1)) : null }; });
    console.log('view', v, JSON.stringify(cam));
    await shot((process.env.PREFIX || 'view') + '_' + v.replace(/[:,]/g, '_'));
  }
};

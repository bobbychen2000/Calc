// Markings package renders (CAAC MH 5001-2021 paint and signs). Run through the harness:
//   SOFTGL=1 OUT=docs/phase2 PREFIX=markings node livetest.mjs jobs/markings.mjs
// VIEWS (';'-separated; default below):
//   thr:<id>                                          the app's threshold view (SHA.qa.threshold, = views.mjs rwy:<id>): stripe count check
//   end:<id>[,<m from the threshold>,<dist>,<pitch>]  close view of a runway end (camera behind, looking along the landing direction)
//   endtop:<id>[,<m>,<height>]                        near-vertical view of a runway-end section (layout check)
//   hold:<n>|hold:<taxiway ref>[,<dist>,<pitch>,<side deg>]  runway-holding position (n = index in SHA.markings.holds())
//   stand:<name>[,<dist>,<side>,<pitch>]             the app's stand view
//   standm:<name>,<icao>[,<dist>,<side>,<pitch>,<yaw offset>]  same with a QA-only parked model (scale / photo comparison)
//   plate:<stand>[,<dist>,<pitch>]                    the start of a stand's lead-in (stand number plate)
//   view:<name>                                        the app's named views (overview, runways, t1, t2, top)
//   look:x,y,z,yaw,pitch,dist[,fov]
//   park:<stand>[:<ICAO>]+...                         DEBUG static aircraft (SHA.qa.park, as views.mjs park:) for the night views
// Other env as jobs/views.mjs (T, QUALITY, WAIT_MS, SHOWUI). Prints the runway marking plan, the decal / sign counts and
// (fix round 2) the apron light-map statistics (SHA.markings.apronLight(); the mast pools arrive on the first frames).
// Fix round 3 (review V1): once the pools are in, prints the stand-floor summary (stand nodes below standLevel, which must be
// 0) and, with LIGHTTABLE=1, the per-stand table from SHA.markings.apronLight().at(stop node): name, class, contact, factor,
// factor / standLevel, factor / stand mean, stand flag of the texel.
const DEFAULT = 'end:18L;end:36R;end:18R;end:36L;endtop:18L,40,260;endtop:18R,40,330;hold:H1;hold:B3;stand:233';
export default async ({ page, shot, base }) => {
  const t = process.env.T || '2026-11-14T03:00:00Z';
  const q = `?fixedres=1&quality=${process.env.QUALITY || 'high'}&t=${encodeURIComponent(t)}${process.env.QUERY ? '&' + process.env.QUERY : ''}`;
  await page.goto(base + 'live.html' + q);
  await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__shaError || null); if (err) { console.log('APP ERROR', err); throw new Error(err); }
  const info = await page.evaluate(() => ({ world: SHA.qa.info().world.markings, m: SHA.markings ? SHA.markings.info() : null }));
  console.log('markings', JSON.stringify(info.world));
  // fix round 2: the apron light map (night flood: apron + airside fill + spill, mast pools; js/live/markings.js apronLightMap)
  console.log('apron light', JSON.stringify(await page.evaluate(() => { const L = SHA.markings.apronLight && SHA.markings.apronLight(); if (!L) return null; const { at, ...st } = L; return st; })));
  if (!process.env.SHOWUI) await page.evaluate(() => SHA.qa.hideUI(true));
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  // fix round 3 (V1): wait for the mast pools (first frame after the gates package's masts), then the per-stand light table
  for (let k = 0; k < 20; k++) { if (await page.evaluate(() => { const L = SHA.markings.apronLight && SHA.markings.apronLight(); return !L || !!L.masts; })) break; await frames(1); }
  const lt = await page.evaluate(() => {
    const L = SHA.markings.apronLight && SHA.markings.apronLight(); if (!L || !L.masts) return null;
    const M = L.masts; const ST = (SHA.data && SHA.data.stands ? SHA.data.stands.stands : (window.SHA_STANDS || {}).stands) || [];
    const rows = ST.map(s => { const a = L.at(s.nose[0], s.nose[1]); const contact = !!(s.contact || (s.bridges && s.bridges.length));
      return { n: s.name, cls: s.cls, contact, f: +a[1].toFixed(3), rel: +(a[1] / M.standLevel).toFixed(3), relMean: +(a[1] / M.standMeanFactor).toFixed(3), stand: a[2] }; });
    const fs = rows.map(r => r.f).sort((a, b) => a - b);
    return { masts: M.n, standLevel: M.standLevel, standMean: M.standMeanFactor, otherFloor: M.otherFloorFactor, gain: M.gain, nodes: rows.length,
      belowStandLevel: rows.filter(r => r.f < M.standLevel - 1e-6).map(r => r.n), atStandLevel: rows.filter(r => Math.abs(r.f - M.standLevel) < 0.006).length,
      min: fs[0], p10: fs[Math.floor(fs.length * 0.1)], median: fs[Math.floor(fs.length / 2)], max: fs[fs.length - 1], notStandTexel: rows.filter(r => !r.stand).map(r => r.n), rows };
  });
  if (lt) { const { rows, ...sum } = lt; console.log('apron light pools', JSON.stringify(await page.evaluate(() => SHA.markings.apronLight().masts)));
    console.log('stand light summary', JSON.stringify(sum));
    if (process.env.LIGHTTABLE) { console.log('stand light table: name cls contact factor factor/standLevel factor/standMean standTexel');
      for (const r of rows) console.log('  ' + [r.n, r.cls, r.contact ? 'contact' : 'remote', r.f.toFixed(3), r.rel.toFixed(3), r.relMean.toFixed(3), r.stand].join(' ')); } }
  else console.log('stand light summary: no mast pools yet');
  for (const v of (process.env.VIEWS || DEFAULT).split(';').filter(Boolean)) {
    const [kind, arg] = v.includes(':') ? [v.slice(0, v.indexOf(':')), v.slice(v.indexOf(':') + 1)] : [v, null];
    const a = arg ? arg.split(',') : [];
    if (kind === 'park') {   // as views.mjs park: (DEBUG static aircraft, bridges dock)
      for (const it of arg.split('+')) { const [n, icao] = it.split(':'); const r = await page.evaluate(([n, i]) => SHA.qa.park ? SHA.qa.park(n, i || null, false) : { ok: false, why: 'no gates package' }, [n, icao || null]); console.log('park', n, JSON.stringify(r)); }
      await frames(3); continue;
    }
    await page.evaluate(() => SHA.qa.clearModels());
    if (kind === 'standm') { const r = await page.evaluate(([n, i]) => SHA.qa.placeModel(n, i), [arg.split(',')[0], arg.split(',')[1]]); console.log('qa model', JSON.stringify(r)); }
    const ok = await page.evaluate(([kind, a]) => {
      const G = SHA.geo, DEG = Math.PI / 180; const vh = (x, z) => Math.atan2(x, -z) / DEG; const gy = G.GROUND_Y;
      if (kind === 'end' || kind === 'endtop') {
        const E = G.runwayEnd(a[0]); if (!E) return false; const h = G.hdgVec(E.hdg);
        const m = +(a[1] || 60); const tgt = [E.thr[0] + h[0] * m, gy, E.thr[1] + h[1] * m];
        if (kind === 'end') SHA.qa.look(tgt, vh(-h[0], -h[1]), +(a[3] || 14), +(a[2] || 190), 45);
        else SHA.qa.look(tgt, vh(-h[0], -h[1]), 82, +(a[2] || 260), 40);
        return true;
      }
      if (kind === 'hold') {
        const H = SHA.markings.holds(); let h = /^\d+$/.test(a[0]) ? H[+a[0]] : H.find(x => x.ref === a[0] && x.kind === 'A' && !x.exitOnly) || H.find(x => x.ref === a[0]);
        if (!h) return false; const side = (+(a[3] || 20)) * DEG; const c = Math.cos(side), s = Math.sin(side);
        const d = [-(h.u[0] * c - h.u[1] * s), -(h.u[0] * s + h.u[1] * c)];   // camera on the holding side, turned by `side`
        SHA.qa.look([h.p[0] + h.u[0] * 4, gy, h.p[1] + h.u[1] * 4], vh(d[0], d[1]), +(a[2] || 30), +(a[1] || 48), 50);
        window.__lastHold = h; return true;
      }
      if (kind === 'sign') {   // sign:<n> or sign:<text fragment>[,<dist>,<pitch>]
        const L = SHA.markings.signs(); const sg = /^\d+$/.test(a[0]) ? L[+a[0]] : L.find(x => x.text.includes(a[0]) && x.kinds.includes('dir')) || L.find(x => x.text.includes(a[0]));
        if (!sg) return false; window.__lastHold = { id: sg.why, ref: null, text: sg.text, src: 'sign' };
        SHA.qa.look([sg.c[0] - sg.f[0] * 6, gy + 1, sg.c[1] - sg.f[1] * 6], vh(sg.f[0] + 0.35 * sg.f[1], sg.f[1] - 0.35 * sg.f[0]), +(a[2] || 8), +(a[1] || 22), 45); return true;
      }
      if (kind === 'plate') {   // plate:<stand>[,<dist>,<pitch>]: the start of the stand's lead-in (stand number plate)
        const st = (SHA.data && SHA.data.stands ? SHA.data.stands.stands : (window.SHA_STANDS || {}).stands || []).find(x => x.name === a[0]); if (!st || !st.leadin) return false;
        const L = st.leadin; let s = 0, i = 1; for (; i < L.length; i++) { const d = Math.hypot(L[i][0] - L[i - 1][0], L[i][1] - L[i - 1][1]); if (s + d > 14) break; s += d; }
        const p = L[Math.min(i, L.length - 1)], q = L[Math.max(0, Math.min(i, L.length - 1) - 1)]; const dx = p[0] - q[0], dz = p[1] - q[1];
        SHA.qa.look([p[0], gy, p[1]], vh(-dx, -dz), +(a[2] || 40), +(a[1] || 30), 50); return true;
      }
      if (kind === 'standm') { const ok = SHA.qa.stand(a[0], +(a[2] || 70), +(a[3] || 1), +(a[4] || 20)); if (ok && a[5]) SHA.rig.yaw += (+a[5]) * DEG; return ok; }
      if (kind === 'stand') return SHA.qa.stand(a[0], +(a[1] || 70), +(a[2] || 1), +(a[3] || 32));
      if (kind === 'thr') return SHA.qa.threshold(a[0]);
      if (kind === 'view') return SHA.qa.view(a[0]);   // the app's named views (overview, runways, t1, t2, top)
      if (kind === 'look') { SHA.qa.look([+a[0], +a[1], +a[2]], +a[3], +a[4], +a[5], +(a[6] || 50)); return true; }
      return false;
    }, [kind, a]);
    if (!ok) { console.log('view not available:', v); continue; }
    await frames(4); if (process.env.WAIT_MS) await page.waitForTimeout(+process.env.WAIT_MS); await frames(2);
    const cam = await page.evaluate(() => { const c = SHA.rig.camera(); return { pos: c.pos.map(x => +x.toFixed(1)), target: c.target ? c.target.map(x => +x.toFixed(1)) : null, hold: window.__lastHold ? { id: window.__lastHold.id, ref: window.__lastHold.ref, text: window.__lastHold.text, src: window.__lastHold.src } : null }; });
    await page.evaluate(() => { window.__lastHold = null; });
    console.log('view', v, JSON.stringify(cam));
    await shot((process.env.PREFIX || 'markings') + '_' + v.replace(/[:,]/g, '_'));
  }
};

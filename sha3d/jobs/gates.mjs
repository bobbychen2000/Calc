// Gates package renders and checks (stands, jet bridges, VDGS, stand signs, remote-stand equipment, push-back overlay).
// Run through the harness (from sha3d/):
//   SOFTGL=1 OUT=docs/phase2 PREFIX=gates node livetest.mjs jobs/gates.mjs
// Env: SET (';'-separated view-set names, default all below), T (ISO time, default 2026-11-14T03:00:00Z = 11:00 local),
// PARK (stands to park DEBUG static aircraft at, ','-separated stand[:ICAO]; default the list below), QUERY (extra URL
// query), QUALITY (default high), ONLY (','-separated view names to render). Each set reloads the app with its own query (the push overlay and the night set need
// one). Prints the gate statistics, the park results (does each bridge dock) and every view's camera.
// The parked aircraft are the gates package's DEBUG option (?park=): a visual check of scale, bridges and GSE, not traffic.
const PARK_DEFAULT = [
  // T2 north pier (north face 226-231, the tip 232-236, south face 237-240): some parked, the others show rest poses
  '229', '230', '233', '234', '237', '239', '231:A320',
  // T1 west face (113-127) and north face (101-112)
  '113', '115', '121', '127', '102', '110',
  // west remote apron (Apron Nr. 4, 401-413) and the east remote apron (501-525)
  '401', '403', '404:A321', '406', '501', '502:A333',
].join(',');
const SETS = {
  // day, DEBUG aircraft parked
  day: { query: (P) => `park=${P}`, views: [
    ['t2_north_pier', [-850, 2.5, -110], 45, 28, 470, 50],
    ['t2_pier_tip', [-790, 2.5, -120], 70, 17, 150, 50],
    ['t2_north_face', [-930, 2.5, -175], 340, 14, 170, 50],
    ['t2_south_face_rest', [-930, 2.5, -40], 160, 16, 170, 50],
    ['t2_vdgs_234', 'vdgs:234', 6.1, 40],
    ['t2_bridge_233', [-770, 6, -150], 200, 10, 45, 50],
    ['t1_west_face', [470, 2.5, 250], 255, 20, 430, 50],
    ['t1_west_close', [480, 2.5, 110], 235, 13, 130, 50],
    ['t1_north_face', [600, 2.5, -40], 345, 22, 330, 50],
    ['remote_west_apron', [-880, 2.5, -1430], 70, 22, 260, 50],
    ['remote_close_404', [-900, 3, -1420], 150, 12, 70, 50],
    ['remote_idle_405', [-890, 2.5, -1320], 200, 14, 90, 50],
    ['remote_east_apron', [480, 2.5, 600], 235, 20, 260, 50],
  ] },
  // DEBUG push-back overlay (no aircraft), top-down and oblique
  push: { query: () => 'debug=push', views: [
    ['push_t2_north_pier_top', [-940, 2.5, -110], 180, 89, 640, 50],
    ['push_t2_plate_frame', [-960, 2.5, -310], 180, 89, 700, 50],   // framed as the stands plate's T2 north + middle panel
    ['push_t2_south_top', [-930, 2.5, 420], 180, 89, 700, 50],
    ['push_t1_top', [520, 2.5, 200], 180, 89, 720, 50],
    ['push_remote_west_top', [-900, 2.5, -1210], 180, 89, 760, 50],
  ] },
  // night (lit stand signs, cab floodlights)
  night: { t: '2026-11-14T12:30:00Z', query: (P) => `park=${P}`, views: [
    ['night_t2_pier_tip', [-790, 2.5, -120], 70, 14, 160, 50],
  ] },
};
export default async ({ page, shot, base }) => {
  const P = process.env.PARK || PARK_DEFAULT;
  const sets = (process.env.SET || Object.keys(SETS).join(';')).split(';').filter(Boolean);
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  let first = true;
  for (const name of sets) {
    const S = SETS[name]; if (!S) { console.log('no set', name); continue; }
    const t = S.t || process.env.T || '2026-11-14T03:00:00Z';
    const q = `?fixedres=1&quality=${process.env.QUALITY || 'high'}&t=${encodeURIComponent(t)}&${S.query(P)}${process.env.QUERY ? '&' + process.env.QUERY : ''}`;
    await page.goto(base + 'live.html' + q);
    await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
    const err = await page.evaluate(() => window.__shaError || null); if (err) { console.log('APP ERROR', err); throw new Error(err); }
    if (first) { first = false;
      const I = await page.evaluate(() => SHA.qa.gates());
      console.log('gates summary', JSON.stringify(I.summary));
      console.log('class reference not docking', JSON.stringify(I.refDock.filter(r => !r.ok)));
    }
    const parked = await page.evaluate(() => SHA.qa.parked());
    if (parked.length) for (const p of parked) { const d = await page.evaluate((n) => SHA.qa.gate(n), p.stand); console.log('parked', p.stand, p.icao, 'bridges', JSON.stringify((d.bridges || []).map(b => ({ model: b.model })))); }
    const docks = await page.evaluate(() => SHA.qa.parked().map(p => { const g = SHA.world.gates.find(x => x.name === p.stand); const B = g.sharesBridgesOf ? SHA.world.gates.find(x => x.name === g.sharesBridgesOf) : g; return { stand: p.stand, icao: p.icao, bridges: SHA.scene.gateSys.bridgesOf(B).map(b => { const Pl = SHA.scene.gateSys.planFor(B, b); return Pl.ok ? 'docked' : 'rest: ' + Pl.why; }) }; }));
    for (const d of docks) console.log('dock', JSON.stringify(d));
    await page.evaluate(() => SHA.qa.hideUI(true));
    const veh = await page.evaluate(() => { const B = SHA.scene.gateSys.vehicleBuckets || {}; const o = {}; for (const k in B) if (B[k].length) o[k.replace(/\d+$/, '')] = (o[k.replace(/\d+$/, '')] || 0) + B[k].length; return o; });
    console.log('vehicles', JSON.stringify(veh), 'idle stair cues', await page.evaluate(() => (SHA.scene.gateSys._idleBoxes || []).length));
    const only = process.env.ONLY ? process.env.ONLY.split(',') : null;
    for (const v of S.views) {
      const [vn, tg] = v; if (only && !only.includes(vn)) continue;
      if (typeof tg === 'string' && tg.startsWith('vdgs:')) {
        // the VDGS seen from the cockpit of the parked aircraft: eye v[2] m above the apron, 2.5 m behind the stop
        const ok = await page.evaluate(([n, eye, fov]) => { const d = SHA.qa.gate(n); if (!d || !d.vdgs) return false; const g = SHA.world.gates.find(x => x.name === n);
          const f = g.dir, G = SHA.geo.GROUND_Y, V = d.vdgs; const tgt = [g.nose[0] + f[0] * V.t, G + V.H0 + 1.6, g.nose[1] + f[1] * V.t];
          const dist = V.t + 2.5, dy = G + eye - tgt[1]; SHA.qa.look(tgt, Math.atan2(-f[0], f[1]) * 180 / Math.PI, Math.atan2(dy, dist) * 180 / Math.PI, Math.hypot(dist, dy), fov); return true; }, [tg.slice(5), v[2], v[3]]);
        if (!ok) { console.log('view not available', vn); continue; }
      } else { const [, , yaw, pitch, dist, fov] = v; await page.evaluate(([tg, yaw, pitch, dist, fov]) => SHA.qa.look(tg, yaw, pitch, dist, fov), [tg, yaw, pitch, dist, fov]); }
      await frames(4); await page.waitForTimeout(300); await frames(2);
      await shot((process.env.PREFIX || 'gates') + '_' + vn);
    }
  }
};

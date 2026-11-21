// Gates package renders and checks (stands, jet bridges, VDGS, stand signs, remote-stand equipment, push-back overlay).
// Run through the harness (from sha3d/):
//   SOFTGL=1 OUT=docs/phase2 PREFIX=gates node livetest.mjs jobs/gates.mjs
// Fix round 1: SET=fix1;fix1night renders the stop-convention, floodlight-mast and idle-stair checks (not in the default list).
// Fix round 2: SET=fix2;fix2night renders the app's "Fly to stand" cameras and the named stand-233 view by day and night,
// a lamp head 22 / 60 m from the camera (view kind mast:<stand>,<d>; prints the sprite radius uncapped / drawn), and
// prints every stand camera against the masts and the stands left without a mast (review N1). View kinds: fly:<stand>,
// stand:<name>,<dist>,<side>,<pitch>, mast:<stand>,<dist>, vdgs:<stand>, or [name, target, yaw, pitch, dist, fov].
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
  // fix round 1: the stop convention at 233 (top view; nose wheel on the stop line, M5), the floodlight masts by day and
  // night (M2) and the staged idle stairs on the west remote apron (L4)
  fix1: { query: (P) => `park=${P}`, views: [
    ['fix1_nose233_top', [-760.58, 2.5, -138.65], 77, 80, 40, 50],
    ['fix1_nosewheel233_side', [-760.58, 3.2, -138.65], 347.33, 6, 26, 40],   // from the starboard side, low: nose gear on the stop line
    ['fix1_masts_t2_north', [-850, 2.5, -110], 45, 18, 420, 50],
    ['fix1_masts_t1', [600, 2.5, 60], 300, 16, 520, 50],
    ['fix1_idle_west', [-880, 2.5, -1430], 70, 22, 260, 50],
  ] },
  fix1night: { t: '2026-11-20T13:30:00Z', query: (P) => `park=${P}`, views: [
    ['fix1_night_masts_t2', [-850, 2.5, -110], 45, 14, 420, 50],
  ] },
  // fix round 2 (review N1): the app's own stand cameras - "Fly to stand" (shell.js flyToStand, the side it picks) at the
  // stands the review found blocked by a mast, and the named stand view of 233 (views.mjs stand:233,-,70,1,24) by day and
  // night (the mast lamp sprites capped / faded near the camera)
  fix2: { query: (P) => `park=${P}`, views: [
    ['fix2_fly_248', 'fly:248'], ['fix2_fly_274', 'fly:274'], ['fix2_fly_115', 'fly:115'], ['fix2_fly_233', 'fly:233'],
    ['fix2_stand_233', 'stand:233,70,1,24'],
  ] },
  fix2night: { t: '2026-11-20T13:30:00Z', query: (P) => `park=${P}`, views: [
    ['fix2_night_stand_233', 'stand:233,70,1,24'], ['fix2_night_fly_233', 'fly:233'],
    // a lamp head 22 m in front of the camera (the mast of stand 236 at the T2 north pier tip): the sprite cap / near fade
    ['fix2_night_mast_near', 'mast:236,22'], ['fix2_night_mast_mid', 'mast:236,60'],
  ] },
};
// (fix round 2, N1) every stand's "Fly to stand" camera against the masts: the side flyToStand picks, the closest mast to
// its sight line (3-D, pole 0-31 m against the segment camera -> target) and whether one is inside the sight wedge
const camCheck = (page) => page.evaluate(() => {
  const DEG = Math.PI / 180, G = SHA.geo.GROUND_Y, M = SHA.qa.masts().masts, out = [];
  for (const s of SHA.data.stands.stands) {
    const side = SHA.qa.standCam ? SHA.qa.standCam(s.name).side : 1; const h = SHA.geo.hdgVec(s.hdg); const lf = [h[1], -h[0]];
    const T = [s.nose[0] - h[0] * 18, G, s.nose[1] - h[1] * 18]; const o0 = [h[0] * 0.75 + lf[0] * 0.66 * side, h[1] * 0.75 + lf[1] * 0.66 * side]; const ol = Math.hypot(o0[0], o0[1]); const o = [o0[0] / ol, o0[1] / ol];
    const dist = ['E', 'EL', 'F'].includes(s.cls) ? 120 : 90; const C = [T[0] + o[0] * dist * Math.cos(24 * DEG), G + dist * Math.sin(24 * DEG), T[2] + o[1] * dist * Math.cos(24 * DEG)];
    let best = 1e9, who = null; for (const m of M) for (let k = 0; k <= 60; k++) { const a = k / 60; const P = [C[0] + (T[0] - C[0]) * a, C[1] + (T[1] - C[1]) * a, C[2] + (T[2] - C[2]) * a]; const y = Math.min(Math.max(P[1], G), G + 31); const d = Math.hypot(P[0] - m.p[0], P[1] - y, P[2] - m.p[1]); if (d < best) { best = d; who = m.stand; } }
    const sc = SHA.qa.standCam ? SHA.qa.standCam(s.name) : null;
    out.push({ stand: s.name, contact: !!(s.bridges && s.bridges.length), side, sight: +best.toFixed(1), mast: who, fan: sc ? sc.clear[side > 0 ? 0 : 1] : null });
  }
  return out;
});
export default async ({ page, shot, base }) => {
  const P = process.env.PARK || PARK_DEFAULT;
  const sets = (process.env.SET || Object.keys(SETS).filter(k => !k.startsWith('fix')).join(';')).split(';').filter(Boolean);
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
      console.log('masts', JSON.stringify(I.masts), 'idle stairs', JSON.stringify(I.idleStairs));
      if (name.startsWith('fix2')) { const K = await camCheck(page);
        console.log('stand cameras: side -1 at', K.filter(k => k.side < 0).length, 'stands (contact', K.filter(k => k.side < 0 && k.contact).length + ');',
          'a mast within 3 m / 5 m of the sight line at', JSON.stringify(K.filter(k => k.sight < 3).map(k => k.stand)), '/', JSON.stringify(K.filter(k => k.sight < 5).map(k => k.stand)),
          '; a mast in the camera (clearance < 1: within the subject / centre margins) on the side taken at', JSON.stringify(K.filter(k => k.fan != null && k.fan < 1).map(k => k.stand + ':' + k.fan)));
        for (const n of ['109', '115', '121', '248', '264', '274', '233']) { const k = K.find(x => x.stand === n); if (k) console.log('stand camera', JSON.stringify(k)); }
        console.log('stands with no mast within 120 m (and why their own candidates failed)', JSON.stringify(await page.evaluate(() => SHA.qa.masts().uncovered.map(u => [u.stand, u.why])))); }
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
      if (typeof tg === 'string' && tg.startsWith('fly:')) {
        // the app's "Fly to stand" (card closed, flight finished): exactly what a user gets from the stand card
        await page.evaluate((n) => { SHA.qa.selectStand(n, true); SHA.qa.closeCard(); const rig = SHA.rig; if (rig.anim) { rig.anim.t = rig.anim.dur; rig.update(0); } }, tg.slice(4));
        console.log('view', vn, JSON.stringify(await page.evaluate((n) => ({ side: SHA.qa.standCam(n).side, target: SHA.rig.target.map(v => +v.toFixed(2)), yaw: +(SHA.rig.yaw * 180 / Math.PI).toFixed(2), dist: SHA.rig.dist }), tg.slice(4))));
      } else if (typeof tg === 'string' && tg.startsWith('mast:')) {
        // in front of a mast's lamp head (the mast placed for stand <a>), <d> m away, 4 deg down; prints the mast sprites'
        // projected radius without and with the cap (gates.js mastSprite) for this camera
        const [ms, d] = tg.slice(5).split(',');
        const ok = await page.evaluate(([ms, d]) => { const M = SHA.qa.masts().masts.find(m => m.stand === ms); if (!M) return false; const G = SHA.geo.GROUND_Y;
          SHA.qa.look([M.p[0], G + M.h, M.p[1]], Math.atan2(M.face[0], -M.face[1]) * 180 / Math.PI, 4, d, 50); return true; }, [ms, +d]);
        if (!ok) { console.log('view not available', vn); continue; }
        await frames(2);
        console.log('mast sprites', vn, JSON.stringify(await page.evaluate(() => { const C = SHA.R.curCam, fs = 2 * Math.tan(C.fov / 2) / SHA.R.H; let raw = 0, cap = 0, n = 0;
          for (const s of SHA.scene.gateSys.staticSprites || []) { if (!s.mast) continue; const d = Math.hypot(s.p[0] - C.pos[0], s.p[1] - C.pos[1], s.p[2] - C.pos[2]); const de = Math.max(0.5, d - Math.min(2, 0.05 * d));
            const r = s.s * 1.6 / (de * fs); raw = Math.max(raw, r); if (d > 10) { cap = Math.max(cap, Math.min(r, 24)); n++; } }
          return { maxRadiusPxUncapped: +raw.toFixed(1), maxRadiusPxDrawn: +cap.toFixed(1), drawn: n }; })));
      } else if (typeof tg === 'string' && tg.startsWith('stand:')) {
        const a = tg.slice(6).split(','); await page.evaluate((a) => SHA.qa.stand(a[0], +a[1] || undefined, +a[2] || undefined, +a[3] || undefined), a);
      } else if (typeof tg === 'string' && tg.startsWith('vdgs:')) {
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

// Building views of SHA Live 3D (package P2d: terminals, tower, hangars, surroundings). Run through the harness:
//   SOFTGL=1 OUT=docs/phase2 PREFIX=buildings node livetest.mjs jobs/buildings.mjs
// VIEWS (';'-separated, default below): a name from NAMED, or look:x,y,z,yaw,pitch,dist[,fov] (SHA.qa.look), or
// view:<app view> (overview / t1 / t2 / tower / top / runways). Other env as jobs/views.mjs (T, QUERY, QUALITY, SHOWUI;
// T=snapshot keeps the app's snapshot instant). Prints a console tally (errors / warnings / page errors) at the end.
// Prints the terminals extension info (parts, hangars, towers, context blocks, far land cover) and the tower anchor.
// FILLCHECK=1 (fix round 1): prints how many fixed-link points, rotundas and VDGS posts stand on paved ground (pavedAt).
// HEADCHECK=1 (fix round 2, review_visual_fix1.md R1): the review's pavement probe (SHA.world.pavedAt < 0.5 = unpaved): stop
//   nodes, class nose tips (class_ref nose_gear_m ahead), painted equipment areas and envelopes (SHA.markings.apron(), share of
//   1 m samples unpaved), mast feet and idle stairs (SHA.qa.masts() / idleStairs()); writes <OUT>/<PREFIX>_headcheck.json.
const NAMED = {
  // T1 from the airside (west), the RWY 18L/36R side, as photo 02 (MNXANL 2023): tower behind the concourse, hall right
  t1: [[520, 2.5, 175], 270, 4, 620, 40],
  t1_close: [[480, 8, 220], 245, 10, 260, 50],
  // T2 from the airside (east), as the aerials 21 / 22: finger piers, central concourse, main hall behind
  t2: [[-1050, 2.5, 180], 100, 22, 1250, 50],
  t2_close: [[-1080, 8, 30], 120, 12, 360, 50],
  // the east control tower, close (photo 02 proportions) and from the apron
  tower: [[499.8, 24, 130.2], 262, 6, 140, 40],
  tower_far: [[499.8, 20, 130.2], 280, 3, 520, 30],
  // hangars: China Eastern (south-west, doors east) and the east hangar group (doors south)
  hangars: [[-800, 12, 1480], 95, 14, 330, 50],
  hangars_east: [[880, 10, -770], 205, 12, 420, 50],
  fbo: [[560, 6, 1080], 255, 12, 300, 50],
  hub: [[-1700, 10, 200], 125, 22, 1400, 50],
  sw: [[-950, 12, 1200], 100, 18, 700, 50],
  // oblique overview from the south-east (the core view) and a far one showing the surroundings and the haze
  overview: [[-300, 2.5, 150], 158, 33, 5600, 50],
  overview_far: [[-300, 2.5, 150], 150, 18, 11000, 55],
  // photo match, photo 02 (MNXANL 2023, 1920 x 1440, iPhone 1x lens: hfov 69.4 deg -> vfov 55.0 deg at 4:3): camera on the
  // RWY 18L/36R centreline abeam the tower (x -6, z 130, eye 4 m above the ground), optical axis 7.8 deg right of the tower
  // (tower at image x 770 of 1920) -> bearing 97.8 deg; rendered at 4:3. p02_tower: same camera, zoomed on the tower.
  p02: [[489.4, 2.5, 197.9], 277.8, 0.46, 500, 55.0, [1280, 960]],
  p02_tower: [[499.8, 24.5, 130.2], 270, -2.04, 506, 6.0, [960, 720]],
};
const DEFAULT = 'overview;overview_far;t1;t1_close;t2;t2_close;tower;tower_far;hangars;hangars_east;fbo;hub;sw';
import fs from 'fs'; import path from 'path';
export default async ({ page, shot, base, W, H, OUT }) => {
  const t = process.env.T || '2026-11-14T03:00:00Z';
  // console tally (fix round 2): errors / warnings / page errors of this run, printed at the end (snapshot mode must stay at 0)
  const tally = { error: 0, warning: 0, pageerror: 0 };
  page.on('console', (m) => { const k = m.type(); if ((k === 'error' || k === 'warning') && !/GPU stall|GL Driver|Automatic fallback/.test(m.text())) {   // (driver noise: as livetest.mjs)
     tally[k]++; console.log('[console ' + k + ']', m.text().slice(0, 300)); } });
  page.on('pageerror', () => { tally.pageerror++; });
  const q = `?fixedres=1&quality=${process.env.QUALITY || 'high'}${t === 'snapshot' ? '' : '&t=' + encodeURIComponent(t)}${process.env.QUERY ? '&' + process.env.QUERY : ''}`;
  await page.goto(base + 'live.html' + q);
  await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__shaError || null); if (err) { console.log('APP ERROR', err); throw new Error(err); }
  const info = await page.evaluate(() => SHA.qa.info());
  console.log('terminals', JSON.stringify(info.world.terminals));
  console.log('buildings', JSON.stringify(info.world.buildings), 'tower anchor', JSON.stringify(info.anchors.tower));
  // FILLCHECK=1 (fix round 1, review H2): is the ground paved (SHA.world.pavedAt, the airfield map incl. the airside fill)
  // under every bridge's fixed link, rotunda and VDGS post?
  if (process.env.FILLCHECK) {
    const r = await page.evaluate(() => {
      const P = SHA.world.pavedAt, S = SHA.data.stands.stands, out = { walk: [0, 0], rotunda: [0, 0], vdgs: [0, 0], bad: [] };
      const hv = (h) => [Math.sin(h * Math.PI / 180), -Math.cos(h * Math.PI / 180)];
      for (const s of S) for (const b of s.bridges || []) {
        const [a, r] = [b.walk[0], b.walk[b.walk.length - 1]]; const L = Math.hypot(r[0] - a[0], r[1] - a[1]);
        if (L > 2) for (let k = 1; k <= 8; k++) { const x = a[0] + (r[0] - a[0]) * k / 8, z = a[1] + (r[1] - a[1]) * k / 8; out.walk[1]++; if (P(x, z) > 0.5) out.walk[0]++; else out.bad.push('walk ' + s.name); }
        out.rotunda[1]++; if (P(b.rotunda[0], b.rotunda[1]) > 0.5) out.rotunda[0]++; else out.bad.push('rotunda ' + s.name);
      }
      for (const s of S) { const g = SHA.qa.gate && SHA.qa.gate(s.name); if (!g || !g.vdgs || !g.vdgs.post) continue;
        const f = hv(s.hdg), x = s.nose[0] + f[0] * g.vdgs.t, z = s.nose[1] + f[1] * g.vdgs.t; out.vdgs[1]++; if (P(x, z) > 0.5) out.vdgs[0]++; else out.bad.push('vdgs ' + s.name); }
      out.bad = [...new Set(out.bad)]; return out;
    });
    console.log('FILLCHECK paved / total: fixed-link points', r.walk.join(' / '), '· rotundas', r.rotunda.join(' / '), '· VDGS posts', r.vdgs.join(' / '), '· not paved:', r.bad.join(', ') || 'none');
  }
  if (process.env.HEADCHECK) {
    const r = await page.evaluate(() => {
      const G = SHA.geo, P = (x, z) => SHA.world.pavedAt(x, z), D = SHA.data.stands, refs = D.class_ref || {}, out = {};
      const st = D.stands.map(s => { const h = G.hdgVec(s.hdg), ng = (refs[s.cls] && refs[s.cls].nose_gear_m) || 0;
        return { n: s.name, node: P(...s.nose), tip: P(s.nose[0] + h[0] * ng, s.nose[1] + h[1] * ng) }; });
      out.stopNodesOff = st.filter(x => x.node < 0.5).map(x => x.n); out.noseTipsOff = st.filter(x => x.tip < 0.5).map(x => x.n);
      const inPoly = (x, z, R) => { let c = false; for (let i = 0, j = R.length - 1; i < R.length; j = i++) { const [xi, zi] = R[i], [xj, zj] = R[j]; if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) c = !c; } return c; };
      const offFrac = (R) => { let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const [x, z] of R) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
        let n = 0, o = 0; for (let x = x0; x <= x1; x += 1) for (let z = z0; z <= z1; z += 1) if (inPoly(x, z, R)) { n++; if (P(x, z) < 0.5) o++; } return n ? o / n : 0; };
      const A = (SHA.markings && SHA.markings.apron && SHA.markings.apron()) || {};
      for (const k of ['equipment', 'envelopes']) { const L = A[k] || []; const bad = [];
        for (const e of L) { const f = offFrac(e.ring); if (f > 0.05) bad.push(e.stand + ' ' + f.toFixed(2)); }
        out[k] = { total: L.length, over5pct: bad.length, over25pct: bad.filter(b => +b.split(' ')[1] >= 0.25).length, list: bad }; }
      const M = SHA.qa.masts ? SHA.qa.masts() : null;
      if (M) out.masts = { total: M.masts.length, footOff: M.masts.filter(m => P(m.p[0], m.p[1]) < 0.5).map(m => m.p.map(v => +v.toFixed(1))) };
      const I = SHA.qa.idleStairs ? SHA.qa.idleStairs() : null;
      if (I) out.idleStairs = I.stats;
      return out;
    });
    fs.writeFileSync(path.join(OUT, (process.env.PREFIX || 'buildings') + '_headcheck.json'), JSON.stringify(r, null, 1));
    console.log('HEADCHECK unpaved: stop nodes', r.stopNodesOff.length, r.stopNodesOff.join(' '), '· nose tips', r.noseTipsOff.length, r.noseTipsOff.join(' '),
      '· equipment areas > 5 %', r.equipment.over5pct, '/', r.equipment.total, '(>= 25 %:', r.equipment.over25pct + ')', '· envelopes > 5 %', r.envelopes.over5pct, '/', r.envelopes.total,
      '· mast feet', r.masts ? r.masts.footOff.length + ' / ' + r.masts.total : '-', '· idle stairs', JSON.stringify(r.idleStairs || null));
  }
  if (!process.env.SHOWUI) await page.evaluate(() => SHA.qa.hideUI(true));
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  for (const v of (process.env.VIEWS || DEFAULT).split(';').filter(Boolean)) {
    let ok = true;
    if (v.startsWith('look:')) { const p = v.slice(5).split(',').map(Number); await page.evaluate((p) => SHA.qa.look([p[0], p[1], p[2]], p[3], p[4], p[5], p[6] || 50), p); }
    else if (v.startsWith('view:')) ok = await page.evaluate((n) => SHA.qa.view(n), v.slice(5));
    else if (NAMED[v]) {
      const [tg, yaw, pitch, dist, fov, vp] = NAMED[v];
      if (vp) { await page.setViewportSize({ width: vp[0], height: vp[1] }); await frames(3); }
      await page.evaluate(([tg, yaw, pitch, dist, fov]) => SHA.qa.look(tg, yaw, pitch, dist, fov), [tg, yaw, pitch, dist, fov]);
    }
    else { console.log('unknown view', v); continue; }
    if (!ok) { console.log('view not available:', v); continue; }
    await frames(4); await frames(2);
    await shot((process.env.PREFIX || 'buildings') + '_' + v.replace(/[:,]/g, '_'));
    if (NAMED[v] && NAMED[v][5]) { await page.setViewportSize({ width: W, height: H }); await frames(3); }
  }
  console.log('console tally: errors', tally.error, '· warnings', tally.warning, '· page errors', tally.pageerror);
};

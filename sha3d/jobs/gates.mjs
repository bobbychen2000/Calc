// Gates package renders and checks (stands, jet bridges, VDGS, stand signs, remote-stand equipment, push-back overlay).
// Run through the harness (from sha3d/):
//   SOFTGL=1 OUT=docs/phase2 PREFIX=gates node livetest.mjs jobs/gates.mjs
// Fix round 1: SET=fix1;fix1night renders the stop-convention, floodlight-mast and idle-stair checks (not in the default list).
// Fix round 2: SET=fix2;fix2night renders the app's "Fly to stand" cameras and the named stand-233 view by day and night,
// a lamp head 22 / 60 m from the camera (view kind mast:<stand>,<d>; prints the sprite radius uncapped / drawn), and
// prints every stand camera against the masts and the stands left without a mast (review N1). View kinds: fly:<stand>,
// stand:<name>,<dist>,<side>,<pitch>, mast:<stand>,<dist>, vdgs:<stand>, or [name, target, yaw, pitch, dist, fov].
// Fix round 3: SET='fix3;fix3night;fix3low' (review_visual_fix2.md V2 / V4 / N5): "Fly to stand" at 238A, 264, 270, 228 and
// 259 by day and 238A at night (aircraft parked there: FIX3_PARK), and prints, for every stand camera on the side the app
// takes, the masts in its near field (head or pole above 10 m in the 16:9 frame at a depth under 45 m, or the pole within
// 25 m of the camera; an independent sampled test, the app's standCamNear, and the review probe's 60 px test), the masts in
// or within 2 m of a painted equipment area, the base plates (+1 m) off pavement, the coverage (masts, stands with no mast
// within 120 m) and the mast-list hash; fix3low reloads at quality=low and compares the mast list with the high tier.
// CHECK_ONLY=1 prints the checks without rendering.
// Fix round 4 (review_visual_fix3.md F1 / F3 / F4 / F7): the fix3 checks also test the app's Tower view (from the app's own
// camera at the job viewport, 1920 x 970, iPhone 15 landscape and portrait, a portrait tablet: no mast in its 250 m near field,
// none >= 20 px within 300 m; verification round 1, was the job viewport and iPhone 15 portrait with 90 m), the 40-71 px heads beyond 45 m on the side
// "Fly to stand" takes, the feet within 3.13 m of a painted envelope line, and the mast cache: the page must have used
// data/sha_masts.json (stats.source 'cache') and a live pass (SHA.qa.mastsLive) must give the same list. SET=masts writes
// data/sha_masts.json / .js from the page's live pass (?masts=live): run it after any change to the placement or its inputs.
// SET=fix4 renders the Tower view, "Fly to stand" at 274 / 260 / 115 / 229 / 224, the 113 stand view and the mast by 290.
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
  // fix round 3 (review_visual_fix2.md V2): "Fly to stand" at the review's five stands (aircraft parked there) by day, 238A at
  // night; the checks (near-field masts, equipment areas, base plates, coverage, hash) print for fix3 / fix3low
  fix3: { park: true, query: (P) => `park=${P}`, views: [
    ['fix3_fly_238A', 'fly:238A'], ['fix3_fly_264', 'fly:264'], ['fix3_fly_270', 'fly:270'], ['fix3_fly_228', 'fly:228'], ['fix3_fly_259', 'fly:259'],
  ] },
  fix3night: { park: true, t: '2026-11-20T13:30:00Z', query: (P) => `park=${P}`, views: [['fix3_night_fly_238A', 'fly:238A']] },
  // (N5) the low tier (the phone's default): the mast list must equal the high tier's
  fix3low: { quality: 'low', query: () => '', views: [] },
  // (fix round 4, F7) write data/sha_masts.json / .js from the page's live placement pass
  masts: { query: () => 'masts=live', views: [] },
  // fix round 4 (review_visual_fix3.md F1 / F3 / F4): the app's Tower view (laptop framing; the phone framing: jobs/views.mjs
  // towercab with DEVICE='iPhone 15'), "Fly to stand" at the review's F3 stands (aircraft parked there: FIX4_PARK), the
  // named stand view of 113 and the mast nearest to the 290 envelope from above (view kinds tower, masttop:<x>,<z>,<h>)
  fix4: { park4: true, query: (P) => `park=${P}`, views: [
    ['fix4_towercab', 'tower'], ['fix4_fly_274', 'fly:274'], ['fix4_fly_260', 'fly:260'], ['fix4_fly_115', 'fly:115'], ['fix4_fly_229', 'fly:229'], ['fix4_fly_224', 'fly:224'],
    ['fix4_stand_113', 'stand:113,75,1,22'], ['fix4_masttop_290', 'masttop:-723,1080,70'],
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
// (fix round 3, review_visual_fix2.md V2 / V4 / N5) the mast checks. Near field: an independent sampled test (the pole every
// 0.5 m from 10 m to the head, the eight corners of the head box, 3-D distance camera -> pole), the app's own standCamNear
// (gate_system.js) and the review probe's test (out/review2/rv.mjs: head / mid / foot sample in the 16:9 frame, a 3 m head
// >= 60 px). The camera is the one the app builds: standCamWedge(stand's node, exact heading, class, the side
// SHA.qa.standCam picks, SHA.qa.camSubject) - for 238A / 259A (on 238's / 259's bridge) their own node and heading.
const mastCheck = (page) => page.evaluate(async () => {
  const GS = await import('./js/live/gate_system.js');
  const G = SHA.geo, Q = SHA.qa.masts(), M = Q.masts, K = GS.STAND_CAM, DEG = Math.PI / 180;
  const ty = Math.tan(K.fov / 2 * DEG), tx = ty * 16 / 9, ND = K.nearDepth || 45, NR = K.nearDist || 25;
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cams = [];
  for (const s of SHA.data.stands.stands) {
    const sc = SHA.qa.standCam(s.name); if (!sc) continue;
    const W = GS.standCamWedge(s.nose, G.hdgVec(s.hdg), s.cls, sc.side, SHA.qa.camSubject(s.name) || []); const c = W.cam;
    const near = [], rv = [];
    for (const m of M) { const H = m.h || 30;
      const d3 = Math.hypot(Math.hypot(m.p[0] - c[0], m.p[1] - c[2]), c[1] > H + 1 ? c[1] - H - 1 : 0);
      const f = m.face, l = [-f[1], f[0]]; const pts = []; for (let y = 10; y <= H + 0.01; y += 0.5) pts.push([m.p[0], y, m.p[1]]);
      for (const a of [-1.1, 0.9]) for (const b of [-2.1, 2.1]) for (const y of [H - 2.1, H + 0.6]) pts.push([m.p[0] + f[0] * a + l[0] * b, y, m.p[1] + f[1] * a + l[1] * b]);
      let zmin = Infinity; for (const P of pts) { const v = [P[0] - c[0], P[1] - c[1], P[2] - c[2]]; const z = dot(v, W.F); if (z < 0.5 || z >= ND) continue;
        if (Math.abs(dot(v, W.R) / z) < tx && Math.abs(dot(v, W.U) / z) < ty) zmin = Math.min(zmin, z); }
      if (d3 < NR || zmin < ND) near.push({ mast: m.stand, d3: +d3.toFixed(1), depth: zmin < ND ? +zmin.toFixed(1) : null, headPx: zmin < ND ? Math.round(4.2 / zmin * 360 / ty) : null });
      for (const yy of [H, H * 0.5, 2]) { const v = [m.p[0] - c[0], yy - c[1], m.p[1] - c[2]]; const z = dot(v, W.F); if (z <= 1) continue; const X = dot(v, W.R) / z, Y = dot(v, W.U) / z;
        if (Math.abs(X) < tx && Math.abs(Y) < ty) { const px = Math.round(3 / z * 360 / ty); if (px >= 60) rv.push({ mast: m.stand, at: yy === H ? 'head' : yy === 2 ? 'foot' : 'mid', z: +z.toFixed(1), px }); break; } } }
    const fn = GS.standCamNearList ? GS.standCamNearList(W, M).length : null;
    // (fix round 4, review_visual_fix3.md F3) heads in the frame at 45 m and more that are still >= 40 px wide (the 4.2 m
    // head at 1280 x 720: 4.2 / depth x 360 / tan(25 deg), i.e. depth <= ~81 m): the middle distance the near field leaves
    const mid = []; for (const m of M) { const H = m.h || 30; const v = [m.p[0] - c[0], H - 0.8 - c[1], m.p[1] - c[2]]; const z = dot(v, W.F); if (z < 45) continue;
      const X = dot(v, W.R) / z, Y = dot(v, W.U) / z; if (Math.abs(X) > tx || Math.abs(Y) > ty) continue; const px = Math.round(4.2 / z * 360 / ty); if (px >= 40) mid.push({ mast: m.stand, z: +z.toFixed(1), px }); }
    cams.push({ stand: s.name, contact: !!s.contact, side: sc.side, clear: sc.clear, near, fn, rv, mid });
  }
  // (fix round 4, F4) the nearest painted stand envelope (the safety line, SHA.markings.apron().envelopes) to every mast foot:
  // the base plate + MAST_ENV_CLEAR 2 m means a foot >= 2 + 0.8 x sqrt 2 = 3.13 m from the line
  const ENV = (A0 => (A0.envelopes || []).filter(e => e && e.ring && e.ring.length >= 3))((SHA.markings && SHA.markings.apron && SHA.markings.apron()) || {});
  // equipment areas (+2 m) and base plates (+1 m margin: corners at +-1.8 m) on pavement (the app's pavedAt at this tier and
  // the tier-independent vector test the placement uses, SHA.qa.pavedVec)
  const A = (SHA.markings && SHA.markings.apron && SHA.markings.apron()) || {}; const EQ = (A.equipment || []).filter(e => e && e.ring && e.ring.length >= 3);
  const inR = (q, R) => { let k = false; for (let i = 0, j = R.length - 1; i < R.length; j = i++) if (((R[i][1] > q[1]) !== (R[j][1] > q[1])) && (q[0] < (R[j][0] - R[i][0]) * (q[1] - R[i][1]) / (R[j][1] - R[i][1]) + R[i][0])) k = !k; return k; };
  const segD = (q, a, b) => { const ex = b[0] - a[0], ez = b[1] - a[1]; const t = Math.max(0, Math.min(1, ((q[0] - a[0]) * ex + (q[1] - a[1]) * ez) / (ex * ex + ez * ez || 1))); return Math.hypot(a[0] + ex * t - q[0], a[1] + ez * t - q[1]); };
  const ringD = (q, R) => { if (inR(q, R)) return 0; let d = Infinity; for (let i = 0, j = R.length - 1; i < R.length; j = i++) d = Math.min(d, segD(q, R[j], R[i])); return d; };
  const eqD = M.map(m => { let d = Infinity, st = null; for (const e of EQ) { const x = ringD(m.p, e.ring); if (x < d) { d = x; st = e.stand; } } return { mast: m.stand, d: +d.toFixed(2), area: st }; });
  const inEquip = eqD.filter(x => x.d < 2); const eqMin = eqD.reduce((a, x) => x.d < a.d ? x : a, { d: Infinity });
  const ringLineD = (q, R) => { let d = Infinity; for (let i = 0, j = R.length - 1; i < R.length; j = i++) d = Math.min(d, segD(q, R[j], R[i])); return d; };
  const envD = M.map(m => { let d = Infinity, st = null; for (const e of ENV) { const x = inR(m.p, e.ring) ? 0 : ringLineD(m.p, e.ring); if (x < d) { d = x; st = e.stand; } } return { mast: m.stand, d: +d.toFixed(2), env: st }; });
  const envNear = envD.filter(x => x.d < 3.13).sort((a, b) => a.d - b.d); const envMin = envD.reduce((a, x) => x.d < a.d ? x : a, { d: Infinity });
  const corners = (m) => { const f = m.face, l = [-f[1], f[0]]; const o = []; for (const a of [-1.8, 1.8]) for (const b of [-1.8, 1.8]) o.push([m.p[0] + f[0] * a + l[0] * b, m.p[1] + f[1] * a + l[1] * b]); return o; };
  const PV = SHA.qa.pavedVec || null;
  const plates = M.map(m => ({ mast: m.stand, raster: corners(m).concat([m.p]).map(q => +SHA.world.pavedAt(q[0], q[1]).toFixed(2)), vec: PV ? corners(m).concat([m.p]).map(q => PV(q[0], q[1]) ? 1 : 0) : null }))
    .filter(x => x.raster.some(v => v < 0.5) || (x.vec && x.vec.some(v => !v)));
  // the named stand views of jobs/views.mjs (app.js SHA.qa.stand: the same direction, other distance / pitch) against the near field
  const named = [['233', 70, 24], ['113', 75, 22], ['102', 110, 20], ['404', 75, 22]].map(([n, dist, pitch]) => { const s = SHA.data.stands.stands.find(x => x.name === n); const h = G.hdgVec(s.hdg); const lf = [h[1], -h[0]];
    const T = [s.nose[0] - h[0] * 18, s.nose[1] - h[1] * 18]; const o0 = [h[0] * 0.75 + lf[0] * 0.66, h[1] * 0.75 + lf[1] * 0.66]; const ol = Math.hypot(o0[0], o0[1]); const o = [o0[0] / ol, o0[1] / ol];
    const cp = Math.cos(pitch * DEG), sp = Math.sin(pitch * DEG); const W = { cam: [T[0] + o[0] * dist * cp, dist * sp, T[1] + o[1] * dist * cp], F: [-o[0] * cp, -sp, -o[1] * cp], R: [o[1], 0, -o[0]] };
    W.U = [W.R[1] * W.F[2] - W.R[2] * W.F[1], W.R[2] * W.F[0] - W.R[0] * W.F[2], W.R[0] * W.F[1] - W.R[1] * W.F[0]];
    return { view: `stand:${n},-,${dist},1,${pitch}`, near: GS.standCamNearList(W, M) }; });
  const h = (() => { let x = 2166136261; for (const m of M) for (const v of m.p) { const s = v.toFixed(2); for (let i = 0; i < s.length; i++) { x ^= s.charCodeAt(i); x = Math.imul(x, 16777619) >>> 0; } } return x.toString(16); })();
  const legend = ((SHA.ui.legendLines && SHA.ui.legendLines.get('gates')) || '').replace(/<[^>]+>/g, '').match(/Apron floodlight masts:[^.;]*/);
  // (fix round 4, F7) the cache: the list the page placed against a live pass with the same inputs (dry: places nothing)
  const L = SHA.qa.mastsLive ? SHA.qa.mastsLive() : null;
  const live = L ? { hash: L.stats.hash, inputs: L.stats.inputs, ms: L.stats.ms, msPrep: L.stats.msPrep, msHash: L.stats.msHash, masts: L.masts.length } : null;
  return { live, msCache: Q.stats && Q.stats.ms, quality: SHA.qa.info().quality, masts: M.length, legend: legend ? legend[0] : null, hash: (Q.stats && Q.stats.hash) || null, hashJob: h, byArea: Q.stats && Q.stats.byArea, rejected: Q.stats && Q.stats.rejected, ms: Q.stats && Q.stats.ms,
    uncovered: Q.uncovered.map(u => u.stand), cameras: Q.stats && Q.stats.cameras, list: M.map(m => [m.stand, m.p[0], m.p[1]]), cams, inEquip, eqMin, envNear, envMin, plates, named,
    source: Q.stats && Q.stats.source || null, inputs: Q.stats && Q.stats.inputs || null,
    byKind: M.reduce((o, m) => { o[m.at] = (o[m.at] || 0) + 1; return o; }, {}), gap: M.filter(m => m.at === 'gap fill').map(m => m.stand) };
});
// (fix round 4, review_visual_fix3.md F1) the app's Tower view against the masts, from the camera the app itself sets
// (SHA.qa.view('tower'), SHA.rig.camera()) - independent of gate_system.js towerViewCams - at the job's viewport and (fix
// round 4 verification, review F1-wide-aspect: app.js keeps the 46 deg vertical field on every landscape aspect) at
// 1920 x 970 (a full-HD browser window), iPhone 15 landscape 734 x 343, iPhone 15 portrait 393 x 659 and a portrait tablet
// 820 x 1080. Near field (an independent sampled test, as mastCheck): the pole every 0.5 m from 10 m to the head or a corner of
// the 4.2 x 2.7 x 2 m head box in the frame at a depth under 250 m (TOWER_NEAR, = gate_system.js TOWER_CAM.nearDepth: a head
// under 1.0 deg; was 90 m), or the pole within 25 m of the eye; and the review probe's test (out/review4/rv4.mjs): a head in
// the frame within 300 m (3-D) that is >= 20 px at that viewport. Also every mast head in the frame with its width in px.
const TOWER_NEAR = 250;
const TOWER_VIEWPORTS = [[1920, 970, 'full-HD window'], [734, 343, 'iPhone 15 landscape'], [393, 659, 'iPhone 15 portrait'], [820, 1080, 'tablet portrait']];
const towerCheck = async (page, W, H, frames) => {
  const one = (tag) => page.evaluate(([ND, tag]) => {
    const DEG = Math.PI / 180, G = SHA.geo.GROUND_Y, M = SHA.qa.masts().masts;
    SHA.qa.view('tower'); if (SHA.rig.anim) { SHA.rig.anim.t = SHA.rig.anim.dur; SHA.rig.update(0); }
    const C = SHA.rig.camera(); const cv = document.querySelector('canvas'); const cw = cv.clientWidth, ch = cv.clientHeight;
    const F = C.dir; const R0 = [-F[2], 0, F[0]]; const rl = Math.hypot(...R0); const R = R0.map(v => v / rl);
    const U = [R[1] * F[2] - R[2] * F[1], R[2] * F[0] - R[0] * F[2], R[0] * F[1] - R[1] * F[0]];
    const ty = Math.tan(C.fov / 2), tx = ty * cw / ch; const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const near = [], heads = [], probe = [];
    for (const m of M) { const Hm = m.h || 30; const c = C.pos;
      const d3 = Math.hypot(Math.hypot(m.p[0] - c[0], m.p[1] - c[2]), c[1] > G + Hm + 1 ? c[1] - G - Hm - 1 : 0);
      const f = m.face, l = [-f[1], f[0]]; const pts = []; for (let y = 10; y <= Hm + 0.01; y += 0.5) pts.push([m.p[0], G + y, m.p[1]]);
      for (const a of [-1.1, 0.9]) for (const b of [-2.1, 2.1]) for (const y of [Hm - 2.1, Hm + 0.6]) pts.push([m.p[0] + f[0] * a + l[0] * b, G + y, m.p[1] + f[1] * a + l[1] * b]);
      let zmin = Infinity; for (const P of pts) { const v = [P[0] - c[0], P[1] - c[1], P[2] - c[2]]; const z = dot(v, F); if (z < 0.5 || z >= ND) continue;
        if (Math.abs(dot(v, R) / z) < tx && Math.abs(dot(v, U) / z) < ty) zmin = Math.min(zmin, z); }
      if (d3 < 25 || zmin < ND) near.push({ mast: m.stand, d3: +d3.toFixed(1), depth: zmin < ND ? +zmin.toFixed(1) : null });
      const v = [m.p[0] - c[0], G + Hm - 0.8 - c[1], m.p[1] - c[2]]; const z = dot(v, F);
      if (z > 0.5) { const X = dot(v, R) / z, Y = dot(v, U) / z; if (Math.abs(X) < tx && Math.abs(Y) < ty) { const hd = { mast: m.stand, z: +z.toFixed(1), d3: Math.round(Math.hypot(...v)), px: Math.round(4.2 / z * ch / 2 / ty), x: Math.round((X / tx * 0.5 + 0.5) * cw), y: Math.round((0.5 - Y / ty * 0.5) * ch) };
        heads.push(hd); if (hd.d3 <= 300 && hd.px >= 20) probe.push(hd); } } }
    heads.sort((a, b) => b.px - a.px);
    return { tag, viewport: [cw, ch], pos: C.pos.map(v => +v.toFixed(2)), yawDeg: +(Math.atan2(F[0], -F[2]) / DEG).toFixed(2), pitchDeg: +(Math.asin(F[1]) / DEG).toFixed(2), fovDeg: +(C.fov / DEG).toFixed(2),
      hfovDeg: +(2 * Math.atan(tx) / DEG).toFixed(1), near, probe, heads: heads.slice(0, 6), nHeads: heads.length };
  }, [TOWER_NEAR, tag]);
  const out = [await one('job viewport')];
  for (const [w, h, tag] of TOWER_VIEWPORTS) { await page.setViewportSize({ width: w, height: h }); await frames(3); out.push(await one(tag)); }
  await page.setViewportSize({ width: W, height: H }); await frames(3); await page.evaluate(() => SHA.qa.view('overview'));
  return out;
};
let HIGH = null;   // the first checked set's mast list (the tier comparison)
function printMastCheck(R, tag) {
  const nl = (k) => k.stand + ':' + k.side + ':' + k.near.map(n => n.mast + '@' + (n.depth ?? '-') + 'm/' + n.d3 + 'm/' + (n.headPx ?? '-') + 'px').join('+');
  console.log(`masts [${tag}] quality ${R.quality}: ${R.masts} (hash ${R.hash} / job ${R.hashJob}, ${R.ms} ms); by area ${JSON.stringify(R.byArea)}`);
  console.log(`masts [${tag}] rejected ${JSON.stringify(R.rejected)}; legend: "${R.legend}"`);
  console.log(`masts [${tag}] stands with no mast within 120 m: ${R.uncovered.length} ${JSON.stringify(R.uncovered)}; cameras ${JSON.stringify(R.cameras)}`);
  const nc = R.cams.filter(k => k.near.length);
  console.log(`near field [${tag}] (sampled) contact stands: ${nc.filter(k => k.contact).length} ${JSON.stringify(nc.filter(k => k.contact).map(nl))}`);
  console.log(`near field [${tag}] (sampled) remote stands: ${nc.filter(k => !k.contact).length} ${JSON.stringify(nc.filter(k => !k.contact).map(nl))}`);
  const fn = R.cams.filter(k => k.fn); console.log(`near field [${tag}] (app standCamNear): ${fn.length} ${JSON.stringify(fn.map(k => k.stand))}; disagree with the sampled test: ${JSON.stringify(R.cams.filter(k => k.fn != null && !!k.fn !== !!k.near.length).map(k => k.stand))}`);
  const rv = R.cams.filter(k => k.rv.length); console.log(`near field [${tag}] (review probe, 3 m head >= 60 px): contact ${rv.filter(k => k.contact).length}, remote ${rv.filter(k => !k.contact).length} ${JSON.stringify(rv.map(k => k.stand + ':' + k.rv.map(x => x.mast + '/' + x.at + '/' + x.px + 'px').join('+')))}`);
  console.log(`stand cameras [${tag}]: side -1 at ${R.cams.filter(k => k.side < 0).length} (contact ${R.cams.filter(k => k.side < 0 && k.contact).length}); subject clearance < 1 on the side taken: ${JSON.stringify(R.cams.filter(k => k.clear[k.side > 0 ? 0 : 1] < 1).map(k => k.stand))}`);
  for (const n of ['238A', '264', '270', '228', '259', '233']) { const k = R.cams.find(x => x.stand === n); if (k) console.log(`stand camera [${tag}] ${n}: side ${k.side}, clear ${JSON.stringify(k.clear)}, near ${JSON.stringify(k.near)}, review ${JSON.stringify(k.rv)}`); }
  console.log(`masts [${tag}] by placement: ${JSON.stringify(R.byKind)}; gap fill for ${JSON.stringify(R.gap)}`);
  console.log(`named stand views [${tag}] near field: ${JSON.stringify(R.named.map(v => v.view + ' ' + (v.near.length ? JSON.stringify(v.near) : 'clear')))}`);
  console.log(`masts [${tag}] foot in or within 2 m of an equipment area: ${R.inEquip.length} ${JSON.stringify(R.inEquip)}; nearest foot to an equipment area ${JSON.stringify(R.eqMin)}`);
  console.log(`masts [${tag}] base plate + 1 m not all on pavement (4 corners + centre; raster pavedAt / vector): ${R.plates.length} ${JSON.stringify(R.plates)}`);
  // (fix round 4) F4: feet within 3.13 m of a painted envelope line; F3: heads >= 40 px at >= 45 m on the side taken; F1: the Tower view
  console.log(`masts [${tag}] foot within 3.13 m of a painted envelope line (base plate + 2 m, F4): ${R.envNear.length} ${JSON.stringify(R.envNear)}; nearest ${JSON.stringify(R.envMin)}`);
  const mid = R.cams.filter(k => k.mid.length), mid60 = R.cams.filter(k => k.mid.some(x => x.px >= 60));
  console.log(`middle distance [${tag}] (F3: a head >= 40 px at a depth >= 45 m on the side taken): ${mid.length} stands (contact ${mid.filter(k => k.contact).length}); >= 60 px: ${mid60.length} (contact ${mid60.filter(k => k.contact).length}) ${JSON.stringify(mid60.map(k => k.stand + ':' + k.mid.map(x => x.mast + '/' + x.z + 'm/' + x.px + 'px').join('+')))}`);
  console.log(`middle distance [${tag}] contact stands: ${JSON.stringify(mid.filter(k => k.contact).map(k => k.stand + ':' + Math.max(...k.mid.map(x => x.px)) + 'px'))}`);
  // (verification round 1) the same at 1440 x 900 (x 1.25): heads >= 60 px there; and the gap-fill masts' largest head
  const m900 = R.cams.filter(k => k.mid.some(x => x.px * 1.25 >= 60)); const gapM = new Set(R.gap); const gapBig = {};
  for (const k of R.cams) for (const x of k.mid) if (gapM.has(x.mast) && (!gapBig[x.mast] || x.px > gapBig[x.mast].px)) gapBig[x.mast] = { px: x.px, in: k.stand, z: x.z };
  console.log(`middle distance [${tag}] at 1440 x 900: a head >= 60 px at ${m900.length} stands (contact ${m900.filter(k => k.contact).length}); gap-fill masts with a head >= 40 px (1280 x 720) on a side taken: ${JSON.stringify(gapBig)}`);
  if (R.tower) for (const T of R.tower) console.log(`tower view [${tag}] ${T.tag} ${T.viewport.join('x')} (eye ${JSON.stringify(T.pos)}, yaw ${T.yawDeg}, pitch ${T.pitchDeg}, fov ${T.fovDeg} x ${T.hfovDeg}): near field (< ${TOWER_NEAR} m) ${T.near.length} ${JSON.stringify(T.near)}; review probe (head in frame <= 300 m, >= 20 px) ${T.probe.length} ${JSON.stringify(T.probe)}; ${T.nHeads} heads in frame, largest ${JSON.stringify(T.heads.slice(0, 3))}`);
  console.log(`masts [${tag}] source ${R.source} (inputs ${R.inputs}); placement ${R.msCache} ms on this page; live pass ${R.live ? R.live.ms + ' ms (prep ' + R.live.msPrep + ', hash ' + R.live.msHash + '), hash ' + R.live.hash + ', inputs ' + R.live.inputs : '-'}`);
  // requirements (review_visual_fix2.md V2 / V4): no contact-stand "Fly to stand" camera with a near-field mast (remote stands
  // are reported above), no mast foot in or within 2 m of an equipment area, every base plate + 1 m on pavement;
  // (fix round 4) no mast in the near field of the Tower view (laptop and phone framing, F1), no foot within 3.13 m of a
  // painted envelope line (F4)
  const bad = []; if (nc.some(k => k.contact)) bad.push('contact-stand camera with a near-field mast'); if (R.inEquip.length) bad.push('mast in an equipment area'); if (R.plates.length) bad.push('base plate off pavement');
  if (R.tower && R.tower.some(T => T.near.length || T.probe.length)) bad.push('mast in the Tower view near field (' + R.tower.filter(T => T.near.length || T.probe.length).map(T => T.viewport.join('x')).join(', ') + ')'); if (R.envNear.length) bad.push('mast within 2 m of a painted envelope');
  // (fix round 4, F7) the page used the stored placement and it equals a live pass
  if (R.source !== 'cache') bad.push('data/sha_masts.json not used (' + R.source + '): rebuild it with SET=masts');
  if (R.live && (R.live.hash !== R.hash || R.live.inputs !== R.inputs)) bad.push('the stored mast list differs from a live pass');
  console.log(`fix3 requirements [${tag}]: ${bad.length ? 'FAILED: ' + bad.join(', ') : 'met'}`); if (bad.length) process.exitCode = 1;
  if (!HIGH) HIGH = R; else { const key = (m) => m[1].toFixed(2) + ',' + m[2].toFixed(2); const a = new Set(HIGH.list.map(key)), b = new Set(R.list.map(key));
    console.log(`tiers: ${HIGH.quality} ${HIGH.masts} (hash ${HIGH.hashJob}) vs ${R.quality} ${R.masts} (hash ${R.hashJob}): only ${HIGH.quality} ${JSON.stringify(HIGH.list.filter(m => !b.has(key(m))))}, only ${R.quality} ${JSON.stringify(R.list.filter(m => !a.has(key(m))))} -> ${HIGH.hashJob === R.hashJob ? 'SAME' : 'DIFFERENT'}`); if (HIGH.hashJob !== R.hashJob) process.exitCode = 1; }
}
// (fix round 4, F7) data/sha_masts.json / .js from the page's live pass (deterministic: no times, no tier)
async function writeMasts(page) {
  const fs = await import('fs');
  const Q = await page.evaluate(() => SHA.qa.masts());
  if (!Q || !Q.stats || !/^live/.test(Q.stats.source || '')) throw new Error('masts: no live placement on this page');
  const stats = { ...Q.stats }; for (const k of ['ms', 'msPrep', 'msHash', 'source', 'inputs']) delete stats[k];
  const out = { what: 'Apron floodlight mast placement of SHA Live 3D (inferred), stored from js/live/gate_system.js placeMasts',
    generator: 'jobs/gates.mjs SET=masts (the page\'s own live pass, ?masts=live): SOFTGL=1 SET=masts node livetest.mjs jobs/gates.mjs',
    src: 'inf', note: 'positions and form inferred (photos show 25-35 m masts; rules in gate_system.js placeMasts). js/live/gates.js uses this list only when `inputs` equals the hash of the page\'s own placement inputs (code, constants, stands, bridges, envelopes, pavement, cameras); otherwise it places the masts live.',
    inputs: Q.stats.inputs, hash: Q.stats.hash, masts: Q.masts, uncovered: Q.uncovered, stats };
  const dir = new URL('../data/', import.meta.url); const json = JSON.stringify(out);
  fs.writeFileSync(new URL('sha_masts.json', dir), json);
  fs.writeFileSync(new URL('sha_masts.js', dir), '// generated by jobs/gates.mjs SET=masts - do not edit. Inferred apron floodlight masts (src inf); see data/sha_masts.json\nwindow.SHA_MASTS = ' + json + ';\n');
  console.log(`masts written: ${out.masts.length} masts, hash ${out.hash}, inputs ${out.inputs}, uncovered ${out.uncovered.length}, live pass ${Q.stats.ms} ms -> data/sha_masts.json / .js`);
}
const FIX3_PARK = '228,238A,259,264,270';
const FIX4_PARK = '113,115,224,229,233,260,274';   // (the review's F3 renders parked 115, 224, 229, 233, 260, 264, 274)
export default async ({ page, shot, base, W, H }) => {
  const P = process.env.PARK || PARK_DEFAULT;
  const con = { error: 0, warning: 0, pageerror: 0, list: [] };
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') { if (/GPU stall|GL Driver|Automatic fallback/.test(m.text())) return; con[m.type()]++; con.list.push(m.type() + ': ' + m.text().slice(0, 200)); } });
  page.on('pageerror', e => { con.pageerror++; con.list.push('pageerror: ' + e.message); });
  const sets = (process.env.SET || Object.keys(SETS).filter(k => !k.startsWith('fix')).join(';')).split(';').filter(Boolean);
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  let first = true;
  for (const name of sets) {
    const S = SETS[name]; if (!S) { console.log('no set', name); continue; }
    const t = S.t || process.env.T || '2026-11-14T03:00:00Z';
    const q = `?fixedres=1&quality=${S.quality || process.env.QUALITY || 'high'}&t=${encodeURIComponent(t)}&${S.query(S.park4 ? process.env.FIX4_PARK || FIX4_PARK : S.park ? process.env.FIX3_PARK || FIX3_PARK : P)}${process.env.QUERY ? '&' + process.env.QUERY : ''}`;
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
    if (name === 'fix3' || name === 'fix3low') { const R = await mastCheck(page); R.tower = await towerCheck(page, W, H, frames); printMastCheck(R, name); }
    if (name === 'masts') await writeMasts(page);
    if (process.env.CHECK_ONLY) continue;
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
      } else if (tg === 'tower') {
        // the app's Tower view (the cab camera, as the "Tower" view button sets it)
        await page.evaluate(() => { SHA.qa.view('tower'); if (SHA.rig.anim) { SHA.rig.anim.t = SHA.rig.anim.dur; SHA.rig.update(0); } });
      } else if (typeof tg === 'string' && tg.startsWith('masttop:')) {
        // straight down from <h> m at the mast nearest to x, z (fix round 4, F4: the base plate and the envelope lines)
        const [x, z, hgt] = tg.slice(8).split(',').map(Number);
        const m = await page.evaluate(([x, z, hgt]) => { const M = SHA.qa.masts().masts.slice().sort((a, b) => Math.hypot(a.p[0] - x, a.p[1] - z) - Math.hypot(b.p[0] - x, b.p[1] - z))[0];
          SHA.qa.look([M.p[0], SHA.geo.GROUND_Y, M.p[1]], 0, 89.5, hgt, 50); return M; }, [x, z, hgt]);
        console.log('view', vn, 'mast', m.stand, JSON.stringify(m.p));
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
  console.log(`console: ${con.error} errors, ${con.warning} warnings, ${con.pageerror} page errors ${con.list.length ? JSON.stringify(con.list.slice(0, 10)) : '-> clean'}`);
};

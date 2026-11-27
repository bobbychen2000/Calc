// sha3d Phase 3 (P3-B): route path geometry with baked integer pieces (new; no sfo3d code).
// A route is a polyline of taxi-graph centreline vertices (integer cm in the world frame: x = east, z = south). buildPath
// turns it into pieces - straight lines and circular fillet arcs - whose lengths and radii are INTEGER cm. The fillet
// arcs replace the sharp OSM vertices (OSM junctions have no fillets, docs/phase1/stands.md §6), so that the nose gear
// follows a curve with a finite radius and the main gear, which follows the same curve one wheelbase behind (the chord
// model of js/sim/traj.js), stays inside the corner.
//
// Determinism (design §1.4, review M5). Everything here that a commit can reach uses only + - * /, Math.sqrt,
// Math.round / floor / abs / min / max on numbers that are integers or are computed from integers by those operations,
// all of which are correctly rounded in IEEE 754 and therefore identical in every JavaScript engine. No Math.sin / cos /
// tan / atan / atan2 / hypot / exp / pow is called: the arc angle comes from atanDet (a fixed Horner polynomial with
// argument reduction, + - * / only), the tangent lengths from tan(theta / 2) = |u x v| / (|u||v| + u.v). Display
// evaluation (pointAt) may use trigonometry; it is never on the commit path.
//
// Fillet rule (design §4.4 "junction fillets R = 45 m (narrow) / 55 m (wide), cut to the room on the legs", inf):
// - the nominal radius is rNom; a vertex whose deflection is small gets a larger radius, up to the one whose arc departs
//   at most cutTolCm (1 m) from the vertex (so digitised OSM curves and the rapid-exit curves stay smooth and fast);
// - each segment's length is shared between the fillets at its two ends (max-min fair: each end first gets up to half,
//   the rest goes to the end that needs more), and a fillet's two tangent lengths are equal;
// - when the room leaves a corner with a radius below rFloorCm (a corner digitised as two vertices a few metres
//   apart: OSM splits links at every shared node), the two vertices are MERGED into one at the intersection of the outer
//   segments (same turn direction, combined deflection < 150 deg), which restores the full radius - but only while every
//   input vertex the merged corner absorbs stays within mergeDevCm (8 m) of its two legs (fix round 1: cascaded merges had
//   moved corners 60-140 m off the links); the router's path-level turn rule (router.js ROUTER.pathTurn) re-routes a route
//   whose merged corner turns more than 100 deg;
// - every input vertex gets the station of its own place on the path (vS: arc midpoint, or its projection onto the
//   pieces when it was merged; fix round 1, V1);
// - deflections below 1e-9 (tan of the half angle) are straight.
// All values [inf]; see docs/phase3/movement.md §3.

export const PATH = {
  rNomCm: { narrow: 4500, wide: 5500 },   // design §4.4 (inf): junction fillets 45 m narrow / 55 m wide
  rPushCm: 2500,                           // push-turn radius of the nose gear (inf; optA_push.mjs used 20 m)
  rFloorCm: 1500,                          // merge two corners when the room would leave less than this: 15 m, above the largest type's fillet floor 1.6 x 0.27 x wheelbase (13.5 m, B77W) (inf)
  cutTolCm: 100,                           // a small deflection may take a radius up to the one cutting 1 m off the vertex (inf)
  mergeMaxCos: -0.8660254037844386,        // never merge into a corner of >= 150 deg (cos 150 deg)
  mergeKinkTan: 0.2679491924311227,        // a neighbour deflecting < 30 deg (tan of the half angle < tan 15 deg) may be absorbed whatever its sign
  mergeDevCm: 800,                         // fix round 1 (V1 / V3): a merge is kept only if every input vertex it absorbs stays within 8 m of the merged corner's two legs (cascaded merges had moved corners 60-140 m off the links; 4 m left 169 arcs < 15 m, 8 m 39, unbounded 258 route nodes > 20 m off the path) (inf)
  aLatCms2: 100,                           // lateral acceleration in turns, v <= sqrt(a_lat R): 1.0 m/s^2 (design §4.4, inf)
  aLatRapidCms2: 125,                      // on rapid exits and the runway lead: 1.25 m/s^2 (ICAO RET design 93 km/h on 550 m = 1.2 m/s^2, from memory) [inf]
  src: 'inf',
  basis: 'design.md §4.4 (fillets 45 / 55 m, a_lat 1.0 m/s^2); merge / cut tolerance values are this package\'s choices',
};

// ------------------------------------------------------------------------------------------ deterministic arctangent
const PI = Math.PI, PI_2 = Math.PI / 2, PI_4 = Math.PI / 4;
const TAN_PI_8 = 0.41421356237309503;
const ATAN_C = []; for (let k = 33; k >= 1; k -= 2) ATAN_C.push(1 / k);   // 1/33, 1/31, ..., 1/1 (division: exact IEEE)
/** arctangent with + - * / only (identical in every IEEE 754 engine). |error| < 1e-13 rad. */
export function atanDet(x) {
  let sign = 1; if (x < 0) { x = -x; sign = -1; }
  let inv = false; if (x > 1) { x = 1 / x; inv = true; }
  let base = 0; if (x > TAN_PI_8) { x = (x - 1) / (x + 1); base = PI_4; }
  const y2 = x * x; let p = ATAN_C[0];
  for (let i = 1; i < ATAN_C.length; i++) p = ATAN_C[i] - y2 * p;
  let r = base + x * p;
  if (inv) r = PI_2 - r;
  return sign * r;
}
/** angle (rad, 0..pi) between vectors u and v (any length), deterministic */
export function angleDet(ux, uz, vx, vz) {
  const lu = Math.sqrt(ux * ux + uz * uz), lv = Math.sqrt(vx * vx + vz * vz);
  const cr = Math.abs(ux * vz - uz * vx), dt = ux * vx + uz * vz, den = lu * lv + dt;
  if (den <= 0) return PI;
  return 2 * atanDet(cr / den);
}
export const RAD2DEG = 180 / PI;
/** heading in degrees true of a world (x, z) direction (hdgVec(h) = [sin h, -cos h]), deterministic */
export function hdgDet(dx, dz) {
  // angle from north [0, -1] clockwise: atan2(dx, -dz)
  let a;
  if (dz < 0) a = atanDet(dx / -dz);
  else if (dz > 0) a = (dx >= 0 ? PI : -PI) - atanDet(dx / dz);
  else a = dx > 0 ? PI_2 : dx < 0 ? -PI_2 : 0;
  let h = a * RAD2DEG; if (h < 0) h += 360; if (h >= 360) h -= 360;
  return h;
}
export const len2 = (dx, dz) => Math.sqrt(dx * dx + dz * dz);

// ------------------------------------------------------------------------------------------ fillet allocation
function vgeom(P, i) {
  const a = P[i - 1], b = P[i], c = P[i + 1];
  const ux = b.x - a.x, uz = b.z - a.z, vx = c.x - b.x, vz = c.z - b.z;
  const lu = Math.sqrt(ux * ux + uz * uz), lv = Math.sqrt(vx * vx + vz * vz);
  const cr = ux * vz - uz * vx, dt = ux * vx + uz * vz;
  const den = lu * lv + dt;
  const t = den > 0 ? Math.abs(cr) / den : Infinity;         // tan(theta / 2)
  const cosT = lu * lv > 0 ? dt / (lu * lv) : 1;             // cos(theta)
  return { ux: ux / lu, uz: uz / lu, vx: vx / lv, vz: vz / lv, lu, lv, cr, t, cosT, turn: cr > 0 ? 1 : cr < 0 ? -1 : 0 };
}
function desired(g, rNom, cutTol) {
  if (!(g.t > 1e-9)) return 0;
  if (!isFinite(g.t)) return 0;                              // reversal: no fillet (flagged by the caller)
  const c2 = Math.sqrt((1 + g.cosT) / 2);                    // cos(theta / 2)
  const secm1 = 1 / c2 - 1;
  const dNom = rNom * g.t;
  const dTol = secm1 > 0 ? cutTol * g.t / secm1 : Infinity;
  return dTol > dNom ? dTol : dNom;
}
// max-min fair share of each segment between its two end fillets; a fillet uses min(left share, right share)
function allocate(P, G, D) {
  const n = P.length; const T = new Array(n).fill(0);
  let want = D.slice();
  for (let it = 0; it < 4; it++) {
    const left = new Array(n).fill(0), right = new Array(n).fill(0);
    for (let j = 0; j < n - 1; j++) {         // segment j: vertex j -> j + 1, length G[j + 1].lu (or computed)
      const lj = segLen(P, j);
      const wa = j === 0 ? 0 : want[j], wb = j + 1 === n - 1 ? 0 : want[j + 1];
      let ga, gb;
      if (wa + wb <= lj) { ga = wa; gb = wb; }
      else { const h = lj / 2; ga = Math.min(wa, h); gb = Math.min(wb, h); const rest = lj - ga - gb; if (wa > ga) ga += Math.min(rest, wa - ga); else if (wb > gb) gb += Math.min(rest, wb - gb); }
      right[j] = ga; left[j + 1] = gb;
    }
    for (let i = 1; i < n - 1; i++) T[i] = Math.min(D[i], left[i], right[i]);
    want = T.slice();
  }
  return T;
}
/** squared distance from (x, z) to the segment (ax, az)-(bx, bz) (+ - * / only) */
function segD2(ax, az, bx, bz, x, z) { const ex = bx - ax, ez = bz - az, l2 = ex * ex + ez * ez; let t = l2 > 0 ? ((x - ax) * ex + (z - az) * ez) / l2 : 0; if (t < 0) t = 0; else if (t > 1) t = 1; const dx = ax + ex * t - x, dz = az + ez * t - z; return dx * dx + dz * dz; }
const segLen = (P, j) => { const dx = P[j + 1].x - P[j].x, dz = P[j + 1].z - P[j].z; return Math.sqrt(dx * dx + dz * dz); };

/**
 * Build the pieces of a path.
 * @param {Array<{x:number,z:number,tag:any}>} verts  polyline vertices in integer cm; tag = the segment from this vertex to the next
 * @param {object} opt  {rNomCm, rFloorCm, cutTolCm, capOf(tag) -> cm/s, aLatCms2, merge: true, mergeMaxCos (default PATH.mergeMaxCos)}
 * @returns Path {lenCm, pieces: [{kind, s0Cm, lenCm, rCm, turn, vmaxCms, linkId, tag, tagOut, g}], vS: [sCm of each input vertex], warn}
 */
export function buildPath(verts, opt = {}) {
  const rNom = opt.rNomCm ?? PATH.rNomCm.narrow, rFloor = opt.rFloorCm ?? PATH.rFloorCm, cutTol = opt.cutTolCm ?? PATH.cutTolCm;
  const aLat = opt.aLatCms2 ?? PATH.aLatCms2, capOf = opt.capOf || (() => 1e9);
  const warn = [];
  // 1. dedup (< 1 cm), keeping the later segment's tag; P[k].orig = the input vertex indices it stands for
  const P = [];
  for (let i = 0; i < verts.length; i++) {
    const v = verts[i];
    if (P.length) { const q = P[P.length - 1]; const dx = v.x - q.x, dz = v.z - q.z; if (dx * dx + dz * dz < 1) { q.tag = v.tag; q.orig.push(i); continue; } }
    P.push({ x: v.x, z: v.z, tag: v.tag, orig: [i] });
  }
  if (P.length < 2) return { lenCm: 0, pieces: [], vS: verts.map(() => 0), warn: ['degenerate path'] };
  // 2. fillets with corner merging
  let G, D, T;
  const recompute = () => { G = P.map((_, i) => (i > 0 && i < P.length - 1 ? vgeom(P, i) : null)); D = G.map(g => (g ? desired(g, rNom, cutTol) : 0)); T = allocate(P, G, D); };
  recompute();
  if (opt.merge !== false) {
    for (let guard = 0; guard < 4 * P.length; guard++) {
      let merged = false;
      for (let i = 1; i < P.length - 1 && !merged; i++) {
        const g = G[i]; if (!(g.t > 0.02) || !isFinite(g.t)) continue;   // only real corners (> ~2.3 deg)
        const R = T[i] / g.t; if (R >= rFloor || T[i] >= D[i] * 0.999) continue;
        // the limiting neighbour: the side whose share is the smaller
        for (const j of [i + 1, i - 1]) {
          if (j < 1 || j > P.length - 2) continue;
          const h = G[j]; if (!h || !isFinite(h.t)) continue;
          if (h.turn !== g.turn && h.t > PATH.mergeKinkTan) continue;   // a real counter-turn (S-bend): no merge; a small kink of either sign: absorbed
          const a = Math.min(i, j), b = a + 1;              // merge vertices a and b
          const p0 = P[a - 1], pa = P[a], pb = P[b], p3 = P[b + 1];
          const ux = pa.x - p0.x, uz = pa.z - p0.z, wx = p3.x - pb.x, wz = p3.z - pb.z;
          const lu = Math.sqrt(ux * ux + uz * uz), lw = Math.sqrt(wx * wx + wz * wz);
          if ((ux * wx + uz * wz) / (lu * lw) <= (opt.mergeMaxCos ?? PATH.mergeMaxCos)) continue;   // would be >= 150 deg (push paths: 100 deg, fix round 2)
          const den = ux * wz - uz * wx; if (Math.abs(den) < 1e-9 * lu * lw) continue;
          const lam = ((pb.x - p0.x) * wz - (pb.z - p0.z) * wx) / den;        // p0 + lam u = intersection
          if (!(lam > 0.5)) continue;
          const nx = p0.x + ux * lam, nz = p0.z + uz * lam;
          const mu = ((nx - pb.x) * wx + (nz - pb.z) * wz) / (lw * lw);        // along w from pb (must be <= 0: before pb)
          if (mu > 0.3) continue;                                               // the merged corner may lie a little past pb, never near p3
          const dpa = Math.sqrt((nx - pa.x) * (nx - pa.x) + (nz - pa.z) * (nz - pa.z));
          if (dpa > 3 * segLen(P, a) + 3000) continue;                         // far outside: not a corner pair
          const orig = pa.orig.concat(pb.orig);
          const dev2 = PATH.mergeDevCm * PATH.mergeDevCm;
          if (orig.some(k => Math.min(segD2(p0.x, p0.z, nx, nz, verts[k].x, verts[k].z), segD2(nx, nz, p3.x, p3.z, verts[k].x, verts[k].z)) > dev2)) continue;   // the corner would leave the links
          const nv = { x: nx, z: nz, tag: pb.tag, orig, merged: true };
          P.splice(a, 2, nv); merged = true; break;
        }
      }
      if (!merged) break;
      recompute();
    }
  }
  // 3. pieces
  const pieces = []; let s = 0;
  let cx = P[0].x, cz = P[0].z;
  const vMid = new Array(P.length).fill(null);   // [s0, s1] of the arc at vertex i (or [s, s])
  const addLine = (x1, z1, tag) => {
    const dx = x1 - cx, dz = z1 - cz, L = Math.sqrt(dx * dx + dz * dz); const lc = Math.round(L);
    if (lc > 0) { pieces.push({ kind: 'line', s0Cm: s, lenCm: lc, rCm: 0, turn: 0, vmaxCms: capOf(tag), linkId: tag ? tag.link : null, tag, g: { x0: cx, z0: cz, x1, z1, hx: dx / L, hz: dz / L, len: L } }); s += lc; }
    cx = x1; cz = z1;
  };
  for (let i = 1; i < P.length; i++) {
    const tagIn = P[i - 1].tag;
    if (i === P.length - 1) { addLine(P[i].x, P[i].z, tagIn); vMid[i] = [s, s]; break; }
    const g = G[i], Ti = T[i];
    if (!(Ti > 0.5) || !(g.t > 1e-9) || !isFinite(g.t)) {
      if (!isFinite(g.t)) warn.push('reversal at vertex ' + P[i].orig[0]);
      addLine(P[i].x, P[i].z, tagIn); vMid[i] = [s, s]; continue;
    }
    const ax = P[i].x - g.ux * Ti, az = P[i].z - g.uz * Ti, bx = P[i].x + g.vx * Ti, bz = P[i].z + g.vz * Ti;
    addLine(ax, az, tagIn);
    const R = Ti / g.t, th = 2 * atanDet(g.t), L = R * th, lc = Math.round(L);
    // centre: from the tangent point A along the left (turn > 0: v is counter-clockwise from u in x-z) normal
    const nx = -g.uz * g.turn, nz = g.ux * g.turn;
    const ccx = ax + nx * R, ccz = az + nz * R;
    const tagOut = P[i].tag, rc = Math.round(R);
    const al = opt.aLatOf ? opt.aLatOf(tagIn, tagOut) : aLat;
    const vmax = Math.min(capOf(tagIn), capOf(tagOut), Math.floor(Math.sqrt(al * R)));
    const s0 = s;
    if (lc > 0) { pieces.push({ kind: 'arc', s0Cm: s, lenCm: lc, rCm: rc, turn: g.turn, vmaxCms: vmax, linkId: tagIn ? tagIn.link : null, tag: tagIn, tagOut, g: { x0: ax, z0: az, hx: g.ux, hz: g.uz, ox: g.vx, oz: g.vz, T: Ti, cx: ccx, cz: ccz, R, th, len: L } }); s += lc; }
    cx = bx; cz = bz; vMid[i] = [s0, s];
  }
  vMid[0] = [0, 0];
  // 4. s of every input vertex (fix round 1, V1). A vertex that kept its own corner gets its arc midpoint (the vertex lies
  //    on the bisector, so that IS its projection onto the arc) or, without a fillet, its own station. Input vertices that
  //    were merged into another corner (or deduplicated) get the station of their projection onto the final pieces: the
  //    nearest point of the pieces between the neighbouring corners' arcs, monotone along the route. (Round 0 spread them
  //    over the merged arc, which put e.g. 27 nodes of 1.1 km of taxiway C inside 70 m.) + - * / sqrt and atanDet only.
  const vS = new Array(verts.length).fill(0);
  let prevS = 0;
  for (let i = 0; i < P.length; i++) {
    const [a, b] = vMid[i] || [s, s]; const o = P[i].orig;
    if (o.length === 1 && !P[i].merged) { const si = Math.max(prevS, Math.round((a + b) / 2)); vS[o[0]] = si; prevS = si; continue; }
    const w0 = i > 0 && vMid[i - 1] ? vMid[i - 1][0] : 0, w1 = i < P.length - 1 && vMid[i + 1] ? vMid[i + 1][1] : s;
    for (let k = 0; k < o.length; k++) {
      const q = verts[o[k]]; const pr = projectOnPieces(pieces, q.x, q.z, Math.max(w0, prevS), w1);
      const si = Math.max(prevS, pr == null ? Math.round((a + b) / 2) : pr.s); vS[o[k]] = si; prevS = si;
    }
  }
  return { lenCm: s, pieces, vS, warn, nMerged: verts.length - P.length };
}

/** deterministic atan2 (rad) from atanDet: + - * / only */
export function atan2Det(y, x) {
  if (x > 0) return atanDet(y / x);
  if (x < 0) return y >= 0 ? atanDet(y / x) + PI : atanDet(y / x) - PI;
  return y > 0 ? PI_2 : y < 0 ? -PI_2 : 0;
}
/**
 * Point at fraction u (0..1 of the UNCUT arc) of an arc piece's geometry, deterministic (+ - * / sqrt): bisection of the
 * arc by chord midpoints projected onto the circle (fix round 2: the push end inside a gentle arc); |error| < 1e-4 cm.
 */
export function arcPointDet(g, u) {
  let a = [g.x0, g.z0], b = arcEnd(g), ua = 0, ub = 1;
  for (let it = 0; it < 30 && ub - ua > 1e-9; it++) {
    const mx = a[0] + b[0] - 2 * g.cx, mz = a[1] + b[1] - 2 * g.cz, m = Math.sqrt(mx * mx + mz * mz) || 1;
    const c = [g.cx + mx * g.R / m, g.cz + mz * g.R / m], uc = (ua + ub) / 2;
    if (u <= uc) { b = c; ub = uc; } else { a = c; ua = uc; }
  }
  const k = ub > ua ? (u - ua) / (ub - ua) : 0; return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k];
}
/** end point of an arc piece (deterministic: tangent point + T along the outgoing direction) */
function arcEnd(g) { const vx = g.x0 + g.hx * g.T, vz = g.z0 + g.hz * g.T; return [vx + g.ox * g.T, vz + g.oz * g.T]; }
/**
 * Station (integer cm) and squared distance of the nearest point of the pieces to (x, z), over the pieces overlapping
 * [sLo, sHi] and with s >= sLo (commit path: + - * / sqrt, atanDet). Returns {s, d2} or null.
 */
export function projectOnPieces(pieces, x, z, sLo = 0, sHi = Infinity) {
  let best = null;
  for (const p of pieces) {
    const e = p.s0Cm + p.lenCm; if (e < sLo || p.s0Cm > sHi || p.lenCm <= 0) continue;
    const g = p.g; let u, px, pz;   // u in [0, 1] along the piece
    if (p.kind === 'line') {
      const t = (x - g.x0) * g.hx + (z - g.z0) * g.hz; u = g.len > 0 ? t / g.len : 0;
    } else {
      const ax = g.x0 - g.cx, az = g.z0 - g.cz, bx = x - g.cx, bz = z - g.cz;
      const phi = p.turn * atan2Det(ax * bz - az * bx, ax * bx + az * bz);   // angle travelled from the arc start
      u = g.th > 0 ? phi / g.th : 0;
      if (phi < g.th / 2 - PI) u = 1;                     // on the far side of the circle: nearer the arc end than its start
    }
    const uMin = p.s0Cm >= sLo ? 0 : (sLo - p.s0Cm) / p.lenCm;
    if (!(u >= uMin)) u = uMin; if (u > 1) u = 1;
    if (p.kind === 'line') { px = g.x0 + g.hx * u * g.len; pz = g.z0 + g.hz * u * g.len; }
    else if (u <= 0) { px = g.x0; pz = g.z0; }
    else if (u >= 1) { const q = arcEnd(g); px = q[0]; pz = q[1]; }
    else {   // the point at angle u th on the circle: centre + R (b / |b|) (the nearest circle point to (x, z))
      const bx = x - g.cx, bz = z - g.cz, lb = Math.sqrt(bx * bx + bz * bz);
      if (lb > 0) { px = g.cx + bx * g.R / lb; pz = g.cz + bz * g.R / lb; } else { px = g.x0; pz = g.z0; }
    }
    const d2 = (x - px) * (x - px) + (z - pz) * (z - pz); const sp = Math.round(p.s0Cm + u * p.lenCm);
    if (!best || d2 < best.d2) best = { s: sp, d2 };
  }
  return best;
}

/**
 * Path-level turn measures (fix round 1, V3): the largest single-arc deflection and the largest heading change within any
 * window of windowCm along the path (degrees), with where they are. The heading is piecewise linear in s (lines 0, arcs
 * turn x th / len), so the window maximum is attained with a window end on a piece boundary: every boundary is tried as
 * the window start and as the window end. Deterministic (+ - * / only, th from atanDet).
 * @returns {{maxArcDeg, arcS0Cm, arcS1Cm, maxWinDeg, winS0Cm, winS1Cm}}
 */
export function turnProfile(path, windowCm = 4000) {
  const P = path.pieces; const n = P.length; const H = new Array(n + 1); H[0] = 0;
  let maxArc = 0, aS0 = 0, aS1 = 0;
  for (let i = 0; i < n; i++) {
    const p = P[i]; const d = p.kind === 'arc' ? p.turn * p.g.th : 0;   // (a cut arc carries its shortened th)
    H[i + 1] = H[i] + d;
    if (p.kind === 'arc' && Math.abs(d) > maxArc) { maxArc = Math.abs(d); aS0 = p.s0Cm; aS1 = p.s0Cm + p.lenCm; }
  }
  const total = n ? P[n - 1].s0Cm + P[n - 1].lenCm : 0;
  const hAt = (s) => {   // cumulative heading change (rad) at s
    if (s <= 0 || !n) return 0; if (s >= total) return H[n];
    let lo = 0, hi = n - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (P[m].s0Cm <= s) lo = m; else hi = m - 1; }
    const p = P[lo]; return H[lo] + (H[lo + 1] - H[lo]) * (s - p.s0Cm) / p.lenCm;
  };
  let maxWin = 0, w0 = 0;
  for (let i = 0; i <= n; i++) {
    const b = i < n ? P[i].s0Cm : total;
    for (const a of [b, b - windowCm]) { if (a < 0 || a + windowCm > total + windowCm) continue; const f = Math.abs(hAt(Math.min(total, a + windowCm)) - hAt(a)); if (f > maxWin) { maxWin = f; w0 = a; } }
  }
  const R2D = 180 / PI;
  return { maxArcDeg: maxArc * R2D, arcS0Cm: aS0, arcS1Cm: aS1, maxWinDeg: maxWin * R2D, winS0Cm: w0, winS1Cm: Math.min(total, w0 + windowCm) };
}

/** index of the piece containing s (binary search on s0Cm) */
export function pieceAt(path, sCm) {
  const P = path.pieces; let lo = 0, hi = P.length - 1;
  if (hi < 0) return -1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (P[m].s0Cm <= sCm) lo = m; else hi = m - 1; }
  return lo;
}
/** DISPLAY: world point (cm) and unit tangent at s (cm); beyond the ends the path continues straight. Uses cos / sin. */
export function pointAt(path, sCm, out = {}) {
  const P = path.pieces;
  if (!P.length) { out.x = 0; out.z = 0; out.hx = 0; out.hz = -1; return out; }
  if (sCm <= 0) { const g = P[0].g; out.x = g.x0 + g.hx * sCm; out.z = g.z0 + g.hz * sCm; out.hx = g.hx; out.hz = g.hz; return out; }
  const i = pieceAt(path, sCm); const p = P[i], g = p.g;
  let u = (sCm - p.s0Cm) / p.lenCm;
  if (i === P.length - 1 && u > 1) {     // beyond the end: straight along the end tangent
    endOf(p, out); const ex = (sCm - p.s0Cm - p.lenCm); out.x += out.hx * ex; out.z += out.hz * ex; return out;
  }
  if (u > 1) u = 1;
  if (p.kind === 'line') { const d = u * g.len; out.x = g.x0 + g.hx * d; out.z = g.z0 + g.hz * d; out.hx = g.hx; out.hz = g.hz; return out; }
  const ph = p.turn * u * g.th, c = Math.cos(ph), sn = Math.sin(ph);
  const rx = g.x0 - g.cx, rz = g.z0 - g.cz;
  out.x = g.cx + rx * c - rz * sn; out.z = g.cz + rx * sn + rz * c;
  out.hx = g.hx * c - g.hz * sn; out.hz = g.hx * sn + g.hz * c;
  return out;
}
function endOf(p, out) {
  const g = p.g;
  if (p.kind === 'line') { out.x = g.x0 + g.hx * g.len; out.z = g.z0 + g.hz * g.len; out.hx = g.hx; out.hz = g.hz; return out; }
  const ph = p.turn * g.th, c = Math.cos(ph), sn = Math.sin(ph), rx = g.x0 - g.cx, rz = g.z0 - g.cz;
  out.x = g.cx + rx * c - rz * sn; out.z = g.cz + rx * sn + rz * c; out.hx = g.hx * c - g.hz * sn; out.hz = g.hx * sn + g.hz * c; return out;
}
/** TEST: independent float evaluation of a piece's length with Math.hypot / Math.atan2 / Math.tan (integer vs float <= 1 cm) */
export function floatLen(p) {
  const g = p.g;
  if (p.kind === 'line') return Math.hypot(g.x1 - g.x0, g.z1 - g.z0);
  const th = Math.atan2(Math.abs(g.hx * g.oz - g.hz * g.ox), g.hx * g.ox + g.hz * g.oz);
  return g.T / Math.tan(th / 2) * th;
}

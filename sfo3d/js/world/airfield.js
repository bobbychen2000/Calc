// Airfield layout in airport frame (s,t) meters, painter for ground map, taxi-line ribbons
import { RUNWAYS, TERMINAL_CENTER, PIERS, ITB, stToWorld, GROUND_Y, DIR_S, DIR_T } from '../geo.js';
import { rng, clamp } from '../math.js';

export const APT_RECT = { s0: -2800, t0: -1760, w: 4700, h: 3220, res: 1.0 }; // 1 m/px

// Runways axis-aligned in (s,t), derived from the FAA NASR runway ends (geo.js RUNWAYS / RWY_ENDS, cycle 2026-09-03)
// through the exact frame (24 Sep 2026; the earlier hand constants were in the legacy equirectangular frame and up to
// 1.9 m off at the ends). c = mean cross-axis coordinate of the two ends (the grid is aligned with 10/28; 1/19 are
// parallel to t to < 0.05 m), a0/a1 = along-axis coordinates of the first / second named end.
export const RWY = RUNWAYS.map(r => {
  const axis = r.ends[0].startsWith('1') && !r.ends[0].startsWith('10') ? 1 : 0;
  const u0 = r.st0[axis], u1 = r.st1[axis], c = (r.st0[1 - axis] + r.st1[1 - axis]) / 2;
  return { name: r.ends.slice(), axis, c: +c.toFixed(2), a0: +u0.toFixed(2), a1: +u1.toFixed(2), disp0: +r.dispA.toFixed(2), disp1: +r.dispB.toFixed(2) };
});
export const RWY_W = 60.96;

// Taxiway centerlines (polylines in s,t), width
export const TAXIWAYS = [
  { id: 'PS', w: 23, pts: [[-1780, -140], [1650, -140]] },
  { id: 'PN', w: 23, pts: [[-1930, 385], [1650, 385]] },
  { id: 'PW', w: 23, pts: [[-171, -1470], [-171, 1260]] },
  { id: 'PE', w: 23, pts: [[356, -1500], [356, 1240]] },
  // runway end connectors
  { id: 'E1L', w: 23, pts: [[-171, -1400], [-21.6, -1400]] },
  { id: 'E1R', w: 23, pts: [[356, -1476], [206.6, -1476]] },
  { id: 'N19', w: 23, pts: [[-171, 1235], [356, 1235]] },
  { id: 'N19R', w: 23, pts: [[-171, 975], [-21.6, 975]] },
  { id: 'W10', w: 23, pts: [[-1780, -140], [-1800, 6.4], [-1935, 235], [-1930, 385]] },
  // cross connectors between PS <-> 10R <-> 10L <-> PN
  ...[-1450, -1100, -700, 950, 1400, 1650].map((s, i) => ({ id: 'X' + i, w: 23, pts: [[s, -140], [s, 385]] })),
  // high speed exits
  { id: 'HSE28L', w: 23, pts: [[700, 6.4], [560, -60], [447, -140]] },
  { id: 'HSE28L2', w: 23, pts: [[-120, 6.4], [-260, -60], [-373, -140]] },
  { id: 'HSE28R', w: 23, pts: [[700, 235], [560, 305], [447, 385]] },
  { id: 'HSE28R2', w: 23, pts: [[-120, 235], [-260, 305], [-373, 385]] },
  // links from PW/PE to runways 1L/1R mid
  { id: 'L1', w: 23, pts: [[-171, -900], [-21.6, -900]] },
  { id: 'L2', w: 23, pts: [[-171, -500], [-21.6, -500]] },
  { id: 'L3', w: 23, pts: [[-21.6, -700], [206.6, -700], [356, -700]] },
  { id: 'L4', w: 23, pts: [[-171, 650], [-21.6, 650], [206.6, 650], [356, 650]] },
];

// Paved areas (polygons in s,t) and concrete flag
export const APRONS = [
  { conc: 1, pts: [[-1560, -165], [-195, -165], [-195, -1420], [-560, -1520], [-1180, -1520], [-1560, -1380]] }, // terminal apron
  { conc: 1, pts: [[-1800, 420], [-240, 420], [-240, 640], [-1800, 640]] }, // north cargo
  { conc: 1, pts: [[-1060, 700], [-200, 700], [-200, 1270], [-1060, 1270]] }, // maintenance
  { conc: 1, pts: [[-640, -1640], [-200, -1640], [-200, -1450], [-640, -1450]] }, // south
  { conc: 0, pts: [[390, -300], [1100, -300], [1100, -180], [390, -180]] }, // remote holding pad
];
// Landside (roads/parking/buildings) polygons
export function landside() {
  const [cs, ct] = TERMINAL_CENTER;
  const circle = (r, n = 64) => Array.from({ length: n }, (_, i) => { const a = i / n * Math.PI * 2; return [cs + Math.cos(a) * r, ct + Math.sin(a) * r]; });
  const band = (pts, w) => ({ kind: 'roadline', pts, w });
  return [
    { kind: 'road', pts: circle(236) },
    { kind: 'road', pts: [[-1420, -1170], [-1050, -1170], [-1050, -530], [-1420, -530]] },
    band([[-1400, -850], [-1800, -850], [-2300, -700], [-2800, -650]], 42),
    band([[-1400, -620], [-1700, -450], [-2150, -260]], 24),
    band([[-1400, -1080], [-1600, -1250], [-1900, -1350], [-2800, -1420]], 26),
    band([[-1100, -1170], [-900, -1380], [-600, -1480]], 16),
    { kind: 'parking', pts: [[-2550, -1330], [-1700, -1330], [-1700, -980], [-2550, -980]] },
    { kind: 'parking', pts: [[-2550, -560], [-1900, -560], [-1900, -380], [-2550, -380]] },
    { kind: 'parking', pts: [[-1650, -1250], [-1470, -1250], [-1470, -1150], [-1650, -1150]] },
  ];
}

export function pierFrame(p) {
  const a = p.ang * Math.PI / 180; const d = [Math.cos(a), Math.sin(a)], n = [-Math.sin(a), Math.cos(a)];
  return { d, n, root: p.root, tip: [p.root[0] + d[0] * p.len, p.root[1] + d[1] * p.len] };
}
// pier outline polygon in (s,t), CCW
export function pierOutline(p) {
  const f = pierFrame(p); const hw = p.w / 2; const out = [];
  const P = (r, o) => [p.root[0] + f.d[0] * r + f.n[0] * o, p.root[1] + f.d[1] * r + f.n[1] * o];
  const r0 = -10, r1 = p.len;
  if (p.end === 'rotunda') {
    const R = p.R; const rc = r1 - R * 0.6; const ha = Math.asin(hw / R);
    out.push(P(r0, -hw), P(rc - R * Math.cos(ha), -hw));
    for (let i = 1; i < 28; i++) { const a = -Math.PI + ha + (2 * Math.PI - 2 * ha) * i / 28; out.push(P(rc + Math.cos(a) * R, Math.sin(a) * R)); }
    out.push(P(rc - R * Math.cos(ha), hw), P(r0, hw));
  } else if (p.end === 'hammer') {
    const cw = 34, ch = p.cross / 2;
    out.push(P(r0, -hw), P(r1 - cw, -hw), P(r1 - cw, -ch), P(r1, -ch), P(r1, ch), P(r1 - cw, ch), P(r1 - cw, hw), P(r0, hw));
  } else {
    out.push(P(r0, -hw), P(r1 - hw, -hw));
    for (let i = 1; i < 12; i++) { const a = -Math.PI / 2 + Math.PI * i / 12; out.push(P(r1 - hw + Math.cos(a) * hw, Math.sin(a) * hw)); }
    out.push(P(r1 - hw, hw), P(r0, hw));
  }
  return out;
}

// Gate stands: walk each pier outline, place candidates, reject collisions
export function computeGates() {
  const gates = []; const R = rng(1234);
  const circles = [];
  const addSeg = (a, b, rad, tag) => { const L = Math.hypot(b[0] - a[0], b[1] - a[1]); for (let d = 0; d <= L; d += 8) circles.push({ c: [a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L], rad, pier: tag }); };
  PIERS.forEach(p => { const o = pierOutline(p); for (let i = 0; i < o.length; i++) addSeg(o[i], o[(i + 1) % o.length], 6, p.name); });
  // terminal ring & ITB as obstacles
  for (let a = 0; a < 360; a += 3) { const r = a * Math.PI / 180; circles.push({ c: [TERMINAL_CENTER[0] + Math.cos(r) * 225, TERMINAL_CENTER[1] + Math.sin(r) * 225], rad: 16, pier: 'ring' }); }
  addSeg([ITB.s + ITB.hs, ITB.t - ITB.ht], [ITB.s + ITB.hs, ITB.t + ITB.ht], 10, 'itb');
  const footprint = (nose, dir, len, span) => {
    const pts = []; const side = [-dir[1], dir[0]];
    for (let k = 0; k <= 7; k++) pts.push({ c: [nose[0] - dir[0] * len * k / 7, nose[1] - dir[1] * len * k / 7], rad: 3.5 });
    const wc = [nose[0] - dir[0] * len * 0.47, nose[1] - dir[1] * len * 0.47];
    for (let k = -4; k <= 4; k++) pts.push({ c: [wc[0] + side[0] * span / 2 * k / 4 - dir[0] * Math.abs(k) * span * 0.05, wc[1] + side[1] * span / 2 * k / 4 - dir[1] * Math.abs(k) * span * 0.05], rad: 3 });
    const tc = [nose[0] - dir[0] * len * 0.93, nose[1] - dir[1] * len * 0.93];
    for (let k = -2; k <= 2; k++) pts.push({ c: [tc[0] + side[0] * span * 0.17 * k / 2, tc[1] + side[1] * span * 0.17 * k / 2], rad: 3 });
    return pts;
  };
  const fits = (pts, pierName) => {
    for (const q of pts) {
      if (q.c[0] > -200 || q.c[1] > -168 || q.c[1] < -1500) return false;
      for (const c of circles) { if (c.pier === pierName && c.skip) continue; if (Math.hypot(q.c[0] - c.c[0], q.c[1] - c.c[1]) < q.rad + c.rad) return false; }
    }
    return true;
  };
  PIERS.forEach(p => {
    const o = pierOutline(p); const f = pierFrame(p);
    // perimeter walk
    const cum = [0]; for (let i = 0; i < o.length; i++) cum.push(cum[i] + Math.hypot(o[(i + 1) % o.length][0] - o[i][0], o[(i + 1) % o.length][1] - o[i][1]));
    const total = cum[cum.length - 1];
    let d = 12;
    while (d < total) {
      let i = 0; while (cum[i + 1] < d) i++;
      const a = o[i], b = o[(i + 1) % o.length]; const L = cum[i + 1] - cum[i]; const u = (d - cum[i]) / L;
      const pt = [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
      const ex = (b[0] - a[0]) / L, ey = (b[1] - a[1]) / L; const nrm = [ey, -ex]; // outward for CCW? verify below
      // along-pier distance from root
      const along = (pt[0] - p.root[0]) * f.d[0] + (pt[1] - p.root[1]) * f.d[1];
      if (along < 30) { d += 6; continue; }
      const wideP = R() < p.wide; const cls = wideP ? ((p.name === 'A' || p.name === 'G') && R() < 0.22 ? 'F' : 'E') : 'C';
      const len = cls === 'F' ? 74 : cls === 'E' ? 76 : 47, span = cls === 'F' ? 80 : cls === 'E' ? 68 : 41;
      let outN = nrm; const probe = [pt[0] + nrm[0] * 2, pt[1] + nrm[1] * 2];
      if (pointIn(probe, o)) outN = [-nrm[0], -nrm[1]];
      const dir = [-outN[0], -outN[1]];
      const noseGap = wideP ? 19 : 16;
      const nose = [pt[0] + outN[0] * noseGap, pt[1] + outN[1] * noseGap];
      circles.forEach(c => { if (c.pier === p.name) c.skip = Math.hypot(c.c[0] - pt[0], c.c[1] - pt[1]) < 22; });
      const fp = footprint(nose, dir, len, span);
      const ok = fits(fp, p.name);
      circles.forEach(c => { c.skip = false; });
      if (ok) {
        gates.push({ pier: p.name, attach: pt, nose, dir, wide: wideP, cls, len, span, id: p.name + (gates.filter(g => g.pier === p.name).length + 1), outN });
        fp.forEach(q => circles.push({ c: q.c, rad: q.rad + 3, pier: '_' }));
        d += cls === 'F' ? 84 : wideP ? 72 : 45;
      } else d += 6;
    }
  });
  return gates;
}
function pointIn(pt, poly) { let inside = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const [xi, yi] = poly[i], [xj, yj] = poly[j]; if (((yi > pt[1]) !== (yj > pt[1])) && (pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi)) inside = !inside; } return inside; }

// ---------- ground map painter ----------
export function paintAirportMap(gates) {
  const W = Math.round(APT_RECT.w / APT_RECT.res), H = Math.round(APT_RECT.h / APT_RECT.res);
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const cx = cv.getContext('2d');
  const P = (s, t) => [(s - APT_RECT.s0) / APT_RECT.res, (APT_RECT.t0 + APT_RECT.h - t) / APT_RECT.res];
  const poly = (pts) => { cx.beginPath(); pts.forEach((p, i) => { const q = P(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.closePath(); };
  const line = (pts, w) => { cx.lineWidth = w / APT_RECT.res; cx.beginPath(); pts.forEach((p, i) => { const q = P(p[0], p[1]); i ? cx.lineTo(q[0], q[1]) : cx.moveTo(q[0], q[1]); }); cx.stroke(); };
  cx.lineJoin = 'round'; cx.lineCap = 'round';
  const layer = (fn) => { cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); cx.fillStyle = '#fff'; cx.strokeStyle = '#fff'; fn(); return cx.getImageData(0, 0, W, H).data; };
  // R: pavement
  const pave = layer(() => {
    APRONS.forEach(a => { poly(a.pts); cx.fill(); });
    RWY.forEach(r => { const hw = RWY_W / 2 + 7.5; const pts = r.axis === 0 ? [[r.a0 - 60, r.c - hw], [r.a1, r.c - hw], [r.a1, r.c + hw], [r.a0 - 60, r.c + hw]] : [[r.c - hw, r.a0 - 60], [r.c + hw, r.a0 - 60], [r.c + hw, r.a1 + 60], [r.c - hw, r.a1 + 60]]; poly(pts); cx.fill(); });
    TAXIWAYS.forEach(t => line(t.pts, t.w + 15));
    landside().forEach(l => { if (l.kind === 'roadline') line(l.pts, l.w); else { poly(l.pts); cx.fill(); } });
  });
  // G: concrete
  const conc = layer(() => {
    APRONS.forEach(a => { if (a.conc) { poly(a.pts); cx.fill(); } });
  });
  // B: wear / rubber / stains
  const wear = layer(() => {
    cx.globalAlpha = 0.35; cx.strokeStyle = '#fff';
    TAXIWAYS.forEach(t => line(t.pts, 5));
    cx.globalAlpha = 0.18;
    gates.forEach(g => { line([g.nose, [g.nose[0] - g.dir[0] * (g.len + 40), g.nose[1] - g.dir[1] * (g.len + 40)]], 3);
      const n = [-g.dir[1], g.dir[0]]; const ex = g.wide ? 10 : 5.8; const c = [g.nose[0] - g.dir[0] * g.len * 0.42, g.nose[1] - g.dir[1] * g.len * 0.42];
      for (const sg of [-1, 1]) { const q = P(c[0] + n[0] * ex * sg, c[1] + n[1] * ex * sg); cx.beginPath(); cx.ellipse(q[0], q[1], 3, 3, 0, 0, 7); cx.fill(); } });
    cx.globalAlpha = 1;
  });
  // A: landside category (roads/parking = 1)
  const cat = layer(() => { landside().forEach(l => { cx.fillStyle = cx.strokeStyle = l.kind === 'parking' ? '#999' : '#fff'; if (l.kind === 'roadline') line(l.pts, l.w); else { poly(l.pts); cx.fill(); } }); });
  const out = new Uint8Array(W * H * 4);
  for (let i = 0; i < W * H; i++) { out[i * 4] = pave[i * 4]; out[i * 4 + 1] = conc[i * 4]; out[i * 4 + 2] = wear[i * 4]; out[i * 4 + 3] = cat[i * 4]; }
  return { data: out, w: W, h: H };
}

// ---------- taxi line ribbons (yellow), gate lead-ins, hold short markings ----------
export function buildMarkingRibbons(gates) {
  const pos = [], col = [], idx = [];
  const Y = GROUND_Y + 0.02;
  const yellow = [0.85, 0.62, 0.08, 1], white = [0.85, 0.85, 0.82, 1], red = [0.7, 0.08, 0.06, 1], black = [0.03, 0.03, 0.03, 1];
  const quad = (a, b, w, c, y = Y) => { // segment a->b in s,t
    const dx = b[0] - a[0], dy = b[1] - a[1]; const L = Math.hypot(dx, dy); if (L < 1e-3) return;
    const nx = -dy / L * w / 2, ny = dx / L * w / 2; const base = pos.length / 3;
    [[a[0] + nx, a[1] + ny], [a[0] - nx, a[1] - ny], [b[0] - nx, b[1] - ny], [b[0] + nx, b[1] + ny]].forEach(p => { const wp = stToWorld(p[0], p[1], y); pos.push(...wp); col.push(...c); });
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  };
  const poly = (pts, w, c, dash = 0, gap = 0) => {
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (!dash) { const n = Math.max(1, Math.ceil(L / 50)); for (let k = 0; k < n; k++) quad(lerp2(a, b, k / n), lerp2(a, b, (k + 1) / n), w, c); }
      else { for (let d = 0; d < L; d += dash + gap) quad(lerp2(a, b, d / L), lerp2(a, b, Math.min(L, d + dash) / L), w, c); }
    }
  };
  const lerp2 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  // taxiway centerlines, broken where they cross runways
  const onRunway = (p) => RWY.some(r => { const u = r.axis === 0 ? p[0] : p[1], v = r.axis === 0 ? p[1] : p[0]; return u > r.a0 - 5 && u < r.a1 + 5 && Math.abs(v - r.c) < RWY_W / 2 + 1; });
  TAXIWAYS.forEach(t => {
    for (let i = 0; i < t.pts.length - 1; i++) {
      const a = t.pts[i], b = t.pts[i + 1]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const n = Math.ceil(L / 4);
      for (let k = 0; k < n; k++) { const p0 = lerp2(a, b, k / n), p1 = lerp2(a, b, (k + 1) / n); if (!onRunway(p0) && !onRunway(p1)) { quad(p0, p1, 0.35, black); } }
      for (let k = 0; k < n; k++) { const p0 = lerp2(a, b, k / n), p1 = lerp2(a, b, (k + 1) / n); if (!onRunway(p0) && !onRunway(p1)) quad(p0, p1, 0.18, yellow, Y + 0.005); }
      // edge lines (double yellow) along taxiways
    }
  });
  // hold-short markings where taxiways meet runways
  TAXIWAYS.forEach(t => {
    for (let i = 0; i < t.pts.length - 1; i++) {
      const a = t.pts[i], b = t.pts[i + 1]; const L = Math.hypot(b[0] - a[0], b[1] - a[1]); const n = Math.ceil(L / 2);
      let prev = onRunway(a);
      for (let k = 1; k <= n; k++) {
        const p = lerp2(a, b, k / n); const cur = onRunway(p);
        if (cur !== prev) {
          const dir = [(b[0] - a[0]) / L, (b[1] - a[1]) / L]; const sgn = cur ? -1 : 1; // hold line placed on the taxiway side
          const hp = [p[0] + dir[0] * sgn * 45, p[1] + dir[1] * sgn * 45]; const nrm = [-dir[1], dir[0]];
          for (let j = 0; j < 4; j++) {
            const off = (j * 0.6 + 0.15) * sgn; const c0 = [hp[0] + dir[0] * off, hp[1] + dir[1] * off];
            const e0 = [c0[0] + nrm[0] * 11, c0[1] + nrm[1] * 11], e1 = [c0[0] - nrm[0] * 11, c0[1] - nrm[1] * 11];
            if (j < 2) poly([e0, e1], 0.3, yellow); else poly([e0, e1], 0.3, yellow, 0.9, 0.9);
          }
        }
        prev = cur;
      }
    }
  });
  // gate lead-in lines + stop bars + safety envelopes
  gates.forEach(g => {
    const back = [g.nose[0] - g.dir[0] * (g.len + 60), g.nose[1] - g.dir[1] * (g.len + 60)];
    poly([back, [g.nose[0] + g.dir[0] * 3, g.nose[1] + g.dir[1] * 3]], 0.18, yellow);
    const n = [-g.dir[1], g.dir[0]];
    const sb = [g.nose[0] + g.dir[0] * 1.5, g.nose[1] + g.dir[1] * 1.5];
    poly([[sb[0] + n[0] * 2.5, sb[1] + n[1] * 2.5], [sb[0] - n[0] * 2.5, sb[1] - n[1] * 2.5]], 0.3, yellow);
    // red safety envelope (rectangle around stand)
    const hw = g.span / 2 + 3, l0 = -2, l1 = g.len + 6;
    const corner = (u, v) => [g.nose[0] - g.dir[0] * u + n[0] * v, g.nose[1] - g.dir[1] * u + n[1] * v];
    poly([corner(l0, -hw), corner(l1, -hw)], 0.2, red, 1.2, 0.8);
    poly([corner(l0, hw), corner(l1, hw)], 0.2, red, 1.2, 0.8);
    // equipment restraint line (white) near pier
    poly([corner(-8, -hw + 4), corner(-8, hw - 4)], 0.2, white);
  });
  // taxilane centerlines between piers (bisectors), vehicle service road ring & pier-side lanes
  const [cs, ct] = TERMINAL_CENTER;
  const angs = PIERS.map(p => { const f = pierFrame(p); const tip = f.tip; return Math.atan2(tip[1] - ct, tip[0] - cs); }).sort((x, y) => x - y);
  for (let i = 0; i < angs.length - 1; i++) {
    const m = (angs[i] + angs[i + 1]) / 2; const dir = [Math.cos(m), Math.sin(m)];
    const a0 = [cs + dir[0] * 300, ct + dir[1] * 300], a1 = [cs + dir[0] * 720, ct + dir[1] * 720];
    const clipped = [a0, a1].map(p => [Math.min(p[0], -205), Math.min(p[1], -175)]);
    poly(clipped, 0.18, yellow);
  }
  // service road ring around the terminal (two white dashed lines)
  for (const r of [262, 274]) { const pts = []; for (let k = 0; k <= 96; k++) { const q = -165 + 310 * k / 96; const qq = q * Math.PI / 180; pts.push([cs + Math.cos(qq) * r, ct + Math.sin(qq) * r]); } poly(pts, 0.15, white, 3, 3); }
  // pier-side vehicle lanes under the jet bridges
  PIERS.forEach(p => { const f = pierFrame(p); for (const sg of [-1, 1]) for (const off of [p.w / 2 + 7, p.w / 2 + 13]) {
    const s0 = [p.root[0] + f.d[0] * 30 + f.n[0] * sg * off, p.root[1] + f.d[1] * 30 + f.n[1] * sg * off];
    const s1 = [p.root[0] + f.d[0] * (p.len - (p.end === 'rotunda' ? p.R * 1.8 : p.w)) + f.n[0] * sg * off, p.root[1] + f.d[1] * (p.len - (p.end === 'rotunda' ? p.R * 1.8 : p.w)) + f.n[1] * sg * off];
    poly([s0, s1], 0.15, white, 3, 3); } });
  return { pos: new Float32Array(pos), col: new Float32Array(col), idx: new Uint32Array(idx) };
}

// The five live G3000 PRIME pages of the parked PC-12 PRO, drawn in each display's own millimetres (avionics.js sets the
// transform from GLB meta 'displays' / the atlas rectangles): the two PDUs in split mode (the PFD on the outboard 60 %,
// a multi-function pane inboard -- SafeTaxi left, the active flight plan right), the MFD (the engine / systems strip on
// its left 19 %, the map, the vertical situation display, the quick-access bar) and the two SDUs (the radio strip, the
// active flight plan / the take-off data form, the tab bar).  Layout fractions from the photos of s/n 3001 parked at
// EDNY (P1046408-10) and the AOPA / Garmin studio shots (out/tmp/avx/research_pages.md); colours Garmin's; numerals
// only (avx_font.js), every word an abstract stroke (legend()).
//
// Each page is drawn from a VIEW: the quantised values it shows (view*() below), so the page's key (avionics.js: a
// redraw only when the key changes) is exactly what is drawn.  Static layers (the SVT, the map relief, the gauge faces'
// cache) are drawn once per page canvas.

import { drawNum, legend, numWidth } from './avx_font.js';
import { bands } from './engine.js';

export const C = {
  bg: '#040507', white: '#eceef0', grey: '#969ca6', dim: '#5d636e', green: '#3fe04a', cyan: '#25d8f0',
  magenta: '#e83ce6', amber: '#ffb000', red: '#ff2a2a', yellow: '#f2e33a', box: '#22252c', boxEdge: '#3c424e',
  key: '#2c3039', keyEdge: '#4a505c', keyHi: '#353a45', blue: '#2b78e4', navy: '#0c1a33', tape: 'rgba(16,30,66,0.62)',
  tapeEdge: 'rgba(200,210,230,0.35)', black: '#000000', brown: '#8a4b2c',
};
const COLOR = { green: C.green, amber: C.amber, red: C.red, white: C.white, grey: '#7d838d', cyan: C.cyan };
const D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const q = (x, s) => Math.round(x / s) * s;
export const PFD_W = 183;                  // the PFD pane (mm) on a 305 mm PDU (the outboard 60 %)

// ------------------------------------------------------------------ drawing helpers (mm units)
function rr(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r); ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h); ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r); ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}
function box(ctx, x, y, w, h, { fill = C.box, stroke = C.boxEdge, r = 1.2, lw = 0.3 } = {}) {
  rr(ctx, x, y, w, h, r);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
}
function line(ctx, pts, color, lw = 0.3, dash = null) {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.strokeStyle = color; ctx.lineWidth = lw;
  if (dash) ctx.setLineDash(dash);
  ctx.stroke();
  if (dash) ctx.setLineDash([]);
}
function poly(ctx, pts, fill, stroke = null, lw = 0.3) {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
}
// numerals with the page's text log (tests compare it with the state)
function N(P, id, str, x, y, size, color = C.white, o = {}) {
  return drawNum(P.ctx, str, x, y, size, { color, log: P.log, id, weight: o.weight || (size >= 3.4 ? 0.14 : 0.13), ...o });
}
function L(P, id, x, y, size, color = C.white, o = {}) { return legend(P.ctx, id, x, y, size, color, { log: P.log, ...o }); }
const sgn = (v) => (v > 0 ? '+' : v < 0 ? '-' : '');
const fmtInt = (v) => String(Math.round(v));

// ------------------------------------------------------------------ views (the quantised values each page shows)
function stateCol(caution, warning) { return warning ? 'red' : caution ? 'amber' : 'green'; }
const deg = (v) => `${String(((Math.round(v) % 360) + 360) % 360 || 360).padStart(3, '0')}°`;

export function viewMfd(S) {
  const e = S.eng, run = e.phase === 'run' || e.phase === 'start';
  const cw = (k) => (run ? stateCol(e.caution[k], e.warning[k]) : 'green');
  const g = S.gear;
  const gearState = g.pos <= 0 && g.target <= 0 ? 'down' : g.pos >= 1 && g.door <= 0 ? 'up' : 'transit';
  const fl = q(S.flaps, 0.1), flMoving = Math.abs(S.flaps - S.flapsT) > 0.01;
  const flapCol = flMoving ? 'white' : Math.abs(S.flaps - 15) < 0.05 ? 'green' : 'amber';
  const trimOk = (v, r) => Math.abs(v) <= 0.25 * r;
  const fuelQ = e.fuel.qty, ff = Math.round(e.ff);
  const endMin = ff >= 1 ? Math.floor(fuelQ / ff * 60) : -1;
  const pcl = S.pitch < -2 && S.rpmT > 0 ? 'rev' : S.toMode ? 'to' : S.rpmT <= 1000 ? 'idl' : null;
  return {
    pcl,
    tq: e.tq.toFixed(1), tqA: q(e.tq, 0.07), tqC: cw('tq'), bug: S.rpmT >= 1700 && run ? e.rating.toFixed(1) : null,
    itt: fmtInt(e.itt), ittA: q(clamp(e.itt, 380, 1010), 1.5), ittC: cw('itt'), start: e.phase === 'start',
    ng: e.ng.toFixed(1), ngA: q(e.ng, 0.15), ngC: cw('ng'), mark13: !!e.starter,
    oilT: fmtInt(e.oilT), oilTC: cw('oilT'), oilTp: q(clamp(e.oilT, -2, 122), 0.3),
    oilP: fmtInt(e.oilP), oilPC: cw('oilP'), oilPp: q(clamp(e.oilP, 48, 152), 0.3),
    np: fmtInt(e.np), npC: run ? (e.warning.np ? 'red' : e.caution.np ? 'amber' : 'normal') : 'normal',
    t1: fmtInt(e.t1), pumps: e.pumps, starter: !!e.starter, ign: !!e.ign,
    qty: fmtInt(fuelQ), ff: String(ff), end: endMin >= 0 ? `${Math.floor(endMin / 60)}:${String(endMin % 60).padStart(2, '0')}` : null,
    tankF: q(clamp(e.fuel.gal / 402, 0, 1), 0.004), low: e.fuel.low,
    gear: gearState, gearPos: q(g.pos, 0.02), flaps: fl, flapC: flapCol,
    stab: q(S.trims.stab, 0.1), ail: q(S.trims.ail, 0.1), rud: q(S.trims.rud, 0.1),
    stabOk: S.trims.stab <= 0.5 && S.trims.stab >= -2.5, ailOk: trimOk(S.trims.ail, 10), rudOk: trimOk(S.trims.rud, 12),
    bat: e.bat.map((b) => [b.v.toFixed(1), String(Math.round(b.a) === 0 ? 0 : Math.round(b.a)), q(clamp((b.v - 20) / 12, 0, 1), 0.01),
      b.v < 22 || b.v > 30.3 ? 'amber' : 'green']),
    elev: fmtInt(S.env.elev), cabAlt: fmtInt(q(S.adc.pa, 10)),
    fod: fuelQ - 469 >= 0 ? fmtInt(q(fuelQ - 469, 1)) : null,
    windDir: Math.round(S.env.windDir) % 360, windKt: Math.round(S.env.windKt), hdg: S.hdg,
    clock: S.clock,
  };
}

export function viewPfd(S, side) {
  const e = S.eng, a = S.adc, v = S.env;
  const ias = a.ias >= 20 ? q(a.ias, 0.25) : null;               // below the tape's 20 kt floor: dashes
  const cas = [];
  if (S.doors.airstair > 0.01 || S.doors.cargo > 0.01) cas.push(['red', 'door']);
  if (e.phase === 'run' && (Math.abs(S.flaps - 15) > 0.05 || Math.abs(S.trims.stab + 1) > 1.5)) cas.push(['amber', 'toConfig']);
  else if (Math.abs(S.flaps - 15) > 0.05 && Math.abs(S.flaps - S.flapsT) < 0.01) cas.push(['amber', 'flapsCas']);
  if (e.fuel.low) cas.push(['amber', 'fuelLow']);
  if (e.phase === 'dry') cas.push(['white', 'dryMot']);
  else if (e.starter) cas.push(['white', 'starterCas']);
  const std = S.baroMode === 'std';
  const baro = std ? null : S.qnhUnit === 'hPa' ? String(Math.round(v.qnh)) : (v.qnh / 33.8639).toFixed(2);
  return {
    side, alt: Math.round(a.alt), baro, unit: S.qnhUnit, std, pre: String(Math.round(v.qnh)),
    sat: Math.round(a.sat), isa: Math.round(a.sat - (15 - 1.98 * a.pa / 1000)),
    ias, tas: ias != null ? Math.round(ias / Math.sqrt(S.atm.sigma)) : 0, hdg: S.hdg,
    mins: Math.round(v.elev + 200), cas, clock: S.clock,
    windDir: Math.round(v.windDir) % 360, windKt: Math.round(v.windKt),
  };
}

export function viewSdu(S, side) {
  if (side === 'L') return { side };
  const v = S.env, a = S.atm, air = a.air || { head: 0, cross: 0 };
  // the runway the take-off data form computes for: 24 (240 deg true) [E: EDNY's]
  const rel = ((v.windDir - 240) % 360 + 540) % 360 - 180;
  return {
    side, elev: fmtInt(v.elev), oat: Math.round(v.oat), unit: S.qnhUnit,
    baro: S.qnhUnit === 'hPa' ? String(Math.round(v.qnh)) : (v.qnh / 33.8639).toFixed(2),
    pa: fmtInt(q(a.pa, 10)), da: fmtInt(q(a.da, 10)), wd: Math.round(v.windDir) % 360, wk: Math.round(v.windKt),
    head: Math.round(v.windKt * Math.cos(rel * D2R)), cross: Math.round(v.windKt * Math.sin(rel * D2R)),
    fuel: fmtInt(q(S.eng.fuel.qty, 10)), rating: S.eng.rating.toFixed(1), isa: Math.round(a.isaDev), hw: air.head,
  };
}

// ================================================================== the PFD
// pane coordinates (mm): x right from the pane's left edge, y down; attitude centre (91.5, 62), pitch 3.7 mm / deg
const PX = { cx: 91.5, cy: 62, ppd: 3.7, pitch: 0.4 };

// the SVT: the apron and the hangars of the outside world (outside.js WORLD) projected conformally from the design eye
// (glTF: x starboard, y up, z aft; the nose to -Z), a Garmin-style synthetic sky and grass -- aircraft-relative, so
// drawn once
function svtLayer(P, world, W, H) {
  const ctx = P.ctx;
  const hy = PX.cy + PX.pitch * PX.ppd;
  const eye = [0, 2.05, 4.0];
  // a rectilinear (perspective) projection, 3.7 mm a degree at the centre: 51 deg of the pane's height
  const K = PX.ppd / D2R;
  const proj = (x, y, z) => {
    const f = Math.max(0.05, -(z - eye[2]));
    return [PX.cx + K * (x - eye[0]) / f, hy - K * (y - eye[1]) / f, f];
  };
  // sky
  let g = ctx.createLinearGradient(0, 0, 0, hy);
  g.addColorStop(0, '#0540c4'); g.addColorStop(0.55, '#2766d6'); g.addColorStop(0.92, '#7099d0'); g.addColorStop(1, '#a9b3b6');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, hy + 0.2);
  // the ground, pixel by pixel through the inverse projection: the terrain database's mottled olive grass (three octaves
  // of value noise in metres), the near apron in blue-grey, a distance haze
  {
    const T = ctx.getTransform(), n1 = noise2(17), n2 = noise2(23), n3 = noise2(41);
    const px0 = Math.floor(T.e), py0 = Math.floor(T.f + hy * T.d), pw = Math.ceil(W * T.a), ph = Math.ceil((H - hy) * T.d);
    const img = ctx.createImageData(pw, ph), d = img.data;
    for (let j = 0; j < ph; j++) {
      const ymm = (py0 + j + 0.5 - T.f) / T.d, dy = ymm - hy;
      const f = dy > 0.02 ? K * eye[1] / dy : 1e5, haze = clamp(f / 900, 0, 1) ** 0.7;
      for (let i = 0; i < pw; i++) {
        const xmm = (px0 + i + 0.5 - T.e) / T.a, X = (xmm - PX.cx) * f / K, Z = eye[2] - f;
        const v = 0.55 * n1(X / 9, Z / 9) + 0.3 * n2(X / 2.6, Z / 2.6) + 0.15 * n3(X / 0.8, Z / 0.8);
        let r, gg, b;
        if (Z > -26 && X > -34 && X < -1.5 - 0.12 * Z) { const t = 0.85 + 0.25 * v; r = 104 * t; gg = 116 * t; b = 134 * t; }
        else { const t = 0.72 + 0.5 * v; r = 98 * t; gg = 110 * t; b = 58 * t; }
        r += (150 - r) * haze; gg += (160 - gg) * haze; b += (150 - b) * haze;
        const o = 4 * (j * pw + i);
        d[o] = r; d[o + 1] = gg; d[o + 2] = b; d[o + 3] = 255;
      }
    }
    const tmp = document.createElement('canvas');
    tmp.width = pw; tmp.height = ph;
    tmp.getContext('2d').putImageData(img, 0, 0);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(tmp, px0, py0); ctx.restore();
  }
  // ground polygons, clipped at a near plane 1.5 m ahead of the eye
  const ground = (pts, fill) => {
    const near = 1.5, out = [];
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length];
      const fa = eye[2] - a[1], fb = eye[2] - b[1];
      if (fa >= near) out.push(a);
      if ((fa >= near) !== (fb >= near)) { const t = (near - fa) / (fb - fa); out.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]); }
    }
    if (out.length < 3) return;
    poly(ctx, out.map(([x, z]) => proj(x, 0, z)), fill);
  };
  // the taxiways (SafeTaxi blue-grey) and their centre lines
  ground([[-6, -60], [6, -60], [6, -400], [-6, -400]], 'rgba(112,124,142,0.8)');
  ground([[-260, -170], [260, -170], [260, -182], [-260, -182]], 'rgba(112,124,142,0.9)');
  for (const [x, z0, z1] of [[-3.2, -150, -6]]) {
    const pts = [];
    for (let z = z1; z >= z0; z -= 4) pts.push(proj(x, 0, z));
    line(ctx, pts, 'rgba(240,215,70,0.75)', 0.3);
  }
  for (const zz of [-170.5, -181.5]) {
    const pts = [];
    for (let x = -250; x <= 250; x += 10) pts.push(proj(x, 0, zz));
    line(ctx, pts, 'rgba(240,215,70,0.8)', 0.25);
  }
  // buildings: grey 3-D blocks, the far ones first; the faces toward the eye
  const B = [...world.hangars, ...world.annex].map((b) => ({ b, d: Math.hypot(b[0], b[1] - eye[2]) })).sort((u, v) => v.d - u.d);
  for (const { b: [cx, cz, bw, bh, bd] } of B) {
    const x0 = cx - bw / 2, x1 = cx + bw / 2, z0 = cz - bd / 2, z1 = cz + bd / 2;
    const face = (pts, fill) => poly(ctx, pts.map(([x, y, z]) => proj(x, y, z)), fill, 'rgba(60,64,72,0.55)', 0.15);
    if (x0 > eye[0]) face([[x0, 0, z0], [x0, 0, z1], [x0, bh, z1], [x0, bh, z0]], '#7d8590');
    if (x1 < eye[0]) face([[x1, 0, z0], [x1, 0, z1], [x1, bh, z1], [x1, bh, z0]], '#7d8590');
    face([[x0, 0, z1], [x1, 0, z1], [x1, bh, z1], [x0, bh, z1]], '#a2a9b2');
    // a roof-line shade band
    const top = [[x0, bh, z1], [x1, bh, z1], [x1, bh * 0.92, z1], [x0, bh * 0.92, z1]];
    poly(ctx, top.map(([x, y, z]) => proj(x, y, z)), 'rgba(70,74,82,0.35)');
  }
}

function pfdPage(P, V, world) {
  const ctx = P.ctx, W = PFD_W, H = 189.5, cx = PX.cx, cy = PX.cy, ppd = PX.ppd;
  const hy = cy + PX.pitch * ppd;
  ctx.save();
  ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
  // the cached SVT
  const sv = P.cache.svt || (P.cache.svt = P.layer(() => svtLayer(P, world, W, H), 0, 0, W, H));
  P.blit(sv, 0, 0);
  // horizon line, pitch ladder (every 2.5 deg, numerals at 5 / 10), white with a dark halo
  const halo = (pts, lw = 0.32) => { line(ctx, pts, 'rgba(0,0,0,0.55)', lw + 0.5); line(ctx, pts, C.white, lw); };
  halo([[0, hy], [W, hy]], 0.3);
  ctx.save();
  ctx.beginPath(); ctx.rect(38, 24, 107, 76); ctx.clip();
  for (let p = -20; p <= 20; p += 2.5) {
    if (p === 0) continue;
    const y = hy - p * ppd, l = p % 10 === 0 ? 11 : p % 5 === 0 ? 6.5 : 2.6;
    if (y < 26 || y > 98) continue;
    halo([[cx - l, y], [cx + l, y]], 0.32);
    if (p % 5 === 0) {
      const s = String(Math.abs(p));
      N(P, 'ladder', s, cx - l - 1.4, y + 1.25, 2.5, C.white, { align: 'right', halo: 0.5 });
      N(P, 'ladder', s, cx + l + 1.4, y + 1.25, 2.5, C.white, { align: 'left', halo: 0.5 });
    }
  }
  ctx.restore();
  // roll scale: arc r 33 with ticks 10 / 20 / 30 / 45 / 60, the zero index, the sky pointer and the slip bar
  const R = 33;
  ctx.beginPath(); ctx.arc(cx, cy, R, (-90 - 60) * D2R, (-90 + 60) * D2R);
  ctx.strokeStyle = 'rgba(0,0,0,0.5)'; ctx.lineWidth = 0.8; ctx.stroke();
  ctx.strokeStyle = C.white; ctx.lineWidth = 0.32; ctx.stroke();
  for (const a of [-60, -45, -30, -20, -10, 10, 20, 30, 45, 60]) {
    const l = Math.abs(a) === 30 || Math.abs(a) === 60 ? 3.4 : 2.0, t = (a - 90) * D2R;
    halo([[cx + R * Math.cos(t), cy + R * Math.sin(t)], [cx + (R + l) * Math.cos(t), cy + (R + l) * Math.sin(t)]], 0.4);
  }
  poly(ctx, [[cx, cy - R], [cx - 2.0, cy - R - 3.6], [cx + 2.0, cy - R - 3.6]], C.white, 'rgba(0,0,0,0.6)', 0.25);
  poly(ctx, [[cx, cy - R + 0.3], [cx - 2.1, cy - R + 3.8], [cx + 2.1, cy - R + 3.8]], C.white, 'rgba(0,0,0,0.6)', 0.25);
  poly(ctx, [[cx - 2.4, cy - R + 4.4], [cx + 2.4, cy - R + 4.4], [cx + 2.4, cy - R + 5.4], [cx - 2.4, cy - R + 5.4]], C.white, 'rgba(0,0,0,0.6)', 0.2);
  // the flight director and the aircraft symbol: single cue (pilot) / cross pointers (co-pilot), as s/n 3001's sides
  if (V.side === 'L') {
    const fd = (s) => poly(ctx, [[cx, cy + 0.6], [cx + s * 21, cy + 6.2], [cx + s * 21, cy + 7.8], [cx, cy + 2.6]], C.magenta, 'rgba(0,0,0,0.6)', 0.2);
    fd(-1); fd(1);
    const ac = (s) => poly(ctx, [[cx, cy], [cx + s * 17, cy + 6.0], [cx + s * 10, cy + 6.0]], C.yellow, '#000', 0.35);
    ac(-1); ac(1);
  } else {
    line(ctx, [[cx - 12, cy], [cx + 12, cy]], 'rgba(0,0,0,0.6)', 1.0);
    line(ctx, [[cx - 12, cy], [cx + 12, cy]], C.magenta, 0.55);
    line(ctx, [[cx, cy - 12], [cx, cy + 12]], 'rgba(0,0,0,0.6)', 1.0);
    line(ctx, [[cx, cy - 12], [cx, cy + 12]], C.magenta, 0.55);
    for (const s of [-1, 1]) poly(ctx, [[cx + s * 28, cy - 1], [cx + s * 15, cy - 1], [cx + s * 15, cy + 3], [cx + s * 17, cy + 3], [cx + s * 17, cy + 1], [cx + s * 28, cy + 1]], '#000', C.white, 0.35);
    poly(ctx, [[cx - 1.1, cy - 1.1], [cx + 1.1, cy - 1.1], [cx + 1.1, cy + 1.1], [cx - 1.1, cy + 1.1]], '#000', C.white, 0.3);
  }

  // ---- airspeed tape (x 9-31, y 25-87): parked at its 20 kt floor below it, the readout dashes
  const T = { x0: 9, x1: 31, y0: 25, y1: 87, mmPerKt: 0.713 };
  const spd = V.ias != null ? V.ias : 30;                          // parked: the tape stops with ~30 kt at the pointer
  box(ctx, T.x0, T.y0, T.x1 - T.x0, T.y1 - T.y0, { fill: C.tape, stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  ctx.save(); ctx.beginPath(); ctx.rect(T.x0, T.y0, T.x1 - T.x0, T.y1 - T.y0); ctx.clip();
  for (let k = 20; k <= 260; k += 5) {
    const y = cy - (k - spd) * T.mmPerKt;
    if (y < T.y0 - 3 || y > T.y1 + 3) continue;
    line(ctx, [[T.x1 - (k % 10 ? 1.6 : 2.6), y], [T.x1, y]], C.white, 0.3);
    if (k % 10 === 0 && k >= 20) N(P, 'spdTape', String(k), T.x1 - 3.4, y + 1.6, 3.2, C.white, { align: 'right' });
  }
  ctx.restore();
  // the selected speed over the tape, the V-speeds at its foot (cyan; their letter tags are legends)
  box(ctx, T.x0, T.y0 - 6.5, T.x1 - T.x0, 5.8, { fill: 'rgba(10,12,18,0.85)', stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  poly(ctx, [[T.x0 + 1.6, T.y0 - 4.8], [T.x0 + 3.6, T.y0 - 3.6], [T.x0 + 1.6, T.y0 - 2.4]], C.cyan);
  N(P, 'selSpd', '130', T.x1 - 1.6, T.y0 - 1.9, 3.4, C.white, { align: 'right' });
  [['130', 'vy'], ['120', 'vx'], ['82', 'vr']].forEach(([s, id], i) => {
    const y = T.y1 - 9.4 + i * 4.0;
    N(P, 'vspd', s, T.x1 - 6.4, y, 2.9, C.cyan, { align: 'right' });
    line(ctx, [[T.x1 - 5.6, y - 1.4], [T.x1 - 3.8, y - 1.4]], C.cyan, 0.35);
    L(P, id, T.x1 - 3.4, y, 2.6, C.cyan, { cw: 0.7 });
  });
  // the pointer box
  poly(ctx, [[5.5, cy - 4.4], [T.x1 - 3.0, cy - 4.4], [T.x1 - 3.0, cy - 1.6], [T.x1 - 0.6, cy], [T.x1 - 3.0, cy + 1.6], [T.x1 - 3.0, cy + 4.4], [5.5, cy + 4.4]],
    '#000', C.white, 0.35);
  if (V.ias == null) N(P, 'ias', '- - -', 17.3, cy + 2.2, 4.4, C.white, { align: 'center', spacing: 0.5 });
  else N(P, 'ias', String(Math.round(V.ias)), T.x1 - 3.8, cy + 2.4, 4.8, C.white, { align: 'right' });

  // ---- altitude tape (x 137-165): 100 ft per 5.7 mm, the drum box, the ground (radar altimeter) hatching
  const A = { x0: 137, x1: 164, y0: 25, y1: 87, mmPerFt: 0.057 };
  box(ctx, A.x0, A.y0, A.x1 - A.x0, A.y1 - A.y0, { fill: C.tape, stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  ctx.save(); ctx.beginPath(); ctx.rect(A.x0, A.y0, A.x1 - A.x0, A.y1 - A.y0); ctx.clip();
  // the ground below the current altitude (RA 0 parked): brown / white diagonal hatching
  ctx.save(); ctx.beginPath(); ctx.rect(A.x0 + 0.3, cy, A.x1 - A.x0 - 0.6, A.y1 - cy); ctx.clip();
  ctx.fillStyle = '#6b3a24'; ctx.fillRect(A.x0, cy, A.x1 - A.x0, A.y1 - cy);
  for (let k = -40; k < 60; k += 2.6) line(ctx, [[A.x0 + k, A.y1 + 2], [A.x0 + k + 30, cy - 28]], 'rgba(235,225,215,0.75)', 0.55);
  ctx.restore();
  const a0 = V.alt;
  for (let k = Math.floor((a0 - 700) / 20) * 20; k <= a0 + 700; k += 20) {
    const y = cy - (k - a0) * A.mmPerFt;
    if (y < A.y0 - 3 || y > A.y1 + 3) continue;
    line(ctx, [[A.x0, y], [A.x0 + (k % 100 ? 1.2 : 2.4), y]], C.white, k % 100 ? 0.22 : 0.3);
    if (k % 100 === 0 && Math.abs(y - cy) > 5.5) N(P, 'altTape', String(k), A.x1 - 1.0, y + 1.3, 2.7, C.white, { align: 'right' });
  }
  ctx.restore();
  // selected altitude (cyan) and the boxed transition / VNAV altitude
  box(ctx, A.x0, A.y0 - 6.5, A.x1 - A.x0, 5.8, { fill: 'rgba(10,12,18,0.85)', stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  line(ctx, [[A.x0 + 1.4, A.y0 - 5.6], [A.x0 + 1.4, A.y0 - 1.6]], C.cyan, 0.7);
  N(P, 'selAlt', '5000', A.x1 - 1.4, A.y0 - 1.9, 3.6, C.cyan, { align: 'right' });
  box(ctx, A.x1 + 2.0, A.y0 - 6.2, 13.5, 5.2, { fill: 'rgba(0,0,0,0.6)', stroke: C.white, r: 0.4, lw: 0.25 });
  N(P, 'vnavAlt', '5500', A.x1 + 8.75, A.y0 - 2.2, 2.8, C.white, { align: 'center' });
  // the drum: thousands + hundreds large, the last two digits on a 20 ft drum
  // (the box ends on the tape's right edge: the VSI pointer beside it never covers the drum)
  const dx = A.x1 - 9.2, dr = A.x1 + 0.4;
  poly(ctx, [[A.x0 - 3.2, cy], [A.x0 - 0.8, cy - 2.2], [A.x0 - 0.8, cy - 4.6], [dx, cy - 4.6], [dx, cy - 7.4], [dr, cy - 7.4],
    [dr, cy + 7.4], [dx, cy + 7.4], [dx, cy + 4.6], [A.x0 - 0.8, cy + 4.6], [A.x0 - 0.8, cy + 2.2]], '#000', C.white, 0.35);
  const neg = a0 < 0, aa = Math.abs(a0), hi = Math.floor(aa / 100), lo20 = aa - hi * 100;
  N(P, 'altDrumHi', `${neg ? '-' : ''}${hi}`, dx - 0.6, cy + 2.6, 5.4, C.white, { align: 'right' });
  ctx.save(); ctx.beginPath(); ctx.rect(dx + 0.2, cy - 7.2, dr - dx - 0.4, 14.4); ctx.clip();
  const base = Math.floor(lo20 / 20) * 20, frac = (lo20 - base) / 20;
  for (let k = -2; k <= 2; k++) {
    const val = ((base + 20 * k) % 100 + 100) % 100, y = cy + 1.6 + (frac - k) * 5.0;
    N(P, k === 0 ? 'altDrumLo' : 'altDrumRoll', String(val).padStart(2, '0'), dr - 0.5, y, 3.4, C.white, { align: 'right' });
  }
  ctx.restore();
  // VSI (x 166-176): scale 1 / 2 / 4 / 6 (x 1,000 fpm), the pointer at 0, no digits on the ground
  box(ctx, 165.5, 30, 9.5, 52, { fill: C.tape, stroke: null, r: 0.8 });
  for (const [v, y] of [[6, 31.5], [4, 38], [2, 46.5], [1, 54], [-1, 70], [-2, 77.5], [-4, 86], [-6, 92.5]]) {
    const yy = v > 0 ? cy - (cy - y) : y - 8;
    line(ctx, [[165.5, yy], [167.5, yy]], C.white, 0.3);
    if (Math.abs(v) >= 2) N(P, 'vsi', String(Math.abs(v)), 171.5, yy + 1.2, 2.4, C.white, { align: 'center' });
  }
  poly(ctx, [[A.x1 + 0.9, cy], [168.4, cy - 2.2], [175.5, cy - 2.2], [175.5, cy + 2.2], [168.4, cy + 2.2]], '#000', C.white, 0.3);
  // baro box under the tape: the set QNH (cyan) and its unit, or STD with the pre-selected value
  box(ctx, A.x0, 89.5, A.x1 - A.x0 + 3, 7.2, { fill: 'rgba(0,0,0,0.75)', stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  if (V.std) {
    L(P, 'pre', A.x0 + 1.2, 92.6, 1.8, C.white);
    N(P, 'baroPre', V.pre, A.x0 + 13.5, 92.8, 2.3, C.white, { align: 'right' });
    L(P, 'hPa', A.x0 + 14.2, 92.8, 1.8, C.white);
    L(P, 'std', A.x0 + 15, 96.2, 3.2, C.white, { align: 'center', cw: 0.7 });
  } else {
    N(P, 'baro', V.baro, A.x0 + 19, 95.2, 3.9, C.cyan, { align: 'right' });
    L(P, V.unit === 'hPa' ? 'hPa' : 'inHg', A.x0 + 19.8, 95.2, 2.2, C.cyan);
  }
  // radar altitude and minimums (cyan: field elevation + 200 ft)
  box(ctx, 120.5, 87.5, 14, 5.6, { fill: 'rgba(0,0,0,0.55)', stroke: null, r: 0.5 });
  L(P, 'ra', 121.6, 91.7, 2.2, C.white);
  N(P, 'ra', '0', 133.4, 92.2, 3.6, C.white, { align: 'right' });
  box(ctx, 112, 94, 23, 6.4, { fill: 'rgba(0,0,0,0.55)', stroke: null, r: 0.5 });
  L(P, 'baroMin', 113, 98.8, 1.6, C.white, { cw: 0.45 });
  N(P, 'mins', String(V.mins), 134, 99.0, 3.4, C.cyan, { align: 'right' });

  // ---- heading: the compass arc (heading up), the heading box, the HDG bug and DTK readouts
  const hc = { x: cx, y: 153, r: 40 };
  ctx.save(); ctx.beginPath(); ctx.rect(0, 108, W, 176 - 108); ctx.clip();
  ctx.beginPath(); ctx.arc(hc.x, hc.y, hc.r + 0.5, 0, 2 * Math.PI); ctx.fillStyle = 'rgba(12,18,36,0.84)'; ctx.fill();
  ctx.strokeStyle = 'rgba(200,210,230,0.5)'; ctx.lineWidth = 0.25; ctx.stroke();
  for (let d = 0; d < 360; d += 5) {
    const rel = ((d - V.hdg + 540) % 360) - 180;
    if (Math.abs(rel) > 70) continue;
    const t = (rel - 90) * D2R, l = d % 10 ? 1.6 : 2.8;
    line(ctx, [[hc.x + hc.r * Math.cos(t), hc.y + hc.r * Math.sin(t)], [hc.x + (hc.r - l) * Math.cos(t), hc.y + (hc.r - l) * Math.sin(t)]], C.white, 0.3);
    if (d % 30 === 0) {
      const rr2 = hc.r - 6.0;
      ctx.save(); ctx.translate(hc.x + rr2 * Math.cos(t), hc.y + rr2 * Math.sin(t)); ctx.rotate(rel * D2R);
      N(P, 'rose', String(d / 10), 0, 1.6, 3.4, C.white, { align: 'center' });
      ctx.restore();
    }
  }
  // the heading bug (cyan) and the FMS course (magenta)
  for (const [d, col] of [[250, C.cyan], [236, C.magenta]]) {
    const rel = ((d - V.hdg + 540) % 360) - 180;
    if (Math.abs(rel) > 70) continue;
    const t = (rel - 90) * D2R, ux = Math.cos(t), uy = Math.sin(t), px = -uy, py = ux;
    if (col === C.cyan) poly(ctx, [[hc.x + hc.r * ux - 1.6 * px, hc.y + hc.r * uy - 1.6 * py], [hc.x + (hc.r + 1.8) * ux - 1.6 * px, hc.y + (hc.r + 1.8) * uy - 1.6 * py],
      [hc.x + (hc.r + 1.8) * ux + 1.6 * px, hc.y + (hc.r + 1.8) * uy + 1.6 * py], [hc.x + hc.r * ux + 1.6 * px, hc.y + hc.r * uy + 1.6 * py], [hc.x + (hc.r + 0.8) * ux, hc.y + (hc.r + 0.8) * uy]], C.cyan);
    else {
      line(ctx, [[hc.x + 6 * ux, hc.y + 6 * uy], [hc.x + (hc.r - 6) * ux, hc.y + (hc.r - 6) * uy]], C.magenta, 0.6);
      poly(ctx, [[hc.x + (hc.r - 3.2) * ux, hc.y + (hc.r - 3.2) * uy], [hc.x + (hc.r - 7) * ux + 1.8 * px, hc.y + (hc.r - 7) * uy + 1.8 * py], [hc.x + (hc.r - 7) * ux - 1.8 * px, hc.y + (hc.r - 7) * uy - 1.8 * py]], C.magenta);
    }
  }
  // the ownship at the rose centre
  poly(ctx, [[hc.x, hc.y - 4], [hc.x + 3.2, hc.y + 2.6], [hc.x, hc.y + 1.2], [hc.x - 3.2, hc.y + 2.6]], C.white, '#000', 0.25);
  ctx.restore();
  poly(ctx, [[cx - 7.4, 104.4], [cx + 7.4, 104.4], [cx + 7.4, 111.2], [cx + 1.2, 111.2], [cx, 113.0], [cx - 1.2, 111.2], [cx - 7.4, 111.2]], '#000', C.white, 0.3);
  N(P, 'hdg', deg(V.hdg), cx, 110.0, 4.2, C.white, { align: 'center' });
  box(ctx, 50, 105, 15, 8.2, { fill: 'rgba(12,16,28,0.8)', stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  L(P, 'hdg', 57.5, 107.8, 1.6, C.white, { align: 'center' });
  N(P, 'hdgBug', deg(250), 57.5, 112.0, 2.9, C.cyan, { align: 'center' });
  box(ctx, 118, 105, 15, 8.2, { fill: 'rgba(12,16,28,0.8)', stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  L(P, 'dtk', 125.5, 107.8, 1.6, C.white, { align: 'center' });
  N(P, 'dtk', deg(236), 125.5, 112.0, 2.9, C.magenta, { align: 'center' });

  // ---- nav-source boxes (lower left), FMS button, RNP
  box(ctx, 0.6, 151.5, 37, 23, { fill: 'rgba(8,10,16,0.8)', stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  for (const [i, id] of [[0, 'loc1'], [1, 'loc2']]) {
    const y = 157.5 + i * 10.5;
    L(P, id, 2, y, 2.0, C.green);
    N(P, 'navFreq', '109.10', 22, y, 2.9, C.white);
    L(P, 'dme', 2, y + 4.2, 1.7, C.white);
    N(P, 'dme', i ? '112.60' : '- - -', 22, y + 4.2, 2.4, C.white);
  }
  box(ctx, 40.5, 166.5, 13, 7, { fill: 'rgba(30,36,50,0.85)', stroke: C.tapeEdge, r: 0.8, lw: 0.25 });
  L(P, 'fms', 47, 171.2, 2.4, C.white, { align: 'center' });
  box(ctx, 119, 166.5, 13, 8, { fill: 'rgba(0,0,0,0.55)', stroke: null, r: 0.6 });
  L(P, 'rnp', 120, 169.6, 1.6, C.white);
  N(P, 'rnp', '1.00', 131, 173.6, 2.5, C.white, { align: 'right' });

  // ---- CAS window (lower right): warnings red, cautions amber, advisories white; the counters
  box(ctx, 134.5, 150.5, 47.5, 25, { fill: 'rgba(6,8,12,0.88)', stroke: C.tapeEdge, r: 0.6, lw: 0.2 });
  V.cas.slice(0, 4).forEach(([lvl, id], i) => {
    const y = 155.5 + i * 4.4;
    if (lvl === 'red') { ctx.fillStyle = 'rgba(255,42,42,0.0)'; }
    L(P, id, 136, y, 2.6, lvl === 'red' ? C.red : lvl === 'amber' ? C.amber : C.white, { cw: 0.42, alpha: 1 });
  });
  line(ctx, [[134.5, 170.4], [182, 170.4]], C.tapeEdge, 0.2);
  poly(ctx, [[136, 171.6], [139, 173.1], [136, 174.6]], C.white);
  L(P, 'cas', 141, 174.6, 2.2, V.cas.some((c) => c[0] === 'amber') ? C.amber : C.white);
  N(P, 'casCount', String(V.cas.length), 168, 174.6, 2.4, C.white, { align: 'right' });
  N(P, 'casCount', '0', 178, 174.6, 2.4, C.white, { align: 'right' });

  // ---- top: COM1 box, FMA bar, menu button
  box(ctx, 0.6, 0.6, 37, 12.4, { fill: 'rgba(14,30,70,0.85)', stroke: 'rgba(120,150,200,0.5)', r: 0.6, lw: 0.2 });
  L(P, 'com1', 1.8, 5.4, 1.8, C.white);
  N(P, 'com1', '123.450', 12.5, 5.6, 3.2, C.green);
  L(P, 'fltId', 1.8, 11.1, 1.6, C.white);
  N(P, 'fltId', '- - - -', 12.5, 11.1, 2.4, C.white, { spacing: 0.4 });
  box(ctx, 42, 0, 98, 11, { fill: 'rgba(14,30,70,0.85)', stroke: 'rgba(120,150,200,0.5)', r: 0.4, lw: 0.2 });
  line(ctx, [[74, 0.6], [74, 10.4]], 'rgba(150,170,210,0.6)', 0.2);
  line(ctx, [[108, 0.6], [108, 10.4]], 'rgba(150,170,210,0.6)', 0.2);
  L(P, 'rol', 58, 5.4, 2.6, C.green, { align: 'center' });
  const ar = V.side === 'L' ? 1 : -1;                              // the arrow points at the coupled side's FD
  line(ctx, [[91 - 8 * ar, 6.2], [91 + 8 * ar, 6.2]], C.green, 0.45);
  poly(ctx, [[91 - 8 * ar - ar * 2.2, 6.2], [91 - 8 * ar, 4.8], [91 - 8 * ar, 7.6]], C.green);
  L(P, 'pit', 124, 5.0, 2.6, C.green, { align: 'center' });
  L(P, 'alts', 124, 9.4, 2.2, C.white, { align: 'center' });
  box(ctx, 167, 1.2, 13, 9.6, { fill: 'rgba(20,22,28,0.85)', stroke: C.tapeEdge, r: 1.2, lw: 0.25 });
  for (const y of [3.9, 6.0, 8.1]) line(ctx, [[170, y], [177, y]], C.white, 0.6);

  // ---- bottom data bar: GS / TAS, SAT / ISA, the active leg, timer / UTC
  ctx.fillStyle = '#05070b'; ctx.fillRect(0, 176.5, W, 13);
  line(ctx, [[0, 176.5], [W, 176.5]], 'rgba(150,160,180,0.45)', 0.2);
  const r1 = 181.6, r2 = 187.8;
  L(P, 'gs', 2, r1, 1.8, C.white); N(P, 'gs', '0', 13, r1, 3.0, C.white, { align: 'right' }); L(P, 'kt', 13.6, r1, 1.8, C.white);
  L(P, 'tas', 2, r2, 1.8, C.white); N(P, 'tas', String(V.tas), 13, r2, 3.0, C.white, { align: 'right' }); L(P, 'kt', 13.6, r2, 1.8, C.white);
  line(ctx, [[19.5, 178], [19.5, 188.8]], 'rgba(150,160,180,0.4)', 0.2);
  L(P, 'sat', 21, r1, 1.8, C.white);
  N(P, 'sat', `${V.sat}°`, 35.5, r1, 3.0, C.white, { align: 'right' }); L(P, 'C', 36, r1, 1.8, C.white, { cw: 0.7 });
  L(P, 'isa', 21, r2, 1.8, C.white);
  N(P, 'isa', `${sgn(V.isa)}${Math.abs(V.isa)}°`, 35.5, r2, 3.0, C.white, { align: 'right' }); L(P, 'C', 36, r2, 1.8, C.white, { cw: 0.7 });
  L(P, 'crs', 68, r1, 1.8, C.white);
  N(P, 'crs', '236°', 81, r1, 3.0, C.white, { align: 'right' });
  poly(ctx, [[83, r1 - 1.0], [86.5, r1 - 1.0], [86.5, r1 - 2.0], [88.3, r1 - 0.5], [86.5, r1 + 1.0], [86.5, r1], [83, r1]], C.green);
  L(P, 'wpt', 89.5, r1 + 0.2, 3.0, C.green, { cw: 0.55 });
  L(P, 'dis', 62, r2, 1.8, C.white); N(P, 'dis', '3.4', 79, r2, 2.8, C.white, { align: 'right' }); L(P, 'nm', 79.6, r2, 1.6, C.white);
  L(P, 'ete', 92, r2, 1.8, C.white); N(P, 'ete', '- -:- -', 112, r2, 2.8, C.white, { align: 'right', spacing: 0.5 });
  L(P, 'tmr', 150, r1, 1.6, C.white); N(P, 'tmr', '- -:- -:- -', 181, r1, 2.6, C.cyan, { align: 'right', spacing: 0.4 });
  L(P, 'utc', 150, r2, 1.6, C.white); N(P, 'utc', V.clock || '- -:- -', 181, r2, 2.9, C.white, { align: 'right', spacing: V.clock ? 1 : 0.4 });
  ctx.restore();
}

// ---- the PDUs' inboard panes (122 x 189.5 mm)
// SafeTaxi (pfd_L): a heading-up airport map at ~600 m across: the apron, the taxi line and lead-in, the hangar
// footprints and the runway, the ownship, a wind barb at the field
function safeTaxi(P, V, world, x0) {
  const ctx = P.ctx, W = 122, H = 189.5;
  ctx.save(); ctx.translate(x0, 0); ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
  const st = P.cache.safeTaxi || (P.cache.safeTaxi = P.layer(() => {
    const ctx = P.ctx;
    ctx.fillStyle = '#101317'; ctx.fillRect(0, 0, W, H);
    // the map: heading up (the nose, -Z, up); 1 mm = 4 m; the ownship at (61, 128)
    const S = 1 / 4, ox = 61, oz = 128, m = (x, z) => [ox + x * S, oz + z * S];
    ctx.save(); ctx.beginPath(); ctx.rect(0, 11, W, 160); ctx.clip();
    // the airport's ground: a dark, faintly mottled grass tone (SafeTaxi's subdued topo), smooth at every scale
    {
      const gw = 24, gh = 32, gc = document.createElement('canvas'); gc.width = gw; gc.height = gh;
      const gx = gc.getContext('2d'), im = gx.createImageData(gw, gh), nz = noise2(17);
      for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) {
        const q = 0.6 * nz(i * 0.35, j * 0.35) + 0.4 * nz(i * 0.9 + 5, j * 0.9), k = 4 * (j * gw + i);
        im.data[k] = 44 + 16 * q; im.data[k + 1] = 50 + 16 * q; im.data[k + 2] = 38 + 10 * q; im.data[k + 3] = 255;
      }
      gx.putImageData(im, 0, 0);
      ctx.imageSmoothingEnabled = true; ctx.drawImage(gc, 0, 11, W, 160);
    }
    const ap = world.apron, A = (pts, fill, stroke) => poly(ctx, pts.map(([x, z]) => m(x, z)), fill, stroke, 0.3);
    A([[ap[0], ap[1]], [ap[0] + ap[2], ap[1]], [ap[0] + ap[2], ap[1] + ap[3]], [ap[0], ap[1] + ap[3]]], '#4f5359', '#a9aeb5');
    A([[-6, -160], [6, -160], [6, -400], [-6, -400]], '#585d64');
    A([[-260, -170], [260, -170], [260, -182], [-260, -182]], '#585d64');
    // the runway 06 / 24 (true 060 / 240 [E: EDNY]) beyond the parallel taxiway; heading 180: north = +Z, east = -X
    const rh = 240 * D2R, ux = -Math.sin(rh), uz = Math.cos(rh), px = -uz, pz = ux, c0 = [60, -300], hl = 700, hw = 22;
    A([[c0[0] - ux * hl - px * hw, c0[1] - uz * hl - pz * hw], [c0[0] + ux * hl - px * hw, c0[1] + uz * hl - pz * hw],
      [c0[0] + ux * hl + px * hw, c0[1] + uz * hl + pz * hw], [c0[0] - ux * hl + px * hw, c0[1] - uz * hl + pz * hw]], '#3a3e44', '#d8dade');
    for (let s = -hl + 40; s < hl - 40; s += 60) line(ctx, [m(c0[0] + ux * s, c0[1] + uz * s), m(c0[0] + ux * (s + 30), c0[1] + uz * (s + 30))], '#eef0f2', 0.35);
    for (const [s, n] of [[-hl + 60, '24'], [hl - 60, '6']]) {
      const [x, y] = m(c0[0] + ux * s, c0[1] + uz * s);
      box(ctx, x - 4, y - 2.6, 8, 4.4, { fill: '#000', stroke: C.white, r: 0.4, lw: 0.2 });
      N(P, 'rwy', n, x, y + 1.2, 2.6, C.white, { align: 'center' });
    }
    // taxi lines (yellow), the lead-in arc
    line(ctx, [m(0, -400), m(0, -3)], C.yellow, 0.35);
    line(ctx, [m(-250, -176), m(250, -176)], C.yellow, 0.3);
    // buildings: dark footprints with a light edge (3-D SafeTaxi blocks seen from above)
    for (const [cx, cz, bw, , bd] of [...world.hangars, ...world.annex]) {
      A([[cx - bw / 2, cz - bd / 2], [cx + bw / 2, cz - bd / 2], [cx + bw / 2, cz + bd / 2], [cx - bw / 2, cz + bd / 2]], '#3c4a63', '#9fb2d4');
    }
    ctx.restore();
    // the title row and the bottom bar
    ctx.fillStyle = '#0a0c10'; ctx.fillRect(0, 0, W, 11);
    L(P, 'map', 3, 7.2, 2.6, C.white);
    for (const [x, k] of [[96, 0], [108, 1]]) {
      box(ctx, x, 1.6, 9, 7.6, { fill: C.key, stroke: C.keyEdge, r: 1.0, lw: 0.2 });
      if (k) for (const y of [3.8, 5.4, 7.0]) line(ctx, [[x + 2.2, y], [x + 6.8, y]], C.white, 0.45);
      else { line(ctx, [[x + 2.4, 7], [x + 6.6, 2.8]], C.white, 0.45); line(ctx, [[x + 4.4, 2.8], [x + 6.6, 2.8], [x + 6.6, 5]], C.white, 0.45); }
    }
    box(ctx, 3, 14, 15, 13, { fill: 'rgba(30,34,42,0.88)', stroke: C.keyEdge, r: 1.2, lw: 0.25 });
    poly(ctx, [[10.5, 16.2], [14, 22.5], [10.5, 20.8], [7, 22.5]], C.white);
    L(P, 'trkUp', 10.5, 25.6, 1.5, C.white, { align: 'center', cw: 0.42 });
    box(ctx, 3, 152, 30, 13, { fill: 'rgba(14,16,22,0.9)', stroke: C.keyEdge, r: 1.2, lw: 0.25 });
    L(P, 'status', 5, 156.4, 1.8, C.white);
    L(P, 'safeTaxi', 8, 162, 1.8, C.white);
    ctx.fillStyle = '#07080b'; ctx.fillRect(0, 171, W, 18.5);
    iconBar(ctx, [8, 26, 44, 62], 180.2, 0, 'pdu');
    // the scale
    line(ctx, [[86, 166], [86, 168], [111, 168], [111, 166]], C.white, 0.35);
    N(P, 'scale', '100', 101, 165.4, 2.4, C.white, { align: 'right' });
    L(P, 'M', 102, 165.4, 1.6, C.white, { cw: 0.7 });
  }, 0, 0, W, H));
  P.blit(st, x0, 0);
  // the ownship (heading up) and the wind barb at the field (direction / speed numerals: the Environment knob)
  poly(ctx, [[61, 124.4], [64.2, 132.2], [61, 130.4], [57.8, 132.2]], C.white, '#000', 0.3);
  windBarb(P, 104, 40, V.windDir, V.windKt, V.hdg, true);
  ctx.restore();
}

// the active flight plan (pfd_R's inboard pane / sdu_L's body): dark keys with identifier legends, constraints
const FPL = [
  // (labels on: a plausible departure from EDNY runway 24 -- invented fixes, no procedure names)
  { id: 'origin', sub: 'field', alt: null, opt: true },
  { id: 'depHdr', sub: 'nyRw', alt: null, cyan: true },
  { id: 'nyRw', sub: null, alt: '1367', spd: null },
  { id: 'wpt', sub: null, alt: null, active: true, dist: '3.4' },
  { id: 'fix1', sub: null, alt: null, spd: '210', dist: '8.1' },
  { id: 'fix2', sub: null, alt: '5500', climb: true, dist: '15.3' },
  { id: 'fix3', sub: null, alt: '120', fl: true, climb: true, dist: '15.8' },
  { id: 'destHdr', sub: 'destF', alt: null, cyan: true, dist: '380' },
];
function fplList(P, x, y, w, rowH, nRows, title = true) {
  const ctx = P.ctx;
  if (title) {
    box(ctx, x + 1, y, w * 0.6, 7.2, { fill: '#2f3d55', stroke: '#51647f', r: 1.2, lw: 0.25 });
    L(P, 'activeFpl', x + 3, y + 4.9, 2.4, C.cyan, { cw: 0.42 });
    poly(ctx, [[x + w * 0.6 - 4, y + 3], [x + w * 0.6 - 1.6, y + 3], [x + w * 0.6 - 2.8, y + 4.6]], C.white);
    y += 9.6;
    line(ctx, [[x + 1, y], [x + w * 0.58, y]], C.grey, 0.25);
    line(ctx, [[x + w * 0.62, y], [x + w - 1, y]], C.grey, 0.25);
    y += 1.6;
  }
  const lw = w * 0.58, rw = w - lw - 3;
  for (let i = 0; i < nRows && i < FPL.length; i++) {
    const r = FPL[i], yy = y + i * rowH;
    box(ctx, x + 1, yy, lw, rowH - 1.4, { fill: C.key, stroke: C.keyEdge, r: 0.9, lw: 0.2 });
    if (r.active) { ctx.fillStyle = C.green; ctx.fillRect(x + 1, yy, 1.2, rowH - 1.4); }
    const col = r.active ? C.green : r.cyan ? C.cyan : C.white;
    L(P, r.id, x + 4, yy + rowH * 0.48, 2.6, col, { cw: 0.48 });
    if (r.sub) L(P, r.sub, x + 4, yy + rowH * 0.82, 1.5, r.active ? C.green : C.grey, { cw: 0.4 });
    if (r.dist) N(P, 'fplDist', r.dist, x + lw - 1, yy + rowH * 0.36, 1.9, C.white, { align: 'right' });
    box(ctx, x + lw + 3, yy, rw, rowH - 1.4, { fill: C.key, stroke: C.keyEdge, r: 0.9, lw: 0.2 });
    const cx = x + lw + 3 + rw * 0.48;
    if (r.alt) {
      N(P, 'fplAlt', r.alt, cx + (r.fl ? 1.5 : 0), yy + rowH * 0.62, 2.8, C.white, { align: 'right' });
      if (r.fl) L(P, 'fl', cx - numWidth(r.alt, 2.8) - 1.2, yy + rowH * 0.62, 2.0, C.white, { align: 'right', cw: 0.6 });
      else L(P, 'ft', cx + 0.6, yy + rowH * 0.62, 1.5, C.white);
      if (r.alt === '5500') line(ctx, [[cx - 9, yy + rowH * 0.72], [cx + 0.2, yy + rowH * 0.72]], C.white, 0.2);
    } else N(P, 'fplAlt', '- - - -', cx, yy + rowH * 0.62, 2.2, C.white, { align: 'right', spacing: 0.4 });
    const sx = x + lw + 3 + rw - 1;
    if (r.climb) L(P, 'climb', sx, yy + rowH * 0.45, 2.2, C.white, { align: 'right', cw: 0.45 });
    else if (r.spd) N(P, 'fplSpd', r.spd, sx - 2, yy + rowH * 0.62, 2.5, C.white, { align: 'right' });
    else N(P, 'fplSpd', '- - -', sx - 2, yy + rowH * 0.5, 1.8, C.white, { align: 'right', spacing: 0.4 });
  }
}
function fplPane(P, x0) {
  const ctx = P.ctx, W = 122, H = 189.5;
  ctx.save(); ctx.translate(x0, 0);
  const c = P.cache.fpl || (P.cache.fpl = P.layer(() => {
    const ctx = P.ctx;
    ctx.fillStyle = '#07090c'; ctx.fillRect(0, 0, W, H);
    ctx.save(); ctx.translate(3, 3); fplList(P, 0, 0, W - 22, 15.8, 8); ctx.restore();
    // scroll bar, the pane's corner icons, the icon bar
    line(ctx, [[W - 14, 20], [W - 14, 150]], 'rgba(150,160,180,0.35)', 0.5);
    line(ctx, [[W - 14, 24], [W - 14, 64]], C.white, 0.8);
    box(ctx, W - 22, 1.6, 9, 7.6, { fill: C.key, stroke: C.keyEdge, r: 1.0, lw: 0.2 });
    box(ctx, W - 11, 1.6, 9, 7.6, { fill: C.key, stroke: C.keyEdge, r: 1.0, lw: 0.2 });
    for (const y of [3.8, 5.4, 7.0]) line(ctx, [[W - 8.8, y], [W - 4.2, y]], C.white, 0.45);
    ctx.fillStyle = '#05060a'; ctx.fillRect(0, 171, W, 18.5);
    iconBar(ctx, [8, 26, 44, 62], 180.2, 0, 'pdu');
  }, 0, 0, W, H));
  P.blit(c, x0, 0);
  ctx.restore();
}

// a METAR-style wind barb (direction / speed numerals), north-up or heading-up
function windBarb(P, x, y, dir, kt, hdg, headingUp) {
  const ctx = P.ctx;
  box(ctx, x - 11, y - 9, 22, 22, { fill: 'rgba(6,8,12,0.75)', stroke: C.keyEdge, r: 1.2, lw: 0.2 });
  const a = ((headingUp ? dir - hdg : dir) - 90) * D2R;            // the barb points from where the wind blows
  const ux = Math.cos(a), uy = Math.sin(a), px = -uy, py = ux;
  if (kt >= 1) {
    line(ctx, [[x - 6 * ux, y - 6 * uy], [x + 6 * ux, y + 6 * uy]], C.white, 0.45);
    // feathers at the upwind end: 10 kt long, 5 kt short, 50 kt a pennant
    let k = Math.round(kt / 5) * 5, s = 6;
    while (k >= 50) { poly(ctx, [[x + s * ux, y + s * uy], [x + (s - 2.4) * ux, y + (s - 2.4) * uy], [x + s * ux + 4 * px, y + s * uy + 4 * py]], C.white); k -= 50; s -= 2.8; }
    while (k >= 10) { line(ctx, [[x + s * ux, y + s * uy], [x + s * ux + 4 * px + 1.2 * ux, y + s * uy + 4 * py + 1.2 * uy]], C.white, 0.45); k -= 10; s -= 1.6; }
    if (k >= 5) line(ctx, [[x + s * ux, y + s * uy], [x + s * ux + 2.2 * px + 0.6 * ux, y + s * uy + 2.2 * py + 0.6 * uy]], C.white, 0.45);
    poly(ctx, [[x - 6 * ux, y - 6 * uy], [x - 4.2 * ux + 1.1 * px, y - 4.2 * uy + 1.1 * py], [x - 4.2 * ux - 1.1 * px, y - 4.2 * uy - 1.1 * py]], C.white);
  } else {
    ctx.beginPath(); ctx.arc(x, y, 2.2, 0, 2 * Math.PI); ctx.strokeStyle = C.white; ctx.lineWidth = 0.4; ctx.stroke();
  }
  N(P, 'windDir', deg(dir), x, y + 10.6, 2.4, C.white, { align: 'center' });
  N(P, 'windKt', String(kt), x + 9.4, y - 5.0, 2.4, C.cyan, { align: 'right' });
}

// the bottom icon row: map globe (selected: a blue rounded square), traffic, eye, checklist / the SDU's five tabs
function iconBar(ctx, xs, y, sel, kind) {
  xs.forEach((x, i) => {
    const s = kind === 'sdu' ? 6.4 : 5.6;
    if (i === sel) box(ctx, x - s, y - s, 2 * s, 2 * s, { fill: C.blue, stroke: null, r: 1.6 });
    ctx.strokeStyle = C.white; ctx.fillStyle = C.white; ctx.lineWidth = 0.45; ctx.lineCap = 'round';
    const k = kind === 'sdu' ? [0, 1, 2, 3, 4][i] : [5, 6, 7, 8][i];
    ctx.beginPath();
    if (k === 0) {            // aircraft
      ctx.moveTo(x - 3.2, y + 0.6); ctx.lineTo(x + 3.2, y - 0.6); ctx.moveTo(x + 1.4, y - 3.6); ctx.lineTo(x - 0.6, y + 3.6);
      ctx.moveTo(x - 2.8, y - 1.6); ctx.lineTo(x - 2.4, y + 1.4); ctx.stroke();
    } else if (k === 1) {     // procedures: a P-like hook
      ctx.arc(x + 0.6, y - 1.2, 2.0, Math.PI, Math.PI * 2.6); ctx.moveTo(x - 1.4, y - 1.2); ctx.lineTo(x - 2.6, y + 3.4); ctx.stroke();
    } else if (k === 2) {     // take-off / landing
      ctx.moveTo(x - 3.6, y + 2.6); ctx.lineTo(x + 3.6, y + 2.6); ctx.moveTo(x - 2.6, y + 1.2); ctx.lineTo(x + 2.8, y - 2.2); ctx.stroke();
    } else if (k === 3) {     // split pane
      ctx.rect(x - 3.6, y - 2.4, 7.2, 4.8); ctx.moveTo(x - 1, y - 2.4); ctx.lineTo(x - 1, y + 2.4); ctx.stroke();
    } else if (k === 4) {     // app grid
      for (const a of [-2.2, 0, 2.2]) for (const b of [-2.2, 0, 2.2]) { ctx.moveTo(x + a - 0.4, y + b); ctx.lineTo(x + a + 0.4, y + b); }
      ctx.lineWidth = 1.1; ctx.stroke();
    } else if (k === 5) {     // map globe
      ctx.arc(x, y, 3.2, 0, 2 * Math.PI); ctx.moveTo(x - 3.2, y); ctx.lineTo(x + 3.2, y); ctx.moveTo(x, y - 3.2);
      ctx.ellipse(x, y, 1.4, 3.2, 0, -Math.PI / 2, Math.PI * 1.5); ctx.stroke();
    } else if (k === 6) {     // traffic
      ctx.moveTo(x - 3, y + 3); ctx.lineTo(x + 3, y - 3); ctx.moveTo(x + 0.4, y - 3); ctx.lineTo(x + 3, y - 3); ctx.lineTo(x + 3, y - 0.4);
      ctx.moveTo(x - 3, y - 1); ctx.lineTo(x - 1, y - 3); ctx.stroke();
    } else if (k === 7) {     // eye
      ctx.ellipse(x, y, 3.6, 2.0, 0, 0, 2 * Math.PI); ctx.moveTo(x + 1.0, y); ctx.arc(x, y, 1.0, 0, 2 * Math.PI); ctx.stroke();
    } else {                  // checklist
      ctx.rect(x - 2.6, y - 3.4, 5.2, 6.8); ctx.moveTo(x - 1.4, y - 1); ctx.lineTo(x + 1.4, y - 1); ctx.moveTo(x - 1.4, y + 1); ctx.lineTo(x + 1.4, y + 1); ctx.stroke();
    }
  });
}

export function drawPdu(P, S, world) {
  const V = viewPfd(S, P.side);
  const ctx = P.ctx;
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, 305, 189.5);
  const pfdX = P.side === 'L' ? 0 : 305 - PFD_W, inX = P.side === 'L' ? PFD_W : 0;
  ctx.save(); ctx.translate(pfdX, 0); pfdPage(P, V, world); ctx.restore();
  if (P.side === 'L') safeTaxi(P, V, world, inX);
  else fplPane(P, inX);
  // the pane divider
  line(ctx, [[P.side === 'L' ? PFD_W : 305 - PFD_W, 0], [P.side === 'L' ? PFD_W : 305 - PFD_W, 189.5]], '#2a2e36', 0.5);
  return V;
}
export function keyPdu(S, side) { return JSON.stringify(viewPfd(S, side)); }

// ================================================================== the MFD
// the engine / systems strip (x 0-58 mm): arc gauges -- ~200 deg from 9 o'clock over the top (0 lies horizontally
// left), coloured bands, limit marks outside, a tapered pointer with a semi-transparent fan, the readout under it
function arcGauge(P, x, y, r, id, val, col, b, o = {}) {
  const ctx = P.ctx, sweep = 200, a0 = 180;
  const ang = (v) => (a0 - clamp((v - b.lo) / (b.hi - b.lo), 0, 1) * sweep) * D2R;
  const pt = (a, rr) => [x + rr * Math.cos(a), y - rr * Math.sin(a)];
  for (const [f, t, c] of b.arcs) {
    ctx.beginPath(); ctx.arc(x, y, r, -ang(f), -ang(t), false);
    ctx.strokeStyle = c === 'green' ? C.green : c === 'grey' ? C.white : COLOR[c]; ctx.lineWidth = c === 'grey' ? 0.45 : 0.85; ctx.stroke();
  }
  for (const [v, c] of b.marks) {
    const a = ang(v);
    line(ctx, [pt(a, r - 0.6), pt(a, r + 2.0)], COLOR[c] || C.white, 0.6);
  }
  if (o.bug != null) {
    const a = ang(o.bug), p = pt(a, r + 0.9), t = [-Math.sin(a), -Math.cos(a)], n = [Math.cos(a), -Math.sin(a)];
    poly(ctx, [p, [p[0] + 2.4 * n[0] + 1.3 * t[0], p[1] + 2.4 * n[1] + 1.3 * t[1]], [p[0] + 2.4 * n[0] - 1.3 * t[0], p[1] + 2.4 * n[1] - 1.3 * t[1]]], C.white);
  }
  if (o.mark13) { const a = ang(13); line(ctx, [pt(a, r - 1.4), pt(a, r + 2.2)], C.white, 0.7); }
  // fan + pointer
  const av = ang(val), cc = COLOR[col] || C.green;
  ctx.beginPath(); ctx.moveTo(x, y); ctx.arc(x, y, r - 0.6, -ang(b.lo), -av, false); ctx.closePath();
  ctx.fillStyle = col === 'green' ? 'rgba(63,224,74,0.22)' : col === 'amber' ? 'rgba(255,176,0,0.3)' : 'rgba(255,42,42,0.35)'; ctx.fill();
  const tip = pt(av, r - 0.7), n = [-Math.sin(av), -Math.cos(av)];
  poly(ctx, [[x + 1.1 * n[0], y + 1.1 * n[1]], tip, [x - 1.1 * n[0], y - 1.1 * n[1]], pt(av + Math.PI, 0.8)], cc, 'rgba(0,0,0,0.6)', 0.15);
}
function readout(P, id, val, x, y, size, col, unitId) {
  const fg = col === 'amber' ? '#000' : col === 'red' ? C.white : col === 'normal' ? C.white : C.green;
  if (col === 'amber' || col === 'red') {
    const w = numWidth(val, size) + 1.6;
    box(P.ctx, x - w + 0.8, y - size - 0.8, w, size + 1.6, { fill: COLOR[col], stroke: null, r: 0.4 });
  }
  N(P, id, val, x, y, size, fg, { align: 'right' });
  if (unitId) L(P, unitId, x + 0.8, y, size * 0.48, C.white, { cw: 0.6 });
}
function vScale(P, x, y0, y1, id, val, col, b) {
  const ctx = P.ctx, yv = (v) => y1 - clamp((v - b.lo) / (b.hi - b.lo), 0, 1) * (y1 - y0);
  for (const [f, t, c] of b.arcs) line(ctx, [[x, yv(f)], [x, yv(t)]], c === 'green' ? C.green : C.white, c === 'grey' ? 0.4 : 0.85);
  for (const [v, c] of b.marks) line(ctx, [[x - 1.3, yv(v)], [x + 1.3, yv(v)]], COLOR[c], 0.55);
  const y = yv(val), cc = COLOR[col] || C.green;
  poly(ctx, [[x - 0.6, y], [x - 2.6, y - 1.3], [x - 2.6, y + 1.3]], cc);
}

function eisStrip(P, V) {
  const ctx = P.ctx;
  // PCL position legend (IDL / T/O / REV, green) over the TRQ / ITT pair
  if (V.pcl) L(P, V.pcl, 29, 4.6, 2.4, C.green, { align: 'center', cw: 0.6 });
  arcGauge(P, 14.5, 16.5, 10, 'tq', +V.tqA, V.tqC, bands('tq'), { bug: V.bug != null ? +V.bug : null });
  arcGauge(P, 43.5, 16.5, 10, 'itt', +V.ittA, V.ittC, bands('itt', { start: V.start }));
  L(P, 'trq', 1.2, 24.6, 1.8, C.white, { cw: 0.62 });
  readout(P, 'tq', V.tq, 21.5, 24.8, 3.8, V.tqC === 'green' ? 'green' : V.tqC, 'psi');
  L(P, 'itt', 30.2, 24.6, 1.8, C.white, { cw: 0.62 });
  readout(P, 'itt', V.itt, 51.6, 24.8, 3.8, V.ittC, 'degc');
  arcGauge(P, 14.5, 36.5, 10, 'ng', +V.ngA, V.ngC, bands('ng'), { mark13: V.mark13 });
  L(P, 'ng', 1.2, 45.2, 1.8, C.white, { cw: 0.62 });
  readout(P, 'ng', V.ng, 21.5, 45.4, 3.8, V.ngC, 'pct');
  // oil: temperature (C, 0-120) and pressure (psi, 50-150) scales side by side
  L(P, 'oil', 44, 29, 1.6, C.white, { cw: 0.6 });
  vScale(P, 37.6, 28.5, 40.5, 'oilT', +V.oilTp, V.oilTC, bands('oilT'));
  vScale(P, 50.6, 28.5, 40.5, 'oilP', +V.oilPp, V.oilPC, bands('oilP'));
  L(P, 'degc', 39.2, 41.6, 1.4, C.white, { cw: 0.6 });
  L(P, 'psi', 46.0, 41.6, 1.4, C.white, { cw: 0.5 });
  readout(P, 'oilT', V.oilT, 40.5, 45.6, 3.6, V.oilTC);
  readout(P, 'oilP', V.oilP, 53.5, 45.6, 3.6, V.oilPC);
  // NP (digital) and T1
  box(ctx, 1, 47.6, 33, 6.8, { fill: C.box, stroke: C.boxEdge, r: 1.2, lw: 0.25 });
  L(P, 'np', 2.4, 52.2, 1.8, C.white, { cw: 0.62 });
  readout(P, 'np', V.np, 26.5, 52.6, 3.8, V.npC === 'normal' ? 'green' : V.npC, 'rpm');
  L(P, 't1', 36, 52.2, 1.8, C.white, { cw: 0.62 });
  N(P, 't1', `${V.t1}`, 52, 52.6, 3.8, C.white, { align: 'right' });
  L(P, 'degc', 52.8, 52.6, 1.8, C.white, { cw: 0.6 });
  // the annunciation row: the boost pumps (green), STARTER / IGNITION while the starter / igniters run
  if (V.pumps) {
    box(ctx, 1.5, 56.4, 13.5, 3.8, { fill: C.green, stroke: null, r: 0.4 });
    box(ctx, 16, 56.4, 13.5, 3.8, { fill: C.green, stroke: null, r: 0.4 });
    L(P, 'pumpL', 8.25, 59.2, 1.6, '#062a0a', { align: 'center', cw: 0.45, alpha: 1 });
    L(P, 'pumpR', 22.75, 59.2, 1.6, '#062a0a', { align: 'center', cw: 0.45, alpha: 1 });
  }
  if (V.starter) { box(ctx, 31, 56.4, 12.6, 3.8, { fill: null, stroke: C.green, r: 0.4, lw: 0.35 }); L(P, 'starter', 37.3, 59.2, 1.6, C.green, { align: 'center', cw: 0.42 }); }
  if (V.ign) { box(ctx, 44.6, 56.4, 12.6, 3.8, { fill: null, stroke: C.green, r: 0.4, lw: 0.35 }); L(P, 'ignition', 50.9, 59.2, 1.6, C.green, { align: 'center', cw: 0.42 }); }
  // fuel: two tank bars (quarters, the half mark, the LOW zone), QTY / FF / END
  box(ctx, 1, 62.5, 56.5, 28, { fill: C.box, stroke: C.boxEdge, r: 1.6, lw: 0.25 });
  L(P, 'fuel', 9.8, 66.2, 1.6, C.white, { align: 'center', cw: 0.55 });
  for (const tx of [4.6, 13.4]) {
    const y0 = 67.5, y1 = 88.4, h = y1 - y0;
    box(ctx, tx, y0, 2.6, h, { fill: '#0a0b0e', stroke: C.white, r: 0.3, lw: 0.3 });
    const low = 134 / 1352 * h;
    ctx.fillStyle = V.low ? C.amber : 'rgba(255,42,42,0.85)'; ctx.fillRect(tx + 0.3, y1 - low, 2.0, low - 0.2);
    ctx.fillStyle = V.low ? C.amber : '#d8dadd'; ctx.fillRect(tx + 0.3, y1 - V.tankF * h + 0.2, 2.0, Math.max(0, V.tankF * h - low - 0.2));
    for (let k = 1; k < 4; k++) line(ctx, [[tx + (tx < 10 ? 2.6 : -0.9), y1 - k * h / 4], [tx + (tx < 10 ? 3.5 : 0), y1 - k * h / 4]], C.white, 0.3);
    const yl = y1 - V.tankF * h, s = tx < 10 ? -1 : 1, xe = tx < 10 ? tx : tx + 2.6;
    poly(ctx, [[xe, yl], [xe + s * 2.0, yl - 1.1], [xe + s * 2.0, yl + 1.1]], V.low ? C.amber : C.green);
  }
  N(P, 'half', '1/2', 10.0, 79.2, 1.8, C.white, { align: 'center', spacing: 0.3 });
  L(P, 'qty', 20.5, 71.4, 1.7, C.white, { cw: 0.6 });
  N(P, 'qty', V.qty, 50.5, 71.8, 3.9, V.low ? C.amber : C.white, { align: 'right' }); L(P, 'lb', 51.2, 71.8, 1.6, C.white, { cw: 0.6 });
  L(P, 'ff', 20.5, 79.0, 1.7, C.white, { cw: 0.6 });
  N(P, 'ff', V.ff, 50.5, 79.4, 3.6, C.white, { align: 'right' }); L(P, 'lbh', 51.2, 79.4, 1.4, C.white, { cw: 0.45 });
  L(P, 'end', 20.5, 86.6, 1.7, C.white, { cw: 0.6 });
  N(P, 'end', V.end || '- -:- -', 50.5, 87.0, 3.2, C.white, { align: 'right', spacing: V.end ? 1 : 0.4 }); L(P, 'hm', 51.2, 87.0, 1.4, C.white, { cw: 0.45 });
  // gear: three pills (nose on top): green + DN when down and locked, hatched in transit, outlined + UP when up
  for (const [gx, gy] of [[12, 99.6], [6, 107.8], [18, 107.8]]) {
    const w = 5.6, h = 9.4;
    if (V.gear === 'down') {
      box(ctx, gx - w / 2, gy - h / 2, w, h, { fill: C.green, stroke: null, r: 2.8 });
      L(P, 'dn', gx, gy + 1.0, 2.0, '#062a0a', { align: 'center', cw: 0.75, alpha: 1 });
    } else if (V.gear === 'up') {
      box(ctx, gx - w / 2, gy - h / 2, w, h, { fill: '#000', stroke: C.white, r: 0.6, lw: 0.35 });
      L(P, 'up', gx, gy + 1.0, 2.0, C.white, { align: 'center', cw: 0.75, alpha: 1 });
    } else {
      rr(ctx, gx - w / 2, gy - h / 2, w, h, 2.8); ctx.fillStyle = '#000'; ctx.fill(); ctx.save(); ctx.clip();
      for (let k = -12; k < 12; k += 1.6) line(ctx, [[gx + k, gy + h / 2 + 1], [gx + k + 7, gy - h / 2 - 1]], C.white, 0.35);
      ctx.restore(); rr(ctx, gx - w / 2, gy - h / 2, w, h, 2.8); ctx.strokeStyle = C.white; ctx.lineWidth = 0.3; ctx.stroke();
    }
  }
  // flaps: marks 0 / 15 / 30 / 40 on an arc, the airfoil pointer
  const fc = { x: 33.5, y: 96.5, r: 18 }, fa = (d) => (-d * 1.5) * D2R;
  for (const d of [0, 15, 30, 40]) {
    const a = fa(d), p0 = [fc.x + (fc.r - 0.5) * Math.cos(a), fc.y - (fc.r - 0.5) * Math.sin(a)], p1 = [fc.x + (fc.r + 1.4) * Math.cos(a), fc.y - (fc.r + 1.4) * Math.sin(a)];
    const at = Math.abs(V.flaps - d) < 0.05, mc = at && V.flapC === 'green' ? C.green : C.white;
    line(ctx, [p0, p1], mc, 0.5);
    line(ctx, [[p1[0] - 0.9, p1[1] - 0.4], [p1[0] - 1.5, p1[1] - 1.2]], mc, 0.4);
    N(P, 'flapMark', String(d), fc.x + (fc.r + 4.4) * Math.cos(a) + (d === 40 ? -1.8 : 0), fc.y - (fc.r + 4.4) * Math.sin(a) + 1.3, 2.4, mc, { align: 'center' });
  }
  const a = fa(V.flaps), ux = Math.cos(a), uy = -Math.sin(a), nx = -uy, ny = ux, L0 = 7.5, L1 = fc.r - 1.2;
  const fcol = COLOR[V.flapC] || C.white;
  ctx.beginPath();
  ctx.moveTo(fc.x + L0 * ux, fc.y + L0 * uy);
  ctx.quadraticCurveTo(fc.x + (L0 + 2) * ux + 1.6 * nx, fc.y + (L0 + 2) * uy + 1.6 * ny, fc.x + (L0 + 5) * ux + 1.3 * nx, fc.y + (L0 + 5) * uy + 1.3 * ny);
  ctx.lineTo(fc.x + L1 * ux, fc.y + L1 * uy);
  ctx.lineTo(fc.x + (L0 + 5) * ux - 0.5 * nx, fc.y + (L0 + 5) * uy - 0.5 * ny);
  ctx.quadraticCurveTo(fc.x + (L0 + 1) * ux - 0.9 * nx, fc.y + (L0 + 1) * uy - 0.9 * ny, fc.x + L0 * ux, fc.y + L0 * uy);
  ctx.fillStyle = fcol; ctx.fill();
  // trims: pitch (side view), roll (plan view), yaw (tail view) on dashed arcs; green in the take-off range
  const trim = (cx0, cy0, val, range, ok, kind) => {
    const col = ok ? C.green : C.white, ang = val / range * 30 * D2R;
    ctx.save(); ctx.setLineDash([0.6, 0.8]);
    ctx.beginPath();
    if (kind === 'roll') ctx.arc(cx0, cy0, 6.2, -Math.PI * 0.95, -Math.PI * 0.05);
    else ctx.arc(cx0 + (kind === 'pitch' ? -4.5 : 4.5), cy0, 5.2, kind === 'pitch' ? -Math.PI * 0.35 : Math.PI * 0.65, kind === 'pitch' ? Math.PI * 0.35 : Math.PI * 1.35);
    ctx.strokeStyle = C.white; ctx.lineWidth = 0.4; ctx.stroke(); ctx.restore();
    ctx.save(); ctx.translate(cx0, cy0); ctx.rotate(kind === 'yaw' ? -ang : ang);
    ctx.fillStyle = col; ctx.strokeStyle = col; ctx.lineWidth = 0.55; ctx.lineCap = 'round';
    if (kind === 'roll') {         // plan view
      ctx.beginPath(); ctx.moveTo(0, -3.6); ctx.lineTo(0, 3.6); ctx.moveTo(-4.4, -0.4); ctx.lineTo(4.4, -0.4); ctx.moveTo(-1.6, 3.2); ctx.lineTo(1.6, 3.2); ctx.stroke();
    } else {                       // side view (pitch: nose right; yaw: the fin)
      const s = kind === 'pitch' ? 1 : -1;
      ctx.beginPath(); ctx.moveTo(-4.4 * s, 0); ctx.lineTo(4.4 * s, 0.2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-4.0 * s, 0); ctx.lineTo(-4.4 * s, -2.4); ctx.lineTo(-3.4 * s, -2.4); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(-0.8 * s, 0.1); ctx.lineTo(0.6 * s, 0.1); ctx.lineTo(0.2 * s, 1.0); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
    if (kind === 'pitch' && ok) poly(ctx, [[cx0 - 9.2, cy0 - 1], [cx0 - 8.4, cy0], [cx0 - 9.2, cy0 + 1], [cx0 - 10, cy0]], C.green);
  };
  trim(9.5, 127, V.stab, 4, V.stabOk, 'pitch');
  trim(28.5, 127.5, V.ail, 10, V.ailOk, 'roll');
  trim(47.5, 127, V.rud, 12, V.rudOk, 'yaw');
  // BAT1 / BAT2: volts and amps with a horizontal bar each
  box(ctx, 1, 136.4, 56.5, 14.2, { fill: C.box, stroke: C.boxEdge, r: 1.6, lw: 0.25 });
  V.bat.forEach(([v, a2, f, col], i) => {
    const x = 2.2 + i * 28;
    L(P, i ? 'bat2' : 'bat1', x, 140.0, 1.6, C.white, { cw: 0.55 });
    box(ctx, x + 6.5, 137.6, 19, 2.8, { fill: '#000', stroke: C.white, r: 0.2, lw: 0.2 });
    ctx.fillStyle = COLOR[col]; ctx.fillRect(x + 6.8, 137.9, Math.max(0.1, f * 18.4), 2.2);
    for (const vv of [22, 30.3]) { const xx = x + 6.5 + (vv - 20) / 12 * 19; line(ctx, [[xx, 136.9], [xx, 137.6]], C.red, 0.35); }
    N(P, i ? 'bat2V' : 'bat1V', v, x + 10.2, 147.6, 3.3, COLOR[col], { align: 'right' });
    L(P, 'v', x + 10.8, 147.6, 1.6, C.white, { cw: 0.7 });
    N(P, i ? 'bat2A' : 'bat1A', a2, x + 22.5, 147.6, 3.3, COLOR[col], { align: 'right' });
    L(P, 'a', x + 23.1, 147.6, 1.6, C.white, { cw: 0.7 });
  });
  // the inertial separator (open on the ground): a green status band
  box(ctx, 1.5, 152.2, 31, 3.8, { fill: C.green, stroke: null, r: 0.3 });
  L(P, 'inertSep', 17, 155.0, 1.6, '#062a0a', { align: 'center', cw: 0.42, alpha: 1 });
  // pressurisation: FMS ELEV (magenta: the field elevation), CAB ALT (= the pressure altitude, unpressurised), dP, rate
  box(ctx, 1, 160, 56.5, 22.5, { fill: C.box, stroke: C.boxEdge, r: 1.6, lw: 0.25 });
  L(P, 'fmsElev', 2.2, 165.0, 1.8, C.white, { cw: 0.48 });
  L(P, 'field', 18, 165.4, 3.0, C.magenta, { cw: 0.55 });
  N(P, 'fmsElev', V.elev, 47.5, 165.6, 3.4, C.magenta, { align: 'right' }); L(P, 'ft', 48.2, 165.6, 1.6, C.white, { cw: 0.65 });
  L(P, 'cabAlt', 2.2, 171.0, 1.6, C.white, { cw: 0.48 });
  N(P, 'cabAlt', V.cabAlt, 13.5, 179.6, 3.4, C.green, { align: 'right' }); L(P, 'ft', 14.1, 179.6, 1.5, C.white, { cw: 0.6 });
  L(P, 'dp', 24, 171.0, 1.6, C.white, { cw: 0.6 });
  N(P, 'dp', '0.00', 33, 179.6, 3.4, C.green, { align: 'right' }); L(P, 'psi', 33.6, 179.6, 1.5, C.white, { cw: 0.5 });
  L(P, 'cabRate', 40, 171.0, 1.6, C.white, { cw: 0.45 });
  N(P, 'cabRate', '+0', 48.5, 179.6, 3.4, C.white, { align: 'right' }); L(P, 'fpm', 49.1, 179.6, 1.5, C.white, { cw: 0.5 });
}

// the moving map's relief (seeded value noise, hill-shaded, tan / brown with lakes), drawn once
function noise2(seed) {
  const R = (i, j) => { const s = Math.sin(i * 127.1 + j * 311.7 + seed * 74.7) * 43758.5453; return s - Math.floor(s); };
  const sm = (t) => t * t * (3 - 2 * t);
  return (x, y) => {
    const i = Math.floor(x), j = Math.floor(y), u = sm(x - i), v = sm(y - j);
    return R(i, j) * (1 - u) * (1 - v) + R(i + 1, j) * u * (1 - v) + R(i, j + 1) * (1 - u) * v + R(i + 1, j + 1) * u * v;
  };
}
function reliefCanvas(wpx, hpx) {
  const cv = document.createElement('canvas');
  cv.width = wpx; cv.height = hpx;
  const g = cv.getContext('2d'), img = g.createImageData(wpx, hpx), d = img.data;
  const N = []; for (let k = 0; k < 16; k++) N.push(noise2(3 + 13 * k));
  const fbm = (u, v, f, n, o, ridge) => {
    let a = 0.5, s = 0, t = 0;
    for (let k = 0; k < n; k++) { let q = N[o + k](u * f, v * f); if (ridge) q = 1 - Math.abs(2 * q - 1); s += a * q; t += a; f *= 2.03; a *= 0.5; }
    return s / t;
  };
  const n = wpx * hpx, e = new Float32Array(n), riv = new Float32Array(n), sc = 1 / Math.max(wpx, hpx);
  for (let y = 0; y < hpx; y++) for (let x = 0; x < wpx; x++) {
    const u = x * sc, v = y * sc, i = y * wpx + x;
    // a fractal plain with a ridged range toward the lower right (the map's south-east), a river winding along the
    // valley floor and a few lakes in the hollows
    const base = fbm(u, v, 3.0, 6, 0, false), rid = fbm(u + 0.3 * base, v, 5.0, 5, 6, true);
    const trend = Math.max(0, (u - 0.45) * 0.9 + (v - 0.35) * 0.8), mount = Math.min(1, trend * 1.6);
    e[i] = 0.55 * base + mount * 0.55 * rid * rid + 0.35 * trend;
    const rv = fbm(u + 0.15 * base, v + 0.1 * base, 2.2, 4, 11, false);
    riv[i] = mount < 0.25 ? Math.exp(-(((rv - 0.5) / 0.0055) ** 2)) : 0;
  }
  // hypsometric tints (pale green-yellow lowland -> tan -> brown range) under a north-west hill shade
  const stops = [0.10, 0.18, 0.30, 0.45, 0.60, 0.78];
  const cols = [[190, 212, 138], [222, 214, 138], [224, 194, 122], [206, 160, 96], [176, 122, 72], [142, 96, 62]];
  const Lx = -0.6, Ly = -0.6, Lz = 0.53, Ln = Math.hypot(Lx, Ly, Lz), k = 55 * wpx / 968;
  for (let y = 0; y < hpx; y++) for (let x = 0; x < wpx; x++) {
    const i = y * wpx + x, h = e[i];
    const x1 = x < wpx - 1 ? 1 : 0, x0 = x > 0 ? 1 : 0, y1 = y < hpx - 1 ? wpx : 0, y0 = y > 0 ? wpx : 0;
    const gx = k * (e[i + x1] - e[i - x0]) / (x1 + x0), gy = k * (e[i + y1] - e[i - y0]) / ((y1 + y0) / wpx);
    const lam = (-gx * Lx - gy * Ly + Lz) / Ln / Math.sqrt(gx * gx + gy * gy + 1);
    let sh = clamp(1 + 1.17 * (lam - 0.85 * Lz / Ln), 0.55, 1.25);
    if (h <= 0.45) sh = Math.sqrt(sh);
    const t = clamp(h, stops[0], stops[5]);
    let j = 0; while (j < 4 && t > stops[j + 1]) j++;
    const f = (t - stops[j]) / (stops[j + 1] - stops[j]);
    let r = (cols[j][0] + f * (cols[j + 1][0] - cols[j][0])) * sh;
    let gg = (cols[j][1] + f * (cols[j + 1][1] - cols[j][1])) * sh;
    let b = (cols[j][2] + f * (cols[j + 1][2] - cols[j][2])) * sh;
    if (h < 0.10) { r = 120; gg = 170; b = 220; }                                       // lakes
    const w = 0.92 * clamp((riv[i] - 0.3) / 0.25, 0, 1);
    r = r * (1 - w) + 110 * w; gg = gg * (1 - w) + 160 * w; b = b * (1 - w) + 215 * w;    // the river
    d[4 * i] = clamp(r, 0, 255); d[4 * i + 1] = clamp(gg, 0, 255); d[4 * i + 2] = clamp(b, 0, 255); d[4 * i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  return { cv, h: e };
}

function mfdMap(P, V) {
  const ctx = P.ctx, x0 = 61.5, y0 = 18.5, W = 242, H = 99;
  const st = P.cache.map || (P.cache.map = P.layer(() => {
    const ctx = P.ctx;
    const k = Math.max(1, Math.round(P.pxPerMm * 0.5));
    const rel = reliefCanvas(Math.round(W * P.pxPerMm / k), Math.round(H * P.pxPerMm / k));
    P.cache.relief = rel;
    ctx.drawImage(rel.cv, x0, y0, W, H);
    // airspace (magenta dotted), roads (light), the route (magenta), VORs / waypoints
    ctx.save(); ctx.beginPath(); ctx.rect(x0, y0, W, H); ctx.clip();
    const rnd = noise2(7);
    for (let i = 0; i < 7; i++) {
      ctx.beginPath(); ctx.ellipse(x0 + 30 + 32 * i * rnd(i, 1) * 1.6, y0 + 20 + 60 * rnd(1, i), 16 + 10 * rnd(i, 3), 10 + 9 * rnd(3, i), rnd(i, i) * 3, 0, 2 * Math.PI);
      ctx.setLineDash([0.6, 0.9]); ctx.strokeStyle = 'rgba(150,70,200,0.85)'; ctx.lineWidth = 0.45; ctx.stroke();
    }
    ctx.setLineDash([]);
    for (let i = 0; i < 9; i++) {
      line(ctx, [[x0 + 240 * rnd(i, 5), y0], [x0 + 240 * rnd(i, 9), y0 + H]], 'rgba(170,200,230,0.5)', 0.25);
    }
    for (let i = 0; i < 26; i++) {
      const x = x0 + 10 + 220 * rnd(i * 3, 2), y = y0 + 8 + 82 * rnd(2, i * 3);
      if (i % 3 === 0) poly(ctx, [[x, y - 2], [x + 2, y], [x, y + 2], [x - 2, y]], 'rgba(150,70,200,0.9)');
      else { ctx.beginPath(); ctx.arc(x, y, 1.4, 0, 2 * Math.PI); ctx.strokeStyle = 'rgba(70,100,200,0.9)'; ctx.lineWidth = 0.4; ctx.stroke(); }
    }
    const route = [[x0 + 8, y0 + 75], [x0 + 70, y0 + 60], [x0 + 118, y0 + 52], [x0 + 160, y0 + 40], [x0 + 236, y0 + 22]];
    line(ctx, route, 'rgba(255,255,255,0.9)', 0.9);
    line(ctx, route, C.magenta, 0.55);
    route.slice(1, 4).forEach(([x, y], i) => { box(ctx, x - 5, y - 6.5, 10, 3.6, { fill: 'rgba(0,0,0,0.75)', stroke: C.white, r: 0.4, lw: 0.2 }); L(P, ['wpt', 'field', 'fix1'][i], x, y - 3.7, 2.0, C.white, { align: 'center', cw: 0.45 }); });
    // the field: an airport symbol with its runway 06 / 24
    const fx = x0 + 118, fy = y0 + 52;
    ctx.beginPath(); ctx.arc(fx, fy, 2.6, 0, 2 * Math.PI); ctx.strokeStyle = 'rgba(60,90,200,1)'; ctx.lineWidth = 0.6; ctx.stroke();
    const ra = (240 - 90) * D2R;
    line(ctx, [[fx - 3.2 * Math.cos(ra), fy - 3.2 * Math.sin(ra)], [fx + 3.2 * Math.cos(ra), fy + 3.2 * Math.sin(ra)]], 'rgba(60,90,200,1)', 0.9);
    // the range ring
    ctx.beginPath(); ctx.arc(fx, fy, 40, Math.PI * 1.1, Math.PI * 1.9); ctx.strokeStyle = 'rgba(255,255,255,0.75)'; ctx.lineWidth = 0.3; ctx.stroke();
    ctx.restore();
    N(P, 'mapRange', '10', fx - 40 * Math.cos(0.4) + 2, fy - 40 * Math.sin(0.4) - 1, 2.4, C.white, { align: 'left' });
    // the North Up button and the status box
    box(ctx, x0 + 3, y0 + 3, 13, 13, { fill: 'rgba(30,34,42,0.88)', stroke: C.keyEdge, r: 1.2, lw: 0.25 });
    poly(ctx, [[x0 + 9.5, y0 + 5.2], [x0 + 13, y0 + 11.5], [x0 + 9.5, y0 + 9.8], [x0 + 6, y0 + 11.5]], C.white);
    L(P, 'northUp', x0 + 9.5, y0 + 14.6, 1.4, C.white, { align: 'center', cw: 0.42 });
    box(ctx, x0 + 3, y0 + H - 20, 34, 17, { fill: 'rgba(14,16,22,0.92)', stroke: C.keyEdge, r: 1.2, lw: 0.25 });
    L(P, 'status', x0 + 5, y0 + H - 15.6, 1.8, C.white);
    for (let i = 0; i < 3; i++) { L(P, ['traffic', 'terrain', 'weather'][i], x0 + 9, y0 + H - 11 + i * 3.4, 1.6, C.white, { cw: 0.42 }); poly(ctx, [[x0 + 5.2, y0 + H - 12.6 + i * 3.4], [x0 + 7.4, y0 + H - 12.6 + i * 3.4], [x0 + 6.3, y0 + H - 10.8 + i * 3.4]], i ? C.yellow : C.white); }
  }, x0, y0, W, H));
  P.blit(st, x0, y0);
  // live: the ownship at the field (rotated to the heading) and the wind barb there
  const fx = x0 + 118, fy = y0 + 52;
  ctx.save(); ctx.translate(fx, fy); ctx.rotate(V.hdg * D2R);
  poly(ctx, [[0, -3.4], [2.6, 2.4], [0, 1.2], [-2.6, 2.4]], C.white, '#000', 0.25);
  ctx.restore();
  windBarb(P, x0 + W - 16, y0 + 15, V.windDir, V.windKt, V.hdg, false);
}

// the vertical situation display: the terrain profile along the route from the field (its elevation the knob's), the
// altitude scale, the selected altitude (cyan dashes), waypoint stalks
function mfdVsd(P, V) {
  const ctx = P.ctx, x0 = 61.5, y0 = 119, W = 242, H = 52;
  ctx.fillStyle = '#0b1220'; ctx.fillRect(x0, y0, W, H);
  ctx.fillStyle = '#121a2c'; ctx.fillRect(x0, y0, W, 8);
  L(P, 'autoFpl', x0 + 3, y0 + 5.6, 2.2, C.white, { cw: 0.48 });
  const ax = x0 + 14, top = y0 + 14, bot = y0 + H - 4, aMax = 12000;
  const yA = (a) => bot - clamp(a / aMax, 0, 1.05) * (bot - top);
  for (const a of [0, 5000, 10000]) {
    line(ctx, [[ax, yA(a)], [x0 + W - 2, yA(a)]], 'rgba(150,170,200,0.25)', 0.2);
    N(P, 'vsdScale', String(a), ax - 1.6, yA(a) + 1.1, 2.2, C.white, { align: 'right' });
  }
  line(ctx, [[ax, top - 2], [ax, bot]], C.white, 0.3);
  // terrain: the field elevation at the left, rising toward the hills along the route
  const elev = +V.elev, rnd = noise2(5);
  const pts = [[ax, bot]];
  for (let i = 0; i <= 100; i++) {
    const u = i / 100, e = elev + 900 * u * u + 380 * (rnd(u * 9, 0.5) - 0.5) * u + 120 * rnd(u * 31, 1.5) * u;
    pts.push([ax + u * (x0 + W - 2 - ax), yA(Math.max(0, e))]);
  }
  pts.push([x0 + W - 2, bot]);
  poly(ctx, pts, '#7f8a2c');
  line(ctx, pts.slice(1, -1), '#c9c34a', 0.35);
  line(ctx, [[ax, yA(elev)], [ax + 22, yA(elev)]], C.white, 0.3);
  line(ctx, [[ax, yA(5000)], [x0 + W - 2, yA(5000)]], C.cyan, 0.4, [1.6, 1.2]);
  box(ctx, x0 + 3, y0 + 9.4, 10.5, 4, { fill: 'rgba(0,0,0,0.6)', stroke: null, r: 0.3 });
  N(P, 'vsdSel', '5000', x0 + 13, y0 + 12.6, 2.2, C.cyan, { align: 'right' });
  for (const [u, wid] of [[0.12, 'wpt'], [0.42, 'fix1'], [0.88, 'fix2']]) {
    const x = ax + u * (x0 + W - 2 - ax);
    line(ctx, [[x, top - 3], [x, bot]], 'rgba(230,235,245,0.7)', 0.3, [1.2, 1.0]);
    L(P, wid, x, top - 4, 1.8, u < 0.2 ? C.green : C.white, { align: 'center', cw: 0.45 });
  }
}

function mfdNavBar(P, V) {
  const ctx = P.ctx, x0 = 61.5, y = 6.4;
  ctx.fillStyle = '#05070a'; ctx.fillRect(x0, 0, 243.5, 9.2);
  line(ctx, [[x0, 9.2], [305, 9.2]], 'rgba(150,160,180,0.5)', 0.25);
  let x = x0 + 2;
  const item = (id, val, unit, w, dashes) => {
    L(P, id, x, y, 1.7, C.white, { cw: 0.55 });
    const vx = x + w;
    if (val == null) N(P, 'nav_' + id, dashes || '- - - -', vx, y, 2.6, C.white, { align: 'right', spacing: 0.4 });
    else N(P, 'nav_' + id, val, vx, y, 2.8, C.white, { align: 'right' });
    if (unit) L(P, unit, vx + 0.6, y, 1.4, C.white, { cw: 0.55 });
    x += w + (unit ? 6 : 3.5);
  };
  L(P, 'dest', x, y, 1.7, C.white, { cw: 0.55 }); L(P, 'destF', x + 7.2, y, 2.6, C.white, { cw: 0.5 }); x += 18;
  item('dtg', '380', 'nm', 16);
  item('enr', null, null, 18, '- -:- -:- -');
  item('fod', V.fod, 'lb', 20);
  item('endr', V.endr || null, null, 14);
  item('msa', '11400', 'ft', 18);
  item('flt', '0:00', null, 14);
  item('tod', null, null, 18, '- -:- -:- -');
  // the title row: Map, the expand / menu buttons
  ctx.fillStyle = '#080a0e'; ctx.fillRect(x0, 9.4, 243.5, 8.8);
  L(P, 'map', x0 + 3, 15.6, 2.4, C.white);
  for (const [bx, k] of [[279, 0], [291, 1]]) {
    box(ctx, bx, 10.2, 10, 7.4, { fill: C.key, stroke: C.keyEdge, r: 1.0, lw: 0.2 });
    if (k) for (const yy of [12.3, 13.9, 15.5]) line(ctx, [[bx + 2.6, yy], [bx + 7.4, yy]], C.white, 0.45);
    else { line(ctx, [[bx + 2.8, 15.6], [bx + 7.2, 11.6]], C.white, 0.45); line(ctx, [[bx + 4.8, 11.6], [bx + 7.2, 11.6], [bx + 7.2, 13.8]], C.white, 0.45); }
  }
}

export function drawMfd(P, S) {
  const V = viewMfd(S), ctx = P.ctx;
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, 305, 189.5);
  eisStrip(P, V);
  line(ctx, [[59.5, 0.5], [59.5, 189]], C.white, 0.45);
  mfdNavBar(P, V);
  mfdMap(P, V);
  mfdVsd(P, V);
  ctx.fillStyle = '#05060a'; ctx.fillRect(61.5, 171.5, 243.5, 18);
  iconBar(ctx, [70, 86, 102, 118], 180.5, 0, 'pdu');
  for (const a of [-2.2, 0, 2.2]) for (const b of [-2.2, 0, 2.2]) { ctx.fillStyle = C.white; ctx.fillRect(296 + a - 0.6, 180.5 + b - 0.6, 1.2, 1.2); }
  return V;
}
export function keyMfd(S) { return JSON.stringify(viewMfd(S)); }

// ================================================================== the SDUs (94 x 151 mm, portrait)
function radioStrip(P) {
  const ctx = P.ctx;
  box(ctx, 0.8, 0.8, 92.4, 25.8, { fill: '#15181e', stroke: '#2c313a', r: 1.4, lw: 0.25 });
  box(ctx, 2, 2.2, 14, 10, { fill: C.key, stroke: C.keyEdge, r: 1.0, lw: 0.2 });
  L(P, 'audio', 3.2, 6.6, 1.5, C.white, { cw: 0.4 });
  box(ctx, 2, 14, 14, 11, { fill: C.key, stroke: C.keyEdge, r: 1.0, lw: 0.2 });
  box(ctx, 6.6, 15.6, 4.8, 4.2, { fill: '#3a62b5', stroke: null, r: 0.5 });
  L(P, 'msgs', 9, 23.4, 1.4, C.white, { align: 'center', cw: 0.4 });
  // COM1 (green box, active) / STBY, MIC / MON, COM2 / STBY, XPDR code / mode
  L(P, 'com1', 18.5, 3.4, 1.3, C.white, { cw: 0.5 });
  box(ctx, 18, 4.2, 22, 6.4, { fill: '#0c1a0e', stroke: C.green, r: 0.8, lw: 0.35 });
  N(P, 'com1', '123.450', 29, 9.3, 3.6, C.green, { align: 'center' });
  L(P, 'stby', 18.5, 14.6, 1.3, C.white, { cw: 0.5 });
  N(P, 'com1s', '125.000', 29, 19.6, 3.6, '#e6f2f6', { align: 'center' });
  box(ctx, 42, 3.4, 10.5, 5.6, { fill: C.green, stroke: null, r: 1.4 });
  L(P, 'mic', 47.25, 7.2, 1.6, '#062a0a', { align: 'center', alpha: 1 });
  L(P, 'mon', 47.25, 14.4, 1.3, C.white, { align: 'center' });
  box(ctx, 42, 15.6, 10.5, 9.4, { fill: C.green, stroke: null, r: 1.4 });
  L(P, 'com1', 47.25, 19.8, 1.4, '#062a0a', { align: 'center', alpha: 1 }); L(P, 'com2', 47.25, 23.2, 1.4, '#062a0a', { align: 'center', alpha: 1 });
  L(P, 'com2', 55, 3.4, 1.3, C.white, { cw: 0.5 });
  N(P, 'com2', '121.500', 65.5, 9.3, 3.6, '#e6f2f6', { align: 'center' });
  L(P, 'guard', 65.5, 12.2, 1.2, C.white, { align: 'center', cw: 0.4 });
  L(P, 'stby', 55, 14.6, 1.3, C.white, { cw: 0.5 });
  N(P, 'com2s', '123.450', 65.5, 19.6, 3.6, '#e6f2f6', { align: 'center' });
  L(P, 'xpdr', 79, 3.4, 1.3, C.white, { cw: 0.5 });
  L(P, 'ident', 85.5, 9.0, 2.4, C.white, { align: 'center', cw: 0.55 });
  L(P, 'alt', 79, 14.6, 1.3, C.white, { cw: 0.5 });
  N(P, 'xpdr', '7000', 85.5, 19.6, 3.6, '#e6f2f6', { align: 'center' });
  L(P, 'alt', 85.5, 23.6, 1.2, C.white, { align: 'center' });
}

function sduFrame(P, sel) {
  const ctx = P.ctx;
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, 94, 151);
  radioStrip(P);
  ctx.fillStyle = '#06070a'; ctx.fillRect(0, 135, 94, 16);
  iconBar(ctx, [12, 29.5, 47, 64.5, 82], 143.2, sel, 'sdu');
}

export function drawSdu(P, S) {
  const V = viewSdu(S, P.side), ctx = P.ctx;
  if (P.side === 'L') {
    const c = P.cache.page || (P.cache.page = P.layer(() => {
    const ctx = P.ctx;
      sduFrame(P, 0);
      ctx.save(); ctx.translate(1, 29); fplList(P, 0, 0, 92, 13.6, 7); ctx.restore();
      box(ctx, 64, 29, 13, 7.2, { fill: C.key, stroke: C.keyEdge, r: 1.0, lw: 0.2 });
      L(P, 'map', 70.5, 33.8, 1.8, C.white, { align: 'center' });
      for (const y of [30.8, 32.6, 34.4]) line(ctx, [[81, y], [89, y]], C.white, 0.5);
      line(ctx, [[91.6, 42], [91.6, 128]], 'rgba(150,160,180,0.35)', 0.5);
      line(ctx, [[91.6, 44], [91.6, 70]], C.white, 0.8);
    }, 0, 0, 94, 151));
    P.blit(c, 0, 0);
    return V;
  }
  // sdu_R: the take-off data form [E: a Garmin performance page] -- the Environment knobs through the air data
  const c = P.cache.frame || (P.cache.frame = P.layer(() => {
    const ctx = P.ctx;
    sduFrame(P, 2);
    box(ctx, 1.5, 28.5, 91, 104.5, { fill: '#07080b', stroke: '#c9ccd2', r: 1.4, lw: 0.35 });
    line(ctx, [[5, 33], [8, 31], [8, 32.2], [11, 32.2], [11, 34.2], [8, 34.2], [8, 35.4], [5, 33]], C.white, 0.45);
    L(P, 'takeoffData', 47, 34.4, 2.2, C.white, { align: 'center', cw: 0.45 });
    for (const y of [31.6, 33.2, 34.8]) line(ctx, [[82, y], [89, y]], C.white, 0.5);
  }, 0, 0, 94, 151));
  P.blit(c, 0, 0);
  const keyBox = (x, y, w, h, label, val, col = C.cyan, unit = null, id = label) => {
    box(ctx, x, y, w, h, { fill: '#16181d', stroke: '#363b44', r: 1.0, lw: 0.2 });
    L(P, label, x + w / 2, y + 3.6, 1.45, C.white, { align: 'center', cw: 0.42 });
    N(P, 'tod_' + id, val, x + w / 2 + (unit ? -1.2 : 0), y + h - 2.0, 3.2, col, { align: 'center' });
    if (unit) L(P, unit, x + w / 2 + numWidth(val, 3.2) / 2 - 0.6, y + h - 2.0, 1.4, col, { cw: 0.55 });
  };
  const r0 = 38.5, rh = 15.2, cw2 = 43.5;
  keyBox(3.5, r0, cw2, 12.6, 'elev', V.elev, C.cyan, 'ft');
  keyBox(48.5, r0, cw2, 12.6, 'oat', `${sgn(V.oat) === '-' ? '-' : ''}${Math.abs(V.oat)}°`, C.cyan, 'C');
  keyBox(3.5, r0 + rh, cw2, 12.6, 'altimeter', V.baro, C.cyan, V.unit === 'hPa' ? 'hPa' : 'inHg');
  keyBox(48.5, r0 + rh, cw2, 12.6, 'wind', `${String(V.wd).padStart(3, '0')}°/${V.wk}`, C.cyan);
  keyBox(3.5, r0 + 2 * rh, cw2, 12.6, 'pa', V.pa, C.white, 'ft');
  keyBox(48.5, r0 + 2 * rh, cw2, 12.6, 'da', V.da, C.white, 'ft');
  keyBox(3.5, r0 + 3 * rh, cw2, 12.6, 'head', `${V.head >= 0 ? '' : '-'}${Math.abs(V.head)}`, C.white, 'kt');
  keyBox(48.5, r0 + 3 * rh, cw2, 12.6, 'cross', `${Math.abs(V.cross)}`, C.white, 'kt');
  keyBox(3.5, r0 + 4 * rh, cw2, 12.6, 'zfw', V.fuel, C.cyan, 'lb');
  keyBox(48.5, r0 + 4 * rh, cw2, 12.6, 'rwy', '24', C.white);
  // the EPECS take-off torque of the day (engine.js ratingShp: flat 44.3 psi, less when hot or high)
  box(ctx, 3.5, r0 + 5 * rh + 1, 88.5, 13, { fill: '#0c1a0e', stroke: C.green, r: 1.0, lw: 0.35 });
  L(P, 'toTrq', 6, r0 + 5 * rh + 6, 1.8, C.white, { cw: 0.45 });
  N(P, 'tod_rating', V.rating, 72, r0 + 5 * rh + 10.6, 4.4, C.green, { align: 'right' });
  L(P, 'psi', 73, r0 + 5 * rh + 10.6, 1.8, C.green, { cw: 0.55 });
  N(P, 'tod_isa', `${V.isa >= 0 ? '+' : '-'}${Math.abs(V.isa)}°`, 22, r0 + 5 * rh + 11, 2.6, C.white, { align: 'right' });
  L(P, 'isa', 6, r0 + 5 * rh + 11, 1.5, C.white);
  return V;
}
export function keySdu(S, side) { return JSON.stringify(viewSdu(S, side)); }

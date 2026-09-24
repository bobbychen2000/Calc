// Fitting the imported artist models (data/models/*.sfom) to the published dimensions of the type they stand for, and the
// ICAO designator -> (airframe, model) mapping. Pure data + arithmetic (no WebGL), so tools/models/check_dims.py can run
// exactly this code under node and compare the result with the manufacturers' documents.
//
// For every TYPES key that renders with a model (each TYPES key uses exactly one model, see TYPE_MODEL):
//   scale     uniform s = (published length of the type the model was built as) / (model length)
//   plugs     derived types are made by inserting (or removing) fuselage plugs in the model: one ahead of the wing and one
//             behind it. The plug stations are per model base (PLUG_AT, between the doors the documents show moving),
//             the plug lengths come from the documents: the forward plug is the station change of a door that lies between
//             the two plugs (e.g. 787 door 2: 15.32 -> 18.36 -> 21.41 m), else the main-gear station change; the aft plug
//             is the rest of the length change.
//   wing      when the type's published span differs from the model's by more than 0.5 %, the outer wing (outboard of the
//             engines) is stretched spanwise and the wing tip device translated rigidly (E175 long wing on the short-wing
//             model, A320neo family sharklet span on the fence-tip models, A330neo, 767-400ER, CRJ900 late build, ...).
//             The tip shape itself is the model's (a fence stays a fence): see docs/research/aircraft_models_check.md.
//   seating   gear-less models are placed so the door the bridge meets is where the documents put it: on the door-1 sill
//             when the source model has a door object (A320 family, A220-100, CRJ700/900, E-Jets), else on the published
//             fuselage top at door 1, else on the published overall height. The 737-800 model has its own gear.
//   docking   the jet bridge docks at the rendered door: the model's own door object where it has one (rendered station,
//             including scale and plugs), else the published door centre; floor at the published sill; the cab stops at the
//             rendered fuselage side at door height.
// Results are written onto the TYPES entry (T.fit, T.Hc, T.dockX1/2, T.dockSill/2, T.dockHW), which js/live/gates.js,
// js/live/aircraft.js and the procedural airframe read.
import { TYPES, SPEC, ICAO_TYPES } from './types.js';
import { MODEL_DIMS, MODEL_FEATURES } from '../../data/models/manifest.js';

// TYPES key -> model key (null: procedural airframe; no artist model of the 777 family is available)
export const TYPE_MODEL = {
  b736: 'b738', b737: 'b738', b738: 'b738', b739: 'b738', b37m: 'b738', b38m: 'b738', b39m: 'b738', b3xm: 'b738',
  a319: 'a319', a19n: 'a319', a320: 'a320', a20n: 'a320', a321: 'a321', a21n: 'a321',
  b752: 'b752', b753: 'b752', b762: 'b763', b763: 'b763', b764: 'b763',
  b772: null, b77l: null, b773: null, b77w: null, b779: null,
  b788: 'b788', b789: 'b788', b78x: 'b788', b744: 'b744', b748: 'b748',
  a332: 'a333', a333: 'a333', a338: 'a333', a339: 'a333', a359: 'a359', a35k: 'a359', a388: 'a388',
  bcs1: 'bcs1', bcs3: 'bcs3', e170: 'e170', e75l: 'e75l', e75s: 'e75l', e190: 'e190', e195: 'e190',
  crj2: 'crj2', crj7: 'crj7', crj9: 'crj9', md11: 'md11',
};
// model key -> TYPES key the model was built as (its published dimensions are the reference for the model's scale)
export const MODEL_BASE = { b738: 'b738', a319: 'a319', a320: 'a320', a321: 'a321', b788: 'b788', e170: 'e170', e75l: 'e75l', e190: 'e190', bcs1: 'bcs1', bcs3: 'bcs3',
  crj2: 'crj2', crj7: 'crj7', crj9: 'crj9', b752: 'b752', b763: 'b763', b744: 'b744', b748: 'b748', a333: 'a333', a359: 'a359', a388: 'a388', md11: 'md11' };
// ICAO designator -> { t: TYPES key, m: model key }
export const TYPE_MODELS = {};
for (const icao in ICAO_TYPES) TYPE_MODELS[icao] = { t: ICAO_TYPES[icao], m: TYPE_MODEL[ICAO_TYPES[icao]] ?? null };

// plug stations in the base airframe (m aft of the nose): [forward plug, aft plug]
export const PLUG_AT = {
  b738: [10.0, 26.0],   // between door 1 (5.03) and the wing root (~14.2) / between the wing TE (~21.6) and the aft door (31.88)
  b752: [15.4, 31.0],   // aft of door 2 (13.99, unchanged on the 757-300) and ahead of the wing / behind the wing, ahead of door 4 (38.23)
  b763: [10.8, 37.0],   // between door 1 (5.70) and the (optional) door 2 (15.96; the 767-400ER door 2 moves with the plug) / ahead of the aft door (42.55)
  b788: [10.8, 38.0],   // between door 1 (6.30) and door 2 (15.32) / between door 3 (32.39) and door 4 (43.56)
  a333: [11.8, 43.5],   // between door 1 (5.85) and door 2 (17.74) / between door 3 (35.96) and door 4 (50.96)
  a359: [12.8, 45.2],   // between door 1 (6.82) and door 2 (18.86) / between door 3 (37.93) and door 4 (52.55)
  e190: [9.0, 23.5],    // between door 1 (5.14) and the wing / between the wing TE and the aft door
};
const SPAN_TOL = 0.005, TIP = 0.8; // span fit threshold (fraction); rigidly translated wing-tip length (model m)

function plugsFor(t, base) {
  const T = SPEC[t], B = SPEC[base]; const dL = T.L - B.L;
  if (Math.abs(dL) < 0.3 || !PLUG_AT[base]) return null;
  const [a1, a2] = PLUG_AT[base];
  let d1 = null, by = 'main gear';
  for (let j = 0; j < Math.min(T.doors.length, B.doors.length); j++) {
    if (B.doors[j] > a1 && B.doors[j] < a2) { d1 = T.doors[j] - B.doors[j]; by = 'door ' + (j + 1); break; }
  }
  if (d1 === null) d1 = T.main[0] - B.main[0];
  return { at1: a1, at2: a2, d1: +d1.toFixed(3), d2: +(dL - d1).toFixed(3), by };
}
// fuselage section of model features F near station xm (model units): the most complete planar cut within +-2 m
// (a cut through a door opening, whose door is a separate object, misses skin triangles)
function secAt(F, xm) {
  const S = F && F.sec; if (!S) return null; const n = S.top.length, i0 = Math.round(xm / S.dx), w = Math.round(2 / S.dx);
  let best = null;
  for (let j = Math.max(0, i0 - w); j <= Math.min(n - 1, i0 + w); j++) {
    const t = S.top[j], b = S.bot[j], h = S.hw[j]; if (t == null || b == null || h == null || h < 0.3 * (t - b) / 2) continue;
    const q = (t - b) - 0.05 * Math.abs(j - i0) * S.dx; if (!best || q > best.q) best = { q, top: t, bot: b, hw: h };
  }
  return best;
}
// top of the fuselage (model units) over the forward fuselage (10-50 % of the length; 747/A380: the upper deck)
function crownOf(F, L) {
  const S = F && F.sec; if (!S) return null; let c = null;
  for (let j = Math.ceil(0.1 * L / S.dx); j <= Math.floor(0.5 * L / S.dx) && j < S.top.length; j++) {
    const t = S.top[j], b = S.bot[j], h = S.hw[j]; if (t == null || b == null || h == null || h < 0.3 * (t - b) / 2) continue;
    if (c == null || t > c) c = t;
  }
  return c;
}
function doorMesh(m) {
  const own = MODEL_FEATURES[m] && (MODEL_FEATURES[m].doors || []).find(d => d.side === 'L');
  if (own) return { ...own, from: m };
  for (const o of (MODEL_FEATURES[m] && MODEL_FEATURES[m].sameNose) || []) {       // identical nose section (e.g. E175 = E170)
    const d = MODEL_FEATURES[o] && (MODEL_FEATURES[o].doors || []).find(q => q.side === 'L');
    if (d) return { ...d, from: o };
  }
  return null;
}

// fit of TYPES[t] to model m; writes the result onto TYPES[t]
export function fitType(t, m) {
  const T = TYPES[t], S = SPEC[t], d = MODEL_DIMS[m], F = MODEL_FEATURES[m] || null; if (!T || !S || !d) return null;
  const base = MODEL_BASE[m], B = SPEC[base];
  const s0 = B.L / d.L;                                   // model units -> metres (published length of the model's own type)
  const pl = base !== t ? plugsFor(t, base) : null;
  const stretch = {};
  if (pl) Object.assign(stretch, { cut1: -pl.at1 / s0, cut2: -pl.at2 / s0, d1: pl.d1 / s0, d2: pl.d2 / s0 });
  const plugM = pl ? (pl.d1 + pl.d2) / s0 : 0;
  const s = T.L / (d.L + plugM);                          // = s0 when the plugs account for the whole length change
  // rendered station (m from the nose) of a model station xm (model units, positive aft)
  const rx = (xm) => s * (xm + (pl && xm > pl.at1 / s0 ? pl.d1 / s0 : 0) + (pl && xm > pl.at2 / s0 ? pl.d2 / s0 : 0));
  // wing span fit
  const semi = F ? F.wing.semi : d.span / 2; const want = S.span / s / 2; let wing = null;
  if (Math.abs(want / semi - 1) > SPAN_TOL) {
    const e = T.eng && T.eng.length ? T.eng[T.eng.length - 1] : null;
    const engOut = Math.max(F && F.wing.engOut ? F.wing.engOut : 0, e ? (e.z + e.r) / s : 0);
    const z0 = Math.max(engOut + 0.5 / s, 0.35 * semi), z1 = semi - TIP;
    if (z1 > z0 + 1) { wing = { z0: +z0.toFixed(3), z1: +z1.toFixed(3), dz: +(want - semi).toFixed(3), xMin: -0.8 * d.L }; stretch.wing = wing; }
  }
  // seating and the door the bridge docks to
  const dm = doorMesh(m); let Hc, seat;
  const x1m = dm ? dm.x : T.doors[0] / s;
  if (d.hasGear) { Hc = -d.low * s; seat = 'gear'; }
  else if (dm && T.sill != null) { Hc = T.sill - dm.ySill * s; seat = 'sill'; }
  else if (T.crown != null && crownOf(F, d.L) != null) { Hc = T.crown - crownOf(F, d.L) * s; seat = 'crown'; }
  else { Hc = T.H - d.H * s; seat = 'fin'; }
  Hc = +Hc.toFixed(3);
  const dockX1 = dm ? +rx(dm.x).toFixed(3) : T.doors[0];
  const dockSill = T.sill != null ? T.sill : Hc - 0.3 * d.R * s;
  // rendered half width of the fuselage at door 1, at door mid height (ellipse through the section's top, bottom, width)
  const sec = secAt(F, x1m);
  let dockHW = T.R;
  if (sec) {
    const yc = (sec.top + sec.bot) / 2, R = (sec.top - sec.bot) / 2, y = (dockSill - Hc) / s + 0.95 / s;
    dockHW = +(sec.hw * Math.sqrt(Math.max(0.05, 1 - ((y - yc) / R) ** 2)) * s).toFixed(3);
  }
  const top = crownOf(F, d.L);
  const fit = { model: m, base, s: +s.toFixed(5), s0: +s0.toFixed(5), plugs: pl, wing, stretch: Object.keys(stretch).length ? stretch : null, rx,
    Hc, seat, door: dm ? { name: dm.name, from: dm.from, x: dockX1, sill: +(Hc + dm.ySill * s).toFixed(3) } : null,
    renderedSpan: +(2 * (semi + (wing ? wing.dz : 0)) * s).toFixed(3), renderedL: +((d.L + plugM) * s).toFixed(3), renderedH: +(Hc + d.H * s).toFixed(3),
    renderedCrown: top != null ? +(Hc + top * s).toFixed(3) : null };
  T.fit = fit; T.Hc = Hc; T.dockX1 = dockX1; T.dockSill = dockSill; T.dockHW = dockHW;
  return fit;
}
// procedural airframes (no model) and every type's second-bridge door
function dockDefaults(T) {
  if (T.dockX1 == null) T.dockX1 = T.doors[0];
  if (T.dockSill == null) T.dockSill = T.sill ?? T.Hc - 0.3 * T.R;
  if (T.dockHW == null) T.dockHW = T.R;
  T.dockX2 = T.dock2 ? T.doors[T.dock2 - 1] : null; T.dockSill2 = T.dock2 ? (T.sill2 ?? T.dockSill) : null;
}
for (const t in TYPE_MODEL) { if (TYPE_MODEL[t]) fitType(t, TYPE_MODEL[t]); if (TYPES[t]) dockDefaults(TYPES[t]); }

// kept for callers of the old API: the fuselage/wing stretch of type t rendered with model m (null = none)
export function stretchFor(t, m) { const T = TYPES[t]; return T && T.fit && T.fit.model === m ? T.fit.stretch : null; }
export function seatType(t, m) { const T = TYPES[t]; if (T && !T.uniform && (!T.fit || T.fit.model !== m) && m && SPEC[t]) { fitType(t, m); dockDefaults(T); } }

// business jets: a uniformly scaled regional-jet airframe (T-tail, rear engines) at the type's published length.
// Lengths: manufacturers' published overall lengths (not re-verified here; the airframe is labelled generic in the UI).
export const BIZ_LEN = { GLF4: 26.92, GLF5: 29.39, GLF6: 30.41, G280: 20.3, GA5C: 29.4, GA6C: 30.4, GLEX: 30.3, GL5T: 29.5, GL7T: 33.8, CL30: 20.92, CL35: 20.92, CL60: 20.85,
  C56X: 15.79, C68A: 18.97, C700: 22.3, C750: 22.04, C25B: 15.6, C25C: 16.3, C560: 14.9, E55P: 15.9, E545: 19.7, E550: 20.7, E135: 26.33, E35L: 26.33,
  LJ45: 17.7, LJ60: 17.9, LJ75: 17.7, FA7X: 23.2, FA8X: 24.5, F900: 20.2, F2TH: 20.2, FA50: 18.5, H25B: 15.6, HDJT: 12.99, PC24: 16.85, BE40: 14.75 };
const NOSCALE = new Set(['sweep', 'dihedral', 'tcRoot', 'tcTip', 'top', 'wheels', 'flex', 'flat', 'noseTop', 'nose', 'pt', 'pb', 'pw', 'noseTip', 'dock2', 'spec', 'fit']);
function scaleObj(o, f) {
  if (Array.isArray(o)) return o.map(v => typeof v === 'number' ? v * f : (v && typeof v === 'object') ? scaleObj(v, f) : v);
  const r = {};
  for (const k in o) { const v = o[k]; r[k] = NOSCALE.has(k) ? v : typeof v === 'number' ? v * f : (v && typeof v === 'object') ? scaleObj(v, f) : v; }
  return r;
}
export function typeForIcao(icao) {
  if (!icao) return null;
  if (TYPE_MODELS[icao]) return TYPE_MODELS[icao];
  if (BIZ_LEN[icao]) {
    const key = 'biz_' + icao;
    if (!TYPES[key]) {
      const B = TYPES.crj2, f = BIZ_LEN[icao] / B.L;
      const T = scaleObj(B, f); T.name = icao; T.key = key; T.cls = 'B'; T.uniform = true; T.wing.y = B.wing.y; T.win.forEach((w, i) => { w.y = B.win[i].y * f; });
      T.fit = B.fit ? { ...B.fit, s: B.fit.s * f, stretch: null } : null;
      TYPES[key] = T;
    }
    return { t: key, m: 'crj2', generic: 'business jet' };
  }
  return null;
}

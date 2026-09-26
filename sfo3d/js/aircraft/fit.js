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
//   seating   models with their own gear stand on it (FG 737-800, 777; the 777's extended oleos compressed to the published
//             fuselage height); gear-less models are placed so the door the bridge meets is where the documents put it: on the door-1 sill
//             when the source model has a door object (A320 family, A220-100, CRJ700/900, E-Jets), else on the published
//             fuselage top at door 1, else on the published overall height. The 737-800 model has its own gear.
//   docking   the jet bridge docks at the rendered door: the model's own door object where it has one (rendered station,
//             including scale and plugs), else the published door centre; floor at the published sill; the cab stops at the
//             rendered fuselage side at door height.
// Results are written onto the TYPES entry (T.fit, T.Hc, T.dockX1/2, T.dockSill/2, T.dockHW), which js/live/gates.js,
// js/live/aircraft.js and the procedural airframe read.
import { TYPES, SPEC, ICAO_TYPES } from './types.js';
import { MODEL_DIMS, MODEL_FEATURES } from '../../data/models/manifest.js';
// x shift of a vertex at model x (forward positive, aft negative) by the fuselage plug at station c (model x) of length
// d: a plug (d > 0) moves everything aft of c aft by d; a negative plug (shorter type) removes the section [c + d, c):
// with bl = 0 its vertices collapse onto c, with a blend bl > 0 the section plus bl is compressed linearly onto bl (no
// step where the removed section reaches into a taper); everything aft of it moves forward by |d|. Used by
// js/live/models.js applyStretch; Python port: tools/liveries/common.py apply_stretch.
export function plugShift(x, c, d, bl = 0) {
  if (d >= 0) return x < c ? -d : 0;
  const D = -d;
  if (x >= c) return 0;
  if (x <= c - D - bl) return D;
  const t = (c - x) / (D + bl);
  return (c - t * bl) - x;
}

// TYPES key -> model key (null: procedural airframe). 777 family: FlightGear 777-200ER (b772) and 777-300ER (b77w) models
// (FGMEMBERS/777, GPL-2.0; tools/convert_models.py): the plain-tip wing types on the -200ER, the raked-tip ones on the -300ER
export const TYPE_MODEL = {
  b736: 'b738', b737: 'b738', b738: 'b738', b739: 'b738', b37m: 'b738', b38m: 'b738', b39m: 'b738', b3xm: 'b738',
  a319: 'a319', a19n: 'a319', a320: 'a320', a20n: 'a320', a321: 'a321', a21n: 'a321',
  b752: 'b752', b753: 'b752', b762: 'b763', b763: 'b763', b764: 'b763',
  b772: 'b772', b773: 'b772', b77l: 'b77w', b77w: 'b77w', b779: 'b77w',
  b788: 'b788', b789: 'b788', b78x: 'b788', b744: 'b744', b748: 'b748',
  a332: 'a333', a333: 'a333', a338: 'a333', a339: 'a333', a359: 'a359', a35k: 'a359', a388: 'a388',
  bcs1: 'bcs1', bcs3: 'bcs3', e170: 'e170', e75l: 'e75l', e75s: 'e75l', e190: 'e190', e195: 'e190',
  crj2: 'crj2', crj7: 'crj7', crj9: 'crj9', md11: 'md11',
};
// model key -> TYPES key the model was built as (its published dimensions are the reference for the model's scale)
export const MODEL_BASE = { b738: 'b738', a319: 'a319', a320: 'a320', a321: 'a321', b788: 'b788', e170: 'e170', e75l: 'e75l', e190: 'e190', bcs1: 'bcs1', bcs3: 'bcs3',
  crj2: 'crj2', crj7: 'crj7', crj9: 'crj9', b752: 'b752', b763: 'b763', b744: 'b744', b748: 'b748', a333: 'a333', a359: 'a359', a388: 'a388', md11: 'md11',
  b772: 'b772', b77w: 'b77w' };
// ICAO designator -> { t: TYPES key, m: model key }
export const TYPE_MODELS = {};
for (const icao in ICAO_TYPES) TYPE_MODELS[icao] = { t: ICAO_TYPES[icao], m: TYPE_MODEL[ICAO_TYPES[icao]] ?? null };

// plug stations in the base airframe (m aft of the nose): [forward plug, aft plug]. The livery atlas splits the mesh at
// these stations (tools/liveries/atlas.py plug bands), so only a 2 cm band stretches; on models that keep their artist
// glass windows the stations lie in a pier between two windows (a window is never stretched).
export const PLUG_AT = {
  b738: [10.0, 26.0],   // between door 1 (5.03) and the wing root (~14.2) / between the wing TE (~21.6) and the aft door (31.88)
  b752: [15.24, 30.96], // aft of door 2 (13.99, unchanged on the 757-300) and ahead of the wing / behind the wing, ahead of door 4 (38.23); both in a window pier of the kept artist glass (tools/liveries/windows.py)
  b763: [10.8, 37.0],   // between door 1 (5.70) and the (optional) door 2 (15.96; the 767-400ER door 2 moves with the plug) / ahead of the aft door (42.55)
  b788: [10.8, 38.0],   // between door 1 (6.30) and door 2 (15.32) / between door 3 (32.39) and door 4 (43.56)
  a333: [11.8, 43.5],   // between door 1 (5.85) and door 2 (17.74) / between door 3 (35.96) and door 4 (50.96)
  a359: [12.8, 45.2],   // between door 1 (6.82) and door 2 (18.86) / between door 3 (37.93) and door 4 (52.55)
  e190: [9.22, 23.54],  // between door 1 (5.14) and the wing / between the wing TE and the aft door; in window piers of the kept artist glass
  b772: [20.0, 34.5],   // between door 2 (17.07) and the wing root LE (22.3 on the model) / between the wing TE (32.4) and door 3 (36.33)
  b77w: [25.0, 42.0],   // between door 2 (17.07) and the wing root LE (27.5 on the model) / between the wing TE (37.6) and door 4 (46.46)
};
// models whose door numbering changes between the types (the 777-300 adds door 3 over the wing): the forward plug is the
// main-gear station change (777-300 vs -200: 37.11 - 31.77 = 5.34 m ahead of the wing), not a door's
const PLUG_BY_GEAR = new Set(['b772', 'b77w']);
// models whose own gear is modelled with extended oleos (FG 777: fuselage 0.3-0.56 m too high on its wheels)
const OLEO = new Set(['b772', 'b77w']);
const SPAN_TOL = 0.005, TIP = 0.8; // span fit threshold (fraction); rigidly translated wing-tip length (model m)
// wing-tip devices the source model lacks, drawn as procedural geometry at the model's own wing tip (js/live/aircraft.js,
// js/aircraft/model.js tipDeviceData; review round 1): A320neo family sharklets on the fence-tip FAM A319/A320/A321
// models, the 737 MAX Advanced Technology split-tip winglet on the FG 737-800 model (whose blended winglet is folded
// away: TIP_CUT). lat = the device's lateral extent (m), subtracted from the published span for the wing span fit;
// height = the device height of the type table (TYPES wing.tipH).
export const TIP_ADD = { a19n: 'sharklet', a20n: 'sharklet', a21n: 'sharklet', b37m: 'split', b38m: 'split', b39m: 'split', b3xm: 'split' };
const TIP_LAT = { sharklet: 0.55, split: 0.5 };
// the 737-800 model's blended winglet (FG winglet.ac): vertices outboard of |z| 17.5 and above y 0.75 (model units; the
// upper-skin profile of the tip rises from 0.72 at 17.45 to 2.47 at 17.85) are folded onto the tip
const TIP_CUT = { b738: { z0: 17.5, y0: 0.75, zTo: 17.62, yTo: 0.6 } };
// 737 MAX: LEAP-1B nacelles in place of the model's CFM56-7B ones, scaled radially by the fan-diameter ratio (69.4 in / 61 in,
// CFM International LEAP-1B and CFM56-7B data) about the nacelle's lowest line, so the ground clearance stays the model's
const ENG_SCALE = { b37m: 1.14, b38m: 1.14, b39m: 1.14, b3xm: 1.14 };

function plugsFor(t, base) {
  const T = SPEC[t], B = SPEC[base]; const dL = T.L - B.L;
  if (Math.abs(dL) < 0.3 || !PLUG_AT[base]) return null;
  const [a1, a2] = PLUG_AT[base];
  let d1 = null, by = 'main gear';
  if (!PLUG_BY_GEAR.has(base)) for (let j = 0; j < Math.min(T.doors.length, B.doors.length); j++) {
    if (B.doors[j] > a1 && B.doors[j] < a2) { d1 = T.doors[j] - B.doors[j]; by = 'door ' + (j + 1); break; }
  }
  if (d1 === null) d1 = T.main[0] - B.main[0];
  const d2 = +(dL - d1).toFixed(3);
  // a shorter aft fuselage: the removed section behind the wing reaches into the start of the tail taper on these
  // models (737-800 model: keel 0.2 m higher at 28.8 m than at 26.0 m), so instead of a hard cut the section plus a blend
  // of up to 3 m is compressed onto the blend length (no step in the skin); the blend ends 0.6 m ahead of the next door
  let bl2 = 0;
  if (d2 < 0) { const nd = B.doors.find(x => x > a2); bl2 = Math.max(0, Math.min(3.0, (nd != null ? nd - 0.6 : a2 + 10) - (a2 - d2))); }
  return { at1: a1, at2: a2, d1: +d1.toFixed(3), d2, bl2: +bl2.toFixed(3), by };
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
// top of the fuselage (model units) over the forward fuselage (10-50 % of the length; 747/A380: the upper deck). The top
// profile is first median-filtered over 5 m so a short dorsal hump or antenna fairing is not taken for the crown (A220-300
// model: a hump of +0.28 m at 12 m seated the aircraft 0.28 m too low, review round 1); the 747 / A380 upper decks are
// longer than the filter and are kept.
function crownOf(F, L) {
  const S = F && F.sec; if (!S) return null;
  const ok = (j) => { const t = S.top[j], b = S.bot[j], h = S.hw[j]; return t != null && b != null && h != null && h >= 0.3 * (t - b) / 2; };
  const w = Math.max(1, Math.round(2.5 / S.dx)); let c = null;
  for (let j = Math.ceil(0.1 * L / S.dx); j <= Math.floor(0.5 * L / S.dx) && j < S.top.length; j++) {
    if (!ok(j)) continue;
    const win = []; for (let i = j - w; i <= j + w; i++) if (i >= 0 && i < S.top.length && ok(i)) win.push(S.top[i]);
    win.sort((a, b) => a - b); const t = win[win.length >> 1];
    if (c == null || t > c) c = t;
  }
  return c;
}
// lowest skin (model units) above model station st (positive aft) and lateral |z| (tools/models/model_features.py underside)
function underAt(F, st, z) {
  const U = F && F.under; if (!U) return null;
  const i = Math.round((st - U.s0) / U.ds), j = Math.round(Math.abs(z) / U.dz); let best = null;
  for (let a = i - 1; a <= i + 1; a++) for (let b = j - 1; b <= j + 1; b++) {
    const r = U.y[a]; const v = r && r[b]; if (v != null && (best == null || v < best)) best = v;
  }
  return best;
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
  if (pl) Object.assign(stretch, { cut1: -pl.at1 / s0, cut2: -pl.at2 / s0, d1: pl.d1 / s0, d2: pl.d2 / s0, bl2: pl.bl2 / s0 });
  const plugM = pl ? (pl.d1 + pl.d2) / s0 : 0;
  const s = T.L / (d.L + plugM);                          // = s0 when the plugs account for the whole length change
  // rendered station (m from the nose) of a model station xm (model units, positive aft)
  // (stations inside a removed section map onto the plug station or the blend, plugShift above)
  const sh = (st, a, dd, bl = 0) => -plugShift(-st, -a, dd, bl);
  const rx = (xm) => s * (xm + (pl ? sh(xm, pl.at1 / s0, pl.d1 / s0) + sh(xm, pl.at2 / s0, pl.d2 / s0, pl.bl2 / s0) : 0));
  // wing span fit
  // 757: the ACAP span (38.05 m) is the plain wing; the model carries blended winglets (fitted to most SFO 757s) whose span
  // is in no primary document here (APB publishes weights only). The wing is fitted up to the winglet root (model |z|
  // 18.55, measured on the model's upper-skin profile: the skin rises 0.5 m within 0.25 m outboard of it), so the plain wing
  // has the documented span and the winglet adds its own (artist) extent (review round 1: squeezing the whole tip to
  // 38.05 m made a winglet aircraft 3 m narrower than any real one)
  const WROOT = { b752: 18.55 };
  const cut = TIP_ADD[t] && TIP_CUT[m];
  if (cut) stretch.tipCut = cut;
  if (ENG_SCALE[t] && TIP_CUT[m]) stretch.engScale = { k: ENG_SCALE[t] };
  const semi = WROOT[m] && S.spanNoTip ? WROOT[m] : cut ? cut.zTo : F ? F.wing.semi : d.span / 2;
  const want = (S.span / 2 - (TIP_ADD[t] ? TIP_LAT[TIP_ADD[t]] : 0)) / s; let wing = null;
  if (Math.abs(want / semi - 1) > SPAN_TOL) {
    const e = T.eng && T.eng.length ? T.eng[T.eng.length - 1] : null;
    const engOut = Math.max(F && F.wing.engOut ? F.wing.engOut : 0, e ? (e.z + e.r) / s : 0);
    const z0 = Math.max(engOut + 0.5 / s, 0.35 * semi), z1 = semi - TIP;
    if (z1 > z0 + 1) { wing = { z0: +z0.toFixed(3), z1: +z1.toFixed(3), dz: +(want - semi).toFixed(3), xMin: -0.8 * d.L }; stretch.wing = wing; }
  }
  // seating and the door the bridge docks to
  const dm = doorMesh(m); let Hc, seat;
  const x1m = dm ? dm.x : T.doors[0] / s;
  if (d.hasGear) {
    Hc = -d.low * s; seat = 'gear';
    // FlightGear gear is modelled with the oleos extended (the simulator compresses them): where the model standing on its
    // own gear puts the fuselage top more than 0.15 m above the published height, the gear (zone 3) is moved up by the
    // excess (oleo compression; the strut tops disappear into the wing / fairing) and the airframe comes down onto it
    const top0 = crownOf(F, d.L);
    if (S.crown && top0 != null && OLEO.has(m)) {
      const ex = Hc + top0 * s - (S.crown[0] + S.crown[1]) / 2;
      if (ex > 0.15) { stretch.gearUp = +(ex / s).toFixed(3); Hc -= ex; seat = 'gear (oleos compressed ' + ex.toFixed(2) + ' m)'; }
    }
  }
  else if (dm && T.sill != null) { Hc = T.sill - dm.ySill * s; seat = 'sill'; }
  else if (T.crown != null && crownOf(F, d.L) != null) { Hc = T.crown - crownOf(F, d.L) * s; seat = 'crown'; }
  else { Hc = T.H - d.H * s; seat = 'fin'; }
  // engine ground clearance: the FAM A330 / 787 / 747-8 / A220-300 models are deeper below the fuselage centre line than
  // the real aircraft (A330-300 model: crown-seated, engines at 0.12 m against N1 0.69-0.79 m, belly fairing 0.5 m low,
  // review round 1). Where the type's published engine clearance (SPEC engClr, the manufacturer's ground-clearance table)
  // is not met, everything below the centre line is compressed vertically by k so the lowest engine point sits at the
  // middle of the published range (A330-300: k 0.85 also brings the belly fairing to 1.81 m against BF1 1.85-1.86 m).
  // Types without a table use the factor of their model's own type. Not for models on their own gear or seated on a door.
  // wing / tailplane dihedral: the FAM A330 wing tip renders 0.8 m below W1 and its tailplane tip 0.5 m below HT (AC A330
  // FIGURE-2-3-0-991-001-A01; review round 1). Where SPEC carries tipClr / htClr (the model's own type's), the wing outboard
  // of the fuselage side (and the tailplane outboard of 0.8 m) is sheared up linearly with |z| so its tip meets the table
  const Fw = F && F.wing, SB = SPEC[base] || {};
  const TC = S.tipClr || SB.tipClr, HC = S.htClr || SB.htClr;
  const hwM = F && F.sec ? (F.sec.hw.filter(v => v != null).sort((a, b) => a - b)[Math.floor(F.sec.hw.filter(v => v != null).length * 0.8)] || 2) : 2;
  let lift = null;
  if (!d.hasGear && Fw && TC && Fw.tipY != null) {
    const dy = (TC[0] + TC[1]) / 2 - (Hc + Fw.tipY * s);
    if (Math.abs(dy) > 0.2) lift = { z0: +hwM.toFixed(3), t: +(dy / s / (Fw.semi - hwM)).toFixed(5), xMin: +(-0.8 * d.L).toFixed(3) };
  }
  let hlift = null;
  if (!d.hasGear && Fw && HC && Fw.htY != null && Fw.htSemi) {
    const dy = (HC[0] + HC[1]) / 2 - (Hc + Fw.htY * s);
    if (Math.abs(dy) > 0.2) hlift = { z0: 0.8, t: +(dy / s / (Fw.htSemi - 0.8)).toFixed(5), xMax: +(-0.8 * d.L).toFixed(3) };
  }
  if (lift) stretch.wingLift = lift;
  if (hlift) stretch.htLift = hlift;
  let squash = null;
  const engZ = T.eng && T.eng.length ? T.eng[0].z / s : 0;
  const eL = F && F.wing && F.wing.engLow != null ? F.wing.engLow + (lift ? lift.t * Math.max(0, engZ - lift.z0) : 0) : null;
  if (!d.hasGear && seat !== 'sill' && eL != null && eL < 0) {
    const C = S.engClr || (SPEC[base] && SPEC[base].engClr);
    if (C) {
      const tgt = (C[0] + C[1]) / 2, now = Hc + eL * s;
      if (now < C[0]) { const k = Math.max(0.75, Math.min(1, (Hc - tgt) / (-eL * s))); if (k < 0.999) { squash = { y0: 0, k: +k.toFixed(4) }; stretch.squash = squash; } }
    }
  }
  const yR = (y) => (squash && y < squash.y0 ? squash.y0 + (y - squash.y0) * squash.k : y);   // model y after the compression
  Hc = +Hc.toFixed(3);
  const dockX1 = dm ? +rx(dm.x).toFixed(3) : T.doors[0];
  // cab floor: the published sill, except on a model standing on its own gear whose door object sits elsewhere (FG
  // 737-800: the artist's door 1L sill is 0.38-0.53 m above the published 2.59-2.74 m, review round 1): the bridge meets the
  // door that is drawn (rendered sill), so cab floor and door outline agree; the deviation is recorded by check_dims
  const dockSill = (seat === 'gear' && dm) ? +(Hc + dm.ySill * s).toFixed(3) : T.sill != null ? T.sill : Hc - 0.3 * d.R * s;
  // rendered half width of the fuselage at door 1, at door mid height (ellipse through the section's top, bottom, width)
  const sec = secAt(F, x1m);
  let dockHW = T.R;
  if (sec) {
    const yc = (sec.top + sec.bot) / 2, R = (sec.top - sec.bot) / 2, y = (dockSill - Hc) / s + 0.95 / s;
    dockHW = +(sec.hw * Math.sqrt(Math.max(0.05, 1 - ((y - yc) / R) ** 2)) * s).toFixed(3);
  }
  const top = crownOf(F, d.L);
  // fin height fit: where the model's fin top misses the published overall height (the artist's fin is too short or too
  // tall relative to the fuselage, e.g. FAM A330/787, FG 737-800), the fin (everything above the fuselage top aft of
  // 60 % of the length, except engines, pylons and gear) is scaled vertically about the fuselage top so that its height
  // above the fuselage top is the published one: mid(H) - mid(crown) where the document gives the fuselage top, else
  // mid(H) - the rendered fuselage top.
  let fin = null;
  if (top != null && S.H) {
    const Hr = Hc + d.H * s, [h0, h1] = S.H, tol = 0.005 * (h0 + h1) / 2;
    if (Hr < h0 - tol || Hr > h1 + tol) {
      const want = (h0 + h1) / 2 - (S.crown ? (S.crown[0] + S.crown[1]) / 2 : Hc + top * s);
      const k = want / ((d.H - top) * s);
      if (k > 0.7 && k < 1.4) { fin = { yF: +top.toFixed(3), xF: +(-0.6 * d.L).toFixed(3), k: +k.toFixed(4) }; stretch.fin = fin; }
    }
  }
  const finTop = fin ? top + (d.H - top) * fin.k : d.H;
  const fit = { model: m, base, s: +s.toFixed(5), s0: +s0.toFixed(5), plugs: pl, wing, stretch: Object.keys(stretch).length ? stretch : null, rx,
    Hc, seat, fin, squash, tipAdd: TIP_ADD[t] || null, door: dm ? { name: dm.name, from: dm.from, x: dockX1, sill: +(Hc + dm.ySill * s).toFixed(3) } : null,
    renderedSpan: +(2 * ((cut ? cut.zTo : F ? F.wing.semi : d.span / 2) + (wing ? wing.dz : 0)) * s + (TIP_ADD[t] ? 2 * TIP_LAT[TIP_ADD[t]] : 0)).toFixed(3), renderedL: +((d.L + plugM) * s).toFixed(3), renderedH: +(Hc + finTop * s).toFixed(3),
    renderedCrown: top != null ? +(Hc + top * s).toFixed(3) : null };
  // rendered engine clearance and the skin above the main gear (the procedural struts of gear-less models reach into it)
  fit.engClear = eL != null ? +(Hc + yR(eL) * s).toFixed(3) : null;
  if (!d.hasGear && T.xMain != null) {
    let lo = -10, hi = d.L + 20; for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2; if (rx(m) < T.xMain) lo = m; else hi = m; }
    const u = underAt(F, (lo + hi) / 2, (S.track || T.track || 6) / 2 / s);
    fit.gearTop = u != null ? +(Hc + yR(u) * s).toFixed(3) : null;
  }
  T.fit = fit; T.Hc = Hc; T.dockX1 = dockX1; T.dockSill = dockSill; T.dockHW = dockHW;
  return fit;
}
// procedural airframes (no model) and every type's second-bridge door
function dockDefaults(T) {
  if (T.dockX1 == null) T.dockX1 = T.doors[0];
  if (T.dockSill == null) T.dockSill = T.sill ?? T.Hc - 0.3 * T.R;
  if (T.dockHW == null) T.dockHW = T.R;
  T.dockX2 = T.dock2 ? T.doors[T.dock2 - 1] : null; T.dockSill2 = T.dock2 ? (T.sill2 ?? T.dockSill) : null;
  // A380 upper-deck door U1L for the upper-deck bridges (js/live/gates.js door 3): Airbus AC380 Dec 01/25
  // FIGURE-2-7-0-991-002 (U1 20.94 m from the nose) and FIGURE-2-3-0-991-001 (U1 sill 7.87-7.89 m at MRW)
  if (T.key === 'a388') { T.dockX3 = 20.94; T.dockSill3 = 7.88; }
}
for (const t in TYPE_MODEL) { if (TYPE_MODEL[t]) fitType(t, TYPE_MODEL[t]); if (TYPES[t]) dockDefaults(TYPES[t]); }

// kept for callers of the old API: the fuselage/wing stretch of type t rendered with model m (null = none)
export function stretchFor(t, m) { const T = TYPES[t]; return T && T.fit && T.fit.model === m ? T.fit.stretch : null; }
export function seatType(t, m) { const T = TYPES[t]; if (T && !T.uniform && (!T.fit || T.fit.model !== m) && m && SPEC[t]) { fitType(t, m); dockDefaults(T); } }

// business jets: a uniformly scaled regional-jet airframe (T-tail, rear engines) at the type's published length.
// Lengths: manufacturers' published overall lengths (not re-verified here; the airframe is labelled generic in the UI).
export const BIZ_LEN = { GLF4: 26.92, GLF5: 29.39, GLF6: 30.41, G280: 20.3, GA5C: 29.4, GA6C: 30.4, GLEX: 30.3, GL5T: 29.5, GL7T: 33.8, CL30: 20.92, CL35: 20.92, CL60: 20.85,
  C56X: 15.79, C68A: 18.97, C700: 22.3, C750: 22.04, C25B: 15.6, C25C: 16.3, C560: 14.9, E55P: 15.9, E545: 19.7, E550: 20.7, E135: 26.33, E35L: 26.33,
  LJ45: 17.7, LJ60: 17.9, LJ75: 17.7, FA7X: 23.2, FA8X: 24.5, F900: 20.2, F2TH: 20.2, FA50: 18.5, H25B: 15.6, PC24: 16.85, BE40: 14.75 };
// (HDJT removed, review round 1: the HondaJet's engines are over the wing; a rear-engine airframe misrepresents it: marker.
// The generic airframe is drawn without a cabin-window row: js/live/aircraft.js, uNoCabin for T.uniform)
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
      T.fit = B.fit ? { ...B.fit, s: B.fit.s * f } : null;
      TYPES[key] = T;
    }
    return { t: key, m: 'crj2', generic: 'business jet' };
  }
  return null;
}

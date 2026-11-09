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
//             A model's blended winglet (WINGLET: 757) is not stretched with the wing: the plain wing is fitted to the
//             plain span and the winglet canted out to the published winglet span.
//   seating   models with their own gear stand on it (FG 737-800, 777; the 777's extended oleos compressed to the published
//             fuselage height), pitched nose-down about the main-gear contact so the nose tyre touches the ground too (T.fit.pitch,
//             applied by js/live/aircraft.js placement(); the FG models stand level with the nose tyre 0.165 m (737) / 0.18 m
//             (777) up, review 4 Nov 2026; the ACAPs show both types nose-down at rest, e.g. 737-800 entry door 1 sill
//             2.59-2.74 m vs door 2 2.97-3.12 m, D6-58325-7 Rev C §2.3.2 p.2-18: ~0.8 deg); gear-less models are placed so the door the bridge meets is where the documents put it: on the door-1 sill
//             when the source model has a door object (A320 family, A220-100, CRJ700/900, E-Jets), else on the published
//             fuselage top at door 1, else on the published overall height. The 737 family on the FG 737-800 (its gear
//             drawn with the oleos fully extended) stands in a stance fitted to the ACAP's door and cargo-door rows: main oleo
//             compressed, pitch, nose leg compressed (NG) or extended (MAX) (STANCE_FIT, close-out round 3 of 7 Nov 2026).
//   docking   the jet bridge docks at the rendered door: the model's own door object where it has one (rendered station,
//             including scale and plugs), else the published door centre; floor at the published sill; the cab stops at the
//             rendered fuselage side at the door's station: the widest skin over the door opening (sill to sill + 1.9 m),
//             measured on planar cuts of the mesh (hwAt) for door 1 (T.dockHW), the second bridge's door (T.dockHW2) and the
//             A380 upper-deck door (T.dockHW3); T.dockSkin holds the skin profile from the sill up for each.
// Results are written onto the TYPES entry (T.fit, T.Hc, T.dockX1/2/3, T.dockSill/2/3, T.dockHW/2/3, T.dockSkin), which js/live/gates.js,
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
  b738: [11.0, 26.0],   // between the forward cargo door (model 9.65-10.65) and the wing-body fairing (13.6) / between the wing TE (~21.6) and the aft cargo door (26.14); removed sections: PLUG_REM
  b752: [15.24, 30.96], // aft of door 2 (13.99, unchanged on the 757-300) and ahead of the wing / behind the wing, ahead of door 4 (38.23); both in a window pier of the kept artist glass (tools/liveries/windows.py)
  b763: [10.8, 37.0],   // between door 1 (5.70) and the (optional) door 2 (15.96; the 767-400ER door 2 moves with the plug) / ahead of the aft door (42.55)
  b788: [10.8, 38.0],   // between door 1 (6.30) and door 2 (15.32) / between door 3 (32.39) and door 4 (43.56)
  a333: [11.8, 43.5],   // between door 1 (5.85) and door 2 (17.74) / between door 3 (35.96) and door 4 (50.96)
  a359: [12.8, 45.2],   // between door 1 (6.82) and door 2 (18.86) / between door 3 (37.93) and door 4 (52.55)
  e190: [9.22, 23.54],  // between door 1 (5.14) and the wing / between the wing TE and the aft door; in window piers of the kept artist glass
  b772: [20.0, 34.5],   // between door 2 (17.07) and the wing root LE (22.3 on the model) / between the wing TE (32.4) and door 3 (36.33)
  b77w: [25.0, 42.0],   // between door 2 (17.07) and the wing root LE (27.5 on the model) / between the wing TE (37.6) and door 4 (46.46)
};
// stations of REMOVED sections (a shorter type: negative plug, the section [at, at + |d|] collapses) where they differ from
// PLUG_AT, and the station of the next feature the aft blend must stop short of (0.6 m ahead). FG 737-800 (close-out round 3
// of 7 Nov 2026): its cargo-door objects lie at 9.65-10.65 (forward) and 26.14-27.14 m (aft); with the plugs at 10.0 / 26.0
// the 737-900ER / -9 / -10 drew the forward cargo door stretched over the plug (2.6-3.8 m long) and the 737-600 / -700 / -7 lost
// up to half of both cargo doors in the removed sections. The ACAP door tables put both cargo doors' changes on the same side:
// D6-38A004 Rev K §2.7.1 keeps the forward cargo door at 8.53 m on every MAX (the forward plug is aft of it) and moves the aft
// one by both plugs (24.05 / 27.97 / 30.61 / 32.28 m: the aft plug is ahead of it). So: inserted plugs at 11.0 (aft of the
// forward cargo door, ahead of the wing-body fairing at 13.6) / 26.0 m (ahead of the aft cargo door); removed sections from
// 10.7 m (forward) and from 22.2 m (aft of the fairing, which ends at ~22 m; the blend stops 0.6 m ahead of the aft cargo
// door at 26.1). Open for the 737-600 (rare at SFO: none in the recorded hours; close-out round 3, fix round 2, v5): its 4.37 m
// forward removal (the ACAP wheelbase change) cannot fit between the forward cargo door (ends 10.65) and the fairing (13.6),
// so it takes 1.45 m of the fairing's front (keel step -0.06 m at 10.7 m), and its 3.86 m aft removal leaves no room for a
// blend between the fairing and the aft cargo door (hard keel step +0.05 m at 22.2 m). Its nacelles, which the forward
// removal reached by 1.3 m (they rendered 2.35 m long instead of 3.57 m), now move rigidly with the wing (js/aircraft/stretch.js)
const PLUG_REM = { b738: { at: [10.7, 22.2], next: 26.1 } };
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
// types drawn with the plain wing: the model's winglet is folded away (TIP_CUT) with no device in its place, and the span
// fit takes the plain tip to SPEC.span. 737-600: the ACAP's baseline -600 has no winglets ('Winglets are installed on some
// 737-600 airplanes as an after-market airline option', D6-58325-7 Rev C §1.2 p.1-5 text; SPEC b736 span 34.32 = §2.2.1
// without winglets). Close-out round 4 (verifier finding 8): the 737-600 drew the FG 737-800's blended winglet at the
// artist's height, its wing shortened 0.71 m a side so the winglet tips met the plain-wing span. Which -600 airframes carry
// the aftermarket winglet is per registration and not sourced here (open).
const TIP_PLAIN = new Set(['b736']);
// how the plain tip is drawn (close-out round 4, fix round 2, verifier finding 4: TIP_CUT folds the winglet to a fixed
// height, y 0.6 at |z| <= 17.62, and leaves the winglet-root fillet's upturn (|z| 17.5-17.62, up to y 0.75-0.95) standing:
// on the 737-600 a 0.15-0.2 m upturned hook painted with the winglet art, with the navigation-light anchor on top of it).
// Every vertex outboard of z0 is folded onto the wing's own tip section: |z| to zTo, the station clamped to the tip chord
// and the height clamped between the section's lower and upper skin lines lo / up at that station (piecewise linear
// through the knots x). Measured on the FG 737-800 conversion (refs/cache/models_orig/b738.sfom, model units): the
// outboard skin loop at |z| 17.38-17.46, leading edge x -23.622 (y 0.552), trailing edge x -24.636 (y 0.518); the
// fillet's upturn starts outboard of |z| 17.46. The folded winglet lies on the tip's edge (zero-area triangles inside the
// section), no part of it above the upper skin.
const TIP_FOLD = { b738: { z0: 17.45, zTo: 17.45, x: [-24.636, -24.414, -24.059, -23.86, -23.712, -23.655, -23.622],
  lo: [0.518, 0.516, 0.521, 0.52, 0.526, 0.537, 0.552], up: [0.518, 0.577, 0.597, 0.6, 0.588, 0.567, 0.552] } };
// height of the model's own blended winglet on the types that keep it (737NG -700W / -800W / -900ER W): the FG winglet rises
// 1.7 model m above the tip's upper skin, its top rendering 0.79 m below ACAP row E 'wingtip' with winglets (6.76 m at OEW,
// D6-58325-7 Rev C §2.3.3; bottom of winglet K 4.32 m: 2.44 m apart, the APB winglet's 8 ft). The winglet (outboard of |z| z0,
// above y0: the TIP_CUT region) is scaled vertically about y0 so its top renders at row E's OEW value in the fitted stance
// (fitType; close-out round 3, fix round 2: found with the E row the verifier asked for). Its span and cant stay the artist's.
const TIP_H = { b738: { z0: 17.45, y0: 0.75 } };
// blended winglets the source model carries, in model units measured on data/models/<m>.sfom (FAM 757-200: the wing's
// upper skin is flat at y ~0.2 out to |z| 18.5 and rises from 18.6 (0.29) through 18.8 (0.71) and 19.0 (2.35) to the tip
// at |z| 19.18, y 2.88: a near-vertical winglet adding 0.64 m of span a side, review 5 Nov 2026 aircraft-v3). The APB
// winglet adds 1.51 m a side (124 ft 10 in -> 134 ft 9 in, Boeing 'Wingspan Increases Due to the Addition of Winglets') and
// does not lengthen the wing, so the span fit puts the winglet root zr at the plain-wing span (SPEC spanPlain, ACAP) and
// the winglet is canted outward from its root (tipShear, p 2: the outward shift grows with the square of the height above
// y0, so the blend at the root keeps its shape and the cant grows towards the tip) until its tip (height yt) meets the
// published winglet span (SPEC span). The winglet keeps the artist's height (no published value here).
const WINGLET = { b752: { zr: 18.6, y0: 0.25, yt: 2.88 } };
// 737 MAX: LEAP-1B nacelles in place of the model's CFM56-7B ones, scaled radially by the fan-diameter ratio (69.4 in / 61 in,
// CFM International LEAP-1B and CFM56-7B data) about the nacelle's TOP line (the pylon attachment: keep 'top'), then raised by
// dy so the lowest nacelle point renders at the OEW value of row E 'engine' (0.56 m, D6-38A004 Rev K §2.3.1-2.3.4), the
// column the stance is fitted to (fitType; close-out round 3, fix round 2, v2: without dy it rendered 0.39-0.42 m, below
// even the MINIMUM 0.43 m; dy is +0.14-0.16 m, so the nacelle grows about its axis to within 0.01 m, as the LEAP-1B was hung
// higher on the MAX). Round 2 of the 5 Nov 2026 review had scaled it about the lowest line (top 0.27 m over the pylon).
// The whole nacelle scales: since fix round 2 the FG inlet lips, left fan cowl, ducts, core cowls and tail pipes are in the
// engine zone (tools/convert_models.py zoneOverride; before, the inlet lip stayed 0.28 m inside the scaled cowl)
const ENG_SCALE = { b37m: 1.14, b38m: 1.14, b39m: 1.14, b3xm: 1.14 };
// nose leg of a model on its own gear whose stance fit (STANCE_FIT) lengthens or shortens it: model units, measured on the
// FG nosegear.ac objects in data/models/b738.sfom (zone 3): outer strut (nouterstrut) y -2.574 .. -1.817, piston
// (nlowerstrut) -3.148 .. -2.495, torque links -3.105 .. -2.355, tyres -3.426 .. -2.705, all at x -4.70 .. -3.95; the main
// gear is at x -20. noseExt (js/aircraft/stretch.js) scales the gear zone ahead of xMin between yTop and yBot linearly and
// moves the wheels below yBot rigidly by e (down: extension; e < 0: compression). Close-out round 3 (aircraft-2): the band
// was the 0.12 m gap between the strut bottom and the tyre tops, so the MAX's +0.35 m stretched the torque links +87 %;
// now it is the whole visible leg from the well (yTop -1.82, the outer strut's top) to the tyre tops (yBot -2.70): every
// part of the leg changes length by e / 0.88 (MAX +0.21-0.26 m: +24-30 %, NG -0.11-0.12 m: -12-13 %; no part is stretched
// more), the well and doors above stay
const NOSE_LEG = { b738: { xMin: -6.0, yTop: -1.82, yBot: -2.70 } };
// stance fit of models on their own gear whose source draws the oleos fully extended and that carry door objects (FG
// 737-800: its animations translate the wheels and lower struts up by gear compression-norm x 0.3048 m, the nose gear by a
// further 0.15 m offset, Models/LWing.xml / RWing.xml / NoseGear.xml, refs/cache/src/fg/737-800): close-out round 3 of 7 Nov
// 2026 (aircraft-1). Standing on its uncompressed gear the 737-800 rendered its forward cargo door 0.25 m above ACAP row C,
// its engine 0.13-0.15 m above row D and, before the round-1 door re-cut, door 1 0.23 m above row B, while door 2 and the
// crown fitted: the airframe stood too high ahead of the main gear. The fit (fitType): least squares over the published
// OEW heights (the MAX (AT OEW) / MAXIMUM column) of the model's own door objects - door 1 (row B), the aft door (NG row G
// sillAft, MAX row M), the forward / aft cargo doors (NG rows C / F, MAX rows D / L: SPEC cargo) - and, since fix round 2,
// the stabiliser tip (NG row H, MAX row N: SPEC htClr; the tailplane re-fitted to the ACAP plan view, tools/convert_models.py
// tailFit) for two unknowns: the main oleo compression dz (stretch.gearUp, >= 0) and the pitch a about the main contact; the
// nose leg is then compressed or extended (noseExt) until its tyre touches. The rows the stance does not fit are fitted
// after it at the same column: the fin top (row J / P, the fin fit below) and the 737 MAX nacelle (row E, ENG_SCALE dy).
// Result (fit.seat; tools/models/check_dims.py against the OEW column, +-3 in, close-out round 3 fix round 2): 737-600 /
// -700 / -800 / -900ER nose-down 1.29 / 1.16 / 0.98 / 0.91 deg, main oleo 0.16 / 0.16 / 0.15 / 0.14 m, nose leg -0.09 / -0.09
// / -0.10 / -0.11 m; 737-7 / -8 / -9 / -10 nose-up 0.12 / 0.14 / 0.22 / 0.12 deg, main oleo 0.12 / 0.12 / 0.15 / 0.13 m, nose leg
// +0.19 / +0.20 / +0.23 / +0.21 m. Every height row is within +-3 in of its OEW value except the NG fuselage top (row A, -0.08
// .. -0.10 m: the FG fuselage section is 3.96 m deep against 4.01 m, D6-38A004 §2.2.2; explained in check_dims). The MAX
// nose leg conflicts with a second Boeing source (pub): "an 8-inch nose gear extension" (0.20 m; Boeing, "Boeing Makes 737 MAX
// Design Decisions", 11 Apr 2012, refs/cache/press/SOURCES.json), while the fitted MAX nose tyre sits ~0.3 m lower below the
// airframe than the NG twin's (inf: from the ACAP sills). The strut length is not the static height: oleo servicing and nose
// load differ, and the documents give no static strut extension. The ACAP rows win because the bridges and the ground
// equipment meet these doors; the difference is recorded (docs/requests/aircraft_closeout.md, close-out round 3 aircraft-2)
const STANCE_FIT = new Set(['b738']);

// A380 upper-deck door U1L: Airbus AC A380 Dec 01/25 FIGURE-2-7-0-991-002 (U1 20.94 m from the nose) and
// FIGURE-2-3-0-991-001 (U1 sill 7.87-7.89 m at MRW, fwd / aft CG; docs/requests/bridges_aircraft.md)
const A388_U1 = { x: 20.94, sill: 7.88 };

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
  // removed sections start at PLUG_REM where the model has one
  const R = PLUG_REM[base]; const b1 = d1 < 0 && R ? R.at[0] : a1, b2 = d2 < 0 && R ? R.at[1] : a2;
  // a shorter aft fuselage: the removed section behind the wing can reach into the start of the tail taper (737-800 model:
  // keel 0.2 m higher at 28.8 m than at 26.0 m), so instead of a hard cut the section plus a blend of up to 3 m is
  // compressed onto the blend length (no step in the skin); the blend ends 0.6 m ahead of the next door (PLUG_REM next)
  let bl2 = 0;
  if (d2 < 0) { const nd = R && R.next != null ? R.next : B.doors.find(x => x > b2); bl2 = Math.max(0, Math.min(3.0, (nd != null ? nd - 0.6 : b2 + 10) - (b2 - d2))); }
  return { at1: b1, at2: b2, d1: +d1.toFixed(3), d2, bl2: +bl2.toFixed(3), by };
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
// rendered skin half width (model units) at station st (model units, positive aft) and model height y, where the jet-bridge
// cab meets the fuselage: the section table F.sec.hwf (half widths at the fractions F.sec.f of each section's height,
// tools/models/model_features.py) interpolated in height, then linearly in station between the nearest complete section
// ahead of st and the nearest behind it (each within 2 m: a cut through a door opening may be incomplete). Review 4 Nov
// 2026: the ellipse through the tallest section within +-2 m (secAt) took a section 1-2 m aft of a widebody's door 1 in
// the tapering nose, and the bellows stopped 0.20-0.29 m short of the skin. Falls back to that ellipse without a table.
function hwAt(F, st, y) {
  const S = F && F.sec; if (!S) return null;
  const at = (j) => {
    const t = S.top[j], b = S.bot[j], h = S.hw[j], r = S.hwf && S.hwf[j];
    if (t == null || b == null || h == null || h < 0.3 * (t - b) / 2 || !r) return null;
    const q = (y - b) / (t - b), f = S.f; if (q < f[0] || q > f[f.length - 1]) return null;
    let k = 0; while (k < f.length - 2 && q > f[k + 1]) k++;
    if (r[k] == null || r[k + 1] == null) return null;
    return r[k] + (r[k + 1] - r[k]) * (q - f[k]) / (f[k + 1] - f[k]);
  };
  const j0 = Math.floor(st / S.dx), w = Math.round(2 / S.dx), n = S.top.length;
  let a = null, b = null;
  for (let j = j0; j >= Math.max(0, j0 - w); j--) { const v = at(j); if (v != null) { a = { j, v }; break; } }
  for (let j = j0 + 1; j <= Math.min(n - 1, j0 + 1 + w); j++) { const v = at(j); if (v != null) { b = { j, v }; break; } }
  if (a && b) return a.v + (b.v - a.v) * (st / S.dx - a.j) / (b.j - a.j);
  if (a || b) return (a || b).v;
  const sec = secAt(F, st); if (!sec) return null;
  const yc = (sec.top + sec.bot) / 2, R = (sec.top - sec.bot) / 2;
  return sec.hw * Math.sqrt(Math.max(0.05, 1 - ((y - yc) / R) ** 2));
}
// model station (units, positive aft) of a rendered station X (m from the nose): inverse of rx (bisection)
function stOf(rx, X, L) { let lo = -10, hi = L + 20; for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2; if (rx(m) < X) lo = m; else hi = m; } return (lo + hi) / 2; }
// top of the fuselage (model units) over the forward fuselage (10-50 % of the length; 747/A380: the upper deck). The top
// profile is first median-filtered over 5 m so a short dorsal hump or antenna fairing is not taken for the crown (A220-300
// model: a hump of +0.28 m at 12 m seated the aircraft 0.28 m too low, review round 1); the 747 / A380 upper decks are
// longer than the filter and are kept.
// ty(st, y): optional map of a profile point (station, model y) to the rendered model y (the stance pitch of gear models)
function crownOf(F, L, ty = null) {
  const S = F && F.sec; if (!S) return null;
  const ok = (j) => { const t = S.top[j], b = S.bot[j], h = S.hw[j]; return t != null && b != null && h != null && h >= 0.3 * (t - b) / 2; };
  const w = Math.max(1, Math.round(2.5 / S.dx)); let c = null;
  for (let j = Math.ceil(0.1 * L / S.dx); j <= Math.floor(0.5 * L / S.dx) && j < S.top.length; j++) {
    if (!ok(j)) continue;
    const win = []; for (let i = j - w; i <= j + w; i++) if (i >= 0 && i < S.top.length && ok(i)) win.push(S.top[i]);
    win.sort((a, b) => a - b); const t = ty ? ty(j * S.dx, win[win.length >> 1]) : win[win.length >> 1];
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
// fuselage bottom on the centre plane (model units) at model station st (positive aft): linear between the two nearest
// complete sections (each within 2 m). A cut through a gear well finds the well's roof on the centre plane, not the belly:
// a section whose bottom is more than 0.3 above the lower of its neighbours is skipped. A cut that crosses the centre plane
// only once (top = bottom) is skipped too (close-out round 5: on the A319 / A320 / A321 FAM models the belly at X 3-5 m is
// the nose-gear doors, a zone the section table leaves out, so the cut found only the crown and keelAt at X 2.5-5.5 m
// interpolated towards it: 0.8-3.8 m too high, X 4 m 5.53-5.72 m against 1.94-1.96 m now; the bottom of the closed doors)
function botAt(F, st) {
  const S = F && F.sec; if (!S) return null;
  const nb = (j) => Math.min(...[j - 1, j + 1].filter(i => i >= 0 && i < S.bot.length && S.bot[i] != null).map(i => S.bot[i]).concat([1e9]));
  const ok = (j) => j >= 0 && j < S.bot.length && S.bot[j] != null && S.top[j] != null && S.top[j] - S.bot[j] > 0.05 && S.hw[j] != null && S.hw[j] >= 0.3 * (S.top[j] - S.bot[j]) / 2 && S.bot[j] <= nb(j) + 0.3;
  const j0 = Math.floor(st / S.dx), w = Math.round(2 / S.dx); let a = null, b = null;
  for (let j = j0; j >= j0 - w; j--) if (ok(j)) { a = j; break; }
  for (let j = j0 + 1; j <= j0 + 1 + w; j++) if (ok(j)) { b = j; break; }
  if (a != null && b != null) return S.bot[a] + (S.bot[b] - S.bot[a]) * (st / S.dx - a) / (b - a);
  return a != null ? S.bot[a] : b != null ? S.bot[b] : null;
}
// STARBOARD skin half width (model units) of the lower lobe at model station st and model height y: the table F.sec.hwl
// (starboard half widths at the heights F.sec.lo above each section's bottom, tools/models/model_features.py), linear in
// height (0 at the keel) and in station between the nearest complete sections; null above the table (hwAt covers the upper
// fuselage; it is the larger side, port on the FG 737-800 / FAM A320 by 1-3 cm).
//   keel-relative: between the two nearest complete sections, when both reach dy and their bottoms differ by < 0.5 model m,
//     the height is taken above the keel interpolated between them (close-out round 3, fix round 2, v3: at the same absolute
//     height a section whose bottom lies above y counted 0, so where the keel rises aft - A319 / A320 aft cargo door - the
//     half width 5 cm above the keel came out 0.09-0.10 m narrower than the mesh);
//   otherwise at the same absolute height, from the nearest sections that have skin there (a section whose bottom lies
//     above y is skipped, not counted 0). Close-out round 4 (verifier finding 3): the keel-relative rule alone returned
//     null above the table (777 keel + 1 m: 0.71 against the mesh's 1.98 m) and blended a fairing section with a fuselage
//     section (A330 4.38 against 2.21 m, 787 4.09 against 2.47 m). Scored against planar cuts of the placed mesh, 32 types,
//     every 0.5 m, keel + 0.05 .. 1.4 m (scratch c4/aircraft/hwstats.py): rows off by > 0.15 m at keel + <= 0.3 m
//     964 (before round 3) / 729 (round 3) / 634 (this rule); 737 family 122 / 95 / 95; A320 family 96 / 76 / 52.
//     Close-out round 4, fix round 2 (verifier finding 2): the absolute-height fallback searched sections up to 2 m away
//     and took the first whose own lower-lobe table still reached y; at a tapering nose or tail that is a far, narrow
//     section (737 nose X 2.5-4 m, keel + 1.4 m: 0.62 against the mesh's 1.19-1.51 m, where round 3 left it to hwAt).
//     It now applies only where y is within the table above the LOCAL keel (botAt, + 0.25 model m: rows at the table's
//     top edge) and only to sections whose bottom is within 0.5 model m of that keel (the keel-relative branch's guard);
//     above that hwLow returns null and the upper table (hwAt) answers. A height up to 0.1 model m above a section's
//     table reads its top row (keel + 1.0 m rows sat 0.007 above it on the 777 and fell through to hwAt: 0.71 against
//     1.98 m), and sections that are not skin (gear-bay keel beam, `ok` below) are skipped. tools/models/skin_check.mjs
//     --baseline, per row against round 3 (same mesh rows): worse by > 0.15 m 545 -> 59 (> 0.5 m: 152 -> 20), 1691
//     better; against round 4 (fix 1): 281 worse, 1226 better; keel + <= 0.3 m off by > 0.15 / 0.5 m 854 / 428 -> 673 /
//     263, every height > 0.15 m 3421 -> 2614 (scratch c4/aircraft/fix2: hwvar.mjs variants A .. K, this is K1).
//     Close-out round 5 (verifier c4-2 finding 5: against round 4 fix 1, 280 rows worse by > 0.15 m, 221 of them tail-cone
//     rows at keel + 1.4 m). Root cause: above the table, aft of the hwf table (0.45 L), hwAt has only the ellipse through
//     the tallest section within 2 m (secAt), which at a tail cone is a section carrying the fin (A330 X 54 keel + 1.4 m
//     0.76 against the mesh's 1.90 m, 747-400 X 55.5 0.97 / 2.45, A380 X 57 0.93 / 2.48, MD-11 X 45.5 1.02 / 2.24); round 4
//     fix 1 had answered those rows from far sections' tables (1.5-2.0, also short) until the round-4 guard (kept) stopped
//     it. Fix: the table now reaches 1.5 model m (tools/models/model_features.py HWL), and its rows above LO_FWD are read
//     only at sections without the hwf table (ahead of 0.45 L hwf is the better answer: nose taper, wing-body fairing). The
//     gear-bay keel-beam test is limited to stations ahead of 0.75 L (main-gear bays lie at 0.4-0.6 L on every model): at
//     a tail cone the section height includes the fin and the test skipped real skin (A220-300 X 35.5-37.5 keel + 0.05 m
//     0.19 against 0.82 m), and a single-crossing cut (top = bottom, botAt) is skipped. tools/models/skin_check.mjs, per row
//     (same mesh rows except where the keel moved, below): against the stored round-4 fix-2 baseline 26 rows worse by >
//     0.15 m (5 by > 0.5 m), 1076 better; against round 4 fix 1 281 -> 48 worse (> 0.5 m: 99 -> 17), 1226 -> 2176 better;
//     against round 3 59 -> 64 worse (20 -> 20), 1691 -> 2733 better; every height > 0.15 / 0.5 m 2614 / 1127 -> 1638 / 623;
//     keel + <= 0.3 m 673 / 263 -> 678 / 192 (A320 family 86 / 72 -> 104 / 6: the nose-gear-bay keel). Still outside the
//     API's validity: the wing box / main-gear bays at keel + 1.4 m (20 rows: A350, 787, A380 wing-body fairing, 777 bay).
const LO_FWD = 1.0;
function hwLow(F, st, y) {
  const S = F && F.sec; if (!S || !S.hwl) return null; const lo = S.lo;
  const top = (j) => S.hwf && S.hwf[j] ? Math.min(LO_FWD, lo[lo.length - 1]) : lo[lo.length - 1];   // (table top at section j)
  const at = (j, dy) => {                                  // section j at dy above its own bottom
    const r = S.hwl[j], t = top(j); if (dy < 0) return 0; if (dy > t + 0.1) return null; dy = Math.min(dy, t);
    if (dy <= lo[0]) return r[0] != null ? r[0] * dy / lo[0] : null;
    let k = 0; while (k < lo.length - 2 && dy > lo[k + 1]) k++;
    if (r[k] == null || r[k + 1] == null) return null;
    return r[k] + (r[k + 1] - r[k]) * (dy - lo[k]) / (lo[k + 1] - lo[k]);
  };
  // (a section whose lower lobe is nowhere wider than 0.2 x its half height is not skin: the cut found the keel beam of a
  // main-gear bay, 777 X 35-39 m: 0.28 m against the mesh's 3.0 m; tested ahead of 0.75 L on the rows up to LO_FWD only, and
  // a cut that crosses the centre plane once, top = bottom, is not a section either)
  const ok = (j) => j >= 0 && j < S.bot.length && S.bot[j] != null && !!S.hwl[j] && !(S.top[j] != null && S.top[j] - S.bot[j] <= 0.05) &&
    !(j < 0.75 * S.top.length && S.top[j] != null && Math.max(...S.hwl[j].filter((v, k) => lo[k] <= LO_FWD).map(v => v ?? 0)) < 0.2 * (S.top[j] - S.bot[j]) / 2);
  const j0 = Math.floor(st / S.dx), w = Math.round(2 / S.dx); let a = null, b = null;
  for (let j = j0; j >= j0 - w; j--) if (ok(j)) { a = j; break; }
  for (let j = j0 + 1; j <= j0 + 1 + w; j++) if (ok(j)) { b = j; break; }
  if (a != null && b != null && Math.abs(S.bot[b] - S.bot[a]) < 0.5) {
    const u = (st / S.dx - a) / (b - a), dy = y - (S.bot[a] + u * (S.bot[b] - S.bot[a]));
    const va = at(a, dy), vb = at(b, dy);
    if (va != null && vb != null) return va + u * (vb - va);
  }
  const kb = botAt(F, st); if (kb == null || y - kb > top(Math.max(0, j0)) + 0.25) return null;
  const abs = (j) => ok(j) && y >= S.bot[j] && Math.abs(S.bot[j] - kb) < 0.5 ? at(j, y - S.bot[j]) : null;
  let A = null, B = null;
  for (let j = j0; j >= j0 - w; j--) { const v = abs(j); if (v != null) { A = { j, v }; break; } }
  for (let j = j0 + 1; j <= j0 + 1 + w; j++) { const v = abs(j); if (v != null) { B = { j, v }; break; } }
  if (A && B) return A.v + (B.v - A.v) * (st / S.dx - A.j) / (B.j - A.j);
  return A ? A.v : B ? B.v : null;
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
  const pl = base !== t && !T.uniform ? plugsFor(t, base) : null;   // T.uniform: generic airframe, scaled uniformly
  const stretch = {};
  if (pl) Object.assign(stretch, { cut1: -pl.at1 / s0, cut2: -pl.at2 / s0, d1: pl.d1 / s0, d2: pl.d2 / s0, bl2: pl.bl2 / s0 });
  const plugM = pl ? (pl.d1 + pl.d2) / s0 : 0;
  const s = T.L / (d.L + plugM);                          // = s0 when the plugs account for the whole length change
  // rendered station (m from the nose) of a model station xm (model units, positive aft)
  // (stations inside a removed section map onto the plug station or the blend, plugShift above)
  const sh = (st, a, dd, bl = 0) => -plugShift(-st, -a, dd, bl);
  const rx = (xm) => s * (xm + (pl ? sh(xm, pl.at1 / s0, pl.d1 / s0) + sh(xm, pl.at2 / s0, pl.d2 / s0, pl.bl2 / s0) : 0));
  // wing span fit (757: SPEC span is the blended-winglet span, 41.07 m, Boeing / APB, spanPlain the ACAP's 38.05 m; review
  // 5 Nov 2026: stretching the plain wing 0.95 m a side to reach the winglet span drew the wing to the winglet root 39.7 m
  // long, +4.3 % against the ACAP; now the plain wing ends at spanPlain and the winglet is canted out, WINGLET above)
  const fold = TIP_PLAIN.has(t) && TIP_FOLD[m];
  const cut = fold || (TIP_ADD[t] && TIP_CUT[m]);
  if (fold) stretch.tipFold = fold; else if (cut) stretch.tipCut = cut;
  if (ENG_SCALE[t] && TIP_CUT[m]) stretch.engScale = { k: ENG_SCALE[t], keep: 'top' };
  const WL = !cut && WINGLET[m] && S.spanPlain ? WINGLET[m] : null;  // (the span fit then ends at the winglet root)
  const semi = cut ? cut.zTo : WL ? WL.zr : F ? F.wing.semi : d.span / 2;
  const want = ((WL ? S.spanPlain : S.span) / 2 - (TIP_ADD[t] ? TIP_LAT[TIP_ADD[t]] : 0)) / s; let wing = null;
  if (Math.abs(want / semi - 1) > SPAN_TOL) {
    const e = T.eng && T.eng.length ? T.eng[T.eng.length - 1] : null;
    const engOut = Math.max(F && F.wing.engOut ? F.wing.engOut : 0, e ? (e.z + e.r) / s : 0);
    const z0 = Math.max(engOut + 0.5 / s, 0.35 * semi), z1 = semi - TIP;
    if (z1 > z0 + 1) { wing = { z0: +z0.toFixed(3), z1: +z1.toFixed(3), dz: +(want - semi).toFixed(3), xMin: -0.8 * d.L }; stretch.wing = wing; }
  }
  // winglet cant (WINGLET above): the tip from the model's semi-span (after the span fit) out to the published span
  let shear = null;
  if (WL && F) {
    const tipNow = F.wing.semi + (wing ? wing.dz : 0), k = (S.span / 2 / s - tipNow) / (WL.yt - WL.y0);
    if (Math.abs(k) > 1e-3) { shear = { z0: +(WL.zr + (wing ? wing.dz : 0)).toFixed(3), y0: WL.y0, yt: WL.yt, k: +k.toFixed(4), p: 2, xMin: +(-0.8 * d.L).toFixed(3) }; stretch.tipShear = shear; }
  }
  // stance of a model on its own gear: the FG 737-800 / 777 models stand level with the nose tyre above the main-tyre
  // bottom (F.contact, tools/models/model_features.py). The model is pitched nose-down by a about the main-gear contact
  // (stretched model frame: x0 = the main contact after the plugs, y0 = its height) so both units touch; the angle is per
  // type (its wheelbase after the plugs). 777 bogie: pivot at the centre axle, the front / aft axles are +-9 mm off the
  // ground at 0.34 deg. js/live/aircraft.js placement() applies it as a rotation of the model matrix, so the model-space
  // positions the shader uses (belly line, registration decal) stay in the body frame.
  let pitch = null;
  const C = d.hasGear && F && F.contact;
  const xOf = (st) => -rx(st) / s;                        // stretched model x (aft negative) of a model station st
  if (C) {
    const xn = xOf(C.nose.st), xm = xOf(C.main.st), dy = C.nose.y - C.main.y;
    if (dy > 0.005 && xn > xm) pitch = { a: +Math.atan2(dy, xn - xm).toFixed(6), x0: +xm.toFixed(3), y0: C.main.y };
  }
  // stance fit (STANCE_FIT above): rows [model station, model height, published OEW height] of the model's own door objects
  // (doors / cargo doors from tools/models/model_features.py) against the type's SPEC rows; the rendered height of a row is
  // Hc0 - dz + s (y0 + (y - y0) cos a - (x - x0) sin a), linear in (dz, sin a) with cos a = 1 (< 0.001 m at 1 deg)
  const dmF = doorMesh(m), dmA = F && (F.doors || []).find(q => q.side === 'L' && q.x > 0.5 * d.L);
  const cgF = F && (F.cargo || []).find(q => q.x < 0.5 * d.L), cgA = F && (F.cargo || []).find(q => q.x >= 0.5 * d.L);
  let stance = null;
  if (pitch && STANCE_FIT.has(m) && NOSE_LEG[m]) {
    const rows = [];
    if (dmF && S.sill) rows.push([dmF.x, dmF.ySill, S.sill[1], 'door 1']);
    if (dmA && S.sillAft) rows.push([dmA.x, dmA.ySill, S.sillAft[1], 'aft door']);
    if (cgF && S.cargo && S.cargo.fwd) rows.push([cgF.x, cgF.ySill, S.cargo.fwd[1], 'fwd cargo door']);
    if (cgA && S.cargo && S.cargo.aft) rows.push([cgA.x, cgA.ySill, S.cargo.aft[1], 'aft cargo door']);
    // the stabiliser tip (NG row H, MAX row N; close-out round 3, fix round 2, v1/v2: with the tailplane re-fitted to the
    // ACAP plan view, tools/convert_models.py tailFit, its tip is the row farthest from the main gear). Not an independent
    // row (close-out round 4, verifier finding 6): the tailplane dihedral (7.0 deg, inf; the ACAP front view draws ~6.4) was
    // fitted to these same rows at this stance. On the door rows alone the stance is 737-600 / -700 / -800 / -900ER 1.49 /
    // 1.29 / 1.02 / 0.91 deg nose-down (now 1.29 / 1.16 / 0.98 / 0.91), MAX -0.20 / -0.20 / -0.31 / -0.21 (now -0.12 / -0.14 /
    // -0.22 / -0.12), T.dockSill NG 2.703-2.719 (now 2.719-2.723), MAX 3.043-3.052 (now 3.033-3.041): every door row within
    // +-3 in either way. Kept until the dihedral has a primary source (then: stance on the doors, dihedral alone to H / N)
    if (F.wing && F.wing.htSt != null && F.wing.htY != null && S.htClr) rows.push([F.wing.htSt, F.wing.htY, S.htClr[1], 'stabilizer tip']);
    if (rows.length >= 2) {
      const Hc0 = -d.low * s; let n = 0, sg = 0, sgg = 0, sb = 0, sgb = 0;
      for (const [st, y, ref] of rows) { const g = s * (xOf(st) - pitch.x0), b = Hc0 + s * y - ref; n++; sg += g; sgg += g * g; sb += b; sgb += g * b; }
      let dz = (sb * sgg - sg * sgb) / (n * sgg - sg * sg), sa = (n * sgb - sg * sb) / (n * sgg - sg * sg);
      if (!(dz >= 0)) { dz = 0; sa = sgb / sgg; }                // (an oleo drawn fully extended cannot extend further)
      const a = Math.asin(Math.max(-0.1, Math.min(0.1, sa)));
      const e = (C.nose.y - C.main.y) * Math.cos(a) - (xOf(C.nose.st) - pitch.x0) * Math.sin(a);   // nose tyre above the ground
      pitch.a = +a.toFixed(6);
      if (dz > 0.001) stretch.gearUp = +(dz / s).toFixed(4);
      if (Math.abs(e) > 0.002) stretch.noseExt = { ...NOSE_LEG[m], e: +e.toFixed(4) };
      stance = { dz: +dz.toFixed(3), rows: rows.map(r => r[3]) };
    }
  }
  // model point (station st, height y) -> [x, y] of the stretched, pitched model (model units)
  const pose = (st, y) => {
    const x = xOf(st); if (!pitch) return [x, y];
    const ca = Math.cos(pitch.a), sa = Math.sin(pitch.a), dx = x - pitch.x0, dy = y - pitch.y0;
    return [pitch.x0 + dx * ca + dy * sa, pitch.y0 + dy * ca - dx * sa];
  };
  const tyP = pitch ? (st, y) => pose(st, y)[1] : null;
  // seating and the door the bridge docks to
  const dm = doorMesh(m); let Hc, seat;
  const x1m = dm ? dm.x : T.doors[0] / s;
  if (d.hasGear) {
    Hc = -d.low * s; seat = 'gear';
    // FlightGear gear is modelled with the oleos extended (the simulator compresses them): where the model standing on its
    // own gear puts the fuselage top more than 0.15 m above the published height, the gear (zone 3) is moved up by the
    // excess (oleo compression; the strut tops disappear into the wing / fairing) and the airframe comes down onto it
    const top0 = crownOf(F, d.L, tyP);
    if (S.crown && top0 != null && OLEO.has(m)) {
      const ex = Hc + top0 * s - (S.crown[0] + S.crown[1]) / 2;
      if (ex > 0.15) { stretch.gearUp = +(ex / s).toFixed(3); Hc -= ex; seat = 'gear (oleos compressed ' + ex.toFixed(2) + ' m)'; }
    }
    if (stance && stretch.gearUp) { Hc -= stretch.gearUp * s; seat = 'gear (main oleo compressed ' + (stretch.gearUp * s).toFixed(2) + ' m)'; }
    if (pitch) { pitch.y0 = +(C.main.y + (stretch.gearUp || 0)).toFixed(3); seat += (pitch.a >= 0 ? ', nose-down ' : ', nose-up ') + Math.abs(pitch.a * 180 / Math.PI).toFixed(2) + ' deg'
      + (stretch.noseExt ? ', nose leg ' + (stretch.noseExt.e >= 0 ? '+' : '') + (stretch.noseExt.e * s).toFixed(2) + ' m' : ''); }
    // TIP_H winglet height in the fitted stance (SPEC wlTop: row E with winglets, OEW value)
    const TW = TIP_H[m];
    if (TW && !cut && stance && pitch && F.wing && F.wing.tip && S.wlTop && !stretch.wing) {
      const k = ((S.wlTop[1] - Hc) / s - pose(F.wing.tip.topSt, TW.y0)[1]) / (Math.cos(pitch.a) * (F.wing.tip.top - TW.y0));
      if (k > 0.8 && k < 1.6) stretch.tipScale = { z0: TW.z0, y0: TW.y0, k: +k.toFixed(4), xMin: +(-0.8 * d.L).toFixed(3) };
    }
    // ENG_SCALE nacelle height in the fitted stance: after the radial scale about its top line, the nacelle is raised by dy
    // so that its lowest point renders at the engine row's OEW value (the column the stance is fitted to, STANCE_FIT)
    const N = F && F.wing && F.wing.nac;
    if (stretch.engScale && stance && pitch && N && S.engClr) {
      const yLow = N.top - stretch.engScale.k * (N.top - N.low), now = Hc + pose(N.lowSt, yLow)[1] * s;
      stretch.engScale.dy = +((S.engClr[1] - now) / s / Math.cos(pitch.a)).toFixed(4);
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
  const Fw = F && F.wing, SB = T.uniform ? {} : SPEC[base] || {};
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
    const C = S.engClr || SB.engClr;
    if (C) {
      const tgt = (C[0] + C[1]) / 2, now = Hc + eL * s;
      if (now < C[0]) { const k = Math.max(0.75, Math.min(1, (Hc - tgt) / (-eL * s))); if (k < 0.999) { squash = { y0: 0, k: +k.toFixed(4) }; stretch.squash = squash; } }
    }
  }
  const yR0 = (y) => (squash && y < squash.y0 ? squash.y0 + (y - squash.y0) * squash.k : y);  // model y after the compression
  // belly fairing (close-out round 3, aircraft-5): the FAM A330 model's wing-body fairing hangs 0.35 model m below the
  // keel of a fuselage whose depth fits (rendered 5.66 m against 5.64 m), so after the engine-clearance compression above
  // its bottom rendered 1.68 m against the belly row 1.85-1.86 m at MRW (2.04 m at 119 t; AC A330 Rev 21 Apr 01/13
  // FIGURE-2-3-0-991-001-A01 row H, the BF1 1.85-1.86 m of the Dec 01/25 revision SPEC cites; the 2025 PDF could not be
  // re-fetched: Airbus' site refuses scripted downloads). Where SPEC bellyClr is missed by more than 3 in, only the fairing
  // (body vertices below the keel line, |z| within 1.1 x the fuselage half width; not engines, pylons or gear) is compressed
  // towards the keel line (stretch.fairing) until its bottom sits at the middle of the range. Keel line: the median section
  // bottom over 0.2-0.3 L and 0.62-0.7 L (constant section), fairing bottom: the lowest section bottom over 0.35-0.55 L.
  let fairing = null;
  const BC = S.bellyClr || SB.bellyClr;
  if (!d.hasGear && BC && F && F.sec) {
    const Sx = F.sec, at = (a, b) => Sx.bot.slice(Math.ceil(a * d.L / Sx.dx), Math.floor(b * d.L / Sx.dx) + 1).filter(v => v != null);
    const kl = [...at(0.2, 0.3), ...at(0.62, 0.7)].sort((a, b) => a - b), fb = at(0.35, 0.55);
    const hwm = Sx.hw.slice(Math.ceil(0.3 * d.L / Sx.dx), Math.floor(0.5 * d.L / Sx.dx) + 1).filter(v => v != null).sort((a, b) => a - b);
    if (kl.length && fb.length && hwm.length) {
      const yk = yR0(kl[kl.length >> 1]), yf = yR0(Math.min(...fb)), now = Hc + yf * s, tgt = (BC[0] + BC[1]) / 2;
      if (now < BC[0] - 0.08 && yf < yk - 0.05) {
        const k = Math.max(0.3, Math.min(1, ((tgt - Hc) / s - yk) / (yf - yk)));
        if (k < 0.999) { fairing = { y0: +yk.toFixed(4), k: +k.toFixed(4), zMax: +(1.1 * hwm[hwm.length >> 1]).toFixed(3) }; stretch.fairing = fairing; }
      }
    }
  }
  const yR = (y) => { const v = yR0(y); return fairing && v < fairing.y0 ? fairing.y0 + (v - fairing.y0) * fairing.k : v; };   // (centre plane)
  Hc = +Hc.toFixed(3);
  // rendered door object: centre station at mid height, sill (pitched on gear models)
  const doorR = dm ? { x: +(-pose(dm.x, (dm.ySill + dm.yTop) / 2)[0] * s).toFixed(3), sill: +(Hc + pose(dm.x, dm.ySill)[1] * s).toFixed(3) } : null;
  const dockX1 = dm ? doorR.x : T.doors[0];
  // cab floor: the published sill, except on a model standing on its own gear, whose stance sets where its door object
  // is: there the bridge meets the door that is drawn (rendered sill), so cab floor and door outline agree. FG 737-800:
  // the artist's door 1L sill rendered 2.97 m in the nose-down OEW stance, 0.23 m above the ACAP's 2.59-2.74 m
  // (D6-58325-7 Rev C §2.3.2); tools/convert_models.py now re-fits door 1L and its skin opening to the OEW sill 2.74 m and
  // the 72 in door (review 5 Nov 2026, aircraft-v2), so the rendered sill is 2.74 m; check_dims records both
  const dockSill = (d.hasGear && dm) ? doorR.sill : T.sill != null ? T.sill : Hc - 0.3 * d.R * s;
  // rendered half width of the fuselage at a door (station st, model units), at door mid height (sill + 0.95 m): model
  // height of a rendered height at that station (the stance pitch undone)
  const yModel = (st, yR) => {
    if (!pitch) return (yR - Hc) / s;
    const y = (yR - Hc) / s, dx = xOf(st) - pitch.x0;
    return pitch.y0 + (y - pitch.y0 + dx * Math.sin(pitch.a)) / Math.cos(pitch.a);
  };
  // the cab's bellows has a flat front: it stops at the widest skin over the door opening (sill to sill + 1.9 m, the
  // passenger doors' clear height), so it closes on the fuselage at the max-breadth line and never cuts into the skin
  // below or above door mid height (737-800 door 1L: 1.76 m at the max breadth vs 1.69 m at sill + 0.95 m)
  const hwDoor = (st, sill) => {
    let h = null; for (let dz = 0.05; dz <= 1.9001; dz += 0.1) { const v = hwAt(F, st, yModel(st, sill + dz)); if (v != null && (h == null || v > h)) h = v; }
    return h != null ? +(h * s).toFixed(3) : T.R;
  };
  const hwMid = (st, sill) => { const h = hwAt(F, st, yModel(st, sill + 0.95)); return h != null ? +(h * s).toFixed(3) : null; };
  const dockHW = hwDoor(x1m, dockSill);
  // the second bridge's door (published station, T.dock2) and the A380 upper-deck door U1L (gates.js door 3)
  const dockHW2 = T.dock2 && T.doors[T.dock2 - 1] != null ? hwDoor(stOf(rx, T.doors[T.dock2 - 1], d.L), T.sill2 ?? dockSill) : null;
  const dockHW3 = t === 'a388' ? hwDoor(stOf(rx, A388_U1.x, d.L), A388_U1.sill) : null;
  const top = crownOf(F, d.L);
  // pitch-induced rise of the fin tip (model units): the published height is the fin top in the real attitude
  // (the fin tip's highest point once pitched: of its forward and aft ends, model_features finTop st0 / st1)
  const finRise = pitch && F.finTop ? Math.max(...[F.finTop.st, F.finTop.st0, F.finTop.st1].filter(v => v != null).map(st => pose(st, d.H)[1] - d.H)) : 0;
  // fin height fit: where the model's fin top misses the published overall height (the artist's fin is too short or too
  // tall relative to the fuselage, e.g. FAM A330/787, FG 737-800), the fin (everything above the fuselage top aft of
  // 60 % of the length, except engines, pylons and gear) is scaled vertically about the fuselage top so that its height
  // above the fuselage top is the published one: mid(H) - mid(crown) where the document gives the fuselage top, else
  // mid(H) - the rendered fuselage top.
  let fin = null;
  // (the fin op stays inside the tailplane's semi-span + 0.5: a T-tail's tailplane rides with the fin, the wing tips do not)
  const finZ = +(Math.max(F && F.wing && F.wing.htSemi ? F.wing.htSemi : 0, 2.0) + 0.5).toFixed(3);
  if (top != null && S.H && stance) {
    // models in a fitted stance (STANCE_FIT): the fin top on the OEW value of the vertical-tail row (NG J 'MAX (AT OEW)', MAX
    // P 'MAXIMUM'), the column the stance is fitted to (close-out round 3, fix round 2, v2: inside the [MIN, MAX] range the
    // fin was left as drawn and rendered 0.11-0.18 m below the OEW value)
    const k = ((S.H[1] - Hc) / s - finRise - top) / (d.H - top);
    if (Math.abs(k - 1) > 1e-4 && k > 0.7 && k < 1.4) { fin = { yF: +top.toFixed(3), xF: +(-0.6 * d.L).toFixed(3), k: +k.toFixed(4), zMax: finZ }; stretch.fin = fin; }
  } else if (top != null && S.H) {
    const Hr = Hc + (d.H + finRise) * s, [h0, h1] = S.H, tol = 0.005 * (h0 + h1) / 2;
    if (Hr < h0 - tol || Hr > h1 + tol) {
      const want = (h0 + h1) / 2 - finRise * s - (S.crown ? (S.crown[0] + S.crown[1]) / 2 : Hc + top * s);
      const k = want / ((d.H - top) * s);
      // (a generic airframe takes a wider range: a scaled CRJ200 fin on a small business jet is up to ~2x too short)
      if (k > (T.uniform ? 0.6 : 0.7) && k < (T.uniform ? 2.4 : 1.4)) { fin = { yF: +top.toFixed(3), xF: +(-0.6 * d.L).toFixed(3), k: +k.toFixed(4), zMax: finZ }; stretch.fin = fin; }
    }
  }
  const finTop = fin ? top + (d.H - top) * fin.k : d.H;
  const topR = pitch ? crownOf(F, d.L, tyP) : top;
  const fit = { model: m, base, s: +s.toFixed(5), s0: +s0.toFixed(5), plugs: pl, wing, stretch: Object.keys(stretch).length ? stretch : null, rx,
    Hc, seat, pitch, fin, squash, tipAdd: TIP_ADD[t] || null, door: dm ? { name: dm.name, from: dm.from, x: dockX1, sill: doorR.sill } : null,
    renderedSpan: +(2 * ((cut ? cut.zTo : F ? F.wing.semi : d.span / 2) + (wing ? wing.dz : 0) + (shear ? shear.k * (shear.yt - shear.y0) : 0)) * s + (TIP_ADD[t] ? 2 * TIP_LAT[TIP_ADD[t]] : 0)).toFixed(3),
    winglet: WL ? { zr: WL.zr, y0: WL.y0, root: +(2 * (WL.zr + (wing ? wing.dz : 0)) * s).toFixed(3), lat: +((F.wing.semi - WL.zr + (shear ? shear.k * (shear.yt - shear.y0) : 0)) * s).toFixed(3), k: shear ? shear.k : 0 } : null, renderedL: +((d.L + plugM) * s).toFixed(3), renderedH: +(Hc + (finTop + finRise) * s).toFixed(3),
    renderedCrown: topR != null ? +(Hc + topR * s).toFixed(3) : null };
  // rendered engine clearance and the skin above the main gear (the procedural struts of gear-less models reach into it)
  fit.engClear = eL != null ? +(Hc + yR0(eL) * s).toFixed(3) : null;   // (engines are not in the fairing compression)
  if (!d.hasGear && T.xMain != null) {
    let lo = -10, hi = d.L + 20; for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2; if (rx(m) < T.xMain) lo = m; else hi = m; }
    const u = underAt(F, (lo + hi) / 2, (S.track || T.track || 6) / 2 / s);
    fit.gearTop = u != null ? +(Hc + (Math.abs((S.track || T.track || 6) / 2 / s) <= (fairing ? fairing.zMax : -1) ? yR(u) : yR0(u)) * s).toFixed(3) : null;
  }
  T.fit = fit; T.Hc = Hc; T.dockX1 = dockX1; T.dockSill = dockSill; T.dockHW = dockHW;
  // stance-aware lower fuselage for the ground equipment (close-out round 3 of 7 Nov 2026, aircraft-1: the belt loaders used
  // an unpitched ellipse through T.Hc and the crown, 2 Hc - crown, which fell 0.15 m when the 737 MAX stood nose-up while its
  // forward belly rose 0.25 m). Rendered metres, aircraft frame of js/live/aircraft.js placement() (X = station aft of the
  // nose, heights above the ground, pitch, plugs and the engine-clearance compression included):
  //   fit.keelAt(X)       lowest skin on the centre plane at station X (the section table's bottom, posed)
  //   fit.skinHW(X, y, w) half width of the fuselage skin at station X and height y (w > 0: the widest over X +- w/2, for a
//                       conveyor end, close-out round 3 fix round 2): lower lobe (to 1 model m above the
  //                       keel, aft of 0.45 L to 1.5 m: close-out round 5) the starboard side, sec.hwl; above it the larger side, sec.hwf; else (or where a wing / fairing
  //                       is cut: wider than 1.1 Rz) the ellipse through the section's top and bottom with Rz; null where no
  //                       skin (below the keel / above the crown). Checked against planar cuts of the placed mesh: see
  //                       docs/requests/aircraft_closeout.md close-out round 3 (scratch hwcmp.mjs numbers)
  //   fit.cargo           {fwd, aft}: X (the model's own cargo-door object, rendered centre; else the published station
  //                       SPEC cargoX), sill (the drawn door's rendered sill; null without a door object), keel (at X), pub
  //                       (the published sill range, SPEC cargo), side ('R': the 737 / A320 cargo doors are on the right)
  const yU = (st, y) => { let v = yModel(st, y); if (fairing && v < fairing.y0) v = fairing.y0 + (v - fairing.y0) / fairing.k; if (squash && v < squash.y0) v = squash.y0 + (v - squash.y0) / squash.k; return v; };
  fit.keelAt = (X) => { const st = stOf(rx, X, d.L), b = botAt(F, st); return b == null ? null : +(Hc + pose(st, yR(b))[1] * s).toFixed(3); };
  const skinAt = (X, y) => {
    const st = stOf(rx, X, d.L), v = yU(st, y); let h = hwLow(F, st, v);
    if (h == null) { h = hwAt(F, st, v); if (h != null && h > 1.1 * d.Rz) h = null; }
    if (h == null) {                                       // ellipse through the section's top and bottom, half width Rz
      const b = botAt(F, st), sec = secAt(F, st); if (b == null || !sec) return null;
      const yc = (sec.top + b) / 2, R = (sec.top - b) / 2, q = (v - yc) / R; if (Math.abs(q) >= 1) return null;
      h = d.Rz * Math.sqrt(1 - q * q);
    }
    return +(h * s).toFixed(3);
  };
  // w > 0: the widest skin over [X - w/2, X + w/2] (ends and middle; close-out round 3, fix round 2, v3: a 0.9 m conveyor
  // end placed by its centre line went 0.04-0.15 m into the skin at its forward corner where the keel rises aft)
  fit.skinHW = (X, y, w = 0) => {
    if (!(w > 0)) return skinAt(X, y);
    let h = null; for (const dx of [-w / 2, 0, w / 2]) { const v = skinAt(X + dx, y); if (v != null && (h == null || v > h)) h = v; }
    return h;
  };
  const cargo = {};
  for (const [k, c] of [['fwd', cgF], ['aft', cgA]]) {
    const X = c ? +(-pose(c.x, (c.ySill + c.yTop) / 2)[0] * s).toFixed(3) : (S.cargoX && S.cargoX[k] != null ? S.cargoX[k] : null);
    const pub = S.cargo && S.cargo[k] ? S.cargo[k] : null; if (X == null && !pub) continue;
    cargo[k] = { X, sill: c ? +(Hc + pose(c.x, yR(c.ySill))[1] * s).toFixed(3) : null, keel: X != null ? fit.keelAt(X) : null, pub,
      side: c ? c.side : 'R', src: c ? 'model door object ' + c.name : 'published station (SPEC cargoX)' };
  }
  if (Object.keys(cargo).length) fit.cargo = cargo;
  if (stance) fit.stance = stance;
  fit.dockHWmid = hwMid(x1m, dockSill);                   // skin half width at door 1 mid height (check_dims: bellows gap)
  // skin half width (m) at the door's station from the sill up, every 0.25 m to sill + 3 m (the bellows' height), per
  // docking door (1, 2, 3 = A380 U1L): for a bellows front that follows the skin (js/live/gates.js draws a flat one)
  const prof = (st, sill) => { const r = []; for (let k = 0; k <= 12; k++) { const v = hwAt(F, st, yModel(st, sill + 0.25 * k)); r.push(v != null ? +(v * s).toFixed(3) : null); } return r; };
  T.dockSkin = { dz: 0.25, 1: prof(x1m, dockSill) };
  if (dockHW2 != null) T.dockSkin[2] = prof(stOf(rx, T.doors[T.dock2 - 1], d.L), T.sill2 ?? dockSill);
  if (dockHW3 != null) T.dockSkin[3] = prof(stOf(rx, A388_U1.x, d.L), A388_U1.sill);
  if (dockHW2 != null) T.dockHW2 = dockHW2;
  if (dockHW3 != null) T.dockHW3 = dockHW3;
  return fit;
}
// procedural airframes (no model) and every type's second-bridge door
function dockDefaults(T) {
  if (T.dockX1 == null) T.dockX1 = T.doors[0];
  if (T.dockSill == null) T.dockSill = T.sill ?? T.Hc - 0.3 * T.R;
  if (T.dockHW == null) T.dockHW = T.R;
  T.dockX2 = T.dock2 ? T.doors[T.dock2 - 1] : null; T.dockSill2 = T.dock2 ? (T.sill2 ?? T.dockSill) : null;
  // A380 upper-deck door U1L for the upper-deck bridges (js/live/gates.js door 3); dockHW3 (rendered skin half width at
  // U1L mid height) is measured by fitType
  if (T.key === 'a388') { T.dockX3 = A388_U1.x; T.dockSill3 = A388_U1.sill; }
}
for (const t in TYPE_MODEL) { if (TYPE_MODEL[t]) fitType(t, TYPE_MODEL[t]); if (TYPES[t]) dockDefaults(TYPES[t]); }

// lower fuselage of any TYPES entry (the fitted model's rendered skin, T.fit.keelAt / skinHW; procedural airframes: the
// ellipse of T.R / T.Hc), rendered metres: keel height at station X, skin half width at station X and height y
export function keelAt(T, X) { const v = T && T.fit && T.fit.keelAt ? T.fit.keelAt(X) : null; return v != null ? v : T.Hc - T.R; }
export function skinHalfWidth(T, X, y, w = 0) {
  const v = T && T.fit && T.fit.skinHW ? T.fit.skinHW(X, y, w) : null; if (v != null) return v;
  const q = (y - T.Hc) / T.R; return Math.abs(q) < 1 ? +(T.R * Math.sqrt(1 - q * q)).toFixed(3) : null;
}
// where a belt loader meets a lower-deck cargo door ('fwd' / 'aft') of a TYPES entry (close-out round 3, aircraft-1; for
// js/world/gates.js beltSill and js/live/gates.js placeVehicles): X station (m aft of the nose), S the conveyor-top height
// (the drawn door's rendered sill; without a door object the middle of the published sill range, at least 0.05 m above the
// keel), hw the starboard skin half width at S (the conveyor's end), keel; null when neither a door object nor a published
// sill exists (other types: the consumer's own default). w: the conveyor's width (m): hw is then the widest skin under
// its end (close-out round 3, fix round 2, v3: on the centre line only, the end of a 0.9 m conveyor reached up to 0.15 m
// into the skin at a corner). Checked on the placed mesh: docs/requests/aircraft_closeout.md close-out round 3
export function cargoDoor(T, door, w = 0) {
  const c = T && T.fit && T.fit.cargo && T.fit.cargo[door]; if (!c || c.X == null) return null;
  const S = c.sill != null ? c.sill : c.pub ? Math.max((c.pub[0] + c.pub[1]) / 2, (c.keel ?? -9) + 0.05) : null; if (S == null) return null;
  return { X: c.X, S: +S.toFixed(3), hw: skinHalfWidth(T, c.X, S, w), keel: c.keel, pub: c.pub, drawn: c.sill != null, w };
}
// kept for callers of the old API: the fuselage/wing stretch of type t rendered with model m (null = none)
export function stretchFor(t, m) { const T = TYPES[t]; return T && T.fit && T.fit.model === m ? T.fit.stretch : null; }
export function seatType(t, m) { const T = TYPES[t]; if (T && !T.uniform && (!T.fit || T.fit.model !== m) && m && SPEC[t]) { fitType(t, m); dockDefaults(T); } }

// business jets and the ERJ-135 / -145 regional jets: the CRJ200 model (T-tail, two rear engines) scaled uniformly to the
// type's length, the outer wing stretched to its span and the fin to its tail height (fitType with T.uniform: no plugs, no
// CRJ200 clearance tables, no CRJ window row). Labelled generic in the UI (js/live/app.js modelNote).
// [length, span (with winglets where the FAA lists one), tail height at OEW, engines] in metres from the FAA Aircraft
// Characteristics Database (https://www.faa.gov/airports/engineering/aircraft_char_database, aircraft_data .xlsx, fetched
// 4 Nov 2026: refs/cache/faa/faa_aircraft_char_database.xlsx, tools/models/faa_acd.py). Review 4 Nov 2026: the span had
// been the CRJ200's scaled by the length ratio (GLEX 24.0 m against 28.65 m) and the lengths were not re-verified (GA5C /
// GA6C were 1.6 / 1.1 m too long). E135: the ACD's E135 row 'Embraer ERJ 135/140/Legacy' gives the ERJ-140's length
// (28.47 m), so the ERJ-135 length is the ACD's E35L row 'Embraer 135BJ Legacy 600' (the ERJ-135 airframe): 26.33 m (review
// 5 Nov 2026, aircraft-v4); span (no winglets) and tail height from the E135 row. Trijets (FA50, F900, FA7X, FA8X: 3
// engines) are drawn with the CRJ's two (typeForIcao flags them: engines 3).
export const BIZ = {
  GLF4: [26.91, 23.71, 7.44, 2], GLF5: [29.38, 28.50, 7.89, 2], GLF6: [30.42, 30.39, 7.86, 2], G280: [20.36, 19.20, 6.49, 2], GALX: [18.99, 17.71, 6.52, 2],
  GA5C: [27.79, 26.32, 7.77, 2], GA6C: [29.29, 28.70, 7.71, 2], GLEX: [30.30, 28.65, 7.77, 2], GL5T: [29.50, 28.65, 7.77, 2], GL7T: [33.71, 31.79, 8.14, 2],
  CL30: [20.97, 19.45, 6.19, 2], CL35: [20.91, 21.00, 6.10, 2], CL60: [20.85, 19.60, 6.31, 2],
  C56X: [15.79, 17.16, 5.24, 2], C68A: [18.99, 22.04, 6.37, 2], C700: [22.31, 21.00, 5.91, 2], C750: [22.04, 19.39, 5.88, 2],
  C25A: [14.54, 15.18, 4.27, 2], C25B: [15.61, 16.25, 4.63, 2], C25C: [16.25, 15.48, 4.69, 2], C560: [14.90, 16.49, 4.57, 2],
  E55P: [15.64, 15.91, 5.12, 2], E545: [19.69, 20.24, 6.43, 2], E550: [20.73, 20.27, 6.43, 2], E35L: [26.33, 21.09, 6.77, 2],
  E135: [26.33, 20.06, 6.77, 2], E145: [29.87, 20.06, 6.77, 2],
  LJ45: [17.68, 14.57, 4.30, 2], LJ60: [17.89, 13.35, 4.48, 2], LJ75: [17.68, 15.51, 4.27, 2],
  FA7X: [23.20, 26.21, 7.83, 3], FA8X: [24.44, 26.30, 7.96, 3], F900: [20.21, 19.32, 7.56, 3], F2TH: [20.21, 19.32, 7.07, 2], FA50: [18.53, 18.87, 6.98, 3],
  H25B: [15.61, 15.67, 5.52, 2], PC24: [16.86, 17.01, 5.39, 2], BE40: [14.75, 13.26, 4.24, 2],
};
const REGIONAL = new Set(['E135', 'E145']);
export const BIZ_LEN = Object.fromEntries(Object.entries(BIZ).map(([k, v]) => [k, v[0]]));   // old export (lengths only)
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
  if (BIZ[icao]) {
    const key = 'biz_' + icao;
    if (!TYPES[key]) {
      const [L, span, H] = BIZ[icao];
      const B = TYPES.crj2, f = L / B.L;
      const T = scaleObj(B, f); T.name = icao; T.key = key; T.cls = 'B'; T.uniform = true; T.wing.y = B.wing.y; T.win.forEach((w, i) => { w.y = B.win[i].y * f; });
      T.L = L; T.wing.span = span; T.H = H; T.fit = null;
      SPEC[key] = { doc: 'FAA ACD', L, span, H: [H, H], src: 'FAA Aircraft Characteristics Database (js/aircraft/fit.js BIZ)' };
      TYPES[key] = T;
      fitType(key, 'crj2'); dockDefaults(T);
    }
    return { t: key, m: 'crj2', generic: REGIONAL.has(icao) ? 'regional jet' : 'business jet', engines: BIZ[icao][3] };
  }
  return null;
}

// Airliner type table: the airframe geometry the procedural renderer draws, and the published dimensions that everything
// else (model fitting, jet-bridge docking, ground physics, stand fit, procedural gear) takes from the manufacturers'
// airport-planning documents. All values are metres; x positions are measured aft from the nose tip.
//
// Two layers:
//  1. geometry (below, `TYPES` literal + derive()): wing planform, engines, tail, windows, cockpit style. Shapes for the
//     procedural airframe only; the planform is also the ground-physics collision shape.
//       wing: rootLE (x of LE at fuselage side), rootC, kinkZ/kinkC (TE kink), tipC, sweep (LE deg), dihedral (deg),
//             y (root height as fraction of R below centerline); eng: underwing engines {z, len, r, y, fwd}; rear: fuselage-mounted
//       gear: main units [{x, z, wheels}] (z = half-track), nose {x, r}; tip: sharklet | blended | split | raked | curved | fence | small | none
//       cockpit: {x0, x1, yb, yt, w} window band (y relative to fuselage centerline), style
//  2. SPEC (published data, applied over the geometry by applySpec): L, span, overall height H, fuselage top (crown) and
//     door-1 sill above the ground, nose-gear and main-gear axle stations, main-gear track, passenger-door CENTRES.
//     Every entry names its document; `inf` lists fields that are inferred (derived from a document value, scaled off a
//     drawing, or taken from a sibling type) and `unv` fields that are not verified against a primary source.
//     Conventions (checked in the documents, see docs/research/aircraft_models_check.md §3):
//       - Boeing door stations are to the door centre line ("longitudinal distance from nose to center of door", 757 ACAP
//         §2.7.1); Airbus AC door figures dimension the door centre line. `doors` lists the left-side main passenger doors
//         in order (1L, 2L, ...); over-wing exits are not doors here; optional doors are in `doorsOpt`.
//       - main: nose tip -> main-gear axle (Boeing: nose gear + wheelbase; 747: wing gear then body gear (+3.07 m);
//         A380: WLG then BLG). track: between the main-gear centre lines (wing gear); trackB: 747/A380 body gear.
//       - crown / sill: [min, max] of the ground-clearance tables (loading/CG variation); the nominal value used at runtime
//         is the mean. crown = top of the fuselage at the forward fuselage (747: top of the upper deck = ACAP "A"; A380:
//         upper deck), sill = door 1 (1L) sill; sill2 = door 2 sill where the table gives it.
//       - dock2: number of the door the second jet bridge of a wide-body stand docks to (null: only the L1 bridge docks).
// The runtime fit of the imported models to these numbers (scale, fuselage plugs, wing-tip span fit, seating on the door
// sill or fuselage top, the rendered door the bridge docks to) is in js/aircraft/fit.js. Checked by tools/models/check_dims.py.
export const TYPES = {
  a20n: { name: 'Airbus A320neo', cls: 'C', L: 37.57, R: 1.98, top: 1.07, Hc: 4.0, Ln: 6.0, Lt: 11.6,
    wing: { span: 35.8, rootLE: 12.9, rootC: 7.0, kinkZ: 6.3, kinkC: 4.3, tipC: 1.5, sweep: 27, dihedral: 5.1, y: 0.62, tcRoot: 0.15, tcTip: 0.11, tip: 'sharklet', tipH: 2.4, flex: 0.2 },
    eng: [{ z: 5.75, len: 4.9, r: 1.12, y: 1.35, fwd: 2.8 }],
    gear: { main: [{ x: 17.85, z: 3.8, wheels: 2 }], nose: { x: 5.2, r: 0.37 }, r: 0.58, w: 0.36 },
    hstab: { span: 12.45, rootC: 3.7, tipC: 1.45, sweep: 32, x: 31.2, y: 0.25, dihedral: 6 },
    fin: { rootC: 6.3, tipC: 2.4, h: 5.9, sweep: 40, x: 28.7 },
    win: [{ x0: 6.6, x1: 31.4, sp: 0.533, w: 0.24, h: 0.34, y: 0.42 }], doors: [4.1, 15.3, 16.2, 32.6],
    cockpit: { style: 'airbus' } },
  a21n: { name: 'Airbus A321neo', cls: 'C', L: 44.51, R: 1.98, top: 1.07, Hc: 4.1, Ln: 6.0, Lt: 11.8,
    wing: { span: 35.8, rootLE: 16.2, rootC: 7.0, kinkZ: 6.3, kinkC: 4.3, tipC: 1.5, sweep: 27, dihedral: 5.1, y: 0.62, tcRoot: 0.15, tcTip: 0.11, tip: 'sharklet', tipH: 2.4, flex: 0.2 },
    eng: [{ z: 5.75, len: 4.9, r: 1.12, y: 1.35, fwd: 2.8 }],
    gear: { main: [{ x: 22.1, z: 3.8, wheels: 2 }], nose: { x: 5.2, r: 0.37 }, r: 0.6, w: 0.36 },
    hstab: { span: 12.45, rootC: 3.7, tipC: 1.45, sweep: 32, x: 38.1, y: 0.25, dihedral: 6 },
    fin: { rootC: 6.3, tipC: 2.4, h: 5.9, sweep: 40, x: 35.6 },
    win: [{ x0: 6.6, x1: 38.4, sp: 0.533, w: 0.24, h: 0.34, y: 0.42 }], doors: [4.1, 12.6, 27.9, 39.6],
    cockpit: { style: 'airbus' } },
  b738: { name: 'Boeing 737-800', cls: 'C', L: 39.47, R: 1.88, top: 1.12, Hc: 3.25, Ln: 5.6, Lt: 11.0, pointyTail: true,
    wing: { span: 35.8, rootLE: 14.2, rootC: 7.4, kinkZ: 5.4, kinkC: 4.3, tipC: 1.25, sweep: 26, dihedral: 6, y: 0.55, tcRoot: 0.15, tcTip: 0.11, tip: 'blended', tipH: 2.5, flex: 0.25 },
    eng: [{ z: 4.9, len: 4.1, r: 0.99, y: 0.95, fwd: 2.9, flat: 0.86 }],
    gear: { main: [{ x: 20.3, z: 2.86, wheels: 2 }], nose: { x: 4.7, r: 0.34 }, r: 0.56, w: 0.35 },
    hstab: { span: 14.35, rootC: 3.9, tipC: 1.3, sweep: 32, x: 33.1, y: 0.2, dihedral: 7 },
    fin: { rootC: 6.4, tipC: 2.2, h: 6.9, sweep: 36, x: 29.9, dorsal: true },
    win: [{ x0: 5.3, x1: 35.3, sp: 0.508, w: 0.24, h: 0.33, y: 0.4 }], doors: [3.3, 16.4, 17.3, 36.4],
    cockpit: { style: 'boeing' } },
  b38m: { name: 'Boeing 737 MAX 8', cls: 'C', L: 39.52, R: 1.88, top: 1.12, Hc: 3.4, Ln: 5.6, Lt: 11.2, pointyTail: true,
    wing: { span: 35.9, rootLE: 14.2, rootC: 7.4, kinkZ: 5.4, kinkC: 4.3, tipC: 1.25, sweep: 26, dihedral: 6, y: 0.55, tcRoot: 0.15, tcTip: 0.11, tip: 'split', tipH: 2.1, flex: 0.3 },
    eng: [{ z: 4.9, len: 4.6, r: 1.04, y: 0.95, fwd: 3.2, flat: 0.92 }],
    gear: { main: [{ x: 20.3, z: 2.86, wheels: 2 }], nose: { x: 4.7, r: 0.34 }, r: 0.56, w: 0.35 },
    hstab: { span: 14.35, rootC: 3.9, tipC: 1.3, sweep: 32, x: 33.1, y: 0.2, dihedral: 7 },
    fin: { rootC: 6.4, tipC: 2.2, h: 6.9, sweep: 36, x: 29.9, dorsal: true },
    win: [{ x0: 5.3, x1: 35.3, sp: 0.508, w: 0.24, h: 0.33, y: 0.4 }], doors: [3.3, 16.4, 17.3, 36.4],
    cockpit: { style: 'boeing' } },
  b752: { name: 'Boeing 757-200', cls: 'C', L: 47.32, R: 1.88, top: 1.12, Hc: 4.25, Ln: 6.2, Lt: 12.0, pointyTail: true,
    wing: { span: 38.05, rootLE: 16.8, rootC: 8.4, kinkZ: 6.0, kinkC: 5.0, tipC: 1.7, sweep: 27, dihedral: 5.5, y: 0.6, tcRoot: 0.15, tcTip: 0.11, tip: 'blended', tipH: 2.6, flex: 0.35 },
    eng: [{ z: 6.8, len: 5.9, r: 1.17, y: 1.45, fwd: 4.0 }],
    gear: { main: [{ x: 23.0, z: 3.66, wheels: 4 }], nose: { x: 4.6, r: 0.4 }, r: 0.57, w: 0.36 },
    hstab: { span: 15.2, rootC: 4.4, tipC: 1.5, sweep: 32, x: 40.6, y: 0.2, dihedral: 7 },
    fin: { rootC: 7.3, tipC: 2.6, h: 7.5, sweep: 38, x: 36.8 },
    win: [{ x0: 5.4, x1: 42.5, sp: 0.508, w: 0.24, h: 0.33, y: 0.4 }], doors: [3.6, 11.8, 20.6, 21.4, 42.9],
    cockpit: { style: 'boeing' } },
  b763: { name: 'Boeing 767-300ER', cls: 'E', L: 54.94, R: 2.51, top: 1.06, Hc: 5.25, Ln: 7.4, Lt: 14.5,
    wing: { span: 50.9, rootLE: 19.6, rootC: 11.2, kinkZ: 8.0, kinkC: 6.8, tipC: 2.0, sweep: 33, dihedral: 6, y: 0.6, tcRoot: 0.15, tcTip: 0.11, tip: 'blended', tipH: 3.4, flex: 0.5 },
    eng: [{ z: 7.9, len: 6.1, r: 1.48, y: 1.7, fwd: 3.9 }],
    gear: { main: [{ x: 27.9, z: 4.65, wheels: 4 }], nose: { x: 5.1, r: 0.5 }, r: 0.64, w: 0.43 },
    hstab: { span: 18.6, rootC: 5.6, tipC: 1.8, sweep: 34, x: 47.3, y: 0.25, dihedral: 7 },
    fin: { rootC: 9.2, tipC: 3.2, h: 8.6, sweep: 40, x: 43.4 },
    win: [{ x0: 7.4, x1: 49.0, sp: 0.508, w: 0.26, h: 0.38, y: 0.45 }], doors: [4.3, 14.2, 26.9, 50.3],
    cockpit: { style: 'boeing' } },
  b77w: { name: 'Boeing 777-300ER', cls: 'E', L: 73.86, R: 3.1, top: 1.03, Hc: 5.95, Ln: 9.5, Lt: 20.0,
    wing: { span: 64.8, rootLE: 26.0, rootC: 14.0, kinkZ: 10.8, kinkC: 8.2, tipC: 2.2, sweep: 33, dihedral: 6, y: 0.62, tcRoot: 0.14, tcTip: 0.1, tip: 'raked', tipH: 3.8, flex: 0.6 },
    eng: [{ z: 9.7, len: 7.3, r: 1.98, y: 2.1, fwd: 3.4 }],
    gear: { main: [{ x: 38.2, z: 5.5, wheels: 6 }], nose: { x: 7.0, r: 0.6 }, r: 0.66, w: 0.45 },
    hstab: { span: 21.5, rootC: 7.4, tipC: 2.5, sweep: 35, x: 60.0, y: 0.3, dihedral: 7 },
    fin: { rootC: 11.5, tipC: 4.0, h: 9.4, sweep: 42, x: 55.2 },
    // cabin windows: Boeing CAD 3-view 777-300 (boeing.com/commercial/airports/3-view, 7773.zip), measured by
    // tools/liveries/windows_ref.py: first / last window 8.08 / 58.32 m, pitch 0.562 m, window 0.30 x 0.41 m, centre 0.43 m
    // above the fuselage centre line (eta 0.138 of the 6.17 m section); the 777-200 drawing (7772.zip) ends at 48.19 m = this
    // row with the 10.13 m shorter fuselage (derive() below)
    win: [{ x0: 8.08, x1: 58.32, sp: 0.562, w: 0.30, h: 0.41, y: 0.43 }], doors: [5.6, 17.8, 36.0, 51.0, 64.8],
    cockpit: { style: 'boeing' } },
  b789: { name: 'Boeing 787-9', cls: 'E', L: 62.81, R: 2.9, top: 1.03, Hc: 5.55, Ln: 8.6, Lt: 16.5,
    wing: { span: 60.1, rootLE: 22.8, rootC: 12.4, kinkZ: 9.4, kinkC: 7.3, tipC: 1.7, sweep: 34, dihedral: 6.5, y: 0.6, tcRoot: 0.14, tcTip: 0.095, tip: 'raked', tipH: 3.5, flex: 1.6 },
    eng: [{ z: 8.9, len: 6.5, r: 1.62, y: 1.85, fwd: 3.2, chevron: true }],
    gear: { main: [{ x: 33.0, z: 4.9, wheels: 4 }], nose: { x: 7.3, r: 0.55 }, r: 0.64, w: 0.44 },
    hstab: { span: 19.5, rootC: 6.3, tipC: 2.1, sweep: 36, x: 51.2, y: 0.35, dihedral: 7 },
    fin: { rootC: 10.2, tipC: 3.6, h: 8.9, sweep: 42, x: 47.4 },
    win: [{ x0: 9.4, x1: 53.5, sp: 0.53, w: 0.29, h: 0.46, y: 0.5 }], doors: [5.2, 17.6, 36.2, 53.5],
    cockpit: { style: '787' } },
  a359: { name: 'Airbus A350-900', cls: 'E', L: 66.8, R: 2.98, top: 1.03, Hc: 5.6, Ln: 8.8, Lt: 17.5,
    wing: { span: 64.75, rootLE: 24.8, rootC: 13.6, kinkZ: 10.0, kinkC: 7.6, tipC: 1.8, sweep: 34, dihedral: 6, y: 0.6, tcRoot: 0.14, tcTip: 0.095, tip: 'curved', tipH: 2.6, flex: 1.2 },
    eng: [{ z: 9.6, len: 7.2, r: 1.8, y: 2.0, fwd: 3.3 }],
    gear: { main: [{ x: 35.0, z: 5.3, wheels: 4 }], nose: { x: 6.3, r: 0.55 }, r: 0.66, w: 0.45 },
    hstab: { span: 18.8, rootC: 6.3, tipC: 2.1, sweep: 34, x: 57.5, y: 0.3, dihedral: 6 },
    fin: { rootC: 10.5, tipC: 3.8, h: 9.4, sweep: 40, x: 52.8 },
    win: [{ x0: 9.2, x1: 58.0, sp: 0.53, w: 0.28, h: 0.44, y: 0.5 }], doors: [5.8, 17.6, 40.8, 58.6],
    cockpit: { style: 'a350' } },
  b748: { name: 'Boeing 747-8', cls: 'E', L: 76.25, R: 3.25, top: 1.03, Hc: 6.25, Ln: 9.0, Lt: 20.0,
    hump: { x1: 34.0, h: 2.75 }, noseTip: 0.05,
    wing: { span: 68.4, rootLE: 25.0, rootC: 16.8, kinkZ: 13.0, kinkC: 9.6, tipC: 2.8, sweep: 38, dihedral: 7, y: 0.62, tcRoot: 0.14, tcTip: 0.09, tip: 'raked', tipH: 4.2, flex: 1.0 },
    eng: [{ z: 12.6, len: 6.3, r: 1.58, y: 1.9, fwd: 3.6, chevron: true }, { z: 21.4, len: 6.3, r: 1.58, y: 1.6, fwd: 3.0, chevron: true }],
    gear: { main: [{ x: 35.2, z: 5.5, wheels: 4 }, { x: 38.4, z: 1.9, wheels: 4 }], nose: { x: 6.8, r: 0.6 }, r: 0.64, w: 0.44 },
    hstab: { span: 22.2, rootC: 8.2, tipC: 2.6, sweep: 38, x: 64.0, y: 0.3, dihedral: 7 },
    fin: { rootC: 13.0, tipC: 4.4, h: 11.2, sweep: 45, x: 57.8 },
    win: [{ x0: 9.0, x1: 67.0, sp: 0.51, w: 0.27, h: 0.4, y: 0.52 }, { x0: 10.5, x1: 30.5, sp: 0.51, w: 0.26, h: 0.38, y: 4.05 }], doors: [6.3, 16.8, 33.0, 49.5, 64.8],
    cockpit: { style: 'b747', du: 0.12, dv: 0.78 } },
  a388: { name: 'Airbus A380-800', cls: 'F', L: 72.72, R: 3.57, top: 1.36, Hc: 5.9, Ln: 9.5, Lt: 19.0,
    wing: { span: 79.75, rootLE: 22.0, rootC: 19.0, kinkZ: 16.0, kinkC: 10.5, tipC: 3.4, sweep: 34, dihedral: 5.6, y: 0.72, tcRoot: 0.13, tcTip: 0.09, tip: 'fence', tipH: 2.6, flex: 0.8 },
    eng: [{ z: 15.5, len: 6.4, r: 1.72, y: 2.0, fwd: 3.5 }, { z: 25.6, len: 6.4, r: 1.72, y: 1.7, fwd: 2.6 }],
    gear: { main: [{ x: 33.8, z: 6.0, wheels: 4 }, { x: 37.4, z: 2.7, wheels: 6 }], nose: { x: 5.4, r: 0.62 }, r: 0.7, w: 0.47 },
    hstab: { span: 30.4, rootC: 9.5, tipC: 3.2, sweep: 34, x: 60.0, y: 0.4, dihedral: 5 },
    fin: { rootC: 14.5, tipC: 5.2, h: 13.3, sweep: 40, x: 55.5 },
    win: [{ x0: 9.5, x1: 64.5, sp: 0.53, w: 0.27, h: 0.4, y: 0.35 }, { x0: 11.5, x1: 61.0, sp: 0.53, w: 0.27, h: 0.4, y: 3.2 }], doors: [5.6, 17.2, 32.5, 46.8, 61.4],
    cockpit: { style: 'airbus', du: -0.07, dAdd: 0.1, dv: 0.12 } },
  e75l: { name: 'Embraer E175', cls: 'C', L: 31.68, R: 1.505, top: 1.05, Hc: 2.95, Ln: 4.6, Lt: 9.2,
    wing: { span: 28.65, rootLE: 11.6, rootC: 5.6, kinkZ: 4.4, kinkC: 3.4, tipC: 1.2, sweep: 25, dihedral: 5, y: 0.55, tcRoot: 0.15, tcTip: 0.11, tip: 'small', tipH: 1.4, flex: 0.15 },
    eng: [{ z: 4.95, len: 3.5, r: 0.74, y: 0.95, fwd: 2.2 }],
    gear: { main: [{ x: 18.2, z: 2.97, wheels: 2 }], nose: { x: 3.4, r: 0.3 }, r: 0.5, w: 0.3 },
    hstab: { span: 10.0, rootC: 3.0, tipC: 1.1, sweep: 32, x: 26.6, y: 0.2, dihedral: 7 },
    fin: { rootC: 5.2, tipC: 2.0, h: 5.1, sweep: 42, x: 24.4 },
    win: [{ x0: 4.6, x1: 27.6, sp: 0.53, w: 0.25, h: 0.35, y: 0.28 }], doors: [2.9, 27.9],
    cockpit: { style: 'ejet' } },
  crj9: { name: 'Bombardier CRJ900', cls: 'C', L: 36.2, R: 1.34, top: 1.04, Hc: 2.45, Ln: 4.4, Lt: 8.5, pointyTail: true,
    wing: { span: 24.85, rootLE: 16.2, rootC: 4.8, kinkZ: 3.6, kinkC: 3.2, tipC: 1.15, sweep: 26.5, dihedral: 3, y: 0.55, tcRoot: 0.14, tcTip: 0.11, tip: 'small', tipH: 1.3, flex: 0.1 },
    eng: [], rear: { x: 26.4, z: 2.6, y: 0.45, len: 3.9, r: 0.72 },
    gear: { main: [{ x: 20.5, z: 2.0, wheels: 2 }], nose: { x: 3.2, r: 0.3 }, r: 0.47, w: 0.28 },
    hstab: { span: 8.5, rootC: 2.7, tipC: 1.4, sweep: 32, x: 34.2, y: 0, dihedral: -2, tTail: true },
    fin: { rootC: 5.6, tipC: 3.0, h: 4.6, sweep: 45, x: 29.8 },
    win: [{ x0: 4.4, x1: 30.0, sp: 0.508, w: 0.23, h: 0.3, y: 0.25 }], doors: [2.8, 17.9],
    cockpit: { style: 'boeing' } },
  bcs3: { name: 'Airbus A220-300', cls: 'C', L: 38.7, R: 1.85, top: 1.06, Hc: 3.4, Ln: 5.5, Lt: 11.0,
    wing: { span: 35.1, rootLE: 14.7, rootC: 6.6, kinkZ: 5.4, kinkC: 4.1, tipC: 1.3, sweep: 26, dihedral: 5, y: 0.6, tcRoot: 0.14, tcTip: 0.1, tip: 'small', tipH: 1.6, flex: 0.3 },
    eng: [{ z: 5.3, len: 4.5, r: 1.06, y: 1.15, fwd: 2.9 }],
    gear: { main: [{ x: 19.7, z: 3.35, wheels: 2 }], nose: { x: 4.4, r: 0.36 }, r: 0.56, w: 0.34 },
    hstab: { span: 11.5, rootC: 3.6, tipC: 1.3, sweep: 32, x: 33.2, y: 0.25, dihedral: 7 },
    fin: { rootC: 6.5, tipC: 2.4, h: 6.3, sweep: 40, x: 30.3 },
    win: [{ x0: 5.8, x1: 33.6, sp: 0.53, w: 0.3, h: 0.44, y: 0.42 }], doors: [3.8, 16.9, 34.2],
    cockpit: { style: 'a220' } },
};

// ---------------------------------------------------------------------------------------------------------------- SPEC
// documents (downloaded to refs/cache/acap/, gitignored; URLs in tools/models/check_dims.py)
export const DOCS = {
  NG: 'Boeing D6-58325-7 Rev C (Oct 2025) 737NG ACAP', MAX: 'Boeing D6-38A004 Rev K (Jul 2025) 737 MAX ACAP',
  B757: 'Boeing D6-58327 Rev H (Dec 2024) 757 ACAP', B767: 'Boeing D6-58328 Rev K (Dec 2024) 767 ACAP',
  B777: 'Boeing D6-58329 Rev E (Dec 2024) 777-200/-200ER/-300 ACAP', B777LR: 'Boeing D6-58329-2 Rev G (Dec 2024) 777-200LR/-300ER/F ACAP',
  B777X: 'Boeing D6-86073 Rev G (Sep 2025, preliminary) 777-9 ACAP', B787: 'Boeing D6-58333 Rev Q (Oct 2025) 787 ACAP',
  B744: 'Boeing D6-58326-1 Rev F (Dec 2024) 747-400 ACAP', B748: 'Boeing D6-58326-3 Rev E (Jan 2026) 747-8 ACAP',
  AC319: 'Airbus AC A319 (Rev Jul 15/25)', AC320: 'Airbus AC A320 (Rev Jun 01/24)', AC321: 'Airbus AC A321 (Rev Jul 15/25)',
  AC330: 'Airbus AC A330 (Rev Dec 01/25)', AC350: 'Airbus AC A350 (Rev Jul 15/25)', AC380: 'Airbus AC A380 (Rev Dec 01/25)',
  A221: 'Airbus A220-100 APP BD500-3AB48-22000-00 (2023-09-08)', A223: 'Airbus A220-300 APP BD500-3AB48-32000-00 (2022-05-12)',
  E175: 'Embraer APM-2259 E175 (May 25/18, NTSB DCA20IA014)', E190: 'Embraer APM-1901 E190 (May 21/21)', E195: 'Embraer APM-1997 E195 (Oct 07/08)',
  CRJ2: 'Bombardier CSP A-020 Rev 8 CRJ100/200 APM', CRJ7: 'Bombardier CSP B-020 Rev 15 CRJ700 APM', CRJ9: 'Bombardier CSP C-020 Rev 11 CRJ900 APM',
  MD11: 'Boeing MD-11 ACAP Rev E (2023)', MODEL: 'source-model geometry (FlightAirMap/FlightGear), tools/models/model_features.py', NONE: 'no primary document obtained',
};
const NG_CL = { crown: [5.41, 5.56], sill: [2.59, 2.74] };            // NG §2.3.1-2.3.3: A top of fuselage, B entry door no 1 (-700/-800)
const A32F = { crown: [5.86, 5.97], sill: [3.38, 3.48] };             // AC A320 FIG-2-3-0-991-032 (A320neo): fuselage top, D1
export const SPEC = {
  // ---- Boeing 737 (NG: §2.2 general dims, §2.3 ground clearances, §2.7.1 door 1 "16 ft 6 in (5.03 m)"; MAX: §2.2, §2.3, §2.7.1 p.2-26 table)
  b736: { doc: 'NG', L: 31.24, span: 34.32, H: [12.45, 12.70], crown: [5.38, 5.54], sill: [2.59, 2.74], nose: 4.09, main: [15.32], track: 5.72, doors: [5.03, 23.65],
    src: '§2.2.1 p.2-9 (L, span without winglets, nose gear 13 ft 5 in, wheelbase 36 ft 10 in, track 18 ft 9 in), §2.3.1 p.2-17', inf: ['doors[1]: aft door = MAX aft-door-to-tail distance 7.59 m'] },
  b737: { doc: 'NG', L: 33.63, span: 35.79, H: [12.45, 12.67], ...NG_CL, nose: 4.09, main: [16.69], track: 5.72, doors: [5.03, 26.04],
    src: '§2.2.4 p.2-12 (-700W; without winglets 34.32), §2.3.3 p.2-19', inf: ['doors[1] (as b736)'] },
  b738: { doc: 'NG', L: 39.47, span: 35.79, H: [12.37, 12.62], ...NG_CL, nose: 4.09, main: [19.69], track: 5.72, doors: [5.03, 31.88],
    src: '§2.2.6 p.2-14 (-800W), §2.3.3 p.2-19', inf: ['doors[1] = 737-8 aft door (same fuselage, MAX §2.7.1)'] },
  b739: { doc: 'NG', L: 42.11, span: 35.79, H: [12.37, 12.62], crown: [5.44, 5.59], sill: [2.59, 2.74], nose: 4.09, main: [21.26], track: 5.72, doors: [5.03, 34.52],
    src: '§2.2.8 p.2-16 (-900ERW), §2.3.3 p.2-19', inf: ['doors[1] = 737-9 aft door'] },
  b37m: { doc: 'MAX', L: 35.56, span: 35.92, H: [11.84, 12.50], crown: [5.05, 5.51], sill: [2.77, 3.07], nose: 4.09, main: [17.45], track: 5.72, doors: [5.03, 27.97],
    src: '§2.2.1 p.2-9 (nose gear 13 ft 5 in, wheelbase 43 ft 10 in), §2.3.1 p.2-13 (A, B, P), §2.7.1 p.2-26 (B, H)' },
  b38m: { doc: 'MAX', L: 39.47, span: 35.92, H: [11.86, 12.45], crown: [5.08, 5.51], sill: [2.77, 3.07], nose: 4.09, main: [19.69], track: 5.72, doors: [5.03, 31.88],
    src: '§2.2.2 p.2-10, §2.3.2 p.2-14, §2.7.1 p.2-26' },
  b39m: { doc: 'MAX', L: 42.11, span: 35.92, H: [11.89, 12.40], crown: [5.08, 5.51], sill: [2.79, 3.07], nose: 4.09, main: [21.26], track: 5.72, doors: [5.03, 34.52],
    src: '§2.2.3 p.2-11, §2.3.3 p.2-15, §2.7.1 p.2-26' },
  b3xm: { doc: 'MAX', L: 43.79, span: 35.92, H: [11.91, 12.45], crown: [5.08, 5.54], sill: [2.77, 3.07], nose: 4.09, main: [22.43], track: 5.72, doors: [5.03, 36.20],
    src: '§2.2.4 p.2-12 (preliminary), §2.3.4 p.2-16, §2.7.1 p.2-26' },
  // ---- Boeing 757 (§2.3: A fuselage top, C door 1 sill; letters identified on the figure)
  b752: { doc: 'B757', L: 47.32, span: 38.05, H: [13.49, 13.74], crown: [6.25, 6.45], sill: [3.79, 4.01], nose: 5.89, main: [24.18], track: 7.32, doors: [5.05, 13.99, 38.23],
    src: '§2.2.1 p.2-10, §2.3.1 p.2-12, §2.7.1 p.2-21 ("nose to center of door")', unv: ['span with blended winglets (STC) not in the ACAP: per airframe'] },
  b753: { doc: 'B757', L: 54.43, span: 38.06, H: [13.56, 13.64], crown: [6.27, 6.50], sill: [3.79, 4.01], nose: 5.89, main: [28.24], track: 7.32, doors: [5.05, 13.99, 35.99, 45.34],
    src: '§2.2.2 p.2-11, §2.3.2 p.2-13, §2.7.1 p.2-21' },
  // ---- Boeing 767 (§2.3: A fuselage top, C door 1 sill; §2.7.1 p.2-30: door 2 "OPTION ON -300, -300ER, STANDARD ON -400ER")
  b762: { doc: 'B767', L: 48.51, span: 47.57, H: [15.60, 16.13], crown: [7.16, 7.47], sill: [4.09, 4.47], nose: 4.55, main: [24.24], track: 9.30, doors: [5.70, 36.12],
    src: '§2.2.1 p.2-8 (nose 14 ft 11 in, wheelbase 64 ft 7 in), §2.3.1 p.2-12, §2.7.1 p.2-30' },
  b763: { doc: 'B767', L: 54.94, span: 47.57, H: [15.39, 16.03], crown: [7.19, 7.49], sill: [4.14, 4.50], nose: 4.55, main: [27.31], track: 9.30, doors: [5.70, 42.55], doorsOpt: [15.96],
    src: '§2.2.2 p.2-9, §2.3.2 p.2-13 (C door 1, C\' optional door 2), §2.7.1 p.2-30', unv: ['span with winglets (STC) not in the ACAP: per airframe'] },
  b764: { doc: 'B767', L: 61.37, span: 51.92, H: [16.68, 17.01], crown: [7.22, 7.46], sill: [4.13, 4.39], nose: 4.56, main: [30.76], track: 9.30, doors: [5.70, 19.34, 48.95], dock2: 2,
    src: '§2.2.4 p.2-11, §2.3.4 p.2-15, §2.7.1 p.2-30', inf: ['crown/sill letters A/C assumed as on the -300 figure'] },
  // ---- Boeing 777 (§2.3: A fuselage top, B door 1 sill, D door 2 sill, K/Q vertical tail; letters identified on the figures)
  b772: { doc: 'B777', L: 63.73, span: 60.93, H: [18.42, 18.76], crown: [8.39, 8.68], sill: [4.71, 5.00], sill2: [4.88, 5.07], nose: 5.89, main: [31.77], track: 10.97, doors: [6.75, 17.07, 36.33, 49.54], dock2: 2,
    src: '§2.2.1 p.2-8, §2.3.1 p.2-10, §2.7.1 p.2-23' },
  b77l: { doc: 'B777LR', L: 63.73, span: 64.80, H: [18.48, 18.75], crown: [8.36, 8.70], sill: [4.69, 5.06], sill2: [4.85, 5.11], nose: 5.89, main: [31.78], track: 10.97, doors: [6.74, 17.07, 36.32, 49.53], dock2: 2,
    src: '§2.2.1 p.2-3, §2.3.1 p.2-6, §2.7.1 p.2-19' },
  b773: { doc: 'B777', L: 73.86, span: 60.93, H: [18.42, 18.76], crown: [8.39, 8.68], sill: [4.71, 5.00], sill2: [4.88, 5.07], nose: 5.89, main: [37.11], track: 10.97, doors: [6.74, 17.07, 32.92, 46.46, 59.67], dock2: 2,
    src: '§2.2.2 p.2-9 (L 242 ft 4 in, span 199 ft 11 in, wheelbase 102 ft 5 in), §2.3.2 p.2-11', inf: ['doors = 777-300ER table (D6-58329-2 §2.7.1), same fuselage'] },
  b77w: { doc: 'B777LR', L: 73.86, span: 64.80, H: [18.24, 18.85], crown: [8.46, 8.78], sill: [4.80, 5.13], sill2: [4.92, 5.20], nose: 5.89, main: [37.11], track: 10.97, doors: [6.74, 17.07, 32.92, 46.46, 59.67], dock2: 2,
    src: '§2.2.2 p.2-4, §2.3.2 p.2-7, §2.7.1 p.2-19' },
  b779: { doc: 'B777X', L: 76.73, span: 64.85, spanExt: 71.76, H: [19.28, 19.74], crown: [8.46, 8.79], sill: [4.78, 5.13], sill2: [4.98, 5.23], nose: 5.89, main: [38.22], track: 10.82,
    doors: [6.76, 23.47, 42.72, 61.80], doorsOpt: [50.06], dock2: 2,
    src: 'Fig 2-1 p.2-3 (L 251 ft 9 in; nose gear 19 ft 4 in; wheelbase 106 ft 1 in; track 35 ft 6 in; ground span = folded 212 ft 9 in, extended 235 ft 5 in), Table 2-2 p.2-4 (A, B, E, Q), Table 2-3 p.2-10' },
  // ---- Boeing 787 (§2.3: A fuselage top, B door 1 sill, E door 2 sill, N vertical tail)
  b788: { doc: 'B787', L: 56.72, span: 60.12, H: [16.59, 17.09], crown: [7.67, 8.03], sill: [4.24, 4.72], sill2: [4.39, 4.70], nose: 5.41, main: [28.19], track: 9.80, doors: [6.30, 15.32, 32.39, 43.56], dock2: 2,
    src: '§2.2.1 p.2-5, §2.3.1 p.2-8, §2.7.1 p.2-16' },
  b789: { doc: 'B787', L: 62.81, span: 60.12, H: [16.81, 17.09], crown: [7.42, 7.82], sill: [4.24, 4.80], sill2: [4.42, 4.80], nose: 5.41, main: [31.24], track: 9.80, doors: [6.30, 18.36, 35.43, 49.66], dock2: 2,
    src: '§2.2.2 p.2-6, §2.3.2 p.2-9, §2.7.1 p.2-16' },
  b78x: { doc: 'B787', L: 68.30, span: 60.12, H: [16.89, 17.02], crown: [7.92, 8.15], sill: [4.27, 4.70], sill2: [4.47, 4.75], nose: 5.41, main: [34.29], track: 9.80, doors: [6.30, 21.41, 38.48, 55.14], dock2: 2,
    src: '§2.2.3 p.2-7, §2.3.3 p.2-10, §2.7.1 p.2-16' },
  // ---- Boeing 747 (§2.3: A upper-deck top, B main-deck top, C door 1 sill, S door 2 sill, K vertical tail)
  b744: { doc: 'B744', L: 70.67, span: 64.44, spanRange: [64.44, 64.92], H: [18.80, 19.51], crown: [9.80, 10.23], crownMain: [7.53, 7.91], sill: [4.74, 5.18], sill2: [4.80, 5.15],
    nose: 7.75, main: [33.35, 36.42], track: 11.00, trackB: 3.83, doors: [9.50, 18.80, 30.61, 40.74, 55.14], dock2: 2,
    src: '§2.2.1 p.2-14 (span 64.44 jig / 64.92 at MGW; wheelbase to wing gear), §2.3.1 p.2-17, §2.7.1 p.2-35', inf: ['trackB = 747-8 body-gear track (same body gear)'] },
  b748: { doc: 'B748', L: 76.25, span: 68.40, H: [18.97, 19.51], crown: [9.44, 9.84], crownMain: [7.56, 7.90], sill: [4.78, 5.16], sill2: [4.87, 5.14],
    nose: 7.74, main: [37.40, 40.47], track: 10.99, trackB: 3.83, doors: [9.5, 22.9, 34.7, 46.3, 60.8], dock2: 2,
    src: '§2.2.2 p.2-5 (wheelbase 97 ft 4 in to the wing gear, body gear +10 ft 1 in, body-gear track 12 ft 7 in), §2.3.2 p.2-7, §2.7.1 p.2-14' },
  // ---- Airbus A320 family (AC 2-2-0 general dims, 2-7-0 door location; ground clearances 2-3-0)
  a319: { doc: 'AC319', L: 33.84, span: 34.10, H: [11.89, 12.05], ...A32F, nose: 5.07, main: [16.11], track: 7.59, doors: [5.04, 25.81],
    src: 'FIG-2-2-0-991-002 (wing-tip fence), FIG-2-7-0-991-002 sh.2 (over-wing exits 12.83/13.68)', inf: ['crown/sill = A320neo values (same fuselage section and gear)', 'H from FIG-2-3-0-991-028 text order'] },
  a19n: { doc: 'AC319', L: 33.84, span: 35.80, H: [11.89, 12.05], ...A32F, nose: 5.07, main: [16.11], track: 7.59, doors: [5.04, 25.81],
    src: 'FIG-2-2-0-991-008 (A319neo, sharklets), FIG-2-7-0-991-002', inf: ['crown/sill/H as a319'] },
  a320: { doc: 'AC320', L: 37.57, span: 34.10, H: [11.83, 12.08], ...A32F, nose: 5.07, main: [17.71], track: 7.59, doors: [5.04, 29.53],
    src: 'FIG-2-2-0-991-004 (wing-tip fence; sharklet 35.80), FIG-2-7-0-991-003 sh.2 (over-wing exits 14.43/15.28)', inf: ['H = A320neo range'] },
  a20n: { doc: 'AC320', L: 37.57, span: 35.80, H: [11.83, 12.08], ...A32F, nose: 5.07, main: [17.71], track: 7.59, doors: [5.04, 29.53],
    src: 'FIG-2-2-0-991-009 p.6-7, FIG-2-3-0-991-032 p.6 (VT, D1, fuselage top), FIG-2-7-0-991-003' },
  a321: { doc: 'AC321', L: 44.51, span: 34.10, H: [11.85, 12.10], crown: [5.86, 5.97], sill: [3.39, 3.48], nose: 5.07, main: [21.97], track: 7.59, doors: [5.02, 13.84, 24.79, 36.58],
    src: 'FIG-2-2-0-991-005, FIG-2-3-0-991-005 (D1 3.39-3.48), FIG-2-7-0-991-004 sh.2', inf: ['crown = A320neo values', 'H from the 2-3-0 table text order'] },
  a21n: { doc: 'AC321', L: 44.51, span: 35.80, H: [11.82, 12.10], crown: [5.86, 5.97], sill: [3.38, 3.49], nose: 5.07, main: [21.97], track: 7.59, doors: [5.02, 13.84, 24.79, 36.58],
    src: 'FIG-2-2-0-991-010 p.6-7, FIG-2-3-0-991-049 (A321neo-XLR: D1 3.38-3.49), FIG-2-7-0-991-004 (4-door cabin; ACF/XLR: 1L 5.04, over-wing 18.70/19.54, 3L 26.82, 4L 36.47)',
    inf: ['crown = A320neo values'], unv: ['door layout per airframe (4-door vs ACF)'] },
  // ---- Airbus A330 (2-3-0 tables: D1/D2 door sills, F3 fuselage top forward; VT vertical tail)
  a332: { doc: 'AC330', L: 58.82, span: 60.30, H: [17.21, 17.73], crown: [7.56, 7.75], sill: [4.44, 4.63], sill2: [4.66, 4.86], nose: 6.67, main: [28.85], track: 10.68, doors: [5.85, 14.56, 32.77, 45.63], dock2: 2,
    src: 'FIG-2-2-0-991-002 sh.2 (post-mod 48979), FIG-2-3-0-991-001-B01 (VT1 = shorter fin), FIG-2-7-0-991-006 sh.2' },
  a333: { doc: 'AC330', L: 63.67, span: 60.30, H: [16.72, 17.18], crown: [7.58, 7.74], sill: [4.41, 4.55], sill2: [4.67, 4.83], nose: 6.67, main: [32.05], track: 10.68, doors: [5.85, 17.74, 35.96, 50.96], dock2: 2,
    src: 'FIG-2-2-0-991-001 sh.1-2, FIG-2-3-0-991-001-A01, FIG-2-7-0-991-006-B01' },
  a338: { doc: 'AC330', L: 58.82, span: 64.00, H: [17.79, 18.29], crown: [7.63, 7.84], sill: [4.49, 4.71], sill2: [4.68, 4.88], nose: 6.67, main: [28.85], track: 10.68, doors: [5.85, 14.56, 32.77, 45.63], dock2: 2,
    src: 'FIG-2-2-0-991-012 p.9, FIG-2-3-0-991-036', inf: ['doors = A330-200 table'] },
  a339: { doc: 'AC330', L: 63.66, span: 64.00, H: [16.68, 17.13], crown: [7.70, 7.89], sill: [4.53, 4.73], sill2: [4.74, 4.92], nose: 6.67, main: [32.05], track: 10.68, doors: [5.85, 17.74, 35.96, 50.96], dock2: 2,
    src: 'FIG-2-2-0-991-011 p.7, FIG-2-3-0-991-035, FIG-2-7-0-991-006-B01' },
  // ---- Airbus A350 / A380
  a359: { doc: 'AC350', L: 66.80, span: 64.75, H: [17.14, 17.47], crown: [8.50, 8.64], sill: [5.04, 5.36], nose: 4.63, main: [33.29], track: 10.60, doors: [6.82, 18.86, 37.93, 52.55], dock2: 2,
    src: 'FIG-2-2-0-991-001 p.2-3, FIG-2-3-0-991-001 p.2, FIG-2-7-0-991-001 p.3' },
  a35k: { doc: 'AC350', L: 73.79, span: 64.75, H: [17.11, 17.41], crown: [8.50, 8.61], sill: [5.05, 5.36], nose: 4.63, main: [37.11], track: 10.73, doors: [6.82, 23.30, 42.38, 59.53], dock2: 2,
    src: 'FIG-2-2-0-991-002-C01, FIG-2-3-0-991-009-B01, FIG-2-7-0-991-001-D01', inf: ['main: wheelbase to the centre axle of the 6-wheel bogie (text order)'] },
  a388: { doc: 'AC380', L: 72.73, span: 79.75, H: [24.12, 24.27], crown: [10.75, 10.97], sill: [5.10, 5.36], nose: 4.97, main: [33.58, 36.85], track: 12.46, trackB: 5.26, doors: [6.32, 16.50], dock2: 2,
    src: 'FIG-2-2-0-991-001 p.2 (WLG 33.58, BLG 36.85, WLG track 12.46, BLG track 5.26), FIG-2-3-0-991-001 (VT, M1; upper deck U1 sill 7.87-8.08), FIG-2-7-0-991-002 (main deck M1, M2; U1 20.94)' },
  // ---- Airbus A220 (APP; door stations are not dimensioned in the APP, the ACP successor could not be downloaded)
  bcs1: { doc: 'A221', L: 34.90, span: 35.10, H: [11.5, 11.5], crown: [5.31, 5.44], sill: [2.97, 3.10], nose: 3.39, main: [16.20], track: 6.70, doors: [4.94, 26.24],
    src: '§2.1 Fig 1 p.4-5 (L, span, track legible, labels lost), §3.1 Fig 2 (same clearance values as the A220-300 table)',
    inf: ['doors, main: source model door / main-gear-door objects (doorFL, doorRL, gearLdoor)', 'nose = A220-300 (same forward fuselage)', 'crown/sill = A220-300 Fig 2 A, D'], unv: ['H'] },
  bcs3: { doc: 'A223', L: 38.69, span: 34.98, H: [11.73, 11.73], crown: [5.31, 5.44], sill: [2.97, 3.10], nose: 3.39, main: [18.70], track: 6.73, doors: [4.94],
    src: '§2.1 Table 5 + Fig 1, §3.1 Fig 2 p.10 (A fuselage top, D forward door sill)', inf: ['doors[0] = A220-100 model door object (same forward fuselage)'] },
  // ---- Embraer (APM §2.2 general dims, §2.3 ground clearances: (C) forward passenger door; Fig 2.2 door 0.85 m wide, 1L forward edge 4.71 m)
  e170: { doc: 'NONE', L: 29.90, span: 26.00, H: [9.67, 9.67], sill: [2.54, 2.64], nose: 4.13, main: [14.63], track: 5.20, doors: [5.14],
    src: 'no E170 APM (APM_170.pdf 404, not archived)', inf: ['nose, track, sill, doors = E175 (same nose section and gear)'], unv: ['L', 'span', 'H', 'main'] },
  e75l: { doc: 'E175', L: 31.68, span: 28.65, H: [9.54, 9.86], sill: [2.54, 2.64], nose: 4.13, main: [15.53], track: 5.20, doors: [5.14],
    src: '§2.2.2 p.2-3 (enhanced wingtip), Fig 2.2, Table 2.3 (C forward passenger door, K vertical tail)', inf: ['doors[0] = 1L forward edge 4.71 + 0.85/2'] },
  e75s: { doc: 'E175', L: 31.68, span: 26.00, H: [9.54, 9.86], sill: [2.54, 2.64], nose: 4.13, main: [15.53], track: 5.20, doors: [5.14],
    src: '§2.2.1 p.2-3 (winglet, pre SB 170-57-0058), Fig 2.1, Table 2.2', inf: ['doors[0] as e75l'] },
  e190: { doc: 'E190', L: 36.24, span: 28.72, H: [10.33, 10.57], sill: [2.58, 2.63], nose: 4.13, main: [17.96], track: 5.94, doors: [5.14],
    src: '§2.2 p.2-3, Fig 2.1 p.2-4 (nose gear 4.13, wheelbase 13.83), Fig 2.2 (door 0.85 m), Table 2.3 p.2-10 (C, L)', inf: ['doors[0] = 4.71 + 0.85/2'] },
  e195: { doc: 'E195', L: 38.65, span: 28.72, H: [10.29, 10.57], sill: [2.58, 2.66], nose: 4.13, main: [18.77], track: 5.94, doors: [5.14],
    src: '§2.2.3 p.2-3 (fuselage 38.65), Fig 2.1 p.2-4, Table 2.3 p.2-11', inf: ['nose = E190 (same nose section: door edges 4.71/4.27 as E190)', 'wheelbase 14.64 assigned by magnitude', 'doors[0] as e190'] },
  // ---- Bombardier CRJ (APM 00-02-01/02 dims, 00-02-04 door clearances)
  crj2: { doc: 'CRJ2', L: 26.77, span: 21.23, H: [6.18, 6.32], crown: [3.84, 4.04], sill: [1.50, 1.73], nose: 2.14, main: [13.54], track: 3.14, doors: [4.74],
    src: '00-02-01 Fig 2 p.5 (wheelbase 11.4, half-track 1.57), Fig 3 p.6', inf: ['nose gear and door 1 scaled off Fig 2 (0.91 m door)', 'track = 2 x 1.57'] },
  crj7: { doc: 'CRJ7', L: 32.34, span: 23.25, H: [7.51, 7.51], sill: [1.73, 1.73], nose: 2.23, main: [17.24], track: 4.12, doors: [4.68],
    src: '00-02-02 Table 1/2 (L 32.3, wheelbase 15.01), Fig 1 p.3 (sill 68.0 in), 00-02-04 Table 1 (passenger door FWD side to radome 4.22 m)', inf: ['nose gear scaled off Fig 1 (vector drawing, 11.4 pt/m)', 'doors[0] = 4.22 + 0.91/2'] },
  crj9: { doc: 'CRJ9', L: 36.24, span: 24.85, H: [7.35, 7.35], sill: [1.73, 1.73], nose: 2.24, main: [19.54], track: 4.07, doors: [4.68],
    src: '00-02-02 Table 1 p.1/p.8 (span 24.85 for 15036+, 23.24 before), Table 2 (wheelbase 17.30), Fig 1 (sill 68.0 in), 00-02-04 Table 1 (4.22 m)', inf: ['nose gear scaled off Fig 1', 'doors[0] = 4.22 + 0.91/2'] },
  // ---- McDonnell Douglas MD-11 (Boeing MD-11 ACAP Rev E, 2023; image-only PDF, read from the rendered figures §2.2 p.2-4, §2.3 p.2-5)
  md11: { doc: 'MD11', L: 61.6, span: 51.97, H: [17.53, 17.93], crown: [8.27, 8.69], sill: [4.81, 5.31], nose: 8.5, main: [33.1], track: 10.7, doors: [5.3, 14.9, 28.6, 47.2], dock2: 2,
    src: '§2.2 p.2-4 (L 202 ft 2 in with CF6-80C2D1F; span 170 ft 6 in max with fuel; nose gear 27 ft 10 in; wheelbase 80 ft 9 in; track 35 ft 0 in), §2.3 p.2-5 (C door 1 sill, L vertical tail)',
    inf: ['crown = B (letter identified by magnitude)', 'doors scaled off the §2.2 side view (10.1 px/m)'] },
};
// Not given an airframe (shown as markers, not as a look-alike, until a primary source is obtained):
//   E290/E295 (E-Jet E2): the E2 APM could not be downloaded (techcare.embraer.com 502; the embraer.com spec sheet has no dimensions);
//   A318, CRJX (CRJ1000), B778 (777-8): no document transcribed; none seen at SFO (docs/research/liveries.md census).

// ---------------------------------------------------------------------------------------------------------------- derived airframes
// A derived airframe copies the geometry of its base and moves the wing by the forward fuselage plug (the main-gear
// station difference unless the document shows the plug elsewhere) and the tail by the length difference.
export function derive(baseKey, key, name, extra = {}, fwdPlug = null) {
  const B = JSON.parse(JSON.stringify(TYPES[baseKey])); const S = SPEC[key], SB = SPEC[baseKey];
  const dL = S.L - SB.L; const d1 = fwdPlug ?? (S.main[0] - SB.main[0]);
  const T = Object.assign(B, { name, L: S.L });
  T.wing.rootLE += d1; T.hstab.x += dL; T.fin.x += dL; if (T.rear) T.rear.x += dL;
  T.win.forEach(w => { w.x1 += dL; });
  return (TYPES[key] = Object.assign(T, extra));
}
derive('b738', 'b736', 'Boeing 737-600'); derive('b738', 'b737', 'Boeing 737-700'); derive('b738', 'b739', 'Boeing 737-900ER');
derive('b38m', 'b37m', 'Boeing 737 MAX 7'); derive('b38m', 'b39m', 'Boeing 737 MAX 9'); derive('b38m', 'b3xm', 'Boeing 737 MAX 10');
derive('a20n', 'a319', 'Airbus A319', { eng: [{ z: 5.75, len: 4.4, r: 1.0, y: 1.25, fwd: 2.6 }] }); derive('a20n', 'a19n', 'Airbus A319neo');
derive('a20n', 'a320', 'Airbus A320', { eng: [{ z: 5.75, len: 4.4, r: 1.0, y: 1.25, fwd: 2.6 }] });
derive('a21n', 'a321', 'Airbus A321', { eng: [{ z: 5.75, len: 4.4, r: 1.0, y: 1.25, fwd: 2.6 }] });
derive('b752', 'b753', 'Boeing 757-300');
derive('b763', 'b762', 'Boeing 767-200'); derive('b763', 'b764', 'Boeing 767-400ER');
derive('b77w', 'b772', 'Boeing 777-200ER', { eng: [{ z: 9.3, len: 6.6, r: 1.72, y: 2.0, fwd: 3.2 }] }); derive('b77w', 'b77l', 'Boeing 777-200LR');
derive('b77w', 'b773', 'Boeing 777-300', { eng: [{ z: 9.3, len: 6.6, r: 1.72, y: 2.0, fwd: 3.2 }] }); derive('b77w', 'b779', 'Boeing 777-9', { eng: [{ z: 10.64, len: 7.6, r: 2.1, y: 2.2, fwd: 3.6 }] });
derive('b789', 'b788', 'Boeing 787-8'); derive('b789', 'b78x', 'Boeing 787-10');
derive('b748', 'b744', 'Boeing 747-400');
derive('a359', 'a333', 'Airbus A330-300', { R: 2.82 }); derive('a333', 'a332', 'Airbus A330-200'); derive('a333', 'a339', 'Airbus A330-900neo'); derive('a332', 'a338', 'Airbus A330-800neo');
derive('a359', 'a35k', 'Airbus A350-1000', {}, 23.30 - 18.86); // plug ahead of door 2 (door 2 +4.44, door 3 +4.45; the 6-wheel gear sits 0.62 m further forward)
derive('e75l', 'e170', 'Embraer E170', {}, -0.9); derive('e75l', 'e75s', 'Embraer E175 (short wing)'); derive('e75l', 'e190', 'Embraer E190'); derive('e75l', 'e195', 'Embraer E195');
derive('bcs3', 'bcs1', 'Airbus A220-100');
derive('crj9', 'crj7', 'Bombardier CRJ700'); derive('crj9', 'crj2', 'Bombardier CRJ200');
derive('b763', 'md11', 'McDonnell Douglas MD-11', { R: 3.0 }, 24.2 - 19.6); // wing root LE ~24.2 m (§2.2 plan, 79 ft 6 in); planform otherwise the 767's
TYPES.a20n.eng[0].r = 1.12;

// ---------------------------------------------------------------------------------------------------------------- apply SPEC
const mid = (r) => r ? (r[0] + r[1]) / 2 : null;
function applySpec(key) {
  const T = TYPES[key], S = SPEC[key]; if (!T || !S) return;
  T.L = S.L; T.wing.span = S.span;
  const g = T.gear;
  g.main = S.main.map((x, i) => ({ ...(g.main[i] || g.main[g.main.length - 1]), x, z: (i === 0 ? S.track : (S.trackB ?? S.track)) / 2 }));
  if (key === 'a35k') g.main[0].wheels = 6;                        // A350-1000: six-wheel main bogies (AC A350 2-2-0)
  g.nose.x = S.nose;
  T.doors = S.doors.slice(); T.doorsOpt = (S.doorsOpt || []).slice(); T.dock2 = S.dock2 || null;
  T.H = mid(S.H); T.crown = mid(S.crown); T.sill = mid(S.sill); T.sill2 = mid(S.sill2) ?? T.sill;
  T.spec = S;
  // centre-line height of the procedural airframe: its fuselage top at door 1 on the published fuselage top (747: plus the
  // upper-deck hump from the upper- and main-deck tops), else from the door sill (E-Jets, CRJ700/900: sill about 0.33 R below the centre line, as in their models)
  if (S.crownMain && T.hump) { T.Hc = +(mid(S.crownMain) - (T.top || 1.03) * T.R).toFixed(2); T.hump.h = +(mid(S.crown) - mid(S.crownMain)).toFixed(2); }
  else if (S.crown) T.Hc = +(mid(S.crown) - (T.top || 1.03) * T.R).toFixed(2);
  else if (S.sill) T.Hc = +(mid(S.sill) + 0.33 * T.R).toFixed(2);
}
for (const k in SPEC) applySpec(k);

// aliases for old names
TYPES.narrow = TYPES.a20n; TYPES.wide = TYPES.b77w; TYPES.mid = TYPES.b789;
const NOSE = (k) => /^b(73|75|3[789x]m)/.test(k) ? { pt: 1.0, pb: 0.95, pw: 0.8 } : /^b7[67]/.test(k) ? { pt: 0.92, pb: 0.9, pw: 0.74 } : /^(bcs|crj)/.test(k) ? { pt: 0.97, pb: 0.93, pw: 0.8 } : null;
// upper nose profiles with a windshield "knee" (u = x/Ln, f = fraction of nose rise); smooth-nosed types (787, A350, E-Jet, 747) keep the power curve
const TOP_BOEING = [[0, 0], [0.05, 0.13], [0.15, 0.25], [0.28, 0.36], [0.33, 0.40], [0.47, 0.70], [0.58, 0.85], [0.72, 0.95], [1, 1]];
const TOP_BOEING_WIDE = [[0, 0], [0.05, 0.14], [0.15, 0.27], [0.28, 0.38], [0.32, 0.41], [0.47, 0.70], [0.60, 0.86], [0.75, 0.95], [1, 1]];
const TOP_AIRBUS = [[0, 0], [0.05, 0.16], [0.15, 0.31], [0.28, 0.43], [0.32, 0.46], [0.47, 0.72], [0.60, 0.87], [0.75, 0.96], [1, 1]];
const NOSE_TOP = (k) => /^b(73|75|3[789x]m)/.test(k) || /^(bcs|crj)/.test(k) ? TOP_BOEING : /^b7[67]/.test(k) ? TOP_BOEING_WIDE : /^(a2|a3[12]|a19)/.test(k) ? TOP_AIRBUS : null;
for (const k in TYPES) { const T = TYPES[k]; if (T.key) continue; if (!T.nose && NOSE(k)) T.nose = NOSE(k); if (!T.noseTop && NOSE_TOP(k)) T.noseTop = NOSE_TOP(k).map(p => p.slice());
  const C = T.cockpit; C.x0 = C.x0 ?? 0.28 * T.Ln; C.x1 = C.x1 ?? 0.6 * T.Ln; C.yb = C.yb ?? (C.style === 'boeing' ? 0.17 : 0.15) * T.R * (T.top > 1.2 ? 2.2 : 1); C.dmin = C.dmin ?? 0.1 * T.R; C.w = C.w ?? 2 * T.R; C.slope = C.slope ?? 0.24 * T.R; T.xMain = T.gear.main.reduce((s, g) => s + g.x, 0) / T.gear.main.length; T.track = T.gear.main[0].z * 2; T.rWheel = T.gear.r; T.xNose = T.gear.nose.x; T.rNose = T.gear.nose.r; T.doors = T.doors.slice(0, 5); T.key = k; }

// ICAO Doc 8643 designator -> TYPES key. Designators without an entry are shown as markers (no verified dimensions):
// A318, CRJX, E290, E295, B778. B74F is not a Doc 8643 designator (the 747-400F files under B744) but appears in some feeds.
// B773 is the 777-300 (non-ER, 60.93 m span). CRJ7 covers the CRJ550 (CL-600-2C11, Federal Register 2023-00130).
// E75L = "175 (long wing)", E75S = "175 (short wing)" (Doc 8643); the long wing is the enhanced wing tip (APM-2259 §2.2.2).
export const ICAO_TYPES = {
  B736: 'b736', B737: 'b737', B738: 'b738', B739: 'b739', B37M: 'b37m', B38M: 'b38m', B39M: 'b39m', B3XM: 'b3xm',
  A319: 'a319', A19N: 'a19n', A320: 'a320', A20N: 'a20n', A321: 'a321', A21N: 'a21n',
  B752: 'b752', B753: 'b753', B762: 'b762', B763: 'b763', B764: 'b764',
  B772: 'b772', B77L: 'b77l', B773: 'b773', B77W: 'b77w', B779: 'b779',
  B788: 'b788', B789: 'b789', B78X: 'b78x', B744: 'b744', B74F: 'b744', B748: 'b748',
  A332: 'a332', A333: 'a333', A338: 'a338', A339: 'a339', A359: 'a359', A35K: 'a35k', A388: 'a388',
  BCS1: 'bcs1', BCS3: 'bcs3', E170: 'e170', E75L: 'e75l', E75S: 'e75s', E190: 'e190', E195: 'e195',
  CRJ2: 'crj2', CRJ7: 'crj7', CRJ9: 'crj9', MD11: 'md11',
};
export const ICAO_MAP = ICAO_TYPES; // old name (js/livedata.js)

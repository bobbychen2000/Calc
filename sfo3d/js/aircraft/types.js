// Airliner type definitions (published dimensions, meters). x positions measured from the nose.
// wing: rootLE (x of LE at fuselage side), rootC, kinkZ/kinkC (TE kink), tipC, sweep (LE deg), dihedral (deg), y (root height as fraction of R below centerline)
// eng: list of underwing engines {z, len, r, y (offset below wing), fwd (nacelle front ahead of LE)}; rear: fuselage-mounted engines
// gear: main units [{x, z, wheels}] (z = half-track), nose {x, r}
// tip: winglet type: sharklet | blended | split | raked | curved | fence | small | none
// cockpit: {x0, x1, yb, yt, w} window band (y relative to fuselage centerline), style
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
    win: [{ x0: 10.0, x1: 64.0, sp: 0.51, w: 0.27, h: 0.4, y: 0.52 }], doors: [5.6, 17.8, 36.0, 51.0, 64.8],
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
// fuselage stretches/shrinks of a base airframe: plugs ahead of and behind the wing
export function derive(baseKey, name, L, fwdPlug, extra = {}) {
  const B = JSON.parse(JSON.stringify(TYPES[baseKey])); const dL = L - B.L; const aftPlug = dL - fwdPlug;
  const wingX = B.wing.rootLE, wingTE = B.wing.rootLE + B.wing.rootC;
  const sx = (x) => x > wingTE ? x + fwdPlug + aftPlug : x > wingX - 1 ? x + fwdPlug : x;
  const T = Object.assign(B, { name, L });
  T.wing.rootLE += fwdPlug; T.gear.main.forEach(g => g.x += fwdPlug); T.hstab.x += dL; T.fin.x += dL;
  if (T.rear) T.rear.x += dL;
  T.win.forEach(w => { w.x1 += dL; });
  T.doors = T.doors.map(sx);
  return Object.assign(T, extra);
}
TYPES.b39m = derive('b38m', 'Boeing 737 MAX 9', 42.16, 1.5);
TYPES.b739 = derive('b738', 'Boeing 737-900ER', 42.11, 1.5);
TYPES.b737 = derive('b738', 'Boeing 737-700', 33.63, -3.2);
TYPES.a319 = derive('a20n', 'Airbus A319', 33.84, -1.6);
TYPES.a320 = derive('a20n', 'Airbus A320', 37.57, 0);
TYPES.b753 = derive('b752', 'Boeing 757-300', 54.4, 3.9);
TYPES.b772 = derive('b77w', 'Boeing 777-200ER', 63.73, -5.3, { eng: [{ z: 9.3, len: 6.6, r: 1.72, y: 2.0, fwd: 3.2 }] });
TYPES.crj2 = derive('crj9', 'Bombardier CRJ200', 26.77, -4.4);
TYPES.a321 = derive('a21n', 'Airbus A321', 44.51, 0, { eng: [{ z: 5.75, len: 4.4, r: 1.0, y: 1.25, fwd: 2.6 }] });
TYPES.a20n.eng[0].r = 1.12;
// additional airframes used by the live viewer (dimensions from published lengths; gear/wing positions follow the plug)
TYPES.b788 = derive('b789', 'Boeing 787-8', 56.72, -3.05);
TYPES.b78x = derive('b789', 'Boeing 787-10', 68.28, 3.05);
TYPES.e170 = derive('e75l', 'Embraer E170', 29.90, -0.9);
TYPES.e190 = derive('e75l', 'Embraer E190', 36.24, 2.4);
TYPES.bcs1 = derive('bcs3', 'Airbus A220-100', 35.0, -1.8);
TYPES.crj7 = derive('crj9', 'Bombardier CRJ700', 32.3, -2.1);
TYPES.b762 = derive('b763', 'Boeing 767-200', 48.51, -3.2);
TYPES.b764 = derive('b763', 'Boeing 767-400ER', 61.37, 3.4);
TYPES.b744 = derive('b748', 'Boeing 747-400', 70.66, -4.1);
TYPES.a333 = derive('a359', 'Airbus A330-300', 63.66, -3.3, { R: 2.82 });
TYPES.a332 = derive('a333', 'Airbus A330-200', 58.82, -2.4);
TYPES.a35k = derive('a359', 'Airbus A350-1000', 73.79, 3.8);
TYPES.md11 = derive('b763', 'McDonnell Douglas MD-11', 61.6, 1.9, { R: 3.0 });
// aliases for old names
TYPES.narrow = TYPES.a20n; TYPES.wide = TYPES.b77w; TYPES.mid = TYPES.b789;
const NOSE = (k) => /^b(73|75|3[89]m)/.test(k) ? { pt: 1.0, pb: 0.95, pw: 0.8 } : /^b7[67]/.test(k) ? { pt: 0.92, pb: 0.9, pw: 0.74 } : /^(bcs|crj)/.test(k) ? { pt: 0.97, pb: 0.93, pw: 0.8 } : null;
// upper nose profiles with a windshield "knee" (u = x/Ln, f = fraction of nose rise); smooth-nosed types (787, A350, E-Jet, 747) keep the power curve
const TOP_BOEING = [[0, 0], [0.05, 0.13], [0.15, 0.25], [0.28, 0.36], [0.33, 0.40], [0.47, 0.70], [0.58, 0.85], [0.72, 0.95], [1, 1]];
const TOP_BOEING_WIDE = [[0, 0], [0.05, 0.14], [0.15, 0.27], [0.28, 0.38], [0.32, 0.41], [0.47, 0.70], [0.60, 0.86], [0.75, 0.95], [1, 1]];
const TOP_AIRBUS = [[0, 0], [0.05, 0.16], [0.15, 0.31], [0.28, 0.43], [0.32, 0.46], [0.47, 0.72], [0.60, 0.87], [0.75, 0.96], [1, 1]];
const NOSE_TOP = (k) => /^b(73|75|3[89]m)/.test(k) || /^(bcs|crj)/.test(k) ? TOP_BOEING : /^b7[67]/.test(k) ? TOP_BOEING_WIDE : /^(a2|a3[12]|a19)/.test(k) ? TOP_AIRBUS : null;
for (const k in TYPES) { const T = TYPES[k]; if (!T.nose && NOSE(k)) T.nose = NOSE(k); if (!T.noseTop && NOSE_TOP(k)) T.noseTop = NOSE_TOP(k).map(p => p.slice());
  const C = T.cockpit; C.x0 = C.x0 ?? 0.28 * T.Ln; C.x1 = C.x1 ?? 0.6 * T.Ln; C.yb = C.yb ?? (C.style === 'boeing' ? 0.17 : 0.15) * T.R * (T.top > 1.2 ? 2.2 : 1); C.dmin = C.dmin ?? 0.1 * T.R; C.w = C.w ?? 2 * T.R; C.slope = C.slope ?? 0.24 * T.R; T.xMain = T.gear.main.reduce((s, g) => s + g.x, 0) / T.gear.main.length; T.track = T.gear.main[0].z * 2; T.rWheel = T.gear.r; T.xNose = T.gear.nose.x; T.rNose = T.gear.nose.r; T.doors = T.doors.slice(0, 5); T.key = k; }

// ICAO designator -> model type
export const ICAO_MAP = {
  A19N: 'a319', A319: 'a319', A320: 'a320', A20N: 'a20n', A321: 'a321', A21N: 'a21n', B737: 'b737', B738: 'b738', B739: 'b739', B38M: 'b38m', B39M: 'b39m', B3XM: 'b39m',
  B752: 'b752', B753: 'b753', B762: 'b763', B763: 'b763', B764: 'b763', B772: 'b772', B77L: 'b772', B77W: 'b77w', B773: 'b77w', B778: 'b77w', B788: 'b789', B789: 'b789', B78X: 'b789',
  A332: 'b763', A333: 'b789', A339: 'b789', A359: 'a359', A35K: 'a359', A388: 'a388', B744: 'b748', B748: 'b748', B74F: 'b748', E75L: 'e75l', E75S: 'e75l', E170: 'e75l', E190: 'e75l', E295: 'e75l',
  CRJ7: 'crj9', CRJ9: 'crj9', CRJ2: 'crj2', BCS1: 'bcs3', BCS3: 'bcs3', MD11: 'b77w',
};

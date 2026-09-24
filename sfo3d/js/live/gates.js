// Contact-gate equipment driven by live occupancy:
//  - apron-drive passenger boarding bridges: fixed link, rotunda on its pedestal, three telescoping glazed tunnel
//    sections, drive column with wheel bogie, pre-conditioned-air unit, cab with bellows canopy, service stair,
//    cab floodlight & warning beacon, gate-number signs on both sides of the tunnel
//  - stand equipment on the terminal face: gate identification sign and visual docking guidance display (VDGS)
//  - ground service vehicles placed around the actually parked aircraft, rejected if they would hit the aircraft,
//    the bridge or a neighbouring aircraft
// The bridge docks at the parked aircraft's L1 door (pose from its reported position) and retracts when it leaves.
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { rng, m4, v3, smoother } from '../math.js';
import { stToWorld, GROUND_Y } from '../geo.js';
import { TYPES } from '../aircraft/types.js';
import '../aircraft/fit.js'; // fits the imported models to the published dimensions: T.dockX1/2, T.dockSill/2, T.dockHW
import { inst, buildVehicleMeshes } from '../world/gates.js';
import { makeAtlas } from './signs.js';

const G = GROUND_Y;
const stW = (p, h = 0) => stToWorld(p[0], p[1], h);
const stD = (d) => { const a = stToWorld(d[0], d[1], 0), o = stToWorld(0, 0, 0); return v3.norm([a[0] - o[0], 0, a[2] - o[2]]); };
const hash = (s) => { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return (h >>> 0) % 100000 + 1; };
const DOCK_DELAY = 12, DOCK_TIME = 22, UNDOCK_TIME = 16; // seconds
const C = {
  panel: [0.86, 0.87, 0.88, 1], panelE: [0.45, 0.25, 9, 0], cab: [0.8, 0.81, 0.82, 1], cabE: [0.4, 0.3, 9, 0],
  steel: [0.46, 0.47, 0.49, 1], steelE: [0.45, 0.7, 0, 0], dark: [0.07, 0.07, 0.08, 1], darkE: [0.85, 0, 0, 0],
  yellow: [0.9, 0.7, 0.08, 1], yellowE: [0.5, 0, 0, 0], tyre: [0.05, 0.05, 0.05, 1], tyreE: [0.9, 0, 0, 0],
  unit: [0.74, 0.75, 0.76, 1], unitE: [0.5, 0.2, 0, 0], lamp: [1, 0.93, 0.82, 1], lampE: [0.15, 0, 14, 0], amber: [1, 0.55, 0.05, 1], amberE: [0.2, 0, 14, 0],
};

// rectangular tube along a->b (floor on the a->b line), with window-strip UVs (mat 9: u = metres along, v = 0..1)
function tube(g, a, b, w, h, col, ext) {
  const d = v3.sub(b, a); const L = v3.len(d); if (L < 0.1) return null; const f = v3.mul(d, 1 / L);
  const r = v3.norm(v3.cross(f, [0, 1, 0])); const u = v3.cross(r, f);
  const P = (s, x, y) => v3.add(v3.add(v3.add(a, v3.mul(f, s)), v3.mul(r, x)), v3.mul(u, y));
  const hw = w / 2;
  const side = (x0, y0, x1, y1, n) => {
    const base = g.nv;
    const pts = [P(0, x0, y0), P(L, x0, y0), P(L, x1, y1), P(0, x1, y1)];
    const uvs = [[0, 0], [L, 0], [L, 1], [0, 1]];
    for (let i = 0; i < 4; i++) g.vert(pts[i], n, col, ext, uvs[i]);
    const gn = v3.cross(v3.sub(pts[1], pts[0]), v3.sub(pts[3], pts[0]));
    if (v3.dot(gn, n) > 0) g.idx.push(base, base + 1, base + 2, base, base + 2, base + 3); else g.idx.push(base, base + 2, base + 1, base, base + 3, base + 2);
  };
  side(hw, 0, hw, h, r); side(-hw, 0, -hw, h, v3.mul(r, -1));
  const flat = (y, n, col2, ext2) => { const base = g.nv; const pts = [P(0, -hw, y), P(0, hw, y), P(L, hw, y), P(L, -hw, y)]; for (const p of pts) g.vert(p, n, col2, ext2, [0, 0]); const gn = v3.cross(v3.sub(pts[1], pts[0]), v3.sub(pts[3], pts[0])); if (v3.dot(gn, n) > 0) g.idx.push(base, base + 1, base + 2, base, base + 2, base + 3); else g.idx.push(base, base + 2, base + 1, base, base + 3, base + 2); };
  flat(h, u, col, [ext[0], ext[1], 0, 0]); flat(0, v3.mul(u, -1), C.steel, C.steelE);
  for (const s of [0.05, L - 0.05]) g.box([-0.08, -0.05, -hw - 0.06], [0.08, h + 0.06, hw + 0.06], C.steel, C.steelE, m4.basis(f, [0, 1, 0], P(s, 0, 0)));
  return { f, r, u, P, L };
}
function cyl(g, p, r, h, col, ext, seg = 16) { g.cylinder(r, h, seg, col, ext, m4.translate(p[0], p[1], p[2]), true); }

// representative (largest common) aircraft of a stand class: sets where each bridge's rotunda stands
const REF_TYPE = { B: 'crj9', C: 'b38m', CL: 'a21n', D: 'b763', E: 'b789', EL: 'b77w', F: 'b748' };
const clampN = (x, a, b) => Math.min(b, Math.max(a, x));
// Where the bridge cab meets the aircraft (js/aircraft/fit.js): door `which` = 1 is door 1L, 2 the door the second bridge
// of a wide-body stand docks to (T.dock2, from the manufacturers' documents). x = door CENTRE station from the nose tip
// (the rendered door of the imported model where it has one, else the published centre), cab floor = published door sill
// above the ground, and the cab stops at the rendered fuselage side at door height (T.dockHW).
function doorOf(nose, f, T, which) {
  const left = v3.mul(v3.norm(v3.cross(f, [0, 1, 0])), -1);
  const two = which >= 2 && T.dockX2 != null;
  // (a type without a documented second-bridge door, e.g. the 767-300 whose door 2 is optional, is not docked by the
  // second bridge (docks()); its retracted bridge still points at door 2 or the aft door)
  const x = two ? T.dockX2 : which >= 2 ? ((T.doorsOpt && T.doorsOpt[0]) ?? T.doors[1] ?? T.dockX1) : (T.dockX1 ?? T.doors[0]);
  const sill = two ? (T.dockSill2 ?? T.dockSill) : (T.dockSill ?? (T.sill ?? T.Hc - 0.3 * T.R));
  const d = v3.add(v3.sub(nose, v3.mul(f, x)), v3.mul(left, (T.dockHW ?? T.R) + 0.15)); d[1] = G + sill;
  return { door: d, left };
}
export { doorOf };

export class LiveGateSystem {
  constructor(gates, { atlasExtra = [] } = {}) {
    this.gates = gates; this.anims = new Map(); this.dirty = true; this.live = true;
    this.vehicleMeshes = buildVehicleMeshes();
    const faces = []; const seen = new Set();
    const add = (kind, text) => { const k = kind + ':' + text; if (!seen.has(k)) { seen.add(k); faces.push({ key: k, kind, text }); } };
    for (const g of gates) if (g.bridge) { add('gate', g.name); add('vdgs', g.name); for (const b of g.bridges) add('gate', b.gate); }
    for (const t of atlasExtra) add('vdgs', t);
    this.atlas = makeAtlas(faces);
    this.bbox = [1e9, 0, 1e9, -1e9, 40, -1e9];
    for (const g of gates) { const p = stW(g.nose, 0); this.bbox[0] = Math.min(this.bbox[0], p[0] - 150); this.bbox[2] = Math.min(this.bbox[2], p[2] - 150); this.bbox[3] = Math.max(this.bbox[3], p[0] + 150); this.bbox[5] = Math.max(this.bbox[5], p[2] + 150); }
    for (const g of gates) for (const b of g.bridges || []) this.prepBridge(g, b);
    this.sprites = []; this.aircraftFootprints = null;
  }
  // fixed geometry of one bridge: rotunda position (a fixed walkway carries it out when the stand's door is far from
  // the building) and the direction the retracted tunnel points (towards the stand's door)
  prepBridge(g, b) {
    const T = TYPES[REF_TYPE[g.cls] || 'b38m'];
    const nose = stW(g.nose, G), f = stD(g.dir);
    const { door } = doorOf(nose, f, T, b.door);
    let attach = stW(b.attach, G);
    // a second bridge from the same hold room: its own attach point 7 m further aft along the facade
    const first = g.bridges.find(q => q !== b && q.attachW && Math.hypot(q.attachW[0] - attach[0], q.attachW[2] - attach[2]) < 3);
    if (first) { let p = [-first.u[2], 0, first.u[0]]; if (p[0] * -f[0] + p[2] * -f[2] < 0) p = [-p[0], 0, -p[2]]; attach = v3.add(attach, v3.mul(p, 7)); }
    const to = [door[0] - attach[0], 0, door[2] - attach[2]]; const D = Math.hypot(to[0], to[2]);
    const u = D > 1e-3 ? [to[0] / D, 0, to[2] / D] : stD(g.outN);
    const fixedLen = clampN(D - 27, 3.5, 70);
    b.attachW = attach; b.u = u; b.fixedLen = fixedLen;
    b.rc = [attach[0] + u[0] * fixedLen, G, attach[2] + u[2] * fixedLen];
    const pd = [door[0] - b.rc[0], 0, door[2] - b.rc[2]]; const pl = Math.hypot(pd[0], pd[2]) || 1;
    b.parkDir = [pd[0] / pl, 0, pd[2] / pl]; b.reach = pl;
  }
  // key points of a bridge at extension k (1 = docked at its door of the parked aircraft, 0 = retracted)
  pose(g, b, k) {
    const nose2 = g.dock ? g.dock.nose : g.nose, dir2 = g.dock ? g.dock.dir : g.dir;
    const f = stD(dir2);
    const T = TYPES[g.acType] || TYPES[g._lastType] || TYPES[REF_TYPE[g.cls] || 'b38m'];
    const nose = stW(nose2, G);
    const { door, left } = doorOf(nose, f, T, b.door);
    const floorY = G + 5.4;
    const rc = b.rc;
    const cabDock = v3.add(door, v3.mul(left, 2.0)); cabDock[1] = door[1];
    const cabPark = v3.add([rc[0], G + 4.4, rc[2]], v3.mul(b.parkDir, Math.min(15, b.reach - 2)));
    const kk = smoother(k);
    const cab = v3.lerp(cabPark, cabDock, kk);
    const facing = v3.norm(v3.lerp(b.parkDir, v3.mul(left, -1), kk));
    return { attach: b.attachW, u: b.u, rc, floorY, cab, facing, door, T, kk };
  }
  bridgeGeo(g, b, k, geo, sgn) {
    const P = this.pose(g, b, k);
    const rcTop = [P.rc[0], P.floorY, P.rc[2]];
    // fixed walkway from the terminal face to the rotunda, on columns every ~14 m
    const a0 = [P.attach[0], P.floorY, P.attach[2]];
    tube(geo, v3.add(a0, v3.mul(P.u, -0.3)), v3.add(rcTop, v3.mul(P.u, -2.3)), 2.6, 3.0, C.panel, C.panelE);
    const wl = b.fixedLen - 2.3;
    if (wl > 9) for (let d = 7; d < wl - 3; d += 14) { const c = v3.add(P.attach, v3.mul(P.u, d)); cyl(geo, [c[0], G, c[2]], 0.35, P.floorY - G - 0.05, C.steel, C.steelE, 10); }
    // rotunda on its pedestal
    cyl(geo, [P.rc[0], G, P.rc[2]], 0.6, P.floorY - G - 0.3, C.steel, C.steelE, 12);
    cyl(geo, [P.rc[0], P.floorY - 0.3, P.rc[2]], 2.45, 3.6, C.panel, [0.45, 0.25, 0, 0], 24);
    // telescoping tunnel from the rotunda to the back of the cab (floor slopes to the door sill)
    const cabBack = v3.sub(P.cab, v3.mul(P.facing, 1.8)); cabBack[1] = P.cab[1];
    const dir = v3.norm(v3.sub(cabBack, rcTop)); const s0 = v3.add(rcTop, v3.mul(dir, 2.2));
    const secs = [[0, 0.42, 2.55, 2.85], [0.36, 0.74, 2.68, 2.98], [0.68, 1.0, 2.82, 3.12]];
    let last = null;
    for (const [a, b, w, h] of secs) { const A = v3.add(s0, v3.mul(v3.sub(cabBack, s0), a)), B = v3.add(s0, v3.mul(v3.sub(cabBack, s0), b)); last = tube(geo, A, B, w, h, C.panel, C.panelE); }
    const hdir = v3.norm([dir[0], 0, dir[2]]); const side = v3.norm(v3.cross(hdir, [0, 1, 0]));
    // drive column: two legs, cross beam, bogie with two wheels, control box
    const du = v3.add(s0, v3.mul(v3.sub(cabBack, s0), 0.84));
    for (const sg of [-1, 1]) {
      const leg = v3.add(du, v3.mul(side, sg * 1.25));
      geo.box([-0.16, 0, -0.16], [0.16, Math.max(0.2, du[1] - G - 0.95), 0.16], C.steel, C.steelE, m4.basis(hdir, [0, 1, 0], [leg[0], G + 0.95, leg[2]]));
      geo.cylinder(0.48, 0.34, 14, C.tyre, C.tyreE, m4.mul(m4.basis(hdir, [0, 1, 0], [leg[0], G + 0.48, leg[2]]), m4.mul(m4.rotX(Math.PI / 2), m4.translate(0, -0.17, 0))), true);
    }
    geo.box([-0.35, 0.72, -1.55], [0.35, 1.1, 1.55], C.steel, C.steelE, m4.basis(hdir, [0, 1, 0], [du[0], G, du[2]]));
    geo.box([-0.35, -0.9, 1.5], [0.35, 0, 1.9], C.yellow, C.yellowE, m4.basis(hdir, [0, 1, 0], du));
    // pre-conditioned-air unit slung under the tunnel, with its hose basket
    const pu = v3.add(s0, v3.mul(v3.sub(cabBack, s0), 0.55));
    geo.box([-1.2, -1.5, -0.6], [1.2, -0.15, 0.6], C.unit, C.unitE, m4.basis(hdir, [0, 1, 0], pu));
    geo.box([-0.5, -2.0, -0.45], [0.5, -1.5, 0.45], C.yellow, C.yellowE, m4.basis(hdir, [0, 1, 0], pu));
    // cab + bellows canopy
    const fc = P.facing; const cabM = m4.basis(fc, [0, 1, 0], P.cab);
    geo.box([-1.8, -0.1, -1.8], [1.5, 3.2, 1.8], C.cab, C.cabE, cabM);
    geo.box([-1.9, 3.2, -1.95], [1.65, 3.4, 1.95], C.steel, C.steelE, cabM);
    const bell = 0.45 + 0.4 * P.kk;
    for (let i = 0; i < 5; i++) geo.box([1.5 + i * bell / 5, 0.05, -1.55 - (i % 2) * 0.05], [1.5 + (i + 1) * bell / 5, 3.0, 1.55 + (i % 2) * 0.05], C.dark, C.darkE, cabM);
    // floodlight on the cab roof, amber beacon
    geo.box([0.9, 3.4, -0.35], [1.3, 3.65, 0.35], C.dark, C.darkE, cabM);
    geo.box([1.28, 3.42, -0.3], [1.31, 3.62, 0.3], C.lamp, C.lampE, cabM);
    geo.cylinder(0.14, 0.25, 10, C.amber, C.amberE, m4.mul(cabM, m4.translate(-1.2, 3.4, 1.4)), true);
    this.sprites.push({ p: m4.xform(cabM, [-1.2, 3.8, 1.4]), c: [1, 0.55, 0.08], i: 70, s: 0.25, beacon: true, moving: k > 0.001 && k < 0.999 });
    this.sprites.push({ p: m4.xform(cabM, [1.45, 3.52, 0]), c: [1, 0.92, 0.8], i: 500, s: 0.35, dir: v3.norm(m4.xdir(cabM, [1, -0.8, 0])), k: 3, night: true });
    // service stair from the cab's outboard side door down to the apron
    const out = v3.norm(v3.cross([0, 1, 0], fc)); const sd = v3.dot(out, v3.sub(P.cab, P.rc)) >= 0 ? 1 : -1;
    const stTop = v3.add(v3.add(P.cab, v3.mul(out, sd * 2.4)), v3.mul(fc, -0.6)); const hgt = stTop[1] - G - 0.05;
    if (hgt > 0.8) {
      const run = hgt / Math.tan(40 * Math.PI / 180); const back = v3.mul([fc[0], 0, fc[2]], -1 / Math.hypot(fc[0], fc[2]));
      const stBot = v3.add(stTop, v3.mul(back, run)); stBot[1] = G;
      const sDir = v3.norm(v3.sub(stBot, stTop)); const lat = v3.norm(v3.cross(sDir, [0, 1, 0])); const up = v3.cross(lat, sDir);
      const sM = m4.basis(sDir, up, stTop); const sl = v3.dist(stTop, stBot);
      for (const zz of [-0.55, 0.55]) geo.box([0, -0.28, zz - 0.05], [sl, 0.0, zz + 0.05], C.steel, C.steelE, sM);
      geo.box([0, -0.14, -0.55], [sl, -0.06, 0.55], C.steel, C.steelE, sM);
      for (const zz of [-0.55, 0.55]) geo.box([0, 0.86, zz - 0.025], [sl, 0.92, zz + 0.025], C.yellow, C.yellowE, sM);
      geo.box([-1.1, -0.1, -0.7], [0.1, 0.0, 0.7], C.steel, C.steelE, m4.basis([back[0], 0, back[2]], [0, 1, 0], [stTop[0], stTop[1], stTop[2]]));
    }
    // gate number signs on both sides of the outer tunnel section (lit panels from the sign atlas)
    if (last && sgn) {
      const r = this.atlas.map['gate:' + b.gate];
      const Lh = 0.85, Lw = Lh * r.aspect;
      const mid = v3.add(s0, v3.mul(v3.sub(cabBack, s0), 0.84));
      for (const sg of [-1, 1]) {
        const n = v3.mul(side, sg); const c = v3.add(v3.add(mid, v3.mul(n, 1.46)), [0, 1.6, 0]);
        const along = v3.mul(hdir, -sg); // text runs left-to-right for a viewer facing -n
        const u0 = v3.add(c, v3.mul(along, -Lw / 2)), u1 = v3.add(c, v3.mul(along, Lw / 2));
        signQuad(sgn, [v3.add(u0, [0, -Lh / 2, 0]), v3.add(u1, [0, -Lh / 2, 0]), v3.add(u1, [0, Lh / 2, 0]), v3.add(u0, [0, Lh / 2, 0])], n, r, true);
      }
    }
    return P;
  }
  standGeo(g, geo, sgn) {
    // stand identification sign and visual docking guidance display, on the stand centreline ahead of the nose:
    // on the terminal face, or on its own post when the stop point is far from the building
    const nose = stW(g.nose, G), f = stD(g.dir);
    const b0 = g.bridges[0]; const att = b0 ? b0.attachW : nose;
    let t = v3.dot(v3.sub(att, nose), f); t = clampN(t, 3, 40);
    const post = t > 14; if (post) t = 12;
    const c = v3.add(nose, v3.mul(f, t));
    const outW = v3.mul(f, -1); // display faces the arriving aircraft
    const face = v3.add(c, v3.mul(outW, 0.35));
    const tW = v3.norm(v3.cross(outW, [0, 1, 0]));
    const H0 = post ? 5.2 : 7.2;
    if (post) { geo.box([-0.18, 0, -0.18], [0.18, H0, 0.18], C.steel, C.steelE, m4.basis(tW, [0, 1, 0], [c[0], G, c[2]])); geo.box([-0.5, 0, -0.5], [0.5, 0.25, 0.5], [0.55, 0.55, 0.55, 1], [0.5, 0.3, 0, 0], m4.basis(tW, [0, 1, 0], [c[0], G, c[2]])); }
    const M = m4.basis(v3.mul(tW, -1), [0, 1, 0], [face[0], G + H0, face[2]]);
    geo.box([-0.75, 0, -0.35], [0.75, 2.4, 0.25], [0.2, 0.21, 0.22, 1], [0.5, 0.4, 0, 0], M);
    geo.box([-0.8, -0.35, -0.3], [0.8, 0, 0.2], C.yellow, C.yellowE, M);
    const vr = (g.acType && g.dockType && this.atlas.map['vdgs:' + g.dockType]) || this.atlas.map['vdgs:' + g.name];
    const dh = 0.8, dw = Math.min(1.35, dh * vr.aspect);
    const d0 = v3.add([face[0], G + H0 + 1.35, face[2]], v3.mul(outW, 0.27));
    signQuad(sgn, [v3.add(d0, v3.add(v3.mul(tW, dw / 2), [0, -dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, -dw / 2), [0, -dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, -dw / 2), [0, dh / 2, 0])), v3.add(d0, v3.add(v3.mul(tW, dw / 2), [0, dh / 2, 0]))], outW, vr, true);
    // stand number above the display
    const gr = this.atlas.map['gate:' + g.name]; const gh = 1.4, gw = gh * gr.aspect;
    const g0 = v3.add([face[0], G + H0 + 3.1, face[2]], v3.mul(outW, 0.1));
    if (post) geo.box([-gw / 2 - 0.1, -gh / 2 - 0.1, -0.12], [gw / 2 + 0.1, gh / 2 + 0.1, 0.02], [0.2, 0.21, 0.22, 1], [0.5, 0.4, 0, 0], m4.basis(v3.mul(tW, -1), [0, 1, 0], g0));
    signQuad(sgn, [v3.add(g0, v3.add(v3.mul(tW, gw / 2), [0, -gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, -gw / 2), [0, -gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, -gw / 2), [0, gh / 2, 0])), v3.add(g0, v3.add(v3.mul(tW, gw / 2), [0, gh / 2, 0]))], outW, gr, true);
  }
  // the second (L2) bridge of a wide-body stand only docks wide-body aircraft
  docks(g, b) { if (b.door === 1) return true; const T = TYPES[g.acType] || TYPES[g._lastType]; return !!(T && (T.cls === 'E' || T.cls === 'F') && T.dockX2 != null); }
  // typeKey: TYPES key of the parked aircraft (null = empty); pose: {nose:[s,t], dir:[s,t]}; icao: type designator
  setOccupant(g, typeKey, animate, now, pose, icao) {
    if (typeKey) { g.dock = pose || null; g.dockType = icao || null; }
    const was = !!g.acType; g.acType = typeKey || null; g.empty = !typeKey;
    if (g.bridge && animate && was !== !!typeKey) {
      const cur = this.anims.get(g.id); const k0 = cur ? cur.k : (was ? 1 : 0);
      this.anims.set(g.id, { from: k0, to: typeKey ? 1 : 0, t0: now + (typeKey ? DOCK_DELAY : 0) * 1000, dur: (typeKey ? DOCK_TIME : UNDOCK_TIME) * 1000, k: k0 });
    }
    if (typeKey) g._lastType = typeKey;
    this.dirty = true;
  }
  // full: rebuild the static set (bridges at rest, stand equipment, vehicles); always rebuild moving bridges
  build(now, full) {
    if (full) {
      this.staticSprites = [];
      const geo = new Geo(), sgn = newSignGeo();
      this.vehicleBuckets = {}; for (const k in this.vehicleMeshes) this.vehicleBuckets[k] = [];
      this.keepOut = this.aircraftFootprints ? this.aircraftFootprints() : [];
      this.sprites = this.staticSprites;
      for (const g of this.gates) {
        if (!g.bridge) continue;
        if (!this.anims.has(g.id)) { const Ps = g.bridges.map(b => this.bridgeGeo(g, b, g.acType && this.docks(g, b) ? 1 : 0, geo, sgn)); if (g.acType) this.placeVehicles(g, Ps); }
        this.standGeo(g, geo, sgn);
      }
      if (this.staticMesh) this.staticMesh.dispose(); if (this.signMesh) this.signMesh.dispose();
      this.staticMesh = meshOf(geo); this.signMesh = meshOfSign(sgn);
      for (const k in this.vehicleBuckets) { const list = this.vehicleBuckets[k]; this.vehicleMeshes[k].setInstances(new Float32Array(list.flat()), list.length); }
    }
    if (this.dynMesh) { this.dynMesh.dispose(); this.dynMesh = null; } if (this.dynSign) { this.dynSign.dispose(); this.dynSign = null; }
    this.dynSprites = []; this.sprites = this.dynSprites;
    if (this.anims.size) {
      const dyn = new Geo(), dsgn = newSignGeo();
      for (const g of this.gates) { const a = this.anims.get(g.id); if (a && g.bridge) for (const b of g.bridges) this.bridgeGeo(g, b, this.docks(g, b) ? a.k : 0, dyn, dsgn); }
      this.dynMesh = dyn.nv ? meshOf(dyn) : null; this.dynSign = dsgn.pos.length ? meshOfSign(dsgn) : null;
    }
    this.sprites = (this.staticSprites || []).concat(this.dynSprites);
  }
  items(now = Date.now()) {
    let moving = false;
    for (const [id, a] of this.anims) {
      const u = Math.min(1, Math.max(0, (now - a.t0) / a.dur)); a.k = a.from + (a.to - a.from) * u; moving = true;
      if (u >= 1) { this.anims.delete(id); this.dirty = true; }
    }
    if (this.dirty || !this.staticMesh) { this.dirty = false; this.build(now, true); }
    else if (moving || this._hadDyn) this.build(now, false);
    this._hadDyn = moving;
    const I4 = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
    const out = [];
    if (this.staticMesh) out.push({ mesh: this.staticMesh, prog: 'obj', model: I4, bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
    if (this.dynMesh) out.push({ mesh: this.dynMesh, prog: 'obj', model: I4, bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } });
    if (this.signMesh) out.push({ mesh: this.signMesh, prog: 'sign', bbox: this.bbox, castShadow: false, noCull: true, nearOnly: true, uniforms: { uAtlas: this.atlas.tex } });
    if (this.dynSign) out.push({ mesh: this.dynSign, prog: 'sign', bbox: this.bbox, castShadow: false, noCull: true, nearOnly: true, uniforms: { uAtlas: this.atlas.tex } });
    for (const k in this.vehicleMeshes) out.push({ mesh: this.vehicleMeshes[k], prog: 'objI', bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, shadowMaxCascade: 2 });
    return out;
  }
  // ground service vehicles around the parked aircraft (actual pose), with collision rejection
  placeVehicles(g, Ps) {
    if (!g.dock || !Ps.length) return;
    const P = Ps[0];
    const R = rng(hash(g.id)); const T = P.T;
    const f = stD(g.dock.dir); const r = v3.norm(v3.cross(f, [0, 1, 0])); const nose = stW(g.dock.nose, G);
    const self = footprint(nose, f, T, g);
    const at = (along, sideOff, yaw = 0) => { const p = v3.add(v3.sub(nose, v3.mul(f, along)), v3.mul(r, sideOff)); const c = Math.cos(yaw), s = Math.sin(yaw); const d = v3.norm(v3.add(v3.mul(f, c), v3.mul(r, s))); return { M: m4.basis(d, [0, 1, 0], [p[0], G, p[2]]), p, d }; };
    const bridgeDisks = []; for (const Q of Ps) { bridgeDisks.push({ c: [Q.rc[0], Q.rc[2]], r: 3.4 }, { c: [Q.cab[0], Q.cab[2]], r: 4.0 }); const n = Math.ceil(v3.dist(Q.rc, Q.cab) / 4); for (let i = 1; i < n; i++) { const p = v3.lerp(Q.rc, Q.cab, i / n); bridgeDisks.push({ c: [p[0], p[2]], r: 2.6 }); } }
    const ok = (v, len, wid, tall) => {
      const rt = [-v.d[2], v.d[0]];
      const pts = [[-len / 2, -wid / 2], [len / 2, -wid / 2], [len / 2, wid / 2], [-len / 2, wid / 2], [0, 0]].map(([a, b]) => [v.p[0] + v.d[0] * a + rt[0] * b, v.p[2] + v.d[2] * a + rt[1] * b]);
      for (const q of pts) {
        if (hitsAircraft(self, q, tall)) return false;
        for (const o of this.keepOut) if (o.gate !== g && hitsAircraft(o, q, tall)) return false;
        for (const b of bridgeDisks) if (Math.hypot(q[0] - b.c[0], q[1] - b.c[1]) < b.r) return false;
      }
      return true;
    };
    const tint = () => { const cs = [[0.95, 0.95, 0.95], [0.9, 0.75, 0.1], [0.15, 0.3, 0.6], [0.85, 0.3, 0.1], [0.4, 0.42, 0.45]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    const B = this.vehicleBuckets;
    const put = (bucket, v, len, wid, tall, color) => { if (ok(v, len, wid, tall)) { B[bucket].push(inst(v.M, color || tint())); return true; } return false; };
    const fuse = T.R + 0.4;
    // cargo doors are on the right (starboard) side: forward ahead of the wing, aft behind it
    const fwdCargo = T.L * 0.22, aftCargo = T.L * 0.66;
    const cartCol = () => { const cs = [[0.34, 0.37, 0.4], [0.16, 0.24, 0.42], [0.2, 0.3, 0.24], [0.55, 0.56, 0.57]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    const tugCol = () => { const cs = [[0.9, 0.72, 0.1], [0.92, 0.92, 0.9], [0.12, 0.2, 0.42]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    if (R() < 0.85) put('beltLoader', at(fwdCargo, fuse + 3.9, -1.25), 8.5, 2.2, 1.4);
    if (R() < 0.6) put('beltLoader', at(aftCargo, fuse + 3.9, -1.25), 8.5, 2.2, 1.4);
    // baggage train alongside the aft fuselage behind the wing, tug facing forward, carts trailing
    if (R() < 0.75) { const y = fuse + 6.8, a0 = aftCargo + 2.5; if (put('tug', at(a0, y, 0), 3, 1.8, 2.1, tugCol())) for (let i = 0; i < 3; i++) put('cart', at(a0 + 3.4 + i * 3.4, y, 0), 3.2, 1.8, 1.5, cartCol()); }
    if (R() < 0.45 && T.doors[1] != null) put('catering', at(T.doors[1] + 1, fuse + 4.4, -Math.PI / 2), 8.2, 2.4, 6.3, [0.95, 0.95, 0.95, 1]);
    if (R() < 0.35 && T.eng.length) put('fuel', at(T.xMain - 5, T.eng[T.eng.length - 1].z + 7.5, 0), 8.2, 2.5, 2.9, [0.85, 0.85, 0.85, 1]);
    if (R() < 0.6) put('gpu', at(3.5, fuse + 3.4, 0.3), 2.5, 1.5, 1.6);
    const span = T.wing ? T.wing.span / 2 : 18;
    for (const [a, s] of [[-2.5, 0], [T.wing ? T.wing.rootLE + (span) * Math.tan((T.wing.sweep || 25) * Math.PI / 180) + 1 : T.L * 0.5, span + 1.2], [T.wing ? T.wing.rootLE + span * Math.tan((T.wing.sweep || 25) * Math.PI / 180) + 1 : T.L * 0.5, -(span + 1.2)], [T.L + 2, 0]]) { const v = at(a, s); if (ok(v, 0.4, 0.4, 0.8)) B.cone.push(inst(v.M)); }
  }
}

// ---------------------------------------------------------------- aircraft footprints for collision tests
export function footprint(nose, f, T, gate = null) { return { nose: [nose[0], nose[2]], f: [f[0], f[2]], r: [-f[2], f[0]], T, gate }; }
export function hitsAircraft(fp, q, tall) {
  const dx = q[0] - fp.nose[0], dz = q[1] - fp.nose[1];
  const x = -(dx * fp.f[0] + dz * fp.f[1]); // metres behind the nose
  const y = dx * fp.r[0] + dz * fp.r[1];      // metres to the right
  const T = fp.T;
  if (x > -1 && x < T.L + 1 && Math.abs(y) < T.R + 0.6) return true;                       // fuselage
  const w = T.wing;
  if (w) {
    const ay = Math.abs(y); const le = w.rootLE + ay * Math.tan((w.sweep || 25) * Math.PI / 180);
    const chord = w.rootC - (w.rootC - w.tipC) * Math.min(1, ay / (w.span / 2));
    if (ay < w.span / 2 + 0.5 && x > le - 0.5 && x < le + chord + 0.5 && tall > 2.2) return true;  // under the wing only if low enough
  }
  for (const e of T.eng || []) for (const sg of [-1, 1]) {
    const ex = (w ? w.rootLE + Math.abs(e.z) * Math.tan((w.sweep || 25) * Math.PI / 180) : T.L * 0.4) - (e.fwd || 3);
    if (Math.abs(y - sg * e.z) < e.r + 0.8 && x > ex - 1.5 && x < ex + e.len + 1.5) return true;
  }
  if (T.rear && x > T.rear.x - 1 && x < T.rear.x + T.rear.len + 1 && Math.abs(y) < T.rear.z + T.rear.r + 0.8 && tall > 2.5) return true;
  if (T.hstab && x > T.hstab.x - 1 && x < T.L + 1 && Math.abs(y) < T.hstab.span / 2 + 0.5 && tall > 4.5) return true;
  return false;
}

// ---------------------------------------------------------------- sign geometry (sign program: pos, nrm, uv, extra)
function newSignGeo() { return { pos: [], nrm: [], uv: [], ext: [], idx: [] }; }
function signQuad(s, q, n, r, lit) {
  const b = s.pos.length / 3; for (const p of q) s.pos.push(p[0], p[1], p[2]);
  for (let i = 0; i < 4; i++) { s.nrm.push(n[0], n[1], n[2]); s.ext.push(lit ? 1 : 0, 0, 0, 0); }
  s.uv.push(r.u0, r.v1, r.u1, r.v1, r.u1, r.v0, r.u0, r.v0); s.idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
}
function meshOf(g) { return new Mesh(g.data()); }
function meshOfSign(s) { return new Mesh({ pos: new Float32Array(s.pos), nrm: new Float32Array(s.nrm), uv: new Float32Array(s.uv), extra: new Float32Array(s.ext), idx: new Uint32Array(s.idx) }); }

// Jet bridges (instanced unit parts, animatable) and ground service vehicles
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { m4, v3, rng, lerp, smoother } from '../math.js';
import { stToWorld, GROUND_Y } from '../geo.js';
import { TYPES } from '../aircraft/model.js';

const G = GROUND_Y;
const stW = (p, h = 0) => stToWorld(p[0], p[1], h);
const stD = (d) => { const a = stToWorld(d[0], d[1], 0), o = stToWorld(0, 0, 0); return v3.norm([a[0] - o[0], 0, a[2] - o[2]]); };

// unit meshes
function unitBox(col, ext, uvLen = true) { const g = new Geo(); g.box([0, -0.5, -0.5], [1, 0.5, 0.5], col, ext); // uv: x along, y vertical 0..1
  for (let i = 0; i < g.nv; i++) { g.uv[i * 2] = g.pos[i * 3]; g.uv[i * 2 + 1] = g.pos[i * 3 + 1] + 0.5; } return g; }
function unitCyl(col, ext, seg = 20) { const g = new Geo(); g.cylinder(1, 1, seg, col, ext, null, true); return g; }

function inst(M, data = [0, 0, 0, 0]) { // 3x4 rows + data
  return [M[0], M[4], M[8], M[12], M[1], M[5], M[9], M[13], M[2], M[6], M[10], M[14], ...data];
}
// unit cylinder (axis y 0..1, radius 1) -> centered at c, axis direction ax, radius r, length l
function cylMat(c, ax, r, l) {
  const y = v3.norm(ax); const x = v3.norm(Math.abs(y[1]) > 0.9 ? v3.cross([1, 0, 0], y) : v3.cross(y, [0, 1, 0])); const z = v3.cross(x, y);
  const B = new Float32Array([x[0] * r, x[1] * r, x[2] * r, 0, y[0] * l, y[1] * l, y[2] * l, 0, z[0] * r, z[1] * r, z[2] * r, 0, c[0] - y[0] * l / 2, c[1] - y[1] * l / 2, c[2] - y[2] * l / 2, 1]);
  return B;
}
// matrix mapping unit box (x:0..1, y,z: -0.5..0.5) onto segment a->b with height h (y) and width w, keeping y up
function segBox(a, b, h, w, roll = 0) {
  const d = v3.sub(b, a); const L = v3.len(d); const f = v3.mul(d, 1 / L);
  const r = v3.norm(v3.cross(f, [0, 1, 0])); const u = v3.cross(r, f);
  const B = new Float32Array([f[0], f[1], f[2], 0, u[0], u[1], u[2], 0, r[0], r[1], r[2], 0, a[0], a[1], a[2], 1]);
  return { M: m4.mul(B, m4.scale(L, h, w)), L };
}

export { inst };
export class GateSystem {
  constructor(gates) {
    this.gates = gates;
    const light = [0.82, 0.83, 0.84, 1], dark = [0.08, 0.08, 0.09, 1], gray = [0.45, 0.46, 0.48, 1];
    this.meshes = {
      tunnel: new Mesh(unitBox(light, [0.5, 0.2, 9, 0]).data()),
      cab: new Mesh(unitBox([0.7, 0.71, 0.72, 1], [0.45, 0.2, 9, 0]).data()),
      bellows: new Mesh(unitBox(dark, [0.9, 0, 0, 0]).data()),
      column: new Mesh(unitCyl(gray, [0.5, 0.6, 0, 0], 12).data()),
      rotunda: new Mesh(unitCyl([0.78, 0.79, 0.8, 1], [0.5, 0.3, 0, 0], 24).data()),
      wheel: new Mesh(unitCyl([0.06, 0.06, 0.06, 1], [0.9, 0, 0, 0], 12).data()),
      beam: new Mesh(unitBox(gray, [0.5, 0.6, 0, 0]).data()),
    };
    this.vehicleMeshes = buildVehicleMeshes();
    this.animated = {}; // gateId -> k
    this.buildStatic();
  }
  bridgePose(g, k) {
    // k: 1 docked at L1 door, 0 retracted
    const f = stD(g.dir); const r = v3.norm(v3.cross(f, [0, 1, 0])); const left = v3.mul(r, -1);
    const outW = stD(g.outN);
    const T = TYPES[g.acType || (g.wide ? 'wide' : 'narrow')];
    const attach = stW(g.attach, G);
    const rc = v3.add(v3.add(attach, v3.mul(outW, 3.2)), v3.mul(left, g.wide ? 7 : 5));
    const floorY = G + 5.4;
    const nose = stW(g.nose, G);
    const doorX = T.doors[0];
    const sill = G + T.Hc - 0.3 * T.R;
    const door = v3.add(v3.sub(nose, v3.mul(f, doorX + 0.5)), v3.mul(left, T.R + 0.2));
    door[1] = sill;
    // docked cab center (cab depth 3.4 m, away from fuselage along left)
    const cabDock = v3.add(door, v3.mul(left, 1.9));
    // retracted: cab pulled back toward pier, swung along pier face
    const along = v3.norm(v3.add(v3.mul(outW, 0.6), v3.mul(left, 0.8)));
    const cabPark = v3.add([rc[0], G + 4.2, rc[2]], v3.mul(along, 14));
    const kk = smoother(k);
    const cab = v3.lerp(cabPark, cabDock, kk);
    const cabFacing = v3.norm(v3.lerp(along, v3.mul(left, -1), kk)); // direction cab faces (toward aircraft when docked)
    return { rc, floorY, cab, cabFacing, left, door };
  }
  bridgeInstances(g, k, out) {
    const P = this.bridgePose(g, k); const M = this.meshes;
    const rc = P.rc; const rot = [rc[0], P.floorY - 0.2, rc[2]];
    // rotunda + column
    out.rotunda.push(inst(m4.mul(m4.translate(rc[0], P.floorY - 0.3, rc[2]), m4.scale(2.3, 3.3, 2.3))));
    out.column.push(inst(m4.mul(m4.translate(rc[0], G, rc[2]), m4.scale(0.55, P.floorY - G - 0.3, 0.55))));
    // tunnel from rotunda edge to cab back
    const cabBack = v3.sub(P.cab, v3.mul(P.cabFacing, 1.7));
    const startC = [rc[0], P.floorY + 1.3, rc[2]];
    const endC = [cabBack[0], P.cab[1] + 1.4, cabBack[2]];
    const dir = v3.norm(v3.sub(endC, startC));
    const s0 = v3.add(startC, v3.mul(dir, 2.0));
    const Lt = v3.dist(s0, endC);
    // three telescoping sections
    const secs = [[0, 0.42, 2.9, 2.5], [0.36, 0.74, 3.05, 2.65], [0.68, 1.0, 3.2, 2.8]];
    for (const [a, b, h, w] of secs) {
      const A = v3.add(s0, v3.mul(dir, Lt * a)), B = v3.add(s0, v3.mul(dir, Lt * b));
      const { M: mm, L } = segBox(A, B, h, w); out.tunnel.push(inst(mm, [L, 0, 0, 0]));
    }
    // cab
    const cabA = v3.sub(P.cab, v3.mul(P.cabFacing, 1.7)), cabB = v3.add(P.cab, v3.mul(P.cabFacing, 1.5));
    const cA = [cabA[0], P.cab[1] + 1.55, cabA[2]], cB = [cabB[0], P.cab[1] + 1.55, cabB[2]];
    out.cab.push(inst(segBox(cA, cB, 3.3, 3.4).M, [3.2, 0, 0, 0]));
    // bellows/canopy at aircraft side
    const bA = cB, bB = v3.add(cB, v3.mul(P.cabFacing, 0.5 + 0.3 * k));
    out.bellows.push(inst(segBox(bA, bB, 3.0, 3.1).M));
    // drive unit: legs + wheels under the outer tunnel near cab
    const du = v3.add(s0, v3.mul(dir, Lt * 0.84)); const yb = du[1] - 1.5;
    const side = v3.norm(v3.cross(dir, [0, 1, 0]));
    for (const sg of [-1, 1]) {
      const leg = v3.add(du, v3.mul(side, sg * 1.3));
      out.column.push(inst(m4.mul(m4.translate(leg[0], G + 0.45, leg[2]), m4.scale(0.18, yb - G - 0.45, 0.18))));
      out.wheel.push(inst(cylMat([leg[0], G + 0.45, leg[2]], side, 0.45, 0.35)));
    }
    const beamA = v3.add(du, v3.mul(side, -1.4)), beamB = v3.add(du, v3.mul(side, 1.4));
    out.beam.push(inst(segBox([beamA[0], G + 0.5, beamA[2]], [beamB[0], G + 0.5, beamB[2]], 0.4, 0.5).M));
  }
  buildStatic() {
    const R = rng(99);
    this.staticBuckets = { tunnel: [], cab: [], bellows: [], column: [], rotunda: [], wheel: [], beam: [] };
    this.vehicleBuckets = {}; for (const k in this.vehicleMeshes) this.vehicleBuckets[k] = [];
    for (const g of this.gates) {
      if (g.dynamic) continue;
      const docked = !g.empty;
      this.bridgeInstances(g, docked ? 1 : 0.0, this.staticBuckets);
      if (docked) this.placeServiceVehicles(g, R, this.vehicleBuckets);
    }
    // staging: rows of baggage carts/containers near each pier root
    for (const g of this.gates) { if (R() > 0.3) continue; const f = stD(g.dir); const r = v3.norm(v3.cross(f, [0, 1, 0])); const base = stW(g.attach, G);
      const p0 = v3.add(base, v3.add(v3.mul(f, -9), v3.mul(r, (R() < 0.5 ? -1 : 1) * (g.wide ? 22 : 15))));
      for (let i = 0; i < 4; i++) { const p = v3.add(p0, v3.mul(r, i * 3.3)); this.vehicleBuckets.cart.push(inst(m4.basis(r, [0, 1, 0], [p[0], G, p[2]]), [0.3 + R() * 0.4, 0.3, 0.35, 1])); } }
    this.bbox = [-2000, 0, -2000, 2000, 60, 2000];
    const all = this.gates.map(g => stW(g.nose, 0)); if (all.length) { this.bbox = [1e9, 0, 1e9, -1e9, 30, -1e9]; all.forEach(p => { this.bbox[0] = Math.min(this.bbox[0], p[0] - 120); this.bbox[2] = Math.min(this.bbox[2], p[2] - 120); this.bbox[3] = Math.max(this.bbox[3], p[0] + 120); this.bbox[5] = Math.max(this.bbox[5], p[2] + 120); }); }
  }
  // per-frame items; dyn: [{gate, k}] animated bridges; extraVehicles: {meshName: [instances]}
  items(dyn = [], extraVehicles = {}) {
    const out = [];
    const buckets = {}; for (const k in this.staticBuckets) buckets[k] = this.staticBuckets[k].slice();
    for (const d of dyn) this.bridgeInstances(d.gate, d.k, buckets);
    for (const k in buckets) { const m = this.meshes[k]; m.setInstances(new Float32Array(buckets[k].flat()), buckets[k].length); out.push({ mesh: m, prog: 'objI', bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 } }); }
    for (const k in this.vehicleBuckets) { const list = this.vehicleBuckets[k].concat(extraVehicles[k] || []); const m = this.vehicleMeshes[k]; m.setInstances(new Float32Array(list.flat()), list.length); out.push({ mesh: m, prog: 'objI', bbox: this.bbox, castShadow: true, uniforms: { uEmissiveBoost: 1 }, shadowMaxCascade: 2 }); }
    return out;
  }
  placeServiceVehicles(g, R, B) {
    const T = TYPES[g.acType || (g.wide ? 'wide' : 'narrow')];
    const f = stD(g.dir); const r = v3.norm(v3.cross(f, [0, 1, 0]));
    const nose = stW(g.nose, G);
    const at = (along, side, yaw = 0) => { // along: meters behind nose, side: + right
      const p = v3.add(v3.sub(nose, v3.mul(f, along)), v3.mul(r, side));
      const c = Math.cos(yaw), s = Math.sin(yaw); const d = v3.norm(v3.add(v3.mul(f, c), v3.mul(r, s)));
      return m4.basis(d, [0, 1, 0], [p[0], G, p[2]]);
    };
    const tint = () => { const cs = [[0.95, 0.95, 0.95], [0.9, 0.75, 0.1], [0.15, 0.3, 0.6], [0.85, 0.3, 0.1], [0.4, 0.42, 0.45]]; return [...cs[Math.floor(R() * cs.length)], 1]; };
    // belt loader at forward cargo door (right side)
    if (R() < 0.8) B.beltLoader.push(inst(at(T.L * 0.22, T.R + 3.0, -1.35), tint()));
    // baggage tug + carts
    if (R() < 0.75) {
      const base = T.L * 0.3; B.tug.push(inst(at(base, T.R + 11, Math.PI), tint()));
      for (let i = 0; i < 3; i++) B.cart.push(inst(at(base + 3.2 + i * 3.4, T.R + 11, Math.PI), [0.3 + R() * 0.5, 0.3, 0.35, 1]));
    }
    // catering truck at R2 door
    if (R() < 0.45) B.catering.push(inst(at(T.doors[1] + 1, T.R + 3.5, -Math.PI / 2), [0.95, 0.95, 0.95, 1]));
    // fuel truck outboard of the right engine
    if (R() < 0.35 && T.eng.length) B.fuel.push(inst(at(T.xMain - 6, T.eng[T.eng.length - 1].z + 6.5, 0), [0.85, 0.85, 0.85, 1]));
    // GPU near nose
    if (R() < 0.6) B.gpu.push(inst(at(2.5, -3.5, 0.3), tint()));
    // cones at wingtips & nose
    for (const [a, s] of [[-1.5, 0], [T.L * 0.5, T.R + 0.2 + (g.wide ? 30 : 16.5)], [T.L * 0.5, -(T.R + 0.2 + (g.wide ? 30 : 16.5))], [T.L + 1.5, 0]]) B.cone.push(inst(at(a, s)));
  }
}

// ----- vehicle meshes -----
export function buildVehicleMeshes() {
  const T = (c) => [...c, 1];
  const paint = [0.9, 0.9, 0.9, 1], dark = [0.1, 0.1, 0.11, 1], glass = [0.05, 0.06, 0.07, 1];
  const E_PAINT = [0.45, 0, 20, 0], E_DARK = [0.8, 0, 0, 0], E_GLASS = [0.1, 0, 0, 0], E_METAL = [0.4, 0.8, 0, 0];
  const wheels = (g, xs, zw, r = 0.35, w = 0.25) => { for (const x of xs) for (const z of [-zw, zw]) g.cylinder(r, w, 10, dark, E_DARK, m4.mul(m4.translate(x, r, z + (z > 0 ? -w / 2 : w / 2) - w / 2 + w / 2), m4.rotX(Math.PI / 2))); };
  const M = {};
  { const g = new Geo(); g.box([-1.4, 0.35, -0.8], [1.4, 1.2, 0.8], paint, E_PAINT); g.box([-1.3, 1.2, -0.75], [-0.1, 2.0, 0.75], glass, E_GLASS); g.box([-1.35, 2.0, -0.8], [-0.05, 2.1, 0.8], paint, E_PAINT); wheels(g, [-0.9, 0.9], 0.8, 0.35); M.tug = g; }
  { const g = new Geo(); g.box([-1.5, 0.4, -0.85], [1.5, 0.55, 0.85], [0.3, 0.3, 0.32, 1], E_METAL); const bag = [[0.2, 0.2, 0.25], [0.5, 0.1, 0.1], [0.1, 0.2, 0.4], [0.35, 0.3, 0.2]]; for (let i = 0; i < 6; i++) g.box([-1.4 + (i % 3) * 0.95, 0.55, -0.8 + Math.floor(i / 3) * 0.8], [-0.55 + (i % 3) * 0.95, 1.0 + (i % 2) * 0.2, -0.05 + Math.floor(i / 3) * 0.8], T(bag[i % 4]), [0.8, 0, 20, 0]); g.box([-1.5, 1.3, -0.85], [1.5, 1.4, 0.85], [0.8, 0.8, 0.8, 1], E_METAL); wheels(g, [-1.0, 1.0], 0.85, 0.22, 0.15); M.cart = g; }
  { const g = new Geo(); g.box([-2.5, 0.4, -1.0], [2.5, 1.3, 1.0], paint, E_PAINT); g.box([-2.4, 1.3, -0.9], [-1.2, 2.3, 0.9], glass, E_GLASS);
    // inclined belt
    const bl = m4.mul(m4.translate(-2.8, 1.2, 0), m4.rotZ(0.38)); g.box([0, 0, -0.45], [8.5, 0.35, 0.45], dark, E_DARK, bl); wheels(g, [-1.6, 1.6], 1.0); M.beltLoader = g; }
  { const g = new Geo(); g.box([-3.5, 0.5, -1.1], [3.0, 1.6, 1.1], paint, E_PAINT); g.box([3.0, 0.5, -1.1], [4.5, 2.6, 1.1], paint, E_PAINT); g.box([3.9, 1.6, -1.05], [4.55, 2.4, 1.05], glass, E_GLASS);
    g.box([-3.4, 3.6, -1.2], [2.8, 6.2, 1.2], [0.95, 0.95, 0.95, 1], [0.5, 0, 2, 0]); g.box([-3.0, 1.6, -0.3], [2.4, 3.6, 0.3], [0.3, 0.3, 0.32, 1], E_METAL); wheels(g, [-2.4, 3.6], 1.1, 0.45); M.catering = g; }
  { const g = new Geo(); g.box([2.5, 0.5, -1.2], [4.5, 2.8, 1.2], paint, E_PAINT); g.box([3.9, 1.7, -1.15], [4.55, 2.6, 1.15], glass, E_GLASS); g.cylinder(1.2, 6.0, 16, [0.85, 0.85, 0.86, 1], [0.35, 0.6, 0, 0], m4.mul(m4.translate(-3.8, 2.0, 0), m4.rotZ(-Math.PI / 2))); wheels(g, [-3, -1.5, 3.5], 1.2, 0.5); M.fuel = g; }
  { const g = new Geo(); g.box([-1.2, 0.3, -0.7], [1.2, 1.5, 0.7], paint, E_PAINT); wheels(g, [-0.8, 0.8], 0.7, 0.28); M.gpu = g; }
  { const g = new Geo(); g.lathe([[0.22, 0], [0.05, 0.75]], 10, [0.95, 0.35, 0.05, 1], [0.6, 0, 0, 0], null, true); M.cone = g; }
  const out = {}; for (const k in M) out[k] = new Mesh(M[k].data()); return out;
}

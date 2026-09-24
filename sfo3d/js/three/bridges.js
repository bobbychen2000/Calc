// Jet bridges, stand equipment and ground service vehicles for the three.js renderer.
// All decisions come from js/live/gates.js LiveGateSystem (not copied): which stands are occupied (setOccupant),
// docking animations (anims: from/to/t0/dur), bridge key points (pose()), which bridges dock (docks()), the stand
// sign / VDGS geometry (standGeo()) and the collision-checked vehicle placement (placeVehicles()).
// What changes is how bridges are drawn: instead of rebuilding one merged mesh every frame while a bridge moves
// (gates.js build()), each bridge part is an instance of a unit tube / box / cylinder and docking only rewrites the
// instance matrices of the moving bridges.
// The part layout replicates LiveGateSystem.bridgeGeo (js/live/gates.js lines ~95-175 as of 24 Sep 2026: fixed
// walkway, columns every 14 m, rotunda on its pedestal, three telescoping tunnels, drive column with bogie, PCA unit,
// cab with roof, 5-fold bellows, floodlight, amber beacon, service stair, gate-number signs) because that method emits
// merged Geo geometry rather than transforms. Colours: gates.js constant C (same values).
import { THREE, TSL } from './lib.js';
import { m4, v3 } from '../math.js';
import { GROUND_Y } from '../geo.js';
import { Geo } from '../geom.js';
import { geometryFromData, geometryOf } from './convert.js';
import { SignBuilder, faceIndex, signMeshes } from './signs.js';

const G = GROUND_Y;
const C = { // js/live/gates.js C
  panel: [0.86, 0.87, 0.88, 1], panelE: [0.45, 0.25, 9, 0], cab: [0.8, 0.81, 0.82, 1], cabE: [0.4, 0.3, 9, 0],
  steel: [0.46, 0.47, 0.49, 1], steelE: [0.45, 0.7, 0, 0], dark: [0.07, 0.07, 0.08, 1], darkE: [0.85, 0, 0, 0],
  yellow: [0.9, 0.7, 0.08, 1], yellowE: [0.5, 0, 0, 0], tyre: [0.05, 0.05, 0.05, 1], tyreE: [0.9, 0, 0, 0],
  unit: [0.74, 0.75, 0.76, 1], unitE: [0.5, 0.2, 0, 0], lamp: [1, 0.93, 0.82, 1], lampE: [0.15, 0, 14, 0], amber: [1, 0.55, 0.05, 1], amberE: [0.2, 0, 14, 0],
};
// unit tube: x 0..1 along, y 0..1 up, z -0.5..0.5 across; walls + roof in the panel colour (tunnel material id 9 on the
// walls, uv.x along 0..1 scaled by the instance length in the shader, uv.y up 0..1), steel floor
function unitTubeGeometry() {
  const g = new Geo();
  const side = (z, n) => { const b = g.nv; const pts = [[0, 0, z], [1, 0, z], [1, 1, z], [0, 1, z]], uvs = [[0, 0], [1, 0], [1, 1], [0, 1]]; for (let i = 0; i < 4; i++) g.vert(pts[i], n, C.panel, C.panelE, uvs[i]); if (z > 0) g.idx.push(b, b + 1, b + 2, b, b + 2, b + 3); else g.idx.push(b, b + 2, b + 1, b, b + 3, b + 2); };
  side(0.5, [0, 0, 1]); side(-0.5, [0, 0, -1]);
  g.quad([0, 1, 0.5], [1, 1, 0.5], [1, 1, -0.5], [0, 1, -0.5], C.panel, [C.panelE[0], C.panelE[1], 0, 0]);
  g.quad([0, 0, -0.5], [1, 0, -0.5], [1, 0, 0.5], [0, 0, 0.5], C.steel, C.steelE);
  return geometryFromData(g.data());
}
function unitBoxGeometry() { const g = new Geo(); g.box([0, 0, 0], [1, 1, 1], [1, 1, 1, 1], [0.5, 0, 0, 0]); return geometryFromData(g.data()); }
function unitCylGeometry() { const g = new Geo(); g.cylinder(1, 1, 16, [1, 1, 1, 1], [0.5, 0, 0, 0], null, true); return geometryFromData(g.data()); }

// instance sinks: tube(a, b, w, h) | box(min, max, col, ext, M) | cyl(r, h, col, ext, M)
class Sink {
  constructor() { this.tubes = []; this.boxes = []; this.cyls = []; this.sprites = []; this.signs = []; }
  tube(a, b, w, h) {
    const d = v3.sub(b, a); const L = v3.len(d); if (L < 0.1) { this.tubes.push(null); return null; }
    const f = v3.mul(d, 1 / L); const r = v3.norm(v3.cross(f, [0, 1, 0])); const u = v3.cross(r, f);
    this.tubes.push({ M: new Float32Array([f[0] * L, f[1] * L, f[2] * L, 0, u[0] * h, u[1] * h, u[2] * h, 0, r[0] * w, r[1] * w, r[2] * w, 0, a[0], a[1], a[2], 1]), L });
    // end frames (gates.js tube(): steel boxes at s = 0.05 and L - 0.05)
    const P = (s) => v3.add(a, v3.mul(f, s)); const hw = w / 2;
    for (const s of [0.05, L - 0.05]) this.box([-0.08, -0.05, -hw - 0.06], [0.08, h + 0.06, hw + 0.06], C.steel, C.steelE, m4.basis(f, [0, 1, 0], P(s)));
    return { f, r, u, L };
  }
  box(mn, mx, col, ext, M) { this.boxes.push({ M: m4.mul(M, m4.mul(m4.translate(mn[0], mn[1], mn[2]), m4.scale(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]))), col, ext }); }
  cyl(r, h, col, ext, M) { this.cyls.push({ M: m4.mul(M, m4.scale(r, h, r)), col, ext }); }
}

// LiveGateSystem.bridgeGeo, emitting instance transforms (see header)
function bridgeParts(gs, g, b, k, S) {
  const P = gs.pose(g, b, k);
  const rcTop = [P.rc[0], P.floorY, P.rc[2]];
  const a0 = [P.attach[0], P.floorY, P.attach[2]];
  S.tube(v3.add(a0, v3.mul(P.u, -0.3)), v3.add(rcTop, v3.mul(P.u, -2.3)), 2.6, 3.0);
  const wl = b.fixedLen - 2.3;
  if (wl > 9) for (let d = 7; d < wl - 3; d += 14) { const c = v3.add(P.attach, v3.mul(P.u, d)); S.cyl(0.35, P.floorY - G - 0.05, C.steel, C.steelE, m4.translate(c[0], G, c[2])); }
  S.cyl(0.6, P.floorY - G - 0.3, C.steel, C.steelE, m4.translate(P.rc[0], G, P.rc[2]));
  S.cyl(2.45, 3.6, C.panel, [0.45, 0.25, 0, 0], m4.translate(P.rc[0], P.floorY - 0.3, P.rc[2]));
  const cabBack = v3.sub(P.cab, v3.mul(P.facing, 1.8)); cabBack[1] = P.cab[1];
  const dir = v3.norm(v3.sub(cabBack, rcTop)); const s0 = v3.add(rcTop, v3.mul(dir, 2.2));
  for (const [a, bb, w, h] of [[0, 0.42, 2.55, 2.85], [0.36, 0.74, 2.68, 2.98], [0.68, 1.0, 2.82, 3.12]]) S.tube(v3.add(s0, v3.mul(v3.sub(cabBack, s0), a)), v3.add(s0, v3.mul(v3.sub(cabBack, s0), bb)), w, h);
  const hdir = v3.norm([dir[0], 0, dir[2]]); const side = v3.norm(v3.cross(hdir, [0, 1, 0]));
  const du = v3.add(s0, v3.mul(v3.sub(cabBack, s0), 0.84));
  for (const sg of [-1, 1]) {
    const leg = v3.add(du, v3.mul(side, sg * 1.25));
    S.box([-0.16, 0, -0.16], [0.16, Math.max(0.2, du[1] - G - 0.95), 0.16], C.steel, C.steelE, m4.basis(hdir, [0, 1, 0], [leg[0], G + 0.95, leg[2]]));
    S.cyl(0.48, 0.34, C.tyre, C.tyreE, m4.mul(m4.basis(hdir, [0, 1, 0], [leg[0], G + 0.48, leg[2]]), m4.mul(m4.rotX(Math.PI / 2), m4.translate(0, -0.17, 0))));
  }
  S.box([-0.35, 0.72, -1.55], [0.35, 1.1, 1.55], C.steel, C.steelE, m4.basis(hdir, [0, 1, 0], [du[0], G, du[2]]));
  S.box([-0.35, -0.9, 1.5], [0.35, 0, 1.9], C.yellow, C.yellowE, m4.basis(hdir, [0, 1, 0], du));
  const pu = v3.add(s0, v3.mul(v3.sub(cabBack, s0), 0.55));
  S.box([-1.2, -1.5, -0.6], [1.2, -0.15, 0.6], C.unit, C.unitE, m4.basis(hdir, [0, 1, 0], pu));
  S.box([-0.5, -2.0, -0.45], [0.5, -1.5, 0.45], C.yellow, C.yellowE, m4.basis(hdir, [0, 1, 0], pu));
  const fc = P.facing; const cabM = m4.basis(fc, [0, 1, 0], P.cab);
  S.box([-1.8, -0.1, -1.8], [1.5, 3.2, 1.8], C.cab, C.cabE, cabM);
  S.box([-1.9, 3.2, -1.95], [1.65, 3.4, 1.95], C.steel, C.steelE, cabM);
  const bell = 0.45 + 0.4 * P.kk;
  for (let i = 0; i < 5; i++) S.box([1.5 + i * bell / 5, 0.05, -1.55 - (i % 2) * 0.05], [1.5 + (i + 1) * bell / 5, 3.0, 1.55 + (i % 2) * 0.05], C.dark, C.darkE, cabM);
  S.box([0.9, 3.4, -0.35], [1.3, 3.65, 0.35], C.dark, C.darkE, cabM);
  S.box([1.28, 3.42, -0.3], [1.31, 3.62, 0.3], C.lamp, C.lampE, cabM);
  S.cyl(0.14, 0.25, C.amber, C.amberE, m4.mul(cabM, m4.translate(-1.2, 3.4, 1.4)));
  S.sprites.push({ p: m4.xform(cabM, [-1.2, 3.8, 1.4]), c: [1, 0.55, 0.08], i: 70, s: 0.25, beacon: true, moving: k > 0.001 && k < 0.999 });
  S.sprites.push({ p: m4.xform(cabM, [1.45, 3.52, 0]), c: [1, 0.92, 0.8], i: 500, s: 0.35, dir: v3.norm(m4.xdir(cabM, [1, -0.8, 0])), k: 3, night: true });
  // service stair (always present at bridge heights; kept as instances even if degenerate so slot counts stay fixed)
  const out = v3.norm(v3.cross([0, 1, 0], fc)); const sd = v3.dot(out, v3.sub(P.cab, P.rc)) >= 0 ? 1 : -1;
  const stTop = v3.add(v3.add(P.cab, v3.mul(out, sd * 2.4)), v3.mul(fc, -0.6)); const hgt = Math.max(0.81, stTop[1] - G - 0.05);
  const run = hgt / Math.tan(40 * Math.PI / 180); const back = v3.mul([fc[0], 0, fc[2]], -1 / Math.hypot(fc[0], fc[2]));
  const stBot = v3.add(stTop, v3.mul(back, run)); stBot[1] = G;
  const sDir = v3.norm(v3.sub(stBot, stTop)); const lat = v3.norm(v3.cross(sDir, [0, 1, 0])); const up = v3.cross(lat, sDir);
  const sM = m4.basis(sDir, up, stTop); const sl = v3.dist(stTop, stBot);
  for (const zz of [-0.55, 0.55]) S.box([0, -0.28, zz - 0.05], [sl, 0.0, zz + 0.05], C.steel, C.steelE, sM);
  S.box([0, -0.14, -0.55], [sl, -0.06, 0.55], C.steel, C.steelE, sM);
  for (const zz of [-0.55, 0.55]) S.box([0, 0.86, zz - 0.025], [sl, 0.92, zz + 0.025], C.yellow, C.yellowE, sM);
  S.box([-1.1, -0.1, -0.7], [0.1, 0.0, 0.7], C.steel, C.steelE, m4.basis([back[0], 0, back[2]], [0, 1, 0], [stTop[0], stTop[1], stTop[2]]));
  // gate number signs on both sides of the outer tunnel (quads as in gates.js signQuad)
  const r = gs.atlas.map['gate:' + b.gate];
  if (r) {
    const Lh = 0.85, Lw = Lh * r.aspect; const mid = v3.add(s0, v3.mul(v3.sub(cabBack, s0), 0.84));
    for (const sg of [-1, 1]) {
      const n = v3.mul(side, sg); const c = v3.add(v3.add(mid, v3.mul(n, 1.46)), [0, 1.6, 0]); const along = v3.mul(hdir, -sg);
      const u0 = v3.add(c, v3.mul(along, -Lw / 2)), u1 = v3.add(c, v3.mul(along, Lw / 2));
      S.signs.push({ q: [v3.add(u0, [0, -Lh / 2, 0]), v3.add(u1, [0, -Lh / 2, 0]), v3.add(u1, [0, Lh / 2, 0]), v3.add(u0, [0, Lh / 2, 0])], n, r });
    }
  }
  return P;
}

export class Bridges3 {
  constructor(gateSys, { objMat, objMatInst, tubeMat, signFont, signMats }) {
    this.gs = gateSys; this.objMat = objMat; this.signFont = signFont; this.signMats = signMats;
    this.group = new THREE.Group(); this.group.name = 'gates';
    this.lookup = faceIndex(gateSys.atlas.map);
    this.bridges = []; for (const g of gateSys.gates) if (g.bridge) for (const b of g.bridges) this.bridges.push({ g, b });
    // slot layout from a dry run at rest
    let nt = 0, nb = 0, nc = 0;
    for (const B of this.bridges) { const S = new Sink(); bridgeParts(gateSys, B.g, B.b, 0, S); B.t0 = nt; B.b0 = nb; B.c0 = nc; B.nt = S.tubes.length; B.nb = S.boxes.length; B.nc = S.cyls.length; nt += B.nt; nb += B.nb; nc += B.nc; }
    const inst = (geo, n, mat, extra) => { const g = geo.clone(); for (const [name, size] of extra) g.setAttribute(name, new THREE.InstancedBufferAttribute(new Float32Array(n * size), size)); const m = new THREE.InstancedMesh(g, mat, n); m.castShadow = m.receiveShadow = true; m.frustumCulled = false; m.instanceMatrix.setUsage(THREE.DynamicDrawUsage); this.group.add(m); return m; };
    this.tubes = inst(unitTubeGeometry(), Math.max(1, nt), tubeMat, [['iData', 4]]);
    this.boxes = inst(unitBoxGeometry(), Math.max(1, nb), objMatInst, [['iCol', 4], ['iExt', 4]]);
    this.cyls = inst(unitCylGeometry(), Math.max(1, nc), objMatInst, [['iCol', 4], ['iExt', 4]]);
    this.tubes.name = 'bridgeTubes'; this.boxes.name = 'bridgeBoxes'; this.cyls.name = 'bridgeCyls';
    // vehicles: one InstancedMesh per LiveGateSystem vehicle type (tint in iData, material id 20)
    this.vehicles = {};
    for (const k in gateSys.vehicleMeshes) { const m = inst(geometryOf(gateSys.vehicleMeshes[k]), 256, tubeMat, [['iData', 4]]); m.count = 0; m.name = 'gse_' + k; this.vehicles[k] = m; }
    this.standMesh = null; this.staticSigns = null; this.dynSigns = null; this.sprites = []; this._moving = new Set(); this._tmp = new THREE.Matrix4();
  }
  writeBridge(B, k) {
    const S = new Sink(); bridgeParts(this.gs, B.g, B.b, k, S);
    const T = this._tmp; const td = this.tubes.geometry.attributes.iData.array;
    for (let i = 0; i < B.nt; i++) { const t = S.tubes[i]; T.fromArray(t ? t.M : new Float32Array(16)); this.tubes.setMatrixAt(B.t0 + i, T); td[(B.t0 + i) * 4] = t ? t.L : 1; }
    const bc = this.boxes.geometry.attributes.iCol.array, be = this.boxes.geometry.attributes.iExt.array;
    for (let i = 0; i < B.nb; i++) { const q = S.boxes[i]; T.fromArray(q.M); this.boxes.setMatrixAt(B.b0 + i, T); bc.set(q.col, (B.b0 + i) * 4); be.set(q.ext, (B.b0 + i) * 4); }
    const cc = this.cyls.geometry.attributes.iCol.array, ce = this.cyls.geometry.attributes.iExt.array;
    for (let i = 0; i < B.nc; i++) { const q = S.cyls[i]; T.fromArray(q.M); this.cyls.setMatrixAt(B.c0 + i, T); cc.set(q.col, (B.c0 + i) * 4); ce.set(q.ext, (B.c0 + i) * 4); }
    B.sprites = S.sprites; B.signs = S.signs; B.k = k;
  }
  flush() {
    for (const m of [this.tubes, this.boxes, this.cyls]) { m.instanceMatrix.needsUpdate = true; for (const a of Object.values(m.geometry.attributes)) if (a.isInstancedBufferAttribute) a.needsUpdate = true; }
  }
  signGroup(list) {
    const sb = new SignBuilder(this.signFont);
    for (const B of list) for (const s of B.signs || []) sb.addQuad(s.q, [[s.r.u0, s.r.v1], [s.r.u1, s.r.v1], [s.r.u1, s.r.v0], [s.r.u0, s.r.v0]], s.n, 1, this.lookup(s.r.u0, s.r.v0));
    return signMeshes(sb, this.signMats, 'bridgeSigns');
  }
  replace(key, obj) { if (this[key]) { this.group.remove(this[key]); this[key].traverse(o => o.geometry && o.geometry.dispose()); } this[key] = obj; if (obj) this.group.add(obj); }
  // the LiveGateSystem.items() animation step (gates.js items(): k = from + (to - from) * u; finished -> dirty)
  step(now) {
    const gs = this.gs; const moving = new Set();
    for (const [id, a] of gs.anims) { const u = Math.min(1, Math.max(0, (now - a.t0) / a.dur)); a.k = a.from + (a.to - a.from) * u; moving.add(id); if (u >= 1) { gs.anims.delete(id); gs.dirty = true; } }
    return moving;
  }
  update(now) {
    const gs = this.gs; const moving = this.step(now);
    const kOf = (B) => { const a = gs.anims.get(B.g.id); if (a) return gs.docks(B.g, B.b) ? a.k : 0; return B.g.acType && gs.docks(B.g, B.b) ? 1 : 0; };
    const setChanged = moving.size !== this._moving.size || [...moving].some(id => !this._moving.has(id));
    if (gs.dirty || !this.standMesh) {
      gs.dirty = false;
      for (const B of this.bridges) this.writeBridge(B, kOf(B));
      // stand ID + VDGS (standGeo) and vehicles around parked aircraft (placeVehicles), as gates.js build(now, true)
      const geo = new Geo(); const sgn = { pos: [], nrm: [], uv: [], ext: [], idx: [] };
      gs.vehicleBuckets = {}; for (const k in gs.vehicleMeshes) gs.vehicleBuckets[k] = [];
      gs.keepOut = gs.aircraftFootprints ? gs.aircraftFootprints() : [];
      for (const g of gs.gates) {
        if (!g.bridge) continue;
        if (!gs.anims.has(g.id) && g.acType) gs.placeVehicles(g, g.bridges.map(b => gs.pose(g, b, gs.docks(g, b) ? 1 : 0)));
        gs.standGeo(g, geo, sgn);
      }
      const sm = new THREE.Mesh(geometryFromData(geo.data()), this.objMat); sm.castShadow = sm.receiveShadow = true; sm.name = 'standEquipment';
      const sb = new SignBuilder(this.signFont); sb.addSignArrays(sgn, this.lookup);
      const grp = new THREE.Group(); grp.add(sm); grp.add(signMeshes(sb, this.signMats, 'standSigns')); this.replace('standMesh', grp);
      const T = this._tmp;
      for (const k in this.vehicles) {
        const list = gs.vehicleBuckets[k] || []; const m = this.vehicles[k]; const n = Math.min(list.length, m.instanceMatrix.count);
        const dd = m.geometry.attributes.iData.array;
        for (let i = 0; i < n; i++) { const q = list[i]; T.set(q[0], q[1], q[2], q[3], q[4], q[5], q[6], q[7], q[8], q[9], q[10], q[11], 0, 0, 0, 1); m.setMatrixAt(i, T); dd.set([q[12], q[13], q[14], q[15]], i * 4); }
        m.count = n; m.instanceMatrix.needsUpdate = true; m.geometry.attributes.iData.needsUpdate = true;
      }
      this.replace('staticSigns', this.signGroup(this.bridges.filter(B => !moving.has(B.g.id))));
      this.flush();
    } else if (moving.size) {
      for (const B of this.bridges) if (moving.has(B.g.id)) this.writeBridge(B, kOf(B));
      this.flush();
      if (setChanged) this.replace('staticSigns', this.signGroup(this.bridges.filter(B => !moving.has(B.g.id))));
    }
    if (moving.size) this.replace('dynSigns', this.signGroup(this.bridges.filter(B => moving.has(B.g.id))));
    else if (this.dynSigns) this.replace('dynSigns', null);
    this._moving = moving;
    this.sprites = []; for (const B of this.bridges) if (B.sprites) for (const s of B.sprites) this.sprites.push(s);
  }
}

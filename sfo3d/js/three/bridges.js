// Jet bridges, stand equipment (stand ID sign, VDGS) and ground service vehicles for the three.js renderer.
// Everything is decided and built by js/live/gates.js LiveGateSystem, unchanged: occupancy (setOccupant), docking
// animations, bridge geometry (bridgeGeo), stand equipment (standGeo), collision-checked vehicle placement
// (placeVehicles) and the split into a batched static set and a small per-frame set of moving bridges (build/items).
// This module only converts what items() returns:
//   'obj'  static bridges + stand equipment (one merged mesh, rebuilt by gates.js when occupancy changes) and the
//          moving bridges (rebuilt by gates.js every frame while a bridge docks/undocks: only those bridges)
//   'sign' gate-number / stand-ID / VDGS faces -> MSDF text (js/three/signs.js), looked up in gates.js's own atlas map
//   'objI' GSE per vehicle type -> one InstancedMesh each (instance data: 3x4 matrix rows + tint, world/gates.js inst())
// Using gates.js's own output (instead of re-deriving the bridge parts here) keeps the new renderer in step with the
// bridge geometry work going on in gates.js (docs/requests/static_geometry_round1.md: rotundaW, walkW, stowW, ...).
import { THREE } from './lib.js';
import { geometryOf } from './convert.js';
import { SignBuilder, faceIndex, signMeshes } from './signs.js';

export class Bridges3 {
  constructor(gateSys, { objMat, vehMat, signFont, signMats }) {
    this.gs = gateSys; this.objMat = objMat; this.vehMat = vehMat; this.signFont = signFont; this.signMats = signMats;
    this.group = new THREE.Group(); this.group.name = 'gates';
    this.lookup = faceIndex(gateSys.atlas.map);
    this.objs = new Map(); // shim Mesh -> three object
    this.sprites = []; this._m = new THREE.Matrix4();
  }
  _make(it) {
    const m = it.mesh;
    if (it.prog === 'obj') {
      const o = new THREE.Mesh(geometryOf(m), this.objMat); o.castShadow = it.castShadow !== false; o.receiveShadow = true; o.matrixAutoUpdate = false;
      return o;
    }
    if (it.prog === 'sign') {
      const d = m.data; const sb = new SignBuilder(this.signFont);
      sb.addSignArrays({ pos: d.pos, nrm: d.nrm, uv: d.uv, ext: d.extra }, this.lookup);
      return signMeshes(sb, this.signMats, 'gateSigns');
    }
    if (it.prog === 'objI') {
      const cap = Math.max(16, m.nInst);
      const g = geometryOf(m).clone(); g.setAttribute('iData', new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4));
      const o = new THREE.InstancedMesh(g, this.vehMat, cap); o.castShadow = o.receiveShadow = true; o.frustumCulled = false; o.count = 0; o.userData.cap = cap; o.userData.ver = -1;
      return o;
    }
    return null;
  }
  _instances(o, m) {
    if (o.userData.ver === m.instVersion) return; o.userData.ver = m.instVersion;
    const n = Math.min(m.nInst || 0, o.userData.cap); const A = m.inst; const D = o.geometry.attributes.iData.array; const T = this._m;
    for (let i = 0; i < n; i++) { const q = i * 16; T.set(A[q], A[q + 1], A[q + 2], A[q + 3], A[q + 4], A[q + 5], A[q + 6], A[q + 7], A[q + 8], A[q + 9], A[q + 10], A[q + 11], 0, 0, 0, 1); o.setMatrixAt(i, T); D[i * 4] = A[q + 12]; D[i * 4 + 1] = A[q + 13]; D[i * 4 + 2] = A[q + 14]; D[i * 4 + 3] = A[q + 15]; }
    o.count = n; o.instanceMatrix.needsUpdate = true; o.geometry.attributes.iData.needsUpdate = true;
  }
  update(now) {
    const items = this.gs.items(now); const alive = new Set();
    for (const it of items) {
      const m = it.mesh; if (!m) continue; alive.add(m);
      let o = this.objs.get(m);
      if (it.prog === 'objI' && o && (m.nInst || 0) > o.userData.cap) { this.group.remove(o); o.geometry.dispose(); o = null; this.objs.delete(m); }
      if (!o) { o = this._make(it); if (!o) continue; this.objs.set(m, o); this.group.add(o); }
      if (it.prog === 'objI') this._instances(o, m);
    }
    for (const [m, o] of this.objs) if (!alive.has(m)) {
      this.group.remove(o); this.objs.delete(m);
      o.traverse(q => { if (q.geometry) q.geometry.dispose(); }); // gates.js has disposed the mesh (dispose twice is a no-op)
    }
    this.sprites = this.gs.sprites;
  }
}

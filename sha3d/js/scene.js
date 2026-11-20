// forked from sfo3d@e3218d6 js/scene.js
// Scene assembly: static world items + dynamic aircraft, vehicles, light sprites
// sha3d changes: no SFO airport-grid import (stToWorld / GROUND_Y) and no parkAtGates (the old-renderer demo that parked
// random aircraft at SFO gates: never unlabelled synthetic traffic in sha3d). The gate system is attached by the gates
// extension (js/live/gates.js, another package) as scene.gateSys with items(nowMs) -> renderer items.
import { gl, Mesh } from './gl.js';
import { m4, v3, rng } from './math.js';
import { AC_VS, AC_FS } from './shaders/aircraft.js';
import { ACR_VS, ACR_FS } from './shaders/aircraft_real.js';
import { SPRITE_VS, SPRITE_FS, SMOKE_VS, SMOKE_FS } from './shaders/sprites.js';

export class Scene {
  constructor(R, world) {
    this.R = R; this.world = world; this.aircraft = []; this.dynamicItems = []; this.staticLights = [];
    R.addProgram('aircraft', AC_VS, AC_FS);
    R.addProgram('acr', ACR_VS, ACR_FS);
    R.addProgram('sprite', SPRITE_VS, SPRITE_FS);
    R.addProgram('smoke', SMOKE_VS, SMOKE_FS);
    this.smokeMesh = new Mesh({ pos: new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, -1, 0, 1, 1, 0, -1, 1, 0]) });
    this.smokeFns = [];
    this.spriteMesh = new Mesh({ pos: new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, -1, 0, 1, 1, 0, -1, 1, 0]) });
    this.spriteBuf = new Float32Array(16 * 20000);
    this.extraItemFns = [];
  }
  add(ac) { this.aircraft.push(ac); return ac; }
  frame(t, camPos) {
    const R = this.R;
    const items = this.world.items.slice();
    for (const ac of this.aircraft) { const it = ac.items(camPos); for (let i = 0; i < it.length; i++) items.push(it[i]); }
    if (this.gateSys && this.gateSys.items) items.push(...this.gateSys.items(Date.now()));
    // draw order for early-z: occluders first, expensive ground last
    const pri = { acr: 0, aircraft: 0, obj: 1, objI: 1, decal: 2, water: 3, ground: 4 };
    items.sort((a, b) => (pri[a.prog] ?? 5) - (pri[b.prog] ?? 5));
    for (const fn of this.extraItemFns) items.push(...fn(t));
    // sprites
    let n = 0; const B = this.spriteBuf;
    const put = (s) => { if (n >= 20000) return; const o = n * 16; B[o] = s.p[0]; B[o + 1] = s.p[1]; B[o + 2] = s.p[2]; B[o + 3] = s.s; B[o + 4] = s.c[0]; B[o + 5] = s.c[1]; B[o + 6] = s.c[2]; B[o + 7] = s.i; const d = s.dir || [0, 1, 0]; B[o + 8] = d[0]; B[o + 9] = d[1]; B[o + 10] = d[2]; B[o + 11] = s.dir ? (s.k || 4) : 0; B[o + 12] = s.lens ? 1 : 0; n++; };
    for (const ac of this.aircraft) ac.lightSprites(t).forEach(put);
    for (const L of this.staticLights) { if (typeof L === 'function') L(t).forEach(put); else put(L); }
    this.spriteMesh.setInstances(B.subarray(0, n * 16), n);
    // smoke particles (sorted back to front)
    const parts = []; for (const fn of this.smokeFns) parts.push(...fn(t));
    if (parts.length) {
      const cp = R.curCam ? R.curCam.pos : [0, 0, 0];
      parts.sort((a, b) => v3.dist(b.p, cp) - v3.dist(a.p, cp));
      const SB = new Float32Array(parts.length * 16);
      parts.forEach((q, i) => { const o = i * 16; SB[o] = q.p[0]; SB[o + 1] = q.p[1]; SB[o + 2] = q.p[2]; SB[o + 3] = q.s; SB[o + 4] = q.a; SB[o + 5] = q.seed; });
      this.smokeMesh.setInstances(SB, parts.length);
      items.push({ mesh: this.smokeMesh, prog: 'smoke', blend: 'alpha', bbox: null, castShadow: false, noCull: true,
        uniforms: () => { const C = R.curCam; const right = v3.norm(v3.cross(C.dir, C.up)); const up = v3.cross(right, C.dir); return { uCamRight: right, uCamUp: up }; } });
    }
    items.push({ mesh: this.spriteMesh, prog: 'sprite', blend: 'add', bbox: null, castShadow: false, noCull: true,
      uniforms: () => { const C = R.curCam; const right = v3.norm(v3.cross(C.dir, C.up)); const up = v3.cross(right, C.dir); return { uCamRight: right, uCamUp: up, uFovScale: 2 * Math.tan(C.fov / 2) / R.H }; } });
    return { items };
  }
  commit() { for (const ac of this.aircraft) ac.commit(); }
}

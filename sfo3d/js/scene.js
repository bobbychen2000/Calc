// Scene assembly: static world items + dynamic aircraft, vehicles, light sprites
import { gl, Mesh } from './gl.js';
import { m4, v3, rng } from './math.js';
import { stToWorld, GROUND_Y } from './geo.js';
import { Aircraft, liveryFor, LIVERIES } from './aircraft/fleet.js';
import { TYPES } from './aircraft/model.js';
import { AC_VS, AC_FS } from './shaders/aircraft.js';
import { ACR_VS, ACR_FS } from './shaders/aircraft_real.js';
import { SPRITE_VS, SPRITE_FS, SMOKE_VS, SMOKE_FS } from './shaders/sprites.js';
import { GateSystem } from './world/gates.js';

export const stDir = (d) => { const a = stToWorld(d[0], d[1], 0), o = stToWorld(0, 0, 0); return v3.norm([a[0] - o[0], 0, a[2] - o[2]]); };

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
  parkAtGates(gates, opts = {}) {
    const R = rng(opts.seed || 7); const skip = new Set(opts.skip || []);
    const M = { B39M: 'b39m', B38M: 'b38m', B738: 'b738', B739: 'b739', B737: 'b737', B789: 'b789', B772: 'b772', B77W: 'b77w', B753: 'b753', B752: 'b752', A319: 'a319', A320: 'a320', A321: 'a321', A21N: 'a21n', E75L: 'e75l', CRJ2: 'crj2', BCS3: 'bcs3' };
    const livePool = (opts.liveParked || []).filter(a => M[a.icao]).map(a => ({ key: M[a.icao], flight: a.flight, wide: TYPES[M[a.icao]].cls !== 'C' }));
    for (const g of gates) {
      if (skip.has(g.id)) continue;
      if (R() < (opts.emptyFrac ?? 0.12)) { g.empty = true; continue; }
      const pick = (tbl) => { let u = R() * tbl.reduce((s, x) => s + x[1], 0); for (const [k, w] of tbl) { if ((u -= w) <= 0) return k; } return tbl[0][0]; };
      const type = g.cls === 'F' ? 'a388' : g.cls === 'E' ? pick([['b77w', 0.26], ['b789', 0.24], ['a359', 0.2], ['b763', 0.12], ['b748', 0.12]]) :
        pick([['b738', 0.2], ['b38m', 0.14], ['a20n', 0.17], ['a21n', 0.14], ['b752', 0.09], ['bcs3', 0.07], ['e75l', 0.11], ['crj9', 0.08]]);
      let typeK = type, liv = LIVERIES[Math.floor(R() * LIVERIES.length)];
      const li = livePool.findIndex(p => p.wide === (g.cls !== 'C') && (g.cls !== 'F'));
      if (li >= 0) { const p = livePool.splice(li, 1)[0]; typeK = p.key; liv = liveryFor(p.flight, liv); }
      else if (g.cls === 'C' && R() < 0.5) liv = liveryFor(['UAL', 'UAL', 'SKW', 'ASA', 'SWA', 'JBU', 'AAL', 'DAL'][Math.floor(R() * 8)] + '1', liv);
      const ac = new Aircraft(typeK, liv, { lod: 0, id: 'P' + g.id, dirt: 0.3 + R() * 0.5 });
      const xMain = ac.T.xMain;
      const main = [g.nose[0] - g.dir[0] * xMain, g.nose[1] - g.dir[1] * xMain];
      ac.pos = stToWorld(main[0], main[1], GROUND_Y); ac.fwd = stDir(g.dir);
      ac.lightsOn = { nav: true, beacon: R() < 0.2, strobe: false, landing: false, taxi: false };
      g.aircraft = ac; g.acType = typeK; this.add(ac);
    }
    this.gateSys = new GateSystem(gates);
    this.dynBridges = []; this.extraVehicles = {};
  }
  frame(t, camPos) {
    const R = this.R;
    const items = this.world.items.slice();
    for (const ac of this.aircraft) { const it = ac.items(camPos); for (let i = 0; i < it.length; i++) items.push(it[i]); }
    if (this.gateSys) items.push(...(this.gateSys.live ? this.gateSys.items(Date.now()) : this.gateSys.items(this.dynBridges, this.extraVehicles)));
    // draw order for early-z: occluders first, expensive ground last
    const pri = { acr: 0, aircraft: 0, obj: 1, objI: 1, decal: 2, water: 3, ground: 4 };
    items.sort((a, b) => (pri[a.prog] ?? 5) - (pri[b.prog] ?? 5));
    for (const fn of this.extraItemFns) items.push(...fn(t));
    // sprites
    let n = 0; const B = this.spriteBuf;
    const put = (s) => { if (n >= 20000) return; const o = n * 16; B[o] = s.p[0]; B[o + 1] = s.p[1]; B[o + 2] = s.p[2]; B[o + 3] = s.s; B[o + 4] = s.c[0]; B[o + 5] = s.c[1]; B[o + 6] = s.c[2]; B[o + 7] = s.i; const d = s.dir || [0, 1, 0]; B[o + 8] = d[0]; B[o + 9] = d[1]; B[o + 10] = d[2]; B[o + 11] = s.dir ? (s.k || 4) : 0; n++; };
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

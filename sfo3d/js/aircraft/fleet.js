// Aircraft instances: meshes per type/LOD, per-frame transforms of animated parts, liveries, lights
import { Mesh } from '../gl.js';
import { m4, v3 } from '../math.js';
import { buildAircraft, TYPES } from './model.js';
import { cockpitPanes } from './cockpit.js';
const COCK_STYLE = { boeing: 0, airbus: 1, '787': 2, a350: 3 };

export const LIVERIES = [
  { name: 'navy', top: [0.93, 0.93, 0.94], belly: [0.62, 0.64, 0.68], tail: [0.07, 0.13, 0.33], tail2: [0.12, 0.3, 0.62], eng: [0.07, 0.13, 0.33], stripe: [0, 0, 0, 0], bellyLine: -0.55, tailStyle: 1 },
  { name: 'red', top: [0.94, 0.94, 0.94], belly: [0.94, 0.94, 0.94], tail: [0.62, 0.06, 0.08], tail2: [0.95, 0.95, 0.95], eng: [0.93, 0.93, 0.93], stripe: [0.62, 0.06, 0.08, 1], bellyLine: -5, tailStyle: 1 },
  { name: 'teal', top: [0.95, 0.95, 0.95], belly: [0.95, 0.95, 0.95], tail: [0.05, 0.36, 0.42], tail2: [0.05, 0.16, 0.3], eng: [0.05, 0.16, 0.3], stripe: [0, 0, 0, 0], bellyLine: -5, tailStyle: 1 },
  { name: 'darkblue', top: [0.93, 0.93, 0.94], belly: [0.1, 0.16, 0.3], tail: [0.1, 0.16, 0.3], tail2: [0.75, 0.6, 0.25], eng: [0.1, 0.16, 0.3], stripe: [0, 0, 0, 0], bellyLine: -0.2, tailStyle: 1 },
  { name: 'gray', top: [0.9, 0.9, 0.91], belly: [0.55, 0.57, 0.6], tail: [0.55, 0.57, 0.6], tail2: [0.85, 0.2, 0.15], eng: [0.9, 0.9, 0.91], stripe: [0.2, 0.3, 0.55, 1], bellyLine: -0.7, tailStyle: 1 },
  { name: 'green', top: [0.95, 0.95, 0.95], belly: [0.95, 0.95, 0.95], tail: [0.1, 0.38, 0.25], tail2: [0.9, 0.75, 0.2], eng: [0.1, 0.38, 0.25], stripe: [0, 0, 0, 0], bellyLine: -5, tailStyle: 1 },
  { name: 'orange', top: [0.95, 0.95, 0.95], belly: [0.3, 0.32, 0.36], tail: [0.95, 0.45, 0.1], tail2: [0.3, 0.32, 0.36], eng: [0.95, 0.95, 0.95], stripe: [0, 0, 0, 0], bellyLine: -0.6, tailStyle: 1 },
  { name: 'sky', top: [0.93, 0.94, 0.95], belly: [0.93, 0.94, 0.95], tail: [0.2, 0.45, 0.8], tail2: [0.95, 0.8, 0.2], eng: [0.2, 0.45, 0.8], stripe: [0.2, 0.45, 0.8, 1], bellyLine: -5, tailStyle: 1 },
  { name: 'burgundy', top: [0.94, 0.93, 0.92], belly: [0.45, 0.08, 0.14], tail: [0.45, 0.08, 0.14], tail2: [0.8, 0.65, 0.35], eng: [0.94, 0.93, 0.92], stripe: [0, 0, 0, 0], bellyLine: -0.9, tailStyle: 1 },
  { name: 'purple', top: [0.95, 0.95, 0.96], belly: [0.95, 0.95, 0.96], tail: [0.3, 0.12, 0.45], tail2: [0.85, 0.3, 0.5], eng: [0.3, 0.12, 0.45], stripe: [0, 0, 0, 0], bellyLine: -5, tailStyle: 1 },
  { name: 'silver', top: [0.72, 0.74, 0.76], belly: [0.72, 0.74, 0.76], tail: [0.12, 0.22, 0.45], tail2: [0.8, 0.12, 0.12], eng: [0.72, 0.74, 0.76], stripe: [0, 0, 0, 0], bellyLine: -5, tailStyle: 1 },
  { name: 'yellowtail', top: [0.95, 0.95, 0.95], belly: [0.25, 0.28, 0.33], tail: [0.95, 0.72, 0.1], tail2: [0.25, 0.28, 0.33], eng: [0.25, 0.28, 0.33], stripe: [0, 0, 0, 0], bellyLine: -0.4, tailStyle: 1 },
  { name: 'white', top: [0.95, 0.95, 0.95], belly: [0.95, 0.95, 0.95], tail: [0.95, 0.95, 0.95], tail2: [0.2, 0.25, 0.5], eng: [0.95, 0.95, 0.95], stripe: [0.15, 0.25, 0.55, 1], bellyLine: -5, tailStyle: 0 },
];

// airline -> color family (generic schemes; no logos or wordmarks)
export const AIRLINE_LIVERY = {
  UAL: { name: 'ualish', top: [0.94, 0.94, 0.95], belly: [0.16, 0.3, 0.6], tail: [0.07, 0.14, 0.34], tail2: [0.16, 0.3, 0.6], eng: [0.07, 0.14, 0.34], stripe: [0, 0, 0, 0], bellyLine: -0.35, tailStyle: 1 },
  SKW: 'UAL', ASA: { name: 'asaish', top: [0.95, 0.95, 0.96], belly: [0.95, 0.95, 0.96], tail: [0.05, 0.15, 0.32], tail2: [0.1, 0.55, 0.6], eng: [0.05, 0.15, 0.32], stripe: [0.1, 0.55, 0.6, 1], bellyLine: -5, tailStyle: 1 },
  SWA: { name: 'swaish', top: [0.18, 0.3, 0.64], belly: [0.93, 0.93, 0.94], tail: [0.18, 0.3, 0.64], tail2: [0.85, 0.15, 0.2], eng: [0.18, 0.3, 0.64], stripe: [0, 0, 0, 0], bellyLine: 0.1, tailStyle: 1 },
  JBU: { name: 'jbuish', top: [0.95, 0.95, 0.96], belly: [0.95, 0.95, 0.96], tail: [0.1, 0.2, 0.5], tail2: [0.2, 0.45, 0.8], eng: [0.1, 0.2, 0.5], stripe: [0, 0, 0, 0], bellyLine: -5, tailStyle: 1 },
  AAL: { name: 'aalish', top: [0.76, 0.78, 0.8], belly: [0.76, 0.78, 0.8], tail: [0.15, 0.3, 0.6], tail2: [0.8, 0.12, 0.15], eng: [0.76, 0.78, 0.8], stripe: [0, 0, 0, 0], bellyLine: -5, tailStyle: 1 },
  DAL: { name: 'dalish', top: [0.95, 0.95, 0.96], belly: [0.08, 0.12, 0.28], tail: [0.08, 0.12, 0.28], tail2: [0.75, 0.1, 0.15], eng: [0.08, 0.12, 0.28], stripe: [0, 0, 0, 0], bellyLine: -0.25, tailStyle: 1 },
  ACA: { name: 'acaish', top: [0.95, 0.95, 0.96], belly: [0.25, 0.26, 0.28], tail: [0.08, 0.08, 0.09], tail2: [0.75, 0.1, 0.1], eng: [0.95, 0.95, 0.96], stripe: [0, 0, 0, 0], bellyLine: -0.5, tailStyle: 1 },
  CPA: { name: 'cpaish', top: [0.95, 0.95, 0.96], belly: [0.7, 0.72, 0.74], tail: [0.1, 0.4, 0.35], tail2: [0.95, 0.95, 0.96], eng: [0.95, 0.95, 0.96], stripe: [0, 0, 0, 0], bellyLine: -0.6, tailStyle: 1 },
};
// livery colours are authored as sRGB display values; shading works in linear light
const s2l = (v) => v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
export function linearLivery(L) {
  if (L._lin) return L._lin;
  const c = (a) => a.map(s2l);
  L._lin = { top: c(L.top), belly: c(L.belly), tail: c(L.tail), tail2: c(L.tail2), eng: c(L.eng), stripe: [s2l(L.stripe[0]), s2l(L.stripe[1]), s2l(L.stripe[2]), L.stripe[3]] };
  Object.defineProperty(L, '_lin', { enumerable: false });
  return L._lin;
}
export function liveryFor(flight, fallback) { const code = flight ? flight.slice(0, 3) : null; let L = code && AIRLINE_LIVERY[code]; if (typeof L === 'string') L = AIRLINE_LIVERY[L]; return L || fallback; }
const cache = {};
export function meshes(type, lod) {
  const key = type + ':' + lod; if (cache[key]) return cache[key];
  const A = buildAircraft(type, lod);
  const bb = (d) => d.bbox;
  const out = {
    A, body: new Mesh(A.body),
    gear: A.gear.map(g => ({ ...g, mesh: new Mesh(g.data) })),
    flaps: A.flaps.map(f => ({ ...f, mesh: new Mesh(f.data) })),
    spoilers: A.spoilers.map(s => ({ ...s, mesh: new Mesh(s.data) })),
  };
  cache[key] = out; return out;
}

export function rotAxisAbout(axis, angle, pivot) {
  const [x, y, z] = v3.norm(axis); const c = Math.cos(angle), s = Math.sin(angle), t = 1 - c;
  const R = new Float32Array([t * x * x + c, t * x * y + s * z, t * x * z - s * y, 0, t * x * y - s * z, t * y * y + c, t * y * z + s * x, 0, t * x * z + s * y, t * y * z - s * x, t * z * z + c, 0, 0, 0, 0, 1]);
  return m4.mul(m4.translate(pivot[0], pivot[1], pivot[2]), m4.mul(R, m4.translate(-pivot[0], -pivot[1], -pivot[2])));
}

export class Aircraft {
  constructor(type, livery, opts = {}) {
    this.type = type; this.lod = opts.lod ?? 1; this.M = meshes(type, this.lod); this.T = TYPES[type];
    this.liv = typeof livery === 'number' ? LIVERIES[livery % LIVERIES.length] : livery;
    this.pos = [0, 0, 0]; this.fwd = [1, 0, 0]; this.pitch = 0; this.roll = 0;
    this.gear = 1; this.flaps = 0; this.spoilers = 0; this.lightsOn = { nav: true, beacon: true, strobe: false, landing: false, taxi: false };
    this.prev = {}; this.id = opts.id || ''; this.dirt = opts.dirt ?? 0.4; this.visible = true;
    this.label = opts.label || null;
  }
  matrix() {
    const h = v3.norm([this.fwd[0], 0, this.fwd[2]]);
    const cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
    const f = [h[0] * cp, sp, h[2] * cp];
    const r0 = v3.norm(v3.cross(f, [0, 1, 0])); const u0 = v3.cross(r0, f);
    const cr = Math.cos(this.roll), sr = Math.sin(this.roll);
    const u = v3.add(v3.mul(u0, cr), v3.mul(r0, sr));
    return m4.basis(f, u, this.pos);
  }
  uniforms() {
    const L = this.liv, T = this.T, C = linearLivery(L);
    return {
      uLivTop: C.top, uLivBelly: C.belly, uLivTail: C.tail, uLivTail2: C.tail2, uLivEngine: C.eng, uLivStripe: C.stripe,
      uDims: [T.L, T.R, T.Hc, T.Ln], uWin: [T.win[0].x0, T.win[0].x1, T.win[0].sp, T.win[0].y], uWinSize: [T.win[0].w, T.win[0].h],
      uWin2: T.win[1] ? [T.win[1].x0, T.win[1].x1, T.win[1].sp, T.win[1].y] : [0, 0, 1, 0], uWinSize2: T.win[1] ? [T.win[1].w, T.win[1].h] : [0.1, 0.1],
      uCock: [T.cockpit.x0, T.cockpit.x1, T.cockpit.yb, T.cockpit.dmin ?? 0.18], uCock2: [T.cockpit.w, COCK_STYLE[T.cockpit.style] ?? 0, T.cockpit.slope ?? 0.05, 0],
      uDoors: [...T.doors, ...Array(5 - T.doors.length).fill(-100)], uBellyLine: L.bellyLine * T.R / 1.98, uDirt: this.dirt, uTailStyle: L.tailStyle,
      ...cockpitPanes(T).U, uSeed: this.seed ?? (this.seed = [...(this.id || 'x')].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 997, 7) / 997),
    };
  }
  items() {
    if (!this.visible) return [];
    const M = this.matrix(); const out = []; const U = this.uniforms();
    const bbR = this.T.L * 0.6;
    const bbox = [this.pos[0] - bbR, this.pos[1] - 5, this.pos[2] - bbR, this.pos[0] + bbR, this.pos[1] + this.T.L * 0.35, this.pos[2] + bbR];
    const push = (key, mesh, local) => {
      const model = local ? m4.mul(M, local) : M;
      const prevModel = this.prev[key] || model; this.nextPrev[key] = model;
      out.push({ mesh, prog: 'aircraft', model, prevModel, uniforms: U, bbox, castShadow: true, noCull: true });
    };
    this.nextPrev = {};
    push('body', this.M.body, null);
    this.M.gear.forEach((g, i) => { if (this.gear <= 0.001) return; push('g' + i, g.mesh, rotAxisAbout(g.axis, g.angle * (1 - this.gear), g.pivot)); });
    this.M.flaps.forEach((f, i) => {
      const d = this.flaps; const ang = d * (f.kind === 'inboard' ? 0.52 : 0.45); // radians trailing edge down
      const back = m4.translate(-f.chord * 0.42 * d, -f.chord * 0.1 * d, 0);
      push('f' + i, f.mesh, m4.mul(back, rotAxisAbout([0, 0, 1], ang, f.hinge)));
    });
    this.M.spoilers.forEach((s, i) => {
      const ax = v3.sub(s.hinge2, s.hinge);
      push('s' + i, s.mesh, rotAxisAbout(ax, -s.side * 0.8 * this.spoilers, s.hinge));
    });
    return out;
  }
  commit() { this.prev = this.nextPrev || {}; }
  // world positions of lights
  lightSprites(t) {
    const M = this.matrix(); const S = []; const Lt = this.M.A.lights; const on = this.lightsOn;
    const W = (p) => m4.xform(M, p); const D = (d) => v3.norm(m4.xdir(M, d));
    if (!this.visible) return S;
    if (on.nav) { S.push({ p: W(Lt.navL), c: [1, 0.06, 0.04], i: 40, s: 0.22 }); S.push({ p: W(Lt.navR), c: [0.1, 1, 0.3], i: 40, s: 0.22 }); S.push({ p: W(Lt.tail), c: [1, 1, 1], i: 25, s: 0.2 }); }
    if (on.beacon) { const f = Math.max(0, Math.sin(t * Math.PI * 2 * 1.0 + this.id.length)); const k = Math.pow(f, 8); S.push({ p: W(Lt.beaconTop), c: [1, 0.05, 0.02], i: 250 * k + 3, s: 0.25 }); S.push({ p: W(Lt.beaconBot), c: [1, 0.05, 0.02], i: 250 * k + 3, s: 0.25 }); }
    if (on.strobe) { const ph = (t * 1.1 + (this.id.length * 0.37)) % 1; const k = ph < 0.05 ? 1 : (ph > 0.12 && ph < 0.16 ? 1 : 0); if (k) { S.push({ p: W(Lt.strobeL), c: [1, 1, 1], i: 1500, s: 0.3 }); S.push({ p: W(Lt.strobeR), c: [1, 1, 1], i: 1500, s: 0.3 }); } }
    if (on.landing) { const d = D([1, -0.12, 0]); S.push({ p: W(Lt.landL), c: [1, 0.95, 0.85], i: 900, s: 0.35, dir: d, k: 10 }); S.push({ p: W(Lt.landR), c: [1, 0.95, 0.85], i: 900, s: 0.35, dir: d, k: 10 }); }
    if (on.taxi && this.gear > 0.5) { const d = D([1, -0.15, 0]); S.push({ p: W(Lt.taxi), c: [1, 0.96, 0.9], i: 500, s: 0.3, dir: d, k: 8 }); }
    return S;
  }
}

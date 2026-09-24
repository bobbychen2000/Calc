// Aircraft that renders an imported artist-built model (with procedural landing gear where the model has none),
// falling back to the procedural airframe while the model loads or when far away.
import { m4 } from '../math.js';
import { Aircraft, linearLivery } from '../aircraft/fleet.js';
import { TYPES } from '../aircraft/types.js';
import { getModel } from './models.js';
import { MODEL_DIMS } from '../../data/models/manifest.js';

// published overall heights (m), used to seat gear-less models at the right height above the ground
const HEIGHT = { a319: 11.76, a320: 11.76, a20n: 11.76, a321: 11.76, a21n: 11.76, b788: 16.92, b789: 17.02, b78x: 17.02, e170: 9.67, e75l: 9.86, e190: 10.57,
  bcs1: 11.5, bcs3: 11.5, crj2: 6.22, crj7: 7.57, crj9: 7.51, b752: 13.56, b753: 13.56, b762: 15.85, b763: 15.85, b764: 16.87, b744: 19.4, b748: 19.4,
  a332: 17.39, a333: 16.79, a359: 17.05, a35k: 17.08, a388: 24.09, md11: 17.6 };
const seated = new Set();
export function seatType(typeKey, modelKey) {
  const k = typeKey + ':' + modelKey; if (seated.has(k)) return; seated.add(k);
  const T = TYPES[typeKey], d = MODEL_DIMS[modelKey]; if (!T || !d || d.hasGear || !HEIGHT[typeKey]) return;
  const st = stretchFor(typeKey, modelKey);
  const s = T.L / (d.L + (st ? st.d1 + st.d2 : 0));
  const hc = HEIGHT[typeKey] - d.H * s;
  if (hc > d.R * s + 0.4 && hc < d.R * s + 4) T.Hc = +hc.toFixed(2);
}

// ICAO type designator -> { t: TYPES key (dimensions, gear, fallback), m: model key }
export const TYPE_MODELS = {
  B736: { t: 'b737', m: 'b738' }, B737: { t: 'b737', m: 'b738' }, B738: { t: 'b738', m: 'b738' }, B739: { t: 'b739', m: 'b738' },
  B37M: { t: 'b38m', m: 'b738' }, B38M: { t: 'b38m', m: 'b738' }, B39M: { t: 'b39m', m: 'b738' }, B3XM: { t: 'b39m', m: 'b738' },
  A318: { t: 'a319', m: 'a319' }, A319: { t: 'a319', m: 'a319' }, A19N: { t: 'a319', m: 'a319' }, A320: { t: 'a320', m: 'a320' }, A20N: { t: 'a20n', m: 'a320' },
  A321: { t: 'a321', m: 'a321' }, A21N: { t: 'a21n', m: 'a321' },
  B788: { t: 'b788', m: 'b788' }, B789: { t: 'b789', m: 'b788' }, B78X: { t: 'b78x', m: 'b788' },
  E170: { t: 'e170', m: 'e170' }, E75L: { t: 'e75l', m: 'e75l' }, E75S: { t: 'e75l', m: 'e75l' }, E190: { t: 'e190', m: 'e190' }, E195: { t: 'e190', m: 'e190' }, E290: { t: 'e190', m: 'e190' }, E295: { t: 'e190', m: 'e190' },
  BCS1: { t: 'bcs1', m: 'bcs1' }, BCS3: { t: 'bcs3', m: 'bcs3' },
  CRJ2: { t: 'crj2', m: 'crj2' }, CRJ7: { t: 'crj7', m: 'crj7' }, CRJ9: { t: 'crj9', m: 'crj9' }, CRJX: { t: 'crj9', m: 'crj9' },
  B752: { t: 'b752', m: 'b752' }, B753: { t: 'b753', m: 'b752' },
  B762: { t: 'b762', m: 'b763' }, B763: { t: 'b763', m: 'b763' }, B764: { t: 'b764', m: 'b763' },
  B744: { t: 'b744', m: 'b744' }, B74F: { t: 'b744', m: 'b744' }, B748: { t: 'b748', m: 'b748' },
  A332: { t: 'a332', m: 'a333' }, A333: { t: 'a333', m: 'a333' }, A338: { t: 'a332', m: 'a333' }, A339: { t: 'a333', m: 'a333' },
  A359: { t: 'a359', m: 'a359' }, A35K: { t: 'a35k', m: 'a359' }, A388: { t: 'a388', m: 'a388' },
  MD11: { t: 'md11', m: 'md11' },
  B772: { t: 'b772', m: null }, B77L: { t: 'b772', m: null }, B773: { t: 'b77w', m: null }, B77W: { t: 'b77w', m: null }, B778: { t: 'b77w', m: null }, B779: { t: 'b77w', m: null },
};
// business jets: a uniformly scaled regional-jet airframe (T-tail, rear engines) at the type's published length
const BIZ_LEN = { GLF4: 26.92, GLF5: 29.39, GLF6: 30.41, G280: 20.3, GA5C: 29.4, GA6C: 30.4, GLEX: 30.3, GL5T: 29.5, GL7T: 33.8, CL30: 20.92, CL35: 20.92, CL60: 20.85,
  C56X: 15.79, C68A: 18.97, C700: 22.3, C750: 22.04, C25B: 15.6, C25C: 16.3, C560: 14.9, E55P: 15.9, E545: 19.7, E550: 20.7, E135: 26.33, E35L: 26.33,
  LJ45: 17.7, LJ60: 17.9, LJ75: 17.7, FA7X: 23.2, FA8X: 24.5, F900: 20.2, F2TH: 20.2, FA50: 18.5, H25B: 15.6, HDJT: 12.99, PC24: 16.85, BE40: 14.75 };
const NOSCALE = new Set(['sweep', 'dihedral', 'tcRoot', 'tcTip', 'top', 'wheels', 'flex', 'flat', 'noseTop', 'nose', 'pt', 'pb', 'pw', 'noseTip']);
function scaleObj(o, f) {
  if (Array.isArray(o)) return o.map(v => typeof v === 'number' ? v * f : (v && typeof v === 'object') ? scaleObj(v, f) : v);
  const r = {};
  for (const k in o) { const v = o[k]; r[k] = NOSCALE.has(k) ? (v && typeof v === 'object' ? JSON.parse(JSON.stringify(v)) : v) : typeof v === 'number' ? v * f : (v && typeof v === 'object') ? scaleObj(v, f) : v; }
  return r;
}
export function typeForIcao(icao) {
  if (!icao) return null;
  if (TYPE_MODELS[icao]) return TYPE_MODELS[icao];
  if (BIZ_LEN[icao]) {
    const key = 'biz_' + icao;
    if (!TYPES[key]) {
      const B = TYPES.crj2, f = BIZ_LEN[icao] / B.L;
      const T = scaleObj(B, f); T.name = icao; T.key = key; T.cls = 'B'; T.uniform = true; T.wing.y = B.wing.y; T.win.forEach((w, i) => { w.y = B.win[i].y * f; });
      TYPES[key] = T; HEIGHT[key] = HEIGHT.crj2 * f;
    }
    return { t: key, m: 'crj2', generic: 'business jet' };
  }
  return null;
}
// model key -> TYPES key the model was built from (for plug stretching)
export const MODEL_BASE = { b738: 'b738', a319: 'a319', a320: 'a320', a321: 'a321', b788: 'b788', e170: 'e170', e75l: 'e75l', e190: 'e190', bcs1: 'bcs1', bcs3: 'bcs3',
  crj2: 'crj2', crj7: 'crj7', crj9: 'crj9', b752: 'b752', b763: 'b763', b744: 'b744', b748: 'b748', a333: 'a333', a359: 'a359', a388: 'a388', md11: 'md11' };

export function stretchFor(typeKey, modelKey) {
  const base = MODEL_BASE[modelKey]; if (!base || base === typeKey) return null;
  const T = TYPES[typeKey], B = TYPES[base]; if (!T || !B || T.uniform) return null;
  const dL = T.L - B.L; if (Math.abs(dL) < 0.3) return null;
  // plug ahead of the wing = difference in wing root LE positions; rest behind
  const d1 = T.wing.rootLE - B.wing.rootLE, d2 = dL - d1;
  return { cut1: -(B.wing.rootLE - 1.0), cut2: -(B.wing.rootLE + B.wing.rootC + 1.0), d1, d2 };
}

const I4 = m4.ident();
export class LiveAircraft extends Aircraft {
  constructor(typeKey, modelKey, livery, opts = {}) {
    if (modelKey) seatType(typeKey, modelKey);
    super(typeKey, livery, opts);
    this.modelKey = modelKey; this.model = null; this.lodDist = opts.lodDist ?? 1600; this.farDist = opts.farDist ?? 14000; this.shadowDist = opts.shadowDist ?? 1500;
    this.cabin = 0; this.selected = 0; this._items = null;
    if (modelKey) {
      this.stretch = stretchFor(typeKey, modelKey);
      this.ready = getModel(modelKey, this.stretch).then(m => { this.model = m; this._items = null; }).catch(e => { console.log('model load failed', modelKey, e.message); });
    } else this.ready = Promise.resolve();
  }
  placement() {
    const T = this.T, d = this.model.dims; const s = T.L / d.L;
    const y = d.hasGear ? -d.low * s : T.Hc;
    return m4.mul(m4.translate(T.xMain, y, 0), m4.scale(s, s, s));
  }
  realUniforms(U) {
    const L = this.liv, T = this.T, d = this.model.dims; const s = T.L / d.L; const C = linearLivery(L);
    U.uLivTop = C.top; U.uLivBelly = C.belly; U.uLivTail = C.tail; U.uLivTail2 = C.tail2; U.uLivEngine = C.eng; U.uLivStripe = C.stripe;
    U.uBellyLine = (L.bellyLine * T.R / 1.98) / s; U.uTailStyle = L.tailStyle; U.uDirt = this.dirt;
    U.uFus = [d.R, d.Rz, d.tailX, d.L];
    const cockX = Math.max(2.5, (T.win && T.win[0] ? T.win[0].x0 - 0.45 : 0.12 * T.L)) / s;
    U.uFusB = [d.crown, d.belly, cockX, this.cabin];
    U.uLights = (this.lightsOn.landing || this.lightsOn.taxi) ? 1 : 0; U.uGearUp = this.gear <= 0.001 ? 1 : 0; U.uSel = this.selected;
    return U;
  }
  // exterior lights at the real model's wing tips / tail / crown once it is loaded (procedural positions until then)
  lightSprites(t) {
    const A = this.model && this.model.anchors;
    if (!A) return super.lightSprites(t);
    if (!this._lt || this._ltModel !== this.model) {
      const P = this.placement(); const X = (p, dx = 0, dy = 0, dz = 0) => p ? m4.xform(P, [p[0] + dx, p[1] + dy, p[2] + dz]) : null;
      const base = this.M.A.lights; const s = this.T.L / this.model.dims.L;
      this._lt = { ...base, navL: X(A.navL, -0.15 / s, 0, -0.1 / s), navR: X(A.navR, -0.15 / s, 0, 0.1 / s), strobeL: X(A.navL, -0.6 / s, 0, 0), strobeR: X(A.navR, -0.6 / s, 0, 0),
        tail: X(A.tail, -0.15 / s) || base.tail, beaconTop: X(A.beaconTop, 0, 0.12 / s) || base.beaconTop, beaconBot: X(A.beaconBot, 0, -0.12 / s) || base.beaconBot };
      this._ltModel = this.model;
    }
    const saved = this.M.A.lights; this.M.A.lights = this._lt;
    try { return super.lightSprites(t); } finally { this.M.A.lights = saved; }
  }
  procUniforms() {
    if (!this._pu || this._puLiv !== this.liv) { this._pu = super.uniforms(); this._puLiv = this.liv; }
    return this._pu;
  }
  uniforms() { return this.procUniforms(); }
  // items(camPos): real model near, procedural body at mid range, nothing far away (label/lights only)
  items(camPos) {
    if (!this.visible) return [];
    const d = camPos ? Math.hypot(camPos[0] - this.pos[0], camPos[1] - this.pos[1], camPos[2] - this.pos[2]) : 0;
    if (d > this.farDist) { this.nextPrev = {}; return []; }
    const W = this.matrix();
    const bbR = this.T.L * 0.6;
    const bbox = [this.pos[0] - bbR, this.pos[1] - 5, this.pos[2] - bbR, this.pos[0] + bbR, this.pos[1] + this.T.L * 0.35, this.pos[2] + bbR];
    const shadow = d < this.shadowDist;
    const M = this.model;
    this.nextPrev = {};
    if (!M || d > this.lodDist) {
      if (!M && d < this.lodDist && !this.modelKey) return super.items(); // no imported model for this type: full procedural airframe
      const prevModel = this.prev.body || W; this.nextPrev.body = W; // distant: body only (one draw)
      if (!this._bodyItem) this._bodyItem = { mesh: this.M.body, prog: 'aircraft', uniforms: null, noCull: true };
      return [Object.assign(this._bodyItem, { model: W, prevModel, uniforms: this.procUniforms(), bbox, castShadow: shadow })];
    }
    const model = m4.mul(W, this.placement());
    const prevModel = this.prev.real || model; this.nextPrev.real = model;
    if (!this._items) {
      this._U = {};
      this._items = M.draws.map(dr => ({ mesh: dr.sub, prog: 'acr', uniforms: Object.assign(Object.create(this._U), dr.U), noCull: true }));
    }
    this.realUniforms(this._U);
    const out = [];
    for (const it of this._items) { it.model = model; it.prevModel = prevModel; it.bbox = bbox; it.castShadow = shadow; out.push(it); }
    // procedural landing gear under the gear-less airframes
    if (this.gear > 0.001 && this.M.gear.length && !M.dims.hasGear) {
      const GU = this.procUniforms();
      this.M.gear.forEach((g, i) => {
        const key = 'g' + i;
        const gm = m4.mul(W, rotAxisAboutLocal(g.axis, g.angle * (1 - this.gear), g.pivot));
        const pm = this.prev[key] || gm; this.nextPrev[key] = gm;
        out.push({ mesh: g.mesh, prog: 'aircraft', model: gm, prevModel: pm, uniforms: GU, bbox, castShadow: shadow, noCull: true });
      });
    }
    return out;
  }
}

function rotAxisAboutLocal(axis, angle, pivot) {
  const l = Math.hypot(axis[0], axis[1], axis[2]); const x = axis[0] / l, y = axis[1] / l, z = axis[2] / l;
  const c = Math.cos(angle), s = Math.sin(angle), t = 1 - c;
  const R = new Float32Array([t * x * x + c, t * x * y + s * z, t * x * z - s * y, 0, t * x * y - s * z, t * y * y + c, t * y * z + s * x, 0, t * x * z + s * y, t * y * z - s * x, t * z * z + c, 0, 0, 0, 0, 1]);
  return m4.mul(m4.translate(pivot[0], pivot[1], pivot[2]), m4.mul(R, m4.translate(-pivot[0], -pivot[1], -pivot[2])));
}
export { I4 };

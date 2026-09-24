// Aircraft that renders an imported artist-built model (with procedural landing gear where the model has none),
// falling back to the procedural airframe while the model loads or when far away.
import { m4 } from '../math.js';
import { Aircraft, linearLivery } from '../aircraft/fleet.js';
import { TYPES } from '../aircraft/types.js';
import { getModel, getLiveryTexture } from './models.js';
import { resolveLivery } from './lookup.js';
import { liveryTextureFor } from '../aircraft/liveries.js';
import { TYPE_MODELS, MODEL_BASE, TYPE_MODEL, stretchFor, seatType, typeForIcao, BIZ_LEN } from '../aircraft/fit.js';

// The ICAO designator -> (airframe, model) mapping and the fit of each model to the published dimensions of its type
// (scale, fuselage plugs, wing span, fin height, seating, the door the jet bridge docks to) live in js/aircraft/fit.js,
// so tools/models/check_dims.py can run the same code. Re-exported here for the existing callers.
export { TYPE_MODELS, MODEL_BASE, TYPE_MODEL, stretchFor, seatType, typeForIcao, BIZ_LEN };

const I4 = m4.ident();
// ICAO designator of a TYPES key (reverse of ICAO_TYPES for the brand series lookup, first match)
const TYPE_ICAO = {};
for (const k in TYPE_MODELS) { const t = TYPE_MODELS[k].t; if (t && !TYPE_ICAO[t]) TYPE_ICAO[t] = k; }

// Livery: the app hands every aircraft the livery object of its track (js/live/lookup.js liveryForAirline). Until the
// track carries the registration, the aircraft resolves its brand itself from its ICAO address (US N-number) and type
// (lookup.js resolveLivery), so a SkyWest E175 in Alaska colours is painted Alaska. `liv` returns the resolved livery;
// assigning the same track livery again is a no-op. Imported models then wear the baked brand texture for their model and
// type when one exists (js/aircraft/liveries.js), else the neutral atlas recoloured by the livery's colour family.
export class LiveAircraft extends Aircraft {
  get liv() {
    if (this._livR === undefined || this._livRid !== this.id) { this._livR = resolveLivery(this._livIn, this.id, TYPE_ICAO[this.type] || null); this._livRid = this.id; }
    return this._livR;
  }
  set liv(L) { if (L === this._livIn) return; this._livIn = L; this._livR = undefined; }
  constructor(typeKey, modelKey, livery, opts = {}) {
    if (modelKey) seatType(typeKey, modelKey);
    super(typeKey, livery, opts);
    this.modelKey = modelKey; this.model = null; this.lodDist = opts.lodDist ?? 1600; this.farDist = opts.farDist ?? 14000; this.shadowDist = opts.shadowDist ?? 1500;
    this.cabin = 0; this.selected = 0; this._items = null;
    if (modelKey) {
      this.stretch = stretchFor(typeKey, modelKey);
      this.ready = getModel(modelKey, this.stretch).then(m => { this.model = m; this._items = null; }).catch(e => { console.log('model load failed', modelKey, e.message); });
    } else this.ready = Promise.resolve();
    this.livTex = null; this._livTexKey = null;
  }
  // brand livery texture for the loaded model (fetched once per brand x model x type group, shared)
  updateLiveryTexture() {
    const M = this.model; if (!M || !M.draws.some(d => d.atlas)) return;
    const L = this.liv; const f = L && L.brand ? liveryTextureFor(L.brand, this.modelKey, this.type) : null;
    const key = f ? f.url : null;
    if (key === this._livTexKey) return;
    this._livTexKey = key; this.livTex = null; this._items = null;
    if (!f) return;
    getLiveryTexture(f.url).then(t => { if (this._livTexKey === key) { this.livTex = t; this._items = null; } }).catch(() => {});
  }
  placement() {
    const T = this.T, d = this.model.dims; const s = T.L / d.L;   // d.L includes the fuselage plugs: s = T.fit.s
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
  // cached per livery object (js/live/app.js clears `_pu` when it re-assigns the track livery; the resolved livery decides)
  procUniforms() {
    if (!this._puc || this._puLiv !== this.liv) { this._puc = super.uniforms(); this._puLiv = this.liv; }
    return this._puc;
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
    this.updateLiveryTexture();
    if (!this._items) {
      this._U = {};
      this._items = M.draws.map(dr => ({ mesh: dr.sub, prog: 'acr', noCull: true,
        uniforms: Object.assign(Object.create(this._U), dr.U, dr.atlas && this.livTex ? { uAlbedo: this.livTex, uLivTex: 1 } : null) }));
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

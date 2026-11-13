// GA placeholder aircraft (hwd3d Phase 2, P3; new file, fork map 2.9). Real models are Phase 3: these are plainly
// placeholders - sized from the dimension record (js/aircraft/ga_dims.js: FAA ACD length / span / tail height, class
// rules for the layout), shaped by class (high / low wing, tail-wheel or tricycle gear, fixed gear on singles, V- / T-tail,
// one or two propellers, rear- or wing-mounted jet engines, a rotor and skids for helicopters), in neutral colours, with
// no registration, livery or windows. Nothing here imitates a particular airframe.
//
//   placeholderGeo(dims, { colour }) -> { body, gear, rotor | null, lights }   pure (Node-importable): Geo data in the
//       local frame +x forward, +y up, +z right (starboard), origin = main-gear ground contact (skid centre); `lights` =
//       local light anchors {navL, navR, tail, beaconTop, beaconBot, strobeL, strobeR, landL, landR, taxi}
//   class GaAircraft  (a drawable of js/scene.js: items(camPos), lightSprites(t), commit(), visible)
//       constructor(dims, { id, colour, lodDist, shadowDist }); fields pos [x, y, z] (main-gear contact, world),
//       fwd [x, 0, z] unit, pitch, roll (rad: nose up / right wing down positive), gear 0..1, rotor (rad/s), visible,
//       selected, lightsOn {nav, beacon, strobe, landing, taxi}; T = dims; ready (Promise); dispose()
// Light anchor positions follow 14 CFR 23.1385-1401 / 25.1385 placement in general terms (red left / green right wingtip,
// white aft, anticollision on top and bottom) [inf: positions on the placeholder, not on any surveyed airframe]; their
// intensities are js/env/aircraft_lights.js (P2; Part 25 values, the Part 23 check is open there).
import { Geo } from '../geom.js';
import { m4 } from '../math.js';
import { Mesh } from '../gl.js';
import { aircraftSprites } from '../env/aircraft_lights.js';

const PAINT = { body: [0.86, 0.87, 0.89, 1], wing: [0.80, 0.81, 0.83, 1], dark: [0.16, 0.17, 0.19, 1], tyre: [0.07, 0.07, 0.08, 1], metal: [0.55, 0.56, 0.58, 1], glass: [0.12, 0.15, 0.19, 1] };
const MAT = { paint: [0.45, 0.0, 0, 0], dark: [0.6, 0.0, 0, 0], tyre: [0.9, 0.0, 0, 0], metal: [0.35, 0.8, 0, 0], glass: [0.08, 0.0, 0, 0] };

// a flat prism: polygon [[u, v], ...] (CCW seen from +w), thickness t along w, placed by matrix M (local u -> x, w -> y,
// v -> z before M, i.e. Geo.extrude's (x, z) plane)
function slab(g, poly, t, col, ext, M) {
  const s = new Geo(); s.extrude(poly, -t / 2, t / 2, col, ext, col, ext); s.cap(poly, -t / 2, col, ext, false); g.merge(s, M);
}
function box(g, c, h, col, ext, M = null) {   // centre c, half sizes h
  const s = new Geo(); s.box([c[0] - h[0], c[1] - h[1], c[2] - h[2]], [c[0] + h[0], c[1] + h[1], c[2] + h[2]], col, ext); g.merge(s, M);
}
// lathe along +x: profile [[r, x], ...] (x ascending), centred at (y, z)
function body(g, prof, y, z, col, ext, seg = 14) {
  const s = new Geo(); s.lathe(prof.map(([r, x]) => [r, x]), seg, col, ext);
  // lathe is about +y: rotate y -> x (rotZ(-90 deg): (x, y, z) -> (y, -x, z)), then place
  g.merge(s, m4.mul(m4.translate(0, y, z), m4.rotZ(-Math.PI / 2)));
}
function wheel(g, x, z, r, w, yAxle) {
  const s = new Geo(); s.cylinder(r, w, 10, PAINT.tyre, MAT.tyre, null, true);
  g.merge(s, m4.mul(m4.translate(x, yAxle, z - w / 2), m4.rotX(Math.PI / 2)));
}

export function placeholderGeo(T, { colour = null } = {}) {
  const B = new Geo(), Gr = new Geo(); let Ro = null;
  const cBody = colour || PAINT.body;
  const L = T.L, nose = T.xMain, tail = T.xMain - T.L, R = T.R, Hc = T.Hc;
  const lights = {};
  if (T.cls === 'heli') {
    // pod + tail boom + fin + skids + mast; rotor separate (it turns)
    const pl = 0.42 * L, px0 = nose - pl;
    body(B, [[0.05, px0], [R * 0.9, px0 + 0.15 * pl], [R, px0 + 0.5 * pl], [R * 0.85, px0 + 0.85 * pl], [0.25, nose]], Hc, 0, cBody, MAT.paint);
    body(B, [[R * 0.35, tail + 0.4], [R * 0.3, px0 + 0.1]], Hc + 0.25 * R, 0, cBody, MAT.paint, 8);
    slab(B, [[tail, Hc], [tail + 0.9, Hc], [tail + 0.5, Hc + 1.3], [tail - 0.1, Hc + 1.2]], 0.12, cBody, MAT.paint, m4.mul(m4.translate(0, 0, 0), m4.rotX(-Math.PI / 2)));
    slab(B, [[tail + 0.6, -0.9], [tail + 1.2, -0.9], [tail + 1.2, 0.9], [tail + 0.6, 0.9]], 0.06, cBody, MAT.paint, m4.translate(0, Hc + 0.2, 0));
    box(B, [px0 + 0.62 * pl, Hc + R + 0.25, 0], [0.12, 0.25, 0.12], PAINT.metal, MAT.metal);
    // windscreen band [neutral dark, no glazing detail]
    body(B, [[R * 0.55, nose - 0.32 * pl], [R * 0.62, nose - 0.18 * pl], [0.2, nose - 0.02]], Hc + 0.12, 0, PAINT.glass, MAT.glass, 12);
    const sl = T.skidLen || 2.6, st = T.track / 2;
    for (const sz of [-st, st]) { box(B, [0, 0.06, sz], [sl / 2, 0.05, 0.05], PAINT.metal, MAT.metal); for (const sx of [-sl * 0.3, sl * 0.3]) box(B, [sx, (Hc - R) * 0.5 + 0.05, sz * 0.8], [0.04, (Hc - R) * 0.5, 0.04], PAINT.metal, MAT.metal); }
    for (const sx of [-sl * 0.3, sl * 0.3]) box(B, [sx, Hc - R + 0.02, 0], [0.04, 0.04, st * 0.8], PAINT.metal, MAT.metal);
    // rotor: blades about the mast (local frame of the mast top: origin at the hub)
    Ro = new Geo(); const nb = /^(EC45|EC35|A109|A139|H60|S76|B429|B407)$/.test(T.type || '') ? 4 : 2;   // blade count [inf]
    for (let k = 0; k < nb; k++) box(Ro, [T.rotor / 4, 0, 0], [T.rotor / 4, 0.03, 0.14], PAINT.dark, MAT.dark, m4.rotY(k * 2 * Math.PI / nb));
    box(Ro, [0, 0.05, 0], [0.18, 0.1, 0.18], PAINT.metal, MAT.metal);
    Ro.hub = [px0 + 0.62 * pl, Hc + R + 0.55, 0];
    Object.assign(lights, { navL: [px0 + 0.5 * pl, Hc, -R - 0.02], navR: [px0 + 0.5 * pl, Hc, R + 0.02], tail: [tail + 0.1, Hc + 0.6, 0],
      beaconTop: [px0 + 0.4 * pl, Hc + R + 0.02, 0], beaconBot: [px0 + 0.5 * pl, Hc - R - 0.02, 0], strobeL: null, strobeR: null,
      landL: [nose - 0.1, Hc - R * 0.5, -0.2], landR: [nose - 0.1, Hc - R * 0.5, 0.2], taxi: [nose - 0.2, Hc - R * 0.6, 0] });
  } else {
    const W = T.wing, jet = T.cls === 'jet', prop = !jet;
    // fuselage: nose (spinner or radome) -> cabin -> tail cone
    const tc = tail + 0.05 * L;
    body(B, [[0.08, tail], [R * 0.35, tail + 0.12 * L], [R * 0.85, nose - 0.55 * L], [R, nose - 0.35 * L], [R * 0.95, nose - 0.15 * L], [R * (prop ? 0.55 : 0.45), nose - (prop ? 0.05 : 0.08) * L], [0.05, nose]], Hc, 0, cBody, MAT.paint, 16);
    // windscreen band (dark, neutral) on the upper forward fuselage
    body(B, [[R * 0.7, nose - 0.30 * L], [R * 0.9, nose - 0.22 * L], [R * 0.6, nose - 0.13 * L]], Hc + R * 0.18, 0, PAINT.glass, MAT.glass, 12);
    if (prop) { body(B, [[0.02, nose - 0.02], [Math.min(0.32, R * 0.55), nose - 0.04], [0.02, nose + 0.35]], Hc, 0, PAINT.dark, MAT.dark, 10); }
    // wing (straight or swept planform slab) at the high / low position
    const yW = W.pos === 'high' ? Hc + R * 0.95 : Hc - R * 0.65, le = nose - W.rootLE, hs = W.span / 2, sw = Math.tan((W.sweep || 0) * Math.PI / 180);
    const thick = Math.max(0.12, 0.13 * W.rootC);
    for (const sg of [1, -1]) {
      const poly = sg > 0 ? [[le, 0], [le - W.rootC, 0], [le - hs * sw - W.tipC, hs], [le - hs * sw, hs]] : [[le - W.rootC, 0], [le, 0], [le - hs * sw, -hs], [le - hs * sw - W.tipC, -hs]];
      slab(B, poly, thick, PAINT.wing, MAT.paint, m4.translate(0, yW, 0));
      if (W.pos === 'high' && T.L < 12) box(B, [le - W.rootC * 0.4, (Hc + yW) / 2 - 0.1, sg * hs * 0.35], [0.05, (yW - Hc) * 0.7, 0.05], PAINT.metal, MAT.metal, null);   // strut [inf]
    }
    lights.navL = [le - hs * sw - W.tipC * 0.3, yW, -hs - 0.03]; lights.navR = [le - hs * sw - W.tipC * 0.3, yW, hs + 0.03];
    lights.strobeL = [le - hs * sw - W.tipC * 0.8, yW, -hs - 0.03]; lights.strobeR = [le - hs * sw - W.tipC * 0.8, yW, hs + 0.03];
    lights.landL = [le - 0.05, yW, -Math.min(2.0, hs * 0.35)]; lights.landR = [le - 0.05, yW, Math.min(2.0, hs * 0.35)];
    // tail: fin + horizontal stabiliser (conventional / T) or a V-tail
    const hx = nose - T.hstab.x, finH = Math.max(1.0, T.H - Hc - 0.2), finC = T.hstab.rootC * 1.2;
    const topY = Hc + finH;
    if (T.tail === 'V') {
      for (const sg of [1, -1]) {
        const M = m4.mul(m4.translate(0, Hc + R * 0.5, 0), m4.rotX(-sg * (Math.PI / 2 - 0.62)));   // ~35 deg dihedral [inf]
        slab(B, sg > 0 ? [[hx, 0], [hx - finC, 0], [hx - finC * 0.9, T.hstab.span * 0.42], [hx - finC * 0.35, T.hstab.span * 0.42]] : [[hx - finC, 0], [hx, 0], [hx - finC * 0.35, -T.hstab.span * 0.42], [hx - finC * 0.9, -T.hstab.span * 0.42]], 0.08, cBody, MAT.paint, M);
      }
      lights.tail = [tail + 0.02, Hc + R * 0.4, 0]; lights.beaconTop = [nose - 0.45 * L, Hc + R + 0.03, 0];
    } else {
      // fin: polygon in the (x, y) plane -> slab in (u = x, v = z) rotated so that v -> +y
      const finPoly = [[tail + 0.05, Hc + R * 0.3], [hx + 0.2 * finC, Hc + R * 0.3], [tail + 0.35 * finC + 0.1, topY], [tail + 0.1, topY]].map(([x, y]) => [x, -y]);
      slab(B, finPoly.slice().reverse(), 0.1, cBody, MAT.paint, m4.rotX(Math.PI / 2));
      const yH = T.tail === 'T' ? topY - 0.05 : Hc + R * 0.25, hsS = T.hstab.span / 2;
      for (const sg of [1, -1]) slab(B, sg > 0 ? [[hx, 0], [hx - T.hstab.rootC, 0], [hx - T.hstab.rootC * 0.85, hsS], [hx - T.hstab.rootC * 0.25, hsS]] : [[hx - T.hstab.rootC, 0], [hx, 0], [hx - T.hstab.rootC * 0.25, -hsS], [hx - T.hstab.rootC * 0.85, -hsS]], 0.07, cBody, MAT.paint, m4.translate(0, yH, 0));
      lights.tail = [tail + 0.02, Hc + R * 0.5, 0]; lights.beaconTop = [tail + 0.25 * finC, topY + 0.05, 0];
    }
    lights.beaconBot = [nose - 0.5 * L, Hc - R - 0.03, 0];
    // engines
    if (T.cls === 'twin' || (T.cls === 'turboprop' && T.sub === 'twin')) {
      for (const sg of [1, -1]) { const ez = sg * Math.max(R + 0.9, hs * 0.3), nl = Math.max(1.6, 0.22 * L);
        body(B, [[0.05, le - nl * 0.75], [0.36, le - nl * 0.5], [0.42, le - 0.1], [0.3, le + nl * 0.25], [0.05, le + nl * 0.3]], yW, ez, cBody, MAT.paint, 10);
        body(B, [[0.02, le + nl * 0.28], [0.18, le + nl * 0.3], [0.02, le + nl * 0.42]], yW, ez, PAINT.dark, MAT.dark, 8); }
    }
    if (jet) {
      const n = T.engines || 2, el = Math.max(1.4, 0.13 * L), er = Math.max(0.3, 0.06 * L * 0.6);
      if (T.sub === 'airliner') {
        for (const sg of [1, -1]) { const ez = sg * hs * 0.34, ex = le - hs * 0.34 * sw + el * 0.4; body(B, [[er * 0.9, ex - el], [er, ex - el * 0.6], [er * 0.95, ex], [er * 0.8, ex + 0.1]], yW - er * 1.1, ez, PAINT.metal, MAT.metal, 12); }
      } else if (n === 1) {   // single jet on the upper rear fuselage (SF50-like layout from the class: V-tail single) [inf]
        body(B, [[er * 0.8, tail + 0.18 * L], [er, tail + 0.25 * L], [er * 0.9, tail + 0.18 * L + el]], Hc + R + er * 0.7, 0, PAINT.metal, MAT.metal, 12);
      } else {
        for (const sg of (n >= 3 ? [1, -1, 0] : [1, -1])) { const ex = tail + 0.22 * L + el; const ez = sg * (R + er + 0.15), ey = sg === 0 ? Hc + R + er * 0.6 : Hc + R * 0.35;
          body(B, [[er * 0.8, ex - el], [er, ex - el * 0.7], [er * 0.95, ex], [er * 0.8, ex + 0.05]], ey, ez, PAINT.metal, MAT.metal, 12); }
      }
    }
    // gear (separate mesh: retractable gear is hidden in flight)
    const wr = Math.max(0.2, Math.min(0.6, 0.035 * L)), ww = wr * 0.6;
    for (const sg of [1, -1]) { wheel(Gr, 0, sg * T.track / 2, wr, ww, wr); box(Gr, [0, (wr + (W.pos === 'low' ? yW : Hc - R)) / 2, sg * T.track / 2 * 0.9], [0.05, Math.max(0.05, ((W.pos === 'low' ? yW : Hc - R) - wr) / 2), 0.05], PAINT.metal, MAT.metal); }
    const xw = T.xMain - T.xNose, wr2 = T.gearKind === 'tail' ? wr * 0.45 : wr * 0.8;
    wheel(Gr, xw, 0, wr2, ww * 0.8, wr2); box(Gr, [xw, (wr2 + Hc - R) / 2, 0], [0.04, Math.max(0.05, (Hc - R - wr2) / 2), 0.04], PAINT.metal, MAT.metal);
    lights.taxi = T.gearKind === 'tail' ? lights.landR : [xw + 0.1, wr2 + 0.4, 0];
  }
  return { body: B.data(), gear: Gr.nv ? Gr.data() : null, rotor: Ro ? Object.assign(Ro.data(), { hub: Ro.hub }) : null, lights };
}

// ---------------------------------------------------------------- drawable
const KEEP = new Map();   // geometry cache per dims record (types repeat: C172 x 40)
export class GaAircraft {
  constructor(T, { id = null, colour = null, lodDist = 6000, shadowDist = 2500 } = {}) {
    this.T = T; this.id = id; this.colour = colour; this.lodDist = lodDist; this.shadowDist = shadowDist;
    this.pos = [0, 0, 0]; this.fwd = [0, 0, -1]; this.pitch = 0; this.roll = 0; this.gear = 1; this.rotor = 0; this.rotorAng = 0;
    this.visible = true; this.alpha = 1; this.selected = false; this.lightsOn = { nav: false, beacon: false, strobe: false, landing: false, taxi: false };
    this.seed = Math.random() * 10; this.model = m4.ident(); this.prevModel = null; this.rotModel = m4.ident(); this.prevRot = null;
    this.ready = Promise.resolve(this); this.meshes = null;
  }
  geo() { const k = this.T; if (!KEEP.has(k)) KEEP.set(k, placeholderGeo(this.T, { colour: this.colour })); return KEEP.get(k); }
  ensure() {
    if (this.meshes) return this.meshes;
    const G = this.geo();
    // meshes are shared per geometry record as well (GPU memory: one per type, not per aircraft)
    if (!G._meshes) G._meshes = { body: new Mesh(G.body), gear: G.gear ? new Mesh(G.gear) : null, rotor: G.rotor ? new Mesh(G.rotor) : null };
    return (this.meshes = G._meshes);
  }
  basis() {
    const f = this.fwd, up = [0, 1, 0], r = [-f[2], 0, f[0]];
    const B = new Float32Array([f[0], 0, f[2], 0, 0, 1, 0, 0, r[0], 0, r[2], 0, this.pos[0], this.pos[1], this.pos[2], 1]);
    return m4.mul(m4.mul(B, m4.rotZ(this.pitch)), m4.rotX(this.roll));
  }
  items(camPos) {
    const M = this.ensure(); this.model = this.basis();
    const d = camPos ? Math.hypot(camPos[0] - this.pos[0], camPos[1] - this.pos[1], camPos[2] - this.pos[2]) : 0;
    if (d > this.lodDist) return [];
    const ext = Math.max(this.T.L, this.T.span, this.T.rotor || 0) * 0.6 + 1;
    const bbox = [this.pos[0] - ext, this.pos[1] - 1, this.pos[2] - ext, this.pos[0] + ext, this.pos[1] + this.T.H + 2, this.pos[2] + ext];
    const sh = d < this.shadowDist;
    const out = [{ mesh: M.body, prog: 'obj', model: this.model, prevModel: this.prevModel || this.model, bbox, castShadow: sh, uniforms: this.selected ? { uEmissiveBoost: 0.15 } : null }];
    if (M.gear && this.gear > 0.5) out.push({ mesh: M.gear, prog: 'obj', model: this.model, prevModel: this.prevModel || this.model, bbox, castShadow: sh });
    if (M.rotor) {
      const h = this.geo().rotor.hub; this.rotModel = m4.mul(this.model, m4.mul(m4.translate(h[0], h[1], h[2]), m4.rotY(this.rotorAng)));
      out.push({ mesh: M.rotor, prog: 'obj', model: this.rotModel, prevModel: this.prevRot || this.rotModel, bbox, castShadow: sh });
    }
    for (const it of out) { if (!it.uniforms) delete it.uniforms; it.noCull = true; it.alpha = this.alpha; }   // (slab winding is not checked face by face); alpha: screen-door fade
    return out;
  }
  step(dt) { this.rotorAng = (this.rotorAng + this.rotor * dt) % (Math.PI * 2); }
  worldPt(p) { return m4.xform(this.model, p); }
  lightSprites(t) {
    const on = this.lightsOn; if (!on || !(on.nav || on.beacon || on.strobe || on.landing || on.taxi)) return [];
    const Lc = this.geo().lights, W = {};
    for (const k in Lc) W[k] = Lc[k] ? this.worldPt(Lc[k]) : null;
    const fwd = m4.xdir(this.model, [1, 0, 0]), up = m4.xdir(this.model, [0, 1, 0]), right = m4.xdir(this.model, [0, 0, 1]);
    const landDir = m4.xdir(this.model, [Math.cos(0.05), -Math.sin(0.05), 0]), taxiDir = m4.xdir(this.model, [Math.cos(0.1), -Math.sin(0.1), 0]);
    try { return aircraftSprites(W, { fwd, right, up, landDir, taxiDir }, on, this.seed, t, this.gear); } catch (e) { return []; }
  }
  commit() { this.prevModel = this.model; this.prevRot = this.rotModel; }
  dispose() { this.meshes = null; }   // meshes are shared per type (released with the page)
}

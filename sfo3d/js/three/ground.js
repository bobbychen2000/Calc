// Terrain, airfield and water for the three.js renderer: TSL ports of js/shaders/ground.js and env.js WATER_FS.
//   - bakes (rendered to textures in tiles of at most 1024 x 1024 texels, a few per frame, as js/world/world.js
//     runBake did "to keep individual draws short": one full-target draw of the 16-sample far-city bake risks the GPU
//     watchdog on phones / Windows TDR, review round 1): BAKE_APT_FS (airfield albedo + coverage, green no-taxi paint),
//     BAKE_AUX_FS (seawall distance, concrete mask), BAKE_CITY_FS / BAKE_CITYFAR_FS (procedural city). The bake
//     materials use NoBlending: three r186 forces alpha = 1 for opaque materials with normal blending
//     (NodeMaterial.js 897-901), which erased the airfield coverage alpha (review round 1: airport grass drawn over the
//     Burlingame shore inside APT_RECT)
//   - per-pixel ground: GROUND_FS incl. groundfuncs runwayAt()/endMarkings()/glyph() — the SDF runway markings with
//     analytic anti-aliasing (FAA AC 150/5340-1M dimensions as documented in ground.js), blast-pad chevrons, rubber,
//     concrete joints; lit by three.js (sun + CSM shadows + PMREM IBL + GTAO + the apron floodlights, js/three/flood.js);
//     at night the city has street-light pools and lamp points (energy-conserving far away)
//   - water: WATER_FS wave-slope normals scaled with the wind, Fresnel via IOR 1.333, foam at the seawall; its sky
//     reflection is the same sky/cloud composition as the visible sky, evaluated along the reflected ray FROM THE WATER
//     POINT (review round 1: the IBL cube built at a fixed point showed clouds that were not in the visible sky)
// Geometry (terrain chunks, water grid) comes unchanged from js/live/world.js buildLiveWorld.
import { THREE, TSL } from './lib.js';
import { hash12, hash13, hash22, vnoise, fbm2, band } from './tsl/common.js';
import { geometryOf, textureOf } from './convert.js';
import { CITY_RECT, CITYFAR_RECT } from '../world/world.js';
import { APT_RECT } from '../world/airfield.js';
const { Fn, uniform, uniformArray, vec2, vec3, vec4, float, uv, texture, dot, exp, pow, sqrt, max, min, mix, smoothstep, step, clamp, normalize, length, abs, floor, fract, mod, select, If, fwidth, positionWorld, cameraPosition, normalWorld, cameraViewMatrix, sin, cos, atan, reflect } = TSL;

const toView = (nW) => normalize(cameraViewMatrix.mul(vec4(nW, 0.0)).xyz);

// ---------------------------------------------------------------- grass (groundfuncs grassCol)
function grassCol(p, fw) {
  const n1 = fbm2(p.mul(0.02), 4), n2 = vnoise(p.mul(0.25)), n3 = vnoise(p.mul(1.7));
  const c = mix(vec3(0.50, 0.42, 0.26), vec3(0.40, 0.33, 0.20), smoothstep(0.3, 0.7, n1)).toVar();
  c.assign(mix(c, vec3(0.26, 0.30, 0.15), smoothstep(0.55, 0.8, fbm2(p.mul(0.006).add(3.0), 3)).mul(0.7)));
  const det = float(1.0).sub(smoothstep(0.2, 1.0, fw));
  c.mulAssign(mix(float(0.5), n2, det).mul(0.3).add(0.85));
  c.mulAssign(mix(float(0.5), n3, float(1.0).sub(smoothstep(0.05, 0.3, fw))).mul(0.16).add(0.92));
  return c.mul(0.85);
}
const segD = (p, a, b) => { const pa = p.sub(a), ba = b.sub(a); const h = clamp(dot(pa, ba).div(dot(ba, ba)), 0.0, 1.0); return length(pa.sub(ba.mul(h))); };
// signed distance to the airport land polygon (16 points, constants), inside positive (BAKE_APT_FS polySDF)
function polySDF(p, poly) {
  const d = float(1e9).toVar(); const inside = float(0).toVar();
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length]; const A = vec2(a[0], a[1]), B = vec2(b[0], b[1]);
    d.assign(min(d, segD(p, A, B)));
    const cond = p.y.lessThan(a[1]).notEqual(p.y.lessThan(b[1])).and(p.x.lessThan(float(b[0] - a[0]).mul(p.y.sub(a[1])).div(b[1] - a[1] === 0 ? 1e-9 : b[1] - a[1]).add(a[0])));
    If(cond, () => { inside.assign(float(1.0).sub(inside)); });
  }
  return select(inside.greaterThan(0.5), d, d.negate());
}

// ---------------------------------------------------------------- procedural city (groundfuncs urbanSample)
// returns vec4(albedo, code) with code = kind + 3 * floor(h * 8) + 768 * tiltIndex (0 flat, 1 tilt -0.5, 2 tilt +0.5)
function makeUrban() {
  const H = (a, b, c) => hash13(vec3(a, b, c));
  return Fn(([xz, dens]) => {
    const col = vec3(0).toVar(), h = float(0).toVar(), kind = float(0).toVar(), tilt = float(0).toVar(), done = float(0).toVar();
    const zc = floor(xz.div(1100.0).add(vec2(0.37, 0.61))).toVar();
    const zh = (s) => H(zc.x, zc.y, float(s));
    const ang = float(0.46).add(zh(3).sub(0.5).mul(0.7)).toVar();
    const ca = cos(ang), sa = sin(ang);
    const q = vec2(ca.mul(xz.x).add(sa.mul(xz.y)), sa.negate().mul(xz.x).add(ca.mul(xz.y))).toVar();
    const bx = float(86.0).add(zh(5).mul(20.0)).toVar(), by = float(150.0).add(zh(6).mul(70.0)).toVar();
    const commercial = zh(9).lessThan(0.12).or(dens.lessThan(0.55));
    const cell = floor(q.div(vec2(bx, by))).toVar(); const f = q.sub(cell.mul(vec2(bx, by))).toVar();
    const sw = 10.5;
    const asphalt = vec3(0.13, 0.13, 0.135), sidewalk = vec3(0.3, 0.29, 0.27);
    const bc = cell.add(zc.mul(1000.0)).toVar();
    const bh = (s) => H(bc.x, bc.y, float(s));
    // park block
    If(bh(41).lessThan(0.05), () => {
      col.assign(mix(vec3(0.16, 0.2, 0.08), vec3(0.3, 0.3, 0.17), bh(42)));
      const c7 = floor(xz.div(7.0)); If(H(c7.x, c7.y, float(43)).lessThan(0.3), () => { col.assign(vec3(0.07, 0.1, 0.045)); kind.assign(2.0); h.assign(9.0); });
      done.assign(1.0);
    });
    If(done.lessThan(0.5).and(f.x.lessThan(sw).or(f.y.lessThan(sw))), () => {
      const e = min(f.x, f.y);
      col.assign(select(e.lessThan(1.5).or(e.greaterThan(sw - 1.5)), sidewalk, asphalt));
      const c8 = floor(xz.div(8.0));
      If(e.lessThan(2.8).or(e.greaterThan(sw - 2.8)).and(H(c8.x, c8.y, float(31)).lessThan(0.55)), () => { col.assign(vec3(0.075, 0.1, 0.045)); kind.assign(2.0); h.assign(8.0); });
      done.assign(1.0);
    });
    If(done.lessThan(0.5).and(commercial), () => {
      const g = f.sub(sw).toVar(); const bs = vec2(bx, by).sub(sw);
      const split = float(0.35).add(bh(1).mul(0.35)); const bldg = bh(2).lessThan(0.8);
      const inB = bldg.and(g.x.greaterThan(3.0)).and(g.x.lessThan(bs.x.sub(3.0))).and(g.y.greaterThan(3.0)).and(g.y.lessThan(bs.y.mul(split)));
      If(inB, () => {
        kind.assign(1.0); h.assign(float(7.0).add(bh(3).mul(12.0)));
        col.assign(mix(vec3(0.46, 0.46, 0.45), vec3(0.26, 0.26, 0.27), bh(4)));
        const hv = fract(g.div(9.0)); const gc = floor(g.div(9.0)).add(bc);
        If(H(gc.x, gc.y, float(8)).lessThan(0.12).and(hv.x.greaterThan(0.3)).and(hv.x.lessThan(0.7)).and(hv.y.greaterThan(0.3)).and(hv.y.lessThan(0.7)), () => { col.mulAssign(0.75); });
      }).Else(() => {
        col.assign(vec3(0.19, 0.19, 0.195));
        const stripe = step(0.93, fract(g.x.div(2.8))).mul(step(0.3, fract(g.y.div(12.0)))); col.assign(mix(col, vec3(0.6), stripe.mul(0.5)));
        const cc = floor(vec2(g.x.div(2.8), g.y.div(6.0))).toVar(); const cf = fract(vec2(g.x.div(2.8), g.y.div(6.0)));
        const hc = H(cc.x.add(bc.x), cc.y.add(bc.y), float(12));
        If(hc.lessThan(0.55).and(cf.x.greaterThan(0.18)).and(cf.x.lessThan(0.82)).and(cf.y.greaterThan(0.15)).and(cf.y.lessThan(0.85)).and(mod(cc.y, 2.0).lessThan(1.0)), () => {
          col.assign(mix(vec3(0.75), vec3(0.08, 0.09, 0.12), H(cc.x.add(bc.x), cc.y.add(bc.y), float(13)))); kind.assign(1.0); h.assign(1.4);
        });
        const c10 = floor(xz.div(10.0)); If(H(c10.x, c10.y, float(44)).lessThan(0.08), () => { col.assign(vec3(0.07, 0.1, 0.045)); kind.assign(2.0); h.assign(7.0); });
      });
      done.assign(1.0);
    });
    If(done.lessThan(0.5), () => {
      // residential lots
      const half = bx.sub(sw).mul(0.5); const gx = f.x.sub(sw); const side = select(gx.lessThan(half), float(0.0), float(1.0));
      const lx = select(side.lessThan(0.5), gx, bx.sub(sw).sub(gx)).toVar();
      const lotW = float(12.5).add(bh(21).mul(3.5)).toVar();
      const li = floor(f.y.sub(sw).div(lotW)).toVar(); const ly = f.y.sub(sw).sub(li.mul(lotW)).toVar();
      const lk = li.mul(2.0).add(side);
      const lh = (s) => H(bc.x.add(lk.mul(0.37)), bc.y.sub(lk.mul(0.61)), float(s));
      const hd = float(13.0).add(lh(1).mul(7.0)).toVar(), hw = lotW.sub(2.6).sub(lh(2).mul(1.5)).toVar();
      const setback = float(4.5).add(lh(3).mul(3.0)).toVar(); const r0 = lh(4);
      col.assign(mix(vec3(0.15, 0.18, 0.08), vec3(0.33, 0.29, 0.18), lh(5)));
      If(ly.greaterThan(lotW.sub(3.6)).and(ly.lessThan(lotW.sub(0.6))).and(lx.lessThan(setback.add(1.0))), () => { col.assign(vec3(0.42, 0.41, 0.39)); });
      const inHouse = lx.greaterThan(setback).and(lx.lessThan(setback.add(hd))).and(ly.greaterThan(1.2)).and(ly.lessThan(hw.add(1.2)));
      If(inHouse, () => {
        kind.assign(1.0); h.assign(float(5.0).add(lh(6).mul(3.5)));
        const ri = floor(r0.mul(7.99));
        const roofs = [[0.3, 0.29, 0.28], [0.46, 0.27, 0.19], [0.42, 0.41, 0.39], [0.2, 0.2, 0.21], [0.52, 0.33, 0.22], [0.36, 0.34, 0.31], [0.25, 0.24, 0.24], [0.55, 0.5, 0.44]];
        const rc = vec3(roofs[0][0], roofs[0][1], roofs[0][2]).toVar();
        for (let k = 1; k < 8; k++) If(ri.greaterThan(k - 0.5), () => { rc.assign(vec3(roofs[k][0], roofs[k][1], roofs[k][2])); });
        col.assign(rc);
        const uu = ly.sub(1.2).div(hw).sub(0.5); tilt.assign(select(uu.greaterThan(0.0), float(2.0), float(1.0)));
      }).Else(() => {
        If(lh(7).lessThan(0.1).and(lx.greaterThan(setback.add(hd).add(2.5))).and(lx.lessThan(setback.add(hd).add(7.0))).and(ly.greaterThan(3.5)).and(ly.lessThan(10.0)), () => { col.assign(vec3(0.12, 0.42, 0.5)); });
        const pl = vec2(lx, ly);
        for (let k = 0; k < 2; k++) {
          const tp = k === 0 ? vec2(setback.add(hd).add(3.0).add(lh(8).mul(12.0)), float(1.5).add(lotW.sub(3.0).mul(lh(9)))) : vec2(float(1.5).add(lh(30).mul(2.5)), float(2.0).add(lotW.sub(4.0).mul(lh(31))));
          const tr = float(2.4).add(lh(10 + k * 7).mul(2.8));
          If(lh(11 + k * 7).lessThan(0.8).and(length(pl.sub(tp)).lessThan(tr)), () => { kind.assign(2.0); h.assign(float(6.0).add(lh(12).mul(7.0))); col.assign(mix(vec3(0.07, 0.1, 0.045), vec3(0.15, 0.18, 0.08), lh(13 + k))); });
        }
      });
    });
    return vec4(col, kind.add(floor(h.mul(8.0)).mul(3.0)).add(tilt.mul(768.0)));
  }).setLayout({ name: 'urbanSample', type: 'vec4', inputs: [{ name: 'xz', type: 'vec2' }, { name: 'dens', type: 'float' }] });
}
const urbanKind = (c) => mod(c, 3.0);
const urbanH = (c) => floor(mod(c, 768.0).div(3.0)).div(8.0);
const urbanTilt = (c) => floor(c.div(768.0)); // 0 flat, 1 -0.5, 2 +0.5

// ---------------------------------------------------------------- bakes (world.js bakeGround)
export class GroundBakes {
  constructor(engine, world, sky, Q) {
    this.E = engine; this.W = world; this.sky = sky; this.Q = Q;
    const res = Q.aptRes || 0.8; this.aw = Math.round(APT_RECT.w / res); this.ah = Math.round(APT_RECT.h / res); this.res = res;
    const mk = (w, h, mips = true) => { const rt = new THREE.RenderTarget(w, h, { depthBuffer: false, generateMipmaps: mips, minFilter: mips ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter, magFilter: THREE.LinearFilter }); rt.texture.anisotropy = Q.aniso || 8; return rt; };
    this.apt = mk(this.aw, this.ah); this.aux = mk(Math.round(APT_RECT.w / 2), Math.round(APT_RECT.h / 2));
    this.city = mk(Q.cityRes, Q.cityRes); this.cityFar = mk(Q.cityRes, Q.cityRes);
    this.urban = makeUrban();
    // the airfield source maps are released by js/live/world.js releaseAirportMap right after the (synchronous) bake
    // call, while this bake runs at the next frame: take the three.js textures (which keep the pixel arrays) now
    const T = world.textures;
    this.src = { apt: textureOf(T.aptTex, { anisotropy: 1 }), paint: T.paintTex ? textureOf(T.paintTex) : null };
  }
  aptPoly() { const a = this.W.aptPoly; const P = []; for (let i = 0; i < a.length; i += 2) P.push([a[i], a[i + 1]]); return P; }
  aptMaterial() {
    const aptTex = this.src.apt, paintTex = this.src.paint;
    const A = [APT_RECT.s0, APT_RECT.t0, APT_RECT.w, APT_RECT.h]; const poly = this.aptPoly(); const fw = float(this.res);
    const m = bakeMat();
    m.colorNode = Fn(() => {
      const vu = uv(); const st = vec2(float(A[0]).add(vu.x.mul(A[2])), float(A[1]).add(float(1.0).sub(vu.y).mul(A[3]))).toVar();
      const apt = texture(aptTex, vu).toVar();
      const sdf = polySDF(st, poly);
      const g = grassCol(st, fw).mul(step(0.5, fract(st.x.div(24.0))).mul(0.06).add(0.94));
      const n1 = fbm2(st.mul(0.013), 3).toVar(), n2 = vnoise(st.mul(0.6)).toVar();
      const asph = vec3(0.13, 0.13, 0.135).mul(n1.mul(0.3).add(0.85)).mul(n2.mul(0.14).add(0.93)).toVar();
      const pc = floor(st.div(vec2(37.0, 23.0))); asph.mulAssign(select(hash12(pc.add(3.1)).lessThan(0.12), float(1.2), float(1.0)));
      const conc = vec3(0.38, 0.37, 0.345).mul(n1.mul(0.2).add(0.88)).toVar(); // weathered PCC ~0.3-0.4 (was 0.42: sunlit apron sat within ~25 sRGB levels of white paint)
      const slab = floor(st.div(7.62)); conc.mulAssign(hash12(slab.add(5.3)).mul(0.06).add(0.965));
      conc.mulAssign(fbm2(st.mul(0.004).add(7.0), 4).mul(0.3).add(0.85)); conc.mulAssign(float(1.0).sub(smoothstep(0.55, 0.8, fbm2(st.mul(0.03), 3)).mul(0.12)));
      const jf = abs(fract(st.div(7.62).add(0.5)).sub(0.5)).mul(7.62);
      const joint = float(1.0).sub(smoothstep(0.0, fw.mul(0.6), min(jf.x, jf.y))).mul(0.03).div(fw);
      conc.mulAssign(float(1.0).sub(clamp(joint, 0.0, 1.0).mul(0.25)));
      conc.mulAssign(float(1.0).sub(smoothstep(0.6, 0.9, vnoise(st.mul(0.15))).mul(vnoise(st.mul(1.3))).mul(0.18)));
      const pav = mix(asph, conc, apt.g).toVar();
      pav.mulAssign(float(1.0).sub(apt.b.mul(vnoise(st.mul(0.3)).mul(0.3).add(0.5))));
      If(apt.a.greaterThan(0.8), () => { pav.assign(mix(pav, vec3(0.17, 0.17, 0.18).mul(n1.mul(0.2).add(0.9)), 0.85)); })
        .ElseIf(apt.a.greaterThan(0.4), () => {
          const lot = vec3(0.19, 0.19, 0.2).mul(n1.mul(0.2).add(0.9)).toVar();
          const g2 = vec2(st.x.div(2.7), st.y.div(5.6)); const cf = fract(g2); const cc = floor(g2);
          const row = step(1.0, mod(cc.y, 3.0));
          lot.assign(mix(lot, vec3(0.75), row.mul(step(0.94, cf.x)).mul(0.7)));
          const occ = step(hash12(cc.add(17.0)), 0.7).mul(row);
          const car = occ.mul(step(0.14, cf.x)).mul(step(cf.x, 0.86)).mul(step(0.1, cf.y)).mul(step(cf.y, 0.9));
          const carCol = select(hash12(cc.add(19.0)).greaterThan(0.85), vec3(0.5, 0.07, 0.05), mix(vec3(0.82), vec3(0.07, 0.08, 0.1), hash12(cc.add(18.0))));
          pav.assign(mix(lot, carCol, car));
        });
      if (paintTex) { const gp = texture(paintTex, vu).r; const green = vec3(0.075, 0.2, 0.105).mul(n1.mul(0.2).add(0.9)).mul(n2.mul(0.1).add(0.95)); pav.assign(mix(pav, green, gp.mul(0.95))); }
      const col = mix(g, pav, apt.r);
      const cover = max(apt.r, smoothstep(-1.0, 1.0, sdf));
      return vec4(col, cover);
    })();
    return m;
  }
  auxMaterial() {
    const aptTex = this.src.apt; const A = [APT_RECT.s0, APT_RECT.t0, APT_RECT.w, APT_RECT.h]; const poly = this.aptPoly();
    const m = bakeMat();
    m.colorNode = Fn(() => {
      const vu = uv(); const st = vec2(float(A[0]).add(vu.x.mul(A[2])), float(A[1]).add(float(1.0).sub(vu.y).mul(A[3])));
      const sdf = polySDF(st, poly); const apt = texture(aptTex, vu);
      return vec4(clamp(sdf.negate().div(40.0), 0.0, 1.0), clamp(sdf.div(40.0).mul(0.5).add(0.5), 0.0, 1.0), apt.r.mul(apt.g).mul(float(1.0).sub(step(0.3, apt.a))), 1.0);
    })();
    return m;
  }
  cityMaterial(rect, far) {
    const regionTex = textureOf(this.W.textures.regionTex); const RR = this.W.groundU.uRegionRect; const sun = this.sky.u.sunDir; const texel = rect[2] / this.Q.cityRes;
    const urban = this.urban;
    const m = bakeMat();
    m.colorNode = Fn(() => {
      const xz = vec2(rect[0], rect[1]).add(uv().mul(vec2(rect[2], rect[3]))).toVar();
      const reg = texture(regionTex, xz.sub(vec2(RR[0], RR[1])).div(vec2(RR[2], RR[3])));
      const acc = vec3(0).toVar();
      const roofShade = (c, lo, hi) => { const t = urbanTilt(c); const tl = select(t.greaterThan(1.5), float(0.5), select(t.greaterThan(0.5), float(-0.5), float(0.0))); return Fn(() => {
        // zone orientation (same as inside urbanSample) for the roof normal
        const zc = floor(xz.div(1100.0).add(vec2(0.37, 0.61))); const ang = float(0.46).add(hash13(vec3(zc.x, zc.y, 3.0)).sub(0.5).mul(0.7));
        const nr = normalize(vec3(sin(ang).negate().mul(tl), 1.0, cos(ang).mul(tl)));
        return clamp(dot(nr, sun).div(max(sun.y, 0.2)), lo, hi);
      })(); };
      if (!far) {
        for (let k = 0; k < 4; k++) {
          const p = xz.add(vec2((k & 1) - 0.5, (k >> 1) - 0.5).mul(texel * 0.5));
          const u = urban(p, reg.g).toVar(); const kind = urbanKind(u.w);
          const s = float(1.0).toVar();
          If(kind.lessThan(0.5), () => {
            const sd = sun.xz.negate().div(max(sun.y, 0.15));
            const s1 = urban(p.sub(sd.mul(3.0)), reg.g), s2 = urban(p.sub(sd.mul(6.5)), reg.g);
            s.assign(float(1.0).sub(max(step(3.0, urbanH(s1.w)), step(6.5, urbanH(s2.w))).mul(0.75)));
          }).ElseIf(kind.lessThan(1.5), () => { s.assign(roofShade(u.w, 0.55, 1.25)); });
          acc.addAssign(u.xyz.mul(s));
        }
        return vec4(acc.div(4.0), 1.0);
      }
      for (let k = 0; k < 16; k++) {
        const p = xz.add(vec2((k & 3) + 0.5 - 2.0, (k >> 2) + 0.5 - 2.0).mul(texel * 0.25)).add(hash22(vec2(k, 1.0).add(xz)).sub(0.5).mul(texel * 0.25));
        const u = urban(p, reg.g).toVar(); const kind = urbanKind(u.w);
        const s = select(kind.greaterThan(1.5), float(0.8), select(kind.greaterThan(0.5), roofShade(u.w, 0.6, 1.2), float(0.85)));
        acc.addAssign(u.xyz.mul(s));
      }
      return vec4(acc.div(16.0), 1.0);
    })();
    return m;
  }
  // queue the bakes as tiles (first bake: everything; sun-only rebake: the two city targets, replacing any city tiles
  // still pending); step() renders a few tiles per frame
  enqueue({ sunOnly = false } = {}) {
    const Q = this.queue || (this.queue = []);
    const drop = (k) => { for (let i = Q.length - 1; i >= 0; i--) if (Q[i].kind === k) { const j = Q.splice(i, 1)[0]; if (j.last && j.job.mat) { j.job.mat.dispose(); j.job.mat = null; } } };
    if (!sunOnly) { this.tilesOf(this.apt, () => this.aptMaterial(), 'apt'); this.tilesOf(this.aux, () => this.auxMaterial(), 'aux'); }
    drop('city'); drop('cityFar');
    this.tilesOf(this.city, () => this.cityMaterial(CITY_RECT, false), 'city'); this.tilesOf(this.cityFar, () => this.cityMaterial(CITYFAR_RECT, true), 'cityFar');
  }
  tilesOf(rt, makeMat, kind, T = 1024) {
    const W = rt.width, H = rt.height; const nx = Math.ceil(W / T), ny = Math.ceil(H / T); const job = { makeMat, mat: null, rt };
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      this.queue.push({ kind, job, first: i === 0 && j === 0, last: i === nx - 1 && j === ny - 1, u0: i * T / W, u1: Math.min(1, (i + 1) * T / W), v0: j * T / H, v1: Math.min(1, (j + 1) * T / H) });
    }
  }
  get pending() { return this.queue ? this.queue.length : 0; }
  // render up to `budget` tiles; returns true once the queue is empty. Each tile is its own draw and submit.
  step(renderer, budget = 1) {
    const Q = this.queue; if (!Q || !Q.length) return true;
    if (!this.tileMesh) {
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(12), 3)); g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(8), 2)); g.setIndex([0, 1, 2, 0, 2, 3]);
      this.tileMesh = new THREE.Mesh(g); this.tileMesh.frustumCulled = false; this.tileCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1); // as THREE.QuadMesh
    }
    const prev = renderer.getRenderTarget(), ac = renderer.autoClear; renderer.autoClear = false;
    for (let n = 0; n < budget && Q.length; n++) {
      const t = Q.shift(); const J = t.job; const rt = J.rt; const tex = rt.texture;
      if (!J.mat) { J.mat = J.makeMat(); tex.generateMipmaps = true; renderer.initRenderTarget(rt); } // allocate with its mip chain
      tex.generateMipmaps = t.last; // mip chain once, after the last tile of the target
      // tile quad in NDC with the full-target uv (THREE.QuadMesh convention: v = 0 at the top, y = 1 - 2v)
      const x0 = t.u0 * 2 - 1, x1 = t.u1 * 2 - 1, yT = 1 - t.v0 * 2, yB = 1 - t.v1 * 2;
      const P = this.tileMesh.geometry.attributes.position, U = this.tileMesh.geometry.attributes.uv;
      P.array.set([x0, yT, 0, x0, yB, 0, x1, yB, 0, x1, yT, 0]); U.array.set([t.u0, t.v0, t.u0, t.v1, t.u1, t.v1, t.u1, t.v0]); P.needsUpdate = U.needsUpdate = true;
      this.tileMesh.material = J.mat; renderer.setRenderTarget(rt); renderer.render(this.tileMesh, this.tileCam);
      if (t.last) { J.mat.dispose(); J.mat = null; tex.generateMipmaps = true; if (t.kind === 'apt') this.aptDone = true; }
    }
    renderer.autoClear = ac; renderer.setRenderTarget(prev);
    // airfield source maps: one-time (released once the airfield and aux bakes are complete)
    if (this.src && this.aptDone && !Q.some(t => t.kind === 'apt' || t.kind === 'aux')) { for (const t of [this.src.apt, this.src.paint]) if (t) t.dispose(); this.src = null; }
    return Q.length === 0;
  }
}
// bake materials: no depth, NoBlending so the alpha written is kept (three forces alpha 1 for opaque NormalBlending)
function bakeMat() { const m = new THREE.NodeMaterial(); m.depthTest = m.depthWrite = false; m.blending = THREE.NoBlending; m.transparent = false; return m; }

// ---------------------------------------------------------------- runway markings (groundfuncs)
function makeGlyph(glyphTex) {
  // SDF glyph atlas (textures.js makeGlyphAtlas: 16 cells, 0.5 = edge, 64 atlas px per unit), fwidth AA
  return (code, gu) => {
    const t = vec2(code.add(gu.x).div(16.0), float(1.0).sub(gu.y));
    const d = texture(glyphTex, t).r.sub(0.5);
    const w = max(fwidth(d), 1e-3).mul(0.75);
    const inside = step(0.0, gu.x).mul(step(gu.x, 1.0)).mul(step(0.0, gu.y)).mul(step(gu.y, 1.0)).mul(step(code, 14.5));
    return smoothstep(w.negate(), w, d).mul(inside);
  };
}
// endMarkings(x, y, disp, codes, fw): x = distance from the pavement end inward, y lateral (pilot's right)
function endMarkings(x, y, disp, codes, fw, glyph) {
  const ay = abs(y).toVar(); const m = float(0).toVar(); const xt = x.sub(disp).toVar();
  // displaced threshold: bar, arrowhead row at +-25 / +-75 ft, centreline arrows every 55 m (HANDOFF §4, imagery-measured)
  If(disp.greaterThan(1.0).and(xt.lessThan(0.0)), () => {
    m.assign(max(m, band(xt, -3.05, 0.0, fw).mul(step(ay, 30.0))));
    const xa = xt.negate().sub(5.0);
    const hwa = xa.mul(2.3 / 12.0); const yy = min(abs(ay.sub(7.62)), abs(ay.sub(22.86)));
    m.assign(max(m, float(1.0).sub(smoothstep(hwa.sub(fw), hwa.add(fw), yy)).mul(step(0.0, xa)).mul(step(xa, 12.0))));
    const xr = xt.negate().sub(25.0);
    If(xr.greaterThan(0.0).and(x.greaterThan(20.0)), () => {
      const k = floor(xr.div(55.0)); const xl = xr.sub(k.mul(55.0));
      If(x.sub(float(27.0).sub(xl)).greaterThan(12.0).or(k.lessThan(0.5)), () => {
        const hwc = xl.mul(2.3 / 12.0);
        const head = float(1.0).sub(smoothstep(hwc.sub(fw), hwc.add(fw), ay)).mul(step(xl, 12.0));
        const shaft = band(ay, -1.0, 0.45, fw).mul(band(xl, 12.0, 27.0, fw)).mul(step(12.0, xl));
        m.assign(max(m, max(head, shaft)));
      });
    });
  });
  // threshold stripes (AC 150/5340-1M 2.5.5): 16 x 5.75 ft, double centre gap
  const k8 = floor(ay.sub(1.75).div(3.5)); const f8 = ay.sub(1.75).sub(k8.mul(3.5));
  m.assign(max(m, band(f8, 0.0, 1.75, fw).mul(band(xt, 6.1, 51.8, fw)).mul(step(0.0, k8)).mul(step(k8, 7.5))));
  // designation: letter then digits
  const l = floor(codes.div(256.0)), d1 = floor(mod(codes, 256.0).div(16.0)), d2 = mod(codes, 16.0);
  const inDes = step(60.0, xt).mul(step(xt, 118.0));
  const gy = xt.sub(94.5).div(18.3);
  const gl = glyph(l, vec2(y.add(3.6).div(7.2), xt.sub(64.0).div(18.3)));
  const single = step(14.5, d2);
  const g1 = glyph(d1, vec2(mix(y.add(8.8), y.add(3.6), single).div(7.2), gy));
  const g2 = glyph(d2, vec2(y.sub(1.6).div(7.2), gy)).mul(float(1.0).sub(single));
  m.assign(max(m, max(gl, max(g1, g2)).mul(inDes)));
  // aiming point (2.6) and touchdown zone bars
  m.assign(max(m, band(xt, 310.9, 356.6, fw).mul(band(ay, 11.0, 20.1, fw))));
  const tdz = [[152.4, 3], [457.2, 2], [609.6, 2], [762.0, 1], [914.4, 1]];
  const ft = ay.sub(10.7); const kt = floor(ft.div(3.35)); const fft = ft.sub(kt.mul(3.35));
  for (const [x0, nb] of tdz) m.assign(max(m, band(fft, 0.0, 1.83, fw).mul(band(xt, x0, x0 + 22.9, fw)).mul(step(0.0, kt)).mul(step(kt, nb - 0.5))));
  return m;
}
// runwayAt: returns {m, rub, flag, local}; runway data are constants read from world.groundU (uRw, uRwInfo, uRwEnd)
function runwayAt(st, fw, G, glyph) {
  const rw = G.uRw, info = G.uRwInfo, ends = G.uRwEnd;
  const found = float(0).toVar(); const flag = float(0).toVar(); const m = float(0).toVar(); const rub = float(0).toVar(); const local = vec2(0).toVar();
  const ex = float(0).toVar(), ey = float(0).toVar(), edisp = float(0).toVar(), ecode = float(0).toVar(), x0v = float(0).toVar(), x1v = float(0).toVar(), dvv = float(0).toVar(), d0v = float(0).toVar(), d1v = float(0).toVar();
  for (let i = 0; i < rw.length / 4; i++) {
    const axis = rw[i * 4], c = rw[i * 4 + 1], a0 = rw[i * 4 + 2], a1 = rw[i * 4 + 3];
    const disp0 = info[i * 4], disp1 = info[i * 4 + 1], code0 = info[i * 4 + 2], code1 = info[i * 4 + 3];
    const eA = ends ? ends[i * 4] : 0, lA = ends ? ends[i * 4 + 1] : 0, eB = ends ? ends[i * 4 + 2] : 0, lB = ends ? ends[i * 4 + 3] : 0;
    const u = axis < 0.5 ? st.x : st.y, v = axis < 0.5 ? st.y : st.x;
    const dv = v.sub(c); const inW = abs(dv).lessThan(30.48);
    let padCond = null;
    if (eA > 0.5) padCond = u.lessThanEqual(a0).and(u.greaterThan(a0 - lA));
    if (eB > 0.5) { const cB = u.greaterThanEqual(a1).and(u.lessThan(a1 + lB)); padCond = padCond ? padCond.or(cB) : cB; }
    if (padCond) If(found.lessThan(0.5).and(inW).and(padCond), () => {
      found.assign(1.0);
      const atA = u.lessThanEqual(a0); const xb = select(atA, float(a0).sub(u), u.sub(a1)); const typ = select(atA, float(eA), float(eB));
      const q = xb.sub(abs(dv)).sub(15.0); const k = floor(q.div(29.7).add(0.5)); const f = q.sub(k.mul(29.7));
      const chev = float(1.0).sub(smoothstep(float(0.64).sub(fw), float(0.64).add(fw), abs(f))).mul(step(0.0, k));
      const mm = max(chev, band(xb, 0.0, 0.91, fw)).mul(band(abs(dv), -1.0, 29.9, fw));
      m.assign(select(typ.lessThan(1.5), mm, float(0.0))); flag.assign(select(typ.lessThan(1.5), float(2.0), float(3.0))); local.assign(vec2(u, dv));
    });
    If(found.lessThan(0.5).and(inW).and(u.greaterThan(a0)).and(u.lessThan(a1)), () => {
      found.assign(1.0); flag.assign(1.0);
      const x0 = u.sub(a0), x1 = float(a1).sub(u); const y0 = axis < 0.5 ? dv.negate() : dv;
      const first = x0.lessThan((a1 - a0) * 0.5);
      ex.assign(select(first, x0, x1)); ey.assign(select(first, y0, y0.negate())); edisp.assign(select(first, float(disp0), float(disp1))); ecode.assign(select(first, float(code0), float(code1)));
      x0v.assign(x0); x1v.assign(x1); dvv.assign(dv); d0v.assign(disp0); d1v.assign(disp1); local.assign(vec2(u, dv));
      // rubber in the touchdown zones (landing ends: the 28s land on the x1 side)
      const xl = i < 2 ? x1.sub(disp1) : x0.sub(disp0);
      rub.assign(smoothstep(80.0, 250.0, xl).mul(float(1.0).sub(smoothstep(700.0, 1300.0, xl))).mul(float(1.0).sub(smoothstep(6.0, 14.0, abs(dv)))).mul(vnoise(vec2(u.mul(0.05), dv.mul(1.3))).mul(0.4).add(0.6)));
    });
  }
  If(flag.greaterThan(0.5).and(flag.lessThan(1.5)), () => {
    const mk = endMarkings(ex, ey, edisp, ecode, fw, glyph).toVar();
    // centreline: 120 ft stripes, 80 ft gaps from 120 m past the threshold (existing renderer values)
    const xc = x0v.sub(120.0).sub(d0v);
    const onC = step(d0v.add(120.0), x0v).mul(step(d1v.add(120.0), x1v));
    mk.assign(max(mk, band(abs(dvv), -1.0, 0.45, fw).mul(band(fract(xc.div(60.96)).mul(60.96), 0.0, 36.58, fw)).mul(onC)));
    mk.assign(max(mk, band(abs(dvv), 29.27, 30.18, fw)));
    m.assign(mk);
  });
  return { m, rub, flag, local };
}

// night lighting of the city (street lights). The apron floodlights are NOT here: they are a light
// (js/three/flood.js) that lights the ground, paint, buildings and aircraft alike (review round 1).
// Lamps on a jittered 34 m grid (72 % of the cells), sodium orange or LED white (inferred mix). Per lamp:
//   - the pool of light it throws on the ground: ~15 lux at the centre (0.47 units; 20 lux = 0.62 units,
//     js/three/flood.js E_STAND), Gaussian radius 12 m, over a general street level of ~4 lux (0.12 units);
//   - the lamp itself seen from above: radius 0.8 m, peak radiance 20 units; far away the spot is widened to stay
//     >= ~1.2 px with its peak scaled down so its energy is constant, and it becomes the cell average once the pixel
//     footprint approaches the lamp spacing (review round 1: the old widening grew the average with the footprint^2,
//     which made the far city a pure-white band on the horizon).
// Far-field average: ~0.03-0.04 units of emission (a warm glow, not a white band).
function cityNight(xz, fw, urb, albedo) {
  const S = 34.0; const g = xz.div(S); const c = floor(g); const f = fract(g).sub(0.5);
  const h = hash12(c.mul(1.37).add(11.0)); const off = vec2(hash12(c.add(3.1)), hash12(c.add(7.7))).sub(0.5).mul(0.7);
  const d = length(f.sub(off)).mul(S); const on = step(0.28, h);
  const lc = mix(vec3(1.0, 0.6, 0.3), vec3(0.95, 0.92, 0.88), step(0.72, h));
  const poolE = mix(exp(d.mul(d).div(-144.0)).mul(0.47).mul(on), float(0.47 * Math.PI * 144.0 / (34.0 * 34.0) * 0.72), smoothstep(6.0, 18.0, fw)).add(0.12);
  const r0 = 0.8; const r = max(float(r0), fw.mul(1.2)); const peak = float(20.0 * r0 * r0).div(r.mul(r));
  const spot = exp(d.mul(d).negate().div(r.mul(r))).mul(peak).mul(on);
  const lum = mix(spot, float(20.0 * Math.PI * r0 * r0 / (34.0 * 34.0) * 0.72), smoothstep(34.0 * 0.3, 34.0 * 0.8, fw));
  return albedo.mul(lc).mul(poolE.mul(1.0 / Math.PI)).add(lc.mul(lum)).mul(urb);
}

// ---------------------------------------------------------------- ground material (GROUND_FS)
export function groundMaterial(world, bakes, sky, Q) {
  const G = world.groundU; const T = world.textures;
  const regionTex = textureOf(T.regionTex, { anisotropy: 8 }); const noiseTex = textureOf(T.noise, { anisotropy: Q.aniso }); const glyphTex = textureOf(T.glyphs);
  const RR = G.uRegionRect, AR = G.uAptRect, Vw = G.uVw, Uw = G.uUw, CR = CITY_RECT, CFR = CITYFAR_RECT;
  const aptAlb = bakes.apt.texture, aptAux = bakes.aux.texture, city = bakes.city.texture, cityFar = bakes.cityFar.texture;
  const glyph = makeGlyph(glyphTex);
  const night = sky.u.night;
  const mat = new THREE.MeshStandardNodeMaterial({ metalness: 0 });
  // one evaluation shared by the colour, roughness and emissive slots (TSL Fn.once())
  const core = Fn(() => {
    const wp = positionWorld; const dist = length(cameraPosition.sub(wp)).toVar();
    const N = normalize(normalWorld).toVar();
    const st = vec2(dot(wp.xz, vec2(Vw[0], Vw[1])), dot(wp.xz, vec2(Uw[0], Uw[1]))).toVar();
    const fw = length(fwidth(wp.xz)).mul(0.7).add(0.001).toVar();
    const reg = texture(regionTex, wp.xz.sub(vec2(RR[0], RR[1])).div(vec2(RR[2], RR[3]))).toVar();
    const nzA = texture(noiseTex, wp.xz.mul(1 / 2300)).toVar(), nzB = texture(noiseTex, wp.xz.mul(1 / 170)).toVar();
    const h = wp.y;
    const hillDry = mix(vec3(0.46, 0.38, 0.24), vec3(0.36, 0.29, 0.18), nzA.g); const scrub = vec3(0.11, 0.135, 0.07);
    const slope = float(1.0).sub(N.y), north = N.z.negate();
    const forest = smoothstep(0.35, 0.65, clamp(reg.b.add(nzA.b.sub(0.5).mul(1.2)).add(north.mul(0.9)).add(slope.mul(0.8)).sub(0.25), 0.0, 1.0)).mul(smoothstep(8.0, 60.0, h));
    const albedo = mix(hillDry, scrub, forest).mul(nzB.r.mul(0.3).add(0.85)).toVar();
    const shore = float(1.0).sub(smoothstep(0.4, 2.2, h)).toVar();
    albedo.assign(mix(albedo, vec3(0.19, 0.17, 0.13), shore));
    const auv = vec2(st.x.sub(AR[0]).div(AR[2]), float(1.0).sub(st.y.sub(AR[1]).div(AR[3]))).toVar();
    const inApt = step(0.0, auv.x).mul(step(auv.x, 1.0)).mul(step(0.0, auv.y)).mul(step(auv.y, 1.0)).toVar();
    const aptA = texture(aptAlb, auv).mul(inApt).toVar();
    const aux = texture(aptAux, auv).toVar();
    // urban
    const urb = reg.g.mul(float(1.0).sub(smoothstep(110.0, 180.0, h.add(nzA.r.mul(60.0))))).mul(float(1.0).sub(shore)).mul(float(1.0).sub(aptA.a)).toVar();
    const cuv = wp.xz.sub(vec2(CR[0], CR[1])).div(vec2(CR[2], CR[3])); const fuv = wp.xz.sub(vec2(CFR[0], CFR[1])).div(vec2(CFR[2], CFR[3]));
    const cNear = texture(city, cuv).rgb, cFar = texture(cityFar, fuv).rgb;
    const farProc = vec3(0.2, 0.19, 0.175).mul(nzB.g.mul(0.5).add(0.75)).mul(nzA.a.mul(0.3).add(0.85));
    const inF = step(0.0, fuv.x).mul(step(fuv.x, 1.0)).mul(step(0.0, fuv.y)).mul(step(fuv.y, 1.0));
    const inC = step(0.0, cuv.x).mul(step(cuv.x, 1.0)).mul(step(0.0, cuv.y)).mul(step(cuv.y, 1.0));
    const farC = mix(farProc, cFar, inF);
    const e = min(min(cuv.x, cuv.y), min(float(1.0).sub(cuv.x), float(1.0).sub(cuv.y)));
    const cc = mix(farC, cNear, inC.mul(smoothstep(0.0, 0.04, e)));
    albedo.assign(mix(albedo, cc, urb));
    albedo.assign(mix(albedo, vec3(0.17, 0.17, 0.18), reg.a.mul(float(1.0).sub(aptA.a)).mul(0.9)));
    const rough = float(0.95).toVar();
    // airfield
    albedo.assign(mix(albedo, aptA.rgb, aptA.a));
    const rip = float(1.0).sub(smoothstep(1.6, 2.7, h)).mul(smoothstep(-3.0, -1.0, h)).mul(aptA.a);
    const rk = texture(noiseTex, st.mul(0.35)).r.mul(0.6).add(texture(noiseTex, st.mul(1.1)).g.mul(0.4));
    albedo.assign(mix(albedo, vec3(0.3, 0.28, 0.26).mul(rk.mul(0.8).add(0.5)), rip));
    const R = runwayAt(st, fw, G, glyph);
    const n1 = texture(noiseTex, R.local.mul(vec2(0.0012, 0.02))).b, n2 = texture(noiseTex, R.local.mul(vec2(0.02, 0.5))).r;
    If(R.flag.greaterThan(1.5).and(inApt.greaterThan(0.5)), () => {
      const asph = vec3(0.105, 0.108, 0.118).mul(n1.mul(0.4).add(0.8)).mul(n2.mul(0.12).add(0.94));
      const yel = vec3(0.62, 0.42, 0.06).mul(n2.mul(0.15).add(0.85));
      albedo.assign(mix(asph, yel, R.m)); rough.assign(mix(0.85, 0.65, R.m));
    }).ElseIf(R.flag.greaterThan(0.5).and(inApt.greaterThan(0.5)), () => {
      const asph = vec3(0.12, 0.12, 0.125).mul(n1.mul(0.4).add(0.8)).mul(n2.mul(0.12).add(0.94)).toVar();
      asph.mulAssign(smoothstep(8.0, 20.0, abs(R.local.y)).mul(0.08).add(0.95));
      asph.mulAssign(float(1.0).sub(R.rub.mul(0.62)));
      const paint = mix(vec3(0.74, 0.74, 0.72).mul(n2.mul(0.12).add(0.88)), asph, R.rub.mul(0.7));
      albedo.assign(mix(asph, paint, R.m)); rough.assign(mix(0.8, 0.6, R.m));
    });
    // concrete joints close up (area-correct fade)
    const concMask = aux.b.mul(inApt).toVar();
    const jf = abs(fract(st.div(7.62).add(0.5)).sub(0.5)).mul(7.62); const jw = max(fw, 0.005);
    const joint = float(1.0).sub(smoothstep(0.012, jw.add(0.012), min(jf.x, jf.y))).mul(min(1.0, float(0.025).div(jw)));
    const jOn = step(dist, 350.0).mul(step(0.5, concMask)).mul(step(R.flag, 0.5));
    albedo.mulAssign(float(1.0).sub(joint.mul(0.3).mul(float(1.0).sub(smoothstep(60.0, 220.0, dist))).mul(jOn)));
    const dd = texture(noiseTex, wp.xz.mul(0.9)).a.mul(0.6).add(texture(noiseTex, wp.xz.mul(3.7)).r.mul(0.4));
    albedo.mulAssign(mix(float(1.0), dd.mul(0.3).add(0.85), float(1.0).sub(smoothstep(100.0, 400.0, dist))));
    return vec4(albedo, rough);
  }).once();
  // night light (emissive): street lights in the city (the apron floodlights are a light: js/three/flood.js)
  const emis = Fn(() => {
    const c = core(); const wp = positionWorld; const h = wp.y;
    const st = vec2(dot(wp.xz, vec2(Vw[0], Vw[1])), dot(wp.xz, vec2(Uw[0], Uw[1])));
    const fw = length(fwidth(wp.xz)).mul(0.7).add(0.001);
    const reg = texture(regionTex, wp.xz.sub(vec2(RR[0], RR[1])).div(vec2(RR[2], RR[3])));
    const nzA = texture(noiseTex, wp.xz.mul(1 / 2300));
    const shore = float(1.0).sub(smoothstep(0.4, 2.2, h));
    const auv = vec2(st.x.sub(AR[0]).div(AR[2]), float(1.0).sub(st.y.sub(AR[1]).div(AR[3])));
    const inApt = step(0.0, auv.x).mul(step(auv.x, 1.0)).mul(step(0.0, auv.y)).mul(step(auv.y, 1.0));
    const aptA = texture(aptAlb, auv).a.mul(inApt);
    const urbN = reg.g.mul(float(1.0).sub(smoothstep(110.0, 180.0, h.add(nzA.r.mul(60.0))))).mul(float(1.0).sub(shore)).mul(float(1.0).sub(aptA));
    return cityNight(wp.xz, fw, urbN, c.xyz).mul(night);
  }).once();
  mat.colorNode = vec4(core().xyz, 1.0);
  mat.roughnessNode = core().w;
  mat.emissiveNode = emis();
  return mat;
}

// ---------------------------------------------------------------- water (WATER_FS)
export function waterMaterial(world, bakes, sky) {
  const T = world.textures; const W = world.waterU; const G = world.groundU;
  const waves = textureOf(T.waves); waves.wrapS = waves.wrapT = THREE.RepeatWrapping; const noiseTex = textureOf(T.noise);
  const aux = bakes.aux.texture; const AR = G.uAptRect, Vw = G.uVw, Uw = G.uUw; const U = sky.u;
  const uWind = uniform(new THREE.Vector2(3, -1)), uAmp = uniform(1.0);
  const mat = new THREE.MeshPhysicalNodeMaterial({ metalness: 0, ior: 1.333 });
  const slope = (p) => texture(waves, p).rg;
  // wind: js/live/app.js sets uWaveAmp = 0.45 + knots / 22 (12 kt -> 1.0) and uWind (m/s, downwind). The slope gain and
  // the roughness follow it (review round 1: 12 kt left a mirror-calm bay). Near roughness 0.03 (calm) .. 0.1 (12 kt);
  // far (unresolved waves, Cox-Munk: slope variance 0.003 + 0.00512 U, U in m/s) 0.2 .. 0.36.
  const windK = clamp(uAmp.sub(0.45).div(0.85), 0.0, 1.5);
  const wcore = Fn(() => {
    const wp = positionWorld;
    const ws = length(uWind); const wd = select(ws.greaterThan(0.01), uWind.div(max(ws, 1e-4)), vec2(1, 0));
    const t = U.time; const p = wp.xz;
    const r1 = (v) => vec2(v.x.mul(0.8).sub(v.y.mul(0.6)), v.x.mul(0.6).add(v.y.mul(0.8)));
    const r2 = (v) => vec2(v.x.mul(0.28).add(v.y.mul(0.96)), v.x.mul(-0.96).add(v.y.mul(0.28)));
    const s = slope(p.div(61.0).sub(wd.mul(t).mul(0.028))).mul(0.9).toVar();
    s.addAssign(slope(r1(p).div(23.0).sub(wd.mul(t).mul(0.052))).mul(0.7));
    s.addAssign(slope(r2(p).div(9.1).sub(r2(wd).mul(t).mul(0.07))).mul(0.5));
    s.addAssign(slope(r1(r2(p)).div(3.7).sub(wd.mul(t).mul(0.11))).mul(0.35));
    const fw = length(fwidth(wp.xz));
    s.mulAssign(uAmp.mul(1.5).div(fw.mul(0.05).add(1.0)));
    return normalize(vec3(s.x.negate(), 1.0, s.y.negate()));
  }).once();
  // foam at the seawall (aux.r = distance into the water / 40 m) and distance roughening
  const wfoam = Fn(() => {
    const wp = positionWorld; const p = wp.xz; const t = U.time;
    const st = vec2(dot(p, vec2(Vw[0], Vw[1])), dot(p, vec2(Uw[0], Uw[1])));
    const auv = vec2(st.x.sub(AR[0]).div(AR[2]), float(1.0).sub(st.y.sub(AR[1]).div(AR[3])));
    const inA = step(0.0, auv.x).mul(step(auv.x, 1.0)).mul(step(0.0, auv.y)).mul(step(auv.y, 1.0));
    const dA = mix(float(100.0), texture(aux, auv).r.mul(40.0), inA);
    const fn = texture(noiseTex, st.mul(0.02).add(vec2(t.mul(0.004), 0.0))), fn2 = texture(noiseTex, st.mul(0.09).sub(vec2(0.0, t.mul(0.01))));
    return float(1.0).sub(smoothstep(0.0, fn.r.mul(4.0).add(3.0), dA)).mul(smoothstep(0.35, 0.75, fn2.g)).mul(step(dA, 8.0));
  }).once();
  const wrough = Fn(() => {
    const dist = length(cameraPosition.sub(positionWorld));
    const r = mix(windK.mul(0.07).add(0.03), windK.mul(0.16).add(0.2), smoothstep(30.0, 3000.0, dist));
    return mix(r, float(0.9), wfoam().mul(0.6));
  }).once();
  mat.normalNode = toView(wcore());
  mat.colorNode = vec4(mix(vec3(0.045, 0.075, 0.07), vec3(0.6, 0.62, 0.62), wfoam().mul(0.6)), 1.0);
  mat.roughnessNode = wrough();
  // environment = the visible sky along the reflected ray from this water point (sharp; blurred towards the
  // precomputed sky + average cloud colour as the roughness grows). Also used as the (tiny) diffuse IBL term.
  mat.envNode = Fn(() => {
    const wp = positionWorld; const V = normalize(wp.sub(cameraPosition));
    const Rr = reflect(V, wcore()).toVar(); Rr.y.assign(abs(Rr.y).max(0.003));
    const sharp = sky.skyAlong(wp, Rr);
    const cl = U.sunColor.mul(0.2).add(U.skyUp.mul(0.55)).add(U.skyHorizon.mul(0.15));
    const blur = mix(sky.skyEnvBlur(Rr), cl, U.cloud.x.mul(0.8));
    return mix(sharp, blur, smoothstep(0.08, 0.45, wrough()));
  })();
  mat.userData.uWind = uWind; mat.userData.uAmp = uAmp;
  return mat;
}

// build the ground/water scene objects from the world items (prog 'ground' | 'water')
export function buildGroundObjects(world, gMat, wMat) {
  const group = new THREE.Group(); group.name = 'ground';
  for (const it of world.items) {
    if (it.prog === 'ground') { const m = new THREE.Mesh(geometryOf(it.mesh), gMat); m.receiveShadow = true; m.castShadow = false; m.matrixAutoUpdate = false; group.add(m); }
    else if (it.prog === 'water') { const m = new THREE.Mesh(geometryOf(it.mesh), wMat); m.receiveShadow = true; m.frustumCulled = false; m.matrixAutoUpdate = false; m.renderOrder = -1; group.add(m); }
  }
  return group;
}

// Aircraft for the three.js renderer. The aircraft objects themselves are js/live/aircraft.js LiveAircraft instances
// (pose, gear/flaps state, lights, livery, LOD distances, model placement, light anchors from the model geometry),
// created and updated by the app exactly as in js/live/app.js. This module only draws them:
//   - imported models (.sfom via js/live/models.js getModel/decodeModel): TSL port of js/shaders/aircraft_real.js
//     ACR_FS: livery colours applied by paint zone on the neutralised texture (fin, engines, fuselage top/belly/
//     stripe), glass (kind 1) as a smooth dark dielectric with a clear-coat reflection layer and warm cabin light at
//     night, bare metal (kind 2), dark (3), light lenses (4); clear-coat on paint (the old shader's hand-made clear
//     coat), gear collapse when retracted (zones 3, 4), selection rim
//   - brand x model livery textures (data/liveries/, chosen by js/aircraft/liveries.js and loaded by LiveAircraft
//     itself: ac.livTex): replace the model's livery atlas (texture 0) and skip the zone recolouring; the atlas alpha
//     (< 0.5) marks cabin windows painted into the atlas (uAtlas in ACR_FS), drawn as glass; neutral skins
//     (ac._livNeutral) keep the zone recolouring; freighter brands (brandIsCargo) get painted-over window plugs
//   - procedural airframes (types without an imported model, and every aircraft beyond the LOD distance): TSL port of
//     js/shaders/aircraft.js AC_FS: livery, passenger windows (2 rows, shades), door outlines, flight-deck panes
//     (sdPoly5 on the unwrapped surface), fin / engine / wing parts; gear, flaps and spoilers as in fleet.js items()
// Per-aircraft values (livery, dims, windows, panes) are per-object uniforms (onObjectUpdate) so every aircraft of a
// model shares one material and one GPU program.
import { THREE, TSL } from './lib.js';
import { m4 } from '../math.js';
import { linearLivery, rotAxisAbout } from '../aircraft/fleet.js';
import { brandIsCargo } from '../aircraft/liveries.js';
import { geometryOf, textureOf } from './convert.js';
import { hash12, hash13, facingNormalView } from './tsl/common.js';
const { Fn, uniform, attribute, vec2, vec3, vec4, float, texture, dot, abs, max, min, mix, smoothstep, step, clamp, normalize, length, floor, fract, mod, select, If, Discard, fwidth, positionWorld, cameraPosition, normalWorld, pow, sign, sqrt, atan, Loop } = TSL;

const V3 = () => new THREE.Vector3(), V4 = () => new THREE.Vector4();
// per-object uniform: value read from object.userData.acU[key] every time the object is drawn
const ou = (key, init) => uniform(init).onObjectUpdate(({ object }) => { const U = object.userData.acU; return U ? U[key] : init; });

// ---------------------------------------------------------------- imported models (ACR_FS)
function realMaterial(tex, liveryTex, atlas = false) {
  const m = new THREE.MeshPhysicalNodeMaterial({ side: THREE.DoubleSide, clearcoat: 1 });
  const uTop = ou('top', V3()), uBelly = ou('belly', V3()), uTail = ou('tail', V3()), uEng = ou('eng', V3()), uStripe = ou('stripe', V4());
  const uBellyLine = ou('bellyLine', 0), uDirt = ou('dirt', 0.3), uFus = ou('fus', V4()), uFusB = ou('fusB', V4()), uLights = ou('lights', 0), uGearUp = ou('gearUp', 0), uSel = ou('sel', 0), uNoCabin = ou('noCabin', 0);
  const col = attribute('color', 'vec4'), ext = attribute('extra', 'vec4'), LP = attribute('position', 'vec3');
  const zone = floor(ext.x.add(0.5));
  // retracted gear and open gear doors collapse away (ACR_VS)
  m.positionNode = select(uGearUp.greaterThan(0.5).and(zone.equal(3).or(zone.equal(4))), vec3(0), LP);
  let R = null;
  const core = () => {
    const kc = ext.y; const alphaTest = kc.greaterThan(7.5); const kind = floor(mod(kc, 8.0).add(0.5)).toVar();
    const tx = tex ? texture(tex, TSL.uv()) : vec4(1); if (tex) If(alphaTest.and(tx.a.lessThan(0.5)), () => { Discard(); });
    const mcol = col.rgb, texWhite = col.a;
    const albedo = mcol.mul(tx.rgb).toVar(); const rough = ext.z.toVar(), metal = ext.w.toVar(); const emis = vec3(0).toVar(); const cc = float(0).toVar(); const ccr = float(0.09).toVar();
    // freighter (ACR_FS uNoCabin): cabin glass aft of the flight deck is a painted-over window plug in the top colour
    const plug = kind.equal(1).and(uNoCabin.greaterThan(0.5)).and(LP.x.lessThan(uFusB.z.negate()));
    If(plug, () => { albedo.assign(uTop); rough.assign(0.4); cc.assign(1.0); })
    .ElseIf(kind.equal(1), () => { // glass: dark, smooth reflective layer; warm cabin light behind passenger windows at night
      albedo.assign(vec3(0.012, 0.013, 0.015)); rough.assign(0.4); cc.assign(1.0); ccr.assign(0.02);
      const cockpit = LP.x.greaterThan(uFusB.z.negate());
      const h = hash12(floor(vec2(LP.x.mul(2.0), sign(LP.z))).add(13.0));
      emis.assign(select(cockpit, vec3(0.02, 0.03, 0.05), vec3(1.0, 0.78, 0.5).mul(h.mul(0.45).add(0.55)).mul(step(0.08, h))).mul(uFusB.w));
    }).ElseIf(kind.equal(0), () => {
      if (liveryTex) { albedo.assign(tx.rgb); cc.assign(1.0); }
      else {
        const lumL = dot(tx.rgb, vec3(0.2126, 0.7152, 0.0722));
        const sh = tex ? clamp(lumL.div(pow(max(texWhite, 0.2), 2.2)), 0.0, 1.1) : float(1.0);
        const whiteish = sh.greaterThan(0.5).and(dot(mcol, vec3(0.333)).greaterThan(0.4));
        const shT = mix(float(1.0), sh, 0.5);
        const finPx = LP.y.greaterThan(uFusB.x.add(0.06)).and(abs(LP.z).lessThan(1.2)).and(LP.x.lessThan(uFus.z.mul(0.5)));
        const e = length(vec2(LP.y.div(uFus.x.mul(1.12)), LP.z.div(uFus.y.mul(1.12))));
        const px = fwidth(LP.y).add(1e-3);
        const belly = float(1.0).sub(smoothstep(uBellyLine.sub(px), uBellyLine.add(px), LP.y));
        const c = mix(uTop, uBelly, belly).toVar();
        const sy = uBellyLine.add(uFus.x.mul(0.25));
        c.assign(mix(c, uStripe.rgb, smoothstep(sy.sub(0.09).sub(px), sy.sub(0.09).add(px), LP.y).sub(smoothstep(sy.add(0.09).sub(px), sy.add(0.09).add(px), LP.y)).mul(step(0.5, uStripe.w))));
        If(finPx.and(whiteish).and(zone.notEqual(2)).and(zone.notEqual(7)), () => { albedo.assign(uTail.mul(shT)); })
          .ElseIf(zone.equal(2).and(whiteish), () => { albedo.assign(uEng.mul(shT)); })
          .ElseIf(zone.equal(0).and(whiteish), () => { albedo.assign(select(e.lessThan(1.0).and(LP.x.greaterThan(uFus.z.add(0.5))), c.mul(sh), vec3(0.9).mul(sh))); })
          .ElseIf(whiteish, () => { albedo.assign(vec3(0.9).mul(sh)); });
        cc.assign(1.0);
      }
      albedo.mulAssign(float(1.0).sub(uDirt.mul(0.18).mul(smoothstep(-0.3, -0.9, LP.y.div(max(uFus.x, 0.5))))));
    }).ElseIf(kind.equal(2), () => { rough.assign(0.28); metal.assign(0.9); albedo.assign(max(albedo, vec3(0.55))); })
      .ElseIf(kind.equal(3), () => { rough.assign(0.7); })
      .ElseIf(kind.equal(4), () => { emis.assign(albedo.mul(uFusB.w.mul(40.0).add(0.6)).mul(uLights)); });
    // painted cabin windows of the livery atlas (ACR_FS winA): smooth glass over a dark cabin, warm light at night
    if (atlas && tex) {
      const winA = select(kind.equal(0), float(1.0).sub(smoothstep(0.35, 0.6, tx.a)), float(0.0));
      const h = hash12(floor(vec2(LP.x.mul(2.0), sign(LP.z))).add(13.0));
      albedo.assign(mix(albedo, vec3(0.012, 0.013, 0.015), winA)); rough.assign(mix(rough, 0.4, winA)); ccr.assign(mix(ccr, 0.02, winA));
      emis.addAssign(vec3(1.0, 0.78, 0.5).mul(h.mul(0.45).add(0.55)).mul(step(0.08, h)).mul(uFusB.w).mul(winA));
    }
    // selection rim (ACR_FS uSel)
    const V = normalize(cameraPosition.sub(positionWorld)); const N = normalize(normalWorld);
    emis.addAssign(vec3(1.0, 0.72, 0.2).mul(uSel).mul(0.35).mul(pow(float(1.0).sub(max(dot(N, V), 0.0)), 3.0)));
    const ao = mix(float(0.72), float(1.0), smoothstep(-0.7, 0.3, N.y));
    return { albedo, rough, metal, emis, cc, ccr, ao };
  };
  const A = Fn(() => { R = core(); return vec4(R.albedo, R.rough); }).once();
  const B = Fn(() => { A(); return vec4(R.emis, R.metal); }).once();
  const C = Fn(() => { A(); return vec4(R.cc, R.ccr, R.ao, 0); }).once();
  m.colorNode = vec4(A().xyz, 1.0); m.roughnessNode = A().w; m.metalnessNode = B().w; m.emissiveNode = B().xyz;
  m.clearcoatNode = C().x; m.clearcoatRoughnessNode = C().y; m.aoNode = C().z;
  m.normalNode = facingNormalView(); m.clearcoatNormalNode = facingNormalView();
  return m;
}

// ---------------------------------------------------------------- procedural airframes (AC_FS)
const sdBox = (p, c, hs, r) => { const d = abs(p.sub(c)).sub(hs).add(r); return length(max(d, 0.0)).add(min(max(d.x, d.y), 0.0)).sub(r); };
// signed distance to a 5-gon (AC_FS sdPoly5)
const sdPoly5 = Fn(([p, v0, v1, v2, v3, v4]) => {
  const V = [v0, v1, v2, v3, v4];
  const d = dot(p.sub(v0), p.sub(v0)).toVar(); const s = float(1.0).toVar();
  for (let i = 0, j = 4; i < 5; j = i, i++) {
    const e = V[j].sub(V[i]), w = p.sub(V[i]); const ee = dot(e, e);
    If(ee.greaterThan(1e-10), () => {
      const b = w.sub(e.mul(clamp(dot(w, e).div(ee), 0.0, 1.0)));
      d.assign(min(d, dot(b, b)));
      const c1 = p.y.greaterThanEqual(V[i].y), c2 = p.y.lessThan(V[j].y), c3 = e.x.mul(w.y).greaterThan(e.y.mul(w.x));
      If(c1.and(c2).and(c3).or(c1.not().and(c2.not()).and(c3.not())), () => { s.mulAssign(-1.0); });
    });
  }
  return s.mul(sqrt(d));
}).setLayout({ name: 'sdPoly5', type: 'float', inputs: [{ name: 'p', type: 'vec2' }, { name: 'v0', type: 'vec2' }, { name: 'v1', type: 'vec2' }, { name: 'v2', type: 'vec2' }, { name: 'v3', type: 'vec2' }, { name: 'v4', type: 'vec2' }] });

function procMaterial(noiseTex, detailed) {
  const m = new THREE.MeshPhysicalNodeMaterial({ side: THREE.DoubleSide, clearcoat: 1 });
  const uTop = ou('top', V3()), uBelly = ou('belly', V3()), uTail = ou('tail', V3()), uTail2 = ou('tail2', V3()), uEng = ou('eng', V3()), uStripe = ou('stripe', V4());
  const uBellyLine = ou('bellyLine', 0), uTailStyle = ou('tailStyle', 1), uDirt = ou('dirt', 0.3), uDims = ou('dims', V4()), uWin = ou('win', V4()), uWinSize = ou('winSize', new THREE.Vector2()), uWin2 = ou('win2', V4()), uWinSize2 = ou('winSize2', new THREE.Vector2());
  const uDoorsA = ou('doorsA', V4()), uDoorB = ou('doorB', -100), uPaneInfo = ou('paneInfo', V4()), uSeed = ou('seed', 0.5);
  const uQ = []; for (let i = 0; i < 9; i++) uQ.push(ou('q' + i, V4()));
  const col = attribute('color', 'vec4'), ext = attribute('extra', 'vec4'), LP = attribute('position', 'vec3'), vUV = TSL.uv();
  let R = null;
  const core = () => {
    const part = floor(ext.z.add(0.5)).toVar(); const albedo = col.rgb.toVar(); const rough = ext.x.toVar(), metal = ext.y.toVar(); const cc = float(0).toVar(); const glass = float(0).toVar();
    const L = uDims.x, Rr = uDims.y; const px = max(fwidth(vUV.x), fwidth(vUV.y)).add(1e-4).toVar();
    If(part.equal(1), () => {
      const xn = vUV.x, yr = vUV.y, zz = abs(LP.z);
      albedo.assign(mix(uBelly, uTop, smoothstep(uBellyLine.sub(px), uBellyLine.add(px), yr)));
      const sy = uWin.w.sub(0.55);
      albedo.assign(mix(albedo, uStripe.rgb, smoothstep(sy.sub(0.18).sub(px), sy.sub(0.18).add(px), yr).sub(smoothstep(sy.add(0.02).sub(px), sy.add(0.02).add(px), yr)).mul(step(uWin.x.sub(2.0), xn)).mul(step(0.5, uStripe.w))));
      const tw = xn.add(yr.mul(1.4)).sub(L.sub(Rr.mul(4.6)));
      albedo.assign(mix(albedo, uTail, smoothstep(px.mul(-2.0), px.mul(2.0), tw).mul(smoothstep(Rr.mul(0.05).sub(px), Rr.mul(0.05).add(px), yr)).mul(uTailStyle)));
      cc.assign(1.0);
      if (detailed) {
        const onSide = smoothstep(Rr.mul(0.5), Rr.mul(0.75), zz);
        const doors = [uDoorsA.x, uDoorsA.y, uDoorsA.z, uDoorsA.w, uDoorB];
        for (let row = 0; row < 2; row++) {
          const Wn = row === 0 ? uWin : uWin2, Ws = row === 0 ? uWinSize : uWinSize2;
          const cell = xn.sub(Wn.x).div(Wn.z); const ci = floor(cell.add(0.5)); const cx = cell.sub(ci).mul(Wn.z);
          const valid = Wn.y.greaterThan(Wn.x).and(ci.greaterThanEqual(0.0)).and(ci.lessThanEqual(floor(Wn.y.sub(Wn.x).div(Wn.z).add(0.5)))).and(onSide.greaterThan(0.0));
          const d = sdBox(vec2(cx, yr), vec2(0.0, Wn.w), Ws.mul(0.5), min(Ws.x, Ws.y).mul(0.46));
          let inDoor = float(0);
          for (const dx of doors) inDoor = max(inDoor, float(1.0).sub(step(0.95, abs(Wn.x.add(ci.mul(Wn.z)).sub(dx)))));
          const aa = max(fwidth(d), 1e-4);
          const w = float(1.0).sub(smoothstep(aa.negate(), aa, d)).mul(float(1.0).sub(inDoor)).mul(onSide).mul(select(valid, float(1.0), float(0.0)));
          const ring = float(1.0).sub(smoothstep(float(0.018).sub(aa), float(0.018).add(aa), d)).mul(float(1.0).sub(inDoor)).mul(onSide).mul(select(valid, float(1.0), float(0.0))).sub(w);
          const farF = smoothstep(0.04, 0.2, px);
          albedo.assign(mix(albedo, albedo.mul(0.55), max(ring, 0.0).mul(float(1.0).sub(farF))));
          const hsh = hash13(vec3(ci, float(row).add(sign(LP.z).mul(7.0)), uSeed.mul(113.0)));
          const shadeTop = select(hsh.lessThan(0.22), float(1.0), select(hsh.lessThan(0.32), float(0.45), float(0.0)));
          const yIn = yr.sub(Wn.w.sub(Ws.y.mul(0.5))).div(Ws.y);
          const shade = step(float(1.0).sub(shadeTop), yIn).mul(step(0.001, shadeTop));
          const inner = mix(mix(vec3(0.03, 0.03, 0.032).mul(hash13(vec3(ci, 3.0, uSeed)).mul(0.6).add(0.7)), vec3(0.42, 0.42, 0.41), shade), vec3(0.05), farF.mul(0.6));
          albedo.assign(mix(albedo, inner, w)); rough.assign(mix(rough, 0.6, w)); glass.assign(max(glass, w));
        }
        for (const dx of doors) {
          const ddx = xn.sub(dx);
          const d = sdBox(vec2(ddx, yr), vec2(0.0, uWin.w.sub(0.62)), vec2(0.5, 0.95), 0.18);
          const line = float(1.0).sub(smoothstep(0.0, px.mul(1.2).add(0.012), abs(d))).mul(step(abs(ddx), 1.2)).mul(step(Rr.mul(0.5), zz));
          albedo.assign(mix(albedo, albedo.mul(0.45), line.mul(0.8).mul(float(1.0).sub(smoothstep(0.1, 0.3, px)))));
        }
        // flight-deck panes on the unwrapped surface (x from the nose, arc length from the crown)
        const qs = vec2(xn, ext.w);
        const best = float(1e3).toVar();
        for (let k = 0; k < 3; k++) {
          const sd = sdPoly5(qs, uQ[k * 3].xy, uQ[k * 3].zw, uQ[k * 3 + 1].xy, uQ[k * 3 + 1].zw, uQ[k * 3 + 2].xy).sub(uPaneInfo.x);
          best.assign(select(float(k).lessThan(uPaneInfo.y), min(best, sd), best));
        }
        const inCock = step(uPaneInfo.w, LP.x);
        const aa = max(fwidth(best), 1e-4).mul(0.8); const farF = smoothstep(0.03, 0.12, px);
        const mk = float(1.0).sub(smoothstep(uPaneInfo.z.sub(aa), uPaneInfo.z.add(aa), best)).mul(step(1e-6, uPaneInfo.z)).mul(inCock);
        albedo.assign(mix(albedo, vec3(0.018, 0.019, 0.021), mk)); rough.assign(mix(rough, 0.22, mk));
        const seal = float(1.0).sub(smoothstep(float(0.03).sub(aa), float(0.03).add(aa), best)).mul(inCock);
        albedo.assign(mix(albedo, vec3(0.03, 0.031, 0.033), seal)); rough.assign(mix(rough, 0.55, seal));
        const g = float(1.0).sub(smoothstep(aa.negate(), aa, best)).mul(inCock);
        albedo.assign(mix(albedo, vec3(0.022, 0.024, 0.026).mul(clamp(best.negate().div(0.25), 0.0, 1.0).mul(0.4).add(0.8)), g)); rough.assign(mix(rough, 0.5, g)); glass.assign(max(glass, g));
        void farF;
      }
      albedo.mulAssign(mix(float(0.94), float(1.0), smoothstep(0.8, 1.6, vUV.x)));
      albedo.mulAssign(float(1.0).sub(uDirt.mul(0.25).mul(smoothstep(Rr.mul(-0.4), Rr.negate(), vUV.y)).mul(texture(noiseTex, vec2(vUV.x.mul(0.05), vUV.y.mul(0.2))).b.mul(0.4).add(0.6))));
    }).ElseIf(part.equal(3), () => { // fin
      const diag = vUV.y.add(LP.x.negate().mul(0.06));
      albedo.assign(mix(uTail, uTail2, smoothstep(0.54, 0.56, fract(diag.mul(0.9).add(0.2))).mul(step(0.5, uTailStyle)))); rough.assign(0.26); cc.assign(1.0);
    }).ElseIf(part.equal(4), () => { albedo.assign(uEng); rough.assign(0.3); cc.assign(1.0); })
      .ElseIf(part.equal(11), () => { albedo.assign(vec3(0.8, 0.81, 0.83)); rough.assign(0.14); metal.assign(1.0); })
      .ElseIf(part.equal(5), () => { const a = atan(LP.y, LP.z); albedo.assign(vec3(0.1, 0.105, 0.11).mul(step(0.5, fract(a.mul(22.0 / 6.2831))).mul(0.3).add(0.7))); rough.assign(0.35); metal.assign(0.7); })
      .ElseIf(part.equal(2).or(part.equal(8)).or(part.equal(13)), () => {
        const base = select(part.equal(8), mix(vec3(0.72, 0.73, 0.75), uTop, 0.4), vec3(0.66, 0.67, 0.69));
        albedo.assign(base.mul(texture(noiseTex, LP.xz.mul(0.08)).b.mul(0.12).add(0.92)));
        const le = float(1.0).sub(smoothstep(0.035, 0.06, abs(vUV.y.sub(0.5))));
        albedo.assign(mix(albedo, vec3(0.8, 0.81, 0.83), le)); metal.assign(mix(metal, 1.0, le)); rough.assign(mix(rough, 0.2, le));
        const gl = float(1.0).sub(smoothstep(0.0, px.add(0.03), abs(fract(LP.z.div(1.9).add(0.5)).sub(0.5)).mul(1.9)));
        albedo.mulAssign(float(1.0).sub(gl.mul(0.08).mul(float(1.0).sub(smoothstep(0.05, 0.12, px)))));
      }).ElseIf(part.equal(12), () => { albedo.assign(uTop.mul(0.95)); rough.assign(0.35); cc.assign(1.0); });
    const ao = mix(float(0.75), float(1.0), smoothstep(-0.6, 0.4, normalize(normalWorld).y));
    // glass: smooth clear-coat layer over the dark cabin / flight deck
    return { albedo, rough: rough, metal, cc: max(cc.mul(float(1.0).sub(glass)), glass), ccr: mix(float(0.08), float(0.02), glass), ao };
  };
  const A = Fn(() => { R = core(); return vec4(R.albedo, R.rough); }).once();
  const B = Fn(() => { A(); return vec4(R.metal, R.cc, R.ccr, R.ao); }).once();
  m.colorNode = vec4(A().xyz, 1.0); m.roughnessNode = A().w; m.metalnessNode = B().x; m.clearcoatNode = B().y; m.clearcoatRoughnessNode = B().z; m.aoNode = B().w;
  m.normalNode = facingNormalView(); m.clearcoatNormalNode = facingNormalView();
  return m;
}

// ---------------------------------------------------------------- per-aircraft uniform values
function liveryU(ac, U) {
  const C = linearLivery(ac.liv); const set = (k, a) => { if (!U[k]) U[k] = a.length === 4 ? new THREE.Vector4() : new THREE.Vector3(); U[k].fromArray(a); };
  set('top', C.top); set('belly', C.belly); set('tail', C.tail); set('tail2', C.tail2); set('eng', C.eng); set('stripe', C.stripe);
  U.tailStyle = ac.liv.tailStyle; U.dirt = ac.dirt; U.sel = ac.selected || 0;
}
function realU(ac, U) {
  liveryU(ac, U);
  const L = ac.liv, T = ac.T, d = ac.model.dims; const s = T.L / d.L;
  U.bellyLine = (L.bellyLine * T.R / 1.98) / s;
  (U.fus = U.fus || new THREE.Vector4()).set(d.R, d.Rz, d.tailX, d.L);
  const cockX = Math.max(2.5, (T.win && T.win[0] ? T.win[0].x0 - 0.45 : 0.12 * T.L)) / s;
  (U.fusB = U.fusB || new THREE.Vector4()).set(d.crown, d.belly, cockX, ac.cabin || 0);
  U.lights = (ac.lightsOn.landing || ac.lightsOn.taxi) ? 1 : 0; U.gearUp = ac.gear <= 0.001 ? 1 : 0;
  U.noCabin = L && brandIsCargo(L.brand) ? 1 : 0;
}
function procU(ac, U) {
  const P = ac.procUniforms(); liveryU(ac, U);
  U.bellyLine = P.uBellyLine;
  const v4 = (k, a) => { (U[k] = U[k] || new THREE.Vector4()).set(a[0], a[1], a[2], a[3]); };
  v4('dims', P.uDims); v4('win', P.uWin); v4('win2', P.uWin2); (U.winSize = U.winSize || new THREE.Vector2()).set(P.uWinSize[0], P.uWinSize[1]); (U.winSize2 = U.winSize2 || new THREE.Vector2()).set(P.uWinSize2[0], P.uWinSize2[1]);
  v4('doorsA', P.uDoors.slice(0, 4)); U.doorB = P.uDoors[4] ?? -100; v4('paneInfo', P.uPaneInfo); U.seed = P.uSeed;
  for (let i = 0; i < 9; i++) v4('q' + i, P.uPaneQ.slice(i * 4, i * 4 + 4));
}

// ---------------------------------------------------------------- scene objects per aircraft
export class AircraftRenderer {
  constructor(scene, { noiseTex }) {
    this.scene = scene; this.noiseTex = noiseTex;
    this.group = new THREE.Group(); this.group.name = 'aircraft'; scene.add(this.group);
    this.entries = new Map(); this.realMats = new Map(); this.realGeo = new Map();
    this.procDetailed = procMaterial(noiseTex, true); this.procSimple = procMaterial(noiseTex, false);
  }
  // one material per draw of a model (x livery texture); the livery replaces texture 0 of atlas draws. A neutral skin
  // (js/aircraft/liveries.js neutralTextureFor: the type's own window row, no titles) is drawn like the model's atlas,
  // with the brand's colours by zone (ACR_FS uLivTex = 0); a brand bake is the paint itself (uLivTex = 1).
  materialsFor(model, livRec, neutral = false) {
    const livTex = livRec ? textureOf(livRec, { anisotropy: 8, colorSpace: THREE.SRGBColorSpace }) : null;
    if (livTex) livTex.wrapS = livTex.wrapT = THREE.RepeatWrapping;
    const key = model.key + (livTex ? ':' + livTex.uuid + (neutral ? ':n' : '') : '');
    let mats = this.realMats.get(key); if (mats) return mats;
    mats = model.draws.map(d => {
      const t = d.tex >= 0 && d.U.uAlbedo ? textureOf(d.U.uAlbedo, { anisotropy: 8, colorSpace: THREE.SRGBColorSpace }) : null; if (t) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
      const useLiv = !!(livTex && d.atlas);
      return realMaterial(useLiv ? livTex : t, useLiv && !neutral, !!d.atlas);
    });
    this.realMats.set(key, mats); return mats;
  }
  geometryFor(model) {
    let g = this.realGeo.get(model); if (g) return g;
    g = geometryOf(model.mesh).clone(); g.clearGroups(); model.draws.forEach((d, i) => g.addGroup(d.first, d.count, i));
    g.computeBoundingSphere(); this.realGeo.set(model, g); return g;
  }
  entry(ac) {
    let e = this.entries.get(ac); if (e) return e;
    e = { group: new THREE.Group(), real: null, realModel: null, proc: null, parts: [], U: {} };
    e.group.matrixAutoUpdate = false; this.group.add(e.group);
    const body = new THREE.Mesh(geometryOf(ac.M.body), this.procSimple); body.matrixAutoUpdate = false; body.userData.acU = e.U; body.castShadow = body.receiveShadow = true; e.group.add(body); e.proc = body;
    const add = (list, kind) => list.forEach((p, i) => { const m = new THREE.Mesh(geometryOf(p.mesh), this.procSimple); m.matrixAutoUpdate = false; m.userData.acU = e.U; m.castShadow = m.receiveShadow = true; m.userData.part = { kind, i, p }; e.group.add(m); e.parts.push(m); });
    add(ac.M.gear, 'gear'); add(ac.M.flaps, 'flap'); add(ac.M.spoilers, 'spoiler');
    this.entries.set(ac, e); return e;
  }
  remove(ac) { const e = this.entries.get(ac); if (!e) return; this.group.remove(e.group); this.entries.delete(ac); }
  sync(list, camPos) {
    const alive = new Set(list);
    for (const ac of [...this.entries.keys()]) if (!alive.has(ac)) this.remove(ac);
    for (const ac of list) this.update(ac, camPos);
  }
  // LiveAircraft.items() LOD rules: real model within lodDist, procedural body beyond, nothing past farDist
  update(ac, camPos) {
    const e = this.entry(ac);
    const d = Math.hypot(camPos[0] - ac.pos[0], camPos[1] - ac.pos[1], camPos[2] - ac.pos[2]);
    e.group.visible = ac.visible !== false && d <= ac.farDist; if (!e.group.visible) return;
    const W = ac.matrix(); e.group.matrix.fromArray(W); e.group.matrixWorldNeedsUpdate = true;
    const shadow = d < ac.shadowDist;
    const M = ac.model;
    const useReal = M && d <= ac.lodDist;
    const fullProc = !M && !ac.modelKey && d <= ac.lodDist; // no imported model for this type: full procedural airframe
    if (useReal) {
      if (ac.updateLiveryTexture) ac.updateLiveryTexture(); // brand livery (async; ac.livTex once loaded)
      const liv = ac.livTex || null, neutral = !!ac._livNeutral; // js/live/aircraft.js updateLiveryTexture
      if (e.realModel !== M || e.realLiv !== liv) {
        if (e.real) e.group.remove(e.real);
        e.real = new THREE.Mesh(this.geometryFor(M), this.materialsFor(M, liv, neutral)); e.real.matrixAutoUpdate = false; e.real.userData.acU = e.U; e.group.add(e.real); e.realModel = M; e.realLiv = liv;
      }
      e.real.matrix.fromArray(ac.placement()); e.real.visible = true; e.real.castShadow = shadow; e.real.receiveShadow = true;
      realU(ac, e.U);
    } else if (e.real) e.real.visible = false;
    e.proc.visible = !useReal; e.proc.castShadow = shadow;
    if (!useReal) { procU(ac, e.U); e.proc.material = fullProc ? this.procDetailed : this.procSimple; }
    // procedural gear under gear-less imported models, and all moving parts of full procedural airframes
    for (const m of e.parts) {
      const { kind, p } = m.userData.part; let vis = false, L = null;
      if (kind === 'gear') { vis = ac.gear > 0.001 && ((useReal && !M.dims.hasGear) || fullProc); if (vis) L = rotAxisAbout(p.axis, p.angle * (1 - ac.gear), p.pivot); }
      else if (kind === 'flap' && fullProc) { vis = true; const dd = ac.flaps; const ang = dd * (p.kind === 'inboard' ? 0.52 : 0.45); L = m4.mul(m4.translate(-p.chord * 0.42 * dd, -p.chord * 0.1 * dd, 0), rotAxisAbout([0, 0, 1], ang, p.hinge)); }
      else if (kind === 'spoiler' && fullProc) { vis = true; const ax = [p.hinge2[0] - p.hinge[0], p.hinge2[1] - p.hinge[1], p.hinge2[2] - p.hinge[2]]; L = rotAxisAbout(ax, -p.side * 0.8 * ac.spoilers, p.hinge); }
      m.visible = vis; if (vis) { m.matrix.fromArray(L); m.castShadow = shadow; }
    }
  }
}

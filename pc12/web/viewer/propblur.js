// Propeller in motion (owner 2026-10-03: "the propeller spinning doesn't look too real").
//
// The five blade meshes turn rigidly at the true rate; at display frame rates that strobes (wagon wheel: 1,700 rpm is
// 170 deg a frame at 60 fps, more than two blade spacings) and a rigid blade has none of the motion blur the eye or a
// camera sees.  Once the blades turn more than a few degrees a frame they cross-fade into
//
//   disc   a flat annulus in the plane of rotation (child of the spinning propeller node, on the thrust axis taken from
//          the GLB pivot extras) whose shader draws the motion-blurred blades analytically.  At load the real blade
//          geometry (blade_1, built pitch) is sliced at NR radii; each section is stored as its 2-D support function
//          h(r, phi) in the (tangential, axial) section plane, plus the material-averaged colour / roughness /
//          metalness and the chord angle.  Per fragment the section is turned by the commanded pitch and projected
//          along the view ray onto the disc plane (the angular interval it occludes: exact for the section's convex
//          hull, so the blades read correctly from any side and their apparent width follows fine / feather / reverse
//          pitch); the coverage is that interval box-filtered over the exposure sweep S (trailing: the smear lies behind
//          the blade), periodic over the five blades -- a closed form (two floor / mod terms), no texture taps along
//          the arc.  S -> 0 gives sharp blades (pixel-footprint anti-aliased), S = one blade spacing gives the
//          azimuthally averaged disc: the chord coverage per radius (~20 % at mid-span, ~6 % at the white tips) with
//          the white tip band, black blade and red band as faint rings; the alpha is that coverage mapped so that three's
//          blend (after tone mapping and the sRGB encoding) gives the linear-light average, 1 - (1 - c)^(1/2.2).  Lit by the scene's lights and environment with
//          the normal of the blade face that passes each point (so the stationary glints of a real disc), a clone of the
//          blade material (same specular / environment response), double-sided, depth-tested, no depth write.
//   band   the five black boots round the blade roots on the chrome spinner, blurred the same way on a surface of
//          revolution 1.5 mm outside the spinner (profile sampled from the chrome mesh and smoothed by a quadratic fit,
//          normals from the fit: the raw samples gave stair-stepped reflections), so nothing on the spinner strobes
//          either; once the blur is complete the chrome spinner is held still against the spin (it is axisymmetric under
//          the band: its tessellation re-sampling the studio every frame made the highlights twinkle, review r1 PR1-03).
//          The band is opaque over its whole axial range (it covers the spinner's blade cut-outs, +-53 mm against the
//          boots' +-66: where it went clear with the boot outline the held-still chrome showed a standing dark notch),
//          feathered over BAND_FEATHER at its ends, carries no ghost (black boots on a mirror flickered frame to frame;
//          the disc carries the motion) and closes the boot outline over BAND_FEATHER too (review r2 PR2-01).
//
// Hidden, not just transparent: the faded blades and boots are hidden as meshes (mesh.visible, Model.updateVisibility
// keeps it via mr.blurHidden), so neither picking nor the selection / hover overlays (children of the meshes) see
// them (review r1 PR1-01: a hover over the disc drew one sharp blade at the true spin angle); the disc is picked as
// 'propeller' instead and shows the highlight as a tint (uPbTint) while the propeller is selected / hovered.
//
// Anti-aliasing in time: the sweep is S = min(P, max(w T_eye, 2.5 w dt)) (P = 72 deg, dt = the smoothed frame time,
// T_eye = 1/40 s): the smear always spans at least 2.5 frame steps, so the blades never jump more than 40 % of their
// own smear between frames and never alias; by 0.4 P a frame (~290 rpm at 60 fps) the true pattern has blurred into the
// uniform disc.  Above that a faint ghost of the blade smear (gain GHOST, its own sweep) keeps the disc reading as a
// turning propeller rather than a glass plate: its phase advances with the prop but never more than 0.4 P a frame, so
// it always moves forward (no backwards / standing wagon wheel at any rpm or frame rate).
import * as THREE from 'three';

const TAU = Math.PI * 2;
const NR = 64;                 // radial sections
const NPHI = 64;               // support-function directions
const NZ = 32;                 // axial slices of the root boots
const T_EYE = 1 / 40;          // exposure of the eye / a video camera (s)
const STEP_SWEEP = 2.5;        // sweep >= 2.5 x the per-frame advance
const GHOST = 0.35;            // gain of the moving ghost once the true pattern is uniform
const GHOST_SWEEP = 0.7;       // its sweep (blade spacings)
const GHOST_STEP = 0.4;        // its largest advance per frame (blade spacings)
// sweep (deg) over which the solid blades fade into the disc: [4, 14] left them half-faded -- grey glass, the cowl
// showing through, overlaps darkening twice -- for ~1 s of every start and run-down (review r2 PR2-02); alpha hashing
// instead speckled them with static noise (no temporal anti-aliasing here).  At 60 fps the fade now spans 24-40 rpm.
const FADE_DEG = [6, 10];
const DISC_IN = 0.2;           // disc inner radius (m), inside the spinner
const BAND_OFF = 0.0015;       // band offset outside the chrome spinner (m)
const BAND_FEATHER = 0.005;     // band ends and boot-outline ends feathered over this (m)
// The disc is shaded as one dielectric: averaging a metal's colour into the albedo (and its metalness) would light the
// thin nickel leading-edge sheath (~12 % of the section) like a grey paint covering the whole blade; it counts as a
// grey of this fraction of its colour instead.
const METAL_AS_DIFFUSE = 0.3;

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const wrapP = (x, P) => x - P * Math.floor(x / P);

// ---------------------------------------------------------------- GLSL
const GLSL_COMMON = `
uniform vec3 uPbA, uPbE1, uPbE2;
uniform vec4 uPbBlur;      // sweep (rad), phase offset (rad), pitch (rad), fade
uniform vec4 uPbGhost;     // gain, sweep (rad), phase offset (rad), -
uniform float uPbPeriod;
varying vec3 vPbP;
// integral over [lo, x] of the periodic indicator of [lo, lo + w] (+ a constant)
float pbCum(float x, float lo, float w) { float y = x - lo; return floor(y / uPbPeriod) * w + min(mod(y, uPbPeriod), w); }
// fraction of the exposure sweep s (trailing) during which a blade covers angle th; aa = the pixel's angular footprint
float pbBlur(float th, float lo, float w, float s, float aa) {
  float a = th - 0.5 * aa, b = th + s + 0.5 * aa;
  return (pbCum(b, lo, w) - pbCum(a, lo, w)) / max(b - a, 1e-6);
}
`;

const GLSL_DISC_FS = GLSL_COMMON + `
uniform sampler2D uPbH;    // support function h(r, phi): s = radius, t = direction (repeat)
uniform sampler2D uPbC;    // per radius: row 0 albedo + metalness, row 1 roughness, chord angle
uniform vec4 uPbRad;       // data radius range R0, R1, radial push (explode), -
uniform vec3 uPbCam;       // camera position in the propeller frame
uniform vec4 uPbTint;      // highlight (selected / hovered propeller): colour, strength
varying vec3 vPbN0, vPbN1, vPbN2;
`;

const GLSL_BAND_FS = GLSL_COMMON + `
uniform vec2 uPbRing[${NZ}];   // boot outline: angular interval about the blade axis per axial slice
uniform vec4 uPbZ;             // axial range of the slice centres, of the boots
uniform vec4 uPbBandZ;         // axial range of the band, feather (m), -
uniform vec3 uPbBoot;          // boot reflectance as a metal F0 (linear)
`;

function patchDisc(mat, uni) {
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uni);
    sh.vertexShader = 'uniform float uPbScale;\nvarying vec3 vPbP;\nvarying vec3 vPbN0, vPbN1, vPbN2;\n' +
      sh.vertexShader.replace('#include <project_vertex>', `#include <project_vertex>
  vPbP = position * uPbScale;
  vPbN0 = normalMatrix * vec3(1.0, 0.0, 0.0); vPbN1 = normalMatrix * vec3(0.0, 1.0, 0.0); vPbN2 = normalMatrix * vec3(0.0, 0.0, 1.0);`);
    sh.fragmentShader = GLSL_DISC_FS + sh.fragmentShader
      .replace('#include <color_fragment>', `#include <color_fragment>
  // fragment in the propeller frame: radius, azimuth from blade 1 (positive = direction of rotation)
  float pbX1 = dot(vPbP, uPbE1), pbX2 = dot(vPbP, uPbE2);
  float pbR = max(length(vec2(pbX1, pbX2)), 1e-4);
  float pbTh = atan(pbX2, pbX1);
  vec3 pbEr = (pbX1 * uPbE1 + pbX2 * uPbE2) / pbR;
  vec3 pbEt = cross(uPbA, pbEr);
  // view ray (camera -> fragment): t = tangential / axial slope; the section (s_t, s_a), turned by the pitch p,
  // projects to q = s . R(-p) (1, -t) along the disc's tangent
  vec3 pbV = normalize(vPbP - uPbCam);
  float pbVa = dot(pbV, uPbA);
  pbVa = pbVa >= 0.0 ? max(pbVa, 0.03) : min(pbVa, -0.03);
  float pbT = dot(pbV, pbEt) / pbVa;
  float pbPt = uPbBlur.z;
  vec2 pbU = vec2(cos(pbPt) - pbT * sin(pbPt), -sin(pbPt) - pbT * cos(pbPt));
  float pbUl = length(pbU);
  float pbPhi = atan(pbU.y, pbU.x) * 0.15915494;
  float pbRd = pbR - uPbRad.z;                                   // radius on the unexploded blade
  float pbS = (pbRd - uPbRad.x) / (uPbRad.y - uPbRad.x);
  float pbHp = texture2D(uPbH, vec2(pbS, pbPhi)).r;
  float pbHm = texture2D(uPbH, vec2(pbS, pbPhi + 0.5)).r;
  float pbW = clamp(pbUl * (pbHp + pbHm) / pbR, 0.0, uPbPeriod);   // occluded arc (rad)
  float pbLo = -pbUl * pbHm / pbR;
  float pbAA = (abs(dFdx(pbX2) * pbX1 - dFdx(pbX1) * pbX2) + abs(dFdy(pbX2) * pbX1 - dFdy(pbX1) * pbX2)) / (pbR * pbR);
  float pbCov = mix(pbBlur(pbTh - uPbBlur.y, pbLo, pbW, uPbBlur.x, pbAA),
                    pbBlur(pbTh - uPbGhost.z, pbLo, pbW, uPbGhost.y, pbAA), uPbGhost.x);
  float pbDr = max(fwidth(pbR), 1e-4);
  pbCov *= clamp((pbRd - uPbRad.x) / pbDr + 0.5, 0.0, 1.0) * clamp((uPbRad.y - pbRd) / pbDr + 0.5, 0.0, 1.0);
  vec4 pbC0 = texture2D(uPbC, vec2(pbS, 0.25));
  vec4 pbC1 = texture2D(uPbC, vec2(pbS, 0.75));
  // three blends after tone mapping and the sRGB encoding: the alpha that makes that blend the linear-light average
  // of blade and background over the exposure (a coverage c would darken ~twice as much)
  diffuseColor = vec4(pbC0.rgb, (1.0 - pow(1.0 - clamp(pbCov, 0.0, 1.0), 0.4545)) * uPbBlur.w);
  // the selection / hover highlight on the whole disc (the overlays of the hidden blades are not drawn)
  diffuseColor.rgb = mix(diffuseColor.rgb, uPbTint.rgb, uPbTint.a);
  diffuseColor.a += (1.0 - diffuseColor.a) * uPbTint.a * 0.45 * uPbBlur.w;`)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n  roughnessFactor = pbC1.x;')
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\n  metalnessFactor = pbC0.a;')
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  // the face of the blade that passes this point (chord angle + pitch), the side facing the camera
  float pbBe = pbC1.y + pbPt;
  vec3 pbN = -sin(pbBe) * pbEt + cos(pbBe) * uPbA;
  if (dot(pbN, pbV) > 0.0) pbN = -pbN;
  normal = normalize(vPbN0 * pbN.x + vPbN1 * pbN.y + vPbN2 * pbN.z);`);
  };
  mat.customProgramCacheKey = () => 'pc12:propdisc';
}

function patchBand(mat, uni) {
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uni);
    sh.vertexShader = 'varying vec3 vPbP;\n' +
      sh.vertexShader.replace('#include <project_vertex>', '#include <project_vertex>\n  vPbP = position;');
    sh.fragmentShader = GLSL_BAND_FS + sh.fragmentShader
      .replace('#include <color_fragment>', `#include <color_fragment>
  float pbX1 = dot(vPbP, uPbE1), pbX2 = dot(vPbP, uPbE2);
  float pbR2 = max(pbX1 * pbX1 + pbX2 * pbX2, 1e-8);
  float pbTh = atan(pbX2, pbX1);
  float pbZa = dot(vPbP, uPbA);
  float pbK = clamp((pbZa - uPbZ.x) / (uPbZ.y - uPbZ.x), 0.0, 1.0) * ${(NZ - 1).toFixed(1)};
  int pbI = int(min(floor(pbK), ${(NZ - 2).toFixed(1)}));
  vec2 pbIv = mix(uPbRing[pbI], uPbRing[pbI + 1], pbK - float(pbI));
  // the outline closes at the boots' axial ends, feathered (no crisp ring step)
  float pbEnd = smoothstep(uPbZ.z, uPbZ.z + uPbBandZ.z, pbZa) * smoothstep(uPbZ.w, uPbZ.w - uPbBandZ.z, pbZa);
  float pbMid = 0.5 * (pbIv.x + pbIv.y);
  pbIv = pbMid + (pbIv - pbMid) * pbEnd;
  float pbW = clamp(pbIv.y - pbIv.x, 0.0, uPbPeriod);
  float pbAA = (abs(dFdx(pbX2) * pbX1 - dFdx(pbX1) * pbX2) + abs(dFdy(pbX2) * pbX1 - dFdy(pbX1) * pbX2)) / pbR2;
  // the true pattern only, no ghost (PR2-01: a ghost of black boots on a mirror is a high-contrast flicker)
  float pbCov = pbBlur(pbTh - uPbBlur.y, pbIv.x, pbW, uPbBlur.x, pbAA);
  // time average of the mirror spinner and the black boots: the chrome's reflection (sharp: its own roughness) scaled
  // by the fraction of time the chrome is there, plus the boots' faint dielectric sheen
  diffuseColor.rgb = mix(diffuseColor.rgb, uPbBoot, pbCov);
  // opaque over the band's whole axial range (it hides the turning boots and the still spinner's blade cut-outs, which
  // are shorter than the boots), feathered at its ends
  diffuseColor.a = uPbBlur.w * smoothstep(uPbBandZ.x, uPbBandZ.x + uPbBandZ.z, pbZa) *
    (1.0 - smoothstep(uPbBandZ.y - uPbBandZ.z, uPbBandZ.y, pbZa));`)

  };
  mat.customProgramCacheKey = () => 'pc12:propband';
}

// ---------------------------------------------------------------- geometry sampling
// vertices of a part's meshes in the propeller frame: offset = the part node's rest position in that frame (a blade:
// its node's rest position, no rotation; the propeller's own meshes: none)
function partVerts(rec, filter, offset = null) {
  const out = [];
  const v = new THREE.Vector3();
  for (const mr of rec.meshes) {
    if (filter && !filter(mr)) continue;
    const m = mr.mesh;
    m.updateMatrix();
    const P = m.geometry.attributes.position, I = m.geometry.index;
    const xyz = new Float32Array(P.count * 3);
    for (let i = 0; i < P.count; i++) {
      v.fromBufferAttribute(P, i).applyMatrix4(m.matrix);
      if (offset) v.add(offset);
      xyz[3 * i] = v.x; xyz[3 * i + 1] = v.y; xyz[3 * i + 2] = v.z;
    }
    out.push({ xyz, index: I ? I.array : null, count: I ? I.count : P.count, mat: mr.base });
  }
  return out;
}

// Slice triangles by the planes key(p) = k_j (j = 0..n-1, k_j = k0 + (j + 0.5) dk); calls emit(j, x0, y0, x1, y1, mat)
// with the two section points in the 2-D coordinates (cx(p), cy(p)).
function slice(meshes, key, cx, cy, k0, dk, n, emit) {
  const kv = [0, 0, 0], xv = [0, 0, 0], yv = [0, 0, 0], p = new THREE.Vector3();
  for (const m of meshes) {
    const { xyz, index } = m;
    for (let t = 0; t < m.count; t += 3) {
      for (let c = 0; c < 3; c++) {
        const i = index ? index[t + c] : t + c;
        p.set(xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]);
        kv[c] = key(p); xv[c] = cx(p); yv[c] = cy(p);
      }
      const lo = Math.min(kv[0], kv[1], kv[2]), hi = Math.max(kv[0], kv[1], kv[2]);
      const j0 = Math.max(0, Math.ceil((lo - k0) / dk - 0.5)), j1 = Math.min(n - 1, Math.floor((hi - k0) / dk - 0.5));
      for (let j = j0; j <= j1; j++) {
        const kj = k0 + (j + 0.5) * dk;
        let np = 0, x0 = 0, y0 = 0, x1 = 0, y1 = 0;
        for (let e = 0; e < 3; e++) {
          const a = e, b = (e + 1) % 3, sa = kv[a] - kj, sb = kv[b] - kj;
          if ((sa <= 0) === (sb <= 0)) continue;
          const f = sa / (sa - sb), x = xv[a] + f * (xv[b] - xv[a]), y = yv[a] + f * (yv[b] - yv[a]);
          if (np === 0) { x0 = x; y0 = y; } else { x1 = x; y1 = y; }
          np++;
        }
        if (np === 2) emit(j, x0, y0, x1, y1, m.mat);
      }
    }
  }
}

// Blade sections: support function table, averaged material, chord angle.
function sampleBlade(rec, F) {
  const meshes = partVerts(rec, null, rec.restPos);
  let r0 = Infinity, r1 = -Infinity;
  for (const m of meshes) {
    for (let i = 0; i < m.xyz.length; i += 3) {
      const r = m.xyz[i] * F.e1.x + m.xyz[i + 1] * F.e1.y + m.xyz[i + 2] * F.e1.z;
      r0 = Math.min(r0, r); r1 = Math.max(r1, r);
    }
  }
  const dr = (r1 - r0) / NR;
  const cs = new Float32Array(NPHI), sn = new Float32Array(NPHI);
  for (let j = 0; j < NPHI; j++) { cs[j] = Math.cos(TAU * (j + 0.5) / NPHI); sn[j] = Math.sin(TAU * (j + 0.5) / NPHI); }
  const H = new Float32Array(NR * NPHI).fill(-Infinity);
  const acc = Array.from({ length: NR }, () => ({ L: 0, r: 0, g: 0, b: 0, ro: 0 }));
  const point = (k, x, y) => {
    const o = k * NPHI;
    for (let j = 0; j < NPHI; j++) { const d = x * cs[j] + y * sn[j]; if (d > H[o + j]) H[o + j] = d; }
  };
  slice(meshes, (p) => p.dot(F.e1), (p) => p.dot(F.e2), (p) => p.dot(F.a), r0, dr, NR, (k, x0, y0, x1, y1, mat) => {
    point(k, x0, y0); point(k, x1, y1);
    const L = Math.hypot(x1 - x0, y1 - y0), A = acc[k];
    const c = mat.color || { r: 0.02, g: 0.02, b: 0.02 };
    const kd = 1 - (1 - METAL_AS_DIFFUSE) * (mat.metalness ?? 0);
    A.L += L; A.r += L * kd * c.r; A.g += L * kd * c.g; A.b += L * kd * c.b;
    A.ro += L * (mat.roughness ?? 0.5);
  });
  // per radius: albedo / metalness / roughness averages, chord angle (direction of the largest width, leading edge
  // toward the rotation); empty sections (none) get h = 0 = no coverage
  const col = new Float32Array(NR * 2 * 4);
  const beta = new Float32Array(NR).fill(NaN);
  let last = null;
  for (let k = 0; k < NR; k++) {
    const o = k * NPHI;
    if (!Number.isFinite(H[o])) { for (let j = 0; j < NPHI; j++) H[o + j] = 0; continue; }
    let wMax = -1, wMin = Infinity, jm = 0;
    for (let j = 0; j < NPHI / 2; j++) {
      const w = H[o + j] + H[o + j + NPHI / 2];
      if (w > wMax) { wMax = w; jm = j; }
      wMin = Math.min(wMin, w);
    }
    if (wMax > 1.4 * wMin) {      // a blade section (not the round shank): refine the peak, LE toward +tangential
      const wm = (j) => H[o + ((j + NPHI) % NPHI)] + H[o + ((j + NPHI / 2 + NPHI) % NPHI)];
      const y0 = wm(jm - 1), y1 = wm(jm), y2 = wm(jm + 1), den = y0 - 2 * y1 + y2;
      const dj = den < 0 ? 0.5 * (y0 - y2) / den : 0;
      let b = TAU * (jm + 0.5 + dj) / NPHI;
      if (Math.cos(b) < 0) b -= Math.PI;
      beta[k] = Math.atan2(Math.sin(b), Math.cos(b));
    }
    const A = acc[k];
    if (A.L > 0) last = [A.r / A.L, A.g / A.L, A.b / A.L, 0, A.ro / A.L];
    const c = last || [0.015, 0.015, 0.017, 0, 0.45];
    col.set([c[0], c[1], c[2], c[3]], 4 * k);
    col.set([c[4], 0, 0, 1], 4 * (NR + k));
  }
  // chord angle of the round shank / gaps: the nearest measured section
  for (let k = 0; k < NR; k++) {
    if (Number.isFinite(beta[k])) continue;
    let best = null;
    for (let d = 1; d < NR && best === null; d++) {
      if (k - d >= 0 && Number.isFinite(beta[k - d])) best = beta[k - d];
      else if (k + d < NR && Number.isFinite(beta[k + d])) best = beta[k + d];
    }
    beta[k] = best ?? 0.6;
  }
  for (let k = 0; k < NR; k++) col[4 * (NR + k) + 1] = beta[k];
  return { r0, r1, H, col, beta };
}

function halfTex(data, w, h, format) {
  const u = new Uint16Array(data.length);
  for (let i = 0; i < data.length; i++) u[i] = THREE.DataUtils.toHalfFloat(data[i]);
  const t = new THREE.DataTexture(u, w, h, format, THREE.HalfFloatType);
  t.minFilter = t.magFilter = THREE.LinearFilter;
  t.generateMipmaps = false;
  t.needsUpdate = true;
  return t;
}

// ---------------------------------------------------------------- PropBlur
export class PropBlur {
  // prop: the propeller part record (pivot kind 'spin'); null when the model has no five-bladed propeller
  static create(model, prop) {
    if (!prop || !prop.ex.pivot) return null;
    const blades = prop.children.filter((c) => c.ex.pivot && c.ex.pivot.kind === 'pitch');
    if (blades.length < 2) return null;
    try { return new PropBlur(model, prop, blades); } catch (e) {
      console.warn('prop blur unavailable:', e && e.message ? e.message : e);
      return null;
    }
  }

  constructor(model, prop, blades) {
    const t0 = performance.now();
    this.model = model;
    this.prop = prop;
    this.blades = blades.sort((a, b) => a.id.localeCompare(b.id));
    const nb = this.blades.length;
    this.period = TAU / nb;
    // propeller frame (the node's own axes: the GLB builds it unrotated, so these are the pivot axes as stored)
    const a = new THREE.Vector3().fromArray(prop.ex.pivot.axis).normalize();
    const b1 = new THREE.Vector3().fromArray(this.blades[0].ex.pivot.axis);
    const e1 = b1.addScaledVector(a, -b1.dot(a)).normalize();
    const e2 = new THREE.Vector3().crossVectors(a, e1);          // direction of rotation at blade 1
    this.frame = { a, e1, e2 };
    // the blades must be evenly spaced, blade k at -(k - 1) x 72 deg (or any multiple): the pattern is periodic
    for (const bl of this.blades) {
      const ax = new THREE.Vector3().fromArray(bl.ex.pivot.axis);
      const th = Math.atan2(ax.dot(e2), ax.dot(e1));
      const off = Math.abs(th - this.period * Math.round(th / this.period));
      if (off > 0.02) throw new Error(`${bl.id} is not on the ${nb}-blade spacing (${(off * 180 / Math.PI).toFixed(1)} deg off)`);
    }
    const sec = (this.sections = sampleBlade(this.blades[0], this.frame));
    this.R0 = sec.r0; this.R1 = sec.r1;
    this.outerR = sec.r1 + 0.01;

    // shared uniforms
    const U = (this.U = {
      uPbA: { value: a.clone() }, uPbE1: { value: e1.clone() }, uPbE2: { value: e2.clone() },
      uPbBlur: { value: new THREE.Vector4(0, 0, 0, 0) }, uPbGhost: { value: new THREE.Vector4(0, 0, 0, 0) },
      uPbPeriod: { value: this.period },
    });

    // ---- the disc
    const blMesh = this.blades[0].meshes.find((mr) => mr.base.name === 'prop_blade') || this.blades[0].meshes[0];
    const discMat = blMesh.base.clone();
    discMat.name = 'prop_disc';
    discMat.transparent = true;
    discMat.depthWrite = false;
    discMat.side = THREE.DoubleSide;
    discMat.vertexColors = false;
    // support function: texture rows = directions (repeat), columns = radii; H is stored [radius][direction]
    const T = new Float32Array(NR * NPHI);
    for (let k = 0; k < NR; k++) for (let j = 0; j < NPHI; j++) T[j * NR + k] = sec.H[k * NPHI + j];
    const hTex = halfTex(T, NR, NPHI, THREE.RedFormat);
    hTex.wrapT = THREE.RepeatWrapping;
    this.discU = {
      ...U,
      uPbH: { value: hTex },
      uPbC: { value: halfTex(sec.col, NR, 2, THREE.RGBAFormat) },
      uPbRad: { value: new THREE.Vector4(sec.r0, sec.r1, 0, 0) },
      uPbCam: { value: new THREE.Vector3() },
      uPbScale: { value: 1 },
      uPbTint: { value: new THREE.Vector4(0, 0, 0, 0) },
    };
    patchDisc(discMat, this.discU);
    const disc = (this.disc = new THREE.Mesh(this._discGeometry(DISC_IN, this.outerR, 160), discMat));
    disc.name = 'prop_blur_disc';
    const cam = new THREE.Vector3();
    disc.onBeforeRender = (renderer, scene, camera) => {
      cam.setFromMatrixPosition(camera.matrixWorld);
      this.discU.uPbCam.value.copy(prop.node.worldToLocal(cam));
    };

    // ---- the root-boot band on the spinner
    this.band = null;
    const bootMr = prop.meshes.filter((mr) => mr.base.name === 'deice_boot');
    const chromeMr = prop.meshes.find((mr) => mr.base.name === 'chrome');
    if (bootMr.length && chromeMr) this._makeBand(bootMr, chromeMr);

    for (const m of [disc, this.band].filter(Boolean)) {
      // the band first, writing depth: the disc runs on inside the spinner (DISC_IN) and, drawn after a band that
      // wrote none, showed its dark root coverage through the still spinner's blade cut-outs -- a standing dark notch
      // on the band (review r2 PR2-01)
      m.renderOrder = m === this.band ? 1 : 2;
      m.castShadow = m.receiveShadow = false;
      m.frustumCulled = false;
      m.raycast = () => {};
      m.visible = false;
      prop.node.add(m);
    }
    // the disc stands for the propeller in picking once the blades have faded into it (main.js maps it to the part)
    disc.raycast = (rc, hits) => { if (this.fade >= 0.5) THREE.Mesh.prototype.raycast.call(disc, rc, hits); };
    // the chrome spinner, held still against the spin once the blur is complete (PR1-03)
    // (the mesh's own local transform -- KHR_mesh_quantization's offset and scale -- is premultiplied by the inverse
    // spin, position included, so the spinner stays put about the node's origin on the thrust axis)
    this.still = prop.meshes.filter((mr) => mr.base.name === 'chrome')
      .map((mr) => ({ mesh: mr.mesh, q0: mr.mesh.quaternion.clone(), p0: mr.mesh.position.clone() }));
    this._q = new THREE.Quaternion();

    // the solid blades (and boots) fade out: own material clones (the red band is shared with the airstair door)
    this.fadeMats = [];
    const clones = new Map();
    const own = (mr) => {
      let c = clones.get(mr.base);
      if (!c) { c = mr.base.clone(); c.userData = { ...mr.base.userData }; clones.set(mr.base, c); this.fadeMats.push(c); }
      mr.base = c;
      mr.mesh.material = c;
    };
    this.fadeRecs = [];
    for (const bl of this.blades) for (const mr of bl.meshes) { own(mr); this.fadeRecs.push(mr); }
    for (const mr of bootMr) { own(mr); this.fadeRecs.push(mr); }
    for (const mr of this.fadeRecs) mr.blurFade = true;
    this.tint = { sel: new THREE.Color(0x1d7bff), hover: new THREE.Color(0xffb020) };

    this.dt = 1 / 60;            // smoothed frame time
    this.ghostPhase = 0;         // absolute phase of the ghost pattern (rad)
    this.push = 0;
    this.fade = 0;
    this.fadeChanged = false;    // the fade moved at the last apply (the key-light shadow map needs the blades' change)
    this.state = { fade: 0, sweepDeg: 0, ghost: 0, visible: false };
    this.buildMs = performance.now() - t0;
  }

  // the disc and band on show while the scene's programs compile at load (no shader-compile hitch on the first spin);
  // returns the function that hides them again
  warmup() {
    const ms = [this.disc, this.band].filter(Boolean), was = ms.map((m) => m.visible);
    for (const m of ms) m.visible = true;
    return () => ms.forEach((m, i) => { m.visible = was[i]; });
  }

  _discGeometry(rIn, rOut, seg) {
    const { a, e1, e2 } = this.frame;
    const pos = [], nrm = [], idx = [];
    for (let i = 0; i <= seg; i++) {
      const t = TAU * i / seg, c = Math.cos(t), s = Math.sin(t);
      for (const r of [rIn, rOut]) {
        pos.push(r * (c * e1.x + s * e2.x), r * (c * e1.y + s * e2.y), r * (c * e1.z + s * e2.z));
        nrm.push(a.x, a.y, a.z);
      }
      if (i < seg) { const k = 2 * i; idx.push(k, k + 1, k + 3, k, k + 3, k + 2); }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
    g.setIndex(idx);
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), rOut * 2);
    return g;
  }

  // the five boots: their outline per axial slice (angular interval about the blade axis), drawn blurred on a surface
  // of revolution just outside the chrome spinner
  _makeBand(bootMr, chromeMr) {
    const { a, e1, e2 } = this.frame, P = this.period;
    const boots = partVerts(this.prop, (mr) => bootMr.includes(mr));
    let z0 = Infinity, z1 = -Infinity;
    for (const m of boots) for (let i = 0; i < m.xyz.length; i += 3) {
      const z = m.xyz[i] * a.x + m.xyz[i + 1] * a.y + m.xyz[i + 2] * a.z;
      z0 = Math.min(z0, z); z1 = Math.max(z1, z);
    }
    const dz = (z1 - z0) / NZ;
    const lo = new Float32Array(NZ).fill(Infinity), hi = new Float32Array(NZ).fill(-Infinity);
    const rel = (p) => { const th = Math.atan2(p.dot(e2), p.dot(e1)); return th - P * Math.round(th / P); };
    slice(boots, (p) => p.dot(a), rel, () => 0, z0, dz, NZ, (k, x0, y0, x1) => {
      lo[k] = Math.min(lo[k], x0, x1); hi[k] = Math.max(hi[k], x0, x1);
    });
    // per slice centre; the shader interpolates between them and closes the outline toward the boots' axial ends
    const ring = [];
    for (let k = 0; k < NZ; k++) {
      const ok = Number.isFinite(lo[k]) && hi[k] > lo[k];
      ring.push(new THREE.Vector2(ok ? lo[k] : 0, ok ? hi[k] : 0));
    }
    // spinner profile: largest chrome radius per axial station over the band
    const chrome = partVerts(this.prop, (mr) => mr === chromeMr);
    // the spinner's meridian over the band: the largest chrome radius per axial bin (the bins hold the spinner's own
    // rows and the cut-out rims), then a least-squares quadratic r(z) through them -- smooth reflections, normals from
    // its slope (review r1 PR1-02: 25 raw samples gave a scalloped, stair-stepped band)
    const NB = 48, zb0 = z0 - 0.004, zb1 = z1 + 0.004;
    const NS = 24, rs = new Float32Array(NS + 1).fill(0);
    for (const m of chrome) for (let i = 0; i < m.xyz.length; i += 3) {
      const x = m.xyz[i], y = m.xyz[i + 1], z = m.xyz[i + 2];
      const ax = x * a.x + y * a.y + z * a.z;
      const k = Math.round((ax - zb0) / (zb1 - zb0) * NS);
      if (k < 0 || k > NS || Math.abs(ax - (zb0 + k * (zb1 - zb0) / NS)) > 0.003) continue;
      const r = Math.hypot(x * e1.x + y * e1.y + z * e1.z, x * e2.x + y * e2.y + z * e2.z);
      if (r > rs[k]) rs[k] = r;
    }
    // normal equations of r = c0 + c1 u + c2 u^2, u = (z - zm) / h
    const zm = 0.5 * (zb0 + zb1), hz = 0.5 * (zb1 - zb0), A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], bv = [0, 0, 0];
    for (let k = 0; k <= NS; k++) {
      if (!rs[k]) continue;
      const u = (zb0 + k * (zb1 - zb0) / NS - zm) / hz, ph = [1, u, u * u];
      for (let i = 0; i < 3; i++) { bv[i] += ph[i] * rs[k]; for (let j = 0; j < 3; j++) A[i][j] += ph[i] * ph[j]; }
    }
    const det3 = (M) => M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) +
      M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]);
    const D = det3(A);
    const cf = [0, 1, 2].map((c) => (Math.abs(D) > 1e-12 ? det3(A.map((row, i) => row.map((v, j) => (j === c ? bv[i] : v)))) / D : 0));
    if (!(Math.abs(D) > 1e-12)) cf[0] = Math.max(...rs) || 0.24;
    // lifted so that the band clears every sample (a least-squares curve runs up to ~0.5 mm inside the samples; the
    // band must lie outside the still spinner everywhere to hide it and its blade cut-outs, review r2 PR2-01)
    let lift = 0;
    for (let k = 0; k <= NS; k++) {
      if (!rs[k]) continue;
      const u = (zb0 + k * (zb1 - zb0) / NS - zm) / hz;
      lift = Math.max(lift, rs[k] - (cf[0] + cf[1] * u + cf[2] * u * u));
    }
    cf[0] += lift;
    const rFit = (z) => { const u = (z - zm) / hz; return cf[0] + cf[1] * u + cf[2] * u * u; };
    const dFit = (z) => { const u = (z - zm) / hz; return (cf[1] + 2 * cf[2] * u) / hz; };
    const SEG = 160, pos = [], nrm = [], idx = [];
    for (let k = 0; k <= NB; k++) {
      const z = zb0 + k * (zb1 - zb0) / NB, r = rFit(z) + BAND_OFF, dr = dFit(z);
      for (let i = 0; i <= SEG; i++) {
        const t = TAU * i / SEG, c = Math.cos(t), s = Math.sin(t);
        const er = new THREE.Vector3().copy(e1).multiplyScalar(c).addScaledVector(e2, s);
        const p = er.clone().multiplyScalar(r).addScaledVector(a, z);
        const n = er.clone().addScaledVector(a, -dr).normalize();
        pos.push(p.x, p.y, p.z); nrm.push(n.x, n.y, n.z);
        if (k < NB && i < SEG) { const q = k * (SEG + 1) + i; idx.push(q, q + 1, q + SEG + 2, q, q + SEG + 2, q + SEG + 1); }
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
    g.setIndex(idx);
    g.computeBoundingSphere();
    const boot = bootMr[0].base;
    const mat = chromeMr.base.clone();
    mat.name = 'prop_band';
    mat.transparent = true;
    mat.depthWrite = true;           // opaque over its range (feathered ends): hides the disc inside the spinner
    mat.side = THREE.FrontSide;
    this.bandU = {
      ...this.U,
      uPbRing: { value: ring }, uPbZ: { value: new THREE.Vector4(z0 + 0.5 * dz, z1 - 0.5 * dz, z0, z1) },
      uPbBandZ: { value: new THREE.Vector4(zb0, zb1, BAND_FEATHER, 0) },
      // the boot as a metal's F0: its dielectric reflectance (the black rubber's diffuse is negligible)
      uPbBoot: { value: new THREE.Color(0.04, 0.04, 0.04).multiplyScalar(boot.specularIntensity ?? 1).add(boot.color.clone().multiplyScalar(0.25)) },
    };
    patchBand(mat, this.bandU);
    this.band = new THREE.Mesh(g, mat);
    this.band.name = 'prop_blur_band';
    this.bandFit = { cf, zm, hz, zb0, zb1, z0, z1, lift, rs: Array.from(rs) };
  }

  // radial offset of the blades (explode / build fly-in, m): the disc grows, its data shift outward
  setPush(e) {
    if (e === this.push) return;
    this.push = e;
    const s = (this.outerR + e) / this.outerR;
    this.disc.scale.setScalar(s);
    this.discU.uPbScale.value = s;
    this.discU.uPbRad.value.z = e;
  }

  // per animation step: the frame time (follows a longer frame at once, so the smear always covers the step; relaxes
  // over ~6 frames when they get shorter) and the ghost's capped phase advance
  tick(dt, rpm) {
    if (!(dt > 0)) return;
    const d = Math.min(0.12, Math.max(1 / 240, dt));
    this.dt = d > this.dt ? d : this.dt + (d - this.dt) * 0.15;
    const w = rpm * TAU / 60;
    this.ghostPhase = wrapP(this.ghostPhase + Math.min(w * dt, GHOST_STEP * this.period), TAU);
  }

  // pose: sweep, fade, ghost and pitch uniforms; the solid blades / boots fade out as the disc fades in
  apply(rpm, pitchDeg, propAngle, shown) {
    const P = this.period, w = Math.max(0, rpm) * TAU / 60;
    const S = Math.min(P, Math.max(w * T_EYE, STEP_SWEEP * w * this.dt));
    const sDeg = S * 180 / Math.PI;
    const f = shown ? smooth(FADE_DEG[0], FADE_DEG[1], sDeg) : 0;
    // the ghost takes over as the true pattern blurs out (same phase while it moves less than GHOST_STEP a frame)
    const g = GHOST * smooth(0.55 * P, P, S);
    if (Math.abs(w * this.dt) <= GHOST_STEP * P * 1.0001) this.ghostPhase = wrapP(propAngle, TAU);
    const B = this.U.uPbBlur.value, G = this.U.uPbGhost.value;
    B.set(S, 0, pitchDeg * Math.PI / 180, f);
    G.set(g, GHOST_SWEEP * P, wrapP(this.ghostPhase - propAngle, P), 0);
    this.disc.visible = f > 0.002;
    if (this.band) this.band.visible = f > 0.002;
    this.fadeChanged = f !== this.fade;
    if (f !== this.fade) {
      const vis = f < 0.998;
      for (const m of this.fadeMats) {
        const tr = f > 0.002;
        if (m.transparent !== tr) { m.transparent = tr; m.depthWrite = !tr; m.needsUpdate = true; }
        m.opacity = 1 - f;
        m.visible = vis;
      }
      // hidden as meshes too: not picked, and their highlight overlays (children) not drawn (PR1-01)
      for (const mr of this.fadeRecs) { mr.blurHidden = !vis; mr.mesh.visible = vis && mr.part.shown; }
      this.fade = f;
      this.model.blurFade = f;
      this.model.syncBlurOverlays();
    }
    // the highlight: on the blades' overlays while they show (Model.syncBlurOverlays), as a tint of the disc after
    const hl = (id) => !!id && (id === 'propeller' || id.startsWith('blade_'));
    const T = this.discU.uPbTint.value;
    if (hl(this.model.selected)) T.set(this.tint.sel.r, this.tint.sel.g, this.tint.sel.b, 0.3);
    else if (hl(this.model.hovered)) T.set(this.tint.hover.r, this.tint.hover.g, this.tint.hover.b, 0.3);
    else T.set(0, 0, 0, 0);
    T.w *= smooth(0.5, 0.7, f);
    // the chrome spinner held still against the spin once the blur is complete; turning with the propeller below
    const hold = f >= 0.998;
    for (const c of this.still) {
      if (hold) {
        this._q.setFromAxisAngle(this.frame.a, -propAngle);
        c.mesh.quaternion.copy(this._q).multiply(c.q0);
        c.mesh.position.copy(c.p0).applyQuaternion(this._q);
      } else if (!c.mesh.quaternion.equals(c.q0)) { c.mesh.quaternion.copy(c.q0); c.mesh.position.copy(c.p0); }
    }
    this.holding = hold;
    const st = this.state;
    st.fade = f; st.sweepDeg = sDeg; st.ghost = g; st.visible = this.disc.visible; st.dt = this.dt; st.still = hold;
  }
}

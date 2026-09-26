// Materials: the photo-calibrated lookdev values (viewer/materials.json, a copy of
// render/lookdev_materials.json) turned into MeshPhysicalMaterial at load, plus the shader patches the
// viewer layers on top of any material:
//   paint   primer -> livery sweep along Z (the build's "spray" wipe, nose to tail)
//   lining  back faces (the inside of the single-sided, outward-wound skins, seen through the glazing or
//           in the cutaway) render as a neutral interior lining instead of paint
//   glass   premultiplied glass: reflections are added on top of the tinted see-through, so a dark
//           pane mirrors the studio instead of turning grey; back faces (the view from inside) nearly
//           clear, or dim tinted while the camera is outside a closed cabin (U.cabinClosed)
//   cabin   interior light: IBL x cabinAO, key light x cabinAO^2 on the interior parts / linings and the
//           skins' back faces (no occlusion in the image-based light; Model.updateCabin sets it by viewpoint)
//   collar  station-dependent colour (the heat-blackened exhaust outlet), see render_collar; with render_polish
//           also the hand-polished waviness of the stacks (streaky roughness / tint noise + a small bump)
//   back    a material's own back-face colour (render_back_faces: the sooty inside of the exhaust stacks; the nose-gear
//           lamp's dark LED face behind its clear lens, drawn opaque)
//   grooves the tyres' circumferential tread grooves (render_grooves), in the mesh's own frame about the wheel axis
// Patch flags live in material.userData.pc12 (JSON-able, so Material.clone() keeps them) and are
// (re)installed with installPatch().
import * as THREE from 'three';

// Uniforms shared by every patched material (one write updates all of them).
export const U = {
  paintSweep: { value: 100 },
  primer: { value: new THREE.Color(0x9fae8c) },       // light grey-green zinc-chromate-ish primer
  lining: { value: new THREE.Color() },                // set from LINING below (linear)
  liningRough: { value: 0.72 },
  // "cabin occlusion": the image-based light has no shadowing, so the inside of the fuselage (lining on
  // the skins' back faces, flight deck, cabin) would be lit like the outside.  Scaled down while the skin
  // is closed; 1 in the cutaway / X-ray / explode, where the interior is opened to the studio.  See CABIN.
  cabinAO: { value: 0.05 },
  // 1 = the camera is outside a closed fuselage: glazing seen from inside (the far-side panes, through a
  // near window) renders as dim tinted glass, as the unlit cabin does in the photos and the Cycles
  // renders, instead of letting the studio shine straight through the cabin.  0 = clear from inside.
  cabinClosed: { value: 1 },
  glassDim: { value: 0.82 },           // alpha of those far-side panes
};
// cabin light by viewpoint (Model.updateCabin): outside a closed skin (the studio HDRI's softboxes make
// the unoccluded irradiance ~4x a real cabin's; 0.05, re-checked with the light theme's hangar grade at exposure 1.9:
// the seats read dark grey under the windshield's strip reflections, as in photo 130) / a door open / camera inside
// (eye adapted) / opened up
export const CABIN = { outside: 0.05, door: 0.45, inside: 0.8, open: 1 };

// Interior lining on the back faces.  The lookdev renders use a light grey (0.55) that Cycles darkens
// with real occlusion; the viewer's image-based light has none (a back face inside the cockpit sees the
// whole studio), so a darker neutral reads the same through the tinted glazing.
export const LINING = [0.2, 0.2, 0.195];
U.lining.value.setRGB(...LINING);

// Materials whose back faces are the aircraft interior (jamb: the door / hatch reveals, whose back faces outline the
// exit hatch and the airstair frame from inside the cabin).
const LINING_RE = /^(paint_|trim_black$|seal|jamb$)/;
// Parts inside the closed fuselage (cabin occlusion applies to all their faces), and materials that
// only ever face the cabin (the door / hatch inner linings).
export const INTERIOR_PARTS = new Set(['flight_deck', 'cabin_interior']);
const INTERIOR_MATERIALS = new Set(['lining', 'jamb']);
const PAINT_RE = /^(paint_|trim_black$)/;
// premultiplied glass (reflections on top of the see-through); the cabin glazing also gets the view-from-inside path
// (U.cabinClosed / U.glassDim), a light lens does not (its back face is the lamp, see VIEWER.lens)
const GLASS_RE = /^(glass|lens$)/;
const CABIN_GLASS_RE = /^glass/;

// Viewer-only extras for materials the lookdev table does not cover (emissive displays, position lights).  The
// lights are off, as in every reference photo: glossy coloured lenses; setLights(true) switches them on.
const EXTRAS = {
  screen_pfd: { emissive: [0.018, 0.05, 0.1] },
  screen_mfd: { emissive: [0.018, 0.05, 0.1] },
  screen_sdu: { emissive: [0.018, 0.05, 0.1] },
  light_red: { color: [0.35, 0.01, 0.01], roughness: 0.1, light: [0.6, 0.02, 0.02] },
  light_green: { color: [0.01, 0.3, 0.05], roughness: 0.1, light: [0.02, 0.5, 0.1] },
  light_white: { color: [0.55, 0.55, 0.57], roughness: 0.1, light: [0.5, 0.5, 0.5] },
};
const LIGHT_MATS = new Set();

// Switch the position / strobe lights on (emissive) or off (glossy lenses).
export function setLights(on) {
  for (const m of LIGHT_MATS) {
    const x = EXTRAS[m.name];
    if (x && x.light) m.emissive.setRGB(...(on ? x.light : [0, 0, 0]), THREE.LinearSRGBColorSpace);
  }
}

// Viewer overrides on top of the lookdev values (the lookdev renders have ray-traced occlusion and many samples; the
// viewer's image-based light has neither):
//   envMapIntensity  an occlusion stand-in: the tyres, blades, wheels and legs sit under the fuselage / wing, where the
//                    unoccluded white studio made them read ~40 levels lighter than photo 130 / the Blender hangar render
//   specularIntensity also the dielectric F90 in three r160: less grazing sheen on the rubber / satin composite
//   polish           exhaust_polished render_polish: calmer than the lookdev's (whose bump / tint noise reads as blotchy
//                    camouflage at the viewer's sample count), streaks 3x longer along the stack
//   back             render_back_faces for a material the lookdev table leaves out
const VIEWER = {
  tire: { roughness: 0.65, specularIntensity: 0.5, envMapIntensity: 0.85 },
  prop_blade: { specularIntensity: 0.3, envMapIntensity: 0.75 },
  wheel: { envMapIntensity: 0.75 },
  gear_leg: { envMapIntensity: 0.75 },
  exhaust_polished: { polish: { bump: 0.1, tint_mix: 0.12, stretch_x: 1 / 3 } },
  // the nose-gear lamp: a clear lens with nothing modelled behind it; its back face is the dark (switched-off) LED face.
  // Clear: no milky diffuse on the front (the lookdev's light base colour is for its transmission variant)
  lens: { color: [0.02, 0.02, 0.022], back: { base: [0.03, 0.03, 0.035], rough: 0.25, opaque: true } },
};

export async function loadMaterialSpec(url = new URL('./materials.json', import.meta.url)) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json();
}

const lin = (a) => new THREE.Color().setRGB(a[0], a[1], a[2], THREE.LinearSRGBColorSpace);

function partOf(o) {
  for (let p = o; p; p = p.parent) if (p.userData && p.userData.part) return p.userData.part;
  return null;
}

// Glass: N reflecting surfaces (laminated windshield 2, double-pane cabin windows 4) reflect
// R = N F / (1 + (N - 1) F) at normal incidence (lookdev build_glass); as an F0 scale over the
// single-surface F.  It goes into specularColor (scales F0 only): three.js r160 also uses
// specularIntensity as F90 for dielectrics, so a scale > 1 there made the panes reflect 3.6x the
// environment at grazing angles (white "pill" windows).
function specularForSurfaces(e) {
  const N = e.surfaces || 1, ior = e.ior ?? 1.5;
  const F = ((ior - 1) / (ior + 1)) ** 2;
  return (N * F / (1 + (N - 1) * F)) / F;
}

// The GLB normals are int8 (KHR_mesh_quantization) on a marching-triangles tessellation: a near-mirror
// clear coat (lookdev 0.03) shows both as ripples in the softbox highlights.  The viewer floors the
// clear-coat roughness so the highlights stay smooth (the Cycles renders hide it with more samples of a
// larger light).
const CLEARCOAT_ROUGH_MIN = 0.1;

// glTF-style PBR entry -> MeshPhysicalMaterial (keeps side / flags of the GLB material)
function physicalFrom(name, e, src) {
  const V = VIEWER[name] || {};
  const bc = e.baseColorFactor || [1, 1, 1, 1];
  const blend = e.alphaMode === 'BLEND';
  const m = new THREE.MeshPhysicalMaterial({
    name,
    color: lin(bc),
    metalness: e.metallicFactor ?? 0,
    roughness: e.roughnessFactor ?? 0.5,
    clearcoat: e.clearcoatFactor || 0,
    clearcoatRoughness: e.clearcoatFactor ? Math.max(CLEARCOAT_ROUGH_MIN, e.clearcoatRoughnessFactor || 0) : 0,
    ior: e.ior ?? 1.5,
    specularIntensity: e.specularFactor ?? 1,
    side: e.doubleSided === false ? THREE.FrontSide : src.side,
    transparent: blend,
    opacity: blend ? bc[3] : 1,
    depthWrite: !blend,
  });
  if (e.specularFactor == null && e.surfaces > 1) m.specularColor.setScalar(specularForSurfaces(e));
  for (const k of ['roughness', 'metalness', 'specularIntensity', 'envMapIntensity']) if (V[k] != null) m[k] = V[k];
  if (V.color) m.color.copy(lin(V.color));
  const pol = polishOf(name, e);
  if (pol && pol.rough) {
    // static stand-in for the lookdev's polish noise (the collar patch adds the noise itself): the middle of the
    // roughness range, and the colour pulled half of tint_mix toward the heat tint (the noise's mean pull)
    m.roughness = 0.5 * (pol.rough[0] + pol.rough[1]);
    const tint = e.render_collar && e.render_collar.tint;
    if (tint) m.color.lerp(lin(tint), 0.5 * (pol.tint_mix ?? 0.3));
  }
  m.vertexColors = src.vertexColors;
  m.flatShading = src.flatShading;
  return m;
}

// lookdev render_polish with the viewer's overrides (VIEWER[name].polish)
function polishOf(name, e) {
  const p = e.render_polish, o = VIEWER[name] && VIEWER[name].polish;
  if (!p || !o) return p || null;
  const q = { ...p, ...o };
  if (o.stretch_x != null) { const st = (p.stretch || [1, 1, 1]).slice(); st[0] *= o.stretch_x; q.stretch = st; }
  return q;
}

// Tyre tread grooves (lookdev render_grooves): n circumferential grooves `width` wide at +-0.1 / +-0.3 of the tread
// (tread = `tread` x the tyre width) on the crown, darkened to `floor` x the rubber and roughened to floor_rough.  The
// wheel axis and centre come from the tyre mesh itself (a surface of revolution: the principal axis of its vertices
// with the distinct variance), in the rest pose (world metres; the GLB's quantised mesh frames are scaled per axis);
// the shader evaluates them at each fragment's rest position (like the collar), so they follow the gear as it retracts.
function groovesFor(geo, g, mw) {
  const P = geo.attributes.position;
  if (!P || P.count < 16) return null;
  const n = P.count, c = [0, 0, 0], v = new THREE.Vector3();
  for (let i = 0; i < n; i++) { v.fromBufferAttribute(P, i).applyMatrix4(mw); c[0] += v.x; c[1] += v.y; c[2] += v.z; }
  c[0] /= n; c[1] /= n; c[2] /= n;
  const C = [0, 0, 0, 0, 0, 0];      // xx xy xz yy yz zz
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(P, i).applyMatrix4(mw); const x = v.x - c[0], y = v.y - c[1], z = v.z - c[2];
    C[0] += x * x; C[1] += x * y; C[2] += x * z; C[3] += y * y; C[4] += y * z; C[5] += z * z;
  }
  // power iteration on (tr I - C) finds the smallest-variance axis (the axle for a tyre wider than it is thick)
  const tr = C[0] + C[3] + C[5];
  let a = [1, 0.1, 0.1];
  for (let it = 0; it < 60; it++) {
    const b = [tr * a[0] - (C[0] * a[0] + C[1] * a[1] + C[2] * a[2]),
      tr * a[1] - (C[1] * a[0] + C[3] * a[1] + C[4] * a[2]),
      tr * a[2] - (C[2] * a[0] + C[4] * a[1] + C[5] * a[2])];
    const l = Math.hypot(...b) || 1;
    a = b.map((x) => x / l);
  }
  // width along the axis, outer radius
  let w0 = Infinity, w1 = -Infinity, R = 0;
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(P, i).applyMatrix4(mw); const x = v.x - c[0], y = v.y - c[1], z = v.z - c[2];
    const t = x * a[0] + y * a[1] + z * a[2];
    w0 = Math.min(w0, t); w1 = Math.max(w1, t);
    R = Math.max(R, Math.hypot(x - t * a[0], y - t * a[1], z - t * a[2]));
  }
  const W = w1 - w0;
  if (!(W > 0.02 && R > 1.5 * W / 2)) return null;
  const mid = 0.5 * (w0 + w1);
  const tread = (g.tread ?? 0.62) * W;
  const at = (g.n ?? 4) === 4 ? [-0.3, -0.1, 0.1, 0.3] : Array.from({ length: g.n }, (_, k) => -0.5 + (k + 0.5) / g.n);
  return {
    c: [c[0] + mid * a[0], c[1] + mid * a[1], c[2] + mid * a[2]], a, R,
    off: at.map((f) => f * tread), hw: 0.5 * (g.width ?? 0.006), rMin: R - 0.25 * W,
    floor: g.floor ?? 0.25, rough: g.floor_rough ?? 0.7,
  };
}

// Replace the GLB materials by name with the lookdev ones (and apply the lookdev's per-part
// reassignments: cabin glass / window rings, grey wheel wells).  Materials missing from the table keep
// their GLB values.  Returns {upgraded, kept} material names for the Specs panel / tests.
export function upgradeMaterials(root, spec) {
  const M = (spec && spec.materials) || {};
  const reassign = new Map();
  for (const r of (spec && spec._model && spec._model.reassign) || []) {
    for (const p of r.parts) {
      if (!reassign.has(p)) reassign.set(p, new Map());
      reassign.get(p).set(r.from_material, r.to_material);
    }
  }
  const made = new Map();      // target name -> material
  const interior = new Map();  // material -> its interior clone
  const upgraded = new Set(), kept = new Set();
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    if (!o.isMesh || !o.material || Array.isArray(o.material)) return;
    const src = o.material;
    const part = partOf(o);
    let name = src.name || '';
    const re = reassign.get(part);
    if (re && re.has(name) && M[re.get(name)]) name = re.get(name);
    const e = M[name];
    let m;
    if (e) {
      m = made.get(name);
      if (!m) { m = physicalFrom(name, e, src); made.set(name, m); }
      upgraded.add(name);
      if (e.render_collar) {
        // station-dependent colour needs the mesh's rest placement: one clone per mesh
        m = m.clone();
        const c = e.render_collar;
        m.userData.pc12 = { ...(m.userData.pc12 || {}), collar: {
          x0: c.x0, blend: c.blend ?? 0.005, tintX0: c.tint_x0 ?? c.x0 - 0.1,
          base: e.baseColorFactor.slice(0, 3), tint: c.tint || e.baseColorFactor.slice(0, 3), cbase: c.base,
          rough0: e.roughnessFactor ?? 0.1, rough1: c.rough ?? 0.45, metal1: c.metallic ?? 0.3, spec1: c.spec ?? 1,
          polish: polishOf(name, e) ? polishSpec(polishOf(name, e), e.roughnessFactor ?? 0.1) : null,
        },
        // rest world matrix (model station = glTF Z), so explode / fly-in moves the collar with the part
        rest: o.matrixWorld.toArray() };
      }
      if (e.render_grooves) {
        const g = groovesFor(o.geometry, e.render_grooves, o.matrixWorld);
        if (g) {
          m = m.clone();       // per mesh: its own axis and rest placement
          m.userData.pc12 = { ...(m.userData.pc12 || {}), grooves: g, rest: o.matrixWorld.toArray() };
        }
      }
      const b = e.render_back_faces || (VIEWER[name] && VIEWER[name].back);
      if (b && m.side === THREE.DoubleSide && !(m.userData.pc12 && m.userData.pc12.back)) {
        // e.g. the sooty inside of the polished exhaust stacks, the lamp face behind the nose-gear lens
        if (m === made.get(name)) { m = m.clone(); made.set(name, m); }
        m.userData.pc12 = { ...(m.userData.pc12 || {}), back: { base: b.base, rough: b.rough ?? 0.8, spec: b.spec ?? 1, opaque: !!b.opaque } };
      }
    } else {
      m = src;
      kept.add(name);
      const x = EXTRAS[name];
      if (x && !src.userData.pc12extras) {
        if (x.color) src.color = lin(x.color);
        if (x.roughness != null) src.roughness = x.roughness;
        if (x.emissive) src.emissive = lin(x.emissive);
        if (x.light) LIGHT_MATS.add(src);
        src.userData.pc12extras = true;
      }
    }
    const f = m.userData.pc12 || (m.userData.pc12 = {});
    if (PAINT_RE.test(name)) f.paint = true;
    if (LINING_RE.test(name) && m.side === THREE.DoubleSide) f.lining = true;
    if (GLASS_RE.test(name) && m.transparent) { f.glass = true; if (CABIN_GLASS_RE.test(name)) f.cabinGlass = true; }
    installPatch(m);
    if (INTERIOR_PARTS.has(part) || INTERIOR_MATERIALS.has(name)) {
      if (!interior.has(m)) interior.set(m, clonePatched(m, { interior: true }));
      m = interior.get(m);
    }
    o.material = m;
  });
  return { upgraded: [...upgraded].sort(), kept: [...kept].sort() };
}

// lookdev render_polish (lookdev.py build_metal): a world-space noise (`scale` per metre, the position multiplied by
// `stretch` first: model x = station = glTF Z, so streaks run along the stack; `detail` octaves) mapped 0.3..0.7 -> 0..1
// that drives the roughness between rough[0] and rough[1], pulls the colour up to tint_mix toward the collar's heat
// tint and bumps the normal (strength `bump`, height = noise x bump_distance metres).
function polishSpec(p, rough) {
  const st = p.stretch || [1, 1, 1], k = p.scale ?? 20;
  return {
    // glTF (X, Y, Z) = model (y, z, x)
    freq: [k * (st[1] ?? 1), k * (st[2] ?? 1), k * (st[0] ?? 1)],
    oct: Math.max(1, Math.min(5, Math.round((p.detail ?? 3) + 1))),
    rough: p.rough || [rough, rough], tintMix: p.tint_mix ?? 0.3,
    bump: p.bump ?? 0, dist: p.bump_distance ?? 0.01,
  };
}

// Value noise + band-limited fBm (octaves finer than about a pixel fade out, so the stacks do not sparkle at a
// distance); pcPolishN in 0..1, mean 0.5.
const GLSL_POLISH = `
float pcHash( vec3 p ) {
  p = fract( p * 0.3183099 + 0.1 ); p *= 17.0;
  return fract( p.x * p.y * p.z * ( p.x + p.y + p.z ) );
}
float pcNoise( vec3 x ) {
  vec3 i = floor( x ), f = fract( x );
  f = f * f * ( 3.0 - 2.0 * f );
  return mix( mix( mix( pcHash( i ), pcHash( i + vec3( 1, 0, 0 ) ), f.x ),
                   mix( pcHash( i + vec3( 0, 1, 0 ) ), pcHash( i + vec3( 1, 1, 0 ) ), f.x ), f.y ),
              mix( mix( pcHash( i + vec3( 0, 0, 1 ) ), pcHash( i + vec3( 1, 0, 1 ) ), f.x ),
                   mix( pcHash( i + vec3( 0, 1, 1 ) ), pcHash( i + vec3( 1, 1, 1 ) ), f.x ), f.y ), f.z );
}
float pcFbm( vec3 p, int oct, float fw ) {
  float a = 0.5, s = 0.0, w = 0.0, fr = 1.0;
  for ( int o = 0; o < 5; o ++ ) {
    if ( o >= oct ) break;
    float k = 1.0 - smoothstep( 0.2, 0.6, fw * fr );
    s += a * k * ( pcNoise( p * fr + float( o ) * 7.13 ) - 0.5 );
    w += a;
    fr *= 2.0; a *= 0.5;
  }
  return 0.5 + s / w;
}
// surface-gradient bump (Mikkelsen 2010, unnormalised screen derivatives: heights in world units).  The height
// steps per pixel (dhx, dhy) are explicit forward differences of the noise, not dFdx( h ): those are constant over
// each 2x2 pixel quad and left the mirror-like highlights stair-stepped.
vec3 pcBump( vec3 pos, vec3 n, float dhx, float dhy, float faceDir ) {
  vec3 sx = dFdx( pos ), sy = dFdy( pos );
  vec3 r1 = cross( sy, n ), r2 = cross( n, sx );
  float det = dot( sx, r1 ) * faceDir;
  vec3 g = sign( det ) * ( dhx * r1 + dhy * r2 );
  return normalize( abs( det ) * n - g );
}
float pcPolish( vec3 p, int oct, float fw ) { return clamp( ( pcFbm( p, oct, fw ) - 0.3 ) / 0.4, 0.0, 1.0 ); }
`;

// ------------------------------------------------------------------------------------ shader patches
const GLSL_COLLAR_VS = 'uniform mat4 uRestM;\nvarying vec3 vRestP;\n';
// back face?  Transparent double-sided materials draw a BackSide pass (FLIP_SIDED defined; gl_FrontFacing is flipped
// there) and then a FrontSide pass; opaque double-sided ones one pass (DOUBLE_SIDED).
const GLSL_BACKFACE = `bool pcIsBack() {
#if defined( FLIP_SIDED )
  return true;
#elif defined( DOUBLE_SIDED )
  return !gl_FrontFacing;
#else
  return false;
#endif
}
`;

export function installPatch(mat, extra = {}) {
  const f = { ...(mat.userData.pc12 || {}), ...extra };
  mat.userData.pc12 = f;
  const { paint, lining, glass, cabinGlass, collar, interior, back, grooves, rest } = f;
  if (!paint && !lining && !glass && !collar && !interior && !back && !grooves) return mat;
  const restP = !!(rest && (collar || grooves));
  const physical = !!mat.isMeshPhysicalMaterial;
  if (glass) {
    // premultiplied output: src = diffuse * a + reflections, dst * (1 - a)
    mat.blending = THREE.CustomBlending;
    mat.blendEquation = THREE.AddEquation;
    mat.blendSrc = THREE.OneFactor;
    mat.blendDst = THREE.OneMinusSrcAlphaFactor;
    mat.blendSrcAlpha = THREE.OneFactor;
    mat.blendDstAlpha = THREE.OneMinusSrcAlphaFactor;
  }
  mat.onBeforeCompile = (sh) => {
    let vs = sh.vertexShader, fs = sh.fragmentShader;
    let fsHead = GLSL_BACKFACE;
    if (paint || restP) {
      // world Z (for the paint sweep) and the rest-pose world position (collar, grooves)
      vs = (paint ? 'varying float vPaintZ;\n' : '') + (restP ? GLSL_COLLAR_VS : '') + vs.replace('#include <project_vertex>',
        `#include <project_vertex>${paint ? '\n  vPaintZ = (modelMatrix * vec4(transformed, 1.0)).z;' : ''}${restP ? '\n  vRestP = (uRestM * vec4(transformed, 1.0)).xyz;' : ''}`);
      if (paint) fsHead += 'varying float vPaintZ;\n';
      if (restP) {
        sh.uniforms.uRestM = { value: new THREE.Matrix4().fromArray(rest) };
        fsHead += 'varying vec3 vRestP;\n';
      }
    }
    if (paint) {
      sh.uniforms.uPaintSweep = U.paintSweep;
      sh.uniforms.uPrimer = U.primer;
      fsHead += 'uniform float uPaintSweep;\nuniform vec3 uPrimer;\n';
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  float paintK = smoothstep(-1.2, 1.2, uPaintSweep - vPaintZ);
  diffuseColor.rgb = mix(uPrimer, diffuseColor.rgb, paintK);`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = mix(0.66, roughnessFactor, paintK);
  metalnessFactor = mix(0.0, metalnessFactor, paintK);`);
      if (physical) {
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  #ifdef USE_CLEARCOAT
    material.clearcoat *= paintK;
  #endif`);
      }
    }
    if (collar) {
      const c = collar, P = c.polish;
      const v3 = (a) => `vec3(${a.map((x) => (+x).toFixed(5)).join(', ')})`;
      fsHead += P ? GLSL_POLISH : '';
      // polish noise once per fragment (colour, roughness and the bump share it)
      const polishN = P ? `vec3 pcP = vRestP * ${v3(P.freq)}, pcDx = dFdx( pcP ), pcDy = dFdy( pcP );
  float pcFw = length( abs( pcDx ) + abs( pcDy ) );
  float pcPolishN = pcPolish( pcP, ${P.oct}, pcFw );\n  ` : '';
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  ${polishN}float colT = smoothstep(${(+c.tintX0).toFixed(4)}, ${(c.x0 - c.blend).toFixed(4)}, vRestP.z);
  float colK = smoothstep(${(c.x0 - c.blend / 2).toFixed(4)}, ${(c.x0 + c.blend / 2).toFixed(4)}, vRestP.z);
  vec3 pcTube = mix(${v3(c.base)}, ${v3(c.tint)}, colT);${P ? `
  pcTube = mix(pcTube, ${v3(c.tint)}, pcPolishN * ${(+P.tintMix).toFixed(3)});` : ''}
  diffuseColor.rgb = mix(pcTube, ${v3(c.cbase)}, colK);`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = mix(${P ? `mix(${(+P.rough[0]).toFixed(3)}, ${(+P.rough[1]).toFixed(3)}, pcPolishN)` : (+c.rough0).toFixed(3)}, ${(+c.rough1).toFixed(3)}, colK);
  metalnessFactor = mix(1.0, ${(+c.metal1).toFixed(3)}, colK);`);
      if (P && P.bump > 0) {
        // height = noise x bump_distance (m); Blender's bump 'strength' blends toward the bumped normal
        fs = fs.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  {
    float dhx = ( pcPolish( pcP + pcDx, ${P.oct}, pcFw ) - pcPolishN ) * ${(+P.dist).toFixed(4)};
    float dhy = ( pcPolish( pcP + pcDy, ${P.oct}, pcFw ) - pcPolishN ) * ${(+P.dist).toFixed(4)};
    normal = normalize( mix( normal, pcBump( - vViewPosition, normal, dhx, dhy, faceDirection ), ${(+P.bump).toFixed(3)} * ( 1.0 - colK ) ) );
  }`);
      }
      if (physical && c.spec1 !== 1) {
        // the collar's specular factor (KHR_materials_specular: F0 and F90)
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  material.specularColor *= mix(1.0, ${(+c.spec1).toFixed(3)}, colK);
  material.specularF90 *= mix(1.0, ${(+c.spec1).toFixed(3)}, colK);`);
      }
    }
    if (grooves) {
      // box-filtered coverage of each groove over the fragment's footprint along the axle (sub-pixel grooves at a
      // distance average out instead of aliasing), crown only
      const g = grooves, v3 = (a) => `vec3(${a.map((x) => (+x).toFixed(6)).join(', ')})`, f6 = (x) => (+x).toFixed(6);
      const cov = g.off.map((o) => `pcGroove += max(0.0, min(pcGt + pcGfw, ${f6(o + g.hw)}) - max(pcGt - pcGfw, ${f6(o - g.hw)}));`).join('\n  ');
      fs = fs.replace('#include <color_fragment>', `#include <color_fragment>
  vec3 pcGd = vRestP - ${v3(g.c)};
  float pcGt = dot(pcGd, ${v3(g.a)});
  float pcGfw = max(0.5 * fwidth(pcGt), 1e-5);
  float pcGroove = 0.0;
  ${cov}
  pcGroove = clamp(pcGroove / (2.0 * pcGfw), 0.0, 1.0) * smoothstep(${f6(g.rMin - 0.01)}, ${f6(g.rMin)}, length(pcGd - pcGt * ${v3(g.a)}));
  diffuseColor.rgb *= mix(1.0, ${f6(g.floor)}, pcGroove);`)
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
  roughnessFactor = mix(roughnessFactor, ${f6(g.rough)}, pcGroove);`);
      if (physical) {
        // the groove floor is a cavity: its sheen is mostly occluded
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  material.specularColor *= mix(1.0, ${f6(g.floor)}, pcGroove);
  material.specularF90 *= mix(1.0, ${f6(g.floor)}, pcGroove);`);
      }
    }
    if (back) {
      const v3 = (a) => `vec3(${a.map((x) => (+x).toFixed(5)).join(', ')})`;
      fs = fs.replace('#include <normal_fragment_begin>',
        `if (pcIsBack()) { diffuseColor.rgb = ${v3(back.base)}; roughnessFactor = ${(+back.rough).toFixed(3)}; metalnessFactor = 0.0;${back.opaque ? ' diffuseColor.a = 1.0;' : ''} }
#include <normal_fragment_begin>`);
      if (physical) {
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  if (pcIsBack()) { material.specularColor = vec3(${(0.04 * back.spec).toFixed(5)}); material.specularF90 = ${(+back.spec).toFixed(3)}; }`);
      }
    }
    if (lining) {
      sh.uniforms.uLining = U.lining;
      sh.uniforms.uLiningRough = U.liningRough;
      fsHead += 'uniform vec3 uLining;\nuniform float uLiningRough;\n';
      fs = fs.replace('#include <normal_fragment_begin>',
        `bool pcLining = pcIsBack();
  if (pcLining) { diffuseColor.rgb = uLining; roughnessFactor = uLiningRough; metalnessFactor = 0.0; }
#include <normal_fragment_begin>`);
      if (physical) {
        fs = fs.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
  if (pcLining) {
    material.specularColor = vec3(0.03);
    material.specularF90 = 1.0;
    #ifdef USE_CLEARCOAT
      material.clearcoat = 0.0;
    #endif
  }`);
      }
    }
    if (lining || interior) {
      sh.uniforms.uCabinAO = U.cabinAO;
      fsHead += 'uniform float uCabinAO;\n';
      fs = fs.replace('#include <aomap_fragment>', `{
    // indirect x AO; the key light is mostly blocked by the closed skin: direct x AO^2
    float pcAO = ${interior ? 'uCabinAO' : 'pcLining ? uCabinAO : 1.0'};
    reflectedLight.directDiffuse *= pcAO * pcAO; reflectedLight.directSpecular *= pcAO * pcAO;
    reflectedLight.indirectDiffuse *= pcAO; reflectedLight.indirectSpecular *= pcAO;
  }
#include <aomap_fragment>`);
    }
    if (glass) {
      // cabin glazing: back faces = the view from inside the cabin: nearly clear, faint reflections (or dim tinted
      // while the camera is outside a closed cabin).  Other glass (a light lens) keeps both sides as they are.
      fs = fs.replace('#include <alphamap_fragment>', `#include <alphamap_fragment>
  float pcInside = ${cabinGlass ? 'pcIsBack() ? 1.0 : 0.0' : '0.0'};
  diffuseColor.a = mix(diffuseColor.a, mix(diffuseColor.a * 0.2, uGlassDim, uCabinClosed), pcInside);`);
      sh.uniforms.uCabinClosed = U.cabinClosed;
      sh.uniforms.uGlassDim = U.glassDim;
      fsHead += 'uniform float uCabinClosed;\nuniform float uGlassDim;\n';
      const out = physical || mat.isMeshStandardMaterial
        ? 'gl_FragColor = vec4(totalDiffuse * diffuseColor.a + totalSpecular * mix(1.0, mix(0.35, 0.6, uCabinClosed), pcInside) + totalEmissiveRadiance, diffuseColor.a);'
        : 'gl_FragColor = vec4(outgoingLight * diffuseColor.a, diffuseColor.a);';
      fs = fs.replace('#include <opaque_fragment>', out);
      // physical: the clear-coat block rewrites outgoingLight after totalDiffuse / totalSpecular (glass has
      // no clear coat, so the output above is complete)
    }
    sh.vertexShader = vs;
    sh.fragmentShader = fsHead + fs;
  };
  // the rest matrix is a uniform: programs are shared
  mat.customProgramCacheKey = () => `pc12:${paint ? 'P' : ''}${lining ? 'L' : ''}${glass ? (cabinGlass ? 'G' : 'g') : ''}${interior ? 'I' : ''}${back ? 'B' + back.base.join('/') + (back.opaque ? 'o' : '') : ''}${collar ? 'C' + JSON.stringify(collar) : ''}${grooves ? 'R' + JSON.stringify(grooves) : ''}`;
  mat.needsUpdate = true;
  return mat;
}

// clone that keeps the patch (Material.clone() drops onBeforeCompile but copies userData)
export function clonePatched(mat, extra = {}) {
  const m = mat.clone();
  return installPatch(m, extra);
}

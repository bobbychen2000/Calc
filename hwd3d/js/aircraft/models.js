// Detailed-model registry (hwd3d Phase 3, M2; new file): ICAO type designator -> glTF model + metadata, loaded once per
// type and shared by every aircraft of that type. Types without a model fall back to the GA placeholder
// (js/aircraft/placeholder.js). Provenance of every file: js/aircraft/models/SOURCES.json.
//
//   MODELS {PC12, SF50}: { url, meta, exclude, note, groundGl, lightAnchors, frame }
//   hasModel(type) -> bool
//   loadModel(type, { fetchFn, keepCpu }) -> Promise<AircraftModel>   (js/aircraft/glb.js convertGLB; cached per type)
//   createAircraft(T, opts) -> DetailedAircraft (type has a model) | GaAircraft     T = dims record (T.type = ICAO type)
//        opts as DetailedAircraft (R, id, colour, lodDist, shadowDist); the detailed drawable shows the placeholder until
//        its model is ready and keeps it if the load fails
//   withModelFrame(T) -> T'   the dims record (js/aircraft/ga_dims.js gaDims) with the layout fields the traffic engine and
//        the ground physics use (xMain, xNose, track, L, span, H) replaced by the detailed model's MEASURED frame, so the
//        body that js/live/ground.js separates and the antenna -> main-gear offset of js/live/traffic.js match the drawn
//        model (fix round 1 of Phase 3a: gaDims places the gear by a class rule, e.g. SF50 nose 0.69 m, wheelbase 0.72 m and
//        track 0.23 m off the model). Synchronous (the frame is a constant here, re-measured and compared with the GLB by
//        tools/models/test_models.mjs); T is returned unchanged for types without a model. Phase 3b wires it.
//   modelDims(type, category) -> withModelFrame(gaDims(type, category)): the replacement for every gaDims call in js/live
//        (fix round 2; Phase 3b)
//   MODEL_LOAD_OPTS(type, { palette = true }) -> the convertGLB options of a registered type (the app, the tests and the
//        import tool use the same ones); palette false = the glb's colour factors as written (dev comparisons, see
//        PAINT_FIT below)
// Node: loadModel needs a fetchFn (e.g. (u) => fs.readFile(fileURLToPath(u))) - tools/models/test_models.mjs reads the
// files directly with convertGLB instead.
import { convertGLB } from './glb.js';
import { DetailedAircraft } from './detailed.js';
import { GaAircraft } from './placeholder.js';
import { gaDims } from './ga_dims.js';

const here = (p) => new URL(p, import.meta.url).href;
// material name -> aircraft material id of the 'acobj' program (js/aircraft/detailed.js ACOBJ_FS): 21 paint / trim (plain glTF material since OD4),
// 22 avionics display (self-lit), 23 cabin / flight-deck interior (occluded). Names as written by pc12/model and the SF50
// builder (pc12/cad material table); anything else keeps id 0 (plain PBR).
// OD4: 24 = glazing (alpha-blended 'glass' class, js/aircraft/glb.js): the 'acglass' program shades it as a thin tinted
// sheet (reflection, the pane's diffuse return at its opacity as three.js shades it - OD4 iteration 2 - and transmission);
// 'clear' lens covers keep 0 (diffuse translucent plastic).
export const AC_MAT = (info) => /^(paint_|trim_)/.test(info.name) ? 21 : /^screen/.test(info.name) ? 22
  : /^(leather|carpet|lining|wood|panel_black|interior|seat|cabin)/.test(info.name) ? 23 : info.cls === 'glass' ? 24 : 0;
// OD4: parts whose every plain material is cabin / flight-deck interior (id 23: lit only through the glazing, js/aircraft/
// detailed.js ACOBJ_FS), whatever the material is called - e.g. pc12's metal_dark seat frames in 'cabin_interior' and the
// panel hardware in 'flight_deck', the SF50's 'cabin_lining' / 'cabin_seats'. Paint (21) and displays (22) keep their ids.
export const AC_PART_INTERIOR = /^(flight_deck|cabin_interior|cabin_lining|cabin_seats|cockpit_interior)$/;
export const AC_PART_MAT = (id, part) => (id === 0 && part && AC_PART_INTERIOR.test(part) ? 23 : id);
export const MODELS = {
  // own work: pc12/ parametric model - the ORIGINAL model of this repository's pc12/ project, pc12/out/pc12.glb copied
  // unchanged (sha256 87731cce..., pc12 @ f097de2; owner request 2026-11-14 "use whatever we had in the past": the hwd3d-side
  // variants fr2 / fr3 of tools/models/pc12/build_pc12_variant.py are retired, the builder stays in the repo unused; its
  // --set=none reproduces this file bit for bit), with provenance (docs/phase3_models.md section 4); the internal primary
  // structure (frames / stringers / spars, 'structure') is left out: it is inside the skins and the pc12 viewer shows it
  // only in X-ray
  PC12: { url: here('./models/pc12.glb'), meta: here('./models/pc12_meta.json'), exclude: ['structure'], note: 'pc12/ parametric model (own work)',
    // origin height = pc12's own ground (glTF Y 0, "ground = 0, static on gear", pc12/CLAUDE.md): pc12 sinks its tyres by a
    // static deflection (pc12/model/gear.py: main axle WL 0.265 vs tyre radius 0.2795 -> 14.5 mm; nose 0.212 vs 0.2225 ->
    // 10.5 mm), so the sourced height 4.26 m and prop clearance 0.32 m hold in the hwd3d frame (fix round 1; it was the
    // tyre bottom, 14.5 mm lower)
    groundGl: 0,
    // wing landing lights: the pc12 model has none (its only lamp is the nose-strut lens, kept as the taxi light). The
    // Pilatus "PC-12 NGX Model Building Plan" p. 4 (https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/
    // PC-12-NGX-Model-Building-Plan.pdf, photo "LANDING LIGHTS") shows a multi-LED lamp in a fairing under the wing beside a
    // flap-track fairing [obs]; the spanwise station is not readable from the close-up, so the anchors sit just inboard of
    // the middle flap-track fairing (pc12 BL 3.30), 4.6 cm below the wing lower surface (WL 1.047 at BL 3.15 / STA 6.20 in
    // pc12/out/pc12.glb, measured 2026-11-14; the retired fr3 build's wing sat 0.15 m higher there) [inf: position].
    // Model axes (x = station, y = butt line, z = water line); sprites only (no lamp geometry: a pc12 owner item).
    lightAnchors: {
      landL: { p: [6.20, -3.15, 1.000], src: 'Pilatus PC-12 NGX Model Building Plan p.4 photo "LANDING LIGHTS" (lamp under the wing beside a flap-track fairing) [obs]; station BL 3.15 / STA 6.20 [inf]' },
      landR: { p: [6.20, 3.15, 1.000], src: 'Pilatus PC-12 NGX Model Building Plan p.4 photo "LANDING LIGHTS" (lamp under the wing beside a flap-track fairing) [obs]; station BL 3.15 / STA 6.20 [inf]' },
    },
    // drawn colour of the navy livery band (OD4 iterations 2-3, review F1 / F2; PAINT_FIT below): linear, fitted so that the band
    // in the HWD world, in sun AND in shade together, looks as in the pc12 viewer [inf: appearance fit]; the glb's own factor is
    // (0.10, 0.17, 0.27)
    paintFit: { paint_accent: [0.035, 0.086, 0.181] },
    // measured frame (convertGLB with the options above; tools/models/test_models.mjs fails if the GLB disagrees by > 5 mm):
    // xMain = nose tip -> main-gear contact, xNose = nose tip -> nose-wheel contact (js/live/ground.js meaning), metres
    frame: { L: 14.400, span: 16.281, H: 4.260, xMain: 6.040, xNose: 2.560, track: 4.530, wheelbase: 3.480,
      basis: 'measured from js/aircraft/models/pc12.glb (= pc12/out/pc12.glb @ f097de2, unchanged) by js/aircraft/glb.js; L / span / H / track / wheelbase agree with pc12/CLAUDE.md sourced facts (14.40, 16.28, 4.26, 4.53, 3.48)' },
  },
  // own work: hwd3d/tools/models/sf50 (procedural, from published dimensions; M1, Phase 3)
  SF50: { url: here('./models/sf50.glb'), meta: here('./models/sf50_meta.json'), exclude: [], note: 'tools/models/sf50 procedural model (own work)',
    groundGl: 0,   // the SF50 builder's ground (z = 0 static on the gear); its tyres touch it (no deflection modelled)
    frame: { L: 9.357, span: 11.793, H: 3.325, xMain: 4.453, xNose: 1.148, track: 3.414, wheelbase: 3.305,
      basis: 'measured from js/aircraft/models/sf50.glb by js/aircraft/glb.js; L / span / H / track from FAA ACD + AFM Fig 1-1 (tools/models/sf50/SF50_FACTS.md), wheelbase read off AFM Fig 1-1 [inf]' },
  },
};
export const hasModel = (type) => !!MODELS[type];
// PAINT_FIT (OD4 iteration 2, review F1 "navy cheatline on any sunlit side"): a registry entry's `paintFit` replaces the
// LINEAR base colour of the named materials at load (the glb bytes are not changed; MODEL_LOAD_OPTS palette false and the
// dev viewer's palette=glb draw the file's factors). PC-12: paint_accent only. Why: pc12/model/assemble.py MATERIALS gives
// paint_accent (0.10, 0.17, 0.27) (glTF: linear) and pc12/model/livery.py calls the band "a navy swoosh" [obs: our pc12
// source]. The pc12 viewer shows it navy because its studio light keeps it in the toe of the ACES curve; in the HWD world's
// direct noon sun (white paint ~230, as in the reference) the same factor read steel blue: (106-117, 126-137, 142-152)
// against the reference's (42-62, 66-90, 92-120) at the same pixels (out/pc12_look_rc1, 5 sunlit cameras). A darker world
// exposure was tried and rejected (dull airport, docs section 15.4). Reading the factor as sRGB-encoded (decoded (0.010,
// 0.025, 0.059), the review's option b) was tried and rejected: sunlit grey-navy (41-55, 51-61, 64-73), shaded band near
// black and neutral (14-20, 18-22, 23-27), and under the pc12 viewer's own light (dev/studio.js) black (1-4, 2-17, 8-39)
// where the reference shows (20-42, 36-66, 54-92) - the pc12 author tuned the palette in that viewer, so the factor is
// not sRGB-typed. Iteration 2 fitted the band in direct sun only ((0.017, 0.059, 0.137)); the review of iteration 2 (F2) found
// the shaded sides then near-black navy. The fitted factor since OD4 iteration 3: per channel, the linear value that
// minimises the squared sRGB error of the band's median against the reference viewer's (pc12/web/dev.html, the n_all.png
// harness) at the same pixels over ALL 11 reference cameras of out/pc12_ref_viewer/cameras.json together (dev/model.html,
// HWD Green Ramp 2026-11-13 12:30 PST: the five starboard hwd_* cameras in sun, the five port cameras in shade, the nose),
// each camera's band interpolated in log factor between renders at five factors on the line from the glb factor to the
// iteration-2 one: (0.035, 0.086, 0.181) [inf: appearance fit, docs section 15.7]. A navy (sRGB #345376 at full
// reflectance; navy paints reflect ~1-15 %) near this repository's SF50 accent (0.025, 0.064, 0.147). No single factor
// matches both sides: the world's direct sun puts ~6x the shade's light on the sunlit side, the pc12 viewer's studio ~2-3x,
// so the band stays a little lighter than the reference in sun and darker in shade (docs section 15.7). The decision belongs
// to the pc12 owner, who may retune pc12's palette - then this entry goes. Other pc12 factors are kept as written (white,
// belly, the gold pin-stripe: they read as in the reference in sun and shade, docs section 15.6). Comparisons under the pc12
// viewer's own light (dev look=studio) need palette=glb (the file's factor) since iteration 2.
export function paletteLook(e) {
  const fit = e && e.paintFit; if (!fit || !Object.keys(fit).length) return undefined;
  return (info) => (fit[info.name] ? { base: [...fit[info.name].slice(0, 3), info.base[3]], baseGlb: info.base.slice(), palette: 'paint-fit' } : null);
}
export const MODEL_LOAD_OPTS = (type, { palette = true } = {}) => { const e = MODELS[type]; return e ? { name: type, exclude: e.exclude, groundGl: e.groundGl, lightAnchors: e.lightAnchors, matId: AC_MAT, partMatId: AC_PART_MAT, look: palette ? paletteLook(e) : undefined } : null; };

// dims record -> the same record with the detailed model's measured layout (see the header). The antenna offset T.ant
// (GNSS antenna behind the nose, class rule) is kept as a distance from the nose; with xMain from the model, the antenna ->
// main-gear offset xMain - ant becomes the model's. The original record stays reachable as T'.dimsBase.
const FRAMED = new WeakMap();
export function withModelFrame(T) {
  const e = T && T.type && MODELS[T.type]; if (!e || !e.frame) return T;
  if (FRAMED.has(T)) return FRAMED.get(T);
  const f = e.frame;
  const out = Object.freeze({ ...T, L: f.L, span: f.span, H: f.H, xMain: f.xMain, xNose: f.xNose, track: f.track,
    dimsBase: T, frameSrc: 'model', frameBasis: f.basis,
    dimSrc: Object.assign({}, T.dimSrc || {}, { proportions: 'model (measured from the detailed model)' }),
    provenance: [...(T.provenance || []), `gear / length layout from the detailed ${T.type} model (js/aircraft/models.js frame): ${f.basis}`] });
  FRAMED.set(T, out); return out;
}

// the one call Phase 3b puts in place of EVERY gaDims(type, category) call in js/live (fix round 2: js/live/traffic.js has two,
// the live-track one and the localStorage parked-aircraft restore; the fix-round-1 diff named only the first, which would
// have left a restored parked SF50 on the class-rule layout - xMain 0.69 m, track 0.23 m off). tools/models/test_models.mjs
// lists every gaDims( call in js/live and fails while docs/phase3_models.md's diff does not cover each one.
export function modelDims(type, category) { return withModelFrame(gaDims(type, category)); }

const CACHE = new Map();
const defaultFetch = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(`${u}: HTTP ${r.status}`); return r.arrayBuffer(); };
export function loadModel(type, { fetchFn = defaultFetch, keepCpu = false, palette = true } = {}) {
  const e = MODELS[type]; if (!e) return Promise.reject(new Error('no detailed model for ' + type));
  const key = palette ? type : type + ':glb-palette';   // palette false: the glb's colour factors as written (dev viewer palette=glb)
  if (!CACHE.has(key)) CACHE.set(key, (async () => {
    const [buf, meta] = await Promise.all([fetchFn(e.url), fetchFn(e.meta).then(b => JSON.parse(new TextDecoder().decode(b))).catch(() => null)]);
    // keepCpu false (the app): js/aircraft/detailed.js drops the vertex / index arrays once they are on the GPU (~21 MB of
    // JS heap per type); the dev viewer and the tests keep them
    const m = convertGLB(buf, MODEL_LOAD_OPTS(type, { palette })); m.meta = meta; m.type = type; m.keepCpu = !!keepCpu; return m;
  })());
  const p = CACHE.get(key); p.catch(() => CACHE.delete(key)); return p;
}
export function createAircraft(T, opts = {}) {
  const type = T && T.type;
  if (type && MODELS[type]) return new DetailedAircraft(T, { ...opts, model: loadModel(type, opts) });
  return new GaAircraft(T, opts);
}

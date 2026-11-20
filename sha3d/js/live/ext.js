// sha3d extension registry (new). The four parallel packages (markings, gates, terminals, relay) each own ONE file and
// plug into the core through one call, so nobody edits world.js / app.js lines another package edits:
//
//   js/live/markings.js   registerExtension({ name: 'markings', ... })   CAAC MH 5001-2021 markings (+ signs)
//   js/live/gates.js      registerExtension({ name: 'gates', ... })      stands, jet bridges, VDGS, GSE
//   js/live/terminals.js  registerExtension({ name: 'terminals', ... })  T1 / T2 / tower / hangars (replaces placeholders)
//   js/live/relay.js      RELAY config + detectRelay() (imported by entry.js; not an extension)
// js/live/entry.js imports the three extension files before startApp (one import line each, already present).
//
// Extension object (every member optional except name):
// {
//   name: 'markings',                 // unique; a second registration with the same name replaces the first
//   order: 10,                        // build order (lower first); core placeholders are built before any extension
//   shaderChunks: { sha_ground_paint: `...glsl...` },
//                                     // gl.js defineChunk() overrides applied before the world compiles its programs.
//                                     // 'sha_ground_paint' = the ground-shader paint hook (js/shaders/ground.js has the
//                                     // signature); extra uniforms for it go in groundUniforms below
//   groundUniforms: (ctx) => ({ uMyTex: tex, ... }),
//                                     // merged into the ground program's uniforms (after ctx.R / textures exist)
//   pavement: (api, airport) => {},   // paint extra pavement into the airfield map before it is uploaded:
//                                     //   api.fill(rings, kind) / api.line(pts, widthM, kind), kind 'paved' | 'concrete' |
//                                     //   'apron' | 'shoulder'; rings / pts in world [x, z]
//   claimBuildings: (airport) => ['osm:way/93184730', 'tower', ...],
//                                     // building ids the extension draws itself: the core placeholder skips them
//                                     // ('tower' = the generic control-tower stand-in)
//   buildWorld: async (ctx) => ({ items: [...], sprites: [...], gates: [...], anchors: {...}, info: {...} }),
//                                     // static geometry: renderer items ({mesh, prog, model, uniforms, bbox, castShadow,
//                                     // ...}, see sfo3d CLAUDE.md "Items passed to the renderer"); register programs with
//                                     // ctx.R.addProgram(name, VS, FS). sprites = static light sprites; anchors merge into
//                                     // world.anchors (e.g. {tower: {pos, eyeY}}); gates = stand objects for the app
//   start: (app) => {},               // after the scene exists: app = window.SHA (R, scene, world, rig, ui, qa, env ...);
//                                     // e.g. scene.gateSys = mySystem (its items(nowMs) are drawn every frame)
//   frame: (t, app) => [] ,           // optional per-frame extra items
//   lights: (t, app) => [],           // optional per-frame light sprites ({p, c, i, s})
// }
// ctx passed to buildWorld: { R, airport, stands, taxigraph, geo (js/geo.js module), groundY, quality, ground (maps,
// pavedAt), log, addItems(items) }.
const REG = new Map();
export function registerExtension(ext) {
  if (!ext || !ext.name) throw new Error('registerExtension: name required');
  REG.set(ext.name, ext);
  return ext;
}
export function extensions() { return [...REG.values()].sort((a, b) => (a.order ?? 50) - (b.order ?? 50)); }
export function extension(name) { return REG.get(name) || null; }

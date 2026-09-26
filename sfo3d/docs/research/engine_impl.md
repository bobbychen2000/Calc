# three.js r186 renderer for SFO Live 3D: implementation notes (live3.html)

Status: 26 Sep 2026 (UTC), after review round 1 (§4.3). Decision record: `docs/research/engine.md` (verified). This note records how the port is
built, what was checked in this sandbox, and what is still open. Labels: **Observed** (run or read here), **Inferred**.

## 1. What it is

`live3.html` is the same app as `live.html` on a new renderer: three.js r186 `WebGPURenderer` (WebGPU where the browser
has it, automatic WebGL 2 fallback), TSL node materials, `CSMShadowNode` cascades, GTAO, TRAA (MSAA off), AgX,
PMREM image-based lighting from our own sky model, and an offline MSDF sign atlas. `live.html` and its renderer are
untouched.

```
python3 -m http.server 8000     # repo root
http://localhost:8000/live3.html?mode=snapshot          # recorded snapshot
http://localhost:8000/live3.html                        # live (relay auto-detected via /api/ping, as live.html)
  ?tier=high|medium|low   force a quality tier (default: the old app's choice: phones low, <=4 GB medium, else high)
  ?webgl=1                force the WebGL 2 backend       ?revz=0   no reversed depth buffer
  ?res=1                  render at canvas size x DPR (QA renders; the app's dynamic resolution is ignored)
  ?sat= ?contrast= ?lookSat= ?vignette= ?expo=   grade overrides (defaults 1.0 / 1.8 / 1.0 / app 0.18 / 1.0)
```

QA harnesses (same mock relay and snapshot as `jobs/qa3.mjs`):

```
SOFTGL=1 W=960 H=540 OUT=out/engine PAGES="live3.html,live.html" \
  VIEWS="view:overview;gate:B26,60,1,14;hold:12;tower;thr:28R" node livetest.mjs tools/build3/job_views.mjs
# -> out/engine/new_<view>.png (three.js), out/engine/old_<view>.png (current renderer)
SOFTGL=1 W=960 H=540 OUT=out/engine2 PAGE="live3.html?tier=high" HDR=1 node livetest.mjs tools/build3/job_review.mjs
# -> review views (day, dusk, night) + per-frame metrics + HDR dumps; python3 tools/build3/grade_hdr.py grades dumps offline
SOFTGL=1 PREV=out/three_prev.js node livetest.mjs tools/build3/job_ghost.mjs     # TRAA disocclusion A/B (§4.3)
node tools/build3/wgpu_run.mjs tools/build3/job_dev.mjs                          # dev pages on WebGPU (SwiftShader)
```

## 2. How the app runs unchanged (import-map module swap)

The app (`js/live/entry.js` -> `app.js`), traffic, physics, gates, UI, camera rig, `SFO.qa` hooks and all geometry
builders are imported as they are. `live3.html`'s import map swaps four renderer-facing modules:

| Module the app imports | Replaced by | What the stand-in does |
|---|---|---|
| `js/gl.js` | `js/three/compat/gl.js` | Records instead of uploading: `new Mesh(data)` keeps the typed arrays, `texture()` / raw `gl.tex*` calls keep pixels or a copy of the image source (the builders close/shrink their sources right after upload). `initGL(canvas)` hands the app's canvas to three.js. Unknown `gl.*` calls are no-ops. |
| `js/renderer.js` | `js/three/compat/renderer.js` -> `js/three/renderer3.js` | The old `Renderer` interface (`setupSky`, `light`, `extraCommon`, `render`, `present`, `resize`, `curCam`) on top of three.js. |
| `js/scene.js` | `js/three/compat/scene.js` | Aircraft list, light-sprite collection (same order as the old `Scene.frame`), per-frame hook for bridges/GSE/aircraft. |
| `js/world/world.js` | `js/three/compat/world.js` | Re-exports the original, except `bakeGround` -> TSL bakes (`js/three/ground.js`). |

A scope for `/js/three/` maps `js/renderer.js` and `js/world/world.js` back to the originals so the new modules can
import `sunTransmittance`, `CITY_RECT` etc. `tools/build3/build.mjs --app` applies the same swaps for a one-file
bundle (`out/build3/live3.bundle.js`; set `window.SFO_ASSET_BASE = 'js/three/assets/'` when serving it).

Consequence: the real-time, stands, liveries and traffic workflows' changes to those modules show up in live3.html
without any port work, as long as `app.js` keeps its renderer calls (listed in `docs/requests/engine_exports.md` §1).

## 3. Module map (js/three/)

| File | Content | Ported from |
|---|---|---|
| `engine.js` | `WebGPURenderer` (reversed depth), camera, sun + `CSM3` (CSMShadowNode with a per-cascade slope-scaled bias, normal offset 1.25 texels per cascade, PCF with a per-frame rotated tap pattern so TRAA averages it), post: depth/normal/velocity pre-pass -> GTAO (4 m radius, temporal noise rotation, into the ambient term via `builtinAOContext`) -> lit pass -> TRAA -> + light-sprite pass (after TRAA, un-jittered camera) -> exposure -> bloom (all tiers; threshold in exposed units, soft luminance clamp) -> AgX with a look (contrast 1.8 in log2 around 18 % grey, look saturation 1.0) -> saturation -> vignette -> sRGB -> dither/grain. Low tier: one MRT pass, half-res GTAO multiplied into colour, TRAA, same output chain. Registers the floodlight light node. | `js/renderer.js`, `js/shaders/post.js` |
| `flood.js` | Apron floodlights as a light: CPU field of the 70 observed masts (vector irradiance + horizontal spread, RGBA16F over the masts' box, calibrated to the ICAO 20 lux stand average; lamp units, x `LAMP_M` in the scene, §4.5) and `FloodLightNode` (a three.js analytic light node sampling it per pixel). | new (review round 1) |
| `sky.js` | Rayleigh/Mie single-scattering sky (same constants/steps), sun disk, cirrus, METAR cloud layer, low overcast slab, ENV composition -> PMREM (GGX-prefiltered IBL, ground below the horizon = the airfield bake's mean albedo x irradiance), `skyAlong(ro, rd)` (the visible sky from any point: background and water reflections), night floor with a warm horizon glow (lamp units, §4.5), twilight multiple-scattering term below the horizon (§4.5), exponential height fog with Mie glow as `scene.fogNode`; ambient terms computed on the CPU so `setupSky` stays synchronous. | `common.js` SKY_PRECOMPUTE_FS, `env.js` SKY_FS / ENV_FS / CLOUD_FS, `renderer.js setupSky` |
| `ground.js` | Airfield / aux / city bakes (tiles of <= 1024² texels, a few per frame, NoBlending so the coverage alpha survives), ground material with the SDF runway markings (thresholds, designations from the glyph atlas, TDZ, aiming point, displaced-threshold arrows, blast-pad chevrons, rubber), concrete joints, city street lights at night (energy-conserving far away; the apron floodlights are `flood.js`); water with wind-driven wave slopes and roughness, IOR 1.333 Fresnel, its sky reflection = `skyAlong` from the water point, foam at the seawall. | `js/shaders/ground.js`, `env.js` WATER_FS |
| `markings.js` | Taxiway/hold/edge/road ribbons and stand lead-ins/red boxes with a minimum 1.2 px width measured on the projected perpendicular (foreshortening-aware, on the unit perpendicular: the miter length at joints no longer blows corners up) and area-correct alpha, anti-aliased dashes averaging to their duty ratio far away. | `js/live/markings.js` MARK_VS/FS |
| `objects.js` | PBR object material (MeshPhysical: IOR per material id) for terminals, tower, ITB, garages, masts, EMAS, piers, bridges, stand equipment, GSE: the 14 procedural material ids (curtain wall = coated glass IOR 2.0 over parallax rooms with per-pane roughness / normal variation, panels, garage, corrugated metal, roofs, windows, foliage, tunnel ribs, garage-roof cars, tower cab glass and LED ribbon = coated glass, hangar door, lamp lenses, service facade), vehicle tint. | `js/shaders/objects.js` |
| `signs.js` | Hold / location / painted / distance-remaining / gate / stand / VDGS faces rebuilt as panel + MSDF glyph quads (sharp at any distance); faces found by the UV rectangle the existing builders emit. Fallback when the font fails: the builders' own quads with their canvas atlas (`atlasSignMaterial`). | `js/live/signs.js` makeAtlas styles |
| `bridges.js` | Converts `LiveGateSystem.items()` (batched static bridges + stand equipment, per-frame mesh of the moving bridges only, sign quads, GSE instances -> `InstancedMesh` per vehicle type). Bridges and GSE do not wait for the sign font; sign faces follow when it arrives (or from the atlas fallback). | uses `js/live/gates.js` as is |
| `aircraft.js` | Imported models: paint zones recoloured by livery, clear-coat paint, glass as a smooth clear-coat layer with warm cabin light at night, bare metal, lenses, gear collapse; procedural airframes (windows, doors, flight-deck panes, fin, engines); per-aircraft uniforms (`onObjectUpdate`) so each model is one program; brand x model livery textures as loaded by `LiveAircraft` (`ac.livTex`, js/aircraft/liveries.js) on the atlas draws, atlas alpha = painted cabin-window glass. | `js/shaders/aircraft_real.js`, `aircraft.js` |
| `lights.js` | All light sprites in one instanced additive draw in their own pass after TRAA (directional lobes, 2.2 px minimum with energy conservation, 12 px maximum, halo capped in exposed units, x0.5 by day, x `lampK` (§4.5), markers fade out within 150 m; occlusion by the scene depth per fragment). | `js/shaders/sprites.js` |
| `convert.js`, `tsl/common.js` | Record -> BufferGeometry/Texture (image textures from non-premultiplied ImageBitmap copies, uploaded at once and released: `compat/gl.js` snapshot / `imageHooks`); hashes, value noise, fbm, `band()`, viewer-facing normals, the shared `lampK` uniform. | `common.js` noise chunk |
| `assets/msdf_signs.*` | Offline MSDF atlas (Liberation Sans/Mono Bold, SIL OFL), `tools/build3/msdf_atlas.py`; `build.mjs --app` copies it next to the bundle. | — |
| `dev/*.html`, `dev/ghost.js` | Dev pages: `envtest` (`?night=1` floodlights, `?sprites=1` light pass), `shadowtest` (`?eng=nobias` etc.), `ghosttest` (TRAA A/B), `actest`, `marktest`, `probe`. | — |

## 4. Observed in this sandbox (headless Chromium 141, Mesa llvmpipe via `SOFTGL=1`, 4 vCPU shared)

- `navigator.gpu` exists but no adapter: "Failed to create WebGPU Context Provider"; three.js logs "WebGPU is not
  available, running under WebGL2 backend". **The WebGPU backend could not be exercised here**; the WebGL 2 fallback
  runs everything. `EXT_clip_control` is present, so the reversed depth buffer is active (near 0.25 m to far 180 km in
  one depth range, replacing the old two-range depth).
- Start-up: bakes and scene assembly take 10-30 s here; the first frames take tens of seconds each while llvmpipe
  compiles the programs (`compileAsync` is used to compile the scene's programs before the first frame). Frame times
  on llvmpipe say nothing about a phone GPU (**Unverified**: phone frame rate; test on the owner's iPhone, phase 0 of
  engine.md §8.2).
- Per-frame draw calls (`info.render.drawCalls`, every pass incl. shadows and post; `debugInfo()`), 26 Sep 2026,
  snapshot mode with the mock relay: high tier overview 513 (4.0 M triangles, terrain dominates), gate B26 517-525,
  tower ~800, threshold 28R 453, hold 12 646, UAL close-up 617-619; at night (no sun shadows) 284-406. Low tier:
  tower 322 (2.0 M triangles). (The 25 Sep figures "~800 at the overview, low 361, high ~2000" were
  `info.render.calls`, a counter of render() calls since start-up, not a per-frame figure: review round 1.)
- Texture memory (`info.memory.texturesSize`, incl. render targets): high 982-1062 MB, low 501 MB with 45 aircraft in
  snapshot mode; CPU-side image copies retained after upload: 0 MB (was 232-374 MB, §4.3).

### 4.1 Fixes found on 25 Sep 2026 (both invisible in the 24 Sep renders' numbers, obvious in the images)

- **No cast shadows.** `sun.shadow.bias = -0.0003` is a depth-space bias; for `CSMShadowNode` each cascade camera's
  depth range is hundreds of metres (the 600 m light margin), so the bias moved shadows metres away from their casters
  and on the airport scale they vanished. Isolated with `js/three/dev/shadowtest.html` (plain / reversed / CSM /
  pipeline variants all cast; only the Engine's bias did not). Now `bias = 0`, `normalBias = 0.2` m.
- **GTAO blackened everything not lit by the sun** (terminal walls, back-lit fuselages). three r186 `GTAONode` assumes
  a standard depth buffer (`getViewPosition` maps depth*2-1 on WebGL, depth >= 1 = sky); with the reversed depth
  buffer every pixel read as fully occluded. Fix (`engine.js aoInputs`): a full-screen pass re-encodes the reversed
  depth as standard depth (float, nearest) and GTAO gets a proxy camera with the same frustum and a standard
  projection. Verified with `js/three/dev/envtest.html` (sky + PMREM IBL + CSM + GTAO + spheres, a building and two
  aircraft): with `?revz=0`, with `?ao=0` and with the fix the back-lit sides match. Precision note (**Inferred**): the
  standard depth is float32; at 1 km the reconstructed position is good to ~0.25 m, enough for the 2.2 m AO radius.
- **Liveries**: the brand x model textures are now taken from `LiveAircraft.livTex` (see §3); the old manifest loader
  was removed. Neutral skins (`ac._livNeutral`) keep the zone recolouring; freighter brands get painted-over window plugs
  (ACR_FS `uNoCabin`, docs/requests/liveries_windows.md). Checked in envtest (UAL 2019 on the 737-800 model, FedEx 757).
- **Grade**: saturation 1.2, contrast 1.5 (was 1.1 / 1.35): side by side, the AgX image read flat at distance.
  (Superseded by review round 1: §4.4.)

Dev pages (open through the harness: `DEV="js/three/dev/envtest.html?cz=-110&cx=10&cy=12" node livetest.mjs
tools/build3/job_dev.mjs`): `shadowtest.html` (`?eng=none,plain,practical,nofade,oldbias`), `envtest.html` (`?el=`,
`?az=`, `?tier=`, `?ao=0`, `?env=0`, `?revz=0`, camera `cx/cy/cz`), `actest.html` (aircraft materials), `marktest.html`.

### 4.2 Side-by-side renders, 25 Sep 2026 (960x540, snapshot + mock relay, SOFTGL=1)

`out/engine/cmp_<view>.png` = `old_<view>.png` (live.html) | `new_<view>.png` (live3.html, tier high) for
`view_overview`, `gate_B26_60_1_14`, `hold_12`, `tower`, `thr_28R`; `new_tier_low_<view>.png` and
`cmp_tier_low_grid.png` for the phone tier. Logs: `out/engine/run.log` (both renderers), `out/engine/run2.log` (live3.html
high + low after the grade change). Observed:
- Luminance normalised cross-correlation old vs new (ground region for hold/threshold): hold 0.970, threshold 28R 0.984,
  gate 0.970, tower 0.957, overview 0.959; new is 4-14 sRGB levels brighter on average (AgX + grade vs the old ACES fit).
  The SDF runway markings (threshold bars, 28R designation, arrows, hold bars, `10L-28R` surface sign) are in the same
  places and sharper in the new renderer.
- Cast shadows from bridges, aircraft, buildings, masts and GSE now match the old renderer's; GTAO adds contact shading
  (parapets, under-wing, bridge cabs); the MSDF gate signs (B27) stay sharp where the old atlas blurs.
- Differences that are not the renderer: cloud shadows and aircraft positions follow the mock clock (each page loads at
  a different time), and the brand livery texture arrives asynchronously, so an aircraft can show the zone colours in one
  render and the baked brand texture in another (B25 in `cmp_gate_B26_60_1_14.png`). The liveries workflow was
  re-baking `data/liveries/**` during these runs.
- Start-up to the first complete frame: 360-500 s for both pages under llvmpipe with other agents on the CPU (the old
  page takes as long; the time goes into the app's model decoding and first-frame program compiles, not the bakes).
- Low tier (single MRT pass, 2 cascades x 1024²) renders all views. (The draw-call figures once quoted here were the
  cumulative `info.render.calls`; per-frame figures are in §4.)

## 5. Quality tiers (`engine.js QUALITY3`)

| Tier | Chosen for | Shadows | AO | AA | Bloom | Bakes (m/texel) |
|---|---|---|---|---|---|---|
| high | desktop, > 4 GB | 3 cascades x 2048² | GTAO from a pre-pass, half res | TRAA | yes | airfield 0.8, city 4096² |
| medium | <= 4 GB | 3 x 2048² | same | TRAA | no | 1.0, 4096² |
| low | phones | 2 x 1024² | GTAO half res from the MRT normal of the single pass | TRAA | no | 1.25, 2048² |

## 6. Not ported yet / known gaps

- `decal` items (stand centrelines; off by default in `js/live/world.js`) are not drawn.
- Smoke particles (`scene.smokeFns`, unused by the live app) are not drawn.
- The low tier's single-pass GTAO is applied to the lit colour (the high/medium tiers apply it to the ambient term only).
- Aircraft `.sfom` -> `BufferGeometry` directly; the `.glb` + KTX2 path (engine.md §5) is not done.
- WebGPU backend untested (see §4); the GTAO depth re-encode (§4.1) is written for both coordinate systems but only
  exercised on WebGL 2.
- Roof parapets get a thin dark GTAO line at 100-300 m (tower view): plausible contact shading, maybe strong; to be
  judged by the adversarial reviewer against photos.
- Blender (tools/blender/): Cycles reference renders and baked-AO aircraft assets not started.

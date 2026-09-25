# three.js r186 renderer for SFO Live 3D: implementation notes (live3.html)

Status: 25 Sep 2026 (UTC). Decision record: `docs/research/engine.md` (verified). This note records how the port is
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
  ?sat= ?contrast= ?expo= grade overrides (defaults 1.2 / 1.5 / 1.0)
```

QA harness (same mock relay and snapshot as `jobs/qa3.mjs`; renders both renderers in one browser session):

```
SOFTGL=1 W=960 H=540 OUT=out/engine PAGES="live3.html,live.html" \
  VIEWS="view:overview;gate:B26,60,1,14;hold:12;tower;thr:28R" node livetest.mjs tools/build3/job_views.mjs
# -> out/engine/new_<view>.png (three.js), out/engine/old_<view>.png (current renderer)
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
| `engine.js` | `WebGPURenderer` (reversed depth), camera, sun + `CSMShadowNode` (splits from the rig's `shadowSplits`), post: depth/normal/velocity pre-pass -> GTAO (into the ambient term via `builtinAOContext`) -> lit pass -> TRAA -> bloom (high) -> AgX -> grade (saturation 1.2, S-curve contrast 1.5 around 0.45) -> sRGB. Low tier: one MRT pass, half-res GTAO multiplied into colour, TRAA. | `js/renderer.js`, `js/shaders/post.js` |
| `sky.js` | Rayleigh/Mie single-scattering sky (same constants/steps), sun disk, cirrus, METAR cloud layer, low overcast slab, ENV composition -> PMREM (GGX-prefiltered IBL), exponential height fog with Mie glow as `scene.fogNode`; ambient terms computed on the CPU so `setupSky` stays synchronous. | `common.js` SKY_PRECOMPUTE_FS, `env.js` SKY_FS / ENV_FS / CLOUD_FS, `renderer.js setupSky` |
| `ground.js` | Airfield / aux / city bakes (QuadMesh into render targets), ground material with the SDF runway markings (thresholds, designations from the glyph atlas, TDZ, aiming point, displaced-threshold arrows, blast-pad chevrons, rubber), concrete joints, night floodlight pools and street lights; water with wave-slope normals, IOR 1.333 Fresnel, foam at the seawall. | `js/shaders/ground.js`, `env.js` WATER_FS |
| `markings.js` | Taxiway/hold/edge/road ribbons and stand lead-ins/red boxes with the min-0.75 px width and area-correct alpha, anti-aliased dashes averaging to their duty ratio far away. | `js/live/markings.js` MARK_VS/FS |
| `objects.js` | PBR object material (terminals, tower, ITB, garages, masts, EMAS, piers, bridges, stand equipment, GSE): the 14 procedural material ids (curtain wall, panels, garage, corrugated metal, roofs, windows, foliage, tunnel ribs, garage-roof cars, tower glass, hangar door, lamp lenses, service facade, tower LED ribbon), vehicle tint. | `js/shaders/objects.js` |
| `signs.js` | Hold / location / painted / distance-remaining / gate / stand / VDGS faces rebuilt as panel + MSDF glyph quads (sharp at any distance); faces found by the UV rectangle the existing builders emit. | `js/live/signs.js` makeAtlas styles |
| `bridges.js` | Converts `LiveGateSystem.items()` (batched static bridges + stand equipment, per-frame mesh of the moving bridges only, sign quads, GSE instances -> `InstancedMesh` per vehicle type). | uses `js/live/gates.js` as is |
| `aircraft.js` | Imported models: paint zones recoloured by livery, clear-coat paint, glass as a smooth clear-coat layer with warm cabin light at night, bare metal, lenses, gear collapse; procedural airframes (windows, doors, flight-deck panes, fin, engines); per-aircraft uniforms (`onObjectUpdate`) so each model is one program; brand x model livery textures as loaded by `LiveAircraft` (`ac.livTex`, js/aircraft/liveries.js) on the atlas draws, atlas alpha = painted cabin-window glass. | `js/shaders/aircraft_real.js`, `aircraft.js` |
| `lights.js` | All light sprites in one instanced additive draw (directional lobes, 2.2 px minimum size with energy conservation). | `js/shaders/sprites.js` |
| `convert.js`, `tsl/common.js` | Record -> BufferGeometry/Texture; hashes, value noise, fbm, `band()`, viewer-facing normals. | `common.js` noise chunk |
| `assets/msdf_signs.*` | Offline MSDF atlas (Liberation Sans/Mono Bold, SIL OFL), `tools/build3/msdf_atlas.py`. | — |

## 4. Observed in this sandbox (headless Chromium 141, Mesa llvmpipe via `SOFTGL=1`, 4 vCPU shared)

- `navigator.gpu` exists but no adapter: "Failed to create WebGPU Context Provider"; three.js logs "WebGPU is not
  available, running under WebGL2 backend". **The WebGPU backend could not be exercised here**; the WebGL 2 fallback
  runs everything. `EXT_clip_control` is present, so the reversed depth buffer is active (near 0.25 m to far 180 km in
  one depth range, replacing the old two-range depth).
- Start-up: bakes and scene assembly take 10-30 s here; the first frames take tens of seconds each while llvmpipe
  compiles the programs (`compileAsync` is used to compile the scene's programs before the first frame). Frame times
  on llvmpipe say nothing about a phone GPU (**Unverified**: phone frame rate; test on the owner's iPhone, phase 0 of
  engine.md §8.2).
- Draw calls at the overview (high tier, every pass incl. shadows/post): ~800; triangles ~3.9 M (terrain dominates).

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
- Low tier (single MRT pass, 2 cascades x 1024²): 361 draw calls at the overview (high: ~2000), renders all views.

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

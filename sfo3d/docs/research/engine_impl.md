# three.js r186 renderer for SFO Live 3D: implementation notes (live3.html)

Status: 5 Nov 2026 (UTC), after close-out round 2 (§4.8; review round 3 in §4.7). Round 2 (26 Sep, §4.6) was committed as a WIP snapshot (06ecf63)
that never started: `live3.html` threw at start-up until the round-3 fixes. Decision record: `docs/research/engine.md`
(verified). This note records how the port is built, what was checked in this sandbox, and what is still open. Labels:
**Observed** (run or read here), **Inferred**.

## 1. What it is

`live3.html` is the same app as `live.html` on a new renderer: three.js r186 `WebGPURenderer` (WebGPU where the browser
has it, automatic WebGL 2 fallback), TSL node materials, `CSMShadowNode` cascades, GTAO, TRAA (MSAA off), AgX,
PMREM image-based lighting from our own sky model, and an offline MSDF sign atlas. `live.html` and its renderer are
untouched.

```
python3 -m http.server 8000     # repo root
http://localhost:8000/live3.html?mode=snapshot          # recorded snapshot
http://localhost:8000/live3.html                        # live (relay auto-detected via /api/ping, as live.html)
  ?tier=ultra|high|medium|low   force a quality tier (default: the old app's choice: phones low, <=4 GB medium, else
                          high; the app's ?quality=ultra (4096 shadow map) maps to ultra)
  ?webgl=1                force the WebGL 2 backend       ?revz=0   no reversed depth buffer
  ?res=1                  render at canvas size x DPR (QA renders; the app's dynamic resolution is ignored)
  ?sat= ?contrast= ?lookSat= ?lookSatLo= ?vignette= ?expo= ?cas=   grade overrides (defaults 1.0 / 1.6 / 1.8 /
                          1.0 / app 0.18 / 1.0 / from the render scale)
  ?aodn=0                 GTAO without the denoise pass (A/B)        ?nocast=1  no shadow casters (debug)
```

QA harnesses (same mock relay and snapshot as `jobs/qa3.mjs`):

```
SOFTGL=1 W=960 H=540 OUT=out/engine PAGES="live3.html,live.html" \
  VIEWS="view:overview;gate:B26,60,1,14;hold:12;tower;thr:28R" node livetest.mjs tools/build3/job_views.mjs
# -> out/engine/new_<view>.png (three.js), out/engine/old_<view>.png (current renderer)
SOFTGL=1 W=960 H=540 OUT=out/engine2 PAGE="live3.html?tier=high" HDR=1 node livetest.mjs tools/build3/job_review.mjs
# -> review views (day, dusk, night) + per-frame metrics + HDR dumps; python3 tools/build3/grade_hdr.py grades dumps offline
SOFTGL=1 PREV=out/three_prev.js node livetest.mjs tools/build3/job_ghost.mjs     # TRAA disocclusion A/B (§4.3)
SOFTGL=1 LP_NUM_THREADS=3 W=960 H=540 OUT=out/engine_r3 PAGE="live3.html?tier=high" node livetest.mjs tools/build3/job_round3.mjs
# -> review-round-3 set in one page load (§4.7): overview, gate B20, UAL B39M close-up after 8 / 32 frames and in a
#    3 deg/frame orbit, sprites without occlusion, dusk, night with / without the floodlight spots; SHORT=1 for the low tier
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
| `engine.js` | `WebGPURenderer` (reversed depth), camera, sun + `CSM3` (CSMShadowNode with a per-cascade slope-scaled bias, normal offset 1.25 texels per cascade, PCF with a per-frame rotated tap pattern so TRAA averages it), post: depth/normal/velocity pre-pass -> GTAO (4 m radius, half res, temporal noise rotation over all 24 rotation x offset pairs) -> `AODenoiseNode` (5x5 plane-distance-weighted box at the AO resolution, §4.7) -> into the ambient term via `builtinAOContext` and onto the floodlight term -> lit pass -> TRAA -> CAS sharpening (noise-gated) -> + light-sprite pass (after TRAA, un-jittered camera) -> exposure -> bloom (all tiers; threshold in exposed units, soft luminance clamp) -> AgX with a look (contrast 1.6 on log2 LUMINANCE around 18 % grey, look saturation 1.0 up to grey rising to 1.8 on the shoulder) -> saturation -> vignette -> sRGB -> dither/grain. Low tier: one MRT pass, the PREVIOUS frame's half-res GTAO (reprojected, not denoised) in the ambient term, TRAA, same output chain. Creates the floodlight light in its constructor (§4.7) and registers its nodes. | `js/renderer.js`, `js/shaders/post.js` |
| `flood.js` | Apron floodlights as a light: CPU field of the 70 observed masts at 4 receiver heights (2 / 9 / 16 / 23 m; vector irradiance + horizontal spread, RGBA16F 3-D texture over the masts' box, calibrated to the ICAO 20 lux stand average; lamp units, x `LAMP_M` in the scene, §4.5), `FloodLightNode` (a three.js analytic light node sampling it per pixel, GTAO on the direct term, spread + ground bounce as irradiance) and `MastSpot` / `MastSpotNode` (the 2 masts that light the view most as shadow-casting spot lights; their share is subtracted from the field, so spot + residual = field). | new (review rounds 1-2) |
| `sky.js` | Rayleigh/Mie single-scattering sky (same constants/steps), sun disk, cirrus, METAR cloud layer, low overcast slab, ENV composition -> PMREM (GGX-prefiltered IBL, ground below the horizon = the airfield bake's mean albedo x irradiance), `skyAlong(ro, rd)` (the visible sky from any point: background and water reflections), night floor with a warm horizon glow (lamp units, §4.5), twilight multiple-scattering term below the horizon (§4.5), exponential height fog with Mie glow as `scene.fogNode`; ambient terms computed on the CPU so `setupSky` stays synchronous. | `common.js` SKY_PRECOMPUTE_FS, `env.js` SKY_FS / ENV_FS / CLOUD_FS, `renderer.js setupSky` |
| `ground.js` | Airfield / aux / city bakes (tiles of <= 1024² texels, a few per frame, NoBlending so the coverage alpha survives), ground material with the SDF runway markings (thresholds, designations from the glyph atlas, TDZ, aiming point, displaced-threshold arrows, blast-pad chevrons, rubber), concrete joints, city street lights at night (energy-conserving far away; the apron floodlights are `flood.js`); water with wind-driven wave slopes and roughness, IOR 1.333 Fresnel, its sky reflection = `skyAlong` from the water point, foam at the seawall. | `js/shaders/ground.js`, `env.js` WATER_FS |
| `markings.js` | Taxiway/hold/edge/road ribbons and stand lead-ins/red boxes with a minimum 1.2 px width measured on the projected perpendicular (foreshortening-aware, on the unit perpendicular: the miter length at joints no longer blows corners up) and area-correct alpha, anti-aliased dashes averaging to their duty ratio far away. | `js/live/markings.js` MARK_VS/FS |
| `objects.js` | PBR object material (MeshPhysical: IOR per material id) for terminals, tower, ITB, garages, masts, EMAS, piers, bridges, stand equipment, GSE: the 14 procedural material ids (curtain wall = coated glass IOR 2.0 with no diffuse albedo over an interior-mapped concourse drawn as EMISSION lit by its own illuminance `interiorE` (§4.7), per-pane roughness / normal variation, panels, garage, corrugated metal, roofs, windows, foliage, tunnel ribs, garage-roof deck (the cars are instanced boxes, fading to their mean colour 300-900 m), tower cab glass and LED ribbon = coated glass, hangar door, lamp lenses, service facade), vehicle tint. | `js/shaders/objects.js` |
| `signs.js` | Hold / location / painted / distance-remaining / gate / stand / VDGS faces rebuilt as panel + MSDF glyph quads (sharp at any distance); faces found by the UV rectangle the existing builders emit. Fallback when the font fails: the builders' own quads with their canvas atlas (`atlasSignMaterial`). | `js/live/signs.js` makeAtlas styles |
| `bridges.js` | Converts `LiveGateSystem.items()` (batched static bridges + stand equipment, per-frame mesh of the moving bridges only, sign quads, GSE instances -> `InstancedMesh` per vehicle type). Bridges and GSE do not wait for the sign font; sign faces follow when it arrives (or from the atlas fallback). | uses `js/live/gates.js` as is |
| `aircraft.js` | Imported models: paint zones recoloured by livery, clear-coat paint, glass as a smooth clear-coat layer with warm cabin light at night, bare metal, lenses, gear collapse; procedural airframes (windows, doors, flight-deck panes, fin, engines); per-aircraft uniforms (`onObjectUpdate`) so each model is one program; brand x model livery textures as loaded by `LiveAircraft` (`ac.livTex`, js/aircraft/liveries.js) on the atlas draws, atlas alpha = painted cabin-window glass. | `js/shaders/aircraft_real.js`, `aircraft.js` |
| `lights.js` | All light sprites in one instanced additive draw in their own pass after TRAA (directional lobes, 2.2 px minimum with energy conservation, 12 px maximum, halo capped in exposed units, x0.5 by day, x `lampK` (§4.5), markers fade out within 150 m; occlusion by the scene depth per fragment, switchable for QA: `SFO.R.sprites.depthOn.value = 0`). | `js/shaders/sprites.js` |
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

### 4.3 Review round 1 (25-26 Sep 2026): findings, fixes, evidence

Renders (960x540, `SOFTGL=1`, snapshot + mock relay, tier high unless named `low_`), from
`tools/build3/job_review.mjs`: `out/engine3/` (day, dusk before the twilight fix, night, low tier, TRAA orbit),
`out/engine4/` (final grade, red-box fix: gate, hold 12, UAL close-up), `out/engine5/` (temporal PCF, twilight sky:
UAL close-up, dusk, night). Luminance percentiles are of the PNGs.

| # | Finding | Fix (file) | Evidence (Observed) |
|---|---|---|---|
| 1 | Night/dusk bloom veil | bloom on exposed values, threshold 1.6 after a soft luminance clamp (x8 white), strength 0.035 (`engine.js`) | night gate p1 0, sky (11,17,28), apron (97,90,82) (`engine5/rv_night_gate_B26_60_1_14.png`; review: p1 146, sky (246,236,223)) |
| 2 | Night lighting inverted (emissive apron) | floods are a light (`flood.js`: 70 observed masts, ICAO 20 lux, lights ground, paint, signs, objects, aircraft); exposure keyed on lit concrete; lamp units vs sky units (§4.5) | lead-in line at night (162,128,35) on apron (97,90,82); aircraft side (141,137,135) (review: line (11,6,0) on (222,215,205), aircraft (11,18,32)) |
| 3 | Thin markings vanish at grazing angles | 1.2 px minimum on the projected perpendicular, alpha x true/drawn width (`markings.js`); round 2 found and fixed translucent triangles at red-box corners (miter-scaled normal) | gate: taxilane line (222,209,184) on (206,201,195) (review: 2 levels); crossing centrelines and runway edges visible in `engine4/rv_real_hold_12_300.png`; clean red boxes in `engine4/rv_real_gate_B26_60_1_14.png` |
| 4 | Marker sprite glare disk | sprites clamped to 2.2-12 px radius, halo capped at 0.5 exposed, x0.5 by day, markers fade out 150 -> 60 m (`lights.js`); generic airframe instead of a marker requested (`docs/requests/engine_exports.md` §5.1) | code; no marker disk in any round-2 render |
| 5 | TRAA disocclusion dead with reversed depth | vendored patch of `TAAUtils.samplePreviousDepth` (`tools/build3/build.mjs`, build fails if the patch target moves) | in-app orbit (12 frames at 3 deg/frame around UAL, then 16 static): moving vs settled differ only at 1-2 px edges (mean 0.9, top-1 % 27 levels, no trails; `engine3/rv_real_orbit_moving.png` / `_settled.png`) |
| 6 | Low-tier shadow acne, 2-cascade range | normal offset 1.25 texels per cascade, slope-scaled depth bias (`CSM3`), last split from `Q.shadowDist` (`engine.js`) | no roof striping in `engine3/low_real_tower.png`; soft (not stepped) wing shadow in `low_real_gate_B26_60_1_14.png` |
| 7 | Curtain-wall glass near-black | MeshPhysical, IOR 2.0 coated glass over parallax rooms, per-pane roughness/normal (`objects.js`) | glass (98,103,104) close-up, (106-118) tower view (review: 55-64; reference photo about (119,128,129)) |
| 8 | UAL title across the window belt | liveries workflow (not this renderer): §5.5 of the requests | fixed upstream: title above the window row in `engine4/rv_real_ac_ual_38.png` |
| 9 | Flat daylight image | AgX look: contrast 1.8 in log2 around 18 % grey, look saturation 1.0, saturation 1.0, day gain 1.02 (§4.4) | gate p1 45 / p50 208 / p99.5 243, close-up p1 31-34 / p99.5 240-241, white fuselage (226,229,232) (review: p1 88-112, p99 180-220, fuselage (169,174,183)) |
| 10 | Blue shade | saturation 1.2 -> 1.0; IBL below the horizon from the airfield bake's mean albedo (0.30,0.27,0.21) | partly rejected, see §4.4: open shade (58,82,110) |
| 11 | Roof-junction dark lines | slope-scaled bias (not GTAO: the reviewer showed they stayed with AO off) | no dark seams in `engine3/rv_real_tower.png` |
| 12 | Phantom cloud reflections, mirror-calm bay | water reflection = `skyAlong` from the water point (the visible sky's clouds); wave amplitude and roughness from the METAR wind | reflected cloud under the visible cloud in `engine3/rv_real_thr_28R_900_3.png`, ripples at 12 kt |
| 13 | Dynamic resolution restarts TRAA | render scale quantised to 1/0.85/0.72/0.6/0.5/0.4, at most one change per 8 s, canvas changes at once (`renderer3.js resize`) | code |
| 14 | Strobes/sprites through TRAA | sprites in their own pass after TRAA with the un-jittered camera, depth-tested per fragment against the scene depth | code; lights visible in all night renders |
| 15 | Airfield bake alpha lost | bake materials `NoBlending` (`ground.js`) | Burlingame shore shows city texture in `engine3/rv_real_overview.png` |
| 16 | Image copies kept (359 MB) | `createImageBitmap(premultiplyAlpha: none)` copies, uploaded at once, closed after upload (`compat/gl.js`, `convert.js`); round 2 also uploads textures made before their bitmap arrived | `retainedImageMB` 0 in every round-2 view (round 1: 232-374) |
| 17 | Bridges/GSE gated on the font | bridges and GSE built at once; sign faces follow the font, or the canvas atlas if it fails (shader-side sRGB decode when the atlas was uploaded as linear); `build.mjs --app` copies the atlas next to the bundle | code; `out/build3/assets/` |
| 18 | Device loss / init failure / fake caps | `onDeviceLost` -> synthetic `webglcontextlost` + message; init failure -> message and `__sfoError`; `getExtension` answers from a probe context | WebGL 2 loss path observed by the reviewer; WebGPU loss path **Unverified** |
| 19 | Untiled bakes | tiles of <= 1024² texels, 1 per frame for rebakes (6 on the first bake, 8 with `?res=1`) | code; sun rebakes complete while rendering |
| 20 | Wrong draw-call metric | `debugInfo()` reports `drawCalls`, `frameCalls`, `texMB`, `retainedImageMB` | §4 figures |
| 21 | Tower LED ribbon black by day | coated-glass reflectance (IOR 2.0) | ribbon median (142,145,147) (review: (17-23,21-30,25-35); old renderer about (105,116,129)) |
| 22 | Post chain not at parity | vignette 0.18, ordered dither, grain, bloom on every tier; the app's `sat`, `bloom`, `vignette`, `grain` read | code |

Also found in round 2 and fixed: GTAO's noise pattern was static (`useTemporalFiltering` now on), and three's PCF rotates
its taps by a per-pixel noise that never changes, which TRAA cannot average. `engine.js pcfTemporal` offsets the noise
per frame. After the change the mottle under the wing is visibly smoother (`engine5/rv_real_ac_ual_38.png` vs
`engine4/`). A soft grain on the fuselage above the wing root remains in both. It sits where the livery's dirt layer is
(Inferred).

### 4.4 Grade (day)

The grade was chosen offline on the HDR dumps (`python3 tools/build3/grade_hdr.py <stem> --flip --gain g --contrast c
--looksat l --sat s`). A higher contrast pivots around 18 % grey. It darkens the shade and the glass and lifts sunlit
white, and p50 stays about the same:

| gain / contrast / lookSat / sat | gate p1 / p50 / p99.5 | close-up p1 / p99.5 |
|---|---|---|
| 1.09 / 1.4 / 1.1 / 1.05 (round 1) | 85 / 204 / 238 | 66 / 230 |
| 0.85 / 1.8 / 1.0 / 1.0 (adopted: `DAY_GAIN` 1.02) | 62 / 212 / 246 | 40 / 239 |

The live renders came out at 45 / 208 / 243 and 31 / 240. They include GTAO and TRAA, and the dumps are taken before
those.

The shade colour is only partly changed (finding 10). Open shade on the apron is lit by the sky model's irradiance,
which is about 12,000 K: B/R 1.9 in linear sRGB. A camera at daylight white balance renders that bluish, as it
should. The reviewer's reference pixel (34,29,31) is shade under an aircraft, which is lit mostly by warm bounce from
sunlit concrete. That second bounce is not modelled. The IBL's lower hemisphere now carries the bake's warm albedo,
so downward-facing surfaces get warm bounce, but the ground itself does not. Saturation is 1.0, so the look no longer
adds chroma.

The hazy distant views keep a high p1 (overview 116, hold 12 at 300 m 132). They contain no dark surfaces, and aerial
perspective lifts the shadows. This is content, not grade.

### 4.5 Lamps vs sky: one set of units (the dusk re-check)

The lamps are authored in "lamp units". The floods use E_STAND = 0.62 = 20 lux. Windows, signs, city lights, sprites
and aircraft lenses are tuned against them. The sun and sky are in the sky model's units, where the sun outside the
atmosphere is `sunI` = 20 = the luminous solar constant, about 133 klx, so 1 unit is about 6,670 lux. The luminous
solar constant is Darula, Kittler & Gueymard 2005, 133.3 klx; that figure was recalled, not re-checked here.

The two scales used to be mixed 1:1. That made the lamps about 200x too strong against the twilight sky. At the
'dusk' preset (sun -4.5 deg) the apron rendered 5x brighter than the sky, and dusk looked like night
(`engine2/rv_dusk_gate_B26_60_1_14.png`).

`renderer3.js LAMP_M` = (20 lux / 6,670) / 0.62 = 0.0048 converts lamp units to sky units. It is applied as follows:
- floods: intensity nightF x LAMP_M;
- night-only emission: `nightE` = nightF x LAMP_M;
- sprites, lenses and per-vertex emission: `lampK` = LAMP_M ^ nightF, which is 1 by day, so the day look is
  unchanged;
- the app's night floor: `max(sky, floor)` -> sky + LAMP_M x (floor - sky)+.

The exposure is the larger of two values:
- the app's day exposure without its night term, x `DAY_GAIN`;
- the exposure that puts lit concrete (albedo 0.37) at the display key 0.16 under the total horizontal illuminance
  (sun + sky + floods).

The modelled horizontal illuminance (`debugInfo().eKeyLux`) is:
- day: 66.7 klx;
- dusk: 31.8 lx (floods 20 + twilight sky 11.8);
- night: 20 lx.

For comparison, the sky model alone gives:
- sunset: about 1,270 lx;
- -6 deg: 10 lx;
- -8 deg: 0.8 lx.

Real values are about 400-800 lx at sunset and about 3.4 lx at the end of civil twilight. Those reference figures were
recalled, not re-checked here: Inferred.

Twilight sky: single scattering alone left the -4.5 deg zenith grey and about 20x darker than the sunward horizon.
The IBL therefore lit the whole scene orange (`engine3/rv_dusk_gate_B26_60_1_14.png`). The multiple-scattering
stand-in now decays below the horizon (0.08 x exp(0.8 x elevation in deg)) instead of stopping at -3.8 deg. That adds
a Rayleigh-blue dome of about 40 % of the single-scattered irradiance at -4.5 deg.

The result is `engine5/rv_dusk_gate_B26_60_1_14.png`. The sky is blue (50,84,116) with the twilight gradient, and
sun-facing surfaces are pink-lit. The apron is mid-grey (106,91,83) under floods and sky, with p1 13 / p99.5 243.

Night is unchanged in look: exposure 453 x LAMP_M = 2.2 against the old 2.03.

### 4.6 Review round 2 (26 Sep 2026): changes made, first run in round 3

These changes were committed in the WIP snapshot 06ecf63 (739 changed lines in 8 `js/three` files) when the workflow
was interrupted, and were recorded only in code comments. They never ran: the snapshot threw at start-up (§4.7 #1-2).
The numbers quoted in the code comments for them (e.g. the round-2 grade) are offline values from
`tools/build3/grade_hdr.py` on HDR dumps, not live renders (Inferred from the history). Round 3 is their first run.

| Area | Change (file) |
|---|---|
| Look | AgX contrast on log2 LUMINANCE only, the same offset added to all channels (per channel, contrast 1.8 raised every channel ratio to the power 1.8: navy shade, pastel paint); look saturation 1.0 up to grey, rising to 1.8 on the shoulder; contrast 1.6, `DAY_GAIN` 0.80 (`engine.js agxLook`, `renderer3.js`) |
| AO / AA | GTAO noise rotation from the engine's own frame counter (three's `frameId` steps by the passes per frame); CAS sharpening after TRAA, stronger at lower render scales (`engine.js`) |
| Low tier | 3 cascades x 1024² (2 left rooftop units unshadowed); the previous frame's GTAO, reprojected, in the ambient term instead of multiplied into the lit colour (`engine.js QUALITY3.low`, `buildPipeline`) |
| Floodlights | field at 4 receiver heights (roofs rendered snow-white with the 2 m field everywhere), beam cut-off 81.7 -> 80 deg from nadir, horizontal-spread and ground-bounce terms, GTAO on the direct term, the 2 masts lighting the view as shadow-casting `MastSpot` lights, masts on their own layer (`flood.js`, `renderer3.js _floodSpots`) |
| Canvas | `Renderer3` owns the canvas size (dynamic resolution left three drawing into a corner of a full-size canvas) |
| Aircraft | per-aircraft values from `LiveAircraft.realUniforms()`; registrations from one shared LRU atlas (`RegAtlas`); procedural wing-tip devices drawn; procedural airframe while the livery is pending; brand liveries evicted LRU beyond the tier's `livMB` (`aircraft.js`) |
| Objects | curtain walls show one continuous lit concourse (interior mapping) instead of office rooms; flat roofs with membrane seams, skylights, rooftop units, solar arrays; garage cars as instanced boxes (`objects.js`) |
| Ground / signs / markings | far city lights as sparse point-like clusters; water body colour fix (envNode also drives the diffuse irradiance); canvas sign atlases released once the MSDF font is in; red-box corner miter fix (`ground.js`, `signs.js`, `markings.js`) |
| Start-up UI | progress overlay until the first frame (bake, compile, first frame took minutes on llvmpipe with a black canvas) |

### 4.7 Review round 3 (4 Nov 2026): findings, fixes, evidence

Setup: headless Chromium 1.63 on llvmpipe (`SOFTGL=1`, `LP_NUM_THREADS=3`), 960x540, snapshot + mock relay, tier high
unless named; other agents loaded the 4 CPUs (load 4-8). Jobs: `tools/build3/job_round3.mjs` (default set, `VERIFY2=1`,
`SHORT=1`). Outputs in `out/engine_r3/`: `run1/` (full set, the run in which the shadow-switch crash below was found),
`v2/` (re-check after the later fixes), `low/` (low tier), `navdiag/`. "Before" = the reviewer's copy with the two
start-up workarounds (`out/engine_rev/patched/`, `night/`), "old" = live.html (`out/engine_rev/old_*`).
Grain = standard deviation of luminance minus its Gaussian blur (sigma 2 px) in fixed boxes of the close-up
(`ac:a12a82,38,-,6`): fuselage above the wing root (285,283)-(345,300), shaded apron by the main gear (380,346)-(419,378),
sunlit apron (120,440)-(300,470) as the texture reference. (The reviewer's 15.4 / 9.4 used other boxes; same direction.)

| # | Finding | Root cause | Fix (file) | Evidence (Observed) |
|---|---|---|---|---|
| 1 | live3 cannot start (critical) | `FloodLight` / `MastSpot` wrote `this.scale = 1`: `Object3D.scale` is a non-writable Vector3 | field renamed `level` (`flood.js`, `engine.js setFloodSpots`) | ready in 256 s (run1) / 247 s (v2) / 188 s (low), 0 console errors; HEAD: TypeError at `new FloodLight` |
| 2 | start-up race (critical) | `attachWorld` (inside the app's synchronous `new Scene`) used `engine.flood`, created in the async `init()` | `FloodLight` created in the `Engine` constructor, added to the scene in `init()`; `attachWorld` errors now shown (`engine.js`, `renderer3.js`) | the flood field is set at 5-7 s, before init resolves (logs), every run |
| 3 | blast-pad chevrons 15.0 / 29.7 m | not ported from the WebGL2 shader | first apex 17.0 m, pitch 30.48 m (`ground.js`), = `js/shaders/ground.js` | code (NAIP 2024 peaks 16.6-17.3 m, AC 150/5340-1M Fig. A-9) |
| 4 | night: hard 100 m polygons by the spot masts | three r186 `ShadowNode.updateShadow` replaces a shadow-camera mask with only bit 0 by the main camera's (which has `MAST_LAYER`): the masts were in the spot shadow maps and the 16-sided head ring (r 1.25 m, 0.25 m under the spot) shadowed everything beyond ~79 deg from nadir | spot shadow cameras see layer 0 + an unused marker layer (`flood.js SPOT_SHADOW_LAYER`); spot share evaluated at the field's clamped receiver height (a bright arc at 140-151 m appeared once the polygon was gone: the field's 2 m layer is cut at 140 m, the spot at the true ground height at 151 m) | `run1/r3_night_gate_B20.png` vs `engine_rev/night/new_night_gate.png`: polygon gone; `v2/night_spot_diff.png` (spots on - off): only cast shadows and per-face N.L, no arc (the arc is in `run1/night_spot_diff.png`); shadow masks [9, 9] |
| 4b | (found here) crash after a shadow switch | three r186 disposes a light's shadow node when `castShadow` goes false; render objects not drawn meanwhile reuse the old graph at the next switch-on (`shadowMap` null); `CSMShadowNode.dispose()` removes its cascade lights for good | spot shadow node given as `shadow.shadowNode` and never disposed (`flood.js`); `CSM3.dispose()` a no-op (`engine.js`) | run1: TypeError `reading 'depthTexture'` after spots off -> on; v2: 0 errors through spots off -> on, day -> night -> day -> night, sun shadows present after the second sunrise (`v2/r3_day2_ac8.png`) |
| 5 | AO / shadow grain on the hero close-up | half-res GTAO with no spatial filter (its 5x5 rotation tile left as 2 px blobs), 12 of the 24 noise patterns reachable, CAS amplifying the residue | `AODenoiseNode` (5x5 plane-distance-weighted box at the AO resolution), all 24 (rotation, offset) pairs, CAS noise gate (range < 0.01 not sharpened) (`engine.js`) | grain wing root old 1.50 / before 2.63 / after 0.88 (8 frames), 0.87 (32), 0.86 (v2); shaded apron 0.50 / 2.07 / 0.78; sunlit texture 4.33 / 4.42 / 4.33 (detail kept); orbit at 3 deg/frame: no visible grain (`run1/r3_day_ac_orbit.png`) |
| 6 | curtain wall reads matte khaki | the concourse behind the pane was the ALBEDO, lit by the full sun and sky (linear ~0.11, warm) | pane albedo 0, the hall as emission lit by its own illuminance (5 % daylight factor + 200 lx lamps by day; inferred), x T x (1 - F); facade own-shadow term for downward reflections (`objects.js`, `renderer3.js interiorE / shadeK`) | pane old (24,28,35) / before (59,58,54) / after (49,47,41): -17 % luminance, still warm and matte (close-out verifier: B-R -7.6; this row's "no matte panelling" overstated it). **Open after round 3; fixed in §4.8** |
| 7 | `engine_impl.md` stale | round 2 never documented or run | this file: status, §1, §3, §4.6, §4.7, §5, §6 | — |
| 8 | aircraft nav lights missing (day AND night) | not the day dimming and not the occlusion test: every light sprite between 2.2 and 12 px on screen (neither branch of the `If` / `ElseIf` size clamp) was never rasterised in the WebGL 2 backend; only sub-2.2 px sprites (distant airfield lights) drew. Found with a light-pass readback: green nav light and a test sprite 12 m in front of the camera = 0 in the light pass, with the occlusion test on and off; `envtest.html?sprites=1`, row of lights at 20 m: 0 lit px, at 175 m: 101 | the size / intensity clamp, lobe and marker fade written branchless with the same math (`lights.js`); `SFO.R.sprites.depthOn` QA switch | envtest after: 386 lit px at 20 m (was 0), 440 at 175 m (was 101); in-app (low tier, `out/engine_r3/navdiag/`): light pass at the green nav light 23.6 by day (x exposure 0.36) and 0.216 at night (x 452), test sprite 23.2, identical with the occlusion test on and off (not occluded); green light at the wingtip in `navdiag_depth1.png` / `navdiag_night.png` |
| 9 | quality parity | no ultra tier; 0.8 not a resolution step | `QUALITY3.ultra` (from the app's 4096 shadow map), steps 1 / 0.85 / 0.8 / 0.72 / ... (`engine.js`, `renderer3.js`) | code |
| 10 | fatal message blames the browser | one message for every init failure | browser wording only when neither WebGPU nor WebGL 2 exists (probe), else "an error in the app" + detail; `attachWorld` errors shown (`renderer3.js`) | code |
| 12 | garage-roof cars alias into a speckled disk | 2878 sub-pixel boxes | own car material: every car part fades to the mean car colour from 300 to 900 m (`objects.js CAR_FADE`, `renderer3.js carMat`) | the speckled disk at the terminal core is gone in `run1/r3_day_overview.png` (overview p1/p50/p99.5 before 88/158/198, after 88/158/197) |
| — | `?cas=` ignored | parsed, never applied | applied in `resize()` (`renderer3.js`) | code |
| — | stale `perf_phone.js` reference | — | comments fixed; `perf.js` marked parked (owner deferred phone work) | `grep` |

Luminance p1 / p50 / p99.5 (old -> before -> after): close-up 29/153/224 -> 25/171/226 -> 19/168/226; gate B20
27/170/212 -> 48/181/233 -> 41/181/233; overview 69/135/176 -> 88/158/198 -> 88/158/197. Draw calls (after, high):
overview 532, gate 537, close-up 586, night gate 346 (spots on) / 261 (off); low tier: gate 271, close-up 395, night
gate 186. Texture memory 976-1152 MB high, 532-548 MB low; `retainedImageMB` 0.

Not resolved / rejected, with the evidence:
- **Pane colour** (finding 6; superseded by §4.8, where the A/B was run and the cause fixed): after the fix the pane is mostly the coated glass's Fresnel reflection. From this
  elevated view (camera ~53 m up, pitch 24 deg) a vertical pane keeps the ray's downward slope and reflects the apron
  ~18 m in front of it, not the sky: the reviewer's "sky reflections" are not what this view shows. The reflected apron
  is sunlit here (the pier's own shadow reaches ~13-17 m at the 45 deg sun of the snapshot, so the own-shadow term stays
  off). The remaining warmth is the IBL's lower hemisphere, which is the whole-airfield mean albedo (0.30, 0.27, 0.21:
  grass and sand) where the pane reflects concrete (the bake's 0.38, 0.37, 0.345). Changing the IBL ground changes every
  object's ambient from below and the flood bounce, so it was not done without a full re-verification: next round
  (paved-area mean for the IBL ground, or local reflections).
- **Dusk** was not checked: the app's 'dusk' preset is a clock time (19:45 "PDT", js/live/app.js `lightDate`), which on
  4 Nov is ~1.7 h after sunset; the dusk render is night (eKeyLux 20). Request in `docs/requests/engine_closeout.md`.
- **Overview "lake"** (finding 13): the world has no water there (`js/world/terrain.js`, read); live.html's blue patch is
  not data-driven. Routed to the terrain / old-renderer owners (closeout §2).
- **Seawall foam** (finding 11) and the **replicas** (finding 15): parity today; shared items routed (closeout §3-4).
- **Playwright pin** (finding 14): not changed, `package-lock.json` would go out of sync and npm may not run here
  (closeout §1).
- WebGPU backend: still no adapter in this sandbox.

### 4.8 Close-out round 2 (5 Nov 2026): curtain-wall glass, position lights by day, ultra tier

Setup: as §4.7, load ~2 (container just restarted), heavy jobs through `flock out/.heavy.lock`. App jobs:
`tools/build3/job_close2.mjs`, one page load each: `out/engine_r3/close2/` (`live3.html?tier=high&glassab=1`, ready
89 s, 827 s total, 0 console / page errors) and `out/engine_r3/ultra/` (`?quality=ultra&glassab=1`, `ULTRA=1`). Dev page:
`js/three/dev/glasstest.html` (a 30 m pier on concrete under the snapshot's sun, camera placed as gate:B20 relative to the
B20 facade; loads in 5-15 s instead of 90-300 s) with `tools/build3/job_glass.mjs` (`GV=` variant lists;
`out/engine_r3/glassdev/r1`, `r2` with `v1.json`, `v2.json`). Measures: `tools/build3/glass_meas.py` (display sRGB;
"dark60" = mean of the darker 60 % by luminance). App pane box = the close-out verifier's (x 20-170, y 295-330 of
gate:B20,130,1,24); low view gate:B20,70,1,6 box x 5-370, y 180-222.

**Glass (engine-v1, engine-v2): A/B in the app, gate:B20,130,1,24** (`?glassab=1`: x 1 = the round-3 inputs)

| Variant | dark60 | B-R | G-R | lum |
|---|---|---|---|---|
| live.html (verifier's crop) | (24.4, 28.8, 35.0) | +10.7 | +4.4 | ~28 |
| round 3 ("old") | (47.2, 45.5, 40.3) | -6.9 | -1.6 | 45.5 |
| old, IBL ground = paved mean (0.38, 0.37, 0.345): the requested A/B | (56.9, 56.6, 54.3) | -2.6 | -0.4 | 56.5 |
| old, reflection term only | (34.6, 31.6, 25.1) | -9.4 | -2.9 | 31.8 |
| new, tau_B 0.75 (high; pre-final tint) | (23.8, 29.2, 25.3) | +1.5 | +5.4 | 27.7 |
| new, tau_B 0.75, IBL ground = paved mean (pre-final) | (25.0, 30.3, 26.3) | +1.3 | +5.2 | 28.9 |
| new, tau_B 0.75, reflection only (pre-final) | (19.9, 25.0, 20.6) | +0.7 | +5.1 | 23.6 |
| **new, final tint (tau_B 0.80; ultra run; old there: (47.0, 45.5, 40.4), = high)** | **(25.1, 30.3, 27.4)** | **+2.3** | **+5.2** | **29.0** |
| low view old / new (tau_B 0.75: pre-final tint, not re-run) | (43.0, 45.7, 45.2) / (24.0, 34.1, 31.4) | +2.2 / +7.4 | +2.7 / +10.2 | 45.1 / 31.8 |
| photo a2.jpg, Boarding Area G (Sept 2025, overcast, ~1-2 km of haze; obs) | (31.7, 45.6, 47.1) | +15.4 | +13.9 | ~42 |

Rows marked pre-final were measured with tau_B 0.75 (renders 00:48-00:59) before the final tint 0.80 (ultra run
01:01-01:07); only the bold row is the final material. `close2/panes.json` gives identical old / new values from a wrong
box: use `glass_meas.json` (the values above). (Notes added 7 Nov 2026, env close-out round 3, env-9.)

Root cause (term by term; dev page, 130 m view, first tint: old (48.6, 47.0, 41.7) -> new (18.1, 20.3, 19.3) in `r1`;
reflection only: old (33.5, 30.8, 24.4) in `out/engine_r3/glass`, new (11.4, 13.2, 11.7) without fog in `r1`; hall
only: 0.0 at 745 lx (`r1`) and 2.5 at 4 klx (`glass`), i.e. under AgX's black point by day):
1. **The reflected ground.** From this elevated view a vertical pane mirrors the apron in front of it (dN = 1.3-1.6 x the
   pane's height above the apron), and the IBL's lower hemisphere was the sunlit WHOLE-airfield mean albedo (0.30,
   0.27, 0.21: grass and sand). The reviewer's A/B confirms it: the paved IBL ground moves the round-3 pane from B-R -6.9
   to -2.6. It is not the whole defect: the pane stayed a bright grey (lum 56.5 against live.html's ~28). Fix: the pane
   mirrors a local apron (`objects.js` envAdd through `setupEnvironment`, so three's split-sum weights F0 and F90 both
   see it): the airfield bake's CONCRETE mean (`renderer3 apronAlb` (0.321, 0.306, 0.269), weighted by the aux bake's
   concrete mask) and, where the reflected point lies in the facade's own shadow, sky light only through the open sky
   view factor. With it the pane no longer depends on the IBL ground (new vs new + paved: lum 27.7 / 28.9), so no other
   object's ambient light changed.
2. **The own-shadow term never worked** (engine-v2): `spec` was overwritten two statements after the shadeK factor. It is
   now part of the local reflection (1.), with the pier height 15.2 m (sfo_buildings piers h 14.6 m + 0.6 m parapet). At
   the snapshot's sun (41.6 deg, 149 deg behind the B20 facade) the pier's shadow reaches 14.7 m: the lowest ~2 m of the
   8.4 m glazing band mirror shaded apron, the rest sunlit apron. §4.7's "~18 m, sunlit" holds for the upper panes only.
3. **The hall's daylight**: the 5 % daylight factor was applied to sun + sky (3.5 klx); a daylight factor is defined for
   the sky's diffuse light (CIE), now 786 lx with the 200 lx lamps (`renderer3 interiorE`). Invisible by day at 130 m,
   it matters close up and at dusk.
4. **The frame**: mullions anti-aliased by widening (`gridLine`) covered ~18 % of the facade at 130 m instead of 3.9 %,
   with a metallic F0 ~0.25 mirroring the warm ground at 2.5x the glass's reflectance (the visible khaki grid). Now
   box-filtered, area-preserving (`gridLineA`).
5. **No body tint**: F0 was 0.111 x (0.9, 0.96, 1) and T neutral-blue. Now a blue-green tinted low-e IGU (inferred, no SFO
   glazing specification found; `objects.js` header): tau = (0.50, 0.80, 0.80), Rc 0.10 -> F0 (0.066, 0.102, 0.102),
   T (0.39, 0.62, 0.62), VLT 0.57 (typical 0.4-0.7). Calibrated on the hue of a2.jpg (teal, B ~ G > R): the first tint
   tau (0.62, 0.81, 0.80) came out neutral in the dev view (G-R +2.3, B-R +1.5; AgX's toe at contrast 1.6 compresses hue
   ~4 stops under grey), tau (0.50, 0.80, 0.75) green over blue in the app (+5.4 / +1.5), hence tau_B = tau_G. Final tint on the dev page
   (`glassdev/r3`, `v3.json`): 130 m view (17.5, 21.9, 21.0), G-R +4.4, B-R +3.5 (old there (48.7, 47.4, 42.1), -1.4 /
   -6.7); low view (24.5, 36.1, 35.2), +11.5 / +10.7.
Result: the pane is dark tinted glass (lum 29 = live.html's 28; the photo's 42 is overcast with haze, where the shaded
pane / concrete contrast is lower); teal-green rather than live.html's blue; the khaki grid is gone (`close2/app_cmp.png`:
live.html, old / new, new reflection only; `close2/low_cmp.jpg`; the close-up `close2/ac8_full.jpg` shows the D-pier
glazing as dark teal glass). Night glazing unchanged apart from the thinner mullions (pier box mean (182.9, 178.5, 172.7)
before, (188.4, 183.9, 177.9) now). Still missing: reflections of other objects (bridges, aircraft, other buildings: the
PMREM holds sky + ground only; SSR not tried on llvmpipe) and the mullion finish (a2 shows light aluminium mullions on
BA-G; the B pier's is not documented here).

**Position lights by day (engine-v3).** Owner's rule (nothing physically implausible): a position light has one intensity
day and night (14 CFR 25.1391: forward red / green >= 40 cd, rear white >= 20 cd; eCFR read 5 Nov 2026 by the round-2
fixer), while the day factor (0.5 x lampK = 1) made the records ~100x their night calibration (~2,600 cd). `lights.js
put(s, fixed)` + `renderer3` `fixedK` keep the aircraft position-light records (`isPositionLight`: no direction, s <= 0.22,
i <= 40; the first `fr.nAc` records are aircraft lights, `compat/scene.js`) at the night calibration by day; strobes,
beacons, landing / taxi lights and airfield lights keep the day factor. Day close-up `ac:a12a82,38,-,6`, 13 x 13 px at
the green light (577, 326): before (verifier, `ver/run/v_day_ac8.png`) max (255, 255, 255), 90 green-dominant px; now max
(145, 162, 170), mean (97, 113, 125), 0 green-dominant px (high and ultra alike): no halo, but no visible light either
(`close2/nav_zoom.png`; the light is 14.4 m from the camera, not 38 m; corrected 7 Nov 2026, env close-out round 3 env-9).
**Superseded (env close-out round 3, env-6):** by day the position light is now drawn at its lens size (0.08 m) with
its energy conserved to the 2.2-px floor (`js/env/aircraft_lights.js lensGain`). Rendered (c3e, 14.4 m, 67 cd): a
desaturated pink-on-white, red-on-dark 3-px dot at about 0.85 x sunlit white paint in R, no halo (corrected in close-out
round 5: this line said "a small saturated dot, ~2 x sunlit white paint", the CPU estimate for an assumed 80 cd;
docs/research/environment_impl.md R3.4). The records give 26 / 13 cd at the night calibration, 0.65x the rule's minimum (request in
`docs/requests/engine_closeout.md` Round 2). Parity: live.html still draws a day halo (closeout §8).

**Ultra tier (engine-v5), run once** (`out/engine_r3/ultra/`): tier 'ultra' from `?quality=ultra`, webgl2, ready 166 s,
374 s total, 0 errors; sun and both spot shadow maps 4096²; texture memory 1,893 MB at ready, 2,234 MB after the views
(high: 976-1,152 MB), 31 render targets; draw calls 616 (gate) / 745 (close-up) vs high 483 / 591; 6.17 M triangles;
peak Chromium RSS 4.0 GB on llvmpipe (GPU memory = system RAM here). Headless DPR is 1, so `dprMax 3` was not exercised
(960x540 canvas). Fit for stills on a desktop GPU with >= 4 GB; not for phones.

**Documentation (engine-v4)**: `docs/requests/engine_closeout.md` §0 corrected (everything of round 3 is in 0e92158 +
40a32e3), §4.7 row 6 marked open after round 3; this section is the high-tier and ultra evidence for the final lights.js.

### 4.9 Close-out round 5 (9 Nov 2026, runtime track): fatal hook, SSR occlusion, aureole footprint

- **`renderer3.fatal()` -> `R.onFatal`** (realtime C3F2.1): the message goes to the app's hook (`ui.fail`, which works
  after load) when one is set; the renderer's own `#loading` / `#r3fatal` text stays the fallback (no hook, or the hook
  throws). Stub-DOM check of the method's own source: before 0 hook calls, after 1 (`engine_closeout.md` R5.1).
- **SSR on wet pavement**: the IBL term it replaces is now subtracted with three's specular occlusion from the pre-pass
  GTAO (`engine.js aoScreen`, `ssr.js specularOcclusion`); E9 render: SSR darkening > 20 levels 186 -> 42 px, confined
  to the contact zones under bridges / aircraft / GSE (`environment_impl.md` close-out round 5, R5.1).
- **Fog aureoles**: phone core quad 2 radii again; the energy the rim, the tan-mapped billboard and the quad cut lose is
  folded back (`lights.js aurCoreGain / aurLobeGain`); test_c3 mirrors the shader (0.15 %). R5.2 there.
- **Old renderer**: `js/shaders/sprites.js` draws no halo for lens records (needs `js/scene.js` to pack `s.lens`: request
  `env_closeout.md` R5.2); `js/shaders/ground.js` path tone mixed by coverage (R5.4 there).
- **Terrain**: lake-box grid lines (`terrain.js buildMeshes lakeCell` 80 m): +14 % / +25 % vertices on high / low, built
  faster than before (R5.6 there). GPU cost of all of these: owner item OD-7.

## 5. Quality tiers (`engine.js QUALITY3`)

| Tier | Chosen for | Shadows | AO | AA | Bloom | Bakes (m/texel) | Max image texture |
|---|---|---|---|---|---|---|---|
| ultra | stills / QA (`?quality=ultra` or `?tier=ultra`; run once 5 Nov 2026: textures 1.9-2.2 GB, §4.8) | 3 x 4096², rig splits; floodlight spots 4096² | GTAO full res from a pre-pass + denoise | TRAA + CAS | yes (half res) | airfield 0.6, city 8192² | full |
| high | desktop, > 4 GB | 3 cascades x 2048², splits 1.4 / 5 / 16 x orbit distance (rig); 2 floodlight spots 2048² | GTAO from a pre-pass, half res + denoise | TRAA + CAS | yes (half res) | airfield 0.8, city 4096² | full |
| medium | <= 4 GB | 3 x 2048², same splits; 2 spots 2048² | same | TRAA + CAS | yes (half res) | 1.0, 4096² | 2048 |
| low | phones | 3 x 1024² (round 2: 2 cascades left rooftop units unshadowed): splits a = 0.8 r0, b = max(2.5 a, 0.8 r1), max(1.5 b, min(r2, max(700 m `shadowDist`, 1.6 r1))) of the rig's [r0, r1, r2]; 1 spot 1024² | the previous frame's GTAO (half res, from the MRT normal of the single pass, reprojected; no denoise pass) in the ambient term | TRAA + CAS | yes (quarter res) | 1.25, 2048² | 1024 |

Render-scale steps of the dynamic resolution: 1 / 0.85 / 0.8 / 0.72 / 0.6 / 0.5 / 0.4 (0.8 = the app's low-tier
`scaleMax`, added in round 3; phones rendered 0.72x where live.html renders 0.8x).

## 6. Not ported yet / known gaps

- `decal` items (stand centrelines; off by default in `js/live/world.js`) are not drawn.
- Smoke particles (`scene.smokeFns`, unused by the live app) are not drawn.
- The low tier's AO is the previous frame's GTAO in the ambient term without the denoise pass (an extra full-screen
  pass on the phone was not measured; phone performance is deferred by the owner, `docs/research/mobile_perf.md`).
- Aircraft `.sfom` -> `BufferGeometry` directly; the `.glb` + KTX2 path (engine.md §5) is not done. The texture memory
  (§4: about 500 MB on the low tier with every aircraft texture uploaded, as the old renderer did) is the main phone
  risk that KTX2 would remove.
- **WebGPU backend unverified.** `tools/build3/wgpu_run.mjs` reaches three's WebGPU backend on SwiftShader, but the
  device drops the instance ("A valid external Instance reference no longer exists") and the frames are blank
  (`out/engine2/wgpu3.log`). Still to do on a real GPU (desktop Chrome, then the owner's iPhone):
  - the swizzle patch;
  - the GTAO depth re-encode;
  - the reversed-depth TRAA patch;
  - device-loss recovery.
- Floodlight shadows only from the 2 masts that light the view most (`MastSpot`); the other masts' field passes through
  buildings and aircraft (GTAO darkens their direct and spread parts).
- Under-aircraft shade lacks the second bounce from sunlit concrete (§4.4).
- A dark smear on the apron at the B27 lead-in shows in every light. It is in the pavement wear map of the airfield
  bake, not the renderer (Inferred from its presence by day).
- Blender (tools/blender/): Cycles reference renders and baked-AO aircraft assets not started.
- `js/three/perf.js` (runtime perf flags + timing) is parked, not imported: phone performance deferred by the owner
  (`docs/research/mobile_perf.md`); `engine.js` keeps its two inert hooks (`Q.ao === 'none'`, `Q.aa === 'fxaa'`).
- Replicas of other tracks' logic (drift risk, parity checked by reading on 4 Nov 2026: no differences):
  `signs.js worldSignAtlasMap` / `locName` (js/live/signs.js `buildSigns` face list), `aircraft.js RegAtlas` and the
  LOD / livery-pending / tip-device / gear rules (js/live/models.js `registrationTexture`, js/live/aircraft.js `items()`).
  The exports that would remove them are requested (`docs/requests/engine_closeout.md`).

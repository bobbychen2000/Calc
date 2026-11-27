# Phase 3 (M2) — detailed-model runtime and the PC-12

Status 2026-11-14, after **OD4** (section 15: the owner asked for the original pc12 model at the pc12 viewer's fidelity;
earlier: review fix round 3 iteration 3, section 14, and sections 10–13). Package M2 of Phase 3a: the glTF runtime for the
hwd3d renderer (parser, kinematics, a drawable with the GaAircraft interface, a registry), the PC-12, a dev viewer with
headless stills, and Node tests. The SF50 (package M1, `tools/models/sf50/**`, `docs/phase3_sf50.md`) uses the same
conventions. **Current models: SF50 build sha256 49242e41… (7,051,212 B; fix round 3, `docs/phase3_sf50.md`) and the
PC-12 = the original `pc12/out/pc12.glb` @ f097de2, unchanged (sha256 87731cce…, 6,215,508 B; OD4, section 15)**; the
hwd3d-side variants fr2 / fr3 (sections 4, 10–14) are retired. Each image's caption in `docs/phase3/SOURCES.json` names
the model hash it shows (stills of earlier builds are marked superseded there), and `tools/models/test_models.mjs` fails
when a caption that claims the current model names another hash, or when `js/aircraft/models/SOURCES.json` disagrees with
the files (the first round presented a superseded SF50 build, 1806b9ea…, as the tested one). Nothing here is wired into
`js/live/**`: that is Phase 3b (exact diff in section 3).

## 1. Files (all new, M2)

| File | What |
|---|---|
| `js/aircraft/glb.js` | `.glb` parser + converter to hwd3d Geo data (Node-pure) |
| `js/aircraft/kinematics.js` | pivots → animation (Node-pure): gear + braces + doors, Fowler flaps, ailerons + tabs, elevators, rudder, ruddervators, stabiliser trim, propeller spin + blade pitch |
| `js/aircraft/detailed.js` | `DetailedAircraft` (GaAircraft interface + `setFlaps`, `setControls`), own programs `acobj` / `acglass` |
| `js/aircraft/models.js` | registry ICAO type → `{url, meta, groundGl, lightAnchors, frame}` (PC12, SF50), `MODEL_LOAD_OPTS`, `loadModel`, `createAircraft` (placeholder fallback), `withModelFrame` (traffic frame of a detailed type) |
| `js/aircraft/models/pc12.glb` | **since OD4 (2026-11-14) again the unchanged copy of `pc12/out/pc12.glb` @ f097de2 (87731cce…)**, as until fix round 1; in between (retired) builds of pc12's unchanged builders with the override sets `fr2` / `fr3` (fix round 3 iteration 3: 957b3c4e…; iteration 2: 6e349329…; fix round 3: c46fe4fb…; fix round 2: 9ccfd9a5…) |
| `tools/models/pc12/build_pc12_variant.py` | (fix round 2; **its override sets retired by OD4**, kept for the record and for `--set=none`, which reproduces the current model bit for bit) runs pc12's builders (python3 -B, nothing written into pc12/) with a documented override set, writes `out/pc12_<set>/` (gitignored) with the pc12 commit, a dirty flag and the sha256 of every pc12 source + of itself; `--set=none` reproduces `pc12/out/pc12.glb` bit for bit (checked: 87731cce…) |
| `js/aircraft/models/pc12_meta.json` | subset of `pc12/out/pc12_meta.json` (BOM, checks, wing, stats; OD4) + provenance (`_provenance.source` / `glb_sha256` name `pc12/out/pc12.glb`; `_provenance.reproduced`: the `--set=none` rebuild, identical) + the frame measured with the runtime's own options |
| `js/aircraft/models/SOURCES.json` | provenance of every model file (pc12 from the import; SF50 from its builder's `_provenance`, hash re-computed; refreshed after every SF50 build with `--sources-only`; checked by the test) |
| `tools/models/pc12/import_pc12.mjs` | the copy / subset / provenance step (refuses an uncommitted `pc12/out`); `--variant=out/pc12_fr3` (since fix round 2) imports a variant build and refuses it if its recorded pc12 sources were dirty or differ from the files on disk, or the builder changed; `--sources-only` refreshes the other models' SOURCES entries (now with the SF50 builder state and source-tree hash) |
| `tools/models/test_models.mjs` | Node tests (section 6) |
| `dev/model.html`, `dev/model.js` | viewer: one model, HWD world (or neutral pad), URL parameters, orbit / pinch, sliders; OD4: `look=studio`, the app's post grade |
| `dev/studio.js` | (OD4) `look=studio`: the pc12 reference viewer's lighting (RoomEnvironment env map + SH irradiance, sun, hemisphere, exposure, backdrop) on the hwd3d renderer, for 1:1 comparisons (section 15) |
| `tools/models/pc12/look_compare.py` | (OD4) side-by-sides reference \| hwd3d and same-pixel colour read-backs (section 15) |
| `dev/model_shot.mjs` | headless 1920×1080 stills (JPEG ≤ 600 kB), viewer screenshots; writes each image's caption (pose, time, model sha256, OSM / NAIP notice) into `docs/phase3/SOURCES.json` |
| `docs/phase3/pc12_*.jpg`, `docs/phase3/viewer_*.jpg` | renders (section 7; the SF50 stills from the hwd3d renderer are `viewer_sf50_*.jpg`, since `sf50_*` belongs to M1) |
| `docs/phase3/SOURCES.json` | (fix round 1) caption + licence notice + model hash of **every** image in `docs/phase3`; written by `dev/model_shot.mjs` (pc12_*, viewer_*), `tools/models/sf50/render_checks.py` (sf50_*), and once by hand for the render-check package's `render_*` |

Run:
```bash
python3 -B tools/models/pc12/build_pc12_variant.py --set=fr3   # 2.5 s -> out/pc12_fr3/ (gitignored); bit-identical rebuilds
node tools/models/pc12/import_pc12.mjs                  # the CURRENT PC-12 (OD4): plain pc12/out copy (committed state only), 87731cce…
python3 -B tools/models/pc12/build_pc12_variant.py --set=none   # optional: proves pc12's builders reproduce it (the import records it)
node tools/models/pc12/import_pc12.mjs --variant=out/pc12_fr3     # retired (fix round 3 iteration 3, 957b3c4e…)
node tools/models/pc12/import_pc12.mjs --sources-only   # after EVERY SF50 rebuild (SOURCES.json hashes)
node tools/models/test_models.mjs --json=out/test_models.json
node dev/model_shot.mjs --model=PC12 --out=docs/phase3 --prefix=pc12 [--set=standard] [--jobs=jobs.json] [--t=<ISO>]
node dev/model_shot.mjs --viewer=phone                                          # interactive viewer screenshot
python3 -m http.server 8800 --bind 127.0.0.1  # then http://localhost:8800/dev/model.html?model=PC12&cam=chase&gear=0.5&flaps=40&rpm=1700
```
The fix-round job files (`out/fr1/*.json`, `out/fr2/*.json`, `out/fr3/*.json`, `out/fr3i2/*.json`, gitignored) are reproduced in section 7.

## 2. Format and frames

**Input.** glTF 2.0 binary as written by `pc12/cad/glb.py` (the SF50 builder imports the same writer,
`tools/models/sf50/sf50_kernel.py`): one embedded buffer, `KHR_mesh_quantization` (SHORT normalized positions with the
dequantisation in the node translation / scale, BYTE normalized normals pre-multiplied by that scale, USHORT / UINT
indices), node TRS, PBR factor materials (no textures), part / pivot data in node extras. `glb.js` also reads FLOAT and
all normalized integer types, `byteStride`, sparse accessors, node `matrix`, `COLOR_0`, primitives without normals
(flat normals), and rejects any other required extension. Textures are not read (`stats.textured` lists materials that
have one; none in pc12).

**Axes.** glTF here: X = butt line (+ starboard), Y = water line (+ up), Z = station (+ aft), ground = 0 static on the
gear (`pc12/CLAUDE.md`). hwd3d aircraft local frame (`js/aircraft/placeholder.js`): +x forward, +y up, +z starboard.
`local = (−Z, Y, X) − origin` — a proper rotation (det +1), so winding is kept. Pivot fields that pc12 stores in
**model** axes (x station, y butt line, z water line: flap `travel`, brace `A`, `B0`, `K0`, `bend`; the SF50
`light_anchors`) are mapped model → glTF `(y, z, x)` first (`pc12/web/viewer/kinematics.js` header); a pivot or anchor may
say `axes: 'gl'` instead.

**Origin = main-gear ground contact, measured** (not a constant): for each `gear` pivot part, the lowest vertices of its
tyre material (`/^tire|^tyre/`) in the gear-down rest pose (mean of the vertices within 4 mm of the minimum); the
centreline unit is the nose (or tail) wheel, the outboard pair the mains; origin x / z = midpoint of the two main
contacts. Fixed-gear fallback: lowest tyre vertices per side. **Origin height (fix round 1)**: the registry's `groundGl`,
i.e. the source's own ground plane (both models: glTF Y 0, "static on the gear"), not the lowest tyre point. pc12 sinks
its tyres by a static deflection on purpose (`pc12/model/gear.py`: main axle WL 0.265 vs free tyre radius 0.2795 →
14.5 mm; nose axle 0.212 vs 0.2225 → 10.5 mm); with the old rule every PC-12 height in hwd3d was 14.5 mm above the pc12 /
POH attitude and the nose tyre floated 4 mm. PC-12 now: `origin_gl = (0, 0, 6.430)`; main contacts y −14.5 mm,
z ±2.265 (track **4.530 m**, POH / Pilatus 4.53); nose contact x **3.480 m** ahead (wheelbase, POH three-view 3.48),
y −10.5 mm; height **4.260 m** (Pilatus 4.26); propeller clearance **0.321 m** (sourced 0.32). The SF50's tyres touch its
ground (no deflection modelled): unchanged. **Gear sweep:** the lowest point over the whole retraction is 5 mm below the
gear-down contact (PC-12 nose wheel at gear 0.75; SF50 none), so Phase 3b starts a retraction only above ~0.05 m AGL.

**Materials → the obj material channel** (`js/shaders/objects.js`): vertex colour = `baseColorFactor` (linear) ×
`COLOR_0`; `ext = [roughness, metallic, mat id, emissive]`. Mat ids (`js/aircraft/models.js AC_MAT`, by material name):
21 paint (`paint_*`, `trim_*`), 22 avionics display (`screen*`), 23 interior (`leather|carpet|lining|wood|panel_black|
interior|seat|cabin`), else 0. Ids 21–23 are unused by the obj shader, so the obj program draws the same vertices with
its plain PBR path when the aircraft programs are not installed. `alphaMode: BLEND` materials go to a separate glass
mesh per group.

**Groups.** One mesh per *mover* (a part with a pivot; parts below it ride on it) plus one `static` mesh, each split
opaque / glass, all baked in the local frame at rest (gear down, surfaces neutral, doors closed). PC-12: 33 groups
(static 287,713 opaque + 31,735 glass triangles; door_airstair, door_cargo, 2 flaps, 2 ailerons, 2 aileron tabs, rudder,
rudder tab, stabiliser, 2 elevators, propeller hub, 5 blades, 3 gear legs, 2 nose doors, 2 strut-slot doors (iteration 3),
6 brace links). The pc12
`structure` part (frames / stringers / spars, inside the skins; the pc12 viewer shows it only in X-ray) is excluded by
the registry; everything else is drawn: **427,257 triangles, 259,557 vertices** (fix round 3 iteration 3, 72 parts;
iteration 2: 423,853 / 257,009, 70 parts; fix round 2: 410,834 / 250,968; fix round 1: 422,663 / 259,430) per type (shared by every aircraft of the type). SF50: 22 groups, 463,121 triangles, 284,128 vertices.

**Light anchors** (drawn kinds, `glb.js KINDS`: `navL navR tail beaconTop beaconBot strobeL strobeR strobeTail landL landR
taxi`; any other kind a model names, e.g. the SF50's `iceLight`, is kept in `model.lights`, not drawn), in order:
(0) registry anchors `MODELS[type].lightAnchors` (model axes, each with its source) for lamps the source model does not
draw; (1) node extras `light: '<kind>'` (anchor = node origin); (1b) part extras `light_anchors` / `info.light_anchors`
(model axes); (2) clusters of the lens materials `light_red` / `light_green` / `light_white` and `lens` on a gear part
(pc12/model/details.py, gear.py).
- PC-12, from (2): navL / navR at the wing tips (x 0.893, y 1.833, z ∓7.842; the wing raised in fix round 3), strobes at
  the tip trailing edges, tail light in the bullet tip (x −8.342), upper beacon on the bullet nose, lower beacon on the
  belly-fairing bottom (x −0.970, y 0.924), taxi = the nose-strut lamp (rides on `gear_nose`; off once the leg leaves the down lock).
- PC-12 **landL / landR (fix round 1; WL 1.148 since fix round 3, under the raised wing)**, from (0): the Pilatus "PC-12 NGX Model Building Plan" p. 4
  (https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf, photo
  "LANDING LIGHTS"; looked at in the review's scratch copy, not committed) shows a multi-LED lamp in a fairing under the
  wing beside a flap-track fairing [obs]. The close-up does not show the span station: the anchors sit just inboard of
  the middle flap-track fairing (STA 6.20, BL ±3.15, WL 1.148 since fix round 3, below the wing skin) [inf: position]. Sprites only:
  pc12 has no lamp geometry there (a pc12 owner item). Before, all three landing / taxi anchors collapsed onto the
  nose-strut lamp.
- SF50, from (1): nav / strobe / landing in the wing tips, tail, taxi (the nose-gear lamp, the AFM's "nose landing
  light"), **strobeTail** (fix round 1: drawn in phase with the tip strobes through `aircraftSprites`, so the 3
  anti-collision lights of the AFM flash; before, 2) and iceLight (kept, not drawn).

## 3. Interfaces

### glb.js
`parseGLB(buf) → {json, bin}` · `readAccessor(json, bin, i) → {data, size, count}` · `convertGLB(buf, {name, exclude,
matId, look, originGl, groundGl, lightAnchors, glassToOpaque, groupBy: 'mover'|'part'}) → AircraftModel {name, originGl,
contacts {mainL, mainR, nose}, wheelbase, track, bbox (local, rest), parts [{id, name, group, parent, node, pivot
(local), mover, tris, extras}], partIndex, groups [{key, mover, opaque, glass, bbox}], lights, regPanels [{part, mover,
centre, normal, up, textDir, length, height, note}] (blank registration areas, never filled here: D1; fix round 1 keeps
every builder field, text_dir was dropped), materials, stats}`. GeoData is exactly `Geo.data()` (`pos nrm col extra uv
idx bbox`) plus `mat` (per-vertex material index, CPU only). `KINDS` is exported. OD4 iteration 6: `lampTables(model,
{yieldMs, NA, NE}) → Promise<{ms, rays, lamps, bladeTris, voxels}>` sets `lights[k].occ.vis = {NA, NE, data}` (each drawn
lamp's self-visibility table, RGBA8: seen share gear down / up, the farthest occluder of the direction, section 15.10, and -
round 2, 15.11 - the aircraft's reach in front of the lamp; the propeller blades are not occluders; needs the CPU geometry),
`lampVisLookup(vis, shape, dir, gearUp)` / `lampVisFar(vis, shape, dir)` / `lampVisReach(vis, shape, dir)` (the GPU's
bilinear lookups, for tools and tests), `LAMPVIS` (grid, ray, distance and reach constants). Round 3 (15.12): the tables are
of the DRAWN pose (`kinematics.js` pose gear 1 / gear 0; glb.js imports kinematics.js), `lampTables(model, {yieldMs, NA, NE,
flaps})` also sets `occ.visF = {set, tables, dmax} | null` (one table per tabulated flap setting, for a lamp whose seen share
the flaps change) and returns `flapSet`, `flapLamps`, `posed`; `lampFlapSettings(model)`, `lampFlapX(set, flaps)` (the flap
position in the tables) and `lampVisState(shape, dir, gearUp, flapX)` (the shader's mixed lookup) are exported.

### kinematics.js
`new Kinematics(model).pose(state) → Float32Array[16] per part` (column-major; the motion of each mover, local rest →
local posed; parents first). `state = {gear 0..1 (1 down), flaps deg, rotorAng rad, bladePitch deg, roll, pitch, yaw
(−1..1), stabTrim, ailTrim, rudTrim deg, doors {part id: 0..1}}`. Pivot kinds and laws (the pc12 viewer's, ported):

| kind | law |
|---|---|
| `spin` | rotation `rotorAng` about `axis` (PC-12: axis forward, + = clockwise seen from the cockpit) |
| `pitch` | `bladePitch` clamped to [`reverse`, `feather`] (PC-12 −38 / 62) |
| `flap` | rotation = flaps (≤ `max`) and translation `travel × flaps / max` (Fowler; PC-12 travel 0.345 m aft, 0.060 m down at 40°) |
| `aileron` | + = TE down; cmd = −`sign` × roll; d = cmd ≥ 0 ? cmd × range[1] : −cmd × range[0] (PC-12 −20 / +15) |
| `tab` | `gearing` × parent deflection (+ `ailTrim` on the left aileron tab, + `rudTrim` on a rudder tab), clamped to `range` |
| `elevator` | pull (pitch > 0) = TE up = range[0] |
| `rudder` | yaw > 0 → range[1] (TE to starboard) |
| `ruddervator` | pitch term (`pitchRange`) + `side` × yaw × `yawGain`, clamped to `range` (SF50 builder: ±9° yaw [inf mixing law]) |
| `trim` | `stabTrim` within `range` (PC-12 −4 / +2: LE down = nose up) |
| `door` | `open` (rad) × eased door fraction |
| `gear` | `retract` (deg) × `gearSequence(gear).leg` |
| `gear_door` | `open` (deg) × door; `seq: 'transit'` (default; PC-12 nose clamshells: open only between the locks) or `'down'` (open whenever the leg is out; SF50 nose doors, PC-12 strut-slot doors since fix round 3 iteration 3) |
| `brace` | upper link about A, lower link about the knee; B = `B0` carried by the gear leg's pose; knee = `solveKnee` (port of `pc12/model/brace.py`) on the `bend` side |

Sign convention of every surface: + = trailing edge down (toward the surface's lower side); since fix round 1 the test
**measures** each surface's sign from its trailing-edge motion and compares the travel limits with the certificate.

`gearSequence(gear)`: s = 1 − gear; doors open over s 0…0.12, legs travel (smoothstep) over 0.12…0.88, doors close over
0.88…1. traffic.js ramps `gear` over 6 s, so doors take 0.72 s and the legs 4.6 s [inf: the POH gives no timing; the pc12
viewer uses 0.8 s + 4 s].

### detailed.js — `DetailedAircraft`
**OD4 (2026-11-14):** the `acobj` / `acglass` shading described below (clear-coat lobe, interior ambient × 0.4, glass
tint lit at 0.15) was replaced by the glTF metallic-roughness BRDF, hemisphere view factors with the pavement ground,
the cabin lit through the glazing and glazing as a thin sheet (section 15.3); items carry `uCabinT` / `uCabin` /
`uEmissiveBoost` on every draw; `SYNC_KEYS` includes `groundRef`.
Same public interface as `GaAircraft` (`js/aircraft/placeholder.js`): constructor `(T, {model, R, id, colour, lodDist,
shadowDist, propBlur})`; fields `pos, fwd, pitch, roll, gear (1 = down), rotor (rad/s), rotorAng, visible, selected,
alpha, lightsOn, T, ready, lodDist, shadowDist, model, prevModel`; methods `items(camPos)`, `lightSprites(t)`, `step(dt)`,
`commit()`, `worldPt(p, mover)`, `dispose()`. Added: `setFlaps(deg, instant)` (moves at 11°/s [inf, pc12 viewer]),
`setControls({roll, pitch, yaw, stabTrim, ailTrim, rudTrim, bladePitch, doors}, instant)` (first-order lag 7/s on roll /
pitch / yaw [inf]), `state()`, `loaded`, `error`, `info`. Until the model resolves — or if it fails — it draws a
`GaAircraft` of the same dims record; `SYNC_KEYS` (every field js/live/aircraft.js sets; `alpha` added in fix round 1)
are copied to it every frame. `basis()` is GaAircraft's (pitch / roll about the main-gear contact).

**Fade (fix round 1).** Every item carries `alpha`, the screen-door fade js/live/aircraft.js sets on a re-placement:
`acobj` discards with the obj shader's 4×4 ordered dither (`uAlpha`, which the renderer sets from `it.alpha`), `acglass`
multiplies its blend alpha by `uAlpha`, the `obj` fallback and the placeholder already read it. Before, a detailed
aircraft popped in and out at full opacity (review probe: 0 of 35 / 25 items carried alpha). `pc12_fade.jpg` /
`viewer_sf50_fade.jpg` show alpha 0.5. **Shadow (fix round 2)**: the renderer's shadow program is `void main(){}`, so the
full shadow appeared at once under a fading aircraft. `installAircraftPrograms` now gives `acobj` its own shadow half
(`ACOBJ_SHADOW_FS`: the same 4×4 dither on `uAlpha` in shadow-map texels; the renderer already sets `uAlpha` on any
program that declares it, in both passes), so the PCF shadow darkens in proportion to alpha; the `obj` fallback and the
placeholder path cast only from alpha 0.5 (half way through the fade). No renderer change needed; a general `uAlpha`
dither in `renderer.js SHADOW_FS` for every program (placeholders of all types) is proposed in section 8.

Draw items per aircraft: one `acobj` item per group (31 for the PC-12; `noCull`: every pc12 material is doubleSided), one
`acglass` item per group with glass (4), the propeller disc when spinning: **≤ 36 items**. Shadow casting below
`shadowDist`. **Motion vectors (fix round 1, completed in fix round 2):** each group keeps its own `prevModel`; groups
below a spinning `spin` mover (rotor ≥ 25 rad/s), and the disc, get `prevModel = previous aircraft model × current pose`:
the aircraft's translation and attitude change stay in the velocity, the rotor rotation (~340° per 30-fps frame at 1,700
rpm) is left out. Fix round 1 keyed this on the propeller disc (`res.prop`), which the SF50 fan does not have (no blade
movers), so the fan groups kept their true previous-frame rotation: 0.31 m (40 rad/s) / 0.42 m (59 rad/s) of false motion
0.25 m off the axis (review probe; latent while shutter = 0). Since fix round 2 it is keyed on the `spin` mover itself
(`res.spin`); the test probes a point 0.25 m off the axis at 40, 59 and 178 rad/s (fix round 1 probed a point on the axis,
which no rotation moves): 0 m standing still, 2.00 m for a 2 m move, both types. **CPU memory (fix round 1):** a model
loaded by `loadModel` (the app; `keepCpu` false) drops its vertex / index arrays once they are on the GPU (~21 MB of JS
heap per type); the dev viewer passes `keepCpu: true`. Pose cost (Node, `kin.pose`): **0.03 ms** per aircraft per frame;
model conversion 0.3 s once per type.

`installAircraftPrograms(R)` (called by the constructor when `R` is given) registers, from shader strings in
`detailed.js` that include only the existing chunks (`common`, `shadow`, `vout`, `fout`):
- **`acobj`** (opaque): the obj shader's PBR path + mat 21 paint with a clear-coat lobe (F0 0.04, roughness 0.05
  [inf]); back faces of paint and mat 23 interior with ambient × 0.4 / specular occlusion 0.35 [inf] (the closed cabin
  seen through the glazing); mat 22 displays self-lit (~0.2 scene units by day [inf]); the `uAlpha` screen-door fade.
- **`acglass`** (blend `alpha`, `bothPasses` with the cloud shader's view-depth range rule, sorted by distance): thin
  dielectric glass — Fresnel sky reflection + sun glint (shadowed) over the material's tinted absorption
  (alpha = F + (1 − F) × base alpha; pc12 glass 0.80 / windshield 0.82), so the flight deck and cabin show through; and
  the **propeller disc** (radial coverage, five soft blade sectors drifting at ≤ 2.5 rad/s, a light tip band from the
  blade-tip material): blades fade out and the disc fades in between 25 and 60 rad/s [inf: a 30-fps-camera picture, not
  physics]. The hub / spinner keeps its true angle. Both kinds × `uAlpha`.

### models.js
`MODELS {PC12, SF50}` · `hasModel(type)` · `MODEL_LOAD_OPTS(type)` (the convertGLB options of a registered type: the app,
the tests and the import use the same) · `loadModel(type, {fetchFn, keepCpu}) → Promise<AircraftModel>` (cached per
type) · `createAircraft(T, opts)` → `DetailedAircraft` when `T.type` has a model, else `GaAircraft` · `AC_MAT` ·
**`modelDims(type, category)`** (fix round 2) = `withModelFrame(gaDims(type, category))`, the one call Phase 3b puts in
place of every `gaDims` call in `js/live`. **`withModelFrame(T)`** (fix round 1): the dims record with `L, span, H, xMain` (nose tip → main-gear contact), `xNose`
(nose tip → nose-wheel contact, the js/live/ground.js meaning) and `track` replaced by the model's measured frame
(`MODELS[type].frame`, constants the test compares with the GLB to 5 mm); `ant` (GNSS antenna behind the nose, class rule)
is kept, so `xMain − ant` becomes the model's antenna → origin offset; frozen, cached per record, `dimsBase` = the
original. Synchronous, so traffic can use it before the GLB has loaded.

| type | field | gaDims (class rule) | model frame | gaDims − model |
|---|---|---|---|---|
| PC12 | xMain | 6.488 | 6.040 | +0.448 |
| PC12 | xNose | 3.008 | 2.560 | +0.448 (wheelbase 3.48 and track 4.53 agree) |
| PC12 | antenna → main | 1.010 | 0.562 | +0.448 |
| SF50 | xMain | 5.146 | 4.453 | +0.693 |
| SF50 | xNose (wheelbase) | 1.123 (4.023) | 1.148 (3.305) | −0.025 (+0.718) |
| SF50 | track | 3.185 | 3.414 | −0.229 |
| SF50 | antenna → main | 1.403 | 0.710 | +0.693 |

**FAA ACD gear columns** (recorded in fix round 1; read from `sfo3d/refs/cache/faa/faa_aircraft_char_database.xlsx`,
sheet ACD_Data; its Data_Dictionary: `Wheelbase_ft` "the distance between main gears and nose gear/gears",
`Main_Gear_Width_ft` "Distance between outer tires in the main landing gear"): **PC12** `Wheelbase_ft 10.2` (3.109 m),
`Cockpit_to_Main_Gear_ft 7`, `Main_Gear_Width_ft 15.2` (4.633 m; the model's outer-to-outer width is 4.53 + 0.216 =
4.746 m); **SF50** 10.9 (3.322 m), 10.9, 12.7 (3.871 m; model 3.556 m). The PC-12 ACD wheelbase conflicts with the POH
three-view 3.48 m kept in pc12/CLAUDE.md (the review's estimate from Pilatus drawing 190.10.40.432 agrees); both ACD outer
widths conflict with the manufacturers' tracks (centre to centre). Kept: the POH / AFM values; the ACD gear columns are
not used (the SF50 row repeats 10.9 ft in three columns; its wheelbase agrees with the AFM-derived 3.305 m to 17 mm).

**Wiring for Phase 3b** (`js/live/**`, not touched here). Proposed change — fix round 2: `js/live/traffic.js` makes a dims
record in **two** places, the live track (line ~395) and the localStorage parked-aircraft restore (line ~1577); fix round
1's diff named only the first, which would have left a restored parked SF50 on the class-rule layout (xMain 0.69 m, track
0.23 m off). `tools/models/test_models.mjs` lists every `gaDims(` call in `js/live` and fails while a call is missing here:
```diff
 // js/live/traffic.js line 28:
-import { gaDims } from '../aircraft/ga_dims.js';
+import { modelDims } from '../aircraft/models.js';    // = withModelFrame(gaDims(type, category))
 // js/live/traffic.js line ~395 (live tracks):
-    if (dk !== tr._dimsKey) { tr._dimsKey = dk; tr.dims = gaDims(I.icao, I.category); }
+    if (dk !== tr._dimsKey) { tr._dimsKey = dk; tr.dims = modelDims(I.icao, I.category); }
 // js/live/traffic.js line ~1577 (parked aircraft restored from localStorage):
-        ... tr.dims = gaDims(icao, cat);
+        ... tr.dims = modelDims(icao, cat);
 // js/live/aircraft.js AircraftViews.sync, where the drawable is made:
-  v = new GaAircraft(tr.dims, { id: tr.key, lodDist: …, shadowDist: … });
+  v = createAircraft(tr.dims, { R: this.scene.R, id: tr.key, lodDist: …, shadowDist: … });   // import from '../aircraft/models.js'
+  // per frame, for a DetailedAircraft (v.setFlaps): v.setFlaps(deg), v.groundRef = site.groundY(D.x, D.z), v.rotor (fixed wing)
```
`alpha` and every other field the view sets already reach both drawables. Flaps: PC-12 settings 0 / 15 / 30 / 40 in its
pivot, SF50 `max` 39 (TCDS 15 / 39). `rotor` for fixed-wing types: PC-12 `pivot.rpm` 1,700 → 178 rad/s; idle / taxi rpm
and the SF50 N1 → fan speed are not sourced. Start a gear retraction only above ~0.05 m AGL (section 2). ground.js then
separates the drawn body (nose / tail / gear contacts from `xMain`, `L`, `track`, `xNose`) and traffic.js `toOrigin` uses
`xMain − ant` of the model.

## 4. The PC-12 import
**OD4 (2026-11-14): the current PC-12 is again `pc12/out/pc12.glb` @ f097de2, unchanged (87731cce…; section 15).** The
override sets described below (fr2, fr3) are retired; the text is kept as the record of what they changed and why (their
measured deviations of the original from the Pilatus drawing are now the KNOWN items of `tools/models/test_models.mjs`).

**Until fix round 1** `pc12/out/pc12.glb` @ **f097de2** (2026-11-08) was copied unchanged. **Since fix round 2** the PC-12 is
a build of **pc12's own, unchanged builders** (pc12/model, pc12/cad @ HEAD; `git status --porcelain pc12` empty) run by
`tools/models/pc12/build_pc12_variant.py` with a documented override set (module constants and a few builder functions
replaced before the build; nothing written into `pc12/`, Python run with `-B`), output in the gitignored `out/pc12_<set>/`,
imported with `node tools/models/pc12/import_pc12.mjs --variant=out/pc12_<set>`. **Current: set `fr3` as revised in review fix
round 3 iteration 3, `js/aircraft/models/pc12.glb` sha256 957b3c4e…** (iteration 2: 6e349329…; fix round 3: c46fe4fb…; fix
round 2: `fr2`, 9ccfd9a5…). The `none` set still reproduces `pc12/out/pc12.glb` bit for bit (87731cce…, re-checked in
iteration 3) and `fr3` rebuilds bit-identically (957b3c4e… twice), so the overrides are the only difference. Provenance in `pc12_meta.json` `_provenance.variant` and `SOURCES.json`: the override values, the
builder's sha256, the sha256 of every pc12 source it ran and their tree hash, `pc12_sources_dirty: false`; the test fails if
any of them changes on disk. pc12's own method (drawings first, owner review) applies to `pc12/`; the overrides are
hwd3d's corrections, proposed to the pc12 owner for adoption. Livery: pc12's original neutral scheme (white, cool-grey belly,
navy swoosh, brass pinstripe; `pc12/model/livery.py`), no registration, no logo (D1). Dimension and configuration facts and
their sources stay in `pc12/CLAUDE.md` ("Sourced facts"); they are unchanged: length 14.400, span 16.280 (+0.2 mm), height
4.260, tailplane span 5.200, wing area 25.81 m², track 4.530, wheelbase 3.480, prop diameter 2.668, prop clearance 0.321 m.

**Reference: Pilatus drawing 190.10.40.432** ("PC-12 MODELL ZEICHNUNG / MODEL DRAWING SN2001UP", sheet 1 of the Pilatus
"PC-12 NGX Model Building Plan", https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf),
digitised in fix round 3 from its **vector strokes** (no raster): side view (scale least-squares on the ten labelled frame
lines, residuals < 0.05 mm on the sheet; station from the spinner tip at STA 0.39, pc12's anchor; WL 0 = the drawn ground line,
on which both tyres stand), plan view, front view (track dimension, WL 0 = the tyre bottoms; its propeller disc then sits on
the side view's prop axis) and the body-plan sections EF2 … FR40 (same scale; their common reference line is the side view's
WL reference, so the FR16-30 section spans exactly the side view's keel-to-crown). Starboard windows: MBP p.5 livery sheet
(fix round 2; the two Pilatus documents disagree on the starboard side, the livery is used). **Decision (b), 2026-11-13
(orchestrator, under the owner's delegation; the owner may overrule; `docs/PLAN.md` §6b): the digitised readings and the
registration numbers are not committed.** They live in the gitignored `refs/cache/local/models/pilatus_pc12_meas.json`
(written by the local `refs/cache/local/models/tools/measure_pc12_mbp.py --pdf <the PDF>`, also gitignored; PDF sha256 in the
file); `tools/models/test_models.mjs` compares the model with it and prints SKIP when it is absent (a clean clone never
fails). The builder holds only the fitted model parameters (knots, stations, sizes) with a one-line basis each.

**Override set `fr3`** (each block in `build_pc12_variant.py`; fr2's stations and dihedral kept):
- **Fuselage loft (finding P2)**: pc12's control lines replaced aft of the nose — crown, keel and half-breadth knots
  least-squares fitted to the drawn profile and plan outline (fit residual rms ≤ 4 mm; knots rounded to the millimetre in
  iteration 2, < 0.5 mm change), max-breadth WL and the upper / lower super-ellipse exponents from fits to the body-plan
  sections FR10 … FR38 (rms 3–9 mm each); pc12's knots at STA ≤ 2.80
  (keel ≤ 2.60) and its tail-cone end are kept, so the cowling, the propeller axis (WL 1.655) and the 14.40 m length are
  unchanged. Cabin: crown WL 2.769, keel 0.939, flat-bottomed section (n_bot 3.2 vs pc12 2.45); aft fuselage slimmer (plan)
  and higher underneath, as drawn. The flight deck and the livery lines, which pc12 places at absolute heights, are
  carried by a station-wise map from the old to the new section (same fraction of the upper / lower half-height, butt line
  scaled with the half-breadth); the flight-deck floor follows that map and slopes ~7° up aft [inf]. **Cabin (iteration 2,
  finding F2)**: pc12's construction at one floor height, the map's at STA 6.0 (WL 1.244; the map is constant over STA
  4.46–8.23), the floor one flat panel **1.300 m wide (sourced 1.30)**, seats / club tables / baggage net 0.40 m aft and
  the port side ledge between the doors, so the airstair and cargo doorways at their drawn stations are clear [inf:
  layout] (fix round 3 had mapped pc12's cabin vertex by vertex: a panel 1.257 m wide warped from WL 1.244 up to 1.371 aft,
  seat rails 65 mm and ledges 40 mm under its top, the port ledge across both doorways). `pc12/test/fit_check.py`'s check
  passes on the build (interior and engine inside the skin). pc12's floor-width proxy (OML at WL 1.12 − 2 × 45 mm) does not
  hold for the flatter section: the meta's check measures the floor panel as built (1.300 m) and records a 2 % tolerance,
  which `tools/models/test_models.mjs` enforces. **Carry-through under the floor (iteration 3, finding F4)**: the raised
  wing's upper skin came up to 14 mm through the carpet (STA 5.80–6.46, |BL| ≤ 0.64, 0.74 m², 0.32 m² of it in the aisle);
  inside the fuselage the wing's upper skin and pc12's spar tops (structure) are now held 5 mm under the floor panel's
  underside (WL 1.209 = floor top 1.244 − 30 mm panel − 5 mm) inboard of BL 0.66, blending linearly back to the unchanged
  wing by BL 0.75 (extra skin stations at BL 0.66 / 0.705 / 0.75), inside the fuselage side (OML BL ≈ 0.77 at that
  height), so nothing changes outside [inf: structure]; 296 vertices lowered, by up to 48.6 mm.
- **Cockpit glazing**: windshield plan outline and A-pillar line, side window (a rounded polygon) fitted to the drawing's
  side and plan views; the PRO has no pilot DV window (the NGX drawing shows one: not modelled); fwd / centre skin joint
  moved to STA 4.42 so the side window lies in the forward skin.
- **Openings at the drawn water lines**: window centre WL 2.187 (fr2: 2.047 relative to pc12's lower crown), outline
  0.300 × 0.384 m; airstair door centre WL 1.928, cargo door 1.892 (sourced 0.61 × 1.35 / 1.35 × 1.32 m openings on the drawn
  centres), exit centre 0.569 m below the crown.
- **Wing and gear**: fr2's 6.2° dihedral, the wing raised 0.121 m (mean offset of the drawn front-view outlines from the
  fr2 wing); the reference plane is flat inboard of the fuselage side (BL 0.85) [inf], so the carry-through stays inside the
  drawn belly fairing. Main-gear trunnion +0.104 m (17 mm less than the wing, so the retracted tyre still protrudes 11 mm as
  in fr2; POH ~1 in), legs longer by that, side-brace attachments raised with it, wheel well 0.104 m inboard (where the longer
  leg folds the wheel). Track 4.53, wheelbase 3.48, prop clearance 0.321 unchanged. Landing-light anchors in
  `js/aircraft/models.js` follow the wing (WL 1.148).
- **Nose-gear housing**: with the keel at the drawn height the retracted nose wheel (pc12 geometry) reaches below it and
  needs the box the drawing shows under the cockpit: an open-topped housing, front station and bottom fitted to the drawn
  box, with pc12's clamshell doors moved to its floor and the bay liner extended to it. Iteration 2 (finding F5): lower
  edges rounded (super-ellipse section, exponent 3; width not drawn: bay + 0.10 m each side [inf]), the rear end 5 cm aft of
  the drawn one so the bay opening lies on the flat floor and the end wall no longer coincides with the bay liner [inf], the
  doors follow the curved floor, and a slot (STA 2.905–3.135, ±0.08 m) through the housing floor and the doors' forward
  inner corners lets pc12's strut and taxi lamp pass with the gear down (fix round 3: 104 edge crossings at gear 1);
  the liner's lower edge sits 3 mm inside the housing skin (fix round 3: 6 mm below it, a lime line). **Iteration 3
  (finding F3)**: the slot was a permanent hole - with the gear up the zinc-chromate liner and the stowed strut showed
  through it from below. Two **strut-slot doors** (`gear_door_NSL` / `gear_door_NSR`: the slot outline less 4 mm, split at
  the centre line, 18 mm solid on the housing's curved floor) now close it with the gear up; hinged on their outer edges
  (BL ±0.076), they open 85° whenever the leg is out of the well (pivot `seq: 'down'`, like the SF50's nose doors) and hang
  beside the strut (nearest strut vertex 8.6 mm away at gear 1, 12 mm at gear 0.75; no crossing) [inf: the PC-12's slot closure is not documented; POH: the nose gear is "enclosed by
  doors"]. The clamshells' notch is now the slot outline itself (4 mm from the slot doors, as the doors are from the bay
  opening). The bay liner's front wall (STA 3.02) gets a notch over the slot width up to WL 1.15, so neither the closed slot
  doors nor the strut (gear down; pc12's own crossing, 90 edges at gear 1) pass through it. All four nose doors hinge on
  their outer face (pc12 / iteration 2: mid-thickness, so the hinge-side edge swung 9 mm outboard into the housing floor
  while open in transit: 876 edge crossings at gear 0.75 / 0.5). Strut, braces, doors, housing and liner: 0 crossings at
  gear 1 / 0.75 / 0.5 / 0.25 / 0 (`out/fr3i3/probe/edge_hits.py`, both directions).
- **Belly fairing (finding P1)**: pc12's `details.belly_fairing` (fixed heights) replaced: drawn extent STA 5.12–7.50 and
  centre-line lower outline (side view). Section (iteration 2, finding F6): the lower surface runs from the drawn bottom on
  the centre line (or 3 mm under the surface it covers where that is lower) to 3 mm under the surface it covers (wing lower
  skin, else fuselage underside) at its edge, as (1 − t²) of the local half-width [inf: shape], so it meets the wing at a
  shallow angle instead of the fix-round-3 vertical side wall (a lip up to ~5 cm aft); no wing point hangs below it within
  its width (fr2: 65.6 mm at STA 5.9, BL 0); the lower red beacon sits on its bottom.
- **Belly antennas (iteration 2, finding F7)**: each centre-line blade (pc12 `details.blade_antenna`) is turned about its
  root leading edge to the mean skin slope along its root chord (mounted normal to the skin [inf]) with the root's residual
  to the skin line added: on the re-fitted aft belly the VHF 2 root had floated up to 28 mm under the skin.
- **Dorsal fin**: top edge as drawn, from the crown at FR33 (STA 9.0; pc12 10.35) to the fin leading edge; base half-width
  ~0.1 m (FR38 / FR40 sections). **Fin LE** moved 0.14 m forward onto the drawn line. **Ventral strakes** at the drawn
  stations (STA 9.8–12.2; pc12 12.35–13.75), root on the fuselage side, outer edge 0.15 m out [inf].
- **Winglet (finding P3)**: chord and trailing-edge laws, top chord and the straight-part height (0.262 m, pc12 0.30)
  fitted to the drawing's side view (leading / trailing edge within 3 cm at WL 1.94–2.10); planform re-derived so the span
  over the winglets stays 16.28 m and the area 25.81 m².

**Before → after** (fix round 2 build 9ccfd9a5… → fix round 3 c46fe4fb…, model − drawing, measured by
`tools/models/test_models.mjs` and `out/fr3/meas_glb.py`): crown along the cabin −139…−141 mm (windshield region −27…−116)
→ |≤ 3| mm; keel −139 mm (−52…−135 under the cockpit) → |≤ 2| mm; aft underside −161 (FR30) … −339 (FR38) … −114 mm (STA
12.9) → |≤ 1| mm; half-breadth up to +232 mm aft of FR33 → |≤ 9| mm; body-plan sections rms 30 (FR10) … 180 mm (FR38) →
3–9 mm (max ≤ 25 mm); dorsal fin: nothing above the crown before STA 10.5, top edge up to 449 mm low → starts where drawn
(within 1 cm), top edge |≤ 6| mm; window centre WL −142 mm → −2 mm; airstair / cargo door centre −153 / −112 mm → 0 / 0;
wing outline offsets 0.117 / 0.126 m low → −0.002 / +0.007 m, crown 0.138 m → 0; winglet top chord 0.31 / 0.38 m forward →
leading / trailing edge within 30 mm at WL 1.94–2.10; wing skin below the belly fairing 65.6 mm → none (closest 6.5 mm
inside; iteration 2 with the blended section: 1.7 mm); retracted trailing-link arm 51 → 58 mm (KNOWN, pc12 gear geometry), tyre protrusion 11 → 11 mm.

**Not changed (measured, open, pc12 owner items)**: the rudder trailing edge is drawn 0.3 m (top) to 0.75 m (bottom) further
forward than pc12's fin / rudder planform, with the tail cone ending at the rudder's lower corner (~0.75 m forward of
pc12's tail-cone end); the drawn
tailplane leading edge is ~0.3 m forward of pc12's (larger root chord); the lower cowling (STA 1.2–2.6) is drawn up to
0.13 m lower than pc12's (its chin inlet and engine installation are built around it); the wing planform is drawn ~0.15 m further aft than pc12's POH-derived position — all pc12 "estimated" items left
as they are here (section 9). Overlays of the build on the registered drawing (side, plan, front, sections) are
in the gitignored `out/fr3/ov_*.png`.

## 5. Dev viewer (`dev/model.html`)
URL parameters (header of `dev/model.js`): `model`, `cam` (front34, rear34, side, chase, front, top, gear, nose, tail,
under) or `eye=x,y,z&tgt=x,y,z&fov=` in the aircraft frame, `gear`, `flaps`, `rpm` / `rotor`, `bpitch`, `ctl=roll,pitch,
yaw`, `trim`, `doors=part:0..1`, `at=ramp|run28L|rwy28L|x,z`, `hdg`, `alt`, `apitch`, `aroll`, `t`, `metar`, `lights`,
`alpha` (fix round 1: the screen-door fade), `world=0`, `scale`, `shot`. The dims record is `withModelFrame(gaDims(type))`
and the model is loaded with `keepCpu: true`. The HWD world comes from `buildSite` + `buildHwdWorld` (NAIP ground,
buildings, markings), environment from `AppEnv` + `applyEnvToRenderer` (default 2026-11-13 12:30 PST, a KHWD-format
METAR), renderer at one quality (MSAA 4, 4096² shadow cascades with splits scaled to the camera distance). If any world
module fails, a 300-m concrete pad and the same sky are used (`world=0` forces it). `ramp` = the Green Ramp centroid;
`rwy28L` = 300 m past the 28L threshold on the centreline, runway heading. Presets are framed for the PC-12 and scaled by
the model's length for other types (a custom `eye` / `tgt` is not). `window.HWDM.set({...})` re-poses without a reload;
`HWDM.itemProgs()` lists the draw items. Interaction: drag = orbit, wheel / pinch = zoom, preset buttons, sliders for gear
/ flaps / rpm / roll / pitch / yaw, "cycle gear" (6-s ramp like traffic.js). OD4: `look=studio` (`dev/studio.js`) draws
the aircraft under the pc12 reference viewer's lighting instead of the world (section 15.2); the post grade is the app's
(sat 1.05, grain 0); `dev/model_shot.mjs --format=png` writes lossless stills and `--look=studio` passes the look.

## 6. Tests (`node tools/models/test_models.mjs`), results 2026-11-14 after fix round 3 iteration 3

**OD4 (2026-11-14; PC-12 = original 87731cce…, SF50 49242e41…): see section 15.4 for the current result.** The table
below is of the retired fr3 build.

**Fix round 3 iteration 3 (current models: PC-12 957b3c4e…, override set fr3; SF50 49242e41…, `docs/phase3_sf50.md`).**
Result: **85 PASS, 1 KNOWN** (the retracted trailing-link arm, 58 mm, pc12 gear geometry; limit 70), **0 FAIL**, 4 INFO,
with the local reference data present; clean clone (a copy of the test pointed at an empty local-reference directory,
deleted after the run): **72 PASS, 13 SKIP, 1 KNOWN, 0 FAIL** (2026-11-14 00:30Z). **Since 00:32Z 1 FAIL that is not a
Phase 3a item**: the video pipeline's rewrite of `docs/phase3_video.md` (Phase 3b, edited concurrently, not touched here)
records its frozen app snapshot with `pc12.glb` 6e349329… and no longer carries the iteration-2 SUPERSEDED line for the
PC-12, so "docs/phase3_*.md name the current model hashes" fails on it (84 PASS / 71 PASS + 13 SKIP, 1 KNOWN, 1 FAIL). Fix
on that page: name the current 957b3c4e… (e.g. "the current pc12.glb is 957b3c4e…; re-snapshot before the full render")
or a "PC-12 … SUPERSEDED" line in its head, or take the new snapshot it already plans. New in iteration 3: "gear retracted: nose-gear housing closed
from below" (F3), "cabin floor: no other part rises through the carpet" (F4) and the decision-(b) token grep (F1); the
iteration-2 PC-12 build (6e349329…) fails the first two (202 bad cells, 138 inside an area: liner 76 + strut 126 cells,
STA 3.03–4.26; wing through the carpet in 1,798 cells of 2 cm = 0.72 m², 748 in the aisle, up to 13.5 mm at STA 6.16).
Iteration 2 (PC-12 6e349329…): **82 PASS, 1 KNOWN, 0 FAIL**, 4 INFO,
with the local reference data present. The checks against digitised manufacturer drawings read the gitignored local
reference files (`refs/cache/local/models/pilatus_pc12_meas.json`, `afm_sf50_meas.json`; decision (b), section 4) and print
**SKIP** without them: a clean-clone run (the test pointed at an empty local-reference directory) gives 69 PASS, 13 SKIP
(9 PC-12 + 4 SF50, "local reference data not present"), 1 KNOWN, **0 FAIL**. The belly-fairing coverage, the cabin floor,
the window count and the SF50 nacelle geometry are geometry-only and always run. New in iteration 2: the PC-12 cabin floor
check (F2), the SF50 nacelle check split into a geometry check and an AFM check (F1), the per-type SUPERSEDED rule for
write-ups (F3). Columns below: earlier values where a row did not change, current values in **bold**; drawing / AFM checks
quote deviations only (decision (b)).

| Check | PC-12 | SF50 |
|---|---|---|
| parse + convert | **427,257 tris, 259,557 verts, 72 parts (+ nose-gear housing; iteration 3: + 2 strut-slot doors)**, 33 groups, 0 bad indices / normals | 463,121 tris, 284,128 verts, 43 parts, 22 groups |
| ACD length / span / height (2 %) | 14.400 (−0.12 %) / **16.280** (+0.21 %) / 4.260 (−0.16 %) | 9.357 (0.00 %) / 11.793 (−0.03 %) / 3.325 (+0.10 %) |
| origin on the main contact, at minus the static deflection | y −14.5 mm (pc12 gear.py), track 4.530 | y 0, track 3.414 |
| nose wheel on the ground (within its deflection) | y −10.5 mm, wheelbase 3.480 | y 0, wheelbase 3.305 |
| nothing but tyres below the ground; tyres within their deflection | lowest non-tyre +0.136 m | +0.083 m |
| propeller clearance vs sourced 0.32 m | **0.321 m** | — |
| pivots present / pivot origin = node origin / brace closure / L-R symmetry | PASS (**32 movers: 4 gear_door**, the strut-slot doors `seq: 'down'`; braces 4e-7 m; 7 L/R pairs incl. `gear_door_NSL/NSR`) | PASS (8 pairs) |
| control travel vs certificate, sign measured | — | ailerons 15 / 11.5, LH trim tab 10 / 10, ruddervators 20 / 15, ruddervator tabs 7 / 18, yaw SAS 15 / 15; pull −20, push +15, yaw ±9, roll 15 / 11.5, geared tab +8 / −6 unclamped — **values obs**: FAA TCDS A00018CH Rev. 7, read in the FAA DRS public web viewer (orchestrator decision (a) 2026-11-13 under the owner's delegation; the owner may overrule; `docs/phase3_sf50.md`) |
| gear sweep: deepest point ≤ 0.05 m below the down contact | 5 mm (nose, gear 0.75) | 0 |
| gear retracted: only tyres protrude | **KNOWN** tyres 11 mm (POH ~1 in), trailing-link arm **58 mm** (fr2 51; trunnion +0.104 m with the wing +0.121 m) | PASS (flush; trunnion / wells moved with the wing) |
| gear retracted: no gear vertex above the upper skin (fix round 3, finding S1) | **PASS** (closest −5.2 mm, main shock rod, gear_main_R chrome) | PASS (closest −5.5 mm) |
| **gear retracted: nose-gear housing closed from below (iteration 3, F3)**: in the housing's footprint (1 cm cells, gear 0) no liner / gear area — a bad cell with four bad neighbours fails | **PASS: 0 inside an area**; 22 single-cell gap lines (liner 18, strut 4: the 4-mm door gaps); iteration 2: 202 bad, 138 inside an area | — |
| light anchors: none dropped; anti-collision = documented; wing landing lights | 10 drawn; landL / R at BL ±3.15, **WL 1.148** (with the raised wing) | 9 drawn + iceLight kept; 3 anti-collision |
| registration panels keep every field | — | textDir kept |
| registry frame = measured (5 mm); withModelFrame(gaDims) = model | PASS | PASS |
| **cabin windows per side** | port 4 (3 + cargo door), starboard 5 (4 + exit), no airstair-door window | — |
| window / door / exit stations **and water lines** vs drawing 190.10.40.432 + MBP p.5, ±0.03 m | every station within 5 mm; **window centre WL 2.185 (fr2 2.045), airstair / cargo door centres at the drawn WL (fr2 −153 / −112 mm)**; glass 0.32 × 0.40 | — |
| wing front-view silhouette vs drawing 190.10.40.432 | shape rms 4 mm, top-line slope within 0.06° of the drawn one, **winglet rise within 17 mm** | — |
| cabin crown / wing height vs the drawing | **PASS: offsets crown 0, wing −0.002 / +0.007 m, winglet top +0.018** (fr2 KNOWN: 0.138 / 0.117 / 0.126 / 0.107 m) | — |
| **belly fairing covers the wing (P1)** | **no wing vertex below the fairing within its width (closest 1.7 mm inside; iteration 2: blended section, ≤ 3 mm step at its edge)**; fr2: 65.6 mm below at STA 5.9 | — |
| **cabin floor: no other part rises through the carpet (iteration 3, F4)**: floor footprint, 2 cm cells, nothing of a non-cabin part between the floor top and 0.15 m above it | **PASS: 0 cells** (wing carry-through under the floor, WL 1.209); iteration 2: 1,798 cells (0.72 m², 748 in the aisle), up to 13.5 mm (wing_L / wing_R) | — |
| **cabin floor (iteration 2, F2): one flat panel, sourced 1.30 m wide ± 2 %, no cabin item below its top; meta floor-width check within 2 %** | **PASS: WL 1.244, flat (0 mm spread), 1.300 m, 0 vertices below; meta 1.300 (Δ 0)**; the fix-round-3 build fails it (warp 127 mm, 118 vertices up to 65 mm below, meta 1.257 m); pc12's own `none` build passes (1.281 m panel, OML − lining 1.301) | — |
| **fuselage profile / aft underside / half-breadth vs the drawing (P2), limits 20 / 50 / 20 mm** | **crown and keel ≤ 3 mm (STA 3.3–12.9), aft underside ≤ 1 mm, half-breadth ≤ 9 mm**; fr2 −141 / −339 / +232 mm | — |
| **body-plan sections FR10 … FR38 (rms ≤ 15, max ≤ 40 mm)** | **rms 3–9 mm, max ≤ 25 mm**; fr2 rms 30 … 180 mm | — |
| **dorsal fin start and top edge (5 cm)** | **starts where drawn (within 1 cm; start = first station 1 cm above the crown), top edge ≤ 6 mm**; fr2: nothing before STA 10.5, top 449 mm low | — |
| **winglet side view (P3, 5 cm)** | **leading / trailing edge ≤ 30 mm at WL 1.94–2.10**; fr2: top chord 0.31 / 0.38 m forward | — |
| **wing front-view outline vs AFM Fig 1-1 (fix round 2)** | — | mid-line offset 0.000 m, upper-line slope within 0.12° of the AFM's, top at BL 1.6 below the fuselage max-width line within 0.01 m of the AFM (SKIP without the local reference) |
| SF50 wing tips: outermost = span / 2, **rise above the extrapolated upper line inside the AFM front-view band (local reference; SKIP without it), top chord ≤ 0.08 m (fix round 2)**, lens on the skin opening | — | 5.897 m, rise 0.058 m (inside the band), top chord 0.050 m, rim ≤ 2 mm, lamps behind the lens |
| SF50 nacelle: lip proud of a waist (≥ 10 mm), fillet foot ≥ waist + 0.05 m (geometry; iteration 2); fillet foot ≥ the AFM plan-view cowl half-width + 0.05 m (local reference; SKIP without it) | — | lip 0.344 / waist 0.324 / fillet foot 0.422 m half-width; AFM check PASS |
| drawable: alpha on every item, placeholder sync, uAlpha in both programs | PASS (29 items, placeholder 2) | PASS (25 items) |
| **drawable: spinning groups, point 0.25 m off the axis, 40 / 59 / 178 rad/s (fix round 2)** | still 0 m, moved 2.00 m (prop) | still 0 m, moved 2.00 m (fan; fix round 1: 0.309 / 0.416 m still) |
| **drawable: shadow fades with the aircraft (fix round 2)** | acobj at alpha 0.3 casts through the dithered shadow pass, alpha 0 none; obj fallback 0.3 none / 0.7 casts; placeholder 0.3 none | same |
| drawable: CPU arrays released (keepCpu false) | PASS | PASS |
| **Phase 3b diff covers every gaDims call in js/live (fix round 2)** | both `traffic.js` sites in section 3 (fix round 3: the restore site's arguments are now `(icao, cat)` after the Phase 2 workflow's edit; diff line updated) | |
| provenance: SOURCES.json = files; **builder sources = recorded hashes (fix round 2)**; every docs/phase3 image captioned, current-model claims match; **docs/phase3_*.md name the current hashes or are marked SUPERSEDED (fix round 2; iteration 2: a banner line naming a type marks only that type, e.g. the PC-12 clips of `docs/phase3_video.md`)** | PASS | PASS |
| docs/phase3 in ATTRIBUTION.md / check_airport.py scope | PASS (closed in fix round 3, finding V1; was KNOWN) | |
| **no raster-reading tokens (px/m, px/in, "<n> px", "<n> dpi") in the Phase 3a write-ups, builders / facts, model metas / SOURCES, image captions (iteration 3, F1; decision (b))** | PASS (23 files incl. the test itself; the committed bd22c60 `docs/phase3_render.md` and `sf50_geom.py` would fail it) | |
| synthetic glb (FLOAT stride 24, quaternion, matrix, UINT indices, no normals, light extras incl. an unknown kind) | PASS | |

**Fix round 2 mutation check** (in place, file restored from a copy right after; `grep` confirms the fixed line): the
fix-round-1 runtime (spinning keyed on `prop`, `castShadow: sh`, placeholder shadows untouched) → FAIL "SF50 drawable:
spinning groups … off the axis" (still 0.309 m at 40 rad/s, the review's probe value) and FAIL "shadow fades" for both
types. The fix-round-1 models fail the new shape checks by construction: pc12/out has 6 + 6 windows and the cargo door
0.68 m aft (stations check), a 3.66° top line (silhouette check); SF50 0db80513… had the wing 0.10 m low (outline check)
and a 0.129 m, 0.265-m-wide tip fin (tip check). `docs/phase3_render.md` without its banner fails the write-up check; the
fix-round-1 docs section 3 diff fails the gaDims-coverage check (seen before the diff was rewritten).

**The strengthened tests catch every fixed defect.** Checked by a mutation run in a scratch copy (deleted afterwards):
the reviewed SF50 build (9267d3e0…, kept by the review in `out/review3a/rebuild/`) with the old runtime behaviour
(no item alpha, alpha not synced, no uAlpha, spinning `prevModel = model`, KINDS without strobeTail and unknown kinds
dropped, no textDir, `withModelFrame` = identity, no registry landing lights) → 20 FAIL: PC-12 landing lights,
withModelFrame (both), rv_tab travel (both) and the functional controls check, SF50 light anchors and anti-collision
count, reg-panel text_dir, wing tips (both: rise 0.044 m), nacelle, placeholder sync, uAlpha, item alpha (both), PC-12
spinning motion, SOURCES hashes, stale captions, synthetic unknown light kind.

"Protrusion" = how far a gear vertex (gear = 0 pose) lies below the lowest downward-facing fuselage / wing / gear-door
skin point within ±0.6 m fore-aft on the same butt line (±5 cm); this bridges the wheel-well openings and is
conservative (low).

## 7. Renders (`docs/phase3/`, 1920×1080 JPEG, SwiftShader, HWD world, 2026-11-13 12:30 PST unless noted)

**OD4 (2026-11-14):** the current PC-12 and SF50 stills and the comparison with the pc12 reference viewer are in section
15.5; the paragraphs below describe earlier builds.

**Fix round 3 iteration 3 (PC-12 957b3c4e…, 2026-11-14):** re-shot `pc12_belly_low`, `pc12_gear_closeup`,
`pc12_nose_housing`, `pc12_gearup_housing` and `pc12_cabin_door` with the iteration-2 cameras, plus the new
**`pc12_cabin_aisle.jpg`** {eye −1.2,1.95,0.0 tgt 0.3,1.24,0.0 fov 62, airstair and cargo doors open: the rechecker's aisle
camera}: `node dev/model_shot.mjs --model=PC12 --set= --jobs=out/fr3i3/pc12_jobs.json --out=docs/phase3 --prefix=pc12
--port=8863` (23–47 s per still on the shared CPU). The six fix-round-3 stills stay superseded (their notes now name what
iteration 3 changed: nothing visible there but two small plates beside the nose strut). Seen (every image looked at):
gear up, the housing floor is closed — the slot doors sit flush ahead of the clamshells with 4-mm gap lines, no lime
rectangle and no strut (a lime glint in the clamshells' forward corner gap at close range, as at the other door gaps);
gear down, the two slot doors hang beside the strut at the housing's front with the taxi lamp between them; in the aisle
the carpet is uniform over the wing carry-through (the iteration-2 build showed a bright, hard-edged hexagonal patch there:
the rechecker's `out/recheck3c_2/shots/pc12_rc2_aisle_floor.jpg` with the same camera), only the soft sun patch from a
window remains; the nose-bay liner roof still shows as a lime rectangle between the cockpit seats (pc12 owner item,
section 9). `pc12_cabin_door`, `pc12_belly_low` and `pc12_gear_closeup` look as in iteration 2. No new defect seen.

**Fix round 3 iteration 2 (PC-12 6e349329…):** re-shot `pc12_belly_low` and `pc12_gear_closeup` with the same cameras, new
**`pc12_nose_housing.jpg`** {eye 5.4,0.32,−2.2 tgt 2.9,0.78,0 fov 30, gear down}, **`pc12_gearup_housing.jpg`** {eye
1.2,0.25,−1.0 tgt 2.4,0.85,0 fov 40, gear up, 1.5 m up} and **`pc12_cabin_door.jpg`** {eye 2.0,2.45,−1.45 tgt 1.0,1.25,0.2
fov 44, airstair door open}: `node dev/model_shot.mjs --model=PC12 --set= --jobs=out/fr3i2/pc12_jobs.json --out=docs/phase3
--prefix=pc12 --port=8857`. The other six fix-round-3 stills (`pc12_side`, `front34`, `rear34`, `port`, `chase`,
`flaps40`) show c46fe4fb…; nothing iteration 2 changed is visible in them (cabin interior, nose-gear housing, the belly
fairing's section edges, belly antenna roots), so they are marked superseded in `docs/phase3/SOURCES.json` rather than
re-shot (CPU shared with the video workflow). Seen (every image looked at): the housing under the cockpit as a rounded pod
with the strut leaving through the slot at its front (gear down) and the closed doors on its curved floor with the slot
ahead of them (gear up; the lime zinc-chromate liner shows through the slot, as in a real strut slot); no lime line along
its lower edges any more and no speckle at its aft end; through the open airstair door the flat floor, the clear doorway
and the port ledge starting aft of it; from the low side the belly fairing reads as one smooth fairing under the wing root.
No new defect seen.

**Fix round 3 (PC-12 c46fe4fb…):** `pc12_side`, `pc12_front34`, `pc12_rear34`, `pc12_port`, `pc12_chase`, `pc12_flaps40`,
`pc12_gear_closeup` re-shot with the same cameras (`out/fr3/pc12_jobs_fr3.json`: the fix-round-2 parameters read back from the
captions) plus the new **`pc12_belly_low.jpg`** {eye 1.6,0.30,−7.6 tgt 0.5,0.82,0 fov 34, gear down}: `node dev/model_shot.mjs
--model=PC12 --set= --jobs=out/fr3/pc12_jobs_fr3.json --out=docs/phase3 --prefix=pc12`. `pc12_cockpit`, `pc12_fade`,
`pc12_gear_half`, `pc12_lights_dusk`, `pc12_rear`, `viewer_desktop` and `viewer_phone` show the fix-round-2 PC-12 and are
marked superseded in `docs/phase3/SOURCES.json` (not re-shot this round). Seen in the fix-round-3 images (every one looked
at): the higher cabin with the windows and both doors at their drawn heights, the windshield / side window as drawn
(no DV window), the long dorsal fin rising from the cabin top, the slimmer tail cone, the strakes under it at the drawn
stations, the nose-gear housing under the cockpit, the belly fairing as one smooth fairing over the wing root (from below:
no wing skin under it), the raised wing with the swept-up winglet; the livery swoosh and pinstripe follow the new loft.
No new defect seen; at close range the closed nose doors show their 4-mm gaps (bay liner).

Fix round 2: all re-shot on the models above (captions with the model hash in `docs/phase3/SOURCES.json`), all
looked at. Commands (`out/fr2/render_all.sh`): `node dev/model_shot.mjs --model=<T> --out=docs/phase3
--prefix=<pc12|viewer_sf50> --set=standard --jobs=<file>`, dusk with `--t=2026-11-14T01:05:00Z`, then `--viewer=desktop` /
`--viewer=phone`. Job files of fix round 2 (`out/fr2/`): as fix round 1 below, plus PC-12 `port` {eye −0.5,1.7,−24 tgt
−0.5,1.6,0 fov 34} and `rear` {eye −32,1.7,0 tgt 0,1.7,0 fov 30}, SF50 `front` {eye 22,1.3,0 tgt 0,1.2,0 fov 30}. Fix
round 1's job files (gitignored `out/fr1/`):
`sf50_day.json` {tip_front: eye 3.0,2.3,8.2 tgt −0.1,1.3,5.5 fov 30; tip_rear: eye −3.6,1.9,7.6 tgt −0.1,1.35,5.5 fov 30;
nacelle: eye 2.6,3.4,−2.4 tgt −1.3,2.3,0 fov 34; fade: cam front34 alpha 0.5}, `pc12_day.json` {gear_closeup: cam gear;
cockpit: cam nose; fade: cam front34 alpha 0.5}, dusk (`--t=2026-11-14T01:05:00Z`): PC-12 lights_dusk eye 22,2.4,9 tgt
0,1.6,0 fov 38, 1,700 rpm, flaps 15, all lights, rwy28L; SF50 lights_dusk eye 15,1.8,6.5 tgt 0,1.2,0, rotor 120 rad/s,
nav / strobe / landing / taxi.

| Image | Pose | What to look at |
|---|---|---|
| `pc12_front34.jpg`, `pc12_rear34.jpg`, `pc12_side.jpg` | Green Ramp, hdg 135, gear down | fix round 3: the re-fitted loft, glazing, dorsal fin, winglet; starboard: 4 windows + the exit window |
| `pc12_port.jpg`; `pc12_rear.jpg` (fix round 2, superseded) | Green Ramp | port: airstair door without window, 3 windows, cargo door with its window, all at their drawn heights (fix round 3); from behind: the 6.2° dihedral |
| `pc12_belly_low.jpg` (new in fix round 3, re-shot in iteration 2) | Green Ramp, low from port | nose-gear housing, belly fairing over the wing root (P1, F6), main gear, raised wing |
| `pc12_nose_housing.jpg`, `pc12_gearup_housing.jpg` (new, iteration 2; re-shot in iteration 3) | ramp, gear down / 1.5 m up with the gear up | nose-gear housing: rounded edges, strut slot, doors on the curved floor (F5); iteration 3: strut-slot doors open beside the strut / closed flush with the gear up (F3) |
| `pc12_cabin_door.jpg` (new, iteration 2) | ramp, airstair door open | flat cabin floor, doorway clear (F2) |
| `pc12_cabin_aisle.jpg` (new, iteration 3) | ramp, inside the cabin over the aisle, both doors open | carpet uniform over the wing carry-through (F4); far end: the nose-bay liner roof between the cockpit seats (pc12 owner item) |
| `pc12_chase.jpg` | runway 28L, 1,700 rpm, flaps 15, lights on | low chase-cam; faint prop disc |
| `pc12_gear_half.jpg` | 9 m up, gear 0.5, pitch 6°, flaps 15 | mains folding inward with leg doors and side braces, nose aft with clamshells open |
| `pc12_flaps40.jpg` | ramp, flaps 40 | Fowler flap |
| `pc12_gear_closeup.jpg`, `pc12_cockpit.jpg` | ramp | main gear, radar pod; glazing over the flight deck |
| `pc12_fade.jpg` | ramp, alpha 0.5 | the screen-door fade of a re-placement; since fix round 2 the shadow is dithered too |
| `pc12_lights_dusk.jpg` | 28L, 01:05Z | **wing landing-light glare under the starboard wing (new anchor)**, nose-strut taxi lamp, green nav |
| `viewer_desktop.jpg`, `viewer_phone.jpg` | dev viewer with HUD, 1600×900 and 390×844 @2 (iPhone UA) | layout / touch targets; HUD H 4.26 |
| `viewer_sf50_{front34,rear34,side,chase,gear_half,flaps40}.jpg` | the standard set for the SF50 | upturned tips (rear 3/4, chase), D inlet with polished lip (front 3/4), wing root 0.10 m higher (fix round 2) |
| `viewer_sf50_front.jpg` (new, fix round 2) | from straight ahead | wing height against the fuselage (AFM front view) and the low tip upturn |
| `viewer_sf50_tip_front.jpg`, `viewer_sf50_tip_rear.jpg` | close range, right wing tip | fix round 2: the short pointed upturn (0.06 m above the upper line, AFM); flush lens (green position light, white landing light); strobe lens on the upturn |
| `viewer_sf50_nacelle.jpg` (new) | close range, inlet | raised D lip, waist, cowl faired into the spine |
| `viewer_sf50_fade.jpg` | ramp, alpha 0.5 | fade, dithered shadow |
| `viewer_sf50_lights_dusk.jpg` (new) | 28L, 01:05Z | tip landing-light glare (starboard); the nose lamp's beam points away from this eye |

Seen in them (fix round 2, every image looked at): PC-12 port side — airstair door without a window, three windows,
the cargo door 0.68 m further forward than before with its window; starboard — four windows and the exit hatch with its
window; from behind the steeper 6.2° dihedral and higher winglets; the wing root, flap-track fairings, radar pod and gear
legs unchanged in look. The fades dither aircraft and shadow together (`pc12_fade.jpg`, `viewer_sf50_fade.jpg`). SF50 —
the wing meets the fuselage visibly higher (front view, front 3/4), the tips end in a short pointed, aft-raked upturn
(tip close-ups), the main legs are 0.10 m longer and still fold flush into the wells (`viewer_sf50_gear_half.jpg`). No
regression seen. Not changed and still seen: at dusk the env exposure makes the airframes very dark (env module); the
PC-12 cabin sits 0.14 m low against the drawing (not judgeable in these views without a reference). SwiftShader: 16-27 s
per 1080p still.

## 8. Renderer / shared-file changes wanted (Phase 3b or the file owners)

**Made in OD4 (2026-11-14), the first renderer-file change of this package (more in OD4 iterations 3 and 4, below):** `js/shaders/post.js` FINAL_FS takes
`uniform float uCA` (chromatic-aberration strength) and `js/renderer.js` sets it from `post.ca`; `dev/studio.js` passes 0.
**OD4 iteration 2 (review F8): the default is now 0** (`post.ca ?? 0.0`; it was `?? 1.0`, sfo3d's constant): at a fifth to
half a pixel the effect was invisible except as 1-px purple / red fringes on high-contrast aircraft edges (17-41 such pixels
on the aircraft in each world still, e.g. (115, 77, 103) between white and navy at the front34 wing tip) and on 1-px dark
seams. The app (`js/live/app.js`, not this package's) never set `post.ca`, so it, the video pipeline and the dev viewers
all render without it now; a caller can still pass `ca: 1`. Everything else in the airport world renders as before
(section 15.6: livetest before / after). The aircraft shading changes of OD4 live in `js/aircraft/detailed.js` (aircraft
programs only; section 15).

**Made in OD4 iteration 3 (2026-11-14, section 15.7):**
- **Bloom knee** (review F1 / F3): `js/shaders/post.js` DOWN_FS weights each first-pass tap by w = v² / (v² + K²) of its
  display-referred luminance (v = lum × `post.exposure`); FINAL_FS multiplies the frame by 1 + `post.bloom` × levels × (1 − w)
  / (1 + 0.02 lum) before adding the bloom, so a uniform area keeps its brightness while dark details lose the 7.2 % veil
  of their bright surroundings that sfo3d's un-thresholded six-level bloom laid on them. `js/renderer.js`: `BLOOM_KNEE = 4`
  (exported), `uKnee: post.bloomKnee ?? BLOOM_KNEE`, `uExpo`, `uBloomLevels: this.down.length`. `post.bloomKnee: 0` restores
  sfo3d's bloom. Every caller (app, video pipeline, dev viewers) takes the default; `js/live/app.js` is not changed.
  World check (knee 0 vs 4, same frames): median pixel change 0, 5th–95th percentile within ±1 sRGB level, night and dusk
  within ±1 / −2 at the 1st percentile; lights bloom as before.
- **Aircraft-light pull** (review F7): `js/scene.js` put() packs `s.pull` into iData.y; `js/shaders/sprites.js` pulls a
  flagged sprite toward the camera by max(3 m, its drawn radius), at most half the distance, and scales it by
  (d − pull) / d so its angular size is kept; `js/aircraft/detailed.js lightSprites` flags every sprite of a detailed
  aircraft. Unflagged sprites (airfield lights, placeholders) keep the sfo3d pull min(2 m, 5 % of the distance).

**Made in OD4 iteration 4 (2026-11-20, section 15.8):**
- **Lens occlusion of aircraft lights** (review G1): `js/renderer.js` `copyDepth()` resolves the near pass's MSAA depth
  (DEPTH_COMPONENT32F renderbuffer) into a single-sample DEPTH_COMPONENT32F texture (`blitFramebuffer` DEPTH_BUFFER_BIT,
  NEAREST) after the opaque near draws and before the blended ones, `R.sceneDepth`; only in frames whose items ask for it
  (render-item field `needsDepth`), otherwise no copy and a 1 × 1 `R.noDepth` stays bound; a GL error on the first blit
  turns the test off (warning, light drawn as before). `js/scene.js`: the sprite batch sets `needsDepth` when it holds a
  flagged (`pull`) sprite and passes `uSceneDepth` / `uOcclude`. `js/shaders/sprites.js` `lensVisible()`: a flagged sprite's
  intensity × the share of 3 × 3 depth taps over the lamp's footprint whose scene depth lies behind the lens centre moved
  toward the camera by 0.09 m + 0.0008 m per metre of distance; a hidden lens hides the whole disc (zero-size quad).
  Unflagged sprites (airfield lights, placeholders) are drawn exactly as before.
- **Render-item field `cullFront`** (review G4): `drawItems` culls FRONT faces for such an item (draws only its back faces)
  and restores BACK culling after it; `js/aircraft/detailed.js` draws each glass group as two items, back faces first, as
  three.js r160 draws a transparent double-sided material.

**Made in OD4 iteration 5 (2026-11-21, section 15.9):**
- **Lamp-shape lens test** (review F1 / F3): `js/gl.js` `Mesh.setInstances(f32, n, nVec4 = 4)` takes the number of vec4
  attributes per instance (locations 5 … 4 + nVec4; every other caller keeps 4); `js/scene.js` packs a light sprite in 32
  floats (`SPRITE_F`; the sfo3d 16 + the lamp shape `s.occ`: iData.z shape 1 ellipsoid / 2 box, iData.w geom, iL0 centre +
  h0, iL1 axis 0 + h1, iL2 axis 1 + h2, iL3 facing normal + cos, −2 = none); `js/shaders/sprites.js` `lensVisible()`
  cuts each of 3 × 3 tap rays with the lamp's own shape and classifies the scene depth there: in front of the shape
  (occluder, counts against), inside it ± E (the lamp or the skin it is flush with: seen), behind it (no lamp at that tap:
  not counted for a lamp whose surface is in the depth, seen for one that is not); E = 2 mm + 0.5 × the pixel footprint +
  the float32 depth step at that distance (no per-metre term); a one-sided lamp patch seen from behind is hidden. Unflagged
  sprites (airfield lights, placeholders) are drawn exactly as before (iData.zw = 0, no test).
- **Dev viewer near plane** (`dev/model.js`, F3): beyond 75 m the near plane grows as the app's camera rig sets it
  (d × 0.004, at most 5 m) - with 0.3 m a float32 depth step at 900–1500 m is 0.16–0.45 m, coarser than the airframe that
  hides a light.

**Made in OD4 iteration 6 (2026-11-21, section 15.10):**
- **Self-visibility tables in the lens test** (recheck R1 / R2): `js/scene.js` packs a light sprite in 40 floats (`SPRITE_F`;
  + iL4 = the aircraft's bounding sphere, world centre + radius, and iL5 = (table band | −1, gear-up share)) and keeps the
  lamps' self-visibility tables (`s.occ.vis`, computed by `js/aircraft/glb.js` `lampTables`) in one RGBA8 atlas texture
  (`LampVisAtlas`: NA columns, NE rows per band, a band uploaded the first time its table is seen, the texture doubled when
  full; uniforms `uLampVis` / `uLampVisNE`; a 1 × 1 texture when no table exists). The scene still imports nothing from
  `js/aircraft/**`: the tables arrive as data on the sprites. `js/shaders/sprites.js` `lensVisible()`: below 1.5 pixels (the
  smaller projected half extent of the lamp's ellipsoid) a flagged sprite's visibility is its table's value toward the camera
  × the share of 3 × 3 taps whose depth lies in front of the aircraft's bounding sphere; above 3 pixels the iteration-5 test,
  vetoed where the table says hidden and never below the table where the table clearly sees the lamp (≥ 0.5); blended
  between; from a camera nearer to the lamp than an occluder of its direction (the table's third channel) the iteration-5
  test alone. `js/gl.js` unchanged (`setInstances` takes the 10 vec4s). Unflagged
  sprites (airfield lights, placeholders) are drawn exactly as before. **Round 2 (15.11)**: the atlas's alpha channel (unused
  before) carries each table's reach (the aircraft's own surfaces in front of the lamp), and the external-occluder taps count
  depth more than reach + 0.3 m in front of the lamp as another object (another aircraft, a wall), the bounding sphere only
  for a tap beyond 0.5 m of the line of sight; no layout change in `js/scene.js`. **Round 3 (15.12)**: `js/scene.js` packs
  a lamp's flap tables (the first of their consecutive atlas bands, `LampVisAtlas.bandRun`) and the flap position into
  iL5.z / iL5.w (the two floats that were 0; still 40 floats); `js/shaders/sprites.js` `lampTable` mixes them, measures the
  near-range blend on the SEEN part of the lamp (the projected ellipse's minor half-axis × the table's share) and bounds the
  depth test toward the table (`LENS_BM` 0.15, `LENS_BLO` 0.5). `js/gl.js` and `js/renderer.js` unchanged.
- **Dev viewer lens probe** (`dev/model.js` `HWDM.lensProbe()`): reads the shader's visibility of every sprite of the last
  frame back from the GPU (QA only; the app does not call it).

None is needed for the models to render: the aircraft programs live in `js/aircraft/detailed.js`. Wanted:

1. **`scene.js` PRI**: add `acobj: 0` (aircraft first for early-z, like the old `aircraft` entry).
   ```diff
   -const PRI = { acr: 0, aircraft: 0, ga: 0, obj: 1, objI: 1, sign: 1, decal: 2, mark: 2, paint: 2, water: 3, ground: 4 };
   +const PRI = { acr: 0, aircraft: 0, ga: 0, acobj: 0, obj: 1, objI: 1, sign: 1, decal: 2, mark: 2, paint: 2, water: 3, ground: 4 };
   ```
2. **Prop / fan motion blur**: the velocity buffer is per object; spinning groups now carry the aircraft's motion without
   the rotation (section 3). A rotational blur would need a per-item angular velocity in `js/shaders/post.js MBLUR_FS` —
   not proposed, the disc covers it.
3. **Lit light lenses at night**: the lens geometry stays unlit; the glow comes from the `aircraft_lights.js` sprites.
4. **`js/env/aircraft_lights.js`**: a native `strobeTail` (and optional `iceLight`) kind, so `detailed.js` need not call
   `aircraftSprites` twice for the SF50's tail strobe. **And (OD4 iteration 2, review F9) the daylight sprite size of the
   strobes / beacon**: a flash caught by a still at 30-40 m draws a saturated disc 61-91 pixels across over a tail or a wing
   tip by daylight (`docs/phase3/viewer_sf50_chase.jpg` before this iteration). Not changed here (the file's owner); the
   dev viewer now pins the flash phase (`lseed`, section 15.6) so docs stills are reproducible and show no flash unless a
   job asks for one.
5. **`docs/ATTRIBUTION.md`** (fix rounds 1 and 2, the licence-notice finding; not edited here: not an M1 / M2 file; the test
   reports it as KNOWN until it is done; **needed before the artifact is published**). Add after the `docs/phase2/*.jpg`
   row (line 89 today):
   ```diff
   +| `docs/phase3/*.jpg`, `*.png` (Phase 3a) | Model renders: hwd3d renderer stills of the own PC-12 / SF50 models on the HWD world, and SF50 rasteriser check renders | Produced Works: NAIP 2024 (public domain) base and OSM (ODbL 1.0) airfield content where the HWD world is shown; own models (no logos, no registration); the notice and the model hash are in each caption of `docs/phase3/SOURCES.json` | `dev/model_shot.mjs`, `tools/models/sf50/render_checks.py`, the render-check package's `shoot.mjs` |
   ```
   and extend the coverage sentence (line 92) to "`docs/phase1/`, `docs/phase2/`, `docs/phase3/` and `js/`".
6. **`tools/check_airport.py`** SOURCES coverage (same finding; KNOWN in the test): `sources_coverage()` (line ~257):
   ```diff
   -    ls = subprocess.run(['git', '-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', 'hwd3d/data', 'hwd3d/refs/cache', 'hwd3d/docs/phase1', 'hwd3d/docs/phase2', 'hwd3d/js'],
   +    ls = subprocess.run(['git', '-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', 'hwd3d/data', 'hwd3d/refs/cache', 'hwd3d/docs/phase1', 'hwd3d/docs/phase2', 'hwd3d/docs/phase3', 'hwd3d/js'],
   -        if not f.startswith('hwd3d/js/') and not f.startswith('hwd3d/docs/phase2/'): return True
   +        if not f.startswith('hwd3d/js/') and not f.startswith('hwd3d/docs/phase2/') and not f.startswith('hwd3d/docs/phase3/'): return True
   ```
   (and the folder list in its `say(...)` line and in the header comment at line ~86). `docs/phase3/SOURCES.json` already
   has a key for every image. Until then `tools/models/test_models.mjs` checks the `docs/phase3` captions itself.
7. **`js/aircraft/ga_dims.js`** (P3): optionally record the measured PC12 / SF50 frames there too; `modelDims` /
   `withModelFrame` make it unnecessary for the drawn types.
8. **`js/renderer.js` shadow fade for every program** (fix round 2; the detailed aircraft no longer need it): give
   `SHADOW_FS` the screen-door rule so placeholders (`ga` / `obj` items of all types) fade their shadows too:
   ```diff
   -const SHADOW_FS = `void main(){}`;
   +const SHADOW_FS = `uniform float uAlpha;
   +float shBayer4(vec2 p){ ivec2 q = ivec2(mod(p, 4.0)); int i = q.x + q.y * 4; int m[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5); return (float(m[i]) + 0.5) / 16.0; }
   +void main(){ if (uAlpha < 0.999 && uAlpha >= 0.0 && shBayer4(gl_FragCoord.xy) > uAlpha) discard; }`;
   ```
   `drawItems` already sets `uAlpha` on any program that declares it (both passes). Instanced programs whose items carry
   no `alpha` keep 1 (`it.alpha ?? 1`).

## 9. Open items / not verified

- **OD4 (2026-11-14): the first bullet below describes the retired fr3 build.** The original model's measured deviations
  from drawing 190.10.40.432 / the NGX documents are the KNOWN items of section 15.1 (pc12 owner items); the open look
  items are in sections 15.5–15.9 (iteration 4, 2026-11-20: lens occlusion of aircraft lights, the cabin back-face rule,
  the flight-deck glazing and the two-pass glass; iteration 5, 2026-11-21: the lens test by the lamp's own shape, the
  flight-deck region; iteration 6, 2026-11-21: per-lamp self-visibility tables for the lens test at range, separate
  windshield / side-window veils, the per-type deck ramp; round 2: no propeller blades in the tables, the reach channel for
  other occluders, the tables' residual error stated per light; their open items close sections 15.8–15.11).

- **PC-12 fidelity (pc12 owner)**: fix round 3 fitted the fuselage loft, glazing, openings, wing / gear height, fairings,
  dorsal fin, strakes and winglet to drawing 190.10.40.432 in the hwd3d build (section 4; proposed to the pc12 owner). Still
  open, measured on the same drawing (overlays in `out/fr3/`, `out/recheck3c_1/`): (1) the **rudder trailing edge** is drawn
  0.3 m (top) to 0.75 m (bottom) further forward than pc12's fin / rudder planform, the tail cone ending at the rudder's
  lower corner (~0.75 m forward of pc12's tail-cone end) — the model keeps pc12's fin / rudder / tail-cone end; (2) the **tailplane** leading edge is
  drawn ~0.3 m forward of pc12's (larger root chord); (3) the **lower cowling** (STA 1.2–2.6) is drawn up to 0.1 m lower
  than pc12's (its chin inlet, inlet duct and engine are built around it; kept); (4) the **wing** is drawn ~0.15 m further
  aft than pc12's (leading and trailing edge at BL 2.5–7.5 in the plan view; pc12 places it from the POH aft CG limit =
  46 % MAC; the drawing's station anchor, pc12's spinner tip at STA 0.39, puts the drawn firewall frame ~8 cm aft of the
  POH firewall station 3.00 — not resolved; kept; the winglet was fitted to the drawing in absolute stations); (5) the retracted
  trailing-link arm 58 mm (KNOWN; the trunnion rose 17 mm less than the wing to keep the tyre protrusion at 11 mm).
  **Owner decisions wanted (iteration 2):** (6) **winglet in plan / blend (F4)**: the fit is limited to the side view on
  purpose. In the plan view the model's winglet blend starts ~0.35 m further outboard than drawn and the tip leading edge
  lies up to 0.75 m forward of the drawn one (rechecker's registration of MBP p.9), beyond the whole-wing offset of item 4;
  no test covers the plan view or the blend below WL 1.94. The same sheet prints "WING SPAN = 16.114m" and "PROPELLER 4
  BLADES Ø 2,67m" (seen on the sheet), while the PRO facts are 16.28 m (Pilatus) and 5 blades (EASA TCDS), so the drawn wing
  tip / winglet may not be the PRO's; fitting the plan view would mean moving the planform away from the sourced span. The
  owner (or the pc12 owner) decides whether to fit the plan view as well (keeping 16.28 m, plus a plan-view test) or to keep
  the side-view-only fit. (7) **weather-radar pod position (F9)**: the drawing shows a pod at the starboard wing tip (plan
  and front views) and nothing at mid-span; the model keeps pc12's pod at mid-span, BL 3.7–4.1 (pc12 "estimated"). To be confirmed from PC-12 PRO photos or the drawing before the Phase 3b
  videos. The two Pilatus documents disagree on the starboard windows (section 4). Inferred in fr3: the nose-gear housing
  width, rounded section and rear end (5 cm aft of the drawn end), the strut slot, its two slot doors (open whenever the
  leg is out, 85°) and the notch in the bay liner's front wall (iteration 3), the flat wing centre section inboard of
  BL 0.85 and its upper skin held under the cabin floor inboard of BL 0.66 (iteration 3), the strakes' outward offset, the dorsal-fin base thickness (no fillet radii), the tail-cone end aft of STA 13.0,
  the belly fairing's section law, the antennas mounted normal to the skin, the cabin layout (0.40 m aft of pc12's, ledge
  clear of the doors; the aft seat pair now stands in front of the forward half of the cargo door and the starboard club
  table near the over-wing exit, as in many executive layouts, unverified) and the flight-deck floor, which follows the
  loft map and slopes ~7° up aft.
- **pc12 nose strut vs its bay (pc12 geometry)**: with the gear down (gear 1) pc12's strut crosses the keel skin ahead of
  the bay opening at STA 3.00–3.02 (24 edge crossings, inside the housing, not visible) — as in pc12's own build
  (`none`: 164 crossings with liner and doors). The bay opening would have to start ~0.1 m further forward, into the lower
  cowling; left to the pc12 owner. Its crossing with the bay liner's front wall (90 / 32 at gear 1 / 0.75) is gone since
  iteration 3 (notch over the slot width up to WL 1.15); the housing, the liner and all four nose doors no longer cross the
  strut or braces (0 at gear 1 / 0.75 / 0.5 / 0.25 / 0).
- **pc12 nose-bay liner roof above the flight-deck floor (pc12 owner item, iteration 3 finding F4)**: pc12 closes the
  nose-bay liner with a flat roof at WL 1.300; the flight-deck floor (loft-mapped, sloping ~7° up aft) is lower than that
  over STA ~3.0–3.9, so the lime roof is the top-most surface over STA 3.04–3.88, |BL| ≤ 0.13 (416 cells of 2 cm,
  0.17 m²; pc12's own `none` build has the same, larger) and shows as a lime rectangle between the cockpit seats
  (`pc12_cabin_aisle.jpg`, far end). Not fixed here: the retracted nose wheel's top is at WL 1.291, above the floor plate
  where it dips to WL 1.284, so lowering the roof would put the wheel through the floor; the pc12 owner decides between a
  raised flight-deck floor or a wheel-well hump over the bay [inf either way].
- **pc12 nose doors closed with the gear down** follow the pc12 model and its viewer [inf]; the strut-slot doors (hwd3d,
  iteration 3) stay open whenever the leg is out of the well and close with it [inf].
- **Timing** (gear 0.72 + 4.6 s, flaps 11°/s, control lag) and the **prop-disc thresholds** are inferred, not sourced.
- **Clear-coat / interior / display constants** of `acobj` are visual choices [inf], not measured.
- **PC-12 landing-light position** is inferred (photo shows the lamp, not its span station); the pc12 model has no lamp
  geometry there.
- **Performance at full quality (OD1)**: per PC-12 up to ~163 draw calls and ~2.1 M triangles per frame across 3 shadow
  cascades + far + near passes (review probe), 21.7 MB of GPU buffers per type (shared); laptop GPU frame time **not
  measured** (no GPU here; still true after fix round 2). Done: the CPU copies are released after upload. Not done (needs
  a laptop measurement and, for geometry LOD, the owner under OD1): capping `shadowMaxCascade` for distant aircraft.
  **Owner action**: open `dev/model.html?model=PC12` (and a replay with several PC-12s once Phase 3b is wired) on the
  target laptop and read the frame time (the HUD / browser performance panel).
- SF50 open items (gear retraction directions [inf, unverified, searched again in fix round 2]; digitised AFM data, now
  local reference data under decision (b)): `docs/phase3_sf50.md` §7 / §8. The control-surface travels are **obs** since
  orchestrator decision (a) 2026-11-13 (FAA TCDS A00018CH read in the FAA DRS public web viewer, the FAA's public interface
  for type certificate data sheets; under the owner's delegation, the owner may overrule). **The SF50 take-off video's
  credits must carry the inf marker for the gear motion** (and for the travels only if the owner overrules decision (a)).

## 10. Review fix round 1 (2026-11-13): dispositions

| # | finding | status |
|---|---|---|
| 1 | PC-12 cabin windows / door stations vs Pilatus NGX drawings | **deferred (pc12 owner item)**: `pc12/` is read-only for hwd3d and pc12's method requires its drawing step and the owner's review; recorded (section 4), KNOWN check with the measured counts |
| 2 | PC-12 wing dihedral / height / winglets | **deferred (pc12 owner item)**, same reasons; KNOWN check (3.66°, well below the drawing's) |
| 3 | SF50 wing tips | fixed (M1; `docs/phase3_sf50.md`) |
| 4 | SF50 nacelle section | fixed (M1) |
| 5 | SF50_FACTS: ACD gear values | fixed (docs; PC-12 values in section 3) |
| 6 | SF50_FACTS: lights provenance | fixed (docs) |
| 7 | SF50 gear retraction directions | not resolved: no primary source found; stays [inf] |
| 8, 13 | DRS web-viewer access | deferred: owner decision (`docs/phase3_sf50.md` §7); resolved in fix round 3 by orchestrator decision (a) (values obs with the TCDS citation; the owner may overrule) |
| 9 | alpha fade ignored by the detailed drawable | fixed (section 3) |
| 10 | traffic / ground-physics frame vs the model | fixed in the runtime (`withModelFrame`, tested); wiring is Phase 3b (`js/live/**` not editable here; diff in section 3) |
| 11 | SOURCES.json hashes / superseded build in docs | fixed: SOURCES refreshed, docs and stills of the final build, the test checks hashes and captions |
| 12 | licence notices for docs/phase3 images | fixed for the images (`docs/phase3/SOURCES.json`, every image); ATTRIBUTION row and check_airport scope proposed (section 8: not M1 / M2 files) |
| 14 | SF50 ruddervator tab range inverted | fixed (M1) + sign-measuring travel test |
| 15 | strobeTail / iceLight / text_dir dropped | fixed |
| 16 | motion vectors of spinning groups | fixed |
| 17 | cost at full quality | partly: CPU arrays released; GPU frame time not measurable here (deferred to a laptop run) |
| 18 | PC-12 ground contact 14.5 mm | fixed: origin on pc12's ground (heights 4.26 / clearance 0.32 as sourced); retraction AGL noted |
| 19 | PC-12 landing lights collapsed on the nose lamp | fixed: wing landing-light anchors from the Pilatus MBP p.4 photo (position inferred) |
| 20 | digitised AFM data committed | deferred: owner question (`docs/phase3_sf50.md` §7) |

## 11. Review fix round 2 (2026-11-13): dispositions

| # | finding | status |
|---|---|---|
| F1 | PC-12 cabin windows / door stations (6 per side, airstair-door window, cargo door 0.7-0.8 m aft) | **fixed in the hwd3d build** (section 4): stations re-measured on drawing 190.10.40.432 and MBP p.5, pc12's own builders run with the override set `fr2` (`tools/models/pc12/build_pc12_variant.py`, nothing in `pc12/` changed), imported with full provenance; port 3 + cargo-door window, starboard 4 + exit, no airstair-door window, every station within 5 mm of the drawing; new stations test. Starboard: the two Pilatus documents disagree — livery used, conflict recorded. Remaining then (KNOWN): the cabin section 0.138 m low vs the drawing — fixed in fix round 3 (section 12) |
| F2 | PC-12 dihedral / height / winglets | **fixed in the hwd3d build** (dihedral 6.2° about BL 2.265, fitted to both front-view outlines: shape rms 4 mm, top-line slope within 0.1°, winglet rise within 0.02 m); new silhouette test. The absolute height (wing 0.12 m low, the same offset as the cabin) was the KNOWN pc12 loft item — fixed in fix round 3 (section 12) |
| F3 | DRS access route (owner) | **deferred (owner decision)**, narrowed: FSB item → faa.gov FSB draft (HTTP 200), FJ33-5A envelope / rating → EASA IM.E.016 (HTTP 200); control-surface travels have no non-DRS source and are now **inf (DRS)** in SF50_FACTS and the test labels; video credits must show it (`docs/phase3_sf50.md` §8). Superseded in fix round 3 by orchestrator decision (a): the travels are obs (TCDS A00018CH via the FAA DRS public web viewer); the video credits need the inf marker only for the gear motion |
| F4 | SF50 wing ~0.10 m low vs AFM front view | **fixed** (M1: `Z_LE0` 0.835, gear trunnion / wells / slot / door moved with it; outline test) |
| F5 | SF50 tip fin twice the AFM height, square top; test limit mis-cited | **fixed** (M1: top 0.058 m above the extrapolated upper line, inside the AFM front-view band, 0.05 m pointed top; the test reads the rise as the figure is read; drawing-vs-photo conflict recorded) |
| F6 | SF50 fan motion vectors (spinning keyed on the prop disc) | **fixed** (`detailed.js` keys on the `spin` mover; test with an off-axis point at 40 / 59 / 178 rad/s; the old code fails it with the review's 0.309 m) |
| F7 | shadows pop on a fade | **fixed for the detailed aircraft** (dithered `acobj` shadow pass; obj fallback and placeholder path cast from alpha 0.5); test. General `SHADOW_FS` change for every program proposed (section 8 item 8: `renderer.js` belongs to the other workflow) |
| F8 | docs/phase3 ATTRIBUTION row and check_airport scope | **deferred (not M1 / M2 files)**: exact diffs with current line numbers in section 8 items 5 / 6; a new KNOWN test check reports them until their owners apply them; must be done before publishing |
| F9 | traffic frame: the 3b diff missed the parked-aircraft restore site | **fixed**: `modelDims(type, category)` in `models.js`; the section 3 diff lists both `traffic.js` sites (:395, :1577) and the import; the test fails while any `gaDims(` call in `js/live` is not covered |
| F10 | SF50 provenance names a commit without the builder | **fixed**: `_provenance.builder_state` ("working tree (uncommitted …)"), per-file sha256 of every builder / kernel source + a tree hash, also in SOURCES.json; the same for the PC-12 variant; the test fails if any source on disk differs; rebuilds are bit-identical (SF50 0db80513… from the fix-round-1 sources, 37e2952f… twice; PC-12 `none` = 87731cce…) |
| F11 | `docs/phase3_render.md` stale | **fixed**: SUPERSEDED banner (it describes 9267d3e0… / 87731cce…); `render_pc12_*` captions marked superseded; the test fails a phase3 write-up that names a model without its current hash or the banner |
| F12 | SF50 gear retraction directions; laptop GPU cost | **deferred**: no source found in fix round 2 either (AFM §7 points to the non-public PIM; 3A-15 does not say; web search nothing) → stays [inf, unverified] and the credits must say so; the GPU frame time needs the owner's laptop (section 9) |

## 12. Review fix round 3 (2026-11-13): dispositions (PC-12)

| # | finding | status |
|---|---|---|
| P1 | belly fairing hard-coded (pc12 `details.belly_fairing`), the 6.2° wing hung up to 65 mm below it (STA 5.4–6.8; two bumps from below) | **fixed** (fr3): fairing rebuilt from the drawn extent / lower outline with its lower half pulled 8 mm below the wing's lower skin wherever the wing is lower; the wing's carry-through is flat inboard of BL 0.85 [inf]; new geometry test "belly fairing covers the wing" (0 wing vertices below; closest 6.5 mm inside); `pc12_belly_low.jpg` |
| P2 | cabin section ~0.138 m low, windows / doors 0.13–0.18 m low, dorsal fin ~1.35 m aft, aft underside ~0.18 m low, wing ~0.12 m low | **fixed in the hwd3d build** (fr3, section 4): control lines re-fitted aft of the nose to the drawn profile, plan and body plan (crown / keel ≤ 3 mm, half-breadth ≤ 9 mm, sections rms 3–9 mm), glazing re-fitted, openings at the drawn water lines, wing +0.121 m, main-gear trunnion +0.104 m / well inboard (track 4.53, wheelbase 3.48, prop clearance 0.321 unchanged), nose-gear housing as drawn, dorsal fin from FR33, fin LE and strakes as drawn; interior / livery carried by the loft map; new tests (profile, aft underside, half-breadth, sections, dorsal fin, water lines; SKIP without the local reference) |
| P3 | winglet in side view 0.3–0.4 m forward, LE much less swept | **fixed** (fr3): winglet chord / TE laws, top chord and height fitted to the drawn side view (edges ≤ 30 mm at WL 1.94–2.10), span 16.28 / area 25.81 kept by re-deriving the planform; new side-view test |
| V2 / (b) | digitised Pilatus readings committed (test constants, builder and doc comments) | **moved** to the gitignored `refs/cache/local/models/pilatus_pc12_meas.json` (+ the local digitiser `refs/cache/local/models/tools/measure_pc12_mbp.py`); `test_models.mjs` loads it via `loadLocalRef` and SKIPs the 9 drawing checks without it; the builder keeps fitted parameters only (fr2's reading comments removed); section 4 describes the method without readings or registration numbers |
| S1 (PC-12 side) | the new upward gear check | PASS on the fr3 build (it failed on fr2's stowed oleo piston by 1.9 mm and, with a closed housing, on the nose wheel; the housing is open-topped) |
| — | outside the named files, minimal and needed by the rebuild | `js/aircraft/models.js` PC-12 landing-light anchors WL 1.027 → 1.148 (they follow the raised wing) and the frame span 16.281 → 16.280; `docs/phase3_models.md` section 3 diff: the restore site now reads `gaDims(icao, cat)` (changed by the Phase 2 workflow's `traffic.js` edit); `docs/phase3_sf50.md`: names the current PC-12 hash |


## 13. Review fix round 3, iteration 2 (2026-11-13): dispositions (PC-12, provenance, docs)

Current PC-12: sha256 6e349329… (override set `fr3` as revised here; rebuilt twice bit-identically; `none` still
87731cce… = `pc12/out`; `git status pc12` clean). Probes (gitignored, `out/fr3i2/`, the scratch scripts of this round and the
rechecker's `out/recheck3c_1/`): `fit_check` logic (interior / engine inside the skin) OK for `fr3` and `none`.

| # | finding | status |
|---|---|---|
| F1 | digitised drawing / AFM readings still in committed docs and test code | **fixed**: section 6's silhouette row now gives deviations only (top line within 0.06°, winglet rise within 17 mm), the dorsal-fin rows "starts where drawn (within 1 cm)", the SF50 AFM rows "within 0.12° / 0.01 m of the AFM", "inside the AFM front-view band" (also section 11 F5); section 4 no longer quotes the housing box or the dorsal-fin station; section 9 no longer quotes the tail-cone end station, the drawn firewall frame station or pod readings; the builder comment quotes no reading (`FR3_NOSE_HOUSING`: front station and bottom are fitted parameters, basis "fitted to the drawn box"). `test_models.mjs`: the AFM plan half-width moved to `afm_sf50_meas.json` (`plan_cowl_half_width_m`, with a `src` note); the nacelle check is now geometry-only (lip − waist ≥ 10 mm, fillet foot ≥ waist + 0.05 m) plus a separate AFM check that SKIPs without the local file. `docs/phase3_sf50.md` no longer quotes the AFM cowl half-width. The PC-12 loft knots are rounded to the millimetre (the loft moves < 0.5 mm; every drawing check still within the same limits). **Note for the owner**: decision (b) allows fitted parameters, and the `fr3` loft knots (PC-12) and `sf50_geom.py` control-line knots (SF50) are such fits — but at 0.2–0.6 m spacing they reproduce the drawn outlines to about a millimetre, i.e. the committed code still encodes the drawn outlines closely; coarsening them (fewer knots) would cost fit accuracy. A token grep of the 35 committed / to-be-committed Phase 3 files for the numbers of both local reference files leaves only such fitted parameters, model values and published dimensions (the stations / water lines of the openings are model parameters equal to the drawn centres) |
| F2 | cabin floor 43 mm narrower than the sourced 1.30 m, warped up to WL 1.37 aft, seat rails 65 mm / lining 40 mm below it; floor check redefined | **fixed**: cabin built at one floor height (the loft map's at STA 6.0, WL 1.244), floor one flat panel **1.300 m** wide (sourced 1.30; narrower only where the section is), **0** cabin vertices below its top (fix round 3: 118, up to 65 mm); `fit_check` OK. The meta check records a 2 % tolerance and its result; new test "cabin floor: one flat panel, sourced 1.30 m wide (2 %), no cabin item below its top; meta floor-width check within 2 %" (PASS; the fix-round-3 build fails it: 127 mm warp, 118 vertices, meta 1.257 m; pc12's `none` passes). Seen in `pc12_cabin_door.jpg`. **Also fixed (found in that render)**: fr2's door stations had put pc12's port side ledge across the airstair doorway (and the forward part of the cargo door) and the forward club seat in the airstair doorway: seats, tables and the baggage net 0.40 m aft, port ledge between the doors (`FR3_CABIN`, [inf: layout]); 0 cabin vertices in the airstair doorway band. The flight deck keeps the per-vertex loft map (its floor slopes ~7° [inf], nothing below it) |
| F3 | clean-clone run: 1 FAIL from `docs/phase3_video.md` naming a superseded PC-12 | **fixed**: the write-up check takes a per-type SUPERSEDED banner (a banner line naming PC-12 / pc12.glb marks only that type's parts); `docs/phase3_video.md` carries one for its PC-12 test clips (they show c46fe4fb…; re-render case P before publishing; the SF50 clips stay current). Clean-clone run (empty local-reference directory): 69 PASS, 13 SKIP, 1 KNOWN, **0 FAIL**; with the local reference: 82 PASS, 1 KNOWN, 0 FAIL |
| F4 | winglet plan view / blend, documented whole-wing offset exceeded; drawing prints span 16.114 m and a 4-blade prop | **recorded for the owner** (section 9 item 6): the fit stays limited to the side view on purpose — the sheet's printed span and propeller are not the PRO's (16.28 m, 5 blades: sourced), so its plan-view tip may not be either, and fitting it would move the planform away from the sourced span. Owner (or pc12 owner) decides whether to fit the plan view too (with a plan-view test). Not changed |
| F5 | nose strut through the housing's forward floor (gear down), housing end wall z-fighting the bay liner, sharp-edged tray | **fixed**: strut slot through the housing floor and the doors' forward inner corners — strut × housing **0** crossings and strut × doors **0** at gear 1 / 0.75 / 0.5 / 0.25 / 0 (fix round 3: housing 88 / 44 at gear 1 / 0.75 on c46fe4fb… with the rechecker's probe, doors 48 at gear 1); housing rear end 5 cm aft so its end wall clears the liner (liner × housing 0 crossings; no speckle in `pc12_gearup_housing.jpg` — **correction (iteration 3, finding F3)**: the gear-up
housing was not clean, the open strut slot showed the lime liner and the stowed strut from below, as the iteration-2 still
showed at the housing's forward end; closed in iteration 3, section 14, and re-shot), liner edge 3 mm inside the housing skin (the lime line along the housing in the first render of this round is gone), rounded lower edges (section exponent 3) with the doors on the curved floor. Still crossing (pc12's own geometry, as in `none`): the strut × the liner's front wall at STA 3.02 (90 / 32 at gear 1 / 0.75; resolved in iteration 3 by a notch) and × the keel skin at STA 3.00–3.02 (24 at gear 1) — section 9 |
| F6 | belly fairing a slab with vertical side walls (lip up to ~5 cm aft) | **fixed**: blended section (section 4): from below, within STA 5.12–7.50 and \|BL\| < 0.75, cells with the wing below the fairing **0** (fix round 3: 9 cells up to 59 mm at the edge), fairing lowest WL 0.872 (wing 0.885); the step at its edge is the 3 mm margin; P1 test closest 1.7 mm inside; centre-line outline unchanged where the drawn bottom is visible (lowered below it by 0 mm) |
| F7 | VHF 2 belly antenna root floating under the up-sloping aft belly | **fixed**: centre-line blades turned to the local skin slope; root − skin along the chord: transponder +4 / +4 / +4 / +4 mm, DME +4 / +4 / +4 / +4, VHF 2 +4 / +4 / +4 / +3 mm (fix round 3: VHF 2 +4 → −28 mm; positive = root inside the skin by pc12's 4 mm) |
| F8 | docs stale against fix round 3 / decision (a); SOURCES note "69 parts" | **fixed**: header, sections 1, 2 (counts, light anchors), 4, 6 (counts, closest −5.2 mm, travels obs under decision (a), ATTRIBUTION row PASS), 7, 9 (decision (a); video credits need the inf marker only for the gear motion), sections 10 / 11 rows annotated; `import_pc12.mjs` writes the part count from the build's meta ("70 parts (as built)") and the iteration-2 override text |
| F9 | open items vs drawing 190.10.40.432: radar pod drawn at the starboard tip, rudder TE, tailplane LE, lower cowl, whole wing | **recorded for the owner** (section 9 items 1–7): confirm the radar-pod position from PC-12 PRO photos or the drawing before the Phase 3b videos; the retracted trailing-link arm 58 mm (KNOWN) explained (trunnion raised 17 mm less than the wing). Not changed |

## 14. Review fix round 3, iteration 3 (2026-11-14): dispositions (provenance, PC-12 nose-gear housing and cabin floor)

Current PC-12: sha256 **957b3c4e…** (6,255,744 B, 72 parts, 427,257 triangles drawn; override set `fr3` as revised here;
rebuilt twice bit-identically; `none` still 87731cce… = `pc12/out`; `git status pc12` clean). SF50 rebuilt for its
provenance only (GLB bit-identical, 49242e41…; `docs/phase3_sf50.md` end). Probes (gitignored `out/fr3i3/probe/`, copies
of the rechecker's `dump_pose.mjs`, `below_lab.py`, `edge_hits.py`, `floor_patch.py` plus `cabin_top.py`). This iteration
was restarted after a container restart: the first attempt's F1 / F2 doc edits (committed since in b0d55c1) were checked
and kept; everything else below was done and measured in the restarted run.

| # | finding | status |
|---|---|---|
| F1 | digitised readings and raster-registration numbers of drawing 190.10.40.432 and of the MBP p.2 three-view still in the committed `docs/phase3_render.md` (D3, section 8 note) | **fixed**: D3 gives deviations only (crown 0.10–0.16 m low depending on the anchor, dorsal fairing starting ~1.35 m further forward than the model's, nose and cowling within 2 cm) and says it is superseded by fix round 3; the section 8 note keeps only the accuracy (±2 cm). The removed text is kept, with a `src` note, in the gitignored `refs/cache/local/models/pilatus_pc12_meas.json` (`phase3_render_D3`). New provenance check in `test_models.mjs` (the "fixers' token grep", now automatic): no raster token (pixels per metre or inch, pixel or dpi counts) in `docs/phase3_{models,sf50,render}.md`, `docs/phase3/SOURCES.json`, `tools/models/**` (incl. the test) and `js/aircraft/models/*.json` — PASS, 23 files; the committed bd22c60 `docs/phase3_render.md` (its raster resolution, registration scale and line width) and `sf50_geom.py` header (its scales) fail it |
| F2 | SF50 docs quoting AFM Fig 1-1 readings (SF50_FACTS nacelle row; `docs/phase3_sf50.md` §3 item 4 drawn chords) | **fixed**: the nacelle row gives the model parameters (`NAC_X0` / `NAC_X1` / `_NAC`: inlet FS 5.865, exit 8.010, cowl half-width 0.356 m at FS 6.10–6.30, top 2.635 m) labelled as fitted to Fig 1-1 with the readings in the local file; §3 item 4 names the chord ratio 0.643 fitted to Fig 1-1 and the model chords 1.838 / 1.181 m (after the scaling to the area), not the drawn chords. The SF50 question text now marks the pixel scales as history. Token grep and a value grep of `afm_sf50_meas.json`'s readings over the SF50 files: only model values / fitted parameters remain (allowed by decision (b)) |
| F3 | the strut slot (STA 2.905–3.135, ±0.08 m) open with the gear up: from below the zinc-chromate liner (67 cells) and the stowed strut (143 cells) showed through it; the F5 note called the gear-up housing clean | **fixed** (section 4): two strut-slot doors `gear_door_NSL` / `NSR` (slot outline − 4 mm, 18 mm solid, on the housing floor), hinged on their outer edges, `seq: 'down'` (open 85° whenever the leg is out, closed with the gear up) [inf]; clamshell notch = the slot outline; the bay liner's front wall notched over the slot up to WL 1.15; all nose doors hinge on their outer face. From below at gear 0 (`below_lab.py`, 1 cm): liner 67 → **14** cells and strut 143 → **3** cells, all on the 4-mm door gap lines; new test "gear retracted: nose-gear housing closed from below" (fails on a bad area ≥ 3 cm across: iteration 2 build 138 such cells, now **0**; 22 gap-line cells reported). Crossings strut / braces × doors / housing / liner: **0** at gear 1 / 0.75 / 0.5 / 0.25 / 0 in both directions (the closed slot doors × the liner's front wall had been 74 before the notch; the clamshells × housing in transit 876 before the hinge move; the strut × liner front wall, pc12's own, 90 / 32 at gear 1 / 0.75 → 0). Renders: `pc12_gearup_housing.jpg` (closed floor), `pc12_nose_housing.jpg` (slot doors beside the strut). The F5 row of section 13 is corrected |
| F4 | the flat 1.30 m floor (top WL 1.244, 30 mm panel) did not clear the wing carry-through: the upper skin up to 13.6 mm through the carpet, 0.74 m² (0.32 m² in the aisle), a bright patch in the aisle | **fixed** (section 4): inside the fuselage the wing's upper skin and pc12's spar tops are held 5 mm under the floor panel's underside (WL 1.209) inboard of BL 0.66, blending back to the unchanged wing by BL 0.75 (inside the fuselage side) [inf: structure]; 296 vertices lowered by up to 48.6 mm; nothing changes outside the fuselage. `floor_patch.py`: wing above the carpet in **0** cells (aisle and outboard); top-down map: the wing is the top-most surface only behind the cabin lining (|BL| ≥ 0.67). The floor stays at WL 1.244 (cabin height and door sills unchanged). New test "cabin floor: no other part rises through the carpet" (iteration 2 build: 1,798 cells of 2 cm, 0.72 m², 748 in the aisle, max 13.5 mm at STA 6.16; now **0**). Render `pc12_cabin_aisle.jpg` (the rechecker's camera): no patch. The nose-bay liner roof above the flight-deck floor is listed as a pc12 owner item (section 9; not fixable here without the wheel going through the floor) |
| F5 | decisions (a) and (b) not in `docs/PLAN.md` §6a/6b | **fixed**: `docs/PLAN.md` §6b has a paragraph "Orchestrator decisions under the owner's delegation (2026-11-13)" with (a) and (b), each marked as not from the owner directly and "the owner may overrule" (the file is shared; the edit is that paragraph only) |

Runs: `node tools/models/test_models.mjs` — 85 PASS, 1 KNOWN, 0 FAIL, 4 INFO (local reference present); clean clone
72 PASS, 13 SKIP, 1 KNOWN, 0 FAIL — until the concurrent rewrite of `docs/phase3_video.md` at 00:32Z, which makes the
write-up hash check FAIL on that page (section 6: it names the snapshot's PC-12 6e349329… without a SUPERSEDED line; the
page belongs to the video pipeline and was not edited here). `python3 -B tools/check_airport.py` — all hard checks passed (SOURCES coverage 165 files,
0 without an entry; D1 clean in every `docs/phase3_*.md`); its scope list needed no change (the new image is under
`docs/phase3/`, already scanned). Not changed / open: `docs/phase3_video.md` (Phase 3b's write-up, rewritten concurrently,
not edited here) names the PC-12 of its frozen snapshot (6e349329…) and needs the current hash or a SUPERSEDED line.

## 15. OD4 (2026-11-14): the original pc12 model, at the pc12 viewer's fidelity

**Owner request (2026-11-14, binding; `docs/PLAN.md` OD4):** "The pc12 modeling doesn't look as high fidelity. Do you mind
using whatever we had in the past." Two parts: (1) hwd3d draws the **original model of our own pc12/ project,
`pc12/out/pc12.glb`, unchanged**; (2) it must **look** in hwd3d as it does in the pc12 project's own three.js viewer.

### 15.1 The model: `pc12/out/pc12.glb`, unchanged
- `js/aircraft/models/pc12.glb` = `pc12/out/pc12.glb` @ f097de2, **sha256 87731cce…, bit-identical** (`cmp`), 69 parts,
  452,280 triangles as built (422,663 drawn: the internal `structure` stays excluded, as the pc12 viewer shows it only in
  X-ray), 31 draw groups. `node tools/models/pc12/import_pc12.mjs` (default mode, now documented as the current one) copied
  it and wrote `pc12_meta.json` from `pc12/out/pc12_meta.json` with `_provenance.source` naming `pc12/out/pc12.glb`, its
  commit and sha256, and `_provenance.reproduced`: `python3 -B tools/models/pc12/build_pc12_variant.py --set=none` (pc12's
  builders, no override, nothing written into pc12/) gives the same bytes (87731cce…, checked by the import, which refuses
  a differing `out/pc12_none`). `js/aircraft/models/SOURCES.json` says the same.
- **Variants retired**: the override sets fr2 / fr3 (re-lofted fuselage, moved windows / doors, dihedral, belly fairing,
  nose-gear housing, cabin floor; sections 4 and 10–14) are no longer used. `build_pc12_variant.py` and
  `import_pc12.mjs --variant` stay in the repository for the record. Sections 4 and 10–14 describe the retired builds.
- `js/aircraft/models.js`: header and frame basis name the original; frame constants re-measured (span 16.281); the
  registry landing-light anchors (pc12 has no lamp there) moved to **WL 1.000**, 4.6 cm under the original wing's lower
  surface at BL 3.15 / STA 6.20 (WL 1.047, measured on the GLB; fr3: 1.148 under its raised wing) [inf: position].
- `tools/models/test_models.mjs`: the checks the variants were built to pass (Pilatus drawing 190.10.40.432 / NGX
  documents) are kept and now report the original model's documented deviations as **KNOWN**, each bounded by the value
  measured on the unchanged file (bit-identical, so they cannot drift; any other file fails them) — the KNOWN mechanism
  now takes several bounds (`limits: {key: limit}`) and the drawing checks report numeric summaries (`n_deviations`,
  `max_dev_mm`, `worst_rms_mm`, `top_edge_max_mm`, `top_short_mm`, `top_line_dev_deg`): window count (+3 windows: airstair-
  door and cargo-door windows to port, exit window to starboard), belly fairing vs wing (51.7 mm), the belly fairing's
  upper half inside the cabin over the floor (125 mm, 3.6 m²), window / door stations and water lines (27 deviations, up
  to 761 mm), crown / keel −139…−141 mm, aft underside −339 mm, half-breadth +232 mm, body-plan sections rms ≤ 180 mm,
  dorsal fin (none before STA 10.4, top edge −449 mm), winglet top 254 mm under the drawn chord, wing top line 3.66° vs
  5.31°, crown / wing / winglet heights −139 / −189…−210 / −277 mm; the retracted trailing-link arm (67 mm, KNOWN since
  fix round 1). These are pc12 owner items (pc12/CLAUDE.md "Estimated / reconstructed"), not changed here.
- Docs: `docs/phase3_video.md` carries a "PC-12 parts SUPERSEDED" banner (its clips / snapshot hold fr3 6e349329…);
  `docs/phase3_sf50.md` names the current PC-12 hash. The five stills that show fr3-only features (`pc12_belly_low`,
  `pc12_cabin_aisle`, `pc12_cabin_door`, `pc12_gearup_housing`, `pc12_nose_housing`) are marked superseded in
  `docs/phase3/SOURCES.json` (not re-shot: the original has no nose-gear housing, slot doors or flat floor to show).

### 15.2 How the look was compared
The reference is `out/pc12_ref_viewer/` (gitignored; made by the previous step from the unchanged GLB with the pc12
project's own `pc12/web/dev.html` + three.js r160 — the harness that made `pc12/out/n_all.png` — at 11 cameras,
`cameras.json`; its `viewer_settings.md` records how that viewer lights and shades). hwd3d renders the same cameras with
`node dev/model_shot.mjs --jobs=out/pc12_look/jobs_ref.json --format=png` (new: `--format=png`, lossless) in two settings:
- **HWD ramp, noon** (the usual stills: Green Ramp, heading 135, 2026-11-13 12:30 PST, sun az 191° el 33.5°);
- **`look=studio`** (new, `dev/studio.js`, dev viewer only): the reference viewer's own lighting rebuilt on the hwd3d
  renderer — three r160 `RoomEnvironment` (black room, six emissive panels of radiance 17–100) rendered into hwd3d's
  equirect env map, its cosine-weighted irradiance fitted with second-order spherical harmonics (rms 0.037 of the exact
  integral), the dev.html sun (1.6 from (5, 10, −6)) and hemisphere (0.6, white / 0x8899aa), exposure 1 / 0.6 (three's
  ACES scaling), a backdrop that tone-maps to (223, 227, 230), no shadows, no fog, no bloom / vignette / grain / chromatic
  aberration. With the light the same, any difference left is a material / shading difference.
`python3 -I -B tools/models/pc12/look_compare.py` (new) writes the side-by-sides `out/pc12_look/cmp_<tag>_<cam>.jpg`
(reference | hwd3d) and reads back the sRGB of every material class at the **same pixels** in both images (the classes are
found by colour in the reference, whose background is uniform; masks eroded twice): navy cheatline, gold pin-stripe,
near-black trim / glass / seals, white paint.

### 15.3 Differences seen, root causes, fixes
Before (original GLB, hwd3d runtime as of fix round 3; `out/pc12_look/before/`, `cmp_before_*`), every image looked at:

| # | seen (hwd3d vs reference) | measured | root cause (hwd3d runtime) | fix |
|---|---|---|---|---|
| 1 (revised in 15.6, F2, and 15.7, F1: direct sun × τ) | glass transparent, cabin brightly lit (seats glowing grey-brown behind the windshield and side window), little reflection | seats ~(120, 110, 100) through 20 %-transmission glass | the cabin and flight deck were lit by the full sun (the glazing casts no shadow) and by the sky × 0.4; seen through glass of opacity 0.8 they still read mid-grey | light reaches the cabin only through the glazing: interior surfaces (mat 23; every plain material of the interior parts, `AC_PART_INTERIOR`; the back face of any skin) get sun × τ and sky × τ × 0.35, τ = 1 − glass alpha of the type (`glb.js stats.glazingT`: PC-12 0.196, SF50 0.232) [physics; 0.35 = windows' share of the cabin's view, inf]; an open door's group switches it off (`uCabin`) |
| 2 | glossy black windshield surround and the cheatline read grey-blue | trim lit side ~(60, 65, 75) | `acobj` added a clear-coat lobe (F0 0.04, roughness 0.05) on top of the base layer's own specular for every `paint_*` / `trim_*` material: the sky was reflected twice; the glb asks for one lobe (glTF metallic-roughness) | `acobj` = the glTF metallic-roughness BRDF as three.js r160 evaluates it: one GGX lobe with Smith-correlated visibility and Schlick Fresnel at the glb's roughness, Lambert diffuse, image-based part with three's DFG approximation and multiple-scattering compensation |
| 3 | shaded side of the white paint dull blue-grey | white (116, 128, 146) | the obj shader's hemisphere weight `smoothstep(0, 0.55, (1 + N.y) / 2)` gives a vertical surface 98 % sky, 2 % ground; the ground term used albedo 0.16 | sky / ground view factors of a plane, (1 ± N.y) / 2 (three's HemisphereLight rule), and the ground the aircraft stands on: the world's own pavement albedo (0.295, 0.285, 0.258; `js/shaders/ground.js`, NAIP-calibrated) lit by sun (× 0.8, own shadow [inf]) and sky → shade white (128, 131, 135), neutral **on vertical faces** (half ground, half sky); faces turned up take the clear sky's colour (15.6, F4) |
| 4 (revised in 15.6, F2 / F5, and 15.7, F1: no veil under the direct sun) | grey veil over the glass in sunlight, glass "flat" | glass body ~35 sRGB in sun | the glass tint was shaded as a diffuse layer (sun × 0.15 [inf] + sky) | glazing (`AC_MAT` 24) = thin tinted sheet: specular (env + sun glint, DFG) + transmission (1 − F)(1 − opacity), no diffuse veil; lens covers keep the Lambert term |
| 5 (default 0 since 15.6, F8) | magenta dashes on thin dark seams near the image edge (studio) | G = 0, R ≈ B ≈ 50 at the cargo-door top seam; HDR value there (0.002, 0.002, 0.003) | the final pass's chromatic aberration shifts R and B by about a fifth of a pixel at the frame edge; on a 1-px dark line on a bright ground R and B sample the bright neighbour | `post.ca` (new, default 1 = unchanged); 0 in studio. Not seen in the HWD-world stills (0 magenta pixels in all of them) |
| 6 | the selection glow could leak between aircraft | — | `uEmissiveBoost` was set only for a selected aircraft; GL keeps uniform values per program | every `acobj` draw sets it (0 / 0.15), with `uCabinT` / `uCabin` |
| 7 | dev stills graded differently from the app | — | dev viewer post had sat 1.0, grain 0.006; the app (js/live/app.js) sat 1.05, grain 0 | dev viewer uses the app's values |

Not causes (checked): **colour space** — `baseColorFactor` is linear in the GLB, glb.js keeps it linear, the renderer
lights in linear, tone-maps once (the same ACES fit as three) and encodes sRGB once (no double conversion: the
reference's hint does not hold); **parts dropped** — only `structure` (by design), every material of the reference is
drawn (`trim_black` 1,615 vertices in fus_fwd, `seal` 12,042, `paint_accent` 18,074, `paint_stripe` 3,251); **z-fighting /
depth** — the livery and the surround are cut into the skins (shared boundary vertices), the seals sit 7.5–9 mm off the
glass, the depth buffer is 32-bit float, near plane ≤ 0.3 m in the dev viewer: no fighting at any reference camera;
**normals** — smooth per-vertex normals from the file, unit length (test "parse": 0 non-unit); **MSAA** 4 in both; **the
dashed gold pin-stripe** is in the model (51 pieces in fus_aft), the reference shows the same dashes.

### 15.4 Result
Same-pixel read-backs (sRGB 8-bit medians; `out/pc12_look/measure_{before,studio,world}.json`; "white" = the white paint
just above the cheatline, the same surface; port cameras are in the shade at the HWD noon setting, starboard ones in sun):

| camera (side, light at HWD) | reference navy / white | hwd3d **studio** navy / white | hwd3d HWD before | hwd3d HWD after |
|---|---|---|---|---|
| cockpit (port, shade) | (20, 36, 54) / 157 | (24, 40, 60) / 163 | (31, 44, 63) / (124, 134, 146) | (33, 44, 58) / (128, 130, 133) |
| side (port, shade) | (34, 55, 72) / 164 | (37, 59, 83) / 173 | (32, 48, 74) / (119, 131, 146) | (32, 45, 64) / (128, 131, 135) |
| tail (port, shade) | (35, 56, 78) / 168 | (41, 64, 89) / 178 | (34, 49, 72) / (117, 130, 147) | (31, 45, 63) / (127, 131, 136) |
| nose (port, sun on the nose) | (15, 28, 44) / 229 | (13, 25, 40) / 224 | — | (49, 56, 65) / (221, 219, 215) |
| hwd_front34 (starboard, sun) | (42, 66, 92) / 203 | (45, 69, 96) / 203 | (101, 121, 139) / (225, 222, 218) | (106, 126, 142) / (228, 225, 219) |
| hwd_side (starboard, sun) | (57, 85, 114) / 207 | (62, 91, 121) / 207 | (108, 130, 146) / (227, 225, 221) | (109, 131, 146) / (229, 226, 221) |
| gold pin-stripe, cockpit | (115, 106, 49) | (114, 105, 51) | (93, 91, 54) | (100, 91, 46) |
| windshield surround (trim_black), cockpit | (24, 27, 30) | — | (13, 18, 27) | (8, 13, 20)–(23, 26, 29) |

- **Under the reference's own light (studio) hwd3d now reproduces the reference** within 0–11 levels on every class and
  camera (navy, gold, white; all 11 cameras in `cmp_studio_*`), with the same glossy black surround and soft-box
  reflections in the windshield. Remaining studio differences, all expected: the glass is darker (no diffuse veil, the
  cabin lit through the glazing: the reference viewer lights its cabin as if the skin were transparent — it has no
  shadows); the reference's grid lines and its `structure` part (seen through its windows) are absent; the soft-box
  reflections are smaller and crisper (equirect mip chain vs three's PMREM); the port-side navy is up to ~10 levels
  lighter (second-order irradiance fit of the room).
- **In the HWD world, shade** (every port camera): the cheatline is navy as in the reference, the trim black, the glass
  near-black with the cabin faint, the white paint a neutral grey (128–135 instead of the bluish 116–146 before; the
  reference's studio fill is brighter, 157–229).
- **In the HWD world, direct sun** (starboard cameras): the cheatline reads a mid steel blue, (104–117, 125–137, 140–152)
  vs the reference (38–62, 60–90, 84–120). This is the light, not the material (the studio rows prove the material path):
  the HWD noon sun puts ~6× the shade's light on that side, and the world's exposure (0.45, sfo3d's, kept: lowering it to
  0.36 / 0.29 was tried on the ramp and made the airport dull, `out/pc12_look/expo/`) maps sunlit white paint to ~230,
  where the glb's navy factor (0.10, 0.17, 0.27 linear = sRGB (89, 115, 142) at full reflectance, a light slate blue)
  falls in the mid-tones; the pc12 viewer shows its sunlit side at NoL 0.39 under a key of 1.6 with a fill of similar
  size, so the same paint stays in ACES's toe (navy). The warm sun (R / B 1.46 at 33.5° elevation) desaturates it further.
  Changing that would mean a darker world or different paint factors in the glb (pc12 owner); neither is done here.

### 15.5 SF50, renders, tests, open items
- **SF50** (same programs, no model change; 49242e41…): every `viewer_sf50_*` still re-rendered (the 13 of the set, with
  their recorded poses and times; `lights_dusk` at its 2026-11-14T01:05Z). Its accent colour is a dark linear navy
  (0.025, 0.064, 0.147) and stays navy in the same noon sun next to sunlit white — the paint factor, not the renderer,
  decides the PC-12 cheatline's tone in direct sun. Its `reg_panel` material (same white as the paint but id 0) and its
  paint now take the same single-lobe BRDF (before: paint with the extra clear coat, the panel without: a visible step).
  Glazing τ 0.232, interior parts `cabin_lining` / `cabin_seats` / `flight_deck` lit through it.
- **Renders** (`docs/phase3/`, 1920×1080 JPEG, HWD world, 2026-11-13 12:30 PST unless noted): `pc12_{front34, side,
  rear34, chase, cockpit, port, rear, flaps40, gear_closeup}` and all 13 `viewer_sf50_*` re-rendered
  (`node dev/model_shot.mjs --jobs=out/pc12_look/jobs_docs_pc12.json --prefix=pc12`, `…jobs_docs_sf50.json
  --prefix=viewer_sf50`, `--t=2026-11-14T01:05:00Z` for the dusk still); captions name 87731cce… / 49242e41…. Seen (every
  image looked at): dark windshield with its black surround and centre post, black-framed cabin windows, near-black glass
  with the flight deck faint behind it, navy cheatline on the shaded side and a steel-blue one in direct sun, dashed gold
  pin-stripe, neutral grey shade on the white paint, propeller blades with a sun sheen, the SF50's navy accent, dark
  glazing and fan; the dusk still with lit lenses / sprites over a dark aircraft. Still superseded (not in the requested
  set, show older builds): `pc12_fade`, `pc12_gear_half`, `pc12_lights_dusk`, `viewer_desktop`, `viewer_phone`, and the five
  fr3-only stills (15.1).
- **Comparison set** (`out/pc12_look/`, gitignored): `before/`, `studio/`, `world/` — the 11 reference cameras as PNG;
  `cmp_{before,studio,world}_<cam>.jpg`; `measure_*.json`; `crops/` (windshield, cockpit, door seam);
  `expo/` (the exposure trial); `livetest/` (the app snapshot below).
- **App snapshot**: `RELAY=none PORT=8756 OUT=out/pc12_look/livetest PREFIX=od4 node livetest.mjs jobs/views.mjs`
  (desktop): ready in 3.0 s, 0 console errors / warnings, D1 type-only (27 masked), every view and sheet shot and looked
  at — the airport renders as before (the only renderer-file change is `uCA`, default 1 = the old constant; the app still
  draws placeholders, Phase 3b wiring is in progress elsewhere).
- **Tests**: `node tools/models/test_models.mjs` → **72 PASS, 13 KNOWN, 0 FAIL**, 4 INFO (local reference data present).
  New since the fr3 runs: the 12 PC-12 drawing / NGX checks report KNOWN on the original (15.1); `SYNC_KEYS` gained
  `groundRef`, which `js/live/aircraft.js` (Phase 3b, edited concurrently) now sets on every drawable — the placeholder
  ignores it, the sync check needed it. `python3 -I -B tools/check_airport.py` → **RESULT: ALL HARD CHECKS PASSED**.
- **Performance**: per-shot render time in SwiftShader unchanged (12–22 s for three frames at 1920×1080, as before);
  `acobj` now evaluates one GGX lobe and one env lookup per fragment (two of each with the old clear coat). Laptop GPU
  frame time not measured (no GPU here).

Open / not verified:
- **[Superseded by 15.6: the band takes an appearance-fitted navy in the HWD world (`paintFit`).]** The **sunlit cheatline** stays lighter than the reference (15.4) — a property of the glb's paint factor under outdoor
  sun at the world's exposure; options for the owner: keep (physically consistent), a darker navy factor in `pc12/`
  (pc12 owner), or a darker world exposure (rejected here: dull airport).
- **[Superseded by 15.6: no τ on the light path any more; sky × 0.35, 1 with a door open.]** The **cabin rule** constants (sky × τ × 0.35, sun × τ) and the ground's 0.8 sun factor are inferred; the reference
  viewer lights its cabin unshadowed, so hwd3d's cabin is darker than the reference's in every setting.
- **Studio mode** approximates three's PMREM with hwd3d's box-filtered equirect mips (crisper soft-box reflections; the
  overhead panel near the pole is spread differently) and the room's irradiance with second-order harmonics (port-side
  navy up to ~10 levels lighter). The reference viewer's grid and its `structure` part are not drawn.
- **Depth at airport range**: no z-fighting at the 11 reference cameras (near ≤ 0.3 m in the dev viewer); at the app's
  overview (near up to 5 m, aircraft ~1.5 km away) the 7.5–9 mm seal offsets are below the depth resolution, but the
  seals are sub-pixel there; not checked in the app (it draws placeholders until Phase 3b).
- **[Superseded by 15.6: the renderer's default is 0 now.]** **`post.ca`** stays 1 in the app (js/live/app.js is not this package's); proposed 0 (section 8).

### 15.6 OD4 iteration 2 (review of 2026-11-14, findings F1–F9): dispositions
The review (its renders `out/pc12_look_rc1/`, gitignored; reference shots of `pc12/web/dev.html` = the `n_all.png` harness
and of the production stage viewer) found the owner's main complaint still visible: a pale steel-blue cheatline on every
sunlit side, and cabin windows that read as black holes. Every number below is a same-pixel median (sRGB 8-bit) at the 11
reference cameras, classes found by colour in the dev.html shot (masks eroded by two pixels), read in the review's renders (= the
state before this iteration, "rc1") and in this iteration's (`out/pc12_look_it2/final_world`, `final_studio`,
`final_studio_glb`; `measure_final.json`; script `out/pc12_look_it2/tools/measure_fin.py`). World = HWD Green Ramp,
2026-11-13 12:30 PST (sun az 191°, el 33.6°); starboard cameras (`hwd_*`) in sun, port cameras in shade.

| # | finding | root cause | fix (file) | result |
|---|---|---|---|---|
| F1 major (factor refitted in 15.7, F2: (0.035, 0.086, 0.181)) | navy cheatline reads pale steel blue in sun | the glb's paint_accent (0.10, 0.17, 0.27), glTF linear, is a light slate blue as a reflectance; the pc12 viewer keeps it in the toe of ACES (studio key at NoL ~0.4, no sun), the HWD noon sun puts it in the mid-tones (white paint ~230 in both) | `js/aircraft/models.js` `paintFit: { paint_accent: [0.017, 0.059, 0.137] }` (PAINT_FIT header): the drawn LINEAR colour of the band, replaced at load; glb bytes unchanged; `MODEL_LOAD_OPTS(type, { palette: false })` / dev `palette=glb` draw the file's factor [inf: appearance fit] | sunlit band (5 cameras) rc1 (104–117, 125–137, 140–152) → **(42–61, 73–84, 99–111)**, reference (38–62, 60–90, 84–120); shaded band rc1 (31–36, 44–47, 58–64) → (14–21, 24–28, 37–41), reference (20–35, 36–56, 54–79) |
| F2 major (revised in 15.7, F1: direct sun × τ, no veil under the sun, bloom knee) | cabin windows black holes, no seal contrast, interior gone; ~10× darker than the reference under its own light | (a) the cabin rule multiplied the light coming IN by τ = 1 − glass alpha (0.196) and the view path multiplied it again: 1.4–4 % effective; the glb's opacity is the pc12 viewer's pane coverage, not a measured transmission; (b) the glazing had no diffuse term (three.js shades the glb's BLEND glass with a Lambert layer of the tint at 'opacity' coverage) | `js/aircraft/detailed.js`: interior surfaces take the sun through the openings (shadow map) with no glass factor and the sky × `uCabinAmb` (0.35, `CABIN_SKY_SHARE` [inf]); `GLASS_FS` glazing gets the pane's diffuse return (tint × opacity, as three.js) | cockpit camera, world rc1 → it2 (dev): door window (11, 18, 24) → **(22, 30, 38)** (45, 48, 50); cabin window 2 (15, 21, 29) → (27, 34, 41) (35, 38, 41); side window (4, 9, 17) → (14, 21, 30) (23, 27, 31); door seal (16, 20, 25) now darker than its glass, as in dev (seal 32 < glass 47). Studio (the reference's own light) rc1 → it2: door window (5, 5, 4) → **(52, 51, 51)**, cabin window (1, 1, 0) → (29, 31, 33), windshield (31, 34, 38) → (42, 49, 54) (39, 48, 55), seal (24, 24, 26) < glass. Seats, panel and lining visible through every pane |
| F3 minor | sunlit white in the ACES shoulder, warm cast | the world's exposure 0.45 (sfo3d's) and the sun's colour at 33.6° elevation (renderer sun CCT 5,276 K, sky model) | **not changed** (owner decision: a lower exposure or a softer shoulder changes the whole world; a darker exposure was tried in OD4 and rejected as a dull airport). The navy no longer depends on it (F1) | white unchanged: hwd_side p5 / p50 / p95 220 / 227 / 232 (dev 198 / 217 / 236) |
| F4 minor | shaded faces turned up read blue | physical under a clear sky: such a face sees mostly sky. Checked: the renderer's sky radiance (cosine-weighted upper hemisphere, `R.light.skyUp`) is (0.326, 0.489, 0.809) = CCT 14,500 K; the shade light on a face with N.y 0.7 is ~9,900 K, on a vertical face ~6,900 K (half pavement 5,700 K, half sky). Measured clear-sky skylight spans ~0–263 mired, i.e. CCT ≳ 3,800 K to infinity (Peyvandi, Hernández-Andrés et al., JOSA A 33, 1049 (2016), as summarised by a web search of the paper, not read in full); 14,500 K = 69 mired lies inside | none; 15.3 row 3 now says "neutral on vertical faces" | upper fuselage in shade unchanged (106, 121, 143) |
| F5 minor | glass flat dark in the world, no glossy highlights | the world's sky has no bright panels to reflect (the reference's soft-box blobs are its RoomEnvironment); with the glazing's diffuse term missing, the panes also lacked the reference's grey tint | the F2 fix (pane diffuse return, cabin light) | windshield in sun (hwd_front34) (26, 26, 27) → **(74, 75, 75)** (dev (57, 65, 73)); in shade (cockpit) (23, 22, 21) → (33, 35, 36) (dev (39, 48, 55)); sky / ground gradients in the side panes as before; a sun glint only at aligned angles (physics) |
| F6 minor | cabin black through an open door | the rule was off only for the door's own group | `detailed.js`: while any cabin door is open (> 0.02), `uCabinAmb` = 1 on every group (sky unoccluded, sun through the shadow map, as the pc12 viewer lights its cabin) | `pose_doors_open` (`out/pc12_look_it2/final_pose/`, `cmp/pose_doors_gearup.jpg`): seat, lining and floor visible through the airstair opening. Seen: through the open cargo door the inner side of the starboard skin shows the exterior livery (pc12's skin is one double-sided surface; the pc12 viewer shows the same) - a pc12 model item, not changed |
| F7 minor | a model_shot job inherited doors opened by an earlier job | `setControls` merges `doors`; BASE `doors: null` passed `{}` | `dev/model.js poseAircraft`: every door pivot is closed first, then the named ones applied; stale keys zeroed | after the `doors_open` job, `flaps40_cove`, `gearup_bay`, `nacelle_intake` render with every door closed (rc1: both open) |
| F8 minor | 1-px purple / red fringes (chromatic aberration) in world and app | `post.ca` defaulted to 1 (sfo3d's constant) and the app never sets it | `js/renderer.js` default `post.ca ?? 0.0` (section 8; `js/live/app.js` not touched) | fringe pixels on the aircraft (R − G > 25 and B − G > 15) rc1 9–41 per still → **0–1**. Airport background outside the aircraft (mask grown by three pixels): 78–85 % of pixels identical, mean change 0.18–0.30 levels, all of it on edges near the frame border (the removed radial shift; `bgdiff` checked on hwd_tail) |
| F9 minor | SF50 chase still caught a strobe / beacon flash (discs 61–91 pixels across) | `DetailedAircraft.seed = Math.random()`: the flash phase differed per page load | `dev/model.js` `lseed` (default 0.5: beacon and strobes between flashes in the final frame of `shot()`, t = 1.033–1.066 s); `dev/model_shot.mjs` BASE `lseed: null`. The daylight sprite size is `js/env/aircraft_lights.js`'s (section 8 item 4, not changed) | `viewer_sf50_chase.jpg`: saturated discs of 20 pixels or more before (82×81, 62×64, 55×56) → none; `viewer_sf50_gear_half` likewise. `viewer_sf50_lights_dusk` pins `lseed` 0.378 (tip + tail strobes flash in the final frame) so the dusk still shows them reproducibly |

**F1 in detail.** Three options were rendered at the 11 cameras (plus four candidates at four cameras,
`out/pc12_look_it2/navy_*`):
- the glb factor as written (rc1): shade right, sun steel blue (above);
- the review's option b, the factor read as sRGB-encoded (decoded (0.010, 0.025, 0.059)): sun a grey navy (36–55, 46–61,
  64–73), shade near black and neutral (13–20, 16–22, 23–27), and under the reference's own light (studio) black (0–4,
  2–17, 8–39) where the reference shows (15–62, 28–90, 44–120) - the pc12 author tuned the palette in that viewer, so the
  factor is not an sRGB-typed value; rejected;
- **the fitted factor (taken)**: per channel, the linear value whose sunlit band in the world has the reference's median
  at the same pixels (cameras hwd_front34 and hwd_side; renders at factors 0.010 / 0.020 / 0.025 / 0.030 / 0.10 for R,
  0.025 / 0.040 / 0.060 / 0.064 / 0.17 for G, 0.059 / 0.090 / 0.130 / 0.147 / 0.27 for B, interpolated in log factor):
  (0.017, 0.059, 0.137) - sRGB #23466A at full reflectance, next to this repository's SF50 accent (0.025, 0.064, 0.147).
  Checked on all five sunlit cameras: (50, 74, 100), (61, 84, 111), (47, 76, 106), (50, 74, 99), (42, 73, 104) against the
  reference (42, 66, 92), (60, 89, 118), (57, 85, 114), (38, 60, 84), (62, 90, 120). In shade the band is darker than the
  reference's, (14–21, 24–28, 37–41) vs (20–35, 36–56, 54–79): the world's shade is darker overall (white paint in shade
  126–129 vs the reference's 173–226, which has a studio fill and no shadow); it stays blue (B − R 20–26), not black.
- Cost: under the pc12 viewer's own light (`look=studio`) the fitted band is darker than the reference (1–4, 7–40, 21–77);
  `look=studio&palette=glb` still reproduces the reference band exactly as in 15.4 (navy (24, 40, 60) / (37, 59, 83) / …
  at the cockpit / side cameras), so the material path is unchanged and the difference is the documented colour only.
- The gold pin-stripe (0.72, 0.60, 0.18) and the white / belly paints keep the glb's factors: gold in sun (hwd_nose)
  (111, 100, 54) vs reference (109, 100, 46), in shade (cockpit) (99, 91, 46) vs (115, 106, 49).
- Owner decision: this is a hwd3d-side colour for the pc12 band, chosen by appearance; the pc12 owner may retune pc12's
  palette instead (then `paintFit` goes), or the owner may prefer the file's factor (`palette: false`).

**Renderer / shared files changed** (all documented above and in section 8): `js/renderer.js` (`post.ca` default 0) and
`js/shaders/post.js` (comment). Not changed: `js/gl.js`, `js/scene.js`, the world shaders, `js/live/**`, `js/env/**`.
Aircraft runtime: `js/aircraft/detailed.js` (cabin rule, glazing diffuse, door rule, `CABIN_SKY_SHARE`), `js/aircraft/
models.js` (`paintFit`, `paletteLook`, `MODEL_LOAD_OPTS(type, {palette})`, `loadModel(..., {palette})`), `js/aircraft/glb.js`
(materials keep `baseGlb` when the look hook replaced the factor). Dev: `dev/model.js` (`palette=glb`, `paint=` (a dev-only
linear-colour experiment), `lseed`, door reset), `dev/model_shot.mjs` (`--palette`, `--paint`, BASE `lseed`).

**Renders** (every image looked at): `docs/phase3/pc12_{front34, side, rear34, chase, cockpit, port, rear, flaps40,
gear_closeup}.jpg` and all 13 `viewer_sf50_*.jpg` re-rendered (jobs `out/pc12_look_it2/jobs_docs_*.json`; dusk at
2026-11-14T01:05Z); before / after sheets `out/pc12_look_it2/cmp/docs_pc12_{1,2}.jpg`, `docs_sf50_{1,2}.jpg`. Seen: a navy
band on the sunlit sides and a dark navy one in shade, the gold pin-stripe, tinted panes with the seats, panel and cabin
lining visible behind them, dark seal rings around every cabin window, the windshield's black surround; no strobe discs in
the daylight stills; the SF50's cabin now faintly visible through its windows, its navy and fan unchanged.

**Tests**: `node tools/models/test_models.mjs` → **77 PASS, 13 KNOWN, 0 FAIL**, 4 INFO (local reference data present). New
checks: the cabin rule (no glass factor on the light path; 0.35 closed, 1 on every group with a cabin door open; PC12 and
SF50), the palette (`paintFit` replaces only the named factors, `baseGlb` recorded, `palette: false` = the file), and the
renderer's chromatic-aberration default.

**App** (`RELAY=none PORT=8778 OUT=out/pc12_look_it2/livetest PREFIX=it2 node livetest.mjs jobs/views.mjs`, desktop):
ready in 3.8 s, 0 console errors / warnings, every view and sheet shot and looked at; side by side with the review's run
(`out/pc12_look_it2/cmp/livetest_rc1_it2.jpg`) the airport world renders the same (overview, tower, Green Ramp, West
Hangars, 28L final; the traffic differs because the replay instant and the concurrently edited traffic engine differ). The
PC-12 in the app (the review's job, one parked track switched to the PC12 type: `out/pc12_look_it2/app_pc12/`, 0 errors):
navy band, flight-deck seats visible through the side window, cabin windows still small dark slots at 25 m on a
1280 × 720 frame (about ten pixels wide; their interior is too small to read there).

**`python3 -I -B tools/check_airport.py`** → **RESULT: ALL HARD CHECKS PASSED** (SOURCES coverage 165 files, 0 without an
entry; D1 clean in every `docs/phase3_*.md`; D1(d): 0 types named with a dated window). An earlier run during this
iteration failed on one D1(d) hit in `js/live/traffic.js` (a comment of the concurrent Phase 2 traffic workflow, edited at
07:28Z); that workflow has since changed it; not touched here.

**Open / not verified (iteration 2)**: the fitted navy is an appearance choice for the HWD world (owner / pc12 owner may
prefer the file's factor or a retuned palette); the cabin's sky share 0.35 and the pane's diffuse return are inferred
(they reproduce the reference's dark-grey tinted panes in the studio, (52, 51, 51) vs (45, 48, 50)); in the world the
panes stay about half as bright as the reference's in shade because the world's shade is darker (white 126–129 vs
173–226); no soft-box highlights in the world glass (a clear sky has none); sunlit white stays in the ACES shoulder (F3,
owner); the inside of the pc12 skin shows the exterior livery through an open cargo door (pc12 model); laptop-GPU frame
time not measured (SwiftShader only; the shaders gained no passes: one Lambert term on the glazing, one uniform less).


### 15.7 OD4 iteration 3 (review of 2026-11-14, findings F1–F7): dispositions
The review (its renders `out/pc12_look_rc2/`, gitignored, = the state after iteration 2, "rc2") found the sunlit glazing a
regression: flat, milky grey-beige panes in direct sun. Numbers below are same-pixel sRGB medians at the 11 reference cameras
(classes and boxes from the review's `tools/windows.py`, `measure.py`, `boxes.json`; masks from the dev.html reference
shot, eroded by two pixels), read in rc2 and in this iteration's renders (`out/pc12_look_it3/final_world`, HWD Green Ramp
2026-11-13 12:30 PST, sun az 191° el 33.6°: starboard `hwd_*` cameras in sun, port cameras in shade). Experiment renders,
the scripts that measured them and the side-by-sides are in `out/pc12_look_it3/exp/` and `out/pc12_look_it3/cmp/`.

**The main root cause: the bloom veil (`js/renderer.js`, `js/shaders/post.js`, sfo3d's, unchanged until now).** The bloom
pyramid has six levels; its first down pass takes every pixel of the frame (no threshold, only a soft compression
1 / (1 + 0.02 lum)), the up pass adds every level back at weight 1, and the final pass adds the sum × `post.bloom` (0.012).
A uniform field therefore gains 6 × 1.2 % = 7.2 %, and a small dark detail takes 7.2 % of its blurred surroundings: a
veiling glare that lifts every dark aircraft detail next to sunlit white paint. Decomposition of the sunlit cabin windows
at hwd_front34 (iteration-2 code with the cabin sun × τ and no veil under the sun): (56, 56, 58) with the bloom,
(25, 29, 34) without it; reflection alone (black interior, no veil) (41, 42, 42) with it, (5, 10, 16) without. About 30
sRGB levels of every sunlit window, trim edge and tyre were bloom. The pc12 reference viewer has no bloom.

| # | finding | root cause | fix (file) | result (rc2 → it3; reference dev / stage) |
|---|---|---|---|---|
| F1 major | sunlit glazing milky grey-beige, no tinted-glass contrast | (a) the bloom veil (above); (b) iteration 2 let the direct sun into the cabin with no glass factor, so the light lining (0.86) shone through the panes; (c) the pane's diffuse veil (tint × opacity, a 3.6 % grey card) was lit by the full sun | (a) bloom knee with gain compensation (`js/shaders/post.js`, `js/renderer.js` `BLOOM_KNEE` 4; below); (b) `js/aircraft/detailed.js`: direct sun on interior surfaces × the type's glazing transmission τ (`uCabinSun` = `glb.js stats.glazingT`: PC-12 0.196, SF50 0.232; it crosses the pane on the way in, the view path applies it again on the way out), the sky keeps the share 0.35 without τ (the review's suggestion; it stands for the windows' light and its inter-reflection in a light cabin, which restored the shaded side in iteration 2) [inf]; (c) `GLASS_FS`: the glazing's (mat 24) diffuse return takes the sky / ground light only, `GLASS_VEIL_SUN` 0 (a clear tinted pane does not scatter the direct beam into a grey veil [inf]); lens covers keep the sun | sunlit cabin windows hwd_front34 (99, 97, 90) → **(32, 35, 40)** (53, 59, 60) / (36, 39, 42); hwd_side (76, 79, 81) → **(39, 42, 46)** (35, 42, 49) / (24, 29, 34); cool, dark tinted glass with the sky's gradient in it (`cmp/half_hwd_front34.jpg`, `exp/cmp_side_K.png`). Shaded windows 2–5 levels darker than rc2 (the veil of the sunlit ground is gone): side (31, 34, 36) → (27, 29, 32) (23, 28, 33); cockpit door (22, 30, 39) → (20, 28, 37) (45, 48, 50); cabin window 2 (26, 34, 42) → (24, 32, 39) (35, 38, 40); window 3 (32, 38, 43) → (30, 35, 40) (33, 35, 38); front34 (28, 34, 41) → (23, 30, 36) (37, 41, 41). White beside them unchanged (232, 229, 225) / (122–128, 128–132, 137–138) |
| F2 minor | shaded cheatline near-black navy (cost of the sun-only fit) | no single reflectance matches both sides: the world's noon sun puts ~6× the shade's light on the sunlit side, the pc12 viewer's studio ~2–3× | `js/aircraft/models.js` `paintFit` refitted on ALL 11 cameras together (the review's suggestion): per channel, the linear factor minimising the squared sRGB error of the band median against dev.html over the five sunlit, five shaded cameras and the nose, each camera interpolated in log factor between renders at five factors on the line from the glb's (0.10, 0.17, 0.27) to iteration 2's (0.017, 0.059, 0.137) (`exp/v6`, `exp/tools/fitnavy.py`): **(0.035, 0.086, 0.181)** [inf: appearance fit] (sRGB #345376 at full reflectance) | rms error over the 11 cameras (all with the bloom knee): glb factor 33.2, iteration 2's 21.5, **joint 17**. Sunlit band (49–68, 80–95, 110–124) (dev (38–62, 60–90, 84–120); rc2 (42–61, 73–84, 99–111)): a little lighter than the reference now. Shaded band (14–18, 26–28, 42–46) (dev (20–35, 36–56, 54–79); rc2 (14–21, 24–28, 37–41)): bluer than rc2, still darker than the reference (L* ~9 vs ~22). The bloom knee darkened the shaded band by ~4 levels at a given factor (it no longer takes the veil of the sunlit ground), so the joint fit only holds rc2's shade level. Left to the owner / pc12 owner (palette, or which side to favour). Comparisons under the pc12 viewer's own light need `look=studio&palette=glb` (models.js PAINT_FIT header) |
| F3 minor | black trim, seals, tyres, prop blades ~50 in sun | partly the bloom veil; the rest is physics: a 4.5 % albedo tyre / blade (`tire`, `prop_blade` (0.045, 0.045, 0.05)) in the same sun as 92.5 % white paint reflects ~5 % of its light, ~45–50 sRGB with this tone curve; the warm cast is the warm sun and the pavement (acEnv / acGround) | the bloom knee (F1 a) | dark class (very dark in dev and stage): hwd_side (47, 44, 41) → **(28, 27, 25)**, hwd_rear34 (30, 28, 26) → (18, 17, 16), front34 (32, 31, 29) → (26, 24, 23), cockpit (20, 22, 26) → (16, 18, 22), side (16, 16, 17) → (10, 10, 11); hwd_front34 (56, 52, 48) → (50, 45, 42) and hwd_nose (54, 50, 46) → (49, 45, 42) - those pixels are mostly tyres and blades in direct sun: with `trim_black` at albedo 0 they are unchanged (50, 45, 42), with that and every material's env reflection off (43, 39, 37) (`exp/v4` trim0 / trimEnv0), i.e. sunlit diffuse dark paint, not trim. Windshield surround in shade (cockpit box) (13, 18, 24) → (9, 14, 21) (dev (24, 27, 30)). The side-window frame of hwd_front34 at x 1060: its inner lip still reads (69, 65, 63) / (37, 39, 42) (rc2 (83, 78, 74) / (62, 62, 61); dev (46, 47, 50) / (15, 16, 18)): a glossy edge (roughness 0.16) at a grazing angle mirrors the sunlit pavement - physics in an outdoor scene, a black room in the reference. Accepted |
| F4 minor | glass neutral / warm, no cool sheen or highlight bands | the bloom veil and the sun-lit veil warmed the panes; the world's clear sky has no soft-box panels | F1 (a)–(c) | the panes are cool now: cabin windows (32, 35, 40) / (39, 42, 46); the reflected sky gradient (bluer at the top of each pane, paler toward the horizon) is in every cabin window (`exp/v1/dbgEnv_hwd_side.png`: the env term alone). Sunlit windshield (hwd_front34) (74, 75, 75) → **(21, 24, 31)**, now darker than the reference (57, 65, 73) / (48, 55, 62): it faces up (N.y 0.45–0.85) and mirrors the deep-blue upper sky at F ≈ 0.05–0.09, where the reference mirrors its room's ceiling panels. Shaded windshield (cockpit) (33, 35, 36) → (29, 30, 31) (39, 48, 55). A veil share of 0.25 / 0.5 under the sun was rendered (`exp/v9`): windshield (30, 33, 39) / (37, 42, 48), but the hwd_side cabin windows then (44, 48, 52) / (48, 55, 59) - not taken (it is the grey veil of F1). No horizon / sheen term added: the sky the panes mirror is the world's own |
| F5 minor | shaded faces turned up read blue | physical under a clear sky (15.6 F4) | none (owner decision) | unchanged: the knee leaves uniform areas as they were (below); bluish shaded faces of the review's `pose_win_shade` (104, 124, 154) → (103, 124, 154) at the same pixels |
| F6 minor | sunlit white in the ACES shoulder, warm | world exposure 0.45 and the sun's colour (15.6 F3) | none (owner decision) | unchanged: sunlit white (228–231, 225–229, 220–224), shaded white (126–129, 130–133, 137–140) (white class, rc2 identical) |
| F7 minor | SF50 dusk still: strobe discs cut by the fin and a wing edge | sprites are depth-tested; the sfo3d pull toward the camera (min(2 m, 5 % of the distance), 0.75 m at 15 m) is less than the distance from a lens to the airframe beside it | `js/aircraft/detailed.js lightSprites` flags its sprites (`pull: true`), `js/scene.js` packs the flag (iData.y), `js/shaders/sprites.js` pulls a flagged sprite toward the camera by 3 m or its drawn radius (at most half the distance) and keeps its angular size (s × (d − pull) / d); 3 m ≈ the depth of the airframe around an extremity light [inf]; an occluder farther from the lens (the fuselage in front of the far wing tip: 5.9 m on the SF50) still hides it. Other sprites (airfield lights, placeholders) unchanged | `docs/phase3/viewer_sf50_lights_dusk.jpg` (lseed 0.378): tail-strobe disc and right-tip disc whole, no fin / wing edge through them, same disc sizes as before (`exp/cmp_dusk3.png`: docs before / now). The two discs at the left tip are two lights (landing + strobe) |

**Bloom knee, the renderer change (all callers: app, video pipeline, dev viewers).** `js/shaders/post.js` DOWN_FS, first
pass: each tap is weighted by w = v² / (v² + K²) of its display-referred luminance v = lum × exposure (K = `post.bloomKnee`
?? `BLOOM_KNEE` = 4 in `js/renderer.js`; 0 = sfo3d's behaviour): highlights (lights, glints, the sun; v ≫ K) bloom as
before, diffuse surfaces (sunlit white paint v ≈ 2: w 0.2; pavement v ≈ 1: w 0.06) hardly. FINAL_FS gives the left-out share
of a uniform field back as the pixel's own gain, col × (1 + `post.bloom` × levels × (1 − w) / (1 + 0.02 lum)), so a uniform
area keeps its brightness exactly while a dark detail no longer takes a veil of its bright surroundings. Checked in the HWD
world (`exp/v4`, `exp/v7`, knee 0 vs 4, same frame): a wide ramp view, a hangar view and the hwd_side / side cameras - median
pixel change 0, 5th–95th percentile −1…+1 sRGB level, 1st percentile −4…−10 (dark details beside bright ones); the night
ramp (2026-11-14 05:00Z) 1st–99th percentile within ±1; the dusk still 1st percentile −2, median 0 (`exp/cmp_knee_wide.png`,
`cmp_knee_hangars.png`, `cmp_night_wide.png`). Bloom around lights and the sun is unchanged. 4 rather than 2: at K = 2 the
sunlit windows read (40, 43, 46) / (45, 47, 50) and the dark details keep more veil; both are inside the review's target.

**Under the pc12 viewer's own light (`look=studio`, `out/pc12_look_it3/final_studio{,_glb}`).** `palette=glb` still
reproduces the reference band exactly as in 15.4 / 15.6 (cockpit (24, 40, 60), side (37, 59, 83), hwd_front34
(45, 69, 96), hwd_side (62, 91, 121): unchanged), so the material path is unchanged. The studio has no bloom (the knee does
nothing there). The glazing is darker than the reference there now, by design: the reference viewer lights its cabin as if
the skin were transparent and lays its pane veil under its key light; hwd3d's cabin takes the key × τ and its panes no
veil under a direct light. Cockpit door window (52, 51, 51) → (30, 32, 34) (reference (45, 48, 50)); hwd_front34 cabin
windows (48, 52, 55) → (29, 32, 35) ((53, 59, 60)); hwd_front34 windshield (44, 52, 58) → (29, 34, 39) ((57, 65, 73));
shaded side windows unchanged (43, 49, 55); cockpit windshield (42, 49, 54) → (40, 46, 52) ((39, 48, 55)). With the
default palette the studio band is the fitted navy (cockpit (5, 21, 42), hwd_side (20, 53, 92)): studio comparisons of the
band need `palette=glb`.

**Renders** (every image looked at): `docs/phase3/pc12_{front34, side, rear34, chase, cockpit, port, rear, flaps40,
gear_closeup}.jpg` and all 13 `viewer_sf50_*.jpg` re-rendered (`node dev/model_shot.mjs --jobs=out/pc12_look_it3/jobs_docs_pc12.json
--prefix=pc12 --port=8761`, `--model=SF50 --jobs=…jobs_docs_sf50.json --prefix=viewer_sf50`, the dusk still with
`--t=2026-11-14T01:05:00Z`); captions in `docs/phase3/SOURCES.json` rewritten by the tool (model hashes 87731cce… /
49242e41…). Before / after sheets `out/pc12_look_it3/cmp/docs_pc12_{1..3}.jpg`, `docs_sf50_{1..5}.jpg`. Seen: dark,
cool tinted cabin windows and windshield on the sunlit side with the flight deck faint behind them (no milky panes), the
black surround and frames, the navy band a little lighter in sun and dark navy in shade, the gold pin-stripe, tyres and
blades darker; the SF50 unchanged apart from crisper dark glazing; the dusk still with whole strobe discs. The 11 reference
cameras (`final_world`, `final_studio`, `final_studio_glb`, PNG) and the review's poses (`final_pose`) were rendered for the
numbers above; side-by-sides with dev.html / the stage viewer / rc2 in `cmp/full_*.png`.

**App** (`RELAY=none PORT=8763 OUT=out/pc12_look_it3/livetest PREFIX=it3 node livetest.mjs jobs/views.mjs`, desktop): ready
in 6.0 s, 0 console errors / warnings, D1 type-only (27 masked), every view and sheet shot and looked at. Against the
review's run (`cmp/livetest_rc2_it3.jpg`; the replay instant differs by two minutes, so the traffic and the sun differ
slightly): overview / tower / Green Ramp / West Hangars / 28L final look the same; per view the median pixel change is 0
(−0.3 on the overview), the mean −0.3…−0.7 levels, the 1st percentile −5…−8 (fine dark details: building edges, shadows,
texture detail lose the veil). The review's PC-12 job (one parked track switched to PC12; `out/pc12_look_it3/app_pc12/`,
0 errors, `pc12.glb` served with sha256 87731cce…): port side in sun at 12 m, cabin panes **(88, 90, 90) → (43, 44, 47)**
at the same pixels next to white (237, 235, 231) unchanged (`cmp/app_fl_d12_windows.png`); starboard side in shade
(33, 41, 47) → (28, 36, 40).

**Tests**: `node tools/models/test_models.mjs` → **81 PASS, 13 KNOWN, 0 FAIL**, 4 INFO. New / changed checks: the cabin rule
(closed: `uCabinSun` = the type's glazingT, `uCabinAmb` 0.35; any door open: both 1; PC12 and SF50), the glazing veil without
the direct sun (PC12 and SF50), the bloom knee default, the aircraft-light pull. **`python3 -I -B tools/check_airport.py`**
→ **RESULT: ALL HARD CHECKS PASSED** (SOURCES coverage 165 files, 0 without an entry; D1 clean in every `docs/phase3_*.md`).

**Files changed in this iteration**: renderer / shared - `js/renderer.js` (`BLOOM_KNEE`, knee uniforms, header),
`js/shaders/post.js` (DOWN_FS knee, FINAL_FS gain, header), `js/scene.js` (iData.y pull flag, header),
`js/shaders/sprites.js` (pull of flagged sprites, header); aircraft runtime - `js/aircraft/detailed.js` (`uCabinSun`,
`cabinSunT`, `CABIN_SUN_T`, `uVeilSun` / `GLASS_VEIL_SUN`, sprite `pull`, comments), `js/aircraft/models.js` (`paintFit`
(0.035, 0.086, 0.181), PAINT_FIT header); `tools/models/test_models.mjs`; this file; `docs/phase3/*.jpg` + `SOURCES.json`.
Not changed: `js/gl.js`, the world shaders, `js/live/**`, `js/env/**`, `dev/**`, the glb files.

**Open / not verified (iteration 3)**: the shaded navy band stays darker than the reference (L* ~9 vs ~22) and the sunlit
band a little lighter: no single reflectance matches the world's sun / shade ratio (owner / pc12 owner: palette, or which
side to favour); the bloom knee K = 4 and the gain compensation are a renderer-wide look change (uniform areas unchanged,
dark details crisper; `post.bloomKnee: 0` restores sfo3d's bloom) - owner to confirm; the sunlit windshield is darker than
the reference (it mirrors the deep-blue upper sky, the reference its ceiling panels); under the pc12 viewer's own light the
glazing is now darker than the reference (by design, above); the cabin constants (τ on the direct sun, sky share 0.35, no
veil under the sun) and the 3 m sprite pull are inferred; tyres / blades in direct sun ~45–50 and the bright grazing lip of
glossy trim are physics of the outdoor scene; F5 / F6 unchanged (owner decisions); laptop-GPU frame time not measured
(SwiftShader only; the bloom knee adds one luminance weight per first-pass tap and one gain term per final-pass pixel, no
pass); a video-determinism comparison that spans this change (renderer files edited 08:45–09:55Z) will see the knee.

### 15.8 OD4 iteration 4 (recheck of 2026-11-14, findings G1–G4): dispositions
The recheck (its renders `out/pc12_look_rc3/`, gitignored: the state after iteration 3, commit 65de1d9) found the four
issues below. The first attempt at this iteration was stopped part-way by the account's usage limit (its edits are in the
WIP checkpoint 9672e31); the restart checked every WIP change, finished G3, and rendered and measured everything again.
**Before** = 65de1d9 (its runtime files served from copies, `out/pc12_look_it4/head/`, through the shot tool's
`--override`), **after** = this tree; PNG renders `out/pc12_look_it4/{before,after2}/`, side-by-sides `out/pc12_look_it4/cmp/`
(`sbs_<cam>.jpg`: dev.html | stage / world before | after / studio (palette=glb) before | after), measurements
`measure_final_{world,extra,studio,studio_extra}.json` (same-pixel sRGB medians, the classes and boxes of 15.7). Cameras:
the 11 reference cameras and the recheck's three close-ups (`ws_close`, `sidewin_close_port`, `winglet_close`), HWD Green
Ramp 2026-11-13 12:30 PST (sun az 191°, el 33.6°: starboard `hwd_*` cameras and the nose in sun, port cameras in shade) and
`look=studio`; the recheck's four light-leak cameras (`jobs_leak.json`) by day and at dusk (2026-11-14 01:05Z) for both
types, its SF50 dusk still, its gear-well poses, and two night airfield views (05:00Z, aircraft lights on / off). Every
image was looked at.

| # | finding | root cause | fix (file) | result (before → after) |
|---|---|---|---|---|
| G1 major | light sprites of a detailed aircraft show through the airframe (PC-12 belly beacon as a red disc on the wing root / fuselage side from any camera above the belly; under-wing landing lamp through the wing) | iteration 3's pull alone: a flagged sprite was depth-tested at its position pulled 3 m toward the camera, so no airframe less than 3 m in front of a lens could hide it | **lens-centre occlusion test**: `js/renderer.js` `copyDepth()` resolves the near pass's MSAA depth into a single-sample DEPTH_COMPONENT32F texture after the opaque near draws and before the blended ones, only in frames whose items set `needsDepth`; `js/scene.js` sets it on the sprite batch when it holds a flagged (aircraft) sprite and binds `uSceneDepth` / `uOcclude`; `js/shaders/sprites.js` `lensVisible()` scales a flagged sprite by the share of 3 × 3 depth taps over the lamp's footprint (spacing 0.7 × 0.04 m) whose scene depth lies behind the lens centre moved toward the camera by **0.09 m + 0.0008 m per metre** [inf] (the anchors sit inside their lamp bodies or under flush lenses: PC-12 lamp bodies reach 22–68 mm from their anchors along the sight lines measured, the SF50 anchors lie 1–16 mm under their lenses; per metre: about one pixel of a 45° surface at fov 40° / 1080 lines plus the depth resolution); a hidden lens hides the whole disc (zero-size quad), a half-hidden one draws it at reduced intensity, and the disc's fragments keep the pull, so the airframe beside a visible lens does not cut it. Unflagged sprites (airfield lights, placeholders) are not tested; airfield-only frames make no copy | PC-12, dusk, peak sRGB at the belly-beacon anchor (`out/pc12_look_it4/tools/sprite_check.py`): `leak_side_high` / `leak_follow` / `leak_front_high` **255 → 18 / 12 / 17** (hidden; a CPU replica of the test on the rest-pose mesh, `out/pc12_look_it4/tools/lens_taps.mjs`, gives 0 of 9 taps visible, 0.67–2.57 m of airframe in front of the lens, `out/pc12_look_it4/tools/light_los.mjs`), `leak_low_rear` 255 → 255 (seen from below, 6/9); right landing lamp under the wing at `leak_front_high` **255 → 29** (0/9, the wing 0.85 m in front); every other anchor within ±4 levels (top beacon, tail light, strobes; the top beacon is 4/9 at `leak_follow` and `leak_low_rear`, at the edge of the tail bullet, and is drawn there at reduced intensity, still saturated in its core). By day the same lights (`cmp/leak_day.jpg`): the red disc on the wing root is gone. SF50 dusk still (`cmp/sf50_dusk.jpg`): the tail-strobe disc is gone (peak at its anchor 255 → 33); **correction (recheck of iteration 4, finding F2; section 15.9): the two tip-strobe discs were NOT gone** (255 → 255 at strobeL and at strobeR; this row first said they were, from the CPU centre ray - 0.21 / 0.91 m of tip in front of the anchors - not from the image; the strobes flash in that frame) — they are hidden since iteration 5; landing / position lights and the nose lamp unchanged; the SF50 at the four leak cameras: nothing leaked before, anchors within ±14 levels (dim position lights). Airfield lights unchanged: night views with the aircraft lights off, 136 / 429 pixels change by more than 2 levels (max 8), all on the aircraft's glazing; with them on, changes only inside the aircraft's box: the belly beacon hidden from above (`ab_night_wide`), the top beacon hidden behind the T-tail's stabilizer from the low camera (`ab_night_low`, 0/9, stabilizer 2.59 m in front; `cmp/night_ab_crop.jpg`) |
| G2 minor | `ACOBJ_FS` applied the cabin light (sky 0.35, sun × τ) to every back face, e.g. the main-gear well | `bool cabin = mat == 23 \|\| mat == 22 \|\| back` | `js/aircraft/models.js` `AC_PART_CABIN` (PC-12 `fus_fwd`, `fus_center`, `fus_aft`, `door_airstair`, `door_cargo`, `exit_hatch`, `door_frames`, `glazing_cabin`, `glazing_flightdeck`; SF50 `fuselage`, `windshield`, `cabin_windows`, `door_upper`, `door_lower`, `door_baggage`): their opaque plain / paint materials take id **25** (same glTF material); `ACOBJ_FS`: `cabin = mat == 23 \|\| (back && mat == 25)`; `js/aircraft/glb.js` passes the material record to `partMatId` so blended materials keep their ids | gear-well walls through the opening, gear half way from below (`pose_gearhalf_under`): (84, 95, 88) → **(105, 108, 93)**, zinc-chromate wall (108, 107, 56) → (109, 110, 64) (`cmp/well_crop.jpg`); the black disc in the retracted well is the tyre (pc12: protrudes ~1 in when retracted). Cabin side unchanged: door / cabin windows at the cockpit camera (20, 28, 36) / (24, 32, 39) before and after. Loader check (the proposed tests below): 29 (PC-12) / 18 (SF50) part-material pairs take 25, all on cabin-enclosing parts; none on `gear_bays`, wings, belly fairing, `nose_bay` |
| G3 minor | flight-deck glazing darker than both references: a near-black navy visor in sun, the flight deck behind the side window darker in shade, seats unlit | (a) the flight deck took the cabin's light (sky × 0.35, sun × τ 0.196) although the windshield and the side windows wrap around it and are most of what it sees (PC-12: ~1.3 m² of glazing around a ~1.1 × 1.2 × 1.4 m flight deck; the cabin ~2.1 m² of windows for 5.16 × 1.52 × 1.47 m); (b) since iteration 3 no pane took the direct sun in its diffuse return (`GLASS_VEIL_SUN` 0), while the reference viewer lights every glb BLEND pane like any surface (0.82 coverage of the tint) | (a) `models.js` `AC_PART_DECK`: the flight deck's plain / interior materials take id **26** (displays keep 22), lit by `uDeckAmb` / `uDeckSun` = `DECK_SKY_SHARE` 1 / `DECK_SUN_T` 1 [inf] (the sky unoccluded, the sun where the shadow map lets it in — as the pc12 viewer lights it; 1 with a door open as before); (b) `models.js` `AC_PART_DECK_GLASS`: the flight-deck glazing (PC-12 `glazing_flightdeck`: windshield and crew side windows; SF50 `windshield`) takes id **27**, whose diffuse return takes the sun at `GLASS_VEIL_SUN_DECK` = **0.8** [inf: appearance fit] (`GLASS_FS` `uVeilSunDeck`); the cabin windows (24) keep 0 (iteration 3: with a veil they read above the references, hwd_side veil 0.25 (44, 48, 52) vs (35, 42, 49) / (24, 29, 34)). 0.8 minimises the mean distance outside the dev–stage range over the 11 windshield / side-window boxes of the six glazing cameras (renders at 0, 0.5 and 1, interpolated in linear light; `g3/m_V_*.json`): 15.5 sRGB levels at 0 (deck rule only), 7.4 at 0.5, **5.3 at 0.8**, 5.7 at 1 | world, flight-deck boxes (dev / stage reference): **sun** — hwd_front34 windshield (21, 24, 31) → **(57, 61, 63)** ((57, 65, 73) / (48, 55, 62)); hwd_nose side window (20, 24, 32) → (60, 63, 66) ((51, 60, 67) / (38, 44, 50)), windshield (30, 36, 42) → (46, 54, 63) ((59, 68, 69) / (53, 62, 69)); ws_close side window (15, 20, 29) → (59, 62, 65) ((49, 56, 63) / (37, 43, 49)), windshield (11, 16, 25) → (39, 47, 53) ((43, 53, 60) / (41, 51, 59)); nose windshield L (19, 25, 35) → (50, 55, 61) ((45, 56, 62) / (42, 52, 60)), R (20, 22, 29) → (38, 43, 49) ((53, 61, 65) / (55, 64, 70)); cockpit windshield (29, 30, 31) → (39, 46, 54) ((39, 48, 55) / (44, 54, 62)). **Shade** — cockpit side window (12, 20, 29) → (18, 25, 34) ((23, 27, 31) / (38, 44, 50)); sidewin_close_port side window (19, 23, 26) → (20, 23, 29), wrap-around windshield (30, 31, 31) → (39, 42, 47) ((43, 48, 53) / (45, 53, 60)). The seats are visible through every flight-deck pane in sun and in shade (`cmp/sbs_cockpit.jpg`, `sbs_hwd_nose.jpg`, `sbs_nose.jpg`, `cmp/g4_sidewin_close_port_crop.jpg`). The shaded side window stays below dev in absolute terms by the world's shade level (owner-taste F5 / F6, unchanged): relative to the white paint beside it, 23 / 130 = 0.18 at sidewin_close_port, as dev's 35 / 195. Under `look=studio`: hwd_front34 windshield (29, 34, 39) → (45, 51, 57), nose L / R (22, 29, 34) / (27, 31, 35) → (38, 46, 52) / (37, 44, 49), ws_close side window (25, 30, 35) → (43, 49, 55); the cockpit windshield (40, 46, 52) → (52, 62, 69) and sidewin_close_port (33, 38, 42) → (48, 55, 61) now above the references there (the studio is a comparison aid; the world is the product) |
| G4 minor | dotted hatch / moiré on the wrap-around windshield at grazing angles, also under `look=studio` | the glass was ONE blended pass with culling off: its triangles blended in index order, so where the view crosses the glazing twice (the near pane of the wrap-around windshield over the inside of the far one, thin slivers at that angle) near and far triangles alternated strip by strip. Ruled out on the way (`out/pc12_look_it4/crops/g4_variants.png`, `g4_d12.png`): a flat constant colour shows no hatch (coverage / depth fine; the order of equal layers is invisible), the face normal from derivatives keeps it (not normal interpolation / quantization), no alpha-to-coverage anywhere in the renderer | each glass group is drawn as **two items**, back faces first (render-item field `cullFront`, `js/renderer.js` `drawItems`), then front faces (back faces culled), as three.js r160 draws a transparent double-sided material; and the glazing / opaque roughness as three.js sets it (max(r, 0.0525) + the geometric roughness of the interpolated normal, at most 1; was the glb's 0.02–0.03) | hatch gone in the world and under `look=studio` (`cmp/g4_sidewin_close_port_crop.jpg`, `sbs_sidewin_close_port.jpg`, `sbs_ws_close.jpg`). Side effect, as in the reference: where two panes overlap the near one now covers the far one (shaded side window at sidewin_close_port (27, 28, 29) in the one-pass WIP render → (20, 23, 29)) |

**Docs stills** re-rendered (every image looked at; captions in `docs/phase3/SOURCES.json` rewritten by the tool): the nine
PC-12 stills `docs/phase3/pc12_{front34, side, rear34, chase, cockpit, port, rear, flaps40, gear_closeup}.jpg` and the 13
`viewer_sf50_*.jpg` (`node dev/model_shot.mjs --jobs=out/pc12_look_it4/jobs_docs_pc12.json --prefix=pc12 --port=8761`,
`--model=SF50 --jobs=out/pc12_look_it4/jobs_docs_sf50.json --prefix=viewer_sf50 --port=8762`, the dusk still with
`--jobs=out/pc12_look_it4/jobs_sf50_dusk.json --t=2026-11-14T01:05:00Z`; its caption then said that the strobe lenses are
hidden from that side - untrue for the two tip strobes, see the correction in G1; caption and still redone in 15.9). Before / after sheets `out/pc12_look_it4/cmp/docs_*.jpg`.

**Tests**: `node tools/models/test_models.mjs` (unchanged: `tools/models/` is not in this iteration's file list) → **81
PASS, 13 KNOWN, 0 FAIL**, 4 INFO (`out/pc12_look_it4/test_models_final.txt`); `GLASS_FS` keeps the iteration-3 expression
the veil check reads (`bool glz = … == 24`, `glz ? uVeilSun : 1.0`), with the flight-deck case in front of it (`dglz ?
uVeilSunDeck : glz ? uVeilSun : 1.0`). **Proposed checks** for the test file's owner, `out/pc12_look_it4/test_models_it4_checks.patch`
(gitignored; `git apply --check` clean; with it **88 PASS, 13 KNOWN, 0 FAIL**, `test_models_it4_checks_run.txt`): (G1,
runtime) a Scene with only airfield lights asks for no depth copy, one with a detailed aircraft's light does, `uOcclude` 0 / 1
without / with the copy, the copy sits between the opaque and the blended near draws, the depth blit and the shader's test
and constants; (G2, per type) every part-material pair with id 25 lies on a cabin-enclosing part, none on the gear wells /
wings / belly fairing / nose bay, and the shader's back-face rule; (G3, per type) the flight deck's materials take 26
(displays 22), the flight-deck glazing 27 and the cabin windows 24, the deck uniforms closed / with a door open,
`uVeilSunDeck` on every glass draw, the glazing expression; (G4, per type) every glass group drawn as two items, back faces
first, and the renderer's `cullFront` handling. **`python3 -I -B tools/check_airport.py`** → **RESULT: ALL HARD CHECKS
PASSED** (SOURCES coverage 165 files, 0 without an entry; D1 clean in every `docs/phase3_*.md`;
`out/pc12_look_it4/check_airport_final.txt`). The final `GLASS_FS` was re-rendered at two cameras: pixel-identical to the
`after2` renders, no console errors.

**Files changed in this iteration**: renderer / shared — `js/renderer.js` (`copyDepth`, `sceneDepth` / `noDepth`,
`cullFront`, header), `js/scene.js` (`needsDepth`, `uSceneDepth` / `uOcclude`, header), `js/shaders/sprites.js`
(`lensVisible`, header); aircraft runtime — `js/aircraft/detailed.js` (ids 25 / 26 / 27 in `ACOBJ_FS` / `GLASS_FS`,
`DECK_SKY_SHARE`, `DECK_SUN_T`, `GLASS_VEIL_SUN_DECK`, three.js roughness, two-pass glass, comments), `js/aircraft/models.js`
(`AC_PART_CABIN`, `AC_PART_DECK`, `AC_PART_DECK_GLASS`, `AC_PART_MAT`), `js/aircraft/glb.js` (`partMatId` gets the material
record); this file (sections 8, 9 and 15.8); `docs/phase3/*.jpg` (22 stills) + `SOURCES.json`. Not changed: `js/gl.js`,
the world shaders, `js/live/**`, `js/env/**`, `dev/**`, `tools/**`, the glb files.

**Open / not verified (iteration 4)**: the lens allowance (0.09 m + 0.0008 m per metre), the tap layout and the lamp radius
are inferred; a lens at the edge of an occluder (the PC-12 top beacon behind the tail bullet from behind / below, 4 of 9
taps) is drawn at reduced intensity with a saturated core — a judgement of "partly visible", not a hard cut. The flight-deck
glazing's sun veil (0.8) is an appearance fit to the reference viewer, not physics; after it the nose camera's starboard
windshield pane stays ~15 levels below both references, the sunlit side windows at hwd_nose / ws_close read 3–10 levels
above dev, and under `look=studio` the cockpit windshield and the shaded close-up side window now read above the references.
The flight deck takes the full sky under its roof (`DECK_SKY_SHARE` 1, as the reference viewer lights it) [inf]. The SF50
follows the same rules (its panel and windshield; no SF50 reference viewer to compare with). The app (`livetest.mjs`) was
not re-run in this iteration (`js/live/**` is being changed by a parallel workflow); it draws the same items, so the hidden
lights and the lighter flight-deck glazing apply there too, and a video-determinism comparison spanning this change will
see them. Cost (SwiftShader only, laptop GPU not measured): one depth blit per frame while a detailed aircraft shows a
light, nine depth fetches per sprite vertex of a flagged sprite, and two glass draws per glass group instead of one.
Owner-taste items F2 (navy in shade), F5 / F6 (shaded / sunlit white) and the bloom knee at night are unchanged.

### 15.9 OD4 iteration 5 (recheck of 2026-11-20, findings F1–F4): dispositions
The recheck of iteration 4 (its renders and tools `out/od4f_rc/`, gitignored) found the four issues below. **Before** = the
state it rendered (iteration 4; its renders are pixel-identical to `out/pc12_look_it4/after2`), **after** = this tree.
Renders, measurements and tools of this iteration: `out/od4_it5/` (gitignored). CPU work uses the recheck's BVH over the
rest-pose mesh (`out/od4f_rc/tools/bvh.mjs`) and a replica of the shader with a pixel camera (`out/od4_it5/tools/lens_sim.mjs`:
the depth of a pixel = the first opaque hit through it, rounded to a float32 window depth). Its ground truth is the share of
the lamp's **projected** area that ray casting sees: G × G rays over the lamp's footprint, a ray in the footprint when it
meets the lamp's own triangles (its lamp material and the clear lens over it), seen when the first opaque hit is that lamp
surface within 5 mm (the recheck's tolerance; it makes the PC-12 tail lamp, sunk 1–5 mm into the bullet tip, visible from
behind as on the real aircraft). GPU work uses the dev viewer (`out/od4_it5/tools/gpu_lights2.mjs`, the recheck's tool plus
an isolated mode: one light at a time, on / off renders, peak added sRGB within 3 pixels of the anchor). Every image was looked at.

| # | finding | root cause | fix (file) | result (before → after) |
|---|---|---|---|---|
| F1 major | a hidden lamp is drawn as a full, saturated disc when its centre lies within ~2.8 cm of an occluder's silhouette (SF50 tip strobes from the dusk camera; PC-12 top beacon behind the stabilizer, belly beacon behind the belly fairing, right strobe behind the wing; 7–10 % of 600 directions per light) | iteration 4 counted a tap visible when the scene depth lay behind the lens centre moved 9 cm toward the camera: a tap past the silhouette onto the background, or onto the skin beside the lamp within the 9 cm, was "visible", and one tap of nine drew the disc | **the lens test by the lamp's own shape** (`js/shaders/sprites.js` `lensVisible`). `js/aircraft/glb.js` `lampShape` fits each light's lamp at load: the vertices of the opaque lamp material connected to the anchor (+ the clear lens cover over it, SF50), principal axes, an ellipsoid through the farthest vertex when smaller than the box (pc12's lamps are superellipsoids, e = 0.9) else the box (SF50 lamp patches), + 2 mm; no opaque lamp → `geom` false (pc12's clear nose-strut lens; the registry landing lights: a 2 cm sphere); a one-sided patch (|mean normal| > 0.5: SF50 tip lamps and strobes) gets its facing cone. `js/aircraft/detailed.js` `lightSprites` places it with the anchor's mover (`lampWorld`), `js/scene.js` packs it (32 floats, `js/gl.js` 8 instance vec4s). Per tap (3 × 3 over ±0.55 of the shape's projected half extents) the ray camera → tap point is cut by the shape → [t0, t1], the depth at the tap's pixel → ts along the ray: ts < t0 − E counts against (an occluder), t0 − E ≤ ts ≤ t1 + E is seen (the first surface lies in the lamp's own volume), ts > t1 + E (beside the lamp, or past a silhouette onto the background) is not counted for a lamp in the depth and is seen for a virtual one; visibility = seen / counted (1 when nothing counts: a lamp too small for the depth buffer, or off screen); a one-sided lamp seen from where none of it faces the camera is hidden. Constants [inf: chosen with the CPU replica, grid over tap 0.45 / 0.55 / 0.65, E0 2 / 4 / 6 mm, K 0.25–1 pixel footprints, both types, pixel centre and MSAA-sample-0 depth positions, `out/od4_it5/cpu/grid_*.json`]: LENS_TAP 0.55, E = 2 mm + 0.5 × the pixel footprint + three float32 depth steps | **CPU, 600 directions × 10 / 40 m per light, fov 30° / 720 lines** (`out/od4_it5/cpu/sweep_final.txt`; leak = drawn with 0 % of the lamp seen; over = drawn at ≥ 5/9 with ≤ 9 % seen; false hide = not drawn with ≥ 25 % seen): PC-12 leaks **144 → 4** (tail 3 at 10 m, its lamp flush in the bullet tip; the right landing light 1 at 40 m), over **82 → 0**, false hides 0 → 13 (all at 40 m, 3 cm pixels: tail 10 from ahead / the side, where its photometric output is small, strobes 3), mean |error| per light 0.01–0.42 → 0.002–0.25; SF50 leaks **1124 → 282**, over **1307 → 22**, false hides 0 → 22 of ~5,700 (the residual leaks are 1–3 of 9 taps at grazing views, where the skin around a flush lens lies inside the lamp's volume). **GPU, the recheck's 29 PC-12 cameras at night, one light at a time** (`out/od4_it5/gpu_pc12_iso`, uniform sprites): every hidden named light 0, except `navR_thin0` 254 (5 % of the lamp seen, 1 of 9 taps, as the CPU replica) and `tail_edge0` 254 (1 of 8 taps meets the flush tail lamp at the depth sample; CPU replica 0 of 8; with the real lights this tail position light, seen from ahead, peaks at 24); the controls drawn (`ctl_beaconBot_below`, `ctl_beaconTop_above`, `ctl_navL_front` 255), `ctl_strobeR_out` 0 (7 % seen); visible lights at those cameras (25–68 % seen) drawn at 7 of 8 (`gpu_pc12_iso2`; the top beacon at `strobeL_thin0`, 25 % seen at the stabilizer edge, is not). **Real lights at night**, the recheck's cases (`gpu_pc12_real2`): `beaconTop_edge1` 255 → **0**, `beaconBot_edge0` / `edge1` 254 / 253 → **0 / 5**, `strobeR_edge0` 255 → **0**, `strobeR_edge1` 255 → 196 = the glow of the right position light beside it (15 % seen; the strobe alone 0). **SF50 dusk camera, 1920 × 1080, strobes only** (the recheck's job): strobeL 254 → **0**, strobeR 251 → **0**, strobeTail 0 → 0, with the three strobe sprites emitted (flash on). Airfield lights unchanged (night views, aircraft lights off: ≤ 22 pixels change, max 6 levels, on the aircraft's glazing); with them on, changes only inside the aircraft's box (`out/od4_it5/night/`). The app (`livetest`-style smoke run, replay at night, `out/od4_it5/app/`): no console errors, overview within 0.003 levels mean of the recheck's |
| F2 minor | the dusk still's caption and 15.8 said both tip-strobe discs were gone; the image showed them; the sprites.js header's "nearest real occluder 116–122 mm" held only on the sight lines measured | 15.8 was written from the CPU centre ray, not from the image | the still re-rendered after F1; the caption (`docs/phase3/SOURCES.json`, from `out/od4_it5/jobs_sf50_dusk.json`) and the G1 row of 15.8 rewritten from per-anchor measurements; the shader header no longer has the 116–122 mm claim (the allowance it justified is gone: the occluders in front of the PC-12 nav / strobe lamps are 46–98 mm from the anchors, so a fixed allowance cannot separate them) | `docs/phase3/viewer_sf50_lights_dusk.jpg` at the strobe anchors (`out/od4_it5/docs_dusk/anchor_peaks.json`): before 255 / 255 / 33 (strobeL / strobeR / strobeTail) → **35 / 31 / 30** (the dusk background); the same frame without the strobes: the strobes add **0** at each anchor; with the lens test switched off they add **255** at each (they flash in that frame); the right-wing landing / position light disc (fully seen) stays; the left landing light is drawn at half (50 % of its lamp seen, beam away). Marked crops `out/od4_it5/docs_cmp/sf50_dusk_marked.jpg` |
| F3 minor | the fixed 9 cm allowance was thicker than the winglet / tip skin in front of the PC-12 nav and strobe lamps and the SF50 strobes; the per-metre term let a light show through the fuselage at range with a narrow field of view (belly beacon at 900 m, fov 10°: 250) | allowance per metre, not per pixel, and not tied to the lamp | the allowance is gone: E = 2 mm + 0.5 × the pixel footprint + the depth step, measured against the lamp's own shape (F1); `dev/model.js` near plane beyond 75 m as the app's rig (d × 0.004 ≤ 5 m) - with 0.3 m the float32 depth step at 900–1500 m (0.16–0.45 m) is coarser than the fuselage, and the new per-pixel test then read 59 / 157 at 900 / 1500 m, fov 40° | thin skin, real lights at night: `navL_thin0` / `thin1` 255 / 255 → **6 / 0**, `strobeL_thin0` / `thin1` 255 / 255 → **1 / 0**, `strobeR_thin0` / `thin1` 255 / 255 → **0 / 0** (1–9 % of the lamps seen); CPU sweep "over" (≥ 5/9 drawn, ≤ 9 % seen) PC-12 82 → 0. Range, belly beacon, the recheck's direction (`out/od4_it5/gpu_far`): fov 40° at 500 / 900 / 1500 m **0 / 0 / 0**, 900 m fov 10° 250 → **0**; controls visible at range (`gpu_farctl`): belly beacon from below 900 m fov 10° / 40° 249 / 199, left position light 1500 m fov 40° 129 (sub-pixel, energy kept) and 900 m fov 10° 250, top beacon 900 m fov 10° 234, right strobe 900 m fov 10° 240 |
| F4 minor | flight-deck glazing: the shaded side window below the references (0.7 × dev relative to the shaded white), the sunlit side windows above with a neutral grey, seats milky; SF50 crew seats dark behind the deck-lit panel | (a) the PC-12 has no bulkhead behind the crew seats: what the side windows show behind the seats is the forward-cabin skin, a back face of the cabin-enclosing parts (id 25), lit with the cabin's shares (sky 0.35, sun × τ; debug render `out/od4_it5/dbg/ids_port.png`); (b) the SF50's crew seats are the front row of `cabin_seats` (id 23); (c) the flight-deck veil (0.8) was fitted before the deck's walls were lit | (a, b) `js/aircraft/models.js` `deck: { xAft }` per type [inf: PC-12 2.00 = the aft end of the `flight_deck` part, the crew seat backs; SF50 1.40 = between its front (x 1.5–2.33) and second (≤ 1.0) seat rows]; `js/aircraft/detailed.js` passes the plane (`uDeckPlane`) and `ACOBJ_FS` gives every cabin-rule surface (id 23, back faces of id 25) the deck's shares forward of it, fading into the cabin's over `DECK_RAMP` 1 m aft of it [inf]; (c) `GLASS_VEIL_SUN_DECK` 0.8 → **0.65**, refitted over 26 boxes at 12 cameras (renders at 0.4 / 0.8 interpolated in linear light: 0.4 6.7, 0.6 5.6, 0.7 5.6, 0.8 5.9, 1.0 7.1 levels) | world, same-pixel medians (`out/od4_it5/tools/g4_measure.py`: the recheck's eight grazing / close cameras - boxes masked to glass, its references `out/od4f_rc/ref_shots` - and the 15.8 boxes): mean distance outside the dev–stage range **6.1 → 4.9** (13 boxes, grazing cameras), **6.9 → 6.1** (13 boxes of 15.8 + the cockpit camera's cabin windows). Shade: g4_port_graze side window (20, 26, 34) → (22, 27, 35), wall behind the seats (25, 32, 39) → (29, 36, 44) ((45, 48, 49) / (56, 60, 64)); relative to the shaded white paint beside it (linear) 0.047 → **0.050** (dev 0.058, stage 0.065); sidewin_close_port (18, 23, 29) → (22, 26, 32), relative 0.036 → **0.044** (0.051 / 0.062); cockpit door window (20, 28, 36) → (26, 33, 41). Sun: g4_stbd_graze side window (56, 60, 63) → (54, 57, 61) and seat (58, 61, 64) → (53, 56, 59) (dev (48, 56, 64), stage (37, 43, 49): in range), ws_close side window (58, 61, 64) → (54, 57, 60), hwd_nose (60, 63, 66) → (56, 59, 62), hwd_nose windshield (49, 56, 66) → (55, 61, 68). Worse: g4_top_graze right pane (32, 39, 45) → (28, 35, 42) and the nose camera's right pane (38, 43, 49) → (36, 40, 46): the copilot seat there lies in the roof's shadow; the reference viewer draws no shadows (`out/pc12_ref_viewer/viewer_settings.md`), so its seat is sunlit under the roof. Low sun (16:05 PST): the interior visible, the far wall warm where the sun reaches it (`out/od4_it5/f4/sheet_lowsun.jpg`). SF50: the crew seats lit behind the windshield in sun and shade (`out/od4_it5/f4/sheet_sf50.jpg`). Sheets `out/od4_it5/f4/sheet_f4.jpg`, `sbs_w2_*.jpg` |

**Docs stills** re-rendered (every image looked at; captions in `docs/phase3/SOURCES.json` rewritten by the tool): the nine
PC-12 stills and the 13 `viewer_sf50_*.jpg` (`node dev/model_shot.mjs --jobs=out/pc12_look_it4/jobs_docs_pc12.json --prefix=pc12`,
`--model=SF50 --jobs=out/pc12_look_it4/jobs_docs_sf50.json --prefix=viewer_sf50`, the dusk still with
`--jobs=out/od4_it5/jobs_sf50_dusk.json --t=2026-11-14T01:05:00Z`). Changes: the flight-deck glazing (PC-12 cockpit /
front34 / gear close-up, SF50 front / front34 / fade: the crew seats now lit), the dusk still's strobe discs; the other
stills within a few hundred pixels. Before / after sheets `out/od4_it5/docs_cmp/docs_sheet{1,2,3}.jpg`.

**Tests**: `node tools/models/test_models.mjs` (unchanged; `tools/models/` is not in this iteration's file list) → **81
PASS, 13 KNOWN, 0 FAIL**, 4 INFO (`out/od4_it5/test_models_final.txt`). **Proposed checks** for the test file's owner,
`out/od4_it5/test_models_it5_checks.patch` (gitignored; `git apply --check` clean against the current file): iteration 4's
patch (`out/pc12_look_it4/test_models_it4_checks.patch`, whose G1 constant check no longer matches the shader) with its G1
check updated to the new test, plus: every drawn light has its lamp shape (both types; PC-12 opaque lamps ellipsoids, the
SF50 strobes one-sided), the deck region in the registry, the 32-float sprite layout, the tap classes and the per-pixel
tolerance, the deck-share ramp → **95 PASS, 13 KNOWN, 0 FAIL** (`out/od4_it5/test_models_it5_checks_run.txt`).
**`python3 -I -B tools/check_airport.py`** → **RESULT: ALL HARD CHECKS PASSED** (`out/od4_it5/check_airport_final.txt`).

**Files changed in this iteration**: renderer / shared — `js/gl.js` (`setInstances` nVec4, header), `js/scene.js`
(`SPRITE_F` 32, lamp-shape packing, header), `js/shaders/sprites.js` (`lensVisible`, `lampHit`, iL0–iL3, header); aircraft
runtime — `js/aircraft/glb.js` (`lampShape`, `jacobi3`, `lights[k].occ`), `js/aircraft/detailed.js` (`lampWorld`, sprite
`occ`, `uDeckPlane` / `DECK_RAMP` in `ACOBJ_FS`, `GLASS_VEIL_SUN_DECK` 0.65), `js/aircraft/models.js` (`deck` per type,
`m.deck`); `dev/model.js` (near plane); this file (sections 8, 9, 15.8 corrections, 15.9); `docs/phase3/*.jpg` (22 stills)
+ `SOURCES.json`. Not changed: `js/renderer.js`, the world shaders, `js/live/**`, `js/env/**`, `tools/**`, the glb files.

**Open / not verified (iteration 5)**: the lamp shapes are fitted from the geometry, the tap layout, E and the deck
region / ramp are inferred; a surface inside a lamp's shape counts as the lamp (the skin around a flush SF50 lens at grazing
views: the residual SF50 leaks above, 1–3 of 9 taps); at 40 m (3 cm pixels) a lamp only partly seen at a silhouette can be
hidden (13 PC-12 directions of ~3,000) and the depth sample's position inside a pixel decides single taps (the GPU-only
`tail_edge0` case); the shaded side window stays at 0.86 × dev relative to the shaded white (the rest is the world's darker
shade and the reference's studio reflections, owner-taste F5 / F6); the right windshield panes stay below both references
where the reference viewer, having no shadows, lights the shaded copilot seat. Cost: nine depth fetches and nine ray-shape
cuts per vertex of a flagged sprite, 32 floats per sprite. A video-determinism comparison spanning this change will see the
hidden lights and the lighter flight deck.

### 15.10 OD4 iteration 6 (recheck of 2026-11-21, findings R1–R5): dispositions
The recheck of iteration 5 (its renders and tools `out/od4f_rc2/`, gitignored) found the five issues below. **Before** = the
state it checked (iteration 5 = the runtime files of commit 9085b5d; GPU "before" runs serve copies of them,
`out/od4_it6/head/`, through the tools' `--override`), **after** = this tree. Renders, measurements and tools of this
iteration: `out/od4_it6/` (gitignored). **CPU** (`out/od4_it6/tools/lens6.mjs`, `sweep6.mjs`): the iteration-5 shader
(`it5Test` = `out/od4_it5/tools/lens_sim.mjs` newTest, unchanged), iteration 4 (`oldTest`) and a replica of the new shader
(`it6Test`) on the rest-pose mesh with a pixel camera (float32 window depth, pixel-centre samples, the app rig's near plane
d × 0.004 m in 0.2–5 m); the ground truth as in 15.9 (`truthShare`: the seen share of the lamp's projected area from the
eye, 11 × 11 rays, 5 mm tolerance; glass counts as transparent). **Full sphere** (no eye-height filter): 300 Fibonacci
directions per light, **16 sub-pixel camera positions** per direction (the camera shifted by ((i + ½) / 4, (j + ½) / 4)
pixel, eye and target together, so the lamp falls at 16 places inside its pixel), **5 / 10 / 40 / 80 / 150 / 300 / 400 m**
(20 m as well for the near-range rules), fov 45° / 1080 lines (the app's follow camera; 30° / 1080 and 55° / 720 at
40–300 m as well: the videos' 30–55° and a laptop canvas). **GPU**: the dev viewer at 1920 × 1080 with a new
`HWDM.lensProbe()` (`dev/model.js`) that reads back the shader's visibility of every light sprite of the frame (the same
`lensVisible` code, depth copy, table atlas and camera; one white omni sprite per anchor, always on), plus the recheck's
on / off renders for the peak sRGB at an anchor. The CPU replica and the GPU agree exactly at the same cameras: the 912
light values of the spot checks below (mean |GPU − CPU| 0.0000, none off by more than 0.1), every frame of both roll
sequences (max |GPU − CPU| 0.000 per light), and, at 5–20 m where the depth taps decide, closely (mean |GPU − CPU| 0.002 over 320 PC-12 and 0.022 over 288 SF50 values of the near-range check below: single taps of nine read on the other side of an edge, the GPU's depth sample lying elsewhere in its pixel than the CPU's pixel centre). Every image was looked at.

**Why the depth buffer alone cannot do it (R1 / R2).** Beyond ~60 m a lamp (PC-12 2–8 cm, SF50 1–13 cm half extents) is
smaller than a pixel (6 cm at 80 m, 11.5 cm at 150 m, 23 cm at 300 m, fov 45° / 1080 lines), and the depth copy holds one
sample per pixel, taken up to half a pixel from the lamp. A lamp at its own body's silhouette (the PC-12 belly beacon from
just below the horizon: the belly beside it lies 0.3 m in front of it at a grazing angle, the next row is sky) and a lamp
just inside an occluder's silhouette (a nav lamp under 5–10 cm of winglet skin, the tip's edge 3 cm away) leave the same
pattern of samples; whatever a rule decides, it decides from which texel the lamp happens to fall in, so the answer changes
with the sub-pixel position and a light on a moving aircraft blinks. Candidates tried on the CPU before choosing
(`out/od4_it6/cpu/sw_{a,b,c}_*.json`): taps spread over at least half a pixel, a background / behind-the-lamp tap counted as
seen below 1–2 pixels (the iteration-4 rule blended in by the projected radius), a slope-scaled allowance from the local
depth gradient, with and without extrapolating the occluder's plane to the lamp - all of them stop the blinking of visible
lamps (0 % of positions) but draw hidden lamps near a silhouette at 68–94 % of the positions at 150 m (navL, strobeR: the
skin over the lamp is within a pixel of its edge, so one sample per pixel cannot tell on which side of that edge the lamp
is), i.e. R2 gets worse. The occluder of a lamp at range is (almost always) the aircraft itself, whose geometry is known: so
its visibility is now tabulated per lamp and view direction, and the depth buffer is asked only about other occluders.

| # | finding | root cause | fix (file) | result (before → after) |
|---|---|---|---|---|
| R1 major | beyond ~60 m a sub-pixel lamp the ray cast sees is hidden at 3–13 % of sub-pixel positions: it blinks on a moving aircraft (PC-12 belly beacon, strobes; GPU: bot150a / b, strR150, bot80c, strR80) | iteration 5 dropped taps that pass the lamp onto the background; a sub-pixel lamp's taps all read the one or two texels beside it (above) | **self-visibility tables** (`js/aircraft/glb.js` `lampTables`, `lampVisLookup`, `lampVisFar`, `LAMPVIS`): for every drawn light, once per model, the seen share of the lamp's projected area by view direction - the ground truth's own definition, by ray casting the model at rest (a compact BVH over the opaque triangles; per direction 4 × 4 parallel rays over the bounding rectangle of the lamp's projection, 12 × 12 for a lamp seen nearly edge-on; a ray meets the lamp's own triangles - its lamp material + the clear cover - or the shape of a lamp with no geometry; it sees the lamp when nothing opaque lies more than 5 mm in front of the lamp's surface and something lies at or behind it) on a **128 × 64 lat-long grid (2.8°) in the lamp shape's frame**, RGBA8: seen share gear down (the model at rest), gear up (without the gear legs, wheels, braces and gear doors), and the distance to the farthest occluder of the direction (below); 32 KB per lamp. `js/aircraft/models.js` `loadModel` computes them before handing the model out (time-sliced: a MessageChannel turn every 25 ms, so the page keeps running and a page in the background is not slowed by timer throttling; a still or a video sees the same test from its first frame). `js/aircraft/detailed.js` `lampWorld` passes the table, the gear-up share (kinematics `gearSequence` leg) and the aircraft's bounding sphere (rest bbox + 0.5 m); `js/scene.js` keeps the tables in one RGBA8 atlas (`uLampVis`) and packs 40 floats per sprite (iL4 bounding sphere, iL5 band / gear-up share); `js/shaders/sprites.js` `lensVisible`: **v = mix(max(v5 × g, T × g × vExt × n), T × g × vExt, w)**, w = q × (1 − smoothstep(1.5, 3, r)) with r = the smaller projected half extent of the lamp's ellipsoid in pixels, T = the table (bilinear) toward the camera, g = mix(1, smoothstep(0.04, 0.2, T), q), n = smoothstep(0.25, 0.5, T) × q, q = the near-camera guard (below), v5 = the iteration-5 test (a resolved lamp: it also sees flaps, gear and doors as posed, and other aircraft and buildings), vExt = the share of 3 × 3 taps (over the lamp, at least half a pixel apart) whose depth lies **in front of the aircraft's bounding sphere** (the occluders that are not the aircraft). Below 1.5 pixels the answer depends on the view direction only, not on the pixel grid | **CPU, all lights, full sphere, fov 45° / 1080 lines** (tables below): positions that hide a lamp seen ≥ 50 % at 80 / 150 / 300 / 400 m: PC-12 **1.90 / 3.98 / 4.96 / 6.19 % → 0 / 0 / 0 / 0**, SF50 **0.40 / 1.02 / 1.21 / 1.05 % → 0**; directions where such a lamp blinks: PC-12 **121 / 220 / 296 / 350 → 0**, SF50 **28 / 92 / 91 / 83 → 0** (belly beacon 42 / 71 / 62 / 69 → 0); false hides (≥ 25 % seen, drawn 0 somewhere) PC-12 285 / 377 / 449 / 493 → **0**, SF50 63 / 147 / 174 / 179 → **0**; at fov 30° / 1080 and 55° / 720 (40–300 m, `cpu/sw_h_*`) 0 hidden positions and 0 blinking directions for both types. **GPU, the recheck's range jobs** (`gpu/range_new/`, real lights, HWD world at night, one light at a time, four sub-pixel positions each): bot150a, bot150b and bot80c **0 / 255 / 255 / 255 → 255 × 4**, strR150 **0 / 0 / 255 / 255 → 255 × 4**, strR80 255 / 0 / 255 / 255 → 255 × 4 (peak sRGB at the anchor); probe 0.766–0.770, 0.619–0.624, 0.766–0.770, 0.838–0.850, 0.889–0.890 over the four positions; bot80a / b and bot300lo drawn before and after (`gpu/range_new/sheet_after.jpg`). GPU spot checks, the near-range GPU check and the temporal check below |
| R2 minor | beyond ~100 m a lamp under 5–10 cm of winglet / tip skin is drawn again (E = 2 mm + 0.5 pixel outgrows the skin) | the pixel term of the allowance, the same depth-resolution limit | solved with R1: below 1.5 pixels the table decides (no allowance at all), between 1.5 and 3 pixels the table's veto g joins the iteration-5 test, above 3 pixels the iteration-5 allowance is below half the lamp's own size | hidden lamps (0 % seen) drawn at some position, 150 / 300 / 400 m: PC-12 navL **61 / 68 / 68 → 1 / 1 / 1**, navR 59 / 68 / 70 → 0, strobeL 55 / 64 / 65 → 5, strobeR 51 / 64 / 63 → 2; all PC-12 lights 324 / 421 / 449 → **22**, SF50 366 / 448 / 471 → **27**; "over" (≤ 9 % seen, drawn at ≥ 5/9) PC-12 383 / 562 / 601 → **1**, SF50 495 / 648 / 679 → **0**. What remains are directions within about one table cell (2.8°) of a lamp's visibility edge, where the bilinear table gives a small value (drawn dim at every position, not blinking: of the 22 PC-12 directions none blinks, of the 27 SF50 directions one) [round 2, 15.11: "dim" did not hold - over every direction the PC-12 draws a hidden lamp at up to 0.8-0.99 of full brightness behind thin occluders (an edge-on stabilizer, an antenna, the nose leg); the error per light is stated there] |
| R3 minor | the headline figures excluded the lower hemisphere and stopped at 40 m | sweep filter (eye y < 0.3 m dropped), 10 / 40 m only | full-sphere sweeps at 5–400 m with the 16-position jitter metric, before and after, both models, CPU + GPU (below) | tables below; the iteration-5 claim "lights that should show still do" did not hold beyond 40 m (false hides 64–493 per range, PC-12); it holds now at 10–400 m (0 false hides for the PC-12; SF50 1 at 10 m) and at 5 m all but 1 PC-12 / 4 SF50 directions of ~1,200 (iteration 5: 0 / 25) |
| R4 minor | one veil value for the whole flight-deck glazing moved most sunlit windshield boxes away from the references for the side windows' gain | windshield and crew side windows shared material id 27 | `js/aircraft/models.js` `AC_PART_MAT`: on the deck glazing part, glass_windshield keeps **27**, the other glass (the PC-12's crew side windows) takes **28** (`AC_DECK_WINDSHIELD`); `js/aircraft/detailed.js` `GLASS_FS` `uVeilSunWs` / `uVeilSunSide`, **GLASS_VEIL_SUN_WS 0.9, GLASS_VEIL_SUN_SIDE 0.45** [inf: appearance fit] (0.65 both before), fitted separately over 11 windshield / 13 side-window boxes at the 12 reference cameras (renders at 0.3 and 1.0, interpolated in linear light; `tools/fitveil.py`: windshield 0.5 8.0, 0.65 5.6, 0.8 4.2, **0.9 3.9**, 1.0 4.0 levels outside the dev-stage range; side windows 0.3 5.4, **0.45 4.8**, 0.5 4.9, 0.65 5.5, 0.8 6.8). The SF50's windshield (id 27; it has no deck side-window glass) keeps **0.65** through `deck.veilWs` (`veilNote`): there are no SF50 reference boxes to fit it to | per box below; windshield boxes, mean distance outside the dev-stage range **5.7 → 4.6** sRGB levels, side-window boxes (the glass and what is seen through it) **4.6 → 4.0** |
| R5 minor | the deck-light ramp (1 m) reached the SF50's second seat row; the PC-12's door window brightened, not compared with a reference | fixed `DECK_RAMP` 1 m | per-type ramp: `js/aircraft/models.js` `deck.ramp` → `ACOBJ_FS` `uDeckRamp`; **SF50 0.30 m** (ends at x 1.10, before the second row's front edge at x 1.06); **PC-12 keeps 1 m** (`deck.rampNote`): it has no bulkhead behind the crew seats, its first passenger row (front edge x 1.60) sits in the open forward cabin that the windshield and crew side windows light, and with a 0.3 m ramp the door window and the shaded crew side windows of the reference cameras read further from both references (below) [inf] | SF50 second row front edge: deck share 0.73 → **0** (smoothstep(−1, 0, −0.34) → smoothstep(−0.3, 0, −0.34)); the SF50 cabin windows' second row reads darker in the docs stills (below). PC-12 cockpit camera, door window: (26, 33, 41), 14.3 levels below the range of dev (45, 48, 50) / stage (57, 62, 65), unchanged with the 1 m ramp kept - a 0.3 m ramp gave (20, 28, 36), 19.7; the shaded crew side window by the port grazing camera 11.0 (0.3 m: 14.3). The door window stays darker than both references (it is a cabin window, id 24: its interior is the cabin's, owner-taste F5 / F6) |

**Near range (5–20 m).** At 5–20 m the lamps are 3–17 pixels across (w = 0) and the first form of this test (v5 × g, the
"pre" rule of `cpu/sw_i_*`) kept two faults there. (1) The table is a view from afar: from a camera **nearer to the lamp
than an occluder of its direction** - 5 m from a PC-12 wing-tip strobe on the side of the fuselage, the camera between the
lamp and the fuselage - the eye sees past that occluder while the table says hidden, and g vetoed a lamp the ray cast sees
fully (PC-12 at 5 m: 15 false hides, 8 directions hidden at all 16 positions, strobes and nav lamps; iteration 5: 0). The
tables' third channel now holds, per cell, the distance from the lamp to the farthest first occluder of its rays (0.1 m
units, `LAMPVIS.TFS`), and **q = smoothstep(f, f + 0.5 m, distance to the camera)** (`LENS_TF`) takes the table out where the
camera is nearer: the iteration-5 test alone decides there (the farthest occluders lie 5–12.5 m from the PC-12 lamps).
(2) v5 alone still blinked where a few taps straddle a lamp's own rim (SF50 strobes and landing lights at 5–20 m: 5 / 5 / 1
blinking directions at 5 / 10 / 20 m), so the near term is never below the table where the table clearly sees the lamp:
**max(v5 × g, T × g × vExt × smoothstep(0.25, 0.5, T) × q)** (`LENS_N0` / `LENS_N1`; unchanged where the table is near its
edge, so a hidden lamp is not drawn more often than by v5). All lights, pre → final at 5 / 10 / 20 m (`cpu/sw_i_*`,
`sw_n_*`): PC-12 false hides 15 / 1 / 0 → **1 / 0 / 0**, lamps seen ≥ 50 % hidden at every position 8 / 1 / 0 → **0**, hidden
lamps drawn 0 / 10 / 22 → 1 / 11 / 22; SF50 blinking directions 5 / 5 / 1 → **0 / 0 / 0**, false hides 28 / 26 / 10 → **4 / 1 /
0**, hidden lamps drawn 18 / 22 / 28 → 19 / 22 / 28. Variants measured and not taken: max(v5, T × vExt) without the gate n
(SF50 blinking 0 too, but hidden lamps drawn +7 / +6 at 5 / 10 m, PC-12 0 → 18 at 5 m). **GPU, near range** (`out/od4_it6/gpu/near_after_*`, `jobs_near_*.json`; 8 cases per type where the pre rule hid a lamp seen
≥ 50 % at some of the 16 positions, four sub-pixel positions each, the final shader): PC-12 at 5 m (strobes, navL: hidden at all
16 positions by the pre rule on the CPU) hidden positions **0 of 32**, the values at the seen share (strobeL seen 1.00: 1 × 4,
seen 0.54: 0.44 / 0.44 / 0.56 / 0.56; navL seen 0.81: 0.89 × 4); SF50 at 5–20 m (strobes, landR; the pre rule hid 1–11 of 16
positions) **0 of 32**, values 0.50–1.00 (strobeR seen 0.55: 0.51 / 0.51 / 1 / 1; strobeL seen 0.50: 1 / 0.50 / 1 / 1) - at close
range the brightness still moves with the sub-pixel position between the table's share and the depth test's, but never to
off. [round 3, 15.12: "never to off" held only for lamps seen >= 50 % - the counts above are of those; partly seen lamps at 10–30 m
(the SF50 tip strobes, 10–50 % seen) went fully on / off with the sub-pixel position. Fixed and measured with a jitter
column there.]

**R3: full-sphere range and sub-pixel figures, fov 45° / 1080 lines, 300 directions × 16 sub-pixel positions per light and
range** [round 3, 15.12: these tables are of the iteration-6 (round-1) tree, its truth and tables with the propeller blades at
rest and the raw rest geometry; the final tree's figures at 5–400 m, with a sub-pixel jitter column, are in 15.12 and
supersede them] (`out/od4_it6/cpu/sw_m_*_f45_h1080_centre.json` = `tools/merge_sw.py` over `sw_g` / `sw_k` / `sw_l` / `sw_n`;
`tools/mktable.py`). Per light, each cell gives *blinking directions of a lamp seen ≥ 50 % (hidden at some of the 16
positions, drawn at others) / hidden lamps (0 % seen) drawn at some position / false hides (≥ 25 % seen, drawn 0 at some
position)*, before (iteration 5) → after (the final rule).

**PC12** (cell: blinking directions of a lamp seen >= 50 % / hidden lamps drawn somewhere / false hides, before -> after)

| light | 5 m | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|---|
| navL | 0→0 / 0→0 / 0→0 | 0→0 / 2→1 / 0→0 | 0→0 / 14→1 / 5→0 | 0→0 / 46→1 / 17→0 | 3→0 / 61→1 / 37→0 | 4→0 / 68→1 / 41→0 | 2→0 / 68→1 / 29→0 |
| navR | 0→0 / 0→0 / 0→0 | 0→0 / 0→0 / 0→0 | 0→0 / 11→0 / 4→0 | 0→0 / 45→0 / 17→0 | 6→0 / 59→0 / 37→0 | 8→0 / 68→0 / 40→0 | 1→0 / 70→0 / 27→0 |
| tail | 0→0 / 6→0 / 0→0 | 0→0 / 10→0 / 0→0 | 0→0 / 8→0 / 12→0 | 0→0 / 7→0 / 42→0 | 0→0 / 18→0 / 17→0 | 2→0 / 21→0 / 29→0 | 6→0 / 21→0 / 41→0 |
| beaconTop | 0→0 / 1→0 / 0→0 | 0→0 / 2→0 / 0→0 | 1→0 / 2→3 / 14→0 | 6→0 / 9→3 / 43→0 | 8→0 / 56→3 / 26→0 | 4→0 / 72→3 / 20→0 | 4→0 / 77→3 / 19→0 |
| beaconBot | 0→0 / 0→0 / 0→0 | 0→0 / 0→0 / 0→0 | 1→0 / 0→1 / 3→0 | 42→0 / 0→1 / 44→0 | 71→0 / 2→1 / 73→0 | 62→0 / 13→1 / 64→0 | 69→0 / 22→1 / 71→0 |
| strobeL | 0→0 / 0→0 / 0→0 | 0→0 / 0→0 / 0→0 | 0→0 / 23→5 / 4→0 | 33→0 / 45→5 / 44→0 | 44→0 / 55→5 / 52→0 | 48→0 / 64→5 / 54→0 | 49→0 / 65→5 / 54→0 |
| strobeR | 0→0 / 0→0 / 0→0 | 0→0 / 0→1 / 0→0 | 1→0 / 24→2 / 8→0 | 34→0 / 45→2 / 51→0 | 48→0 / 51→2 / 62→0 | 45→0 / 64→2 / 56→0 | 46→0 / 63→2 / 56→0 |
| landL | 0→0 / 0→1 / 0→1 | 0→0 / 1→4 / 0→0 | 2→0 / 0→3 / 5→0 | 2→0 / 5→3 / 5→0 | 17→0 / 5→3 / 20→0 | 52→0 / 11→3 / 55→0 | 67→0 / 16→3 / 70→0 |
| landR | 0→0 / 0→0 / 0→0 | 0→0 / 0→5 / 0→0 | 2→0 / 1→5 / 4→0 | 4→0 / 6→5 / 6→0 | 13→0 / 7→5 / 15→0 | 56→0 / 15→5 / 58→0 | 63→0 / 21→5 / 65→0 |
| taxi | 0→0 / 0→0 / 0→0 | 0→0 / 0→0 / 0→0 | 0→0 / 1→3 / 5→0 | 0→0 / 5→2 / 16→0 | 10→0 / 10→2 / 38→0 | 15→0 / 25→2 / 32→0 | 43→0 / 26→2 / 61→0 |

| PC12, all lights | 5 m | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|---|
| directions (lamp seen >= 50 % / 0 %) | - → 1394 / 867 → 1394 / 867 | 1379 / 916 → 1379 / 916 → 1379 / 916 | 1379 / 933 → 1379 / 933 → 1379 / 933 | 1379 / 932 → 1379 / 932 → 1379 / 932 | 1379 / 931 → 1379 / 931 → 1379 / 931 | 1379 / 931 → 1379 / 931 → 1379 / 931 | - → 1379 / 931 → 1379 / 931 |
| positions hiding a lamp seen >= 50 % | - → 0.00 % → 0.00 % | 0.00 % → 0.00 % → 0.00 % | 0.00 % → 0.06 % → 0.00 % | 0.00 % → 1.90 % → 0.00 % | 0.39 % → 3.98 % → 0.00 % | 3.27 % → 4.96 % → 0.00 % | - → 6.19 % → 0.00 % |
| blinking directions (seen >= 50 %) | - → 0 → 0 | 0 → 0 → 0 | 0 → 7 → 0 | 0 → 121 → 0 | 29 → 220 → 0 | 179 → 296 → 0 | - → 350 → 0 |
| hidden lamps drawn (directions, of which blinking) | - → 7 (7) → 1 (1) | 256 (37) → 15 (15) → 11 (1) | 321 (116) → 84 (84) → 23 (0) | 350 (135) → 213 (207) → 22 (0) | 396 (194) → 324 (306) → 22 (0) | 489 (313) → 421 (363) → 22 (0) | - → 449 (372) → 22 (0) |
| over (<= 9 % seen, drawn >= 5/9) | - → 0 → 0 | 212 → 0 → 0 | 313 → 28 → 1 | 395 → 169 → 1 | 482 → 383 → 1 | 644 → 562 → 1 | - → 601 → 1 |
| false hides (>= 25 % seen, drawn 0) | - → 0 → 1 | 0 → 0 → 0 | 1 → 64 → 0 | 7 → 285 → 0 | 57 → 377 → 0 | 242 → 449 → 0 | - → 493 → 0 |
| mean abs error | - → 0.036 → 0.035 | 0.223 → 0.043 → 0.038 | 0.250 → 0.092 → 0.023 | 0.278 → 0.151 → 0.023 | 0.303 → 0.226 → 0.023 | 0.341 → 0.306 → 0.023 | - → 0.327 → 0.023 |

**SF50** (cell: blinking directions of a lamp seen >= 50 % / hidden lamps drawn somewhere / false hides, before -> after)

| light | 5 m | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|---|
| navL | 0→0 / 10→2 / 0→0 | 0→0 / 20→1 / 0→0 | 0→0 / 37→1 / 0→0 | 0→0 / 44→1 / 3→0 | 5→0 / 43→1 / 16→0 | 3→0 / 54→1 / 20→0 | 4→0 / 56→1 / 21→0 |
| navR | 0→0 / 13→0 / 2→0 | 0→0 / 23→0 / 2→0 | 0→0 / 34→0 / 1→0 | 1→0 / 41→0 / 4→0 | 7→0 / 39→0 / 13→0 | 6→0 / 52→0 / 20→0 | 7→0 / 54→0 / 23→0 |
| tail | 0→0 / 10→0 / 0→1 | 0→0 / 12→0 / 0→0 | 0→0 / 21→2 / 0→0 | 0→0 / 34→2 / 0→0 | 0→0 / 46→2 / 0→0 | 0→0 / 59→2 / 0→0 | 0→0 / 62→2 / 0→0 |
| strobeL | 3→0 / 33→10 / 7→0 | 3→0 / 38→10 / 7→0 | 5→0 / 56→10 / 11→0 | 8→0 / 59→10 / 12→0 | 16→0 / 60→10 / 19→0 | 14→0 / 60→10 / 16→0 | 14→0 / 60→10 / 15→0 |
| strobeR | 1→0 / 31→4 / 7→1 | 1→0 / 42→7 / 7→1 | 4→0 / 60→8 / 11→0 | 6→0 / 60→8 / 8→0 | 14→0 / 60→8 / 17→0 | 12→0 / 61→8 / 12→0 | 12→0 / 62→8 / 14→0 |
| strobeTail | 0→0 / 8→0 / 0→1 | 0→0 / 10→0 / 0→0 | 0→0 / 22→2 / 0→0 | 0→0 / 37→2 / 0→0 | 0→0 / 45→2 / 0→0 | 0→0 / 58→2 / 0→0 | 0→0 / 60→2 / 0→0 |
| landL | 0→0 / 18→1 / 2→0 | 0→0 / 23→1 / 3→0 | 0→0 / 33→1 / 1→0 | 1→0 / 33→1 / 5→0 | 10→0 / 33→1 / 16→0 | 16→0 / 43→1 / 33→0 | 5→0 / 44→1 / 26→0 |
| landR | 1→0 / 15→2 / 3→1 | 1→0 / 18→2 / 2→0 | 0→0 / 35→2 / 2→0 | 0→0 / 35→2 / 2→0 | 12→0 / 33→2 / 18→0 | 14→0 / 43→2 / 33→0 | 7→0 / 45→2 / 27→0 |
| taxi | 0→0 / 0→0 / 4→0 | 0→0 / 1→1 / 6→0 | 6→0 / 4→1 / 17→0 | 12→0 / 4→1 / 29→0 | 28→0 / 7→1 / 48→0 | 26→0 / 18→1 / 40→0 | 34→0 / 28→1 / 53→0 |

| SF50, all lights | 5 m | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|---|
| directions (lamp seen >= 50 % / 0 %) | - → 1185 / 636 → 1185 / 636 | 1181 / 678 → 1181 / 678 → 1181 / 678 | 1186 / 676 → 1186 / 676 → 1186 / 676 | 1185 / 675 → 1185 / 675 → 1185 / 675 | 1185 / 673 → 1185 / 673 → 1185 / 673 | 1185 / 673 → 1185 / 673 → 1185 / 673 | - → 1185 / 674 → 1185 / 674 |
| positions hiding a lamp seen >= 50 % | - → 0.16 % → 0.00 % | 0.00 % → 0.11 % → 0.00 % | 0.00 % → 0.20 % → 0.00 % | 0.00 % → 0.40 % → 0.00 % | 0.02 % → 1.02 % → 0.00 % | 0.43 % → 1.21 % → 0.00 % | - → 1.05 % → 0.00 % |
| blinking directions (seen >= 50 %) | - → 5 → 0 | 0 → 5 → 0 | 0 → 15 → 0 | 0 → 28 → 0 | 3 → 92 → 0 | 25 → 91 → 0 | - → 83 → 0 |
| hidden lamps drawn (directions, of which blinking) | - → 138 (90) → 19 (5) | 456 (26) → 187 (144) → 22 (8) | 503 (108) → 302 (276) → 27 (1) | 530 (169) → 347 (308) → 27 (1) | 551 (242) → 366 (326) → 27 (1) | 558 (323) → 448 (383) → 27 (1) | - → 471 (405) → 27 (1) |
| over (<= 9 % seen, drawn >= 5/9) | - → 12 → 4 | 482 → 30 → 8 | 595 → 87 → 2 | 670 → 289 → 0 | 750 → 495 → 0 | 807 → 648 → 0 | - → 679 → 0 |
| false hides (>= 25 % seen, drawn 0) | - → 25 → 4 | 0 → 27 → 1 | 0 → 43 → 0 | 1 → 63 → 0 | 10 → 147 → 0 | 39 → 174 → 0 | - → 179 → 0 |
| mean abs error | - → 0.096 → 0.080 | 0.397 → 0.102 → 0.080 | 0.421 → 0.159 → 0.050 | 0.445 → 0.226 → 0.050 | 0.467 → 0.285 → 0.050 | 0.491 → 0.364 → 0.050 | - → 0.385 → 0.050 |

The aggregate rows give iteration 4 → iteration 5 → iteration 6 (iteration 4 was not swept at 5 and 400 m: "-").
"Directions" excludes eyes inside the airframe and lamps with no projected area (a one-sided SF50 patch edge-on). At 80–400
m every light is below 1.5 pixels in the final rule (w = 1) and no camera is nearer than an occluder (q = 1). Other settings
(`cpu/sw_h_*`, first form of the rule, which equals the final one beyond 20 m; iteration 5 → 6, 40 / 80 / 150 / 300 m): fov 30°
/ 1080 PC-12 blinking directions 0 / 26 / 134 / 230 → 0, hidden positions 0 / 0.33 / 2.77 / 3.67 % → 0; SF50 7 / 14 / 40 / 81
→ 0; fov 55° / 720 PC-12 106 / 231 / 293 / 409 → 0 (1.49–7.54 % of positions → 0), SF50 27 / 98 / 102 / 107 → 0.

**GPU spot checks** (`out/od4_it6/gpu/spot_*`, `jobs_spot_*_sel.json`, `tools/spot_summary.py`): per type 12 cases picked
from the CPU sweep where iteration 5 blinked or leaked (80 / 150 / 300 m), four sub-pixel camera positions each, the probe value
of the case's light before → after (night, neutral pad, aircraft raised so the eye is above it). PC-12, 8 blink cases: hidden
positions **6 → 0** (beaconBot 80 m 0.50 / 1 / 1 / 0.75 → 1 × 4, 150 m 0 / 1 / 1 / 1 → 1 × 4; beaconTop 150 m (seen 0.56) 0 /
0.29 / 0.20 / 0.67 → 0.50 × 4; strobeR 150 m 0 / 0 / 1 / 0 → 1 × 4, 300 m 0 / 0.50 / 1 / 1 → 1 × 4); 4 leak cases: drawn
positions **12 → 0** (navL 150 m 0.5 / 1 / 0.5 / 0.5 → 0 × 4, navL 300 m and tail 150 m 1 × 4 → 0 × 4). SF50, 8 blink cases: hidden
positions **4 → 0** (taxi 150 m (seen 0.88) 0 × 4 → 0.91 × 4; landL 150 m 0.25 / 0.50 / 0.20 / 0.60 → 0.55 × 4); 4 leak cases:
drawn positions **10 → 0** (navL 300 m, strobeR, strobeTail, tail 150 m). After, every case reads the same value at its four
positions.

**Temporal check** (`out/od4_it6/seq/`, `tools/seq6.mjs`, `seq_truth.mjs`, `seq_sheet.py`): 60 frames at 30 fps of each type
moving past a fixed camera ~150 m away, by night (2026-11-14 05:00Z), 1920 × 1080, fov 40°, one white omni sprite per light
anchor (always on: the count is about the lens test, not the flash pattern); per frame the GPU probe, the CPU ray-cast truth
from that frame's camera and the CPU replica; "flicker" = a drawn ↔ not-drawn change between consecutive frames whose truth
both say the light is seen (≥ 25 %). **Roll**: the aircraft on runway 28L at 25 m/s, the camera 12 m up (4.6° down: the
recheck's geometry), 50 m of travel. PC-12: flicker of seen lights, iteration 5 → 6, tail **8 → 0**, beaconTop **4 → 0**,
beaconBot **1 → 0**, strobeR **7 → 0** (all others 0 → 0); drawn in frames where the truth sees the light: tail 52 → 60 of 60,
beaconTop 58 → 60, beaconBot 53 → 60, strobeR 6 → 17 of 17. SF50: strobeL **2 → 0**, taxi **10 → 0** (drawn 38 → 60 of 60 frames
seen). **Low pass** (the final shader): 30 m up at 50 m/s, 100 m of travel, the camera on the ground ~155 m away looking up:
flicker of seen lights **0** for every light of both types, and every frame whose truth sees a light draws it (PC-12: tail, taxi,
landL 60 / 60, beaconBot 57 / 57, landR 36 / 36, beaconTop 35 / 35, strobeR 20 / 20, strobeL 14 / 14; SF50: navL, strobeL, landL
60 / 60, taxi 43 / 43, tail and strobeTail 10 / 10); drawn in frames whose truth says hidden: PC-12 landR 3 of 22, navR and
beaconBot 1 each (at a visibility edge), SF50 none; the GPU equals the CPU replica in every frame (max |GPU − CPU| 0.000). What the after runs still show: the PC-12's far-side lights through the cabin windows (glass counts as
transparent in the truth and in the tables): navR is seen 27.5 % in 7 frames through two aligned cabin windows and drawn in
none (the table's 2.8° cells smooth the narrow window aperture away; no flicker), strobeR is drawn dim (at most 0.48) in 31 of 41
frames whose truth says hidden, with 5 on / off changes in those frames (the bilinear table at the aperture's edge).

**R4 per box** (same-pixel sRGB medians, the boxes of 15.8 / 15.9: `tools/g4m6.py`; references dev / stage; distance outside
their range in sRGB levels; before = iteration 5's renders as measured by the recheck, `out/od4f_rc2/g4measure_before_w3_w2.json`,
after = `out/od4_it6/f4/final2_*`, this tree; camera, box, sun / shade, before (median) distance → after (median) distance):
**windshield (id 27)**, mean distance 5.7 → 4.6: ws_close windshield (sun) (41, 48, 55) 3.3 → (45, 52, 58) 0.3 [dev (46, 54, 61), stage (43, 52, 59)]; g4_top_graze ws_right (sun) (28, 35, 42) 13.0 → (34, 42, 48) 6.7 [dev (39, 49, 56), stage (41, 51, 59)]; g4_top_graze ws_left (sun) (45, 50, 54) 2.0 → (51, 57, 60) 4.7 [dev (42, 52, 60), stage (40, 50, 57)]; g4_low_front windshield (sun) (46, 51, 58) 1.7 → (50, 56, 62) 5.7 [dev (41, 51, 59), stage (38, 48, 57)]; cockpit windshield (shade) (37, 43, 51) 3.7 → (41, 48, 56) 0.0 [dev (39, 48, 55), stage (44, 54, 62)]; hwd_front34 windshield (sun) (60, 62, 64) 1.0 → (58, 59, 62) 0.3 [dev (57, 65, 73), stage (48, 55, 62)]; nose windshield_L (sun) (52, 57, 62) 2.7 → (56, 63, 68) 8.0 [dev (45, 56, 62), stage (42, 52, 60)]; nose windshield_R (sun) (36, 40, 46) 19.0 → (41, 46, 51) 13.7 [dev (53, 61, 65), stage (55, 64, 70)]; hwd_nose windshield (sun) (55, 61, 68) 8.0 → (59, 66, 73) 3.3 [dev (65, 72, 76), stage (62, 70, 77)]; ws_close windshield (sun) (41, 48, 52) 3.3 → (48, 51, 57) 2.3 [dev (43, 53, 60), stage (41, 51, 59)]; sidewin_close_port windshield_wrap (shade) (41, 44, 49) 4.7 → (40, 43, 48) 5.7 [dev (44, 50, 54), stage (45, 53, 60)].
**crew side windows (id 28) and what is seen through them**, mean distance 4.6 → 4.0: g4_port_graze side_window (shade) (22, 27, 35) 14.0 → (22, 27, 35) 14.0 [dev (37, 42, 47), stage (51, 58, 63)]; g4_port_graze side_seat (shade) (41, 40, 42) 3.0 → (40, 40, 42) 3.0 [dev (37, 43, 48), stage (48, 55, 62)]; g4_port_graze side_wall_r (shade) (29, 36, 44) 11.0 → (29, 36, 44) 11.0 [dev (45, 48, 49), stage (56, 60, 64)]; g4_stbd_graze side_window (sun) (54, 57, 61) 0.3 → (48, 50, 55) 0.0 [dev (53, 61, 66), stage (41, 47, 52)]; g4_stbd_graze side_seat (sun) (53, 56, 59) 1.7 → (47, 49, 53) 0.0 [dev (48, 56, 64), stage (37, 43, 49)]; ws_close side_window (sun) (54, 57, 60) 1.3 → (48, 50, 54) 0.0 [dev (50, 58, 65), stage (39, 45, 51)]; sidewin_close_port side_window (shade) (22, 26, 32) 11.0 → (22, 26, 32) 11.0 [dev (34, 38, 41), stage (50, 55, 59)]; g4_side_wrap side_window (sun) (51, 55, 60) 1.3 → (44, 49, 54) 0.0 [dev (47, 55, 63), stage (40, 47, 53)]; g4_rear_port side_window (shade) (33, 40, 49) 0.7 → (33, 40, 49) 0.7 [dev (35, 40, 45), stage (47, 54, 60)]; cockpit sidewin (shade) (19, 26, 35) 1.7 → (19, 26, 35) 1.7 [dev (23, 27, 31), stage (38, 44, 50)]; hwd_nose sidewin (sun) (56, 59, 62) 1.7 → (50, 52, 57) 0.0 [dev (51, 60, 67), stage (38, 44, 50)]; ws_close sidewin (sun) (54, 57, 61) 2.0 → (48, 51, 55) 0.0 [dev (49, 56, 63), stage (37, 43, 49)]; sidewin_close_port sidewin (shade) (20, 24, 29) 10.7 → (20, 24, 29) 10.7 [dev (30, 35, 40), stage (44, 52, 58)].
**cabin windows (id 24, not refitted)**, mean distance 10.3 → 10.3: cockpit door_window (shade) (26, 33, 41) 14.3 → (26, 33, 41) 14.3 [dev (45, 48, 50), stage (57, 62, 65)]; cockpit cabin_win2 (shade) (24, 31, 40) 6.3 → (24, 31, 40) 6.3 [dev (35, 38, 41), stage (55, 60, 64)].

**Docs stills** re-rendered with this tree (`node dev/model_shot.mjs --jobs=out/pc12_look_it4/jobs_docs_pc12.json --prefix=pc12`,
`--model=SF50 --jobs=out/pc12_look_it4/jobs_docs_sf50.json --prefix=viewer_sf50`, the dusk still with
`--jobs=out/od4_it5/jobs_sf50_dusk.json --t=2026-11-14T01:05:00Z`) and compared with the committed ones
(`out/od4_it6/tools/docs_cmp6.py`; every image looked at). The nine PC-12 stills, the SF50 dusk still and five SF50 day stills
render the same (mean |difference| ≤ 0.04 sRGB levels, at most 5 pixels off by more than 24: the noon stills show no sunlit
flight-deck glass, and the dusk still's lights are several pixels across, where the test is iteration 5's), so they and their
captions stay as they were. Seven SF50 day stills change and are replaced (captions in `docs/phase3/SOURCES.json` rewritten
by the tool; only the render time differs): fade, front34, flaps40, rear34 and side (803 / 642 / 58 / 58 / 87 pixels: the
second seat row behind the cabin windows is darker, R5), nacelle and gearup_root_top (110 / 20 pixels: fewer bright dots
along a window-frame seam). Before / after sheets: `out/od4_it6/docs_cmp/sf50_kept_sheet.jpg`, `docs_sheet{1,2,3,4}.jpg`.

**Tests**: `node tools/models/test_models.mjs` → **107 PASS, 13 KNOWN, 0 FAIL**, 4 INFO (`out/od4_it6/test_models_final.txt`):
iteration 5's proposed checks (`out/od4_it5/test_models_it5_checks.patch`, which carries iteration 4's) applied and updated to
this iteration (the G3 deck check for ids 27 / 28 and the type's windshield veil, the 40-float sprite layout, the tap rule's
per-pixel term, the deck ramp), plus the iteration-6 checks: every drawn light has its table (NA × NE × [gear down, gear up,
farthest occluder]; PC-12 10 lamps, SF50 9); the tables agree with an independent ray cast (16 directions per light, mean
|table − ray cast| PC-12 0.024, SF50 0.058, limit 0.08); the farthest-occluder channel holds at least half the ray cast's
distance (PC-12 28 of 29 directions, SF50 27 of 29, limit 90 %); every light takes a share of its table from 38 m (PC-12) /
61 m (SF50) at fov 30° / 1080 lines (limit 80 m; the table alone from 77 / 123 m there, from 50 / 80 m at fov 45°); the deck ramp
ends before the first seat row aft of the deck or the registry says why (SF50: ends at x 1.10, the second row's front edge at
x 1.06; PC-12: rampNote); the shader / scene / drawable / registry wiring. **`python3 -I -B tools/check_airport.py`** →
**RESULT: ALL HARD CHECKS PASSED** (`out/od4_it6/check_airport_final.txt`). The live app (replay shim, relay-less, night) loads
and draws with 0 console errors (`out/od4_it6/tools/app_smoke.mjs`, `out/od4_it6/app/`; no detailed aircraft in its pack at
that instant, so the app path of the tables was exercised by the dev viewer only).

**Files changed in this iteration**: renderer / shared - `js/scene.js` (`SPRITE_F` 40, `LampVisAtlas` RGBA8, iL4 / iL5 packing,
`uLampVis` / `uLampVisNE`, header), `js/shaders/sprites.js` (`lensVisible`: table blend, near gate, near-camera guard,
`lampTable`, external-occluder taps, `LENS_R1` / `R2` / `G0` / `G1` / `QMIN` / `N0` / `N1` / `TF`, iL4 / iL5, header); aircraft
runtime - `js/aircraft/glb.js` (`lampTables`, `lampVisLookup`, `lampVisFar`, `LAMPVIS`, a compact BVH), `js/aircraft/models.js`
(`loadModel` computes the tables; `AC_DECK_WINDSHIELD`, id 28 in `AC_PART_MAT`; `deck.ramp` / `rampNote` / `veilWs` /
`veilNote` per type), `js/aircraft/detailed.js` (`lampWorld`: table, gear-up share, bounding sphere, `LAMPVIS_BS_MARGIN`;
`GLASS_FS` `uVeilSunWs` / `uVeilSunSide`, `GLASS_VEIL_SUN_WS` / `_SIDE`, the type's `deck.veilWs`; `ACOBJ_FS` `uDeckRamp`,
`DECK_RAMP_DEFAULT`); `dev/model.js` (`HWDM.lensProbe()`); `tools/models/test_models.mjs` (iteration 5's proposed checks
applied - they contain iteration 4's - and updated; new iteration-6 checks); this file (sections 3, 8, 9, 15.10);
`docs/phase3/viewer_sf50_{fade,front34,flaps40,rear34,side,nacelle,gearup_root_top}.jpg` + `SOURCES.json`. Not changed: `js/renderer.js`, `js/gl.js` (its `setInstances` already takes 10 vec4s), the world shaders,
`js/live/**`, `js/video/**`, `js/env/**`, the glb files.

**Open / not verified (iteration 6)**: the tables are of the model at rest (flaps 0, controls neutral, doors closed; gear
down / up), so below 3 pixels a lamp's visibility ignores a deflected surface, an open door or gear in transit (above 3
pixels the depth test sees them, but the near gate's floor can still draw a lamp that only a deflected surface hides);
within ~one table cell (2.8°) of a visibility edge the bilinear table draws a hidden lamp dim or a visible one dimmer (the
residual "hidden lamps drawn" above: drawn at every position, not blinking; round 2, 15.11: not "dim" - up to 0.8-0.99 behind thin occluders
narrower than a cell; stated per light there), and a narrow aperture (two aligned cabin
windows) is smoothed away; the gate / blend constants (`LENS_R1` 1.5, `LENS_R2` 3 pixels, `LENS_G0` 0.04, `LENS_G1` 0.2,
`LENS_N0` 0.25, `LENS_N1` 0.5, `LENS_TF` 0.5 m) and the 0.5 m bounding-sphere margin are inferred; within the near-camera
guard (a camera nearer than an occluder of the lamp's direction, i.e. within ~12 m) the test is iteration 5's, including its
SF50 near leaks there; an occluder that is not the aircraft but lies inside its bounding sphere (another aircraft parked
within ~11 m) does not hide a sub-pixel lamp [round 2, 15.11: fixed by the reach channel; and the propeller blades were in the
tables, also fixed there]; load cost: the tables take 4.6 s (PC-12) and 6.8 s (SF50) per model in the dev page on this shared 4-CPU machine under load (3.4–3.9 / 6.7–8.0 s before the farthest-occluder channel was added; Node, same load: 8.5 / 11.0 s against 6.0 / 7.9 s), before the drawable leaves its placeholder;
per frame one RGBA8 lookup and nine more depth fetches per vertex of an aircraft light; the atlas is 32 KB per lamp. Laptop GPU
frame time not measured. The windshield / side-window veils are appearance fits to the reference viewer, not physics; the
shaded side windows stay below the references by the world's shade level (owner-taste F5 / F6, unchanged); the SF50's
windshield veil is not fitted (no references). The PC-12's first passenger row is partly deck-lit (rampNote) [inf]. A
video-determinism comparison spanning this change will see the lens test at range, the veils and the SF50 cabin.

### 15.11 OD4 iteration 6, round 2 (recheck of 2026-11-21, findings F1–F3): dispositions
The recheck of iteration 6 (its tools and renders `out/od4_rc6_1/`, gitignored) found the three issues below. **Before** =
iteration 6 as it handed over (copies of its runtime files in `out/od4_it6r2/head/`, served to the GPU tools through
`--override`), **after** = this tree; tools, renders and measurements of this round: `out/od4_it6r2/` (gitignored). **CPU**:
`out/od4_it6r2/tools/lens7.mjs` `it7Test` = a replica of the new shader (it equals `it6Test` of 15.10 except for the
external-occluder taps, which it always evaluates), on the model **without the propeller blades** (F1: in the app a lamp is
on only with the engine running, and above `PROP_BLUR` the blades are not drawn) - for the depth buffer and for the ray-cast
truth alike; **truth** = 15.10's (11 × 11 rays over the lamp's support box × 1.05), re-cast with 61 × 61 rays when fewer than
30 of the 121 meet the lamp (F3 below: a flat SF50 lamp patch seen nearly edge-on). Sweeps (`tools/sweep7.mjs`): the
recheck's seeded random set of 300 directions per light (its `sw_a`), 16 sub-pixel positions, 25 / 35 / 50 / 60 / 120 / 250 m,
fov 45° / 1080 lines, the app rig's near plane. **GPU**: the recheck's own tools (`out/od4_rc6_1/tools/gpu_rc.mjs`,
`seq_rc.mjs`, `seq_truth_rc.mjs`) and jobs, unchanged; dev viewer, 1920 × 1080, night (2026-11-14 05:00Z), neutral pad. The round was paused part-way (usage limit) and resumed; every result below was re-checked against
the final tree (no runtime file changed after the resume). Re-run or added after the resume (`out/od4_it6r2b/`, gitignored): the F1 GPU
jobs (the first run had loaded `sprites.js` before its last edit), the dense table-error check (F3), the tests, `check_airport`,
an app smoke test with a detailed aircraft, and the docs stills the first run had not reached.
Every image was looked at.

| # | finding | root cause | fix (file) | result (before → after) |
|---|---|---|---|---|
| F1 major | the tables held the five Hartzell blades at rotor angle 0: the PC-12 taxi light (nose leg, 2.15 m behind the prop plane) faded out and back as a taxiing PC-12 turned in front of a camera; landing lights at larger angles | `lampTables` built its occluder BVH from every opaque triangle at rest. In the app a lit PC-12 runs its engine (idle ~110 rad/s), and above `PROP_BLUR[1]` (60 rad/s) the blades are replaced by the translucent disc, which is not in the depth copy: the lamp is seen through it | `js/aircraft/glb.js` `lampTables`: **every triangle of a part below a 'pitch' mover below the 'spin' mover is left out** of the occluders (`bladeChain`, = `detailed.js` `prop.blades`; 29,640 PC-12 triangles, none on the SF50, whose fan has no blade movers); the axisymmetric spinner stays | **CPU** (the recheck's `prop_taxi.mjs` grid, lamp at 150 m, el −20..+10° × az −40..+40°, 1,296 directions; table vs the blade-free truth, `out/od4_it6r2/cpu/prop_*.txt`): directions where the table is below 0.5 although the truth is 1.0: taxi **79 → 0** (below 0.25: 34 → 0), landL **9 → 0**, beaconBot 0 → 0; largest (truth − table) taxi 0.05. **GPU** (the recheck's `jobs_prop_taxi.json`, probe): all 36 jobs (150 / 60 / 20 m, rpm 1700 = the disc and rpm 0 = rest blades drawn) **1.000** (`gpu/prop_summary.json`; re-run on the final tree after the resume, `out/od4_it6r2b/gpu/prop_after/`: all 36 again 1.000, peak 254–255, 0 page errors, the glow looked at in `prop_sheet.jpg`): el 2° az 16° 0.000 → 1.000 at 150 and 60 m, 0.010 → 1.000 at 20 m; el 2° az −14° 0.222 → 1.000, el −2° az 18° 0.214 → 1.000, el −2° az −16° 0.223 → 1.000 (iteration 5: 1.000 at all; the glow looked at in `gpu/prop_after_sheet.jpg`). **Temporal** (the recheck's `taxi60`: idle prop turning 60° in front of a camera 60 m ahead, 1.7 m up, 60 frames): the taxi light is drawn at **1.00 in all 60 frames** (iteration 6: 10 frames below half of the blade-free truth, down to 0.04 in frames 11–17 and 41–45; iteration 5: 1.00), landL 0 on / off changes and 0 frames below half (iteration 6: 2 and 3; min 0.38, was 0), landR 0 below half (1); beaconTop and the strobes still 0 flicker (iteration 5: 12 / 2 / 2); `gpu/seq/taxi60_after_sheet.jpg` (looked at), `truth.json` (`seq_truth_rc.mjs`) |
| F2 minor | external-occluder taps ignored every surface inside the aircraft's bounding sphere (11.6 m PC-12, 8.2 m SF50): another aircraft's wing or a hangar wall 1–3 m in front of a lamp did not hide it (sub-pixel; at near range through the floor) | `vExt` counted a tap only when its depth lay in front of the sphere's entry | **the table's fourth channel = the aircraft's reach in front of the lamp** (`js/aircraft/glb.js` `LAMPVIS.RHO` / `VOX` / `VS` / `RMIN`, `reachVoxels`, `reachSplat`, `lampVisReach`): per direction, an upper bound of how far in front of the lamp (from the plane through its centre, normal to the line of sight) any surface of the aircraft at rest (gear down, no blades) lies within RHO = 0.5 m of the line of sight - the first surface a ray in that cylinder meets coming from the camera is its farthest point in front, so the reach is the largest along-distance over the surface points in the cylinder; computed by splatting the surface (sampled at ≤ 5 cm into 10 cm voxels, each bounding its points within bV = 0.137 m) onto the grid, with one cell diagonal of slack so the bilinear lookup never falls below it; voxels within 0.25 m of the lamp (its housing) left out. `js/shaders/sprites.js` `lensVisible`: a tap's depth is **another object's when it lies more than reach + `LENS_XM` (0.3 m ≥ RMIN) in front of the lamp's plane**; the bounding sphere is kept only for a tap whose texel lies beyond `LENS_RHO` (= RHO) of the line of sight (its offset + `LENS_TXL`, 0.71 of a pixel; fov 45° / 1080: beyond ~460 m). `lampTable` returns (share, farthest occluder, reach) | **GPU** (the recheck's `jobs_occW_*` / `jobs_occB.json`: a second aircraft of the same type as a pure occluder, its wing 1–2 m in front of navR, camera 90° to the side at el 1° / 3°, 35 / 60 / 150 m; probe / peak added sRGB at the anchor, round 2 vs iteration 6 vs iteration 5, `gpu/occW_{PC12,SF50}_sheet.jpg`): with the occluder, **PC-12 0.000 / 0 in 5 of 6 cases** and 0.051 / 238 at 150 m el 1° (iteration 6 0.152–0.191 / 250–255, iteration 5 0 / 0); **SF50 0.000 / 0 in 5 of 6** and 0.306 / 254 at 150 m el 1° (iteration 6 0.918–0.922 / 255, iteration 5 0 / 0). At 150 m el 1° the other wing is seen edge-on, a band one to two pixels tall whose edge runs through the lamp's pixel (`gpu/occW_edge_zoom.jpg`): 3 of the 9 taps see past it, the lamp is drawn at a third of its share. Without the occluder every value is iteration 6's (PC-12 0.152 / 0.191, SF50 0.918–0.926: the tables' share of a tip lamp seen from abeam). occB: navR behind the other aircraft's fuselage 0.000 (iteration 6: 0.152, the quad then depth-culled), the controls (occluder outside the sphere) 0.000, the belly-beacon cases unchanged (0.859 / 0.716, as iteration 6). **CPU**: the aircraft is never taken for another object - `it7` (reach rule) equals `it6` (sphere) in every count of both sweeps (5,700 light-directions × 6 ranges × 16 positions, `cpu/sw_a_*`); reach vs a brute-force ray cast (25 × 25 parallel rays in the disc, 200 random directions per light, `tools/reach_check.mjs`): never below it (beyond the RMIN housing allowance), median excess 0.26–0.54 m per light, 90th percentile 0.41–2.0 m |
| F3 minor | near self-occlusion edges the drawn share departs from the ray-cast truth by up to ~0.5, steadily; 15.10 called the residual "dim" | two causes, separated this round: **(a)** the recheck's SF50 "hidden lamps drawn" (strobes 0.44 / 0.55) are mostly the truth's own sampling: a flat SF50 lamp patch (strobe h = 131 × 20 × 10 mm) seen nearly edge-on meets 1–8 of the truth's 121 rays, which read 0 / 0.25 / 1; with 61 × 61 rays the same directions read 0.24–0.52, where the table (its 12 × 12 re-cast over the patch's own outline) reads 0.38–0.47 (`tools/dbg_dir2.mjs`); **(b)** the rest is the bilinear 2.8° grid at sharp edges (an occluder metres away: the cabin roof for a tip strobe) and at **thin occluders** narrower than a cell as seen from the lamp (an edge-on stabilizer, an antenna, the nose leg: the grid never resolves them; found after the resume by the dense check below), steady at every sub-pixel position | **no change to the table**: measured and not taken - finer grids (`tools/grid_exp7.mjs`, same truth for all): 128 × 128 (1.4° rows) and 256 × 128 (1.4° cells) against today's 128 × 64, 300 random directions per light at 150 m: PC-12 strobes max |table − truth| 0.67 / 0.75 → 0.50 / 0.44 (128 × 128) → 0.54 / 0.87 (256 × 128), directions off by > 0.25 (of 300) 5 / 5 → 1 / 4 → 1 / 4, landR 5 → 0 → 0, the other PC-12 lights and every SF50 light within ±2 directions (SF50 strobes 0.31–0.36 at every grid: their residual is not the grid); table time (Node, this machine under load, two runs) PC-12 +52–56 % / +183 %, SF50 +38–74 % / +144–223 % (e.g. PC-12 6.5 → 9.8 → 18.2 s), the atlas 2× / 4× (64 / 128 KB per lamp, 19 lamps = 2,432 rows at NE 128, above the 2,048 a WebGL2 device must support) - a small gain at near double the load time, while the placeholder is shown; a "conservative minimum" for the hidden side moves the error onto visible lamps near every edge (dimmed or hidden: R1's failure mode). **15.10 corrected**: the residual is stated per light (table below) instead of "dim" | **per light at 120 and 250 m** (the table decides; both ranges alike), `cpu/sw_a_*` with the corrected truth, cell = largest \|drawn − truth\| / directions (of 300) off by more than 0.25 / hidden lamps (truth 0) drawn (largest value) / lamps seen ≥ 50 % drawn more than 0.25 below their share: **PC-12** navL 0.18 / 0 / 1 (0.04) / 0, navR 0.15 / 0 / 1 (0.07) / 0, tail 0.20 / 0 / 0 / 0, beaconTop 0.18 / 0 / 0 / 0, beaconBot 0.34 / 1 / 1 (0.34) / 0, strobeL 0.49 / 2 / 2 (0.49) / 0, strobeR 0.19 / 0 / 2 (0.02) / 0, landL 0.34 / 1 / 2 (0.34) / 0, landR 0.27 / 1 / 2 (0.03) / 0, taxi 0.46 / 1 / 2 (0.05) / 0; **SF50** navL 0.36 / 4 / 0 / 1, navR 0.31 / 4 / 1 (0.20) / 2, tail and strobeTail 0.17 / 0 / 0 / 0, strobeL 0.33 / 4 / 0 / 2, strobeR 0.38 / 6 / 0 / 1, landL 0.25 / 0 / 0 / 0, landR 0.31 / 1 / 0 / 0, taxi 0.16 / 0 / 2 (0.02) / 0 (the truth itself scatters by ~0.1 at 11 × 11 rays) [round 3,
15.12: these figures and the truth were of the raw rest geometry; against the DRAWN pose (the SF50 nose doors open with the gear
down) the SF50 taxi light's largest error was 0.96 - fixed there, restated with the final tree]. **Every direction** (after the resume: `out/od4_it6r2b/tools/dense_err.mjs`, `cpu/dense_err_*.json`; the shipped table as the shader reads it against a 512 × 256 table of the same estimator, 0.7° cells, at each of its 131,072 cell centres, weighted by solid angle; `dense_check.mjs`: at each light's worst direction the independent ray cast above, at 150 m, confirms the PC-12 values, e.g. beaconBot el −8.8° az 0.4° truth 0.00, drawn 0.88): the 300-direction sample understated the largest errors. **PC-12**, largest |drawn − truth| navL / navR 0.40, tail 0.50, beaconTop 0.44, beaconBot 0.88, strobeL / strobeR 0.99, landL / landR 0.95, taxi 0.80; directions off by more than 0.25: 0.07–1.1 % of the sphere per light (within ±15° of the aircraft's horizontal, where ground cameras sit: 0.27–3.4 %), more than 0.5: 0–0.23 % (ground band 0–0.87 %); hidden lamps drawn above 0.25: 0.07–1.1 % of each light's hidden directions (ground band 0.25–4.7 %, the taxi light the most); seen lamps (≥ 0.5) drawn more than 0.25 below their share: 0–1.3 % (ground band 0–3.4 %, largest 0.93). The largest errors are thin occluders: the stabilizer seen edge-on 10 m in front of a tip strobe (el 14°, az ±139°: drawn 0.99, truth 0), an antenna 4.3 m in front of a landing light (0.95), the nose leg 4.5 m in front of the belly beacon from ahead and below (0.88), the far wing and winglet edge-on 8 m in front of the taxi light (0.80); then sharp edges (the recheck's bank pass: strobeL across the cabin roof 0.49–0.73 for a truth of 1.0). **SF50**: the fine table's own estimator (4 × 4 rays, 12 × 12 for a lamp nearly edge-on) is off by up to 0.4 on its flat lamp patches (at the worst directions the ray cast reads the strobes 0.67 where the fine table says 0.25, the landing lights 0.38–0.42 for 1.0; the drawn value is within 0.15 of the ray cast there except navL / navR from nearly overhead, 0.24 for 0.57), so its dense maxima (0.23–0.63) are upper bounds and the sample above stands (largest 0.16–0.38). So: steady at every sub-pixel position and never blinking, but not "dim": in a narrow band of directions behind a thin occluder a hidden PC-12 lamp is drawn at up to full brightness (it does not wink out for the frame or two in which the occluder passes over it), and near a sharp edge a seen lamp can be drawn dimmer, by up to ~0.9 in the worst cell. With the recheck's 11 × 11 truth the SF50 strobes showed 13–14 hidden directions drawn (up to 0.55); with the corrected truth 0 |

**What the sweeps show (CPU, `out/od4_it6r2/cpu/sw_a_*`, it7 = this tree).** No regression of R1–R3: for both types and at
every range (25–250 m) 0 blinking directions of a lamp seen ≥ 50 %, 0 positions hiding such a lamp, 0 lamps hidden at every
position; false hides (≥ 25 % seen, drawn 0 somewhere) PC-12 0, SF50 1–2 (25–35 m: the near range, iteration 5's test there);
hidden lamps drawn somewhere PC-12 17–20, SF50 6 of ~5,700 light-directions (with the recheck's 11 × 11 truth and the rest
blades, `out/od4_rc6_1/cpu/sw_a_*` it6: SF50 strobes alone 13–14 each). The PC-12 taxi light, blade-free truth: 0 blinking,
0 false hides, hidden directions drawn 3–4 (largest 0.02–0.05).

**GPU, regression checks.** The iteration-5 recheck's R1 range jobs (`od4f_rc2/jobs_range*.json`, four sub-pixel positions
each; `gpu/range_after/`, `range80_after/`, `gpu/range_sheet.jpg`) read exactly iteration 6's values: bot150a 0.766–0.770, bot150b
0.619–0.624, bot80c 0.766–0.770, strR150 0.838–0.850, strR80 0.889–0.890, bot80a / b 0.979–0.981 / 0.936–0.938, bot300lo 1.0, and
the two iteration-5 false hides tail150 0.502 / navL150 0.416 at every position (CPU truth 0.49 / 0.38; the CPU replica gives
0.502 / 0.416 at the same cameras, `tools/dbg_eye.mjs`). The bank pass (`seq/bank150_PC12`, the recheck's path) is frame for
frame identical to iteration 6 (strobeL across the cabin roof 0.49–0.73 in 15 frames whose truth is 1.0: F3's residual,
unchanged). **Posed movers** (`gpu/jobs_posed.json`, `gpu/posed_after/`): the reach is a bound of the aircraft at rest, so a moved part beside a lamp's line of sight could be taken for another object. The ten R1 range cameras above (80 / 150 / 300 m, first sub-pixel position) with flaps 40°, the gear at 0.5 (in transit), both, and full control deflection (roll, pitch, yaw 1): all 40 posed probes equal their rest values (beaconBot 0.624–1.000, tail 0.502, navL 0.416, strobeR 0.838 / 0.889) - at these cameras no moved part comes within the taps' 0.5 m cylinder beyond reach + 0.3 m. Not shown: a posed part that does (open item below).

**Tests**: `node tools/models/test_models.mjs` → **112 PASS, 13 KNOWN, 0 FAIL**, 4 INFO (final tree after the resume,
`out/od4_it6r2b/test_models_final2.txt`; the first run after the resume failed one provenance check on a raster-reading token
(a number followed by the pixel unit) this section had used, reworded; 15.10: 107 PASS). The proposed patch `out/pc12_look_it4/test_models_it4_checks.patch` no longer applies and is not needed: its
checks (G1–G4) were applied with iteration 5's patch in iteration 6 and are in the file (updated since). New / changed checks:
the propeller blades are not in the tables (PC-12: 29,640 blade triangles left out, all of them; SF50: none) and the PC-12
taxi light's table is ≥ 0.9 at el 2° az ±16°, el 2° az −14°, el −2° az 18° / −16°, el 6° az ±12° (it is 1.00 at each; with the
rest blades 0.00–0.22); the reach channel is an upper bound of the aircraft's own surfaces in front of each lamp (an
independent ray cast without BVH, 81 parallel rays in the RHO disc, 16 directions per light: PC-12 160 / 160, SF50 135 / 135,
mean excess 0.76 / 0.47 m); the shader's external taps use the reach (`LENS_RHO` = `LAMPVIS.RHO`, `LENS_XM` ≥ `LAMPVIS.RMIN`, the
tap threshold); the independent ray cast of the table check leaves the blades out as the tables do (mean |table − ray cast|
PC-12 0.022, SF50 0.058, unchanged). **`python3 -I -B tools/check_airport.py`** → **RESULT: ALL HARD CHECKS PASSED**
(`out/od4_it6r2/check_airport.txt`; final tree after the resume: again ALL HARD CHECKS PASSED, `out/od4_it6r2b/check_airport.txt`). **App smoke test** (after the resume, `out/od4_it6r2b/tools/app_smoke2.mjs`, `app/`, looked at): the live app (`live.html`, snapshot mode) on a local recorded pack (gitignored) at an instant when a PC-12 taxis, the environment at night (`?t=`): `loadModel` computed the PC-12's tables in the app, the atlas holds them (4 bands: the lights drawn), the depth copy runs, and from the app's follow camera at 45 and 150 m the starboard nav light is drawn (the port one is behind the fuselage, the tail light faces away); 0 console errors (15.10's smoke run had no detailed aircraft in view).

**Load cost**: the reach adds ~0.9 s of splatting per PC-12 (profile: `reachSplat` 0.89 of 4.3 s) and ~0.7 s per SF50; the
tables now take 4.7–6.3 s (PC-12) and 7.9 s (SF50) in the dev page on this machine under load (the recheck's runs of
iteration 6: 4.0–4.2 s PC-12), before the drawable leaves its placeholder. The BVH walk now visits the near child first
(identical tables, a few per cent faster). **Docs stills** (`out/od4_it6r2/stills/`, the jobs of 15.10, the last two rendered after the resume; compared with the committed ones by `out/od4_it6r2b/tools/docs_cmp7.py`, sheets `out/od4_it6r2b/docs_cmp/docs_sheet{1,2,3}.jpg`, looked at): the nine PC-12 stills, the twelve SF50 day stills and the SF50 dusk still render the same (mean |difference| ≤ 0.041 sRGB levels, at most 5 pixels off by more than 24: viewer_sf50_front, a seam), so `docs/phase3/` and its captions are unchanged this round.

**Files changed in this round**: `js/aircraft/glb.js` (`lampTables`: blades left out, `bladeTris`, `NA` / `NE` options, the
reach channel - `reachVoxels`, `reachSplat`, `LAMPVIS.RHO` / `VOX` / `VS` / `RMIN`; `lampVisReach`; the BVH's split axis and
near-child-first walk; header), `js/shaders/sprites.js` (`lampTable` returns the reach, the external-occluder taps against
reach + `LENS_XM`, `LENS_XM` / `LENS_RHO` / `LENS_TXL`, header), `tools/models/test_models.mjs` (the checks above), this file
(sections 3, 8, 9, 15.10 annotations, 15.11). Not changed: `js/scene.js` (the atlas already carried RGBA), `js/aircraft/
detailed.js`, `models.js`, `kinematics.js`, `js/renderer.js`, `js/gl.js`, `dev/model*`, the glb files, `js/live/**`,
`js/video/**`.

**Open / not verified (round 2)**: the reach is a bound for the aircraft **at rest** (gear down, flaps 0, controls neutral,
doors closed): a moved part beside a lamp's line of sight and more than reach + 0.3 m in front of it is taken for another
object (POSED) [round 3, 15.12: the tables and the reach are now of the drawn gear-down / gear-up pose, the reach covers the gear
in transit and the tabulated flap settings, and the flaps have their own tables; the belly-beacon case the recheck found is
fixed there]; an occluder within reach + 0.3 m in front of a lamp is still not seen while the lamp is sub-pixel (in grazing
directions the reach is metres: the PC-12 taxi light from ahead 2.7 m); beyond ~460 m (fov 45° / 1080 lines) the outer taps
fall back to the bounding sphere [round 3, 15.12: corrected - the corner taps start to fall back at ~370 m there (complete at
~460 m), at ~195 m on a 720-line canvas at 55°; the formula and the per-light blind-window shares are in 15.12]; with a slowly turning, drawn propeller (below `PROP_BLUR[1]`: engine start / stop) a lamp
behind the blades is drawn through them wherever the reach covers the blades (the taxi light from ahead; iteration 6 hid it
in fixed directions whatever the rotor angle); the tables' residual near edges and behind thin occluders is as stated above (F3: on the PC-12 up to 0.99 of full brightness for a
hidden lamp in narrow bands of directions, over every direction; no grid change); RHO, VOX,
VS, RMIN and `LENS_XM` are inferred. Laptop GPU frame time still not measured.

### 15.12 OD4 iteration 6, round 3 (recheck of 2026-11-27, findings F1–F5): dispositions
The recheck of round 2 (its tools, renders and measurements `out/od4_rc6_2/`, gitignored) found the five issues below.
**Before** = round 2 as handed over (copies of its runtime files in `out/od4_it6r3/head/`), **after** = this tree; tools,
renders and measurements of this round: `out/od4_it6r3/` (gitignored). **Truth** = the recheck's own ray cast
(`out/od4_rc6_2/tools/rc2lib.mjs` `truthRC`: 21 × 21 perspective rays over the lamp's support, 61 × 61 when fewer than 60
meet the lamp; the model posed by the app's own `Kinematics.pose` with the state of the run, no propeller blades) - the
DRAWN pose, which none of round 2's sweeps, tests or tables used (F1). **CPU replica** of the new shader:
`out/od4_it6r3/tools/lens8.mjs` `it8Test` (round 2's `it7Test` plus the flap tables and the F2 rule; `IT8_OLD` = round 2's
rule on this round's tables); sweeps `tools/sw8.mjs` on the recheck's own seeded direction sets (500 uniform + 250 within
±12° of the aircraft's horizontal per light, 16 sub-pixel camera positions, fov 45° / 1080 lines, the app rig's near plane),
so every before / after pair below is the same directions, cameras and truth. **GPU**: the recheck's tools and jobs unchanged
(`out/od4_rc6_1/tools/gpu_rc.mjs` lens probe and on / off renders, `out/od4_rc6_2/tools/seq_rc2.mjs` sequences); dev viewer,
1920 × 1080, night (2026-11-14 05:00Z), neutral pad. The GPU equals the CPU replica in every value compared this round (below).
Every image was looked at.

| # | finding | root cause | fix (file) | result (before → after) |
|---|---|---|---|---|
| F1 major | the SF50 taxi light was drawn through its own open nose-gear doors, at every range (2.5–400 m): the table said "seen" (0.87–0.92) where the drawn door hides the lamp completely, and from the ground band nearly head-on it drew ~2× the seen share; 15.11 gave its largest error as 0.16, against the drawn pose 0.96 | `js/aircraft/glb.js` `lampTables` ray-cast the **raw glTF rest geometry**, where the SF50's nose doors are closed. In every drawn gear-down state they stand open: `js/aircraft/kinematics.js` `gearSequence` `doorDown` = 1 with the gear down and the doors' pivot `seq: 'down'` (the SF50 builder: "open whenever the gear is down", AFM Fig 1-1 shows them open) - correct, and unchanged. The doors lie within the reach + 0.3 m, so vExt did not see them, and at near range the floor tq × n(T) kept the table's value although v5 saw the door. Round 2's sweeps, the test's ray cast and the 15.11 F3 figures used the same rest geometry, so none of them could see it; the gear-up channel likewise dropped the gear parts instead of posing them | **the tables are of the DRAWN pose** (`lampTables`; glb.js now imports kinematics.js): occluders posed by `Kinematics(model).pose(...)` - the airframe and the gear with `{ gear: 1 }` for channel 0 (gear down), the gear with `{ gear: 0 }` for channel 1 (gear up: legs retracted, doors shut; was "without the gear parts"), the lamp placed with its mover's gear-down pose (every lamp of both types is at rest there); the blade exclusion kept; the reach (channel 3) an upper bound over the gear down / up / in transit (0.5) and the flaps (F3). The near floor needs no change: with a table that sees the door, T ≈ 0 behind it and the floor with it. **Also found**: the "surface behind the lamp" rule of a lamp under a clear cover looked 80 m back, so a ray through the SF50 tip landing light's cover that met the main gear legs 3 m behind counted as a view of the lamp with the gear down and not with it up (gear-down / gear-up 0.38 / 0.11 where the ray cast sees 0.08); it now looks `LAMPVIS.BACK` = 1 m behind, the recheck truth's own rule (the SF50 tables change; the PC-12 lamps have no cover). `tools/models/test_models.mjs`: the independent ray cast is of the drawn gear-down pose; new checks - the gear-up and flap tables against an independent ray cast of that pose, the reach as read in those poses an upper bound of the posed aircraft, the SF50 taxi light ≤ 0.1 at the recheck's three cameras | **CPU** (`out/od4_rc6_2/tools/sf50taxi.mjs`, 750 directions at 150 m): hidden in the drawn pose but drawn **44 → 0**; grid (`tools/grid8.mjs`, 2°, el −10..40°, az ±90°, `cpu/grid8_SF50_taxi_gear1_final.txt`): hidden cells drawn above 0.25 **792 of 1,252 → 0**, seen cells drawn more than 0.25 below 0, largest error 0.16; F3 check (`cpu/f3check_SF50.json`, 2,000 + 1,000 directions, 150 m): SF50 taxi off by more than 0.25 **20.9 % → 0.0 %** of the sphere (95 % interval 0.0–0.2 %), **32.6 % → 0.0 %** of the ground band, largest error **0.96 → 0.21**; the full sweep (below): SF50 hidden lamps drawn above 0.25 at 10–400 m 41–45 → **0**, at 5–30 m 44–50 → **0**. **GPU** (the recheck's `jobs_sf50taxi.json`; `gpu/sf50taxi/`, `cmp.json`): probe 0.875–0.901 → **0.000 in all 18 jobs** (el 13.1° az 18.5° at 150 m × 4 sub-pixel positions, 40 m × 4, 12 m and 4 m; el 16.5° az 38.5° and el 8° az 16.2° at 150 m × 4), peak added sRGB 252–255 → **0**; the crops (`gpu/sf50taxi_crops_sel.jpg`, looked at) show the open door and no glow. Re-run after the cover-rule change (`gpu/sf50taxi_final/`): the first position of each case and a 4 m close-up, **0.000 in all 6**, the GPU equal to the CPU replica. **Temporal** (the recheck's `curve150_SF50` path, 30 frames, `seq/curve150_SF50`): the taxi light drawn 0.50–1.00 for a truth of 0.42–0.97, largest \|drawn − truth\| **0.09**, **0 of 30** frames off by more than 0.25 (round 2, the recheck's 90-frame run of the same arc: drawn 0.875–1.00 for the same truth range, 76 of 90 frames off by more than 0.25, largest 0.56); 0 flicker for every light |
| F2 major | at 10–30 m partly seen lamps (10–50 %) blinked with the sub-pixel position on a moving aircraft - mostly the SF50: tip strobes fully on / off, landing and nav lights swinging 0.3–0.7; 15.10's "never to off" held only for lamps seen ≥ 50 % and no jitter amplitude was reported | (a) the blend radius r = min(\|h·pr\|, \|h·pu\|) was the lamp ellipsoid's support along the screen x / y axes, not the minor half-axis of its projected ellipse: for the thin SF50 strobe patch (131 × 20 × 10 mm) seen tilted r was 3.8–4.7 pixels for a 0.7–0.9 pixels sliver, so w = 0 and iteration 5's v5 alone decided, its 3 × 3 taps straddling the sliver (0 or 1); (b) the near floor tq × n(T) is ~0 for T < 0.25–0.5, so v5's jitter was unbounded for partly seen lamps | `js/shaders/sprites.js` `lensVisible`: **r = the minor half-axis of the projected ellipse** (√ of the smaller eigenvalue of Σ h_i² p_i p_iᵀ, p_i = (a_i·R, a_i·U)) **× the table's share T** - the width of the SEEN part of the lamp in the worst case (a sliver along its long axis): one depth sample per pixel cannot resolve a seen part narrower than ~1.5 pixels, so the table decides there; and where the table holds (qn), **the depth test is bounded toward the table's value tq = T g vExt**: never below max(tq n(T), tq − `LENS_BM`, tq × `LENS_BLO`), never above tq + `LENS_BM` (`LENS_BM` 0.15, `LENS_BLO` 0.5; round 2's floor kept as the first term). Chosen with the CPU replica over ten variants (`cpu/sw8_nearX_*`: 250 directions × 5–40 m × 16 positions, both types; an exploration on the tables before the cover-rule change below; SF50: r alone still 1–4 on / off at 5–25 m, spreads up to 0.60; r × T alone 1 on / off at 5 m, spreads up to 0.55; the bound alone ±0.25 / ±0.15 on / off at 5–25 m / none, spreads up to 0.48 / 0.33; r × √T + bound ±0.15 0 on / off, 0.33 / 0.30 at 5 / 10 m; r × T + bound ±0.15 the smallest: 0 on / off, largest spread 0.33 at 5 m and ≤ 0.20 from 10 m; its cost on the PC-12: more steady table residuals at 5–15 m, below) [inf] | **CPU, the recheck's direction sets** (`cpu/sw8_near_*`, `sw8_main_*`; tables below, before = the recheck's own sweeps of the round-2 tree): SF50 on / off of lamps seen ≥ 25 % at 5 / 10 / 15 / 20 / 25 / 30 m **8 / 10 / 8 / 7 / 6 / 3 → 0**; light-directions whose drawn value varies by more than 0.25 between sub-pixel positions **1.9 / 3.5 / 3.8 / 3.9 / 3.2 / 2.5 % → 0.1 / 0 / 0 / 0 / 0 / 0 %**, largest spread **0.82 / 0.99 / 1.00 / 1.00 / 0.94 / 1.00 → 0.33 / 0.28 / 0.15 / 0.15 / 0.13 / 0.07** (strobes 1.00 → 0.01–0.02 from 15 m); PC-12 spread > 0.25 0.4–1.4 % → **0**, largest 0.33–0.44 → 0.04–0.27; from 40 m both types ≤ 0.02. **GPU** (the recheck's `jobs_near3_SF50.json`, its four cases × four sub-pixel positions, `gpu/near3_SF50/cmp.json`; the GPU equals the CPU replica in all 16 values): strobeR 15 m (truth 0.35–0.36) **1.000 / 0.004 / 0.004 / 1.000 → 0.270 / 0.269 / 0.267 / 0.267**; strobeL 20 m (truth 0.12) 0.33 / 1 / 1 / 1 → **0.206–0.207**; landL 25 m (truth 0.25) 0.25 / 0.001 / 0.66 / 0.33 → **0.217 × 4**; navR 20 m (truth 0.49) 0.291–0.292; the crops (`gpu/near3_sheet.jpg`, looked at) show the same disc at every position. **Temporal** (the recheck's `crawl15_SF50`: an SF50 taxiing at 1 m/s, the camera ~15 m from the right tip strobe, 40 frames at 30 fps; `seq/crawl15_SF50_truth.txt`): strobeR (truth 0.33–0.37 in every frame) drawn **0–0.5 with 8 on / off flickers → 0.25–0.28, 0 flickers, 0 jumps**; landL (truth 0.49–0.54) 0.33–0.75 with 2 jumps → **0.36–0.39, 0 jumps**; the taxi light (truth 0.05, F1) 0.875 → 0.01–0.04. At 25 m (`crawl25_SF50`, new, the same path with the camera 27 m away): 0 flicker and 0 jumps for every light; strobeR 0.46–0.50 for a truth of 0.47–0.49, landL 0.44–0.51 for 0.60–0.64 |
| F3 minor | with flaps 40 the deployed Fowler flaps hide the PC-12 belly beacon from beside the aircraft at low elevation (az ±72–90°, el −8…+5°: a runway-side camera on a landing PC-12), but the flaps-0 table drew it at 0.76–1.0, and the deployed flap lay within reach + 0.3 m | the tables were at flaps 0 | **flap tables** (`js/aircraft/glb.js` `lampTables`, `lampFlapSettings`, `lampFlapX`, `lampVisState`): per lamp, one more table per tabulated flap setting - the smallest and the largest non-zero setting of the model's flap pivots, PC-12 15 / 40, SF50 15 / 39 (the take-off and landing settings `js/live/aircraft.js` flies) - ray cast in the same pass (the flap parts posed per setting, small BVHs); kept only for a lamp whose seen share some setting changes by more than 3 / 255 (PC-12: 7 of 10 lamps - the beacons, strobes, landing and taxi lights; SF50: the taxi light), 32 KB each. `js/scene.js` places a lamp's flap tables in consecutive atlas bands (`LampVisAtlas.bandRun`; a run that does not fit is dropped and the sprite keeps its flaps-0 table) and packs the first band and the flap position into iL5.z / iL5.w; `js/aircraft/detailed.js` `lampWorld` passes them (`lampFlapX` of the drawable's flap angle: 0 / 1 / 2 at 0 / 15 / 40°, piecewise linear, PC-12 30° = 1.6 [inf]); `js/shaders/sprites.js` `lampTable` mixes the shares and the farthest occluder linearly and takes the larger reach of the two tables (each a bound for its own setting). The reach of a lamp's flaps-0 table covers the flaps at rest, each flap table its own setting (a lamp without flap tables: every setting) | **CPU, the recheck's grid** (`tools/grid8.mjs`, 1°, el −20..10°, az 0..180°, flaps 40, `cpu/grid8_PC12_beaconBot_flaps40.txt`): hidden belly-beacon cells drawn above 0.25 **137 → 23** of 1,044 (without / with the flap tables), largest error 1.0 → 0.9 (a few cells at the flap's edge); **posed sweeps** (the recheck's `posLand` / `posClimb` states and direction sets, 80 / 150 / 300 m, `cpu/sw8_pos*`): PC-12 flaps 40 hidden lamps drawn above 0.25 **107 → 12** per range (beaconBot 5 → 1, landL 46 → 0–1, landR 46 → 1: the landing lights hidden from behind by the flaps), flaps 15 + gear up 43 → 9; SF50 0 → 0; no blinking and spread ≤ 0.02 before and after. **GPU** (the recheck's `jobs_posed_PC12.json`, `gpu/posed_PC12/cmp.json`, GPU = CPU replica): flaps 40, el 2° az 77° at 150 m **0.761–0.764 → 0.000**, el −3° az 83° at 80 m **1.000 → 0.000** (truth 0 at all positions); control flaps 0, el 0° az 80° 0.916–0.917 (truth 0.95), unchanged. Tests: the belly beacon's flap tables ≤ 0.15 at those two cameras with flaps 40 and 0.918 at the control |
| F4 minor | the external-occluder blind window [0, reach + 0.3 m] is large for the PC-12 in the ground band and 15.11 described it only qualitatively; the bounding-sphere fallback starts earlier than "beyond ~460 m" | the fallback distance was quoted for the edge of the corner tap's full fallback, not its start; the window was not measured per light | **documented** (below, the `js/shaders/sprites.js` header and 15.11 corrected): the per-light shares of seen directions with a window of 3 m or more, and the fallback distances with their scaling. Not done: telling the aircraft's own pixels apart in the depth copy (an aircraft id) would remove the window, but the near pass is multisampled and its resolve averages an id across a silhouette's samples - where a sub-pixel lamp's taps fall - and the aux target's four channels are in use (distance, motion, alpha); a renderer change beyond this round [inf] | per light below; the round-3 reach (per pose) leaves the flaps-0 window as round 2's: PC-12 ground band 16–60 % of seen directions have a window ≥ 3 m (belly beacon 59.9 %), whole sphere 4–27 %; SF50 ≤ 6.7 % |
| F5 minor | 15.10's R3 tables were of the round-1 tree (rest blades in tables and truth); the final tree's figures at the R3 ranges were not in the docs; the F3 shares were quoted without their sampling uncertainty | the round-2 sweeps used a different direction set and ranges | the final tree's figures at 5–400 m with a jitter column (below; 15.10's tables annotated as superseded), on the recheck's own direction sets and truth, before (= the recheck's runs of the round-2 tree) → after; the F3 shares with Wilson 95 % intervals | below |

**The final tree at 5–400 m (F2, F5).** CPU, the recheck's direction sets and truth (500 uniform + 250 ground-band directions per
light, 16 sub-pixel positions, fov 45° / 1080 lines; 5–30 m seeds 4343 / 4444, 10–400 m seed 4242), before = the recheck's own
sweeps of the round-2 tree (`out/od4_rc6_2/cpu/sw_near_*`, `sw_main_PC12`, `sw_main2_SF50`), after = `cpu/sw8_near_*`,
`cpu/sw8_main_*` (variant `it8`; `tools/mk15.py`). Per light and range: *on / off* = directions of a lamp seen ≥ 25 % drawn
below 0.02 at some position and above 0.25 at another; *hidden drawn* = lamps the truth sees 0 % of drawn above 0.25 somewhere;
*false hides* = lamps seen ≥ 25 % drawn 0 somewhere; the **jitter** = the largest sub-pixel spread (max − min over the 16
positions) of the light at that range. These supersede 15.10's R3 tables.

**PC12, 5–30 m** (cell: on / off of a lamp seen ≥ 25 % / hidden lamps drawn > 0.25 / false hides / jitter = largest sub-pixel spread; before → after)

| light | 5 m | 15 m | 20 m | 25 m | 30 m |
|---|---|---|---|---|---|
| navL | 0→0 / 0→0 / 0→0 / 0.33→0.27 | 0→0 / 0→1 / 0→0 / 0.43→0.09 | 0→0 / 0→1 / 0→0 / 0.41→0.02 | 0→0 / 0→0 / 0→0 / 0.28→0.01 | 0→0 / 0→0 / 0→0 / 0.20→0.01 |
| navR | 0→0 / 0→0 / 0→0 / 0.33→0.26 | 0→0 / 0→0 / 0→0 / 0.44→0.09 | 0→0 / 0→0 / 0→0 / 0.43→0.04 | 0→0 / 0→0 / 0→0 / 0.28→0.04 | 0→0 / 0→0 / 0→0 / 0.19→0.04 |
| tail | 0→0 / 0→0 / 0→0 / 0.33→0.15 | 0→0 / 0→0 / 0→0 / 0.03→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| beaconTop | 0→0 / 0→0 / 0→0 / 0.33→0.22 | 0→0 / 0→0 / 0→0 / 0.32→0.08 | 0→0 / 0→0 / 0→0 / 0.20→0.01 | 0→0 / 0→0 / 0→0 / 0.07→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| beaconBot | 0→0 / 1→3 / 0→0 / 0.28→0.21 | 0→0 / 3→4 / 0→0 / 0.19→0.03 | 0→0 / 3→3 / 0→0 / 0.02→0.02 | 0→0 / 3→3 / 0→0 / 0.02→0.02 | 0→0 / 2→2 / 0→0 / 0.02→0.02 |
| strobeL | 0→0 / 0→0 / 0→0 / 0.33→0.17 | 0→0 / 3→4 / 0→0 / 0.29→0.05 | 0→0 / 4→4 / 0→0 / 0.23→0.02 | 0→0 / 4→4 / 0→0 / 0.15→0.02 | 0→0 / 4→4 / 0→0 / 0.05→0.02 |
| strobeR | 0→0 / 0→0 / 0→0 / 0.22→0.15 | 0→0 / 5→6 / 0→0 / 0.29→0.05 | 0→0 / 6→6 / 0→0 / 0.22→0.02 | 0→0 / 5→5 / 0→0 / 0.13→0.02 | 0→0 / 5→5 / 0→0 / 0.03→0.02 |
| landL | 0→0 / 0→2 / 0→0 / 0.33→0.22 | 0→0 / 3→3 / 0→0 / 0.04→0.02 | 0→0 / 3→3 / 0→0 / 0.02→0.02 | 0→0 / 3→3 / 0→0 / 0.02→0.02 | 0→0 / 3→3 / 0→0 / 0.02→0.02 |
| landR | 0→0 / 0→1 / 0→0 / 0.33→0.11 | 0→0 / 2→2 / 0→0 / 0.05→0.02 | 0→0 / 2→2 / 0→0 / 0.02→0.02 | 0→0 / 2→2 / 0→0 / 0.02→0.02 | 0→0 / 2→2 / 0→0 / 0.02→0.02 |
| taxi | 0→0 / 0→0 / 1→1 / 0.33→0.21 | 0→0 / 1→4 / 0→0 / 0.33→0.11 | 0→0 / 1→3 / 0→0 / 0.33→0.05 | 0→0 / 3→3 / 0→0 / 0.22→0.01 | 0→0 / 3→3 / 0→0 / 0.09→0.01 |

| PC12, all lights | 5 m | 15 m | 20 m | 25 m | 30 m |
|---|---|---|---|---|---|
| light-directions | 7284 → 7284 | 7500 → 7500 | 7500 → 7500 | 7500 → 7500 | 7500 → 7500 |
| on / off (seen ≥ 25 %) | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| blinking (seen ≥ 50 %, drawn 0 somewhere) | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| light-directions with a sub-pixel spread > 0.25 | 0.4 % → 0.0 % | 1.4 % → 0.0 % | 0.6 % → 0.0 % | 0.1 % → 0.0 % | 0.0 % → 0.0 % |
| jitter (largest sub-pixel spread) | 0.33 → 0.27 | 0.44 → 0.11 | 0.43 → 0.05 | 0.28 → 0.04 | 0.20 → 0.04 |
| hidden lamps drawn > 0.25 | 1 → 6 | 17 → 24 | 19 → 22 | 20 → 20 | 19 → 19 |
| false hides (seen ≥ 25 %, drawn 0) | 1 → 1 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| mean abs error | 0.035 → 0.030 | 0.032 → 0.025 | 0.029 → 0.025 | 0.027 → 0.025 | 0.026 → 0.025 |

**PC12, 10–400 m** (cell: on / off of a lamp seen ≥ 25 % / hidden lamps drawn > 0.25 / false hides / jitter = largest sub-pixel spread; before → after)

| light | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|
| navL | 0→0 / 0→0 / 2→2 / 0.42→0.14 | 0→0 / 0→0 / 2→2 / 0.03→0.01 | 0→0 / 0→0 / 2→2 / 0.01→0.01 | 0→0 / 0→0 / 2→2 / 0.01→0.01 | 0→0 / 0→0 / 2→2 / 0.01→0.01 | 0→0 / 0→0 / 2→2 / 0.01→0.01 |
| navR | 0→0 / 0→1 / 0→0 / 0.33→0.15 | 0→0 / 1→1 / 0→0 / 0.03→0.01 | 0→0 / 1→1 / 0→0 / 0.01→0.01 | 0→0 / 1→1 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| tail | 0→0 / 2→2 / 0→0 / 0.32→0.05 | 0→0 / 2→2 / 0→0 / 0.01→0.01 | 0→0 / 2→2 / 0→0 / 0.01→0.01 | 0→0 / 2→2 / 0→0 / 0.01→0.01 | 0→0 / 2→2 / 0→0 / 0.01→0.01 | 0→0 / 2→2 / 0→0 / 0.01→0.01 |
| beaconTop | 0→0 / 0→0 / 0→0 / 0.33→0.15 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| beaconBot | 0→0 / 0→1 / 0→0 / 0.33→0.14 | 0→0 / 1→1 / 0→0 / 0.01→0.01 | 0→0 / 1→1 / 0→0 / 0.01→0.01 | 0→0 / 1→1 / 0→0 / 0.01→0.01 | 0→0 / 1→1 / 0→0 / 0.01→0.01 | 0→0 / 1→1 / 0→0 / 0.01→0.01 |
| strobeL | 0→0 / 4→7 / 0→0 / 0.33→0.14 | 0→0 / 11→11 / 0→0 / 0.02→0.02 | 0→0 / 11→11 / 0→0 / 0.02→0.02 | 0→0 / 11→11 / 0→0 / 0.02→0.02 | 0→0 / 11→11 / 0→0 / 0.02→0.02 | 0→0 / 11→11 / 0→0 / 0.02→0.02 |
| strobeR | 0→0 / 0→0 / 0→0 / 0.30→0.15 | 0→0 / 5→5 / 0→0 / 0.01→0.01 | 0→0 / 5→5 / 0→0 / 0.01→0.01 | 0→0 / 5→5 / 0→0 / 0.01→0.01 | 0→0 / 4→4 / 0→0 / 0.01→0.01 | 0→0 / 4→4 / 0→0 / 0.01→0.01 |
| landL | 0→0 / 2→8 / 0→0 / 0.27→0.07 | 0→0 / 8→8 / 0→0 / 0.02→0.02 | 0→0 / 8→8 / 0→0 / 0.02→0.02 | 0→0 / 8→8 / 0→0 / 0.02→0.02 | 0→0 / 8→8 / 0→0 / 0.02→0.02 | 0→0 / 8→8 / 0→0 / 0.02→0.02 |
| landR | 0→0 / 3→6 / 1→1 / 0.28→0.07 | 0→0 / 5→5 / 1→1 / 0.02→0.02 | 0→0 / 4→4 / 1→1 / 0.02→0.02 | 0→0 / 4→4 / 1→1 / 0.02→0.02 | 0→0 / 4→4 / 1→1 / 0.02→0.02 | 0→0 / 4→4 / 1→1 / 0.02→0.02 |
| taxi | 0→0 / 1→4 / 0→0 / 0.33→0.16 | 0→0 / 3→3 / 0→0 / 0.01→0.01 | 0→0 / 3→3 / 0→0 / 0.01→0.01 | 0→0 / 3→3 / 0→0 / 0.01→0.01 | 0→0 / 3→3 / 0→0 / 0.01→0.01 | 0→0 / 3→3 / 0→0 / 0.01→0.01 |

| PC12, all lights | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|
| light-directions | 7441 → 7441 | 7500 → 7500 | 7500 → 7500 | 7500 → 7500 | 7500 → 7500 | 7500 → 7500 |
| on / off (seen ≥ 25 %) | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| blinking (seen ≥ 50 %, drawn 0 somewhere) | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 |
| light-directions with a sub-pixel spread > 0.25 | 1.1 % → 0.0 % | 0.0 % → 0.0 % | 0.0 % → 0.0 % | 0.0 % → 0.0 % | 0.0 % → 0.0 % | 0.0 % → 0.0 % |
| jitter (largest sub-pixel spread) | 0.42 → 0.16 | 0.03 → 0.02 | 0.02 → 0.02 | 0.02 → 0.02 | 0.02 → 0.02 | 0.02 → 0.02 |
| hidden lamps drawn > 0.25 | 12 → 29 | 36 → 36 | 35 → 35 | 35 → 35 | 33 → 33 | 33 → 33 |
| false hides (seen ≥ 25 %, drawn 0) | 3 → 3 | 3 → 3 | 3 → 3 | 3 → 3 | 3 → 3 | 3 → 3 |
| mean abs error | 0.037 → 0.029 | 0.026 → 0.026 | 0.025 → 0.025 | 0.025 → 0.025 | 0.025 → 0.025 | 0.025 → 0.025 |

**SF50, 5–30 m** (cell: on / off of a lamp seen ≥ 25 % / hidden lamps drawn > 0.25 / false hides / jitter = largest sub-pixel spread; before → after)

| light | 5 m | 15 m | 20 m | 25 m | 30 m |
|---|---|---|---|---|---|
| navL | 0→0 / 0→0 / 0→0 / 0.33→0.20 | 0→0 / 0→0 / 0→0 / 0.45→0.15 | 0→0 / 0→0 / 0→0 / 0.60→0.11 | 1→0 / 0→0 / 0→0 / 0.46→0.04 | 2→0 / 0→0 / 0→0 / 0.50→0.04 |
| navR | 0→0 / 0→0 / 0→0 / 0.55→0.28 | 0→0 / 0→0 / 0→0 / 0.51→0.15 | 0→0 / 0→0 / 0→0 / 0.53→0.11 | 0→0 / 0→0 / 0→0 / 0.47→0.04 | 0→0 / 0→0 / 0→0 / 0.45→0.01 |
| tail | 0→0 / 0→0 / 0→0 / 0.33→0.14 | 0→0 / 0→0 / 0→0 / 0.27→0.02 | 0→0 / 0→0 / 0→0 / 0.05→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 |
| strobeL | 4→0 / 0→0 / 4→0 / 0.67→0.15 | 3→0 / 0→0 / 3→0 / 1.00→0.02 | 3→0 / 0→0 / 2→0 / 1.00→0.02 | 0→0 / 0→0 / 0→0 / 0.94→0.02 | 0→0 / 0→0 / 0→0 / 1.00→0.02 |
| strobeR | 2→0 / 0→0 / 0→0 / 0.82→0.15 | 2→0 / 0→0 / 1→0 / 1.00→0.01 | 2→0 / 0→0 / 1→0 / 0.97→0.01 | 0→0 / 0→0 / 0→0 / 0.92→0.01 | 0→0 / 0→0 / 0→0 / 0.96→0.01 |
| strobeTail | 0→0 / 0→0 / 0→0 / 0.33→0.14 | 0→0 / 0→0 / 0→0 / 0.26→0.02 | 0→0 / 0→0 / 0→0 / 0.05→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 |
| landL | 0→0 / 0→0 / 2→0 / 0.36→0.33 | 1→0 / 0→0 / 1→0 / 0.66→0.15 | 1→0 / 0→0 / 1→0 / 0.50→0.15 | 2→0 / 0→0 / 0→0 / 0.75→0.12 | 1→0 / 0→0 / 1→0 / 0.60→0.06 |
| landR | 1→0 / 0→0 / 1→0 / 0.46→0.33 | 1→0 / 0→0 / 1→0 / 0.60→0.15 | 1→0 / 0→0 / 1→0 / 0.50→0.15 | 3→0 / 0→0 / 0→0 / 0.50→0.13 | 0→0 / 0→0 / 0→0 / 0.60→0.07 |
| taxi | 1→0 / 44→0 / 0→0 / 0.50→0.16 | 1→0 / 48→0 / 0→0 / 0.37→0.15 | 0→0 / 50→0 / 0→0 / 0.35→0.09 | 0→0 / 50→0 / 0→0 / 0.17→0.03 | 0→0 / 50→0 / 0→0 / 0.05→0.01 |

| SF50, all lights | 5 m | 15 m | 20 m | 25 m | 30 m |
|---|---|---|---|---|---|
| light-directions | 6628 → 6628 | 6750 → 6750 | 6750 → 6750 | 6750 → 6750 | 6750 → 6750 |
| on / off (seen ≥ 25 %) | 8 → 0 | 8 → 0 | 7 → 0 | 6 → 0 | 3 → 0 |
| blinking (seen ≥ 50 %, drawn 0 somewhere) | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| light-directions with a sub-pixel spread > 0.25 | 1.9 % → 0.1 % | 3.8 % → 0.0 % | 3.9 % → 0.0 % | 3.2 % → 0.0 % | 2.5 % → 0.0 % |
| jitter (largest sub-pixel spread) | 0.82 → 0.33 | 1.00 → 0.15 | 1.00 → 0.15 | 0.94 → 0.13 | 1.00 → 0.07 |
| hidden lamps drawn > 0.25 | 44 → 0 | 48 → 0 | 50 → 0 | 50 → 0 | 50 → 0 |
| false hides (seen ≥ 25 %, drawn 0) | 7 → 0 | 6 → 0 | 5 → 0 | 0 → 0 | 1 → 0 |
| mean abs error | 0.079 → 0.046 | 0.079 → 0.042 | 0.073 → 0.043 | 0.070 → 0.043 | 0.066 → 0.043 |

**SF50, 10–400 m** (cell: on / off of a lamp seen ≥ 25 % / hidden lamps drawn > 0.25 / false hides / jitter = largest sub-pixel spread; before → after)

| light | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|
| navL | 0→0 / 0→0 / 0→0 / 0.55→0.15 | 0→0 / 0→0 / 0→0 / 0.20→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 |
| navR | 1→0 / 0→0 / 1→0 / 0.50→0.15 | 0→0 / 0→0 / 0→0 / 0.41→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 |
| tail | 0→0 / 0→0 / 0→0 / 0.42→0.14 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| strobeL | 1→0 / 0→0 / 1→0 / 0.69→0.06 | 0→0 / 0→0 / 0→0 / 0.51→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| strobeR | 2→0 / 0→0 / 2→0 / 0.99→0.04 | 0→0 / 0→0 / 0→0 / 0.47→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 | 0→0 / 0→0 / 0→0 / 0.02→0.02 |
| strobeTail | 0→0 / 0→0 / 0→0 / 0.38→0.14 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| landL | 1→0 / 0→0 / 1→0 / 0.40→0.26 | 0→0 / 0→0 / 0→0 / 0.35→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| landR | 4→0 / 0→0 / 3→0 / 0.50→0.28 | 0→0 / 0→0 / 0→0 / 0.34→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 | 0→0 / 0→0 / 0→0 / 0.01→0.01 |
| taxi | 1→0 / 41→0 / 2→0 / 0.38→0.15 | 0→0 / 45→0 / 0→0 / 0.01→0.01 | 0→0 / 44→0 / 0→0 / 0.01→0.01 | 0→0 / 44→0 / 0→0 / 0.01→0.01 | 0→0 / 44→0 / 0→0 / 0.01→0.01 | 0→0 / 44→0 / 0→0 / 0.01→0.01 |

| SF50, all lights | 10 m | 40 m | 80 m | 150 m | 300 m | 400 m |
|---|---|---|---|---|---|---|
| light-directions | 6747 → 6747 | 6750 → 6750 | 6750 → 6750 | 6750 → 6750 | 6750 → 6750 | 6750 → 6750 |
| on / off (seen ≥ 25 %) | 10 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| blinking (seen ≥ 50 %, drawn 0 somewhere) | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| light-directions with a sub-pixel spread > 0.25 | 3.5 % → 0.0 % | 0.3 % → 0.0 % | 0.0 % → 0.0 % | 0.0 % → 0.0 % | 0.0 % → 0.0 % | 0.0 % → 0.0 % |
| jitter (largest sub-pixel spread) | 0.99 → 0.28 | 0.51 → 0.02 | 0.02 → 0.02 | 0.02 → 0.02 | 0.02 → 0.02 | 0.02 → 0.02 |
| hidden lamps drawn > 0.25 | 41 → 0 | 45 → 0 | 44 → 0 | 44 → 0 | 44 → 0 | 44 → 0 |
| false hides (seen ≥ 25 %, drawn 0) | 10 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |
| mean abs error | 0.082 → 0.044 | 0.062 → 0.044 | 0.060 → 0.044 | 0.060 → 0.044 | 0.060 → 0.044 | 0.060 → 0.044 |

So: no light of either type goes on / off with the sub-pixel position at any range (SF50 before: 3–10 per range at 5–30 m), no
lamp seen ≥ 50 % is hidden anywhere it was not before (the one PC-12 landR direction under the belly, drawn 0.00–0.02 for a
truth of 0.71 at every range, is round 2's: a narrow aperture, steady), the jitter is ≤ 0.33 at 5 m, ≤ 0.28 at 10 m, ≤ 0.15
from 15 m and ≤ 0.02 from 40 m for both types, and the SF50's taxi-light leaks (F1) are gone. **The cost** is on the PC-12 at
5–20 m: hidden lamps drawn above 0.25 at 5 / 10 / 15 / 20 m 1 / 12 / 17 / 19 → **6 / 29 / 24 / 22** (of ~1,700 hidden
light-directions per range): directions where the table is wrong high near an edge (the round-2 F3 residual: strobes and
landing lights in the ground band, drawn 0.24–0.76, steady at every position) and where round 2's depth test, which saw the
lamp hidden, used to decide - with r × T the table decides a lamp whose seen part is under ~1.5 pixels. From 25 m the counts are
round 2's (19–36 per range, the table residual of 15.11). The mean absolute error falls at every range (PC-12 0.037 → 0.029 at
10 m, SF50 0.082 → 0.044).

**F3 residuals restated with their sampling uncertainty (F5)** (`tools/f3check.mjs` = the recheck's, on this tree; 2,000 uniform + 1,000
ground-band directions per light at 150 m, the table regime: drawn = T × smoothstep(0.04, 0.2, T); truth on the drawn gear-down pose;
before = the recheck's run on the round-2 tables (`out/od4_rc6_2/cpu/f3check_*.json`) → after (`cpu/f3check_*.json`), Wilson 95 %
interval of the after value in brackets; `tools/f3ci.py`). The PC-12 tables at flaps 0 / gear down are round 2's, so its figures are
unchanged (the recheck's own numbers, which ran slightly higher than 15.11's dense check: e.g. taxi hidden-drawn in the ground band 7.5 %
(3.8–14.1 %) of 107 against 15.11's 4.7 % - within the interval); the SF50 taxi light is F1's fix, the SF50 landing lights the cover rule's.

| PC12 light | set | off > 0.25 % | off > 0.5 % | hidden drawn > 0.25 % (of hidden) | seen ≥ 0.5 drawn > 0.25 below % | largest error |
|---|---|---|---|---|---|---|
| navL | all | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.0) | 0.0 → 0.0 (0.0–0.7) | 0.24 → 0.24 |
| navL | ground | 0.3 → 0.3 (0.1–0.9) | 0.0 → 0.0 (0.0–0.4) | 0.8 → 0.8 (0.2–3.0) | 0.0 → 0.0 (0.0–2.5) | 0.27 → 0.27 |
| navR | all | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.0) | 0.0 → 0.0 (0.0–0.7) | 0.19 → 0.19 |
| navR | ground | 0.1 → 0.1 (0.0–0.6) | 0.0 → 0.0 (0.0–0.4) | 0.4 → 0.4 (0.1–2.1) | 0.0 → 0.0 (0.0–2.5) | 0.34 → 0.34 |
| tail | all | 0.2 → 0.2 (0.1–0.6) | 0.0 → 0.0 (0.0–0.2) | 0.5 → 0.5 (0.1–2.6) | 0.0 → 0.0 (0.0–0.3) | 0.5 → 0.5 |
| tail | ground | 0.6 → 0.6 (0.3–1.3) | 0.0 → 0.0 (0.0–0.4) | 1.4 → 1.4 (0.5–4.1) | 0.0 → 0.0 (0.0–0.7) | 0.48 → 0.48 |
| beaconTop | all | 0.1 → 0.1 (0.0–0.3) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.7) | 0.0 → 0.0 (0.0–0.5) | 0.29 → 0.29 |
| beaconTop | ground | 0.1 → 0.1 (0.0–0.6) | 0.0 → 0.0 (0.0–0.4) | 0.7 → 0.7 (0.1–3.6) | 0.0 → 0.0 (0.0–1.4) | 0.29 → 0.29 |
| beaconBot | all | 0.3 → 0.3 (0.2–0.7) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.4) | 0.4 → 0.4 (0.2–1.0) | 0.37 → 0.37 |
| beaconBot | ground | 1.2 → 1.2 (0.7–2.1) | 0.1 → 0.1 (0.0–0.6) | 1.2 → 1.2 (0.5–3.1) | 0.7 → 0.7 (0.3–1.7) | 0.51 → 0.51 |
| strobeL | all | 0.7 → 0.7 (0.4–1.2) | 0.3 → 0.3 (0.2–0.7) | 1.4 → 1.4 (0.6–2.9) | 0.7 → 0.7 (0.3–1.3) | 0.78 → 0.78 |
| strobeL | ground | 1.8 → 1.8 (1.1–2.8) | 0.5 → 0.5 (0.2–1.2) | 1.5 → 1.5 (0.7–3.3) | 1.9 → 1.9 (1.0–3.5) | 0.74 → 0.74 |
| strobeR | all | 0.7 → 0.7 (0.4–1.2) | 0.1 → 0.1 (0.0–0.3) | 0.9 → 0.9 (0.4–2.4) | 0.7 → 0.7 (0.3–1.3) | 0.52 → 0.52 |
| strobeR | ground | 1.4 → 1.4 (0.8–2.3) | 0.3 → 0.3 (0.1–0.9) | 1.2 → 1.2 (0.5–2.8) | 1.7 → 1.7 (0.9–3.3) | 0.76 → 0.76 |
| landL | all | 1.0 → 1.0 (0.6–1.5) | 0.1 → 0.1 (0.0–0.3) | 0.5 → 0.5 (0.2–1.2) | 1.1 → 1.1 (0.6–2.0) | 0.69 → 0.69 |
| landL | ground | 3.8 → 3.8 (2.8–5.2) | 1.2 → 1.2 (0.7–2.1) | 2.1 → 2.1 (1.1–4.1) | 4.1 → 4.1 (2.8–6.1) | 0.78 → 0.78 |
| landR | all | 1.2 → 1.2 (0.8–1.8) | 0.3 → 0.3 (0.1–0.7) | 0.6 → 0.6 (0.3–1.3) | 1.4 → 1.4 (0.9–2.4) | 0.7 → 0.7 |
| landR | ground | 2.9 → 2.9 (2.0–4.1) | 0.8 → 0.8 (0.4–1.6) | 2.2 → 2.2 (1.2–4.1) | 2.4 → 2.4 (1.4–4.0) | 0.78 → 0.78 |
| taxi | all | 0.3 → 0.3 (0.1–0.7) | 0.0 → 0.0 (0.0–0.2) | 0.5 → 0.5 (0.2–1.4) | 0.1 → 0.1 (0.0–0.5) | 0.4 → 0.4 |
| taxi | ground | 1.2 → 1.2 (0.7–2.1) | 0.2 → 0.2 (0.1–0.7) | 7.5 → 7.5 (3.8–14.1) | 0.3 → 0.3 (0.1–1.0) | 0.69 → 0.69 |

| SF50 light | set | off > 0.25 % | off > 0.5 % | hidden drawn > 0.25 % (of hidden) | seen ≥ 0.5 drawn > 0.25 below % | largest error |
|---|---|---|---|---|---|---|
| navL | all | 1.4 → 1.4 (0.9–2.0) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.0) | 2.0 → 2.0 (1.3–3.0) | 0.39 → 0.39 |
| navL | ground | 0.5 → 0.5 (0.2–1.2) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–0.9) | 0.0 → 0.0 (0.0–0.9) | 0.3 → 0.3 |
| navR | all | 0.9 → 0.9 (0.6–1.5) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.0) | 1.0 → 1.0 (0.6–1.8) | 0.41 → 0.41 |
| navR | ground | 0.2 → 0.2 (0.1–0.7) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–0.9) | 0.0 → 0.0 (0.0–0.9) | 0.27 → 0.27 |
| tail | all | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.0) | 0.0 → 0.0 (0.0–0.7) | 0.2 → 0.2 |
| tail | ground | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–1.2) | 0.0 → 0.0 (0.0–1.1) | 0.16 → 0.16 |
| strobeL | all | 1.4 → 1.4 (1.0–2.1) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.8) | 0.1 → 0.1 (0.0–0.7) | 0.34 → 0.34 |
| strobeL | ground | 6.6 → 6.6 (5.2–8.3) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–1.3) | 0.5 → 0.5 (0.1–1.6) | 0.36 → 0.36 |
| strobeR | all | 2.0 → 2.0 (1.5–2.7) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.8) | 0.7 → 0.7 (0.3–1.6) | 0.4 → 0.4 |
| strobeR | ground | 6.5 → 6.5 (5.1–8.2) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–1.5) | 0.4 → 0.4 (0.1–1.5) | 0.4 → 0.4 |
| strobeTail | all | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.0) | 0.0 → 0.0 (0.0–0.7) | 0.2 → 0.2 |
| strobeTail | ground | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–1.2) | 0.0 → 0.0 (0.0–1.1) | 0.16 → 0.16 |
| landL | all | 0.6 → 0.1 (0.0–0.4) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.2) | 0.1 → 0.1 (0.0–0.5) | 0.39 → 0.31 |
| landL | ground | 0.7 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–1.0) | 0.0 → 0.0 (0.0–0.9) | 0.39 → 0.2 |
| landR | all | 0.5 → 0.1 (0.1–0.4) | 0.0 → 0.0 (0.0–0.2) | 0.0 → 0.0 (0.0–1.1) | 0.3 → 0.3 (0.1–0.8) | 0.39 → 0.27 |
| landR | ground | 0.6 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–0.4) | 0.0 → 0.0 (0.0–0.9) | 0.0 → 0.0 (0.0–0.8) | 0.44 → 0.23 |
| taxi | all | 20.9 → 0.0 (0.0–0.2) | 9.6 → 0.0 (0.0–0.2) | 17.9 → 0.0 (0.0–0.4) | 15.4 → 0.0 (0.0–0.7) | 0.96 → 0.21 |
| taxi | ground | 32.6 → 0.0 (0.0–0.4) | 17.7 → 0.0 (0.0–0.4) | 36.2 → 0.0 (0.0–1.9) | 11.8 → 0.0 (0.0–1.6) | 0.95 → 0.16 |

**F4: the external-occluder blind window and the fallback.** A sub-pixel lamp (w = 1) is hidden by another object (another
aircraft, a building) only through the external-occluder taps, which count a depth sample as another object's when it lies more
than reach + `LENS_XM` (0.3 m) in front of the lamp. Anything nearer the lamp than that - the window [0, reach + 0.3 m] - does not
hide it; beyond 3 m in front of the lamp the sprite's depth pull (3 m) hides the disc anyway. Per light, the share of the seen
directions (table ≥ 0.25) whose window is 3 m or more (no protection 0–3 m in front of the lamp) and the median / 90th percentile
window (`tools/reach_stats.mjs` = the recheck's, on this tree's flaps-0 tables; 4,000 uniform / 2,000 ground-band directions,
`cpu/reach_stats_final.txt`; round 2's (`out/od4_rc6_2/cpu/reach_stats.txt`) are the same within 0.4 points - the gear-up and
in-transit gear add to the reach only near the wells, the deployed flaps only in a lamp's flap tables - except the SF50 taxi light,
whose seen directions are now the drawn pose's (1,590 instead of 1,888: the open doors hide it from the others) and whose
window grew with the doors in front of it: 0.3 / 1.2 % → 1.5 / 2.8 %):

| light | whole sphere: seen directions, median / 90th-percentile window (m), window >= 3 m | ground band (el within ±15°): the same |
|---|---|---|
| PC12 navL | 1,996, 0.90 / 1.70, **5.9 %** | 922, 0.61 / 9.50, **17.1 %** |
| PC12 navR | 1,995, 0.86 / 1.70, **4.4 %** | 927, 0.60 / 9.23, **15.7 %** |
| PC12 tail | 3,030, 1.16 / 3.00, **10.5 %** | 1,295, 1.35 / 3.10, **30.3 %** |
| PC12 beaconTop | 2,220, 0.96 / 3.27, **11.4 %** | 1,345, 1.50 / 10.08, **33.5 %** |
| PC12 beaconBot | 2,193, 1.63 / 4.26, **26.9 %** | 1,353, 3.30 / 6.16, **59.9 %** |
| PC12 strobeL | 2,485, 0.90 / 2.22, **7.8 %** | 1,058, 0.91 / 10.43, **27.4 %** |
| PC12 strobeR | 2,453, 0.90 / 2.09, **6.6 %** | 1,050, 0.85 / 10.16, **23.3 %** |
| PC12 landL | 2,048, 1.68 / 4.98, **16.8 %** | 1,243, 2.65 / 6.33, **43.8 %** |
| PC12 landR | 2,055, 1.70 / 5.04, **17.4 %** | 1,232, 2.60 / 6.13, **41.9 %** |
| PC12 taxi | 2,495, 1.40 / 4.90, **15.8 %** | 1,694, 2.01 / 7.80, **36.2 %** |
| SF50 navL | 2,457, 0.70 / 1.20, **0.0 %** | 972, 0.70 / 1.21, **0.0 %** |
| SF50 navR | 2,524, 0.71 / 1.23, **0.0 %** | 1,017, 0.70 / 1.25, **0.0 %** |
| SF50 tail | 1,824, 0.85 / 1.46, **2.4 %** | 932, 0.70 / 1.23, **0.0 %** |
| SF50 strobeL | 1,943, 0.74 / 1.30, **0.0 %** | 970, 0.70 / 1.34, **0.0 %** |
| SF50 strobeR | 1,981, 0.70 / 1.30, **0.0 %** | 1,053, 0.70 / 1.30, **0.0 %** |
| SF50 strobeTail | 1,824, 0.85 / 1.46, **2.4 %** | 932, 0.70 / 1.23, **0.0 %** |
| SF50 landL | 2,615, 0.80 / 1.26, **1.6 %** | 999, 0.72 / 1.45, **6.7 %** |
| SF50 landR | 2,663, 0.80 / 1.30, **1.6 %** | 1,009, 0.70 / 1.43, **6.3 %** |
| SF50 taxi | 1,590, 1.10 / 1.51, **1.5 %** | 845, 1.30 / 1.69, **2.8 %** |

The window is wide where the aircraft itself runs along the line of sight - the PC-12 belly beacon and landing lights seen from
low abeam / ahead (the wing, the belly fairing and the nose leg within 0.5 m of the sight line, metres in front of the lamp), the
tip lamps along the wing (90th percentiles of ~10 m) - and narrow on the SF50 (median 0.7–1.3 m). A second aircraft parked within
that distance of such a lamp, in that line, does not hide it while the lamp is under ~1.5 pixels; a resolved lamp's depth test (w <
1) sees it. **Fallback to the bounding sphere**: a sub-pixel lamp's taps lie `LENS_QMIN` = 0.5 pixels apart, so a tap's texel lies
off = (tap offset + `LENS_TXL`) pixels from the line of sight - 1.414 pixels for a corner tap, 1.207 pixels for an edge tap, 0.707 pixels for the
centre - and the reach is replaced by the sphere over off = 0.8 … 1 × `LENS_RHO` (0.4 … 0.5 m). With fp = d × 2 tan(fov / 2) /
lines, a tap starts to fall back at d = 0.4 m × lines / (2 tan(fov / 2) × off) and has fully fallen back at 0.5 m × …:

| canvas | corner taps (4 of 9) start / complete | edge taps (4) | centre tap |
|---|---|---|---|
| fov 45°, 1080 lines (the follow camera) | 369 / 461 m | 432 / 540 m | 737 / 922 m |
| fov 40°, 1080 lines (the videos' typical) | 420 / 525 m | 492 / 614 m | 839 / 1,049 m |
| fov 30°, 1080 lines | 570 / 712 m | 668 / 835 m | 1,140 / 1,425 m |
| fov 55°, 720 lines (a laptop canvas) | 196 / 244 m | 229 / 286 m | 391 / 489 m |

(15.11 said "beyond ~460 m"; that is where the corner taps have fully fallen back at fov 45° / 1080, not where they start.)
Beyond the start, an object inside the aircraft's bounding sphere (11.6 m PC-12, 8.2 m SF50) and in front of the lamp does not
count at that tap.

**GPU** (the recheck's tools, `out/od4_it6r3/gpu/`, every job's `cmp.json` against the CPU replica of this tree; page errors 0):
`sf50taxi` 18 + `sf50taxi_final` 6 values, `near3_SF50` 16, `posed_PC12` 12, `f3_PC12` 8: the GPU equals the CPU replica in
every value (max |GPU − CPU| 0.000). The four documented worst F3 directions (`jobs_f3_PC12.json`, unchanged by this round's
tables) read strobeL 0.993–0.994, beaconBot 0.872–0.875, landL 0.956, taxi 0.797 against a truth of 0 - the documented 0.99 / 0.88 / 0.95 / 0.80, unchanged: the PC-12's flaps-0 / gear-down tables are round 2's. The temporal sequences are above (F1, F2).

**Tests**: `node tools/models/test_models.mjs` → **123 PASS, 13 KNOWN, 0 FAIL**, 4 INFO (`out/od4_it6r3/test_models_final.txt`;
round 2: 112 PASS). The recheck's suggestion is in: the independent ray cast of the table check is of the **drawn** default pose
(`Kinematics.pose({gear: 1})`, mean |table − ray cast| PC-12 0.022, SF50 0.058) - it would have caught both this round's F1 and
round 2's F1. New: the gear-up tables against a ray cast of `pose({gear: 0})` where the gear changes the table by more than 0.3
(PC-12 24 directions: mean |error| 0.000; SF50: no such direction), the flaps-40 / 39 tables against a ray cast of that pose
(PC-12 25 directions: mean 0.031, max 0.23 at a flap edge; SF50: none), the reach the shader reads in each of those poses an upper
bound of the posed aircraft (PC-12 144 + 160, SF50 128 + 144 directions, all), the SF50 taxi light ≤ 0.1 at the recheck's three
cameras (table 0.000, ray cast 0.000; round 2's table 0.87–0.92), the belly beacon's flap tables (above), the shader's F2 rule
(`rm`, `w`, the bound, `LENS_BM` / `LENS_BLO`) and the flap wiring (scene.js iL5.z / w, `bandRun`, lampWorld, `lampFlapX`). The
proposed patch `out/pc12_look_it4/test_models_it4_checks.patch` still does not apply (`git apply --check`) and is not needed: its
checks have been in the file since 15.10 (as 15.11 found). **`python3 -I -B tools/check_airport.py`** → **RESULT: ALL HARD CHECKS
PASSED** (`out/od4_it6r3/check_airport_final.txt`, after this section was written).

**App** (`out/od4_it6r3/tools/app_smoke3.mjs` = round 2's smoke test with a longer wait; `app/`, looked at): the live app,
snapshot mode, a local recorded pack (gitignored) at an instant when an SF50 taxis, night environment: `loadModel` computed the
SF50's tables in the app (25.5–29 s on this machine at a load average of 10–15), and from the follow camera at 45 and 150 m the
depth copy runs and the atlas holds the table of the light in view; 0 page errors. Found on the way: `DetailedAircraft.lightSprites`
swallowed any exception and drew no light at all; it now warns once in the console (`js/aircraft/detailed.js`).

**Docs stills**: the four stills with aircraft lights on (`pc12_chase`, `viewer_sf50_chase`, `viewer_sf50_gear_half`,
`viewer_sf50_lights_dusk`; the others draw no light sprite, and the tables change nothing else) re-rendered with this tree
(`out/od4_it6r3/stills/`) and compared with the committed ones (`tools/docs_cmp8.py`): mean |difference| ≤ 0.004 sRGB levels, at most
1 pixel off by more than 24 - unchanged, so `docs/phase3/` and its captions are unchanged this round (the dusk still looked at: its
camera, low ahead-right, sees no taxi-light glow before or after).

**Load cost** (Node, this machine, load average ~10): the tables take PC-12 8.2–9.0 s, SF50 9.9–12.0 s (round 2's code in the same
conditions 7.2 / 8.4–9.2 s): per ray one more walk for the posed gear-up and one per flap state, on small BVHs (gear 13,560 / 32,864
triangles, flaps 4,048 / 3,780). Memory: the flap tables add 32 KB each - PC-12 7 lamps × 2, SF50 1 × 2 = 512 KB; the atlas then
holds 35 bands (19 + 16) when both types are drawn, more than its first allocation of 32 bands (2,048 rows), so it doubles to 4,096
rows; on a device whose `MAX_TEXTURE_SIZE` is the WebGL2 minimum of 2,048 a table that does not fit is dropped (that sprite keeps
the depth test alone, or its flaps-0 table) [not seen on any device here].

**Files changed in this round**: `js/aircraft/glb.js` (`lampTables`: the drawn poses via kinematics.js, gear-up posed, flap tables,
per-pose reach, the 1 m surface-behind rule `LAMPVIS.BACK`, `FLAPDIFF`; `lampFlapSettings`, `lampFlapX`, `lampVisState`;
`reachSplat` keep option; header), `js/shaders/sprites.js` (`lampTable` + `flapMix`, the projected-ellipse r × T, the bound
`LENS_BM` / `LENS_BLO`, header incl. F4's distances), `js/scene.js` (`LampVisAtlas.bandRun`, iL5.z / w), `js/aircraft/detailed.js`
(`lampWorld` visF / flapX, the light-sprite warning), `tools/models/test_models.mjs` (the checks above), this file (sections 3, 8,
15.10 / 15.11 annotations, 15.12). Not changed: `js/aircraft/kinematics.js` (`gearSequence` `doorDown` is right: the drawn pose is
what the tables now follow), `js/aircraft/models.js`, `js/renderer.js`, `js/gl.js`, `dev/model*`, `docs/phase3/*`, the glb files,
`js/live/**`, `js/video/**`.

**Open / not verified (round 3)**: controls deflected and cabin doors open are still not tabulated (above ~1.5 pixels of seen lamp the
depth test sees them; below, a lamp a deflected aileron or an open airstair door hides is drawn at its table value - bounded at
near range by the table, not by the depth test); the PC-12 nose clamshells, open only in transit, are not in either gear table
(gear-in-transit lamps are mixed from the down / up tables by the leg's travel); between two tabulated flap settings the shares
are interpolated (PC-12 30° = 0.6 of the way from 15° to 40°) [inf]; the near-range bound trades jitter for the table's own error:
at 5–20 m the PC-12 draws 6–29 hidden light-directions per range above 0.25 (steady; round 2 1–19) and a seen lamp can be drawn up
to `LENS_BM` away from what its resolved depth test says; `LENS_BM` 0.15, `LENS_BLO` 0.5 and the r × T measure are inferred from the
CPU exploration; the external-occluder blind window (F4) is unchanged and documented, not removed; the flap tables need the atlas to
grow past 2,048 rows when both types are drawn; laptop GPU frame time still not measured. A video-determinism comparison spanning
this round will see the SF50 taxi light behind its doors, the PC-12 belly beacon and landing lights behind the deployed flaps, and
the steadier near-range lamps.

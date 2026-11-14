# Phase 3 (M2) — detailed-model runtime and the PC-12

Status 2026-11-14, after **review fix round 3, iteration 3** (section 14; earlier rounds: sections 10–13). Package M2 of
Phase 3a: the glTF runtime for the hwd3d renderer (parser, kinematics, a drawable with the GaAircraft interface, a registry),
the PC-12 built from `pc12/`'s own builders, a dev viewer with headless stills, and Node tests. The SF50 (package M1,
`tools/models/sf50/**`, `docs/phase3_sf50.md`) uses the same conventions. **Every test of this page is of SF50 build sha256
49242e41… (7,051,212 B; fix round 3, `docs/phase3_sf50.md`) and of the fix-round-3-iteration-3 PC-12 build (sha256
957b3c4e…, 6,255,744 B: pc12's own builders with the override set 'fr3', section 4)**; each image's caption in
`docs/phase3/SOURCES.json` names the model hash it shows (stills of earlier builds are marked superseded there), and
`tools/models/test_models.mjs` fails when a caption that claims the current model names another hash, or when
`js/aircraft/models/SOURCES.json` disagrees with the files (the first round presented a superseded SF50 build, 1806b9ea…,
as the tested one). Nothing here is wired into `js/live/**`: that is Phase 3b (exact diff in section 3).

## 1. Files (all new, M2)

| File | What |
|---|---|
| `js/aircraft/glb.js` | `.glb` parser + converter to hwd3d Geo data (Node-pure) |
| `js/aircraft/kinematics.js` | pivots → animation (Node-pure): gear + braces + doors, Fowler flaps, ailerons + tabs, elevators, rudder, ruddervators, stabiliser trim, propeller spin + blade pitch |
| `js/aircraft/detailed.js` | `DetailedAircraft` (GaAircraft interface + `setFlaps`, `setControls`), own programs `acobj` / `acglass` |
| `js/aircraft/models.js` | registry ICAO type → `{url, meta, groundGl, lightAnchors, frame}` (PC12, SF50), `MODEL_LOAD_OPTS`, `loadModel`, `createAircraft` (placeholder fallback), `withModelFrame` (traffic frame of a detailed type) |
| `js/aircraft/models/pc12.glb` | build of pc12's unchanged builders with the override set `fr3` (fix round 3 iteration 3: sha256 957b3c4e…; iteration 2: 6e349329…; fix round 3: c46fe4fb…; fix round 2, set `fr2`: 9ccfd9a5…); until fix round 1 an unchanged copy of `pc12/out/pc12.glb` @ f097de2 (87731cce…) |
| `tools/models/pc12/build_pc12_variant.py` | (fix round 2) runs pc12's builders (python3 -B, nothing written into pc12/) with a documented override set, writes `out/pc12_<set>/` (gitignored) with the pc12 commit, a dirty flag and the sha256 of every pc12 source + of itself; `--set=none` reproduces `pc12/out/pc12.glb` bit for bit (checked: 87731cce…) |
| `js/aircraft/models/pc12_meta.json` | subset of the build's meta (BOM, checks, wing, stats; since fix round 3 `out/pc12_fr3/pc12_meta.json`) + provenance (incl. `_provenance.variant`: overrides, builder and pc12-source hashes) + the frame measured with the runtime's own options |
| `js/aircraft/models/SOURCES.json` | provenance of every model file (pc12 from the import; SF50 from its builder's `_provenance`, hash re-computed; refreshed after every SF50 build with `--sources-only`; checked by the test) |
| `tools/models/pc12/import_pc12.mjs` | the copy / subset / provenance step (refuses an uncommitted `pc12/out`); `--variant=out/pc12_fr3` (since fix round 2) imports a variant build and refuses it if its recorded pc12 sources were dirty or differ from the files on disk, or the builder changed; `--sources-only` refreshes the other models' SOURCES entries (now with the SF50 builder state and source-tree hash) |
| `tools/models/test_models.mjs` | Node tests (section 6) |
| `dev/model.html`, `dev/model.js` | viewer: one model, HWD world (or neutral pad), URL parameters, orbit / pinch, sliders |
| `dev/model_shot.mjs` | headless 1920×1080 stills (JPEG ≤ 600 kB), viewer screenshots; writes each image's caption (pose, time, model sha256, OSM / NAIP notice) into `docs/phase3/SOURCES.json` |
| `docs/phase3/pc12_*.jpg`, `docs/phase3/viewer_*.jpg` | renders (section 7; the SF50 stills from the hwd3d renderer are `viewer_sf50_*.jpg`, since `sf50_*` belongs to M1) |
| `docs/phase3/SOURCES.json` | (fix round 1) caption + licence notice + model hash of **every** image in `docs/phase3`; written by `dev/model_shot.mjs` (pc12_*, viewer_*), `tools/models/sf50/render_checks.py` (sf50_*), and once by hand for the render-check package's `render_*` |

Run:
```bash
python3 -B tools/models/pc12/build_pc12_variant.py --set=fr3   # 2.5 s -> out/pc12_fr3/ (gitignored); bit-identical rebuilds
node tools/models/pc12/import_pc12.mjs --variant=out/pc12_fr3     # the current PC-12 (fix round 3 iteration 3, 957b3c4e…)
node tools/models/pc12/import_pc12.mjs                  # plain pc12/out copy (committed state only; before fix round 2)
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
idx bbox`) plus `mat` (per-vertex material index, CPU only). `KINDS` is exported.

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
/ flaps / rpm / roll / pitch / yaw, "cycle gear" (6-s ramp like traffic.js).

## 6. Tests (`node tools/models/test_models.mjs`), results 2026-11-14 after fix round 3 iteration 3

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
   `aircraftSprites` twice for the SF50's tail strobe.
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

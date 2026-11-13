# Phase 3 (M2) — detailed-model runtime and the PC-12

Status 2026-11-13, after **review fix round 2** (section 11; round 1: section 10). Package M2 of Phase 3a: the glTF runtime
for the hwd3d renderer (parser, kinematics, a drawable with the GaAircraft interface, a registry), the PC-12 imported from
`pc12/`, a dev viewer with headless stills, and Node tests. The SF50 (package M1, `tools/models/sf50/**`,
`docs/phase3_sf50.md`) uses the same conventions. **Every test and still of this page is of SF50 build
2026-11-13T20:12:10Z (sha256 37e2952f…, 7,051,052 B) and of the fix-round-2 PC-12 build (sha256 9ccfd9a5…, 6,043,144 B:
pc12's own builders with the window / door / dihedral override set 'fr2', section 4)**: each image's caption in `docs/phase3/SOURCES.json` names the model hash it
shows, and `tools/models/test_models.mjs` fails when a caption that claims the current model names another hash, or when
`js/aircraft/models/SOURCES.json` disagrees with the files (the first round presented a superseded SF50 build, 1806b9ea…,
as the tested one). Nothing here is wired into `js/live/**`: that is Phase 3b (exact diff in section 3).

## 1. Files (all new, M2)

| File | What |
|---|---|
| `js/aircraft/glb.js` | `.glb` parser + converter to hwd3d Geo data (Node-pure) |
| `js/aircraft/kinematics.js` | pivots → animation (Node-pure): gear + braces + doors, Fowler flaps, ailerons + tabs, elevators, rudder, ruddervators, stabiliser trim, propeller spin + blade pitch |
| `js/aircraft/detailed.js` | `DetailedAircraft` (GaAircraft interface + `setFlaps`, `setControls`), own programs `acobj` / `acglass` |
| `js/aircraft/models.js` | registry ICAO type → `{url, meta, groundGl, lightAnchors, frame}` (PC12, SF50), `MODEL_LOAD_OPTS`, `loadModel`, `createAircraft` (placeholder fallback), `withModelFrame` (traffic frame of a detailed type) |
| `js/aircraft/models/pc12.glb` | (fix round 2) build of pc12's unchanged builders with the override set `fr2` (sha256 9ccfd9a5…); until fix round 1 an unchanged copy of `pc12/out/pc12.glb` @ f097de2 (87731cce…) |
| `tools/models/pc12/build_pc12_variant.py` | (fix round 2) runs pc12's builders (python3 -B, nothing written into pc12/) with a documented override set, writes `out/pc12_fr2/<set>/` (gitignored) with the pc12 commit, a dirty flag and the sha256 of every pc12 source + of itself; `--set=none` reproduces `pc12/out/pc12.glb` bit for bit (checked: 87731cce…) |
| `js/aircraft/models/pc12_meta.json` | subset of the build's meta (BOM, checks, wing, stats; since fix round 2 `out/pc12_fr2/fr2/pc12_meta.json`) + provenance (incl. `_provenance.variant`: overrides, builder and pc12-source hashes) + the frame measured with the runtime's own options |
| `js/aircraft/models/SOURCES.json` | provenance of every model file (pc12 from the import; SF50 from its builder's `_provenance`, hash re-computed; refreshed after every SF50 build with `--sources-only`; checked by the test) |
| `tools/models/pc12/import_pc12.mjs` | the copy / subset / provenance step (refuses an uncommitted `pc12/out`); `--variant=out/pc12_fr2/fr2` (fix round 2) imports a variant build and refuses it if its recorded pc12 sources were dirty or differ from the files on disk, or the builder changed; `--sources-only` refreshes the other models' SOURCES entries (now with the SF50 builder state and source-tree hash) |
| `tools/models/test_models.mjs` | Node tests (section 6) |
| `dev/model.html`, `dev/model.js` | viewer: one model, HWD world (or neutral pad), URL parameters, orbit / pinch, sliders |
| `dev/model_shot.mjs` | headless 1920×1080 stills (JPEG ≤ 600 kB), viewer screenshots; writes each image's caption (pose, time, model sha256, OSM / NAIP notice) into `docs/phase3/SOURCES.json` |
| `docs/phase3/pc12_*.jpg`, `docs/phase3/viewer_*.jpg` | renders (section 7; the SF50 stills from the hwd3d renderer are `viewer_sf50_*.jpg`, since `sf50_*` belongs to M1) |
| `docs/phase3/SOURCES.json` | (fix round 1) caption + licence notice + model hash of **every** image in `docs/phase3`; written by `dev/model_shot.mjs` (pc12_*, viewer_*), `tools/models/sf50/render_checks.py` (sf50_*), and once by hand for the render-check package's `render_*` |

Run:
```bash
python3 -B tools/models/pc12/build_pc12_variant.py --set=fr2   # 1.5 s -> out/pc12_fr2/fr2/ (gitignored)
node tools/models/pc12/import_pc12.mjs --variant=out/pc12_fr2/fr2   # the current PC-12 (fix round 2)
node tools/models/pc12/import_pc12.mjs                  # plain pc12/out copy (committed state only; before fix round 2)
node tools/models/pc12/import_pc12.mjs --sources-only   # after EVERY SF50 rebuild (SOURCES.json hashes)
node tools/models/test_models.mjs --json=out/test_models.json
node dev/model_shot.mjs --model=PC12 --out=docs/phase3 --prefix=pc12 [--set=standard] [--jobs=jobs.json] [--t=<ISO>]
node dev/model_shot.mjs --viewer=phone                                          # interactive viewer screenshot
python3 -m http.server 8800 --bind 127.0.0.1  # then http://localhost:8800/dev/model.html?model=PC12&cam=chase&gear=0.5&flaps=40&rpm=1700
```
The fix-round job files (`out/fr1/*.json`, `out/fr2/*.json`, gitignored) are reproduced in section 7.

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
opaque / glass, all baked in the local frame at rest (gear down, surfaces neutral, doors closed). PC-12: 31 groups
(static 273,055 opaque + 41,546 glass triangles; door_airstair, door_cargo, 2 flaps, 2 ailerons, 2 aileron tabs, rudder,
rudder tab, stabiliser, 2 elevators, propeller hub, 5 blades, 3 gear legs, 2 nose doors, 6 brace links). The pc12
`structure` part (frames / stringers / spars, inside the skins; the pc12 viewer shows it only in X-ray) is excluded by
the registry; everything else is drawn: **410,834 triangles, 250,968 vertices** (fix round 2; 422,663 / 259,430 before:
fewer windows) per type (shared by every aircraft of the type). SF50: 22 groups, 463,121 triangles, 284,128 vertices.

**Light anchors** (drawn kinds, `glb.js KINDS`: `navL navR tail beaconTop beaconBot strobeL strobeR strobeTail landL landR
taxi`; any other kind a model names, e.g. the SF50's `iceLight`, is kept in `model.lights`, not drawn), in order:
(0) registry anchors `MODELS[type].lightAnchors` (model axes, each with its source) for lamps the source model does not
draw; (1) node extras `light: '<kind>'` (anchor = node origin); (1b) part extras `light_anchors` / `info.light_anchors`
(model axes); (2) clusters of the lens materials `light_red` / `light_green` / `light_white` and `lens` on a gear part
(pc12/model/details.py, gear.py).
- PC-12, from (2): navL / navR at the wing tips (x 0.894, y 1.543, z ∓7.827), strobes at the tip trailing edges, tail
  light in the bullet tip (x −8.342), upper beacon on the bullet nose, lower beacon under the fuselage (x −0.970,
  y 0.738), taxi = the nose-strut lamp (rides on `gear_nose`; off once the leg leaves the down lock).
- PC-12 **landL / landR (fix round 1; WL 1.027 since fix round 2, 4.6 cm under the raised wing)**, from (0): the Pilatus "PC-12 NGX Model Building Plan" p. 4
  (https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf, photo
  "LANDING LIGHTS"; looked at in the review's scratch copy, not committed) shows a multi-LED lamp in a fairing under the
  wing beside a flap-track fairing [obs]. The close-up does not show the span station: the anchors sit just inboard of
  the middle flap-track fairing (STA 6.20, BL ±3.15, WL 1.00, 4.5 cm below the wing skin) [inf: position]. Sprites only:
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
| `gear_door` | `open` (deg) × door; `seq: 'transit'` (default; PC-12 nose clamshells: open only between the locks) or `'down'` (open whenever the leg is out; SF50 nose doors) |
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
three-view 3.48 m kept in pc12/CLAUDE.md (the review estimates ~3.5 m from Pilatus drawing 190.10.40.432); both ACD outer
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
-        ... tr.dims = gaDims(q.t, q.c) ...
+        ... tr.dims = modelDims(q.t, q.c) ...
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
`tools/models/pc12/build_pc12_variant.py` with the override set **`fr2`** (module constants set before the build; nothing
written into `pc12/`; outputs in the gitignored `out/pc12_fr2/fr2/`), imported with `import_pc12.mjs --variant`. The
`none` set reproduces `pc12/out/pc12.glb` bit for bit (87731cce…), so the overrides are the only difference. Provenance in
`pc12_meta.json` `_provenance.variant` and `SOURCES.json`: the override values, the builder's sha256, the sha256 of every
pc12 source it ran and their tree hash, `pc12_sources_dirty: false`; the test fails if any of them changes on disk. pc12's
own method (drawings first, owner review) applies to `pc12/`; these overrides are hwd3d's measured corrections, proposed
to the pc12 owner for adoption (`pc12/model/fuselage_parts.py` FIXED_WINDOWS / AIRSTAIR / CARGO / EXIT / DOOR_WINDOWS /
WIN_*, `pc12/model/wing.py` DIHEDRAL / Z_QC0). Livery: pc12's original neutral scheme (white, cool-grey belly, navy
swoosh, brass pinstripe; `pc12/model/livery.py`), no registration, no logo (D1). Dimension and configuration facts and
their sources stay in `pc12/CLAUDE.md` ("Sourced facts"); all overall checks are unchanged (14.400 / 16.281 / 4.260 m,
track 4.530, wheelbase 3.480, prop clearance 0.321).

**Measurements (fix round 2; the PDF and rasters stay in scratch, never committed).** Pilatus "PC-12 NGX Model Building
Plan" (https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf), p.9 = drawing
**190.10.40.432** (A0, "MASSTAB 1:24"), rasterised at 200 dpi:
- *Side view (from port)*: scale from the 9 labelled frame lines EF1 −1880 … FR40 +8770 mm (FR10-relative chain
  dimensions): **328.44 px/m** (nominal 1:24 = 328.08), residuals ≤ 0.43 px (1.3 mm); x from the spinner tip at STA 0.39
  (pc12's anchor, `pc12/refs/mbp.py`), which puts FR10 at STA 3.080; z from the drawn ground line (the tyres touch it). Check:
  tail top 4.266 m (published 4.26), propeller axis WL 1.653 (pc12 1.655). Openings = enclosed white regions:
  **airstair door** 4.656–5.286 (centre 4.971, **no window**), **windows** 5.607 / 6.201 / 6.980 (0.289 × 0.374 m inside the
  line, centre WL 2.185 = 0.583 m below the drawn crown), **cargo door** 7.548–8.936 (centre 8.242) with **its window at
  7.961**. pc12 had the airstair at 4.715 with a window, port windows 5.52 / 6.32 / 7.12 / 7.92 and the cargo door at
  8.925 (0.68 m aft).
- *Starboard detail view* (registered on its FR16 line, same scale): openings at 5.602, **exit 6.203** (outline
  5.969–6.438 × 0.63 m, window 6.199), 6.978, 7.955 — the port stations mirrored (≤ 6 mm).
- *MBP p.5 livery sheets* (300 dpi, scale from the 14.40 m length): port windows 5.593 / 6.190 / 6.967 / 7.947 (agree
  with the drawing ≤ 15 mm: the sheet is to scale); **starboard 5 windows: 5.339, exit 6.192 (bracketed), 6.967, 7.716,
  8.469**. **Conflict** between the two Pilatus documents on the starboard side (drawing: 4 at the mirrored port stations
  in a partial view FR16-STA 8.98; livery: 5, unevenly spaced). Used: the livery (the only full starboard side; its port
  side is exact; the review's count source). Starboard fixed windows 5.339 / 6.967 / 7.716 / 8.469 + the exit window.
- *Front view* (track dimension 4530 → 328.04 px/m, z from the tyre bottoms): port wing upper / lower outline WL at BL 2.0
  … 7.5 (upper 1.355 … 1.873, lower 1.105 … 1.712); **upper-line slope 5.28°** over BL 3–7; winglet top BL 8.04, WL 2.135.
  (The drawing's own data block says span 16.14 m; the model keeps the published 16.28 m.)

**Overrides `fr2`.** Windows: the stations above, outline 0.295 × 0.380 m (r 0.065), centre 0.583 m below the model's crown
(WL 2.047). Doors: airstair centre 4.971 without window, cargo centre 8.242 with its window at 7.961 (opening sizes kept at
the sourced 0.61 × 1.35 / 1.35 × 1.32 m and their heights, which sit within 4 cm of the drawing relative to the
fuselage); exit at 6.195, 0.48 × 0.64 m as drawn (pc12 had 0.51 × 0.91 m from "Type III" at 5.52), centre 0.569 m below the
crown. Wing: reference-plane **dihedral 4.5° → 6.2°**, the least-squares fit of the upper AND lower outline shapes (rms 4
mm; top line 5.36° vs 5.28°), pivoted about the main-gear butt line (BL 2.265: Z_QC0 0.905 → 0.837) so the gear trunnion,
wells and gear-down geometry are unchanged; the wing is 4 cm lower at the fuselage side and up to 0.16 m higher at the tip.
Retracted mains: tyre protrusion 11 mm (POH ~1 in; was 27), trailing-link arm 51 mm (was 67; KNOWN). Landing-light anchors
follow the wing (WL 1.027). Glazing part renamed "Cabin windows (7 fixed …)", qty 7.

**What is still off (KNOWN, pc12 owner item, measured by the test):** relative to the ground and the propeller axis the
drawing's **cabin section is 0.138 m higher** than pc12's (crown WL 2.768 vs 2.630, keel 0.938 vs 0.800) while the nose
(STA ≤ 3.0) agrees; the wing outline is 0.117 (upper) / 0.126 (lower) m higher and the winglet top 0.107 m higher on the
drawing — the same offset, so relative to the fuselage the wing now sits as drawn. Fixing it moves the cabin loft, the
glazing constraints, the wing root, the gear legs and the fin height (`pc12/model/fuselage.py` control lines): a pc12
redesign through its drawings-first method, not an hwd3d override. Windows and doors are placed relative to the model's
crown, so they look right on the fuselage. Also unchanged: the retracted trailing-link arm (51 mm). **For the OD3 landing
video**: the window / door layout and the dihedral are now as drawn; the 0.14 m cabin height offset is visible only
against a ground-level reference at close range (the aircraft sits 0.14 m "low" on its gear) — the owner may approve
the video with it or wait for the pc12 loft fix.

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

## 6. Tests (`node tools/models/test_models.mjs`), results 2026-11-13 after fix round 2

No FAIL; 3 KNOWN (measured values printed; a KNOWN check fails if its value grows past its limit): the PC-12 cabin /
wing height offset vs drawing 190.10.40.432 (pc12 loft), the PC-12 retracted trailing-link arm (pc12), and the docs/phase3
licence plumbing outside M1 / M2 (ATTRIBUTION row, check_airport scope).

| Check | PC-12 | SF50 |
|---|---|---|
| parse + convert | 410,834 tris, 250,968 verts, 69 parts, 31 groups, 0 bad indices / normals | 463,121 tris, 284,128 verts, 43 parts, 22 groups |
| ACD length / span / height (2 %) | 14.400 (−0.12 %) / 16.281 (+0.22 %) / **4.260** (−0.16 %) | 9.357 (0.00 %) / 11.793 (−0.03 %) / 3.325 (+0.10 %) |
| origin on the main contact, at minus the static deflection | y −14.5 mm (pc12 gear.py), track 4.530 | y 0, track 3.414 |
| nose wheel on the ground (within its deflection) | y −10.5 mm, wheelbase 3.480 | y 0, wheelbase 3.305 |
| nothing but tyres below the ground; tyres within their deflection | lowest non-tyre +0.136 m | +0.083 m |
| propeller clearance vs sourced 0.32 m | **0.321 m** | — |
| pivots present / pivot origin = node origin / brace closure / L-R symmetry | PASS (30 movers; braces 4e-7 m) | PASS (8 pairs) |
| control travel vs certificate, sign measured | — | ailerons 15 / 11.5, LH trim tab 10 / 10, ruddervators 20 / 15, ruddervator tabs 7 / 18, yaw SAS 15 / 15; pull −20, push +15, yaw ±9, roll 15 / 11.5, geared tab +8 / −6 unclamped — **values inf (DRS)** until the owner decides (`docs/phase3_sf50.md` §8) |
| gear sweep: deepest point ≤ 0.05 m below the down contact | 5 mm (nose, gear 0.75) | 0 |
| gear retracted: only tyres protrude | **KNOWN** tyres 11 mm (POH ~1 in), trailing-link arm 51 mm | PASS (flush; trunnion / wells moved with the wing) |
| light anchors: none dropped; anti-collision = documented; wing landing lights | 10 drawn; landL / R at BL ±3.15, WL 1.027 | 9 drawn + iceLight kept; 3 anti-collision |
| registration panels keep every field | — | textDir kept |
| registry frame = measured (5 mm); withModelFrame(gaDims) = model | PASS | PASS |
| **cabin windows per side** | port 4 (3 + cargo door), starboard 5 (4 + exit), no airstair-door window | — |
| **window / door / exit stations vs drawing 190.10.40.432 + MBP p.5, ±0.03 m (fix round 2)** | every station within 5 mm; window centre 0.585 m below the crown (drawing 0.583); outline 0.295 × 0.377 | — |
| **wing front-view silhouette vs drawing 190.10.40.432 (fix round 2)** | shape rms 4 mm (upper + lower, BL 2–7.5), top line 5.36° (drawing 5.28°), winglet rise 0.281 m above the BL 7.5 upper line (drawing 0.262) | — |
| cabin crown / wing height vs the drawing | **KNOWN** crown 0.138 m, wing 0.117 / 0.126, winglet 0.107 m low (pc12 loft) | — |
| **wing front-view outline vs AFM Fig 1-1 (fix round 2)** | — | mid-line offset 0.000 m, upper slope 4.07° (AFM 3.95°), top at BL 1.6 0.438 m below the fuselage max-width line (AFM 0.43) |
| SF50 wing tips: outermost = span / 2, **rise above the extrapolated upper line 0.04–0.09 m (AFM front view 0.061 ± 0.02), top chord ≤ 0.08 m (fix round 2)**, lens on the skin opening | — | 5.897 m, rise 0.058 m, top chord 0.050 m, rim ≤ 2 mm, lamps behind the lens |
| SF50 nacelle: lip proud of a waist, fillets | — | lip 0.344 / waist 0.324 / fillet foot 0.422 m half-width |
| drawable: alpha on every item, placeholder sync, uAlpha in both programs | PASS (29 items, placeholder 2) | PASS (25 items) |
| **drawable: spinning groups, point 0.25 m off the axis, 40 / 59 / 178 rad/s (fix round 2)** | still 0 m, moved 2.00 m (prop) | still 0 m, moved 2.00 m (fan; fix round 1: 0.309 / 0.416 m still) |
| **drawable: shadow fades with the aircraft (fix round 2)** | acobj at alpha 0.3 casts through the dithered shadow pass, alpha 0 none; obj fallback 0.3 none / 0.7 casts; placeholder 0.3 none | same |
| drawable: CPU arrays released (keepCpu false) | PASS | PASS |
| **Phase 3b diff covers every gaDims call in js/live (fix round 2)** | traffic.js:395 and :1577 both in section 3 | |
| provenance: SOURCES.json = files; **builder sources = recorded hashes (fix round 2)**; every docs/phase3 image captioned, current-model claims match; **docs/phase3_*.md name the current hashes or are marked SUPERSEDED (fix round 2)** | PASS | PASS |
| docs/phase3 in ATTRIBUTION.md / check_airport.py scope | **KNOWN** (not M1 / M2 files; diffs in section 8) | |
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

All re-shot in **fix round 2** on the models above (captions with the model hash in `docs/phase3/SOURCES.json`), all
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
| `pc12_front34.jpg`, `pc12_rear34.jpg`, `pc12_side.jpg` | Green Ramp, hdg 135, gear down | shape, livery, glazing; starboard: 4 windows + the exit window (fix round 2) |
| `pc12_port.jpg`, `pc12_rear.jpg` (new, fix round 2) | Green Ramp | port: airstair door without window, 3 windows, cargo door with its window; from behind: the 6.2° dihedral |
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

- **PC-12 fidelity (pc12 owner)**: the cabin section 0.138 m low against drawing 190.10.40.432 (and the wing with it), the
  retracted gear arm 51 mm (section 4); the two Pilatus documents disagree on the starboard windows (section 4). The
  window / door layout and the dihedral are fixed in the hwd3d build (fix round 2) and proposed to the pc12 owner.
- **pc12 nose doors closed with the gear down** follow the pc12 model and its viewer [inf].
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
- SF50 open items (gear retraction directions [inf, unverified, searched again in fix round 2], control-surface travels
  inf (DRS) until the owner decides, digitised drawing data): `docs/phase3_sf50.md` §7 / §8. **The SF50 take-off video
  depends on both: its credits must carry the inf marker for the gear motion and the control-surface travels unless the
  owner supplies a source / approves the DRS route.**

## 10. Review fix round 1 (2026-11-13): dispositions

| # | finding | status |
|---|---|---|
| 1 | PC-12 cabin windows / door stations vs Pilatus NGX drawings | **deferred (pc12 owner item)**: `pc12/` is read-only for hwd3d and pc12's method requires its drawing step and the owner's review; recorded (section 4), KNOWN check with the measured counts |
| 2 | PC-12 wing dihedral / height / winglets | **deferred (pc12 owner item)**, same reasons; KNOWN check (3.66° vs ~5.2°) |
| 3 | SF50 wing tips | fixed (M1; `docs/phase3_sf50.md`) |
| 4 | SF50 nacelle section | fixed (M1) |
| 5 | SF50_FACTS: ACD gear values | fixed (docs; PC-12 values in section 3) |
| 6 | SF50_FACTS: lights provenance | fixed (docs) |
| 7 | SF50 gear retraction directions | not resolved: no primary source found; stays [inf] |
| 8, 13 | DRS web-viewer access | deferred: owner decision (`docs/phase3_sf50.md` §7) |
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
| F1 | PC-12 cabin windows / door stations (6 per side, airstair-door window, cargo door 0.7-0.8 m aft) | **fixed in the hwd3d build** (section 4): stations re-measured on drawing 190.10.40.432 and MBP p.5, pc12's own builders run with the override set `fr2` (`tools/models/pc12/build_pc12_variant.py`, nothing in `pc12/` changed), imported with full provenance; port 3 + cargo-door window, starboard 4 + exit, no airstair-door window, every station within 5 mm of the drawing; new stations test. Starboard: the two Pilatus documents disagree — livery used, conflict recorded. Remaining (KNOWN): the cabin section is 0.138 m low vs the drawing (pc12 loft) |
| F2 | PC-12 dihedral / height / winglets | **fixed in the hwd3d build** (dihedral 6.2° about BL 2.265, fitted to both front-view outlines, rms 4 mm, top line 5.36° vs 5.28°, winglet rise 0.281 / 0.262 m); new silhouette test. The absolute height (wing 0.12 m low, the same offset as the cabin) is the KNOWN pc12 loft item |
| F3 | DRS access route (owner) | **deferred (owner decision)**, narrowed: FSB item → faa.gov FSB draft (HTTP 200), FJ33-5A envelope / rating → EASA IM.E.016 (HTTP 200); control-surface travels have no non-DRS source and are now **inf (DRS)** in SF50_FACTS and the test labels; video credits must show it (`docs/phase3_sf50.md` §8) |
| F4 | SF50 wing ~0.10 m low vs AFM front view | **fixed** (M1: `Z_LE0` 0.835, gear trunnion / wells / slot / door moved with it; outline test) |
| F5 | SF50 tip fin twice the AFM height, square top; test limit mis-cited | **fixed** (M1: top 0.058 m above the extrapolated upper line, AFM 0.061 ± 0.02, 0.05 m pointed top; the test reads the rise as the figure is read; drawing-vs-photo conflict recorded) |
| F6 | SF50 fan motion vectors (spinning keyed on the prop disc) | **fixed** (`detailed.js` keys on the `spin` mover; test with an off-axis point at 40 / 59 / 178 rad/s; the old code fails it with the review's 0.309 m) |
| F7 | shadows pop on a fade | **fixed for the detailed aircraft** (dithered `acobj` shadow pass; obj fallback and placeholder path cast from alpha 0.5); test. General `SHADOW_FS` change for every program proposed (section 8 item 8: `renderer.js` belongs to the other workflow) |
| F8 | docs/phase3 ATTRIBUTION row and check_airport scope | **deferred (not M1 / M2 files)**: exact diffs with current line numbers in section 8 items 5 / 6; a new KNOWN test check reports them until their owners apply them; must be done before publishing |
| F9 | traffic frame: the 3b diff missed the parked-aircraft restore site | **fixed**: `modelDims(type, category)` in `models.js`; the section 3 diff lists both `traffic.js` sites (:395, :1577) and the import; the test fails while any `gaDims(` call in `js/live` is not covered |
| F10 | SF50 provenance names a commit without the builder | **fixed**: `_provenance.builder_state` ("working tree (uncommitted …)"), per-file sha256 of every builder / kernel source + a tree hash, also in SOURCES.json; the same for the PC-12 variant; the test fails if any source on disk differs; rebuilds are bit-identical (SF50 0db80513… from the fix-round-1 sources, 37e2952f… twice; PC-12 `none` = 87731cce…) |
| F11 | `docs/phase3_render.md` stale | **fixed**: SUPERSEDED banner (it describes 9267d3e0… / 87731cce…); `render_pc12_*` captions marked superseded; the test fails a phase3 write-up that names a model without its current hash or the banner |
| F12 | SF50 gear retraction directions; laptop GPU cost | **deferred**: no source found in fix round 2 either (AFM §7 points to the non-public PIM; 3A-15 does not say; web search nothing) → stays [inf, unverified] and the credits must say so; the GPU frame time needs the owner's laptop (section 9) |

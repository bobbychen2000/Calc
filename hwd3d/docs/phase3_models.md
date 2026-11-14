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

**Made in OD4 (2026-11-14), the first renderer-file change of this package (more in OD4 iteration 3, below):** `js/shaders/post.js` FINAL_FS takes
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
  items are in section 15.5.

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

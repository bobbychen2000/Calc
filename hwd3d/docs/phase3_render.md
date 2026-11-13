# Phase 3 — independent render check of the SF50 and PC-12 models

> **SUPERSEDED (review fix round 2, 2026-11-13).** Everything below describes SF50 build 9267d3e0… and pc12.glb 87731cce…,
> neither of which is current: the SF50 was rebuilt twice since (fix round 1: 0db80513…; fix round 2: 37e2952f…, wing
> root 0.10 m higher, AFM front-view tip height), and the PC-12 is now the fix-round-2 build 9ccfd9a5… (window / door layout
> and dihedral fitted to the Pilatus drawings). Its SF50 conclusions on the tips, the nacelle and the close-ups, and its
> PC-12 window / wing remarks, are historical. The current state and stills are in `docs/phase3_models.md` and
> `docs/phase3_sf50.md`; every `render_*.jpg` caption in `docs/phase3/SOURCES.json` is marked superseded.
> `tools/models/test_models.mjs` fails while a phase3 write-up names a model without its current hash and without this banner.

Status 2026-11-13. This is an independent check of the two detailed models in the hwd3d renderer. It is not M1 (SF50
builder) or M2 (runtime, PC-12 import). No model, runtime, shader or shared file was changed: the only files written are
this page, `docs/phase3/render_*.jpg` and scratch scripts and results in `out/phase3_render/` (gitignored).
`git status --porcelain pc12 sfo3d` prints nothing.

Models checked:

| Model | File | sha256 |
|---|---|---|
| SF50 | `js/aircraft/models/sf50.glb` | 9267d3e0… (M1's final build, the same hash M1 reported) |
| PC-12 | `js/aircraft/models/pc12.glb` | 87731cce… (M2's import of `pc12/out/pc12.glb` @ f097de2) |

## 1. How the renders were made

- **Renderer.** The renders use the real hwd3d renderer via M2's `dev/model.html`, with the HWD world and the NAIP
  ground. They run on SwiftShader at 1920×1080 with MSAA 4 and 4096² shadow cascades. The page is driven by
  `out/phase3_render/shoot.mjs`, a copy of M2's `dev/model_shot.mjs` with two differences: it passes `?metar=`, and it
  records the light sprites. `shoot_flash.mjs` renders at an instant when a strobe or beacon is flashing.
- **SF50 morning.** An early-November morning; the sky and wind come from a real KHWD METAR of that hour
  (`00000KT 10SM CLR 10/08 A3013`). The sun is low in the east-southeast, about 10° up. (The exact instant is not
  given here: it was chosen near a recorded movement, default D1.)
- **PC-12 midday.** An early-November midday; real KHWD METAR of that hour (`25005KT 10SM CLR 17/11 A3014`). The sun
  is in the south, about 36° up. Both METARs come from `refs/cache/metar/` (IEM archive).
- **Night.** 2026-11-06 03:40Z (19:40 PST, sun elevation −30.2°). The last available METAR, 052054Z, is carried forward
  [inf: no report for that hour is in the cache].
- **Placement.**
  - The ramp shots are on the Green Ramp at heading 135.
  - The runway shots are on runway 28L, 300 m past the threshold, on the runway heading.
  - The take-off rotation is the SF50 pitched 8° about the main-gear contact.
  - The landing flare is the PC-12 0.6 m up, pitched 5°, flaps 40, 1,700 rpm.
  - The pitch and flare values are illustrative [inf].

## 2. Bounding boxes against `data/ga_types.json` (FAA ACD)

Two independent measurements were made:

- **Raw glTF.** `geom_check.py` parses the glTF itself (it does not use `glb.js`), applies the node hierarchy, and drops
  the pc12 `structure` part, as the registry does.
- **Runtime frame.** `local_check.mjs` measures the converted local frame through `glb.js`, which is what the renderer
  draws.

| | ACD (row) | Model (raw glTF) | Δ |
|---|---|---|---|
| PC-12 length | 14.417 m (353) | 14.400 m (spinner tip glTF Z 0.390 → tail-bullet tip Z 14.790) | −17 mm (−0.12 %) |
| PC-12 span (with winglets) | 16.246 m | 16.281 m (winglet tips X ±8.141) | +35 mm (+0.22 %) |
| PC-12 tail height | 4.267 m | 4.2745 m from the lowest point (tyres, Y −0.0145); 4.260 m from the pc12 ground | +7.5 mm (+0.18 %) |
| SF50 length | 9.357 m (368) | 9.357 m (nose Z 0.900 → tail cone Z 10.257) | 0 |
| SF50 span | 11.796 m | 11.788 m (wing tips X ±5.894) | −8 mm (−0.07 %) |
| SF50 tail height | 3.322 m | 3.3254 m (V-tail tip) | +3.4 mm (+0.10 %) |

**Runtime frame** (+x forward, +y up, +z starboard, origin = main-gear contact):

| | PC-12 | SF50 |
|---|---|---|
| x (aft … nose) | −8.360 … 6.040 | −4.904 … 4.453 |
| y | 0 … 4.274 | 0 … 3.325 |
| z (span) | ±8.141 | ±5.894 |
| Track | 4.530 m | 3.414 m |
| Wheelbase | 3.480 m | 3.305 m |
| Nothing below y = 0 | at gear 1, 0.5 and 0 | at gear 1, 0.5 and 0 |
| Tail-strike angle about the main contact | 11.8° (set by the ventral antenna at x −2.79, y 0.58) | 14.0° (set by the left ventral fin) |

M2's `tools/models/test_models.mjs` was re-run: everything passes, with one KNOWN item, the PC-12 retracted
trailing-arm protrusion of 67 mm.

**Axes and origin verified.**
- The nose is at +x and the tail at −x.
- The green light (navR) is at z +7.83 / +5.82 (starboard) and the red light (navL) at −z. Each anchor is 2–3 cm from
  the lens of its own colour.
- In every ramp render the tyres sit on the pavement.
- The gear sequence moves the right way: PC-12 mains inward and nose aft; SF50 mains inward and nose forward.

## 3. Renders (`docs/phase3/render_*.jpg`, all looked at)

**SF50**

| Image | Pose |
|---|---|
| `render_sf50_ramp_am_front34.jpg`, `render_sf50_ramp_am_rear34.jpg` | Ramp, morning sun (the rear view is into the sun) |
| `render_sf50_chase_takeoff_roll.jpg`, `render_sf50_chase_rotation8.jpg` | Close chase from behind and above (eye 13 m behind, 4.5 m up, 2.5 m right), flaps 15, fan running, nav/strobe/landing on |
| `render_sf50_side_rotation8.jpg` | Starboard side, rotation 8°: tail and ventral fins clear, nose wheel off the ground |
| `render_sf50_gear_075.jpg`, `render_sf50_gear_050_under.jpg`, `render_sf50_gear_000.jpg` | Gear transition, 8 m up |
| `render_sf50_nose_close.jpg`, `render_sf50_nose_gear_doors.jpg` | Close-ups of the nose and the nose gear with its open doors |
| `render_sf50_defect_nose_seam_dashed.jpg`, `render_sf50_defect_pinstripe_fragments.jpg` | Close-ups of defect D1 |
| `render_sf50_night_ramp_front34.jpg`, `render_sf50_night_chase.jpg`, `render_sf50_night_front_landing.jpg`, `render_sf50_night_strobes.jpg` | Night with lights |

**PC-12**

| Image | Pose |
|---|---|
| `render_pc12_ramp_noon_front34.jpg`, `render_pc12_ramp_noon_rear34.jpg` | Ramp, midday sun |
| `render_pc12_chase_final.jpg`, `render_pc12_chase_flare.jpg` | Close chase from behind and above (eye 20 m behind, 6.5 m up, 3.5 m right), flaps 40, 1,700 rpm with the prop disc, at 4 m and 0.6 m |
| `render_pc12_side_flare.jpg` | Starboard side, flare 5° |
| `render_pc12_gear_075.jpg`, `render_pc12_gear_050_under.jpg`, `render_pc12_gear_000.jpg` | Gear transition, 10 m up |
| `render_pc12_nose_close_pinstripe.jpg`, `render_pc12_tail_close_pinstripe.jpg`, `render_pc12_cockpit_glazing.jpg`, `render_pc12_flaps40_wingroot.jpg` | Close-ups |
| `render_pc12_night_ramp_front34.jpg`, `render_pc12_night_chase.jpg`, `render_pc12_night_front_landing.jpg`, `render_pc12_night_strobes_beacons.jpg` | Night with lights |

The full set is in `out/phase3_render/img/`. It has 20 SF50 stills (including the gear at 0.25, tail and gear close-ups
and a nacelle close-up) and 19 PC-12 stills. The per-job parameters, HUD text and light sprites are in
`out/phase3_render/<prefix>.json`. No page errors were logged in any run.

## 4. Defects found (most visible first)

**D1. Seams and pin-stripes render as broken dashes (both models; visible in every close and chase view).**
- SF50:
  - The nose access-panel seam and the grey pin-stripe each side of the navy swoosh show as separate dark slivers
    instead of continuous lines. See `render_sf50_defect_nose_seam_dashed.jpg` and
    `render_sf50_defect_pinstripe_fragments.jpg`.
  - The `paint_stripe` geometry is 3,767 triangles in 62 disconnected pieces, 32 of them shorter than 5 cm.
  - The `seam` geometry is 56 pieces, 45 of them shorter than 5 cm.
  - The strips are 7.8 mm (stripe) and about 7–17 mm (seam) wide, on a skin whose median triangle edge is 22.4 mm.
  - The seam strips sit 0.80 mm below the skin (median), as grooves; 9.4 % of their area is covered by skin.
- PC-12: the brass pin-stripe shows the same dotted look along the swoosh and on the fin. See
  `render_pc12_tail_close_pinstripe.jpg` and `render_pc12_nose_close_pinstripe.jpg`. The `paint_stripe` geometry is
  3,609 triangles in 114 pieces, 57 of them shorter than 5 cm. It is 10–16 mm wide on skin edges of 31–50 mm.
- Likely cause [inf]: a band narrower than one skin triangle, trimmed by implicit marching triangles, which loses the
  band wherever no vertex falls inside it.
- Fix suggestion (builders, not done here):
  - Widen the stripes to at least two skin cells.
  - Or refine the skin locally along the stripe before trimming.
  - Or draw them as continuous overlay strips offset about 0.5 mm outward. Z-fighting is not a risk at that offset
    (section 5).
- The PC-12 is a pc12 model (owner) item.

**D2. PC-12 landing lights are in the wrong place.**
- The model's only landing and taxi light is a lamp on the nose strut (anchors `landL`, `landR` and `taxi` at x 3.48,
  y 0.81, on `gear_nose`).
- Pilatus's own *PC-12 NGX Model Building Plan* (pilatus-aircraft.com, `PC-12-NGX-Model-Building-Plan.pdf`), p. 4,
  "Detailed view — Landing lights", shows something different: two LED lamp units in a faired housing under the wing
  lower surface, next to the flap-track fairings. The same page's "Nose gear" photo shows the fork and wheel with no
  lamp in view.
- The spanwise station, and which wing, cannot be read from the photo.
- So in a night landing video the PC-12 shows the wrong light pattern: one glare spot on the nose leg (see
  `render_pc12_night_front_landing.jpg`) instead of lamps under the wing.
- This is a pc12 model item. Phase 3b could override the anchors.

**D3. PC-12 cabin crown sits 0.10–0.16 m low, and the dorsal fairing is short (silhouette).**
- Pilatus drawing 190.10.40.432 (the Model Building Plan p. 9 side view) was measured on a 100-dpi raster. It was
  registered by its 2,690 / 1,380 mm water-line dimensions and the FR10–FR30 frame spacing (166.6 px/m both ways).
  - It puts the cabin crown 2.73 m above the hatched ground line.
  - Anchoring instead on the 4.26 m tail height gives 2.79 m.
- On the p. 2 brochure three-view, registered on its 14.40 m and 4.26 m extension lines, the crown is 2.75–2.76 m
  (median over STA 4.5–10).
- The model crown is 2.630 m (`pc12/model/fuselage.py` `_top`), so it is 0.10–0.16 m low. The 1.83 m external fuselage
  depth agrees with the drawing (crown to the "290" keel line), so the whole cabin section sits low. The nose and
  cowling match: STA 1–3 is +16 mm.
- Both drawings show a long straight dorsal fairing from about frame FR33 (≈ STA 9.0) to the fin. The model's
  `dorsal_fin` starts at STA 10.35, so the top silhouette is 0.37 m low (median) over STA 10–12.
- Tail height and length match. One drawing pixel is 6 mm (p. 9) or 16 mm (p. 2), with lines about 2 px wide.
- The overlay image is kept in `out/phase3_render/silhouette/` (gitignored, because it contains the Pilatus drawing).
- pc12/CLAUDE.md lists the fuselage contours as "estimated / reconstructed". This is an owner item for pc12.

**D4. SF50 pylon NACA inlet reads as a letter "A" / "Λ" on the nacelle side.**
- The NACA inlet is a flat dark `inlet_dark` cap in `nacelle`, |X| > 0.2, Z ≈ 6.0–7.0. It is planar, not recessed, so at
  chase distances it looks like a printed glyph. See `out/phase3_render/img/sf50_day3_gear_close.jpg` and
  `sf50_day2_gear_050.jpg`.
- It is not a logo, but it could be read as one. Its position is [inf] in M1's builder.

**D5. SF50 nose-gear doors look like a solid box under the nose.**
- With the gear down, the two doors (`seq: 'down'`, ±85°) read from most angles as a 0.85 m grey box or plank. See
  `render_sf50_nose_gear_doors.jpg`.
- An open door is consistent with the AOPA 2022 ramp photo (reference only), which shows a large panel hanging below
  the nose beside the nose wheel. So the open state looks right, but the door shape and thickness need a photo check.

**D6. Smaller items.**
- **SF50 main-gear wells** are open from below with the gear down. No well roof: the inside of the wing upper skin is
  seen as back-facing paint. In the debug facing pass this is 10.7k of the 18.4k back-face pixels. In the real
  renderer it reads as a dark cavity (`render_sf50_gear_050_under.jpg`), which is acceptable.
- **SF50 main-gear leg gap.** The leg (`gear_main_L`) does not touch the airframe: the minimum surface gap is 12 mm
  (sampled, an upper bound), at the trunnion inside the well. It is not visible in any render.
- **SF50 `fan_face`** is 22 mm from the fan, inside the nacelle and invisible.
- **PC-12 pitot masts** (both wings, X ±5.06) stand 9.6 mm clear of the wing skin. This would be visible only in
  extreme close-ups.
- **PC-12 horizontal-stabiliser tip caps** show back faces or normals opposite their winding: 532 back-face and 199
  inverted-normal pixels over 26 directions. No dark patch is visible in `render_pc12_tail_close_pinstripe.jpg`.
- **SF50 tail strobe.** The GLB has a `light:strobeTail` anchor that `js/aircraft/glb.js` ignores (non-standard kind),
  so in the renderer the SF50 has only the two wing-tip strobes. The real light set is not verified here.
- **PC-12 retracted mains.** The trailing arm protrudes 67 mm (M2's KNOWN item); it is visible as a small bulge in
  `render_pc12_gear_000.jpg`.

## 5. Checks that found no defect

**No z-fighting.**
- The debug renderer `out/phase3_render/dbg.html` uses plain WebGL2 and the same `glb.js` conversion. It draws the
  material-ID image twice, with the triangles in forward and in reverse order, using float32 depth, LEQUAL and the
  app's near/far range (near 0.1–0.25 m, far 324 m).
- This was done for 8 views at 10–25 m. At most 13 pixels per 1024² view differ in material (PC-12), and 7 (SF50), out
  of 54k–304k model pixels.
- Exactly coincident triangles of different materials with non-zero area exist only between PC-12 engine modules, as
  internal end caps of 0.08–0.13 m² inside the cowling. The SF50's 315 coincident lip/paint triangles at Z 5.947 all have
  zero area.

**Normals and holes.** 26 orthographic directions were checked; every visible opaque pixel is classified by its winding
and by the sign of N·V. Glass is drawn as an occluder.

| | Back faces visible | Normal opposite winding | Where the back faces are |
|---|---|---|---|
| SF50 | 0.94 % of model pixels | 0.026 % | Almost all the main-gear wells and the inside of the exhaust nozzle |
| PC-12 | 0.28 % | 0.037 % | Gear wells, the stabiliser tips, and scattered single pixels on thin edges |

The pixel counts cover all 26 directions. Of the facing images, only three were looked at: SF50 from below, SF50 from
the rear quarter below, and PC-12 from the front quarter below (flagged pixels enlarged). The stabiliser-tip location
of the PC-12 back faces comes from that last image. No hole in an exterior skin was seen in those images or in any
render.

**Glass.** In both models the windshield, side windows and cabin windows are see-through, with seats, panel and
interior visible, and tinted with reflections. None is opaque or invisible (`render_pc12_cockpit_glazing.jpg`,
`render_sf50_nose_close.jpg`).

**Lights at a flash instant** (`render_pc12_night_strobes_beacons.jpg`, `render_sf50_night_strobes.jpg`). The screen
positions were computed from the sprite list and match the picture.
- PC-12:
  - Red top beacon on the bullet nose.
  - Red lower beacon on the belly, just aft of the mains.
  - White strobes at both wing tips.
  - White tail light at the bullet tip.
- SF50:
  - White strobes at both wing tips.
  - White tail light at the tail cone.
- Green is on the starboard tip and red on the port tip.

**Gear transition.**
- At gear 0.75, 0.5, 0.25 and 0 both models fold as documented.
- The PC-12 tyres stay visible in the wells when retracted (POH: about 1 in).
- The SF50 gear is flush when retracted.

**Ground contact.** Nothing is below the ground at rest; the tail clears in the 8° SF50 rotation and the 5° PC-12 flare.

## 6. Silhouette comparison with the real aircraft (references are reference only, kept in the session scratchpad, never committed)

**PC-12.** Pilatus *PC-12 NGX Model Building Plan* PDF,
`https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf` (HTTP 200).
- p. 2: three-view with 47 ft 3 in (14.40 m) length, 4.26 m height, 16.28 m span and 4.53 m track.
- p. 4: detail photos of the antennas, flap system, nose gear, landing lights, and tail and antenna.
- p. 9: drawing 190.10.40.432.
- Result: the overall planform, T-tail, fin, nose and cowl, gear positions and track agree. The deviations are the crown
  and dorsal fairing (D3) and the landing lights (D2).

**SF50.** No three-view drawing was obtained.
- Wikimedia Commons refused again (API HTTP 429, "too many requests"). This is recorded and was not worked around.
- Used instead (all HTTP 200):
  - The Cirrus Vision Jet product page `https://cirrusaircraft.com/aircraft/vision-jet/` and its air-to-air and
    lifestyle photos.
  - The AOPA *Flight Training* 2022 "Ramp appeal: Cirrus SF50 Vision Jet" lead photo.
- Consistent with the photos:
  - The nacelle sits low on the aft fuselage, with the inlet just aft of the cabin roof.
  - The V-tail has large surfaces.
  - The windshield has a centre post at the top (cockpit photo).
  - The cabin windows are large rounded squares ("squircle").
  - The clam-shell door has the upper half hinged up and steps in the lower half.
  - A nose-gear door hangs open with the gear down (AOPA photo).
- The photos are perspective views of banked aircraft, so no quantitative overlay was attempted.
- Not checked: the SF50 landing-light position (M1 put it in the wing tips) and the ventral-fin size.

## 7. Renderer observations (not model defects; for Phase 3b)

- **Nav lights from dead ahead.** From a camera about 24 m ahead and near the centreline, `aircraft_lights.js` emits no
  red or green sprite for either model. The light-to-viewer direction is about 18° inside the opposite sector, where
  `navIntensity` ramps to zero.
  - This follows the FAR 23.1389 overlap limits, but a close camera would see the lenses.
  - In those frames only the landing and taxi glare shows (`render_*_night_front_landing.jpg`).
- **Taxi light off-axis.** The taxi light is invisible at 45° off-axis: there is no sprite outside its 20° beam.
- **Strobes and beacons** appear only at flash instants. A still catches them by chance; `shoot_flash.mjs` searches for
  a flash time.
- **Ground streaks.** The runway texture shows motion-blur-like streaks in the runway chase stills even with a static
  camera. The cause was not investigated; it may be the renderer's velocity or temporal pass.

## 8. Not verified / open

- Real-photo checks of the following were not done:
  - SF50 nose-door shape.
  - SF50 landing-light location.
  - SF50 tail-strobe existence.
  - SF50 nacelle NACA-inlet position.
  - PC-12 landing-light spanwise station.
  - PC-12 window count per side.
- Laptop-GPU appearance and performance were not checked. All renders are SwiftShader.
- The take-off rotation (8°) and flare (5°, 0.6 m) attitudes are illustrative, not taken from the recorded tracks.
- The PC-12 crown measurement (D3) was made on a 100-dpi raster of the drawing, accurate to about ±2 cm. pc12's own
  registration pipeline (`pc12/refs/mbp.py`) was not run, because it writes into pc12/.
- The night METAR is carried forward [inf].

**Re-run** (from `hwd3d/`):

```bash
python3 -B out/phase3_render/geom_check.py
node out/phase3_render/local_check.mjs
node out/phase3_render/dbg_run.mjs --model=SF50
node out/phase3_render/shoot.mjs --model=SF50 --t=… --metar="…" --jobs=out/phase3_render/jobs_sf50_day.json --prefix=…
```

These are scratch files in the gitignored `out/` folder.

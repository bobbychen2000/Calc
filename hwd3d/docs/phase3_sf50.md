# Phase 3 (M1): Cirrus SF50 Vision Jet — own parametric model

Status 2026-11-13 after **review fix round 3** (§9): current build 2026-11-13T21:13:45Z, **sha256 49242e41…**, 7,051,212 B
(builder source hashes in `sf50_meta.json` `_provenance.sources_sha256`, tree 48ac26ba…; fix round 2 build: 37e2952f…).

Owner decision OD3 asks for a follow-cam video of a real SF50 take-off from 28L, so the SF50 must hold up at chase-camera
range: gear down and retracting, fan, control surfaces, flaps, lights, glazing. This is an own model, built in Python with
the `pc12/` loft kernel, from published dimensions and the manufacturer's flight-manual drawings. No third-party geometry,
texture, photo or drawing is in the repository.

| file | what |
|---|---|
| `tools/models/sf50/build_sf50.py` | build entry point → `js/aircraft/models/sf50.glb` + `sf50_meta.json` |
| `tools/models/sf50/sf50_geom.py` | every parameter, control line and section law, each tagged `[obs: …]` / `[inf: …]` |
| `tools/models/sf50/sf50_{fuselage,wing,tail,nacelle,gear,interior}.py` | component builders |
| `tools/models/sf50/sf50_kernel.py`, `sf50_assemble.py` | pc12 kernel import (read-only), airfoils, SDFs, materials; glTF writer |
| `tools/models/sf50/raster.py`, `render_checks.py` | numpy z-buffer rasteriser and the check renders below |
| `tools/models/sf50/SF50_FACTS.md` | **the fact table**: every value with its source URL, quoted words and obs/inf |

```bash
cd hwd3d
python3 -B tools/models/sf50/build_sf50.py        # ~3 s: 43 parts, 463,121 triangles, 7,051,212 B GLB, prints the checks
#   (--out-dir=out/<dir> for a trial build; the meta records the sha256 of every builder / kernel source: fix round 2)
python3 -B tools/models/sf50/render_checks.py     # ~7.5 min (CPU): docs/phase3/sf50_*.png + their captions in docs/phase3/SOURCES.json
node tools/models/pc12/import_pc12.mjs --sources-only   # after EVERY rebuild: js/aircraft/models/SOURCES.json hashes
node tools/models/test_models.mjs                 # M2's loader / kinematics / provenance test (fails on a stale SOURCES or caption)
```
Always run Python with `-B`: the builder imports `pc12/cad` and `pc12/model/{lifting,airfoil,parts}.py` and must not write
`__pycache__` into `pc12/` (`git status --porcelain pc12 sfo3d` stays empty; checked after every build).

## 1. Sources (details and quotes in SF50_FACTS.md)

- **FAA TCDS A00018CH Rev. 7** (found on FAA DRS by searching the number, read in DRS's public web viewer; it gives no
  dimensions; **obs** since fix round 3, decision (a) below): engine, weights,
  datum ("89 inches in front of the flat surface of forward cabin bulkhead"), **control-surface travels**
  (aileron UP 15 / DOWN 11.5, LH aileron trim ±10, ruddervator pitch UP 20 / DOWN 15, yaw ±9, trim UP 7 / DOWN 18,
  yaw SAS ±15, flaps 15° (50 %) / 39° (100 %)).
- **EASA TCDS EASA.IM.A.615 Issue 6**: configuration sentence and dimensions (length 9.36 m, span 11.67 m (38.3 ft),
  height "3.23 m (10.9 ft)", wing area 18.18 m²).
- **FAA TCDS E3GL Rev. 26**: FJ33-5A envelope (42.7 in long, 25.1 in high, 18.4 in forward flange). Fix round 2: length,
  height, dry weight and the 1,846 lbf rating are also in **EASA TCDS IM.E.016 Issue 13** (easa.europa.eu, HTTP 200).
- **FAA Aircraft Characteristics Database** (already in `data/ga_types.json`): 38.7 / 30.7 / 10.9 ft.
- **Cirrus AFM P/N 31452-001** (third-party hosted copy; reference only): Fig 1-1 three-view with dimensions (11.1 ft,
  18.3 ft, 14.7 ft, 11.2 ft track), Fig 1-2 interior dimensions with FS ticks, tyres, walk-around list, light counts.
- Cirrus product page, AOPA Pilot (July 2017) flight report, FAA FSB report, Wikipedia (secondary), Lednicer's airfoil guide.
- **Refused**: Wikimedia Commons API (HTTP 429). FAA DRS's data-pull API needs a key (403); the two TCDS PDFs and the
  FSB report were then opened through the public DRS web viewer in headless Chromium (no login, no key, no bot check).
  **Decided in fix round 3 (decision (a), orchestrator decision 2026-11-13 under the owner's delegation; the owner may
  overrule):** the DRS public web viewer is the FAA's intended public interface for type certificate data sheets, so the
  values read there (every control-surface travel and flap deflection, datum, weights, fuel, the FJ33-5A flange
  diameters) are **obs** with the TCDS citation in SF50_FACTS and in the test labels (fix round 2 had marked them
  "inf (DRS)"). Fix round 2 had also found the FSB item word for word in the FSB Rev 4 *draft* on faa.gov
  (https://www.faa.gov/aircraft/draft_docs/fsb/FSBR_SF50_Rev_4_Draft.pdf, HTTP 200) and the FJ33-5A length / height /
  weight / rating in EASA IM.E.016. No DRS access was made in fix rounds 1-3.
- Fix round 1: Cirrus product-page photographs (fetched by the review, scratch only, never committed) were used
  qualitatively for the wing-tip and nacelle shapes (SF50_FACTS S11).

Conflicts kept visible: span 38.7 ft (three sources, used) vs 38.3 ft (EASA); EASA's "3.23 m (10.9 ft)" read as a
transposition of 3.32 m; the AFM side view draws the cabin crown higher than the AFM interior figure and front view
(the model follows the latter two).

**Digitised drawing data (decision (b), fix round 3):** every reading of the AFM figures (outlines, stations, per-butt-line
water lines, angles, raster scales and registrations) is local reference data in the gitignored
`refs/cache/local/models/afm_sf50_meas.json` (with a `src` note); committed files keep only the fitted model parameters with
a one-line basis (as `pc12/` does), and the drawing-vs-model checks of `tools/models/test_models.mjs` print SKIP in a
clean clone. Dimension labels printed on the figures (e.g. "11.1 ft (3.4 m)") are published values and stay quoted.

## 2. Frame and origin

Model axes as `pc12/`: **x = FS, metres aft of the TCDS datum** (the nose tip is at FS 0.900 [inf]), y = butt line
(+ starboard), z = height above ground, aircraft static on its gear. glTF axes (pc12 `to_gl`): **X = starboard,
Y = up, Z = aft**. **glTF origin = FS 0 (TCDS datum), butt line 0, ground plane.** The main-gear ground contact is at
glTF (0, 0, 5.353) ± 1.707 in X; `js/aircraft/glb.js` measures it from the tyres (M2's test: origin_gl [0, 0, 5.353],
track 3.414, nose contact 3.305 ahead). Rest pose: gear down and locked, flaps up, surfaces neutral, doors closed; the
nose-gear doors are closed in the geometry and open through their pivot (`seq: 'down'`).

## 3. Method

1. **Digitising the reference drawings** (scratch only; readings local since fix round 3): AFM Fig 1-1 was rasterised; enclosed regions (windows,
   door, nacelle, V-tail, strakes, gear doors, wheels) were segmented and measured row by row, outlines read on gridded
   crops. Scales come from the drawing's own dimensions (the figures are not drawn to one scale; registrations local).
   Fig 1-2's FS ticks give the cabin OML outline, which anchors the station of every window and the nose (FS 0.900 m:
   three windows agree within 4 cm).
2. **Fuselage**: lofted like `pc12/model/fuselage.py` from four control lines (crown, keel, half-breadth, max-breadth
   water line) and a super-ellipse section law whose exponents flatten the belly over the wing box (the wing-root fairing,
   lowest at 0.60 m). Overlay of the lines on the AFM views: [scratch images, not committed]; the check renders below show
   the result. Openings are cut with signed-distance fields and `trim` (marching triangles): two wrap-around windshield
   panes with an 8 cm centre post (plan outline + sill line), squircle cabin windows (3 port incl. the door window, 3
   starboard incl. the egress window), the clam-shell cabin door (parallelogram, upper half up / lower half down), the
   baggage door, the nose-gear bay. Glass is recessed 5–6 mm behind black seals with inward reveals; the windshield has a
   dark frame band. Panel lines (radome joint, CAPS cover ahead of the windshield, door seams) are thin seam bands.
3. **Livery** (original, neutral, no logo): white, light-grey belly, slate-blue swoosh along the lower side rising to the
   tail with a cool-grey pin-stripe; de-ice boots dark grey; bare-metal heated inlet lip. **Registration panels**: blank
   1.25 × 0.30 m areas on both sides of the aft fuselage (separate parts `reg_panel_L/R`, material `reg_panel`,
   `info.reg_panel` = centre / normal / up / text direction) — the runtime may fill them only for aircraft not flagged
   LADD/PIA (D1); the videos are type-only.
4. **Wing**: planform solved from the TCDS area and the 38.7 ft span with the chord ratio (0.643, tip fairing / fuselage
   side) and LE sweep (5.65°) fitted to Fig 1-1 (model chords 1.838 / 1.181 m after the scaling to the area), root TE
   fillet reaching the 18.3 ft station; NACA 23015 → 23012 (the real section is unpublished; the 230xx family is
   documented on the Citation I and is exactly defined); dihedral 4.8°, washout 3° [inf]. Wing skin trimmed at
   the fuselage OML. Single-slotted flaps on a drop hinge (0/15/39°), ailerons with the left trim tab and the right servo
   tab, flap-hinge fairings, aileron fences, root vortex generators, pitot probes, static wicks. Main-gear wells: a disc
   for the stowed tyre plus the leg slot, closed by the leg door when retracted.
   **Wing root height (fix round 2)**: `Z_LE0` 0.735 → **0.835 m**, fitted to the AFM Fig 1-1 front view registered on
   the main-wheel bottoms and checked against its fuselage max-width line (readings and residuals in the local reference
   file; `tools/models/test_models.mjs` checks mid-line, upper-line slope and the wing top vs the fuselage max-width line
   when it is present). The remaining difference on the upper / lower lines is section thickness (the drawn outline is
   thicker than NACA 230xx [inf]). The belly fairing (keel 0.60 m, fitted to the AFM side view) is unchanged; the main-gear
   trunnion (WL 0.820 → 0.920), the leg-door top, the stowed-tyre well (BL 1.096 → 0.996) and the leg slot moved with the
   wing (`G.WING_DZ`), so the retracted gear is still flush (test).
   **Wing tip (fix round 1, height and shape revised in fix round 2)**: an upswept, aft-raked tip lofted from the tip rib
   (BL 5.50) with banked sections (`sf50_wing.py TIP`, `tip_extension`): the leading edge rounds aft over a ~0.3 m body,
   the outer part turns up 70° from the wing plane (bend radius 0.060 m) into a **short pointed fin whose top is 0.13 m
   above the tip chord plane, i.e. 0.058 m above the extrapolated upper-surface line**, fitted to the AFM Fig 1-1 front
   view (fix round 1 had a fin about twice as high, a broad plate with a 0.265 m square top, and its test cited the figure
   for a limit it does not show; the reading is local reference data since fix round 3) — with the top 0.16 m behind the
   rib trailing edge and a 0.05 m top chord (the leading edge rakes aft past the rib trailing edge, `le_top` 1.10), the slender raked spike of the Cirrus
   photos; the photos read taller than the drawing, but are perspective views: the height follows the orthographic
   drawing (conflict in SF50_FACTS). The body reach is solved so the outermost point is at the 38.7 ft span (model 11.793 m). Lamps
   are **flush**: a clear lens cut into the tip leading edge (inboard 60 % landing light, outboard 40 % red / green
   position light, reflectors 14 mm behind it, dark rim) and a clear strobe lens on the outboard face of the upturn.
   Evidence: AFM Fig 1-1 plan / front, Fig 8-1, Cirrus photos; every number is inferred.
5. **V-tail**: 38° dihedral, root 1.29 m / tip 0.70 m chord, NACA 0010 [inf], tip height 3.325 m. Ruddervators
   (66 % hinge, pivot kind `ruddervator` with `pitchRange [-20, 15]`, `side ±1`, `yawGain 9`) with pitch servo / trim
   tabs; boots; tip caps. **Ventral fins** canted 40° from vertical below the tail, each with a yaw-SAS surface at its aft
   end (kind `rudder`, ±15°).
6. **Nacelle**: cowl along a 4° nose-down centre line, model inlet highlight FS 5.865, exit FS 8.010 (fitted to Fig 1-1), short diverter under the
   inlet, D-to-round inlet duct to an 18-blade fan (0.41 m, kind `spin`), exhaust nozzle with a 12-lobe mixer and plug,
   aft pylon fairing, pylon NACA inlets and louver, metal exhaust tray on the tail cone. The FJ33-5A's 1.085 m length fits
   between the fan face and the exit (1.805 m). **Fix round 1** (`sf50_nacelle.py section_yz`, `FILLET`, `WAIST`): the
   upper half keeps the AFM side top line and plan half-width (the fitted value in `sf50_geom.py`; the reading is local
   reference data, decision (b)); the lower half is a flatter D at the inlet and
   blends aft into concave fillets that leave the cowl side vertically and meet the fuselage crown tangentially 0.13 m
   outboard (FS 6.4-7.3, tapering to 0.07 m at the exit); the inlet opening is a D with a flat bottom; an 8.5 % waist
   0.13 m behind the highlight leaves the polished lip ring ~2 cm proud (lip half-width 0.344 m at FS 5.92, waist 0.324 m
   at FS 6.03). Before: one super-ellipse tube lying on the spine with the inlet the size of the tube.
7. **Gear**: trailing-link mains (oleo, link inboard of the tyre, shock absorber, brake disc and caliper, leg-mounted
   door whose plane leans so it lies along the sloping lower skin when stowed) retract **inward 90°** about a fore-aft
   axis at the trunnion (WL 0.920 since fix round 2); the tyre stows flat in the wing. Castering nose gear (oleo, fork, torque links, drag brace,
   **landing light** on the strut) retracts **forward 100°** into the keel bay between two doors. Retracted-gear
   clearance is checked by M2's test: nothing protrudes more than 1 mm except inside the openings, and (fix round 3)
   no gear vertex stands above the upper skin. **Fix round 3 (S1)**: stowed, the inboard side of the main gear faces up,
   so the trailing link lies on top of the flat tyre; its end stood 3.5-4.5 mm above the wing upper skin at BL 1.02 (12
   vertices per side). The link now runs 0.092 m inboard of the wheel centre (was 0.100) with a 0.020 m tube (was 0.022)
   (`sf50_gear.py LINK_DY, LINK_R` [inf]): its top is 5.5 mm below the skin, 0.9 mm clear of the tyre sidewall.
8. **Cabin**: panel with two large displays and two touch controllers, glareshield, side yokes, 2 crew + 2 middle +
   3 aft seats at the AFM Fig 1-2 stations, lining, carpet, bulkheads — visible through the glazing.
9. **Lights**: named anchor nodes `light:<kind>` with `extras.light = kind`: navL / navR (behind the tip lenses), strobeL /
   strobeR (strobe lenses on the upturns), landL / landR (tip landing lights), taxi (the nose-gear lamp, which the AFM
   calls the nose landing light; moves with the gear), tail, strobeTail and iceLight. Since fix round 1 the runtime keeps
   every kind and draws strobeTail in phase with the tip strobes (3 anti-collision lights, AFM); iceLight is kept, not
   drawn. The SF50 has no rotating beacon (AFM: anti-collision = 3). Per-tip landing-light count and positions are [inf]
   (SF50_FACTS "Lights").

Smooth shading on the lofted skins (one continuous grid per surface); crisp edges at every trimmed opening, door, seam,
control-surface gap and rib (separate vertices, flat rims).

## 4. Checks (model vs source; `sf50_meta.json` → `checks`)

| check | source | model | Δ | source |
|---|---|---|---|---|
| overall length | 9.357 m | 9.357 | 0 mm | FAA ACD / AFM 30.7 ft |
| span (to the outermost tip point) | 11.796 m | 11.793 | −3 mm | FAA ACD / AFM / Cirrus 38.7 ft (EASA 11.67) |
| height | 3.322 m | 3.325 | +3 mm | FAA ACD / AFM / Cirrus 10.9 ft |
| wing reference area | 18.18 m² | 18.18 | 0 | EASA TCDS / AFM |
| main-gear track | 3.414 m | 3.414 | 0 | AFM 11.2 ft |
| wheelbase | 3.322 m | 3.305 | −17 mm | FAA ACD row 368 `Wheelbase_ft 10.9` (fix round 3; before: the model's own drawing-fitted value); the model's axles are fitted to the AFM side view [inf] |
| V-tail tip to tip | 4.481 m | 4.490 | +9 mm | AFM 14.7 ft |
| nose → wing root LE | 3.383 m | 3.383 | 0 | AFM 11.1 ft |
| nose → wing root TE (fillet) | 5.578 m | 5.585 | +7 mm | AFM 18.3 ft |
| fuselage max width (OML) vs cabin width | 1.549 m (61 in) | 1.696 | +147 mm = the walls [inf] | AFM Fig 1-2 table / Cirrus 5.1 ft (fix round 3; before: a reading of the Fig 1-2 outline, now local); the OML is fitted to that outline |
| main tyre OD | 0.457 m | 0.457 | 0 | AFM 18 × 5.5 |
| FJ33-5A length in the nacelle | 1.085 m | 1.805 available | ok | TCDS E3GL |

M2's `node tools/models/test_models.mjs` (run 2026-11-13 after **fix round 3** on build 2026-11-13T21:13:45Z, sha256
49242e41…; fix round 2 ran on 37e2952f…): parse (0 bad indices, unit normals), ACD length / span / height within 0.1 %, origin on the main-gear contact,
nose wheel on the ground, nothing below the ground, pivots present (door 3, flap 2, aileron 2, tab 4, ruddervator 2,
rudder 2, spin 1, gear_door 2, gear 3; none unsupported), pivot origin = node origin, left / right symmetry, **every
control-surface travel vs the TCDS table with the sign measured from the trailing-edge motion** (ailerons, LH trim tab,
ruddervators, ruddervator tabs [−7, +18], yaw SAS; full pull / push / yaw / roll; the geared tab reaches +8 / −6 without
clamping; labels **obs** TCDS A00018CH since fix round 3), gear retracted flush, **no gear vertex above the upper skin**
(fix round 3: worst −5.5 mm, the link end; was +4.5 mm), every light node kept (3 anti-collision drawn), registration
panels with text_dir, **wing outline vs the AFM front view** (mid-line, upper-line slope, wing top vs the fuselage
max-width line), **wing-tip rise vs the AFM front view** (model 0.058 m) — both from the gitignored local reference file
since fix round 3 and SKIP in a clean clone — **wing tips** (outermost point 5.897 m = span / 2; top chord 0.05 m; lens = an
open patch on the skin opening, rim within 2 mm; lamps behind it), fan motion vectors at 40 / 59 / 178 rad/s with an
off-axis point, builder sources = the recorded hashes, **nacelle** (lip 2.0 cm proud of the waist, fillet foot 0.422 m
half-width at FS 6.80), the traffic frame — all PASS (with the local file present; the 3 AFM checks SKIP without it).

Model size: 43 parts, 463,121 triangles, 284,128 vertices, **7,051,212 bytes** (KHR_mesh_quantization; fix round 2:
7,051,052 B; fix round 1: 463,845 / 7,059,280), comparable to pc12.glb (current, fix round 3 iteration 2: 6e349329…, 423,853 triangles drawn; fix round 3: c46fe4fb…, 415,703; M2's fix-round-2 import: 9ccfd9a5…, 410,834). (The size M1 reported for the reviewed build, 6,864,552 B, was wrong:
that file had 6,864,788 B; superseded.)

## 5. Check renders (`docs/phase3/`, numpy rasteriser, not the app renderer)

- `sf50_side.png`, `sf50_top.png`, `sf50_front.png` — orthographic, dimensioned (blue = published value, orange = inferred).
- `sf50_34.png` — 3/4 front, gear down. `sf50_34rear.png` — flaps 39°, half pull, roll 0.4, cabin door open.
- `sf50_gearup.png` — from below, gear retracted. `sf50_nose.png`, `sf50_tail.png`, `sf50_inlet.png` — close range.
- **Fix round 3**: `sf50_gearup.png` re-rendered from build 49242e41… and looked at (the S1 change is inside the wing,
  invisible from below); new hwd3d-renderer still `viewer_sf50_gearup_root_top.jpg` (gear up, starboard wing root from
  above: clean upper skin; the recheck's close-up camera on the old build showed the shield-shaped patch, the same camera
  on this build shows plain skin, scratch `out/fr3_sf50/`). The other eight check renders and M2's `viewer_sf50_*` stills
  are of build 37e2952f…, which differs only in the trailing link (8 mm, inside the wing when stowed) and the light-anchor
  metadata; their captions carry `superseded` with exactly that note (not re-rendered: CPU budget).
- All nine re-rendered in fix round 2 from build 37e2952f… and looked at (fix round 1: 0db80513…); captions with the
  model hash in `docs/phase3/SOURCES.json` (written by `render_checks.py`). The hwd3d-renderer stills of this build
  (M2's files) include `viewer_sf50_tip_front.jpg`, `viewer_sf50_tip_rear.jpg`, `viewer_sf50_nacelle.jpg`,
  `viewer_sf50_lights_dusk.jpg`.

Looked at against the AFM three-view (overlays in scratch, never committed): profile, plan and front silhouettes,
window and door stations, nacelle top line and inlet station, V-tail angle and tip, gear stance agree to within the
drawing's own tolerance (~2 %). M2's viewer stills of this model in the real renderer are `docs/phase3/viewer_sf50_*.jpg`
(M2's files).

## 6. Inferred / open (to check against photographs when allowed)

Window shapes, windshield outline and frame width, door split line, wing-tip numbers (upturn angle, height, rake) and
the lamp layout, nacelle fillet width and waist, the pylon, wing dihedral, incidence and airfoil, flap / aileron spans
and the drop-hinge flap, V-tail airfoil and hinge line, ventral-fin shape and cant, gear geometry (trunnion, link,
**retraction directions: no primary source found**, nose doors), light positions and the per-tip landing-light count,
antenna positions, interior layout. The wheelbase (3.305 m) is drawing-derived and agrees with the FAA ACD (3.322 m);
the turning-radius table suggests ≈3.0 m. Renderer: nothing is required from Phase 3b for this model.

## 7. Review fix round 1 (2026-11-13)

| finding | disposition |
|---|---|
| wing tips: no upswept, raked tip; protruding box lamps | **fixed**: §3 item 4; test "wing tip R / L" |
| nacelle: tube on the spine, inlet = tube | **fixed**: §3 item 6; test "nacelle" |
| ruddervator tab range inverted | **fixed**: `sf50_tail.py` range [−7, +18]; gearing −0.4 kept (a servo tab moves opposite to its surface); test "travel rv_tab_* vs type certificate" and the functional controls check |
| FAA ACD gear values not recorded | **fixed** (docs): SF50_FACTS wheelbase / track rows; the PC-12 ACD values are in `docs/phase3_models.md` |
| lights provenance (landing-light row misread) | **fixed** (docs): SF50_FACTS "Lights"; per-tip count marked inf |
| gear retraction directions unsourced | **not resolved**: searched (AFM text, AOPA, web search 2026-11-13), nothing found; kept **[inf]**, to be named in the video credits |
| DRS web-viewer access (two findings) | **deferred to the owner**: question below; values marked "not independently verified" |
| digitised AFM tables committed | **deferred to the owner**: question below |

Questions for the owner (resolved in fix round 3 by orchestrator decisions (a) and (b) under the owner's delegation,
§9; the owner may overrule):
1. **DRS access.** After DRS's data API refused with 403 (key required), M1 read TCDS A00018CH, E3GL and the FSB report
   through DRS's public web viewer in headless Chromium (no login, no key). Is that the intended public interface
   (record the decision in PLAN.md 6a/6b), or a work-around under your rule? If the latter, the control-surface travels
   and the FJ33-5A envelope have no other public source we found and stay "not independently verified".
2. **Digitised drawing data.** `sf50_geom.py` commits control lines and stations fitted to the third-party-hosted Cirrus
   AFM drawings (pixel scales in SF50_FACTS §3). pc12 keeps "data extracted from" manufacturer drawings in a gitignored
   cache but commits its fitted parameters. May these SF50 tables stay committed, or should they move to
   `refs/cache/local/` (the build would then need that cache)?
3. **Fix round 2 addendum.** The digitised numbers now also include the AFM Fig 1-1 front-view wing outline (7 butt
   lines, upper / lower WL), the tip-top height and the wing-top-to-fuselage-line distance in
   `tools/models/test_models.mjs` (`AFM_SF50`), as measured facts with their source; they fall under question 2.

## 8. Review fix round 2 (2026-11-13)

| finding | disposition |
|---|---|
| wing ~0.10-0.11 m low vs the AFM front view (Z_LE0 from "belly = root lower surface") | **fixed**: `Z_LE0` 0.835 (§3 item 4, SF50_FACTS "Wing root height"); gear trunnion / wells / slot / leg door moved with it (`G.WING_DZ`); new test "wing front-view outline vs AFM Fig 1-1" (mid-line, upper-line slope and top vs the fuselage line within their limits; the readings are local since fix round 3); retracted gear still flush |
| tip fin twice the AFM front-view height, square top; test limit cited Fig 1-1 wrongly | **fixed**: fin top 0.058 m above the extrapolated upper line (fitted to the front view), pointed 0.05 m top chord; the test now measures the rise the way the figure is read (above the extrapolated upper line, fit BL 3.5-5.4), limits from the front-view reading (local reference file since fix round 3), top chord ≤ 0.08 m [inf: photos]; drawing-vs-photo conflict in SF50_FACTS |
| fan motion vectors (runtime) | fixed by M2 (`docs/phase3_models.md` §10) |
| provenance: build commit did not contain the builder | **fixed**: `_provenance` records `builder_state` ("working tree (uncommitted: tools/models/sf50 is not in git)"), sha256 of every builder and pc12-kernel source and a tree hash; SOURCES.json carries them; the test fails if a source on disk differs from the recorded hash. Rebuild from this tree is bit-identical (checked: the fix-round-1 sources reproduced 0db80513… before the edits, the new ones 37e2952f… twice) |
| DRS access route (owner) | **deferred to the owner**, narrowed: FSB item and FJ33-5A envelope / rating moved to non-DRS sources (S12 faa.gov FSB draft, S13 EASA IM.E.016); control-surface travels and flap deflections stay DRS-only and are now **inf (DRS)** in SF50_FACTS and the test labels; the SF50 video must show the inf marker for the control motion unless the owner approves the route → **decided in fix round 3** (decision (a), §9): obs |
| digitised AFM data committed (owner) | **deferred to the owner** (question 2 + addendum 3) → **decided in fix round 3** (decision (b), §9): local reference file |
| gear retraction directions unsourced | **deferred (no source found)**: AFM §7 refers to the non-public Pilot's Information Manual; AFM 3A-15 alternate extension does not say which way the legs swing; web search (Twin & Turbine Apr 2019, AOPA, Wikipedia, Skybrary) has nothing. Stays **[inf, unverified]**; the take-off video credits must carry the inf marker, or the owner supplies a source (PIM §7 or a retraction video frame) |

## 9. Review fix round 3 (2026-11-13)

Orchestrator decisions for this round (2026-11-13, under the owner's delegation; the owner may overrule): **(a)** FAA DRS's
public web viewer (no login, no key, no bot check) is the FAA's intended public interface for type certificate data sheets;
values read there from TCDS A00018CH / E3GL are **obs** with the TCDS citation. **(b)** Digitised measurements of the AFM
figures are not committed; they live in the gitignored `refs/cache/local/models/afm_sf50_meas.json`, the tests SKIP without
it, and committed code keeps only fitted parameters with a one-line basis.

| finding | disposition |
|---|---|
| S1: with gear 0, 12 vertices of each stowed main-gear leg 3.5-4.5 mm above the wing upper skin at the root | **fixed**: trailing link 0.092 m inboard of the wheel centre, tube 0.020 m (`sf50_gear.py LINK_DY, LINK_R` [inf]); link top now 5.5 mm below the skin (0 vertices above), 0.9 mm clear of the tyre. New test "gear retracted: no gear vertex above the upper skin" (upper skin interpolated in the upward-facing skin triangles at each gear vertex's plan position, topmost counts; runs for every model). Renders: `sf50_gearup.png`, `viewer_sf50_gearup_root_top.jpg` (looked at) |
| V1: light-anchor `src` held free text in `sf50_meta.json` / `pc12_meta.json` (check_airport fails); SOURCES entry for `sf50_meta.json` without made_by / note; no ATTRIBUTION row; check_airport did not scan docs/phase3 | **fixed**: `sf50_assemble.py light_src` writes `src` obs / inf and the text to `basis` (GLB node extras and meta); `import_pc12.mjs` does the same for the PC-12 meta lights (takes effect at the next PC-12 import); `import_pc12.mjs` writes made_by / note for the SF50 meta entry; `docs/ATTRIBUTION.md` has a Phase 3 models / renders row; `tools/check_airport.py` scans docs/phase3 (js/aircraft/models was already in js/) |
| (a) DRS values inf (DRS) | **obs** with the TCDS citation: SF50_FACTS (S1 / S3 / S8 rows, travel rows), the test labels (`TRAVEL`), this document. The take-off video needs no inf marker for the control motion; the gear retraction directions stay **inf** (no source) |
| (b) digitised AFM data committed | **moved** to `refs/cache/local/models/afm_sf50_meas.json` (front-view wing outline per butt line, wing-top distance, tip rise, scales, registrations, every reading quoted in SF50_FACTS / `sf50_geom.py` / `sf50_wing.py` comments / this document), with a `src` note. `test_models.mjs` `loadLocalRef(name)` (shared with the PC-12 checks): the wing-outline and two tip-rise checks SKIP when absent (checked by moving the file away: 3 SKIP, no FAIL from them). The meta checks compare with published values only (wheelbase: FAA ACD 10.9 ft; fuselage width: the 61 in cabin) |


Runs after fix round 3 (build 49242e41…, bit-identical on a second build into `out/fr3_sf50/rebuild`; `git status pc12 sfo3d`
clean): `node tools/models/test_models.mjs` — every SF50 check PASS (with the local reference file; 3 SKIP without it, 4
since fix round 3 iteration 2, which made the nacelle's AFM plan-view comparison a local-reference check, finding F1);
the run reports 3 FAIL that are not SF50 items: the PC-12 "no gear vertex above the upper skin" (the new check: 4 vertices
of the stowed PC-12 oleo piston 1.9 mm above the wing upper skin, PC-12 variant), the Phase 3b gaDims diff (a new
`gaDims` call in `js/live/traffic.js`, Phase 2 work in progress) and `docs/phase3_models.md` not naming the new SF50 hash.
`python3 -B tools/check_airport.py` — SOURCES coverage now includes docs/phase3 (160 files, 0 without an entry, 0 entries
without made_by / note); "src values" still FAILS on the committed `pc12_meta.json` light anchors until the next PC-12
import (`import_pc12.mjs` now writes `src` obs / inf + `basis`; dry run: all 10 anchors `inf`); `sf50_meta.json` is clean.
(Those three FAILs were closed by M2's PC-12 fix-round-3 build and doc updates; after fix round 3 iteration 2 the whole
suite has 0 FAIL, with and without the local reference data: `docs/phase3_models.md` section 6.)

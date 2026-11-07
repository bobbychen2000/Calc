# Aircraft track close-out (review of 4 Nov 2026): changes for other owners and requests

From: owner of `js/aircraft/**`, `js/live/aircraft.js`, `js/live/lookup.js`, `js/live/models.js`, the docking math in
`js/live/gates.js`, `data/models/manifest.*`, `data/liveries/**`, `tools/models/**`, `tools/liveries/**`.
Checks: `python3 tools/models/check_dims.py` (before: 24 flagged / 24 explained; after: 27 flagged / 26 explained /
1 unexplained, with stricter rules, see §3), headless docking census (gates.js `LiveGateSystem` without WebGL, every
stand that accepts the type: docking counts unchanged for all 16 types tested).

## 1. What changed for everybody who reads `TYPES` or draws the models

| Field / API | Change |
|---|---|
| `T.fit.pitch` `{a, x0, y0}` | New. Models on their own gear (FG 737-800, 777-200ER / -300ER) are pitched nose-down by `a` rad about the main-gear contact `(x0, y0)` (stretched model frame), so the nose tyre touches the ground too. Before, the nose tyre floated 0.165 m (737) / 0.18 m (777). 737 family 0.51-0.83 deg (737-800 0.60), 777 family 0.33-0.41 deg. The ACAPs show both types nose-down at rest: 737-800 entry door 1 sill 2.59-2.74 m vs door 2 2.97-3.12 m (D6-58325-7 Rev C §2.3.2), about 0.8 deg. `js/live/aircraft.js placement()` applies it as a rotation of the model matrix, so every caller of `ac.placement()` (WebGL2 and `js/three/aircraft.js`) gets it. The vertices and the shader's model-space positions are unchanged. |
| `T.dockSill`, `T.dockX1` (737 family) | 3.122 -> 2.967 m and 5.246 -> 5.205 m: the drawn door 1L in the nose-down stance. |
| `T.dockHW` | Now taken at door 1's own station. It is the widest skin over the door opening (sill to sill + 1.9 m), measured on planar cuts of the mesh (`MODEL_FEATURES.sec.hwf`), so the flat bellows front never cuts the skin. Before, it was an ellipse through the tallest section within +-2 m. Widebodies: 0.17-0.24 m less (777-300ER 3.039 -> 2.852, 787-9 2.733 -> 2.622, A350-900 2.868 -> 2.653, A380 M1L 3.200 -> 2.962). A320 / CRJ: +0.06 m, because the old value put the bellows 0.06 m inside the skin. |
| `T.dockHW2` | New: the skin at the second bridge's door (777-300ER 3.078, 787-9 2.882, A380 M2L 3.540). `gates.js doorOf(..., 2)` uses it. |
| `T.dockHW3` | New, for the A380 U1L (bridges_aircraft.md): 3.34 m measured at the sill. The gates.js ellipse estimate (~3.0 m) is no longer used. |
| `T.dockSkin` | New: `{dz: 0.25, 1: [...], 2: [...], 3: [...]}`, the rendered skin half-width (m) at each docking door from the sill up to sill + 3 m, so a bellows can follow the skin (see §2, bridges). |
| 757 span | `TYPES.b752/b753.wing.span` is now 41.07 m, the blended-winglet span the model carries. Source: Boeing Airport Technology "Wingspan Increases Due to the Addition of Winglets", APB data, `refs/cache/acap/wingletspans.pdf`; the FAA ACD gives 41.09 m. Before, ground physics, the far LOD and the stand fit used the plain 38.05 m while the drawn tips reached 39.16 m. The model's tip is now fitted to 41.07 m. This agrees with `tools/stands/geom.py` (41.1). |
| `typeForIcao` (business jets) | Length, span and tail height now come from the FAA Aircraft Characteristics Database (public domain, `refs/cache/faa/faa_aircraft_char_database.xlsx`, `tools/models/faa_acd.py`; `js/aircraft/fit.js BIZ`). The span is fitted separately from the length: GLEX was 24.03 m, now 28.65 m; GA5C / GA6C lengths were 1.5 / 1.1 m too long. New: E145, C25A, GALX. The result now carries `generic: 'business jet' | 'regional jet'` (E135 / E145) and `engines` (3 for FA50 / F900 / FA7X / FA8X, which are drawn with the CRJ's two). `BIZ_LEN` is kept (lengths). |
| `parseCallsign(cs, info)` | Optional 2nd argument. With `{vehicle: true}`, emitter category C1-C7 or type SERV / GRND / TWR it returns `{airline: null, vehicle: true, label: 'Airfield vehicle'}`. |
| `MODEL_FEATURES` | New `contact` (nose / main tyre bottoms), `finTop`, and `sec.f` / `sec.hwf` (half-widths at fractions of the section height over the forward 45 %). `tools/models/model_features.py` now keeps the source-model door objects when the source models are absent: it was re-run without them, and every existing feature is reproduced exactly. |

## 2. Requests

| File (owner) | Request |
|---|---|
| `js/live/traffic.js` (realtime), ~line 617 | `tr.cs = parseCallsign(I.flight)` -> `parseCallsign(I.flight, { vehicle: tr.vehicle, category: I.category, icao: I.dbIcao })`, and parse again when `tr.vehicle` becomes true. Then SFO's airfield operations vehicles (N3xxQX, type SERV, callsigns OPS12 / OPS16: 12 in the 4 Nov recording) are no longer shown as the airline "Jet-Ops". |
| `js/live/ui.js` (UI) | When `tr.cs.vehicle`, show `tr.cs.label` ("Airfield vehicle") in place of the airline line. |
| `js/live/app.js` (app) | (a) `modelNote`: use `m.generic` ("business jet" / "regional jet": E135 / E145 are not business jets), and when `m.engines === 3` add "three-engine type drawn with two engines". (b) Still open from `aircraft_models_777.md`: b772 / b77w in the model-source table, which currently prints "FlightGear/FlightAirMap undefined". (c) Still open: `setOccupant(G, ..., icao)` needs `{freighter: isFreighter(...)}`, else a 777F / 747-400F / MD-11F gets an L2 bridge at a door it does not have. |
| `js/live/traffic.js:605` (realtime) | Still open from `liveries_brand.md`: `liveryForAirline(al)` gets no reg / hex / type, so the brand is resolved from a debug hook. |
| `js/live/entry.js:12` (app) | Still open: `MODEL_KEYS` lacks b772 / b77w. |
| `js/live/gates.js` bridge geometry (bridges) | (a) The bellows front is a flat plane at `T.dockHW`. Where the skin narrows above the sill, the gap at door mid height is: 787-9 0.19 m, 787-8 0.11 m, A330-300 0.10 m, A350-900 0.10 m, 747-8 0.10 m, 757 0.09 m, 737 0.06 m. At the A380 U1L the skin is 3.35 m at the sill, 2.97 m at mid height and 2.27 m at sill + 2 m. `T.dockSkin[door]` gives the profile per 0.25 m, so you can shape the bellows bands or tilt the canopy. (b) The gate-number sign on the tunnel side that faces the stand reads mirrored ("B13", review image `out/review_aircraft/rev2_gate_B13_zoom.png`). |
| `js/world/gates.js` (legacy scene) | The second bridge's door should use `T.dockHW2 ?? T.dockHW`. |
| `tools/drawing/common.py` (drawings) | Its port of `applyStretch` draws the 737 / 777 level. The app now pitches them by `T.fit.pitch`: rotate about `(x0, y0)` in the stretched model frame (`tools/models/check_dims.py rendered()` shows how). |
| `tools/live/gatecheck.py:119` (realtime tools) | It still derives business-jet spans as CRJ200 span x length ratio. Please read the span from the new `BIZ` export (`[length, span, tail height, engines]`, FAA ACD) or from `typeForIcao(k)` -> `TYPES[t].wing.span`. |
| `tools/stands/geom.py` (stands) | 767-300ER: TYPES keeps the plain 47.57 m (ACAP; the model has a plain tip), while geom.py uses the 50.9 m APB winglet span. Which SFO 767-300ERs carry winglets (UAL / DAL fleets) is not sourced. Keeping the larger value for clearance is conservative; please say so in its source note. |
| static / stands: `realtime_closeout.md` §3 (B777 antenna reference) | This track cannot measure it: no manufacturer document here gives the GPS antenna station. Please add the B777 / B787 / A350 families to the per-family ADS-B medians of `static_fixup.md` §1.6 (your method). |

## 3. check_dims changes

- Heights above the ground are now flagged beyond +-0.08 m (the ACAPs' nominal +-3 in), not 1 % of the length.
- The fuselage top is measured as `fit.js crownOf` defines it: centre-plane section cuts with a 5 m median. Before, it was the highest body vertex, which takes an antenna or dorsal fairing for the crown and reported A350 +0.35 m, A380 +0.27 m, CRJ200 +0.17 m.
- New rows: nose and main tyre bottom above the ground (all 0.00 m now; 777 bogie front axle -0.01 m), and bridge 2 cab floor against the published door-2 sill.
- 777 REF now has crown / door-1 sill / door-2 sill. The letters A / B / D are checked on the rendered D6-58329-2 §2.3.2 drawing.
- The 757 REF span is the winglet span (41.07 m). AC A321 is cited at Rev 35 (Jul 01/26). The A220 ACP is noted as available but not fetched.
- The 737NG door-1 sill (+0.23 m) stays flagged and explained (§4.1). The one unexplained flag is A333 belly at 0.5 L, 1.68 m against BF1 1.85-1.86 m. It appeared because of the stricter tolerance; the BF1 station on the AC A330 figure is not re-checked, because the document was not restored.

## 4. Open in this track (blocked, or the evidence does not support a change)

1. **737NG door-1 sill**: 2.97 m against 2.59-2.74 m (+0.23 m, 0.15 m beyond +-3 in). The FG door object fills its opening in the skin: a planar cut at the door station has one skin layer. Lowering it means re-cutting the skin in the FG 737-800 source and re-baking every b738 livery. The source models and `refs/cache/models_orig/` were not restored. The bridge meets the drawn door, so cab floor and door outline agree. 737 MAX: 2.97 m, within 2.77-3.07 m.
2. **Missing bakes are blocked**: FDX / CAL / EVA B77L, ACA-X CRJ7, AAR A388, plus CSG and JSX, which have no brand at all. `tools/liveries/build.py` needs the pre-atlas models in `refs/cache/models_orig/*.sfom`, which were lost with the container. A trial bake failed with FileNotFoundError on `models_orig/b77w.sfom`, and the fleet edits were reverted. Re-creating them needs `tools/convert_models.py` on the FAM / FlightGear sources. FDX / AAR / ACA-X designs would carry over. CAL / EVA cargo titles, CSG and JSX need photo references and the owner's approval.
3. **737-900ER window row: the proposed fix is rejected** (737-800 row + plugs). The 900ER has the mid-cabin exit pair aft of the wing, like the 737-9. The MAX-9 row shows it as a 2.2 m gap at 25.2-27.4 m; the 737-800 row has no such gap, so a derived row would paint windows over that exit. Forward of the wing the NG row starts at 5.64 m against the MAX's 6.11 m. A splice (NG forward + plug, MAX-9 aft) would fit, but it needs a 737-900ER drawing to verify. The MAX-9 row is kept and documented as inferred.
4. **A321neo Cabin Flex (ACF) door layout per operator**: needs fleet / seat-map sources for AAL / DAL / JBU / ASA.
5. **E175 window stations**: needs Embraer APM-2259 figures (not restored) or a calibrated photo.
6. **767-300ER winglets per operator**: needs a source (see §2, stands).

## Round 2 (review round 1 of 5 Nov 2026: aircraft-v1 .. v5)

Checks: `python3 tools/models/check_dims.py` before 27 flagged / 26 explained / 1 unexplained -> after 22 / 21 / 1 (the
eight 737 door-1 sill flags are gone; three new 737 MAX aft-door rows are flagged and explained, see 4.; the unexplained
one is still the A333 belly at 0.5 L). New: `node tools/models/dock_foot.mjs [--check]` (bridge closure vs the rendered
skin, rows in check_dims), the headless docking census of the 737 family (old vs new sill).

### 1. What changed for everybody who reads `TYPES` or draws the models

| Field / API | Change |
|---|---|
| Bridge closure (bellows) | **aircraft-v1.** The flat-fronted bellows block (front at `T.dockHW`, 3.1 m along the fuselage, 3.0 m tall) cut 0.17-0.26 m into the tapering nose skin aft of door 1 on every widebody and stood 0.2-0.4 m off it forward (and above a narrow body's crown). The closure is now fitted to the drawn skin: `js/aircraft/dock.js` `bellowsShape(T, door, kk)` / `bellowsGeo(...)`, called from `js/live/gates.js bridgeGeo` (2 small edits: import + the bellows line; the flat boxes remain the fallback). Every fibre of the closure runs from the cab front (frame y 0.05-3.0 m, unchanged) to the skin, the front follows the skin over the whole footprint, the top curtain comes down onto the fuselage at about door clear height + 0.15 m (2.05 m above the sill; lower only where a narrow body's nose crown ends below it). Source of the rule: AC 150/5220-21C §2.3.f(3) ("folding bellows aircraft closure ... when fitted to the aircraft fuselage, must surround both the open aircraft door and the doorway"); REACH / TOP_OVER / extension limits are inferred and marked so. The cab pose, joint limits, solids and `T.dockHW*` are unchanged. |
| `data/models/dock_foot.js` (`DOCK_FOOT`) | New, generated by `tools/models/dock_foot.mjs`: the rendered skin of every docking door (67 doors, 47 types) on a 0.4 m x 0.15 m grid over the footprint, measured by planar cuts of the drawn mesh (decoded .sfom + `applyStretch` + the `placement()` matrix incl. the stance pitch: the review's own method). Each grid records the X / sill / hw of the door it was measured for; `dock.js` ignores a stale one (flat bellows + one console warning). **Re-run it after any change to fit.js / types.js / a model.** |
| `js/aircraft/stretch.js` | New: `applyStretch` moved out of `js/live/models.js` (re-exported there, API unchanged) so node tools measure exactly what is drawn. New stretch op `tipShear` (757 winglet, below); Python port in `tools/liveries/common.py apply_stretch`. |
| 737NG door 1L | **aircraft-v2.** `tools/convert_models.py` `door_fit` re-fits the FG 737-800's door 1L and its skin opening (a spatial deformation of the converted mesh: coincident vertices move together, the skin stays closed, UVs follow): sill down 0.227 model m so it renders at the ACAP OEW sill 2.74 m (D6-58325-7 Rev C §2.3.2 B; the fitted stance is the OEW one: crown 5.56, fin 12.60, door 2 3.16 against 5.56 / 12.62 / 3.12), top kept (door 1.87 m tall against 34 x 72 in, §2.7.1). `T.dockSill` of the 737 family: 2.967 -> 2.739 m (MAX 2.74 against 2.77-3.07: -0.03, within +-3 in). Source restored: `refs/cache/src/fg/737-800` (blob-less sparse clone at the pinned 9126249, GPL-2.0, SOURCES.json); `refs/cache/models_orig/b738.sfom` regenerated; `tools/liveries/atlas.py b738` re-run (verified first: the unmodified re-conversion re-atlases to the committed model: same triangles and charts, neutral atlas texture different in 0.001 % of pixels); `model_features.py` re-run (only b738 `sec` and `doors` changed); all 32 b738 livery bakes of the job table re-baked (`tools/liveries/build.py --models b738`, 96 webp; the livery manifest was first shown to regenerate byte-identically; after the bake only the 13 b738 entries' byte counts changed, brands and design frames identical; the orphan `*/b738@b739-*.webp`, not in the manifest, is untouched). Tooling restored for this: `cairosvg` 2.7.1 (pip; numpy untouched), `tools/liveries/out/frames.json` seeded from the manifest's frames. |
| `TYPES.b752/b753` 757 wing | **aircraft-v3.** The plain wing is no longer stretched: the span fit ends at the model's winglet root (`fit.js WINGLET`, measured on the model: upper skin rises from \|z\| 18.6) and targets the ACAP plain span 38.05 m (D6-58327 Rev H §2.2.1 p.2-10, fetched to `refs/cache/acap/757_Rev_H.pdf`); the artist's near-vertical winglet is canted out (`tipShear`, quadratic in height so the blend keeps its shape) until its tip meets the APB winglet span 41.07 m. Rendered: span 41.06, plain wing to the winglet root 37.98 (was 39.7-40.1), winglet 1.54 m a side (published 1.51). `T.fit.winglet = {zr, y0, root, lat, k}`. |
| `typeForIcao('E135')` | **aircraft-v4.** Length 26.33 m (FAA ACD row E35L "Embraer 135BJ Legacy 600", the ERJ-135 airframe) instead of the ERJ-140's 28.47 m; span 20.06 / tail 6.77 m from the E135 row. |
| check_dims | **aircraft-v5.** Header prints the rules (lengths / spans 1 %, stations 1 % of L, heights +-0.08 m, closure 0.05 m); the overall height is a vertical row. New rows: bridge closure per docking door (skin outside the outline, gap on the outline, drawn vertices inside the skin; before = the flat front), 757 plain span at the winglet root and winglet extent, the 737 family's own aft door sill (REF `sillAft`, §2.3.1/2.3.2 G, MAX §2.3.x M). |

Numbers (all docking doors; `tools/models/dock_check.mjs`, finer cuts than the table): skin through the closure outline
max 0.036 m (flat front before: 0.261 m, 29 of 67 doors > 0.10 m); gap on the outline max 0.041 m (747-8 door 2 near the
sill; all others <= 0.03); drawn closure vertices inside the skin max 0.07 m (747-8 door 1, inside the closure, not on its
outline). End to end through `gates.js` (docked poses at 3 stands per type, 189 dockings, 47 types): max 0.029 m. A test
with the closure frame flipped fore/aft gives 0.68-0.78 m, so the check sees orientation errors.

Visual check (one headless llvmpipe page load, 960 x 540, `out/review_aircraft/r1_*.png`): the snapshot docks only
narrow bodies (B13 737-800, D4 737-700, D10 737-9, A321s at B18-B26); at B13 the closure meets the Alaska 737's skin with no
visible gap or clipping from ahead and from aft of the door, its top curtain draped from the cab frame onto the fuselage;
the 757-300 seen from ahead shows the winglets canted out. No widebody is docked in the snapshot, so the widebody closure
rests on the numeric checks above.

### 2. Requests

| File (owner) | Request |
|---|---|
| `js/live/gates.js` (bridges) | (a) Done from this side: the bellows is now `bellowsGeo` (js/aircraft/dock.js); please keep the call when editing `bridgeGeo` (a bellows box edit there has no effect while a shape exists). The cab stays square to the fuselage axis; `dock.js skinTaper(T, door)` gives the plan-view taper if you want to turn the cab to the skin instead (not needed for contact). (b) **G7 bridge 0 and G8 bridge 0 no longer dock the 737 family**: with the door at the ACAP sill (2.74 m, before 2.97 m) the tunnel from the rotunda floor (Hr 5.22-5.23 m, inferred) at 13.0-13.8 m extension is 1:3.7-1:4.0, steeper than the 1:4 limit (AC 150/5220-21C §3.4.b(6)). Census of all stands accepting each 737 type: docked bridges 95 -> 93 (b738), 90 -> 88 (b737), etc.; every other stand unchanged; max docked slope 0.217. The rotunda height / rest pose of G7 / G8 are the bridges track's inferences. |
| `tools/drawing/common.py` (drawings) | Port the new stretch op `tipShear` (js/aircraft/stretch.js; Python: tools/liveries/common.py) for the 757; the 737 door re-fit is in the mesh itself (nothing to port). |
| `js/world/gates.js` (legacy scene) | Still draws the flat bellows at `T.dockHW`; `js/aircraft/dock.js` can be used the same way if the legacy scene is kept. |
| `tools/live/gatecheck.py` (realtime tools) | Business-jet length of E135 is now 26.33 m (`BIZ`). |

### 3. Rejected / deferred in this round

- None of the five findings is rejected.
- 737NG door 1L **width** (artist 1.0 m against 0.86 m) and **station** (rendered 5.21 m against 5.03 m, inside 1 % of L) are
  unchanged: the sill was the finding; the bridge docks at the drawn door and the closure covers it.
- The right-hand forward door (doorRF, the galley service door) keeps the artist's sill (the ACAP gives no 1R sill row).

### 4. Open (aircraft track)

1. **737 MAX stance** (done in Round 3 below; found while adding the aft-door rows): the app stands every 737 on the FG 737-800 model's gear,
   nose-down 0.5-0.7 deg; the MAX ACAP (D6-38A004 Rev K §2.3) shows the MAX nose-up at rest (forward door 2.77-3.07 m, aft
   passenger door 2.49-2.90 m, against the NG's 2.59-2.74 / 2.97-3.12 m: its taller nose gear). Rendered MAX aft door 3.15 m:
   0.26-0.33 m above the range (flagged, explained in check_dims); door 1 is within +-3 in. Fix: a MAX nose-gear extension
   and a nose-up stance in fit.js (and a dockSill for the MAX door from its own stance).
2. Still open from round 1: missing bakes for FDX / CAL / EVA B77L, ACA-X CRJ7, AAR A388, CSG and JSX (now unblocked for the
   FG 737 only; the FAM / FG 777 sources are not restored yet: `refs/cache/models_orig` holds only b738), A321neo ACF
   layouts, E175 windows, 767-300ER winglets, A333 belly at 0.5 L.

## Round 3 (verifier findings of review round 1, 5 Nov 2026: aircraft round 2, v1 .. v6)

Checks: `python3 tools/models/check_dims.py` before 22 flagged / 21 explained / 1 unexplained -> after 27 / 26 / 1 (the three
MAX aft-door flags are gone; new and explained: the MAX fuselage-top row x4, §3, and the new 737NG engine row x4, §1; the
unexplained one is still the A333 belly at 0.5 L); `node tools/models/dock_foot.mjs` (re-run: 67 doors, 0 stale; only the
eight 737 door-1 grids changed); headless docking census of the 737 family (real `LiveGateSystem.planFor`, the verifier's g78 scripts);
the converter's new door-fit self-check; one headless llvmpipe page load (800 x 450, `out/review_aircraft/acr2_*.png`: the
parked 737-8 on its extended nose leg, tyre on the apron; a UAL 737-800's door 1L with no band at the sill; the UAL 737-9
docked at D10 with the cab at the raised sill and the LEAP nacelle hanging below its pylon; all parked 737s report nose /
main tyre 0.000 m above the apron through the app's own placement()). The D10 tunnel sign still reads mirrored (bridges,
round 1 request (b)).

### 1. What changed for everybody who reads `TYPES` or draws the models

| Field / API | Change |
|---|---|
| 737 MAX stance (`b37m/b38m/b39m/b3xm`) | **v3.** The MAX now stands nose-UP on an extended nose leg, as D6-38A004 Rev K §2.3.1-2.3.4 shows it (forward door B 2.77-3.07 m above aft passenger door M 2.49-2.90 m on the 737-8; the NG's door 1 is 0.38 m below its door 2). `js/aircraft/fit.js` fits the pitch (least squares) to the MAXIMUM column of rows B and M (read as the OEW condition, like the NG document's "MAX (AT OEW)" column the NG stance already matches: inf) about the main-gear contact (the NG main gear, unchanged), then extends the nose leg until the nose tyre touches: new stretch op `noseExt {xMin, yTop, yBot, e}` (`js/aircraft/stretch.js`; Python port `tools/liveries/common.py`): gear-zone vertices ahead of xMin between the outer strut's bottom and the wheels are stretched, the wheels move down rigidly (`fit.js NOSE_LEG`, measured on the FG nosegear objects). `T.fit.pitch.a` is now negative for the MAX (nose-up; `placement()` already takes any sign). Result (rendered, m; ACAP OEW / range in brackets): 737-7 0.73 deg nose-up, leg +0.34, door 1 3.06 (2.77-3.07), aft door 2.90 (2.49-2.92); 737-8 0.66 deg, +0.35, 3.07 (2.77-3.07), 2.90 (2.49-2.90); 737-9 0.74 deg, +0.39, 3.11 (2.79-3.07: +0.04), 2.87 (2.51-2.82: +0.05); 737-10 0.61 deg, +0.36, 3.08 (2.77-3.07), 2.89 (2.54-2.87); nose and main tyres 0.00; fin top within 0.03 of H (the fin fit takes the pitch); fuselage top at the main gear 5.57-5.58 (5.51 / 5.54). Before: nose-down 0.51-0.60 deg, aft door 3.15-3.16 (+0.26-0.33). The rotation also moves the drawn door-1 centre aft: `T.dockX1` 5.21 -> 5.29 m (artist's door; ACAP 5.03, inside 1 % of L). `T.dockSill` of the MAX: 2.74 -> 3.06-3.11 m (bridge cab floor = the drawn door). The NG types are unchanged (2.74 m). |
| `SPEC.b37m/b38m/b39m/b3xm.sillAft` | New: row M of §2.3.1-2.3.4 ([min, max], pub). |
| 737 MAX nacelles (`stretch.engScale`) | Found with v3: the LEAP-1B nacelle (`ENG_SCALE` 1.14, fan 69.4 / 61 in) was scaled about its lowest line, so its top rose 0.27 m over the pylon junction and its bottom stayed the CFM56's: 0.86 m in the nose-up stance against row E 0.43-0.56 m (the NG's row D is 0.48-0.64 m: the bigger fan hangs lower). New option `engScale.keep: 'top'` (JS + Python port): scaled about the pylon line, the bottom renders 0.57-0.58 m. `SPEC.engClr` added for the 737 family (MAX row E, NG row D), so check_dims now shows the engine row; the NG's 0.75-0.77 m (+0.13-0.15 over its OEW max) is the artist's nacelle position, explained, not re-fitted (open). |
| FG 737-800 door 1L (`data/models/b738.sfom`, `refs/cache/models_orig/b738.sfom`, 32 b738 livery bakes) | **v2.** `tools/convert_models.py door_fit`: the station range now takes in the two skin columns that close the opening (x -4.54 / -5.77, the apices of the skin fan below the sill) with a 0.3 m linear fade-out (`ramp`) and only the side skin (`zMin` 1.0: the nose-gear well's aft wall at x -4.54 stays). The fan no longer folds over the door's bottom panel. New self-check in the converter: every triangle with a moved vertex is compared before / after; any that turns over (> 90 deg) stops the conversion (`RuntimeError`), > 45 deg is reported. Self-check now: 605 triangles touched, 0 folded, 3 turned > 45 deg (door-handle relief facets of 1e-5..4e-4 m2: the lower door is stretched 14 % in height); with the old range: 4 folded (fuselage t300-303, the fan under the sill) and 14 > 45 deg, which now raises. Final mesh (atlas output): inward-facing skin triangles around door 1L 46 / 0.072 m2 -> 45 / 0.0084 m2 (the rest are the artist's sub-0.001 m2 facets, as before the door fit); the verifier's horizontal ray probes (x -5.6 / -5.2 / -4.9, y -0.69 .. -0.55) hit one surface, the door panel, instead of three coincident ones. Topology unchanged (nv 76921, ni 82284, 13801 atlas triangles in 84 charts); `model_features.py` re-run: only b738 `sec` changed; the livery manifest diff is byte counts only (all 96 referenced b738 webp re-baked). Bridge closure on the 737s after the re-fit: skin through the outline <= 0.022 m, gap <= 0.014 m, drawn vertices inside <= 0.033 m. Re-atlased (`tools/liveries/atlas.py b738`) and all b738 liveries re-baked (`tools/liveries/build.py --models b738`). |
| check_dims winglet rows | **v4.** The 757 plain-wing span at the winglet root is measured on the stretched mesh (`winglet_root`: per side the upper-skin profile in 0.1 m bins of \|z\|, a dihedral line fitted over 0.6-0.85 of the semi-span, the root where the 3-bin median first stays > 0.10 m above it). Rendered 38.14 m (ACAP 38.05) and winglet 1.46 m a side (APB 1.51); sensitivity: the pre-v3 wing stretch would read 40.01 m (flagged), the model without the winglet cant 38.33 m / span 39.16 m (span flagged). |
| check_dims stance rows | Gear models are seated on `dims.low` (+ gearUp), as `placement()` does (an extended nose tyre is not the seat). New row for nose-up stances: fuselage top at the main-gear station (see §3). |
| `refs/cache/src/fg/737-800` | **v6.** Now a plain export (no `.git`) of FGMEMBERS/737-800 @9126249: the 35 files of the old sparse checkout (each verified byte-identical to its blob at the commit) plus `Models/Liveries-800/N563AS.png/.xml` (the Alaska tail that `fg_texture` samples); 8.7 MB, GPL-2.0. `refs/cache/src/fg/SOURCES.json` is keyed `737-800/*` (so `tools/cache/sync.py` classifies every file as GPL and stages it) and lists each file's git blob SHA-1. The 103 `src/fg/737-800/...` entries (81 of them `.git` internals) were removed from `refs/MANIFEST.json`; `sync.py --dry-run` now plans 37 files there for commit. `tools/liveries/liveries.py fg_texture` and `tools/liveries/atlas.py` read the plain files (git only as a fallback; atlas.py now warns instead of silently dropping the source texture). The `.git` of the old clone is kept outside the repo (scratchpad) only. |

### 2. Requests

| File (owner) | Request |
|---|---|
| `js/live/gates.js` / stand data (bridges) | **v1 (major, not fixed here: bridge geometry).** G7 b0 and G8 b0 still dock no 737NG (b738 / b737 at the ACAP OEW sill 2.74 m: tunnel 1:4.0 / 1:3.7 against the 1:4 limit, AC 150/5220-21C; rotunda floor Hr 5.227 / 5.225 m, inferred), and F5 b0 docks nothing (1:2.0-1:2.7 for every type, also the A320). The 737 sill was not raised (the verifier's instruction): please re-derive Hr / h0 / rest extension of G7 / G8 bridge 0 and the F5 bridge from a source, or record the gap in bridges_closeout. With the MAX stance (v3) the MAX now docks at G7 / G8 (slope 0.213-0.237) (census, docked bridges over all stands accepting the type: b38m 93 -> 95, b37m 92, b39m 96, b3xm 94; b738 95, b737 90, b736 90, b739 94 unchanged). |
| `tools/drawing/common.py` (owner of tools/drawing this round: bridges) | **v5 (not fixed here: not this track's file).** `_stretch` ports only `wing`, `fin` and the plugs, so a 757 is drawn with the artist's plain tip (span ~39.2 m, near-vertical winglet) against the 41.06 m rendered, and the MAX without its nose leg; nor does it apply `T.fit.pitch` (737 / 777 stance). Cheapest fix: replace the body of `_stretch` by `tools/liveries/common.apply_stretch` (it ports every op of js/aircraft/stretch.js, incl. `tipShear` and the new `noseExt`, in the same order) ~~and rotate by `T.fit.pitch` about `(x0, y0)` as `tools/models/check_dims.py rendered()` does (now with either sign of `a`)~~. **Corrected in close-out round 3 (aircraft-4): do NOT add a pitch rotation** - `model_geom` already transforms by the app's own `placement()` matrix (jobs/extract2d.mjs `A.placement = ac.placement()`), which contains the stance pitch; a second rotation would tilt the drawn 737 / 777 by another 0.2-1.4 deg. |
| `tools/cache/sync.py` (lead) | Nothing needed for v6: with the `737-800/*` key the existing rules stage the GPL files. If a blob-less clone is ever placed under refs/cache again, a RULES entry `('*/.git/*', 'local', ...)` would keep its internals out of the manifest. |

### 3. Rejected / deferred in this round

- **v3, fuselage top row (explained, not fitted):** in the nose-up stance the highest fuselage top over 0.1-0.5 L (the
  row's definition) is the forward cabin top, 5.68-5.73 m against row A 5.51-5.54 m. D6-38A004 rows A, B and M cannot all
  hold there on one rigid fuselage: on the model the top 1-3 m aft of door 1 is 2.6-2.7 m above the door-1 sill, so with
  door 1 at row B's 3.07 m it is ~5.7 m. Row A matches the top at the main-gear station (new row: 5.57 against 5.51-5.54,
  within +-3 in). The sills are what the bridges dock to, so they are fitted.
- **v3, nose-leg length:** the fitted extension is 0.34-0.39 m (737-8: 0.35 m). It follows from the ACAP sills with the NG
  main gear unchanged: the two documents' OEW heights, MAX minus NG, are +0.33 m at door 1 (5.03 m) and -0.22 m at the aft
  door (31.88 m), a rotation about 21.1 m, 1.4 m aft of the main gear (the cargo-door and stabiliser rows move the same
  way: up forward, down aft). No primary source for the MAX nose-gear strut length is in the cache, so the extension is
  not checked against one (inf).
- **737NG engine row (new, explained):** 0.75-0.77 m against row D's OEW 0.61 / 0.64 m (+0.13-0.15): the FG nacelle hangs
  higher than the real one while crown, sills and fin fit the OEW stance. Moving it would part it from its pylon; open.
- **v1, v5:** other tracks' files (§2).

## Round 3 of the close-out (7 Nov 2026: findings aircraft-1 .. aircraft-10, docs/requests/closeout3_findings.json)

Checks: `python3 tools/models/check_dims.py` before 27 flagged / 26 explained / 1 unexplained -> after **30 / 30 / 0** (gone:
MAX fuselage top x4, NG engine x4, MAX aft door x3, A333 belly at 0.5 L; new and explained: the FG artist's cargo-door
stations x14, see 1.); `node tools/models/dock_foot.mjs` re-run (737 family door-1 grids; all closure rows <= 0.04 m);
headless docking census of the 737 family through the real `LiveGateSystem.planFor` (old aircraft fit vs new, same tree):
docked bridges b736 91 / b737 91 / b738 95 / b739 94 / b37m 93 / b38m 96 / b39m 96 / b3xm 94 **unchanged, 0 bridges changed
status**, max docked slope 0.219 (NG) / 0.239 (MAX); `python3 tools/sat/check.py` ISSUES 0, APP ISSUES 0, 17 WARNINGS (as
before). Scripts: scratchpad `c3/aircraft/scripts/` (stance_fit.py, belly.mjs, belt_api.mjs, hwcmp.mjs, census.mjs).

### 1. What changed for everybody who reads `TYPES` or draws the models

| Field / API | Change |
|---|---|
| 737 family stance (`b736 b737 b738 b739 b37m b38m b39m b3xm`) | **aircraft-1 (root cause), aircraft-5 (NG nacelle).** The FG 737-800 gear is drawn with its oleos fully extended (its own animations translate wheels and lower struts up by `gear compression-norm x 0.3048 m`, the nose gear by a further 0.15 m: `refs/cache/src/fg/737-800/Models/LWing.xml`, `NoseGear.xml`), exactly the FG 777 case. Standing on it, the 737-800's forward cargo door rendered 0.25 m above row C, its engine 0.13 m above row D, and door 1 0.23 m above row B - which round 1 had hidden by re-cutting the door (doorFit). `js/aircraft/fit.js STANCE_FIT` now fits the stance to the ACAP's OEW rows of the model's own door objects (door 1 B, aft door G / M, forward / aft cargo door C / F (NG) or D / L (MAX)): least squares for the main oleo compression (`stretch.gearUp`) and the pitch about the main contact; the nose leg is then compressed (NG) or extended (MAX) until its tyre touches (`stretch.noseExt`, e < 0 allowed). The door re-cut is undone (the artist's door renders 2.70-2.72 m against B 2.59-2.74). Result: 737-800 1.02 deg nose-down, main oleo 0.14 m, nose leg -0.12 m; 737-8 0.20 deg nose-up, main 0.13 m, nose leg +0.22 m. Every row fits within +-3 in, also the rows NOT fitted: fuselage top (highest over 0.1-0.6 L) 5.51 / 5.48 against A 5.56 / 5.51, engine 0.59 / 0.41 against D 0.64 / E 0.43-0.56, MAX fuselage bottom 1.52 against C 1.27-1.55. **`T.Hc` changes** (737-800 3.595 -> 3.452, MAX 3.465-3.47), **`T.fit.renderedCrown` changes** (the 0.1-0.5 L crown; 737-800 5.566 -> 5.414, 737-8 5.716 -> 5.49; round 2 had raised the MAX's to 5.70-5.75 without listing it: aircraft-4), `T.dockSill` 2.70-2.72 (NG, was 2.739) / 3.04-3.06 (MAX, was 3.06-3.11), `T.dockX1` 5.16-5.26. New `T.fit.stance = {dz, rows}`. |
| 737 fuselage plugs | Found with aircraft-1: the forward plug at 10.0 m cut through the FG forward cargo door (9.65-10.65 m), so the 737-900ER / -9 / -10 drew that door 2.6-3.8 m long and the -600 / -700 / -7 lost up to half of both cargo doors in their removed sections. D6-38A004 §2.7.1 keeps the forward cargo door at 8.53 m on every MAX (plug aft of it) and moves the aft one by both plugs (plug ahead of it): `PLUG_AT.b738` 11.0 / 26.0 m for inserted plugs, `PLUG_REM.b738` 10.7 / 22.2 m for removed sections (aft blend stops 0.6 m ahead of the aft cargo door). Re-atlased (`tools/liveries/atlas.py b738`, plug bands 10.99 / 25.97) and all b738 livery bakes re-done (`build.py --models b738`, 32 jobs; manifest diff: byte counts, `pxm` 35.6 -> 37.2, one frame `ycM`). Open: the 737-600's 4.37 m forward removal still reaches 1.5 m into the wing-body fairing's front. |
| `T.fit.cargo`, `T.fit.keelAt(X)`, `T.fit.skinHW(X, y)`, exports `keelAt(T, X)`, `skinHalfWidth(T, X, y)`, `cargoDoor(T, door)` (js/aircraft/fit.js) | **aircraft-1, for the belt loaders.** Stance-aware lower fuselage in rendered metres of the `placement()` frame: `keelAt` = lowest skin on the centre plane at station X; `skinHW` = STARBOARD skin half width at (X, y) (lower lobe from `MODEL_FEATURES.sec.hwl`, new; above it `hwf`; wing / fairing cuts replaced by the section ellipse); `T.fit.cargo.{fwd,aft}` = `{X, sill, keel, pub, side, src}` (the model's own cargo-door object - FG 737-800 `cargodoorF/R` - else the published station `SPEC.cargoX`); `cargoDoor(T, door)` -> `{X, S, hw, keel, pub, drawn}`: where the conveyor ends (drawn sill, else the published range's middle above the keel). Measured against planar cuts of the placed mesh: keel within 0.01 m and half width within 0.05 m at the 737 / A320 cargo stations (hwcmp.mjs; the source models are 1-3 cm asymmetric, hence the starboard table); conveyor end vs skin with `cargoDoor`: **-0.016 .. +0.007 m** for the 737 and A320 families (belt_api.mjs). Not valid at gear wells (the centre-plane cut finds the well roof) and widebody wing boxes (documented). |
| `SPEC` (js/aircraft/types.js) | New: NG `sillAft` (row G), `cargo` {fwd, aft} (NG C / F, MAX D / L, A321 C1 / C2, A321neo XLR C1 / C2), MAX `bottom` (row C), A321 / A321neo `bottomFA` (F1 / F2), `cargoX` (MAX §2.7.1 rows C / G; A321 FIGURE-2-7-0-991-036 8.16 m and the aft cargo-door figure 29.62 m). |
| `MODEL_FEATURES` (tools/models/model_features.py) | New `cargo` (source cargo-door objects; FG 737-800 only), `sec.lo` / `sec.hwl` (starboard lower-lobe half widths, every station; manifest.js +48 KB); the FG / FAM source objects are now read whenever the source is present (the b738 doors had been the stale re-cut values). |
| A330 family belly fairing (`stretch.fairing`) | **aircraft-5.** AC A330 re-fetched (Rev 21, Apr 01/13, SKYbrary bookshelf copy; the current Dec 01/25 revision could not be fetched: Airbus' site refuses scripted downloads, the 2023 URL is 404): FIGURE-2-3-0-991-001-A01 row H = 1.86 / 1.85 m at MRW (2.04 m at 119 t) - the same values as the BF1 1.85-1.86 m SPEC carries. The FAM A330's fuselage depth fits (5.66 against 5.64 m) but its fairing hangs 0.35 model m below the keel, rendered 1.68 m. New op `fairing {y0, k, zMax}` (js/aircraft/stretch.js + Python port): only the fairing (body below the keel line within 1.1 x the fuselage half width; not engines / pylons / gear) is compressed towards the keel to the middle of the range: A333 1.85 (k 0.46), engines 0.74 unchanged, door closures unchanged (<= 0.02 m). |
| `js/live/models.js` | **aircraft-10.** New exports `registrationLayout(reg, flag, flagFirst, {row, maxW, measure})` (the decal's draw list: font, both rows, flags; `maxW` scales to a slot like RegAtlas), `drawRegistration(ctx, layout, x0, y0)`, `drawFlag`; `registrationTexture` draws from them (same output). New `modelPositions(key, stretch)` (decoded, stretched vertex positions + zones without GPU objects, for QA tools). |
| `js/live/aircraft.js` | **aircraft-10.** New `ac.lodState(camPos)` -> `{d, draw: 'none' | 'body' | 'proc' | 'real', shadow, tip, gear}`: the per-frame LOD decision `items()` itself now uses; new public getter `ac.livNeutral` (`_livNeutral` kept). |
| `js/aircraft/fleet.js` position lights | **aircraft-9.** The records of pages without a light viewer (offline renderer) come from `js/env/aircraft_lights.js`: `MINIMA_FACTOR x` the 14 CFR 25.1391 dead-ahead 40 cd / rear 20 cd in lamp units (i 125.4 at s 0.22, 75.9 at s 0.2; was 40 / 25 = 26 / 13 cd), aviation colours `AV_*`, `phys: true` (renderer3 keeps physical records at the night calibration by day). The live app already drew `aircraftSprites` (unchanged). |
| `tools/models/qa_stance.mjs` | **aircraft-3.** Tyre heights are measured on the mesh the app draws (`modelPositions` + `matrix() x placement()`, lowest zone-3 vertex ahead of / behind 0.3 L); prints `STANCE_CHECK ok|FAIL` (0.02 m). check_dims: REF `B37M` added (D6-38A004 §2.2.1 / §2.3.1 / §2.7.1), so the 737-7 aft door is checked (2.87 against 2.49-2.92); the SPEC fallback carries `sillAft`. |
| check_dims rows | New: model's own cargo-door sills and stations, fuselage bottom at the cargo doors (MAX C, A321 F1 / F2), `T.fit.keelAt` = rendered keel, fuselage top highest over 0.1-0.6 L (gear models). The withdrawn explanations (MAX crown, NG engine, MAX aft door) are removed. |
| ACA-X CRJ700 livery | **aircraft-6 (partly).** `refs/cache/src/fam3d/{crj9/glTF2/CRJ7.glb, a380/glTF2/A380.glb}` restored (plain export of FlightAirMap-3dmodels @0906d9b, GPL-2.0, SOURCES.json with blob SHA-1s); `refs/cache/models_orig/crj7.sfom`, `a388.sfom` regenerated (re-atlased they reproduce the committed models: same positions, livery-atlas UVs within 1.5e-5, same charts; the committed models are kept). `ACA-X` types += `CRJ7` (Jazz C-FCJZ on the ground at SFO in our 4-7 Nov recording) and baked: `data/liveries/ACA-X/crj7-{hi,mid,lo}.webp`. |

### 2. Requests

| File (owner) | Request |
|---|---|
| `js/world/gates.js` `beltSill` / `lowSkin`, `js/live/gates.js` placeVehicles belt loaders (bridges, **bridges-3**) | Use `cargoDoor(T, door)` (js/aircraft/fit.js): conveyor top `S` = `.S`, station `X` = `.X` (instead of 0.22 L / 0.66 L), end at `.hw` (+ a few cm) from the centre line instead of the unpitched ellipse `2 Hc - crown`; `vehicleSettings()` collects `.S` per type. `null` -> keep today's default. Measured: ends within -0.016 .. +0.007 m of the starboard skin (737 / A320 families). **With today's formula the new 737 stance makes the NG forward conveyor end 0.14-0.16 m inside the skin (before: 0.05-0.06 m), the aft ones 0.44-0.88 m off it; MAX forward 0.28-0.42 m off (before 0.73-0.93)** - please switch before the next render QA. The collision test (`acHit`, ell = true) can use `skinHalfWidth(T, X, y)` / `keelAt(T, X)` the same way. `BELT_PUB` can go: `T.fit.cargo.pub` carries the type's own rows (MAX D / L, not the NG's). |
| `tools/drawing/common.py` (bridges, bridges-7) | Port the new stretch ops `fairing` and the `noseExt` sign (compression) - or, as asked, import `tools/liveries/common.apply_stretch` (it has both). Do NOT rotate by `T.fit.pitch` (it is in the extracted `placement()` matrix; see the corrected Round 3 request above). |
| `js/three/aircraft.js` (engine) | **aircraft-10:** `RegAtlas.draw` -> `registrationLayout(reg, flag, flagFirst, {row: REG_ROW, maxW: REG_W - 4, measure})` + `drawRegistration(ctx, L, x0, y0)`; `update()` -> `ac.lodState(camPos)` (`draw === 'real'` / `'proc'` / `'body'`, `tip`, `gear`; keep the LiveryCache acquire step); `ac._livNeutral` -> `ac.livNeutral`. |
| `js/three/lights.js` (engine / env) | **aircraft-9:** the comments at the header and `isPositionLight` cite the old fleet.js records (i 40 / s 0.22, 26 / 13 cd); the records are now `phys: true` with i 125.4 / 75.9 (80 / 40 cd), which renderer3 already handles through `s.phys === true`. |
| owner (aircraft-7) | See open questions: CAL / EVA 777F cargo titles, CSG, JSX designs. |

### 3. Rejected / deferred in this round

- **aircraft-2 (nose leg source):** recorded, not "fixed" by matching Boeing's 8 in: with the oleo-compressed stance the MAX nose
  leg is +0.21-0.26 m on the FG model (was +0.34-0.39) and the MAX nose tyre sits 0.32-0.38 m lower below the airframe than its
  NG twin's, against "an 8-inch nose gear extension" (0.20 m; Boeing press release 11 Apr 2012, cached in `refs/cache/press/`
  with SOURCES.json). The ACAP rows (pub) win because the bridges and the ground equipment meet those doors; the strut
  extension is not the static height (oleo servicing / nose load), and no document gives the static strut length. The leg is
  now scaled over its whole visible length (0.88 model m: +24-30 %, no part stretched more), so the +87 % torque link is gone.
- **aircraft-6:** FDX B77L and AAR A388 are not baked: our recording (all hours, 4-7 Nov) shows no FedEx 777F and no Asiana
  A380 on the ground or below 2,500 ft within 8 km of SFO (FedEx's 777Fs fly to OAK; HL7625 only passed within 40 nm), and
  DataSF does not list them (docs/research/liveries.md §1.1). CAL / EVA B77L (seen at SFO: B-18777, B-18780; B-16781,
  B-16790) wait for the owner's cargo-title approval (aircraft-7) and need the FG 777 source re-exported
  (`git clone --filter=blob:none https://github.com/FGMEMBERS/777` @371a354, `git show <commit>:Models/777-300ER.ac` and its
  textures into `refs/cache/src/fg/777_export/Models`, then `tools/convert_models.py b77w` -> `models_orig`). Found on the
  way: **CAL B77W** (B-18001 / -006 / -053 at SFO) has no bake either (CAL's types list only A359) - same prerequisite.
- **aircraft-8:** no new primary source fetched (conserving rate limits): the 737-900ER window row stays the MAX-9 row (inf),
  A321neo ACF door layouts per operator and 767-300ER winglets per operator need fleet / seat-map sources, E175 window
  stations need Embraer APM-2259 (NTSB docket DCA20IA014 attachment 2, not restored). All remain tagged inf.
- **FG 737-800 cargo-door stations** (new explained check_dims rows): the artist drew the forward door 1.6 m aft and the aft
  one 1.3 m forward of D6-38A004 §2.7.1; moving the objects needs a skin re-cut and a re-bake (open). Their sills fit.

### 4. Open (aircraft track)

1. CAL / EVA B77L cargo titles, CSG, JSX (owner, aircraft-7); CAL B77W bake (FG 777 source, 3.).
2. 737-600 forward removed section reaches into the wing-body fairing (1.5 m); FG 737 cargo-door stations.
3. Still open from earlier rounds: A321neo ACF layouts, E175 windows, 767-300ER winglets, 737-900ER row (inf).

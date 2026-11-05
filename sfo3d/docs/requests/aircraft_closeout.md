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

1. **737 MAX stance** (found while adding the aft-door rows): the app stands every 737 on the FG 737-800 model's gear,
   nose-down 0.5-0.7 deg; the MAX ACAP (D6-38A004 Rev K §2.3) shows the MAX nose-up at rest (forward door 2.77-3.07 m, aft
   passenger door 2.49-2.90 m, against the NG's 2.59-2.74 / 2.97-3.12 m: its taller nose gear). Rendered MAX aft door 3.15 m:
   0.26-0.33 m above the range (flagged, explained in check_dims); door 1 is within +-3 in. Fix: a MAX nose-gear extension
   and a nose-up stance in fit.js (and a dockSill for the MAX door from its own stance).
2. Still open from round 1: missing bakes for FDX / CAL / EVA B77L, ACA-X CRJ7, AAR A388, CSG and JSX (now unblocked for the
   FG 737 only; the FAM / FG 777 sources are not restored yet: `refs/cache/models_orig` holds only b738), A321neo ACF
   layouts, E175 windows, 767-300ER winglets, A333 belly at 0.5 L.

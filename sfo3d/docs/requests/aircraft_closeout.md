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

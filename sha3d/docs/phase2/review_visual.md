# Phase 2 adversarial visual review (P2f integration renders)

Date: 2026-11-21. I was asked to find what is wrong. I did not build any of this. This is a report only: nothing in
`js/`, `data/` or `tools/` was changed, nothing was committed, and `sfo3d/`, `pc12/` and `hwd3d/` were not touched.
There is no scoring.

**Inputs**
- the 25 `docs/phase2/view_*.png`, each looked at in full and cropped / enlarged where needed;
- the Commons photos (`photos_contact_sheet.jpg`; full files 02, 09, 11 and 14 in `refs/cache/photos/commons/`);
- the plates `airport_overlay.jpg` and `stands_overlay.jpg`;
- `standards_refs.md` §1.3-1.6, `markings.md`, `gates.md` and `buildings.md`;
- the data (`sha_airport.json` aprons / runways / `aip_facts`, `sha_stands.json`) and the shader and paint code.

**Extra renders:** made with `livetest.mjs` (SOFTGL, deviceScaleFactor 1) to confirm or reject suspects. Four are kept
as evidence (`review_*.png`, see the end of this report).

Severity: **high** = wrong in the main views or against the reference, fix before Phase 3. **Medium** = clearly visible
or against a cited clause or photo. **Low** = cosmetic or a small fidelity gap.

## Summary

The geometry and the CAAC marking *data* are right. Orientation, runway widths and surfaces, stripe counts 12 / 16,
designations, displaced thresholds, aiming points, TDZ pairs, hold pattern A and its text order, stand plates, the red
and white apron lines and bridge docking all check out. No FAA marking, sign or lighting constant was found in a code
path.

Two problems dominate what a viewer sees:
1. **The runway paint shader blurs the markings away in every runway-end view.** The threshold stripes become two
   solid blocks, so 12 and 16 cannot be told apart, and the numerals become bars.
2. **There is an unpaved brown strip between the terminal facades and the OSM apron polygons.** It runs under every T2
   pier fixed link, rotunda and VDGS post, and along the T1 north face.

After those come the night scene (no airfield or apron lighting, clipped white glazing), the missing apron floodlight
masts, and a few paint conflicts.

## Findings

| # | Sev | Render(s) | What is wrong | Exact fix |
|---|---|---|---|---|
| H1 | **high** | `view_rwy_18L/18R/36L/36R.png` (and `markings_rwy_*`, `markings_phone_rwy_36L`); `review_stripes_fade.png` | **Threshold stripes, numerals and centreline wash out at any normal view angle.** Each 12-stripe (18L/36R) or 16-stripe (18R/36L) field renders as two solid white blocks either side of the centre gap. The "L 18" / "R 36" numerals are two thin bars, and the 0.45 m centreline is a faint 3-4 m smear. The counts are right in the near-vertical renders (`markings_desig_18L_top` 12, `markings_dthr_36L_top` 16), so the 12-vs-16 CAAC distinction exists only in top views. **Cause:** `js/shaders/ground.js:58` `float fw = length(fwidth(wp.xz)) * 0.7` is an isotropic footprint. In the threshold view (camera ~68 m up, ~350 m before the threshold, 6° pitch) the along-track footprint is ~2.7 m, so fw ≈ 1.9 m. `js/live/markings.js` then replaces the stripes with their mean density (`c = mix(c, w/P…, smoothstep(0.6, 2.0, fw))`) and blurs every `mkBand` / `mkGlyph` edge by ±fw. The across-track footprint is only ~0.5 m against a stripe period of 3.25-3.4 m (~6.5 px), so the stripes are resolvable. | In `shaGroundPaint` (markings.js GLSL), before the early return, take `vec2 dX = dFdx(wp.xz), dY = dFdy(wp.xz);`. Per runway, with axis `d = ra.zw` and normal `n = vec2(-d.y, d.x)`, set `fwS = abs(dot(dX,d)) + abs(dot(dY,d))` and `fwT = abs(dot(dX,n)) + abs(dot(dY,n))`, and pass both into `mkEnd`. Use **fwT** for every lateral edge (stripe `mkBand(ff…)`, the stripe-fade `smoothstep(0.6, 2.0, fwT)`, edge-stripe, CL-width, TDZ / aiming-point lateral bands, arrow width). Use **fwS** for along-track edges (stripe ends, CL dash ends and their fade, TDZ / aim / bar ends). For glyphs use the footprint along the SDF gradient: sample d at p ± ε, or `fw = 0.7 * fwidth(d)` on the decoded distance. Re-render the four `rwy:` views and count the stripes. |
| H2 | **high** | `view_stand_233`, `view_bridge_230` (lower left), `view_stand_102` (strip along the T1 facade), `view_laptop_live_stand_233`, `view_phone_stand_233`, `view_night_stand_233`; `buildings_t2_close.png`; `review_under233.png`, `review_nose233_top.png` | **A brown "dirt moat" (RGB ~109,99,85) runs between the terminals and the aprons.** It covers the band where the fixed links, rotundas, VDGS posts and stand-number posts stand at the T2 piers and the T1 north face. The red bridge-area hatching runs off the apron onto it (`review_nose233_top`). Data check: the points under stand 233's walkway (-786, -117.5), its rotunda (-772.9, -118), 102's walkway (719.2, -1) and 102's rotunda lie inside **no** `aprons` polygon and no building; the OSM apron ways stop 15-40 m short of the facades. The ground shader then draws grass with the S2 hint capped at 0.16 inside the aerodrome (`rho = mix(rho, min(rho, vec3(0.16)), aero)`). Photo 09 shows a dark asphalt service road there, with white lines, Chinese text and vehicles. The S2 plate (`airport_overlay.jpg`, T2 panel) shows the strip as bright paved ground. | Add airside pavement through the existing extension hook `pavement(api, airport)` in `js/live/terminals.js`, which owns the T1 / T2 parts. For every part with an airside facade, `api.fill(offset(ring, 45 m) ∩ aerodrome ring, 'paved')`. 'paved' gives asphalt, not 'apron' concrete, which matches photo 09. Then `api.line(b.walk, 24, 'paved')` plus a 14 m disc at every rotunda and VDGS / sign post (from `SHA.qa.gates()`) so the fill also catches the gates package's points. Tag it `src: inf` ("OSM apron gap; paved in S2 / photo 09"). A cleaner alternative is an inferred `apron_fill` polygon in `tools/airport/build_airport.py`, from S2 brightness between the building outline and the apron. Optionally draw the service-road edge lines later (white, 6.2.23). |
| M1 | medium | `view_night_hold_H1`, `view_night_stand_233`, `view_night_t2pier` | **The night airfield is black.** At a runway-holding position only the two sign faces are lit. There are no taxiway centreline lights (green, green / yellow on entries, 7.5.1), no edge lights (blue, 7.5.2), and no stop bar or runway guard lights (7.5.3 / 7.5.5). The aprons are near black: the ground shader adds only `0.06 × albedo` as an "even flood". Photos 12, 13, 19 and 20 show bright high-mast floodlit aprons and lit taxiways. | (a) Now: in `js/shaders/ground.js` raise the `apronN` term from 0.06 to ~0.35-0.5 with a warm tint (≈ 1.0, 0.82, 0.6), and fall it off with distance from the stand rows / masts (M2). (b) Add sprite lights, labelled inf, from data that already exists: taxiway centreline lights every 15-30 m along the decal centrelines (green, alternating green / yellow from the runway CL to the hold on entries) and edge lights along the edge-line ribbons. Add a red stop bar, plus a yellow RGL pair, at the 22 entry holds from `SHA.markings.holds()` (direction `u`, extents `eL` / `eR`). (c) Until then, drop night views from the named set or label them "airfield lighting not modelled". |
| M2 | medium | `view_t1`, `view_tower`, `view_bridge_230`, `view_t2pier`, `view_stand_*`; `buildings_compare_t1.png` | **No apron floodlight masts.** Photos 02, 09, 14, 16 and 17 show 25-35 m masts at regular spacing along every apron edge. They are the most prominent vertical apron feature in all of them. The renders show none, and `gates.md` lists them as missing. | Gates package: place masts (inf) on the apron behind each contact and remote stand row, one per ~2 stands (≈ 80-100 m), 30 m high, with a 4-6 lamp head. Keep them clear of the stand envelopes (`SHA.markings.apron().envelopes`) and of the bridge sweep. Reuse the positions as the night flood sources for M1. |
| M3 | medium | `view_night_t2pier`, `view_night_stand_233` | **Night glazing is clipped to pure white.** The T2 curtain walls, the fixed links and the bridge tunnels are uniform white bands with no mullion contrast or variation. The photos (07, 12, 13) show warm, partly transparent glazing with dark frames. | In the objects shader's curtain-wall material (mat 1), cut the night emissive to ~0.3 of the current value and tint it warm (≈ 1.0, 0.85, 0.65). Vary it per bay with a hash (10-30 % of bays dimmer) and keep the mullions dark. Tunnels stay at 0.4 of the facade glow, as `gates.md` intends. |
| M4 | medium | `view_rwy_36L`, `view_rwy_18R`; `review_stripes_fade.png` (right) | **Yellow lead-on lines paint over the white displaced-threshold arrows.** The crossing taxiway in the 300 m displaced area of 18R / 36L has lead-on curves from both sides. Each continues 60 m parallel, 0.9 m off the CL, so two yellow lines run through the arrow shafts and arrowheads. MH 5001-2021 6.2.1-2 says runway markings win at intersections. `caac_decals.js` cuts lead-ons only over the designation numerals. | In `js/live/caac_decals.js`, add the displaced-threshold arrow polygons (head and shaft, from `plan()` arrows / `arrowH`) and the 1.8 m threshold bar to the "runway marking wins" cut set used for the numerals. Also keep only the lead-on that points in an allowed take-off direction in a displaced portion, not both. |
| M5 | medium | `review_nose233_top.png`; all DEBUG-parked stands | **Nose-tip vs nose-wheel at the stop line.** The painted stop line lies exactly under the B738's nose tip. Per the clause quoted in `markings.md` §5, a stop line marks the **nose wheel** (6.2.16-7). The data's `nose_note` says a per-type nose offset was due "when the aircraft models are placed (Phase 2 / 4)", and it was not applied. Every parked aircraft and every docked cab position is therefore a few metres off, and the two packages still disagree (markings §11.2, gates §10.9). | Decide one convention. Recommended: the OSM stop node is the nose-wheel stop. Then in `js/live/gates.js` `park()` / `setOccupant`, place each model with its nose-gear contact point (from the `.sfom` gear data) on the stop node, and recompute the class-reference `cab` points in `build_stands.py`. Keep the painted stop line at the node. |
| M6 | medium | `view_overview`, `view_t2`; `rvm` approach render | **Water is ink-black from above.** Canals and ponds near the airport (e.g. the pond south of the runways and the rectangle north of them) render at RGB ≈ (28, 35, 32) at midday, while the far-ground rivers in the same frame are blue (47, 63, 76). The shoreline shows as a dotted beige outline, which is aliasing of the 67 km of thin bank-kerb geometry. At grazing angles (approach view) the same canals turn sky-blue, so the look changes sharply with camera pitch. | In `js/shaders/ground.js`, raise the water body albedo from `vec3(0.016,0.022,0.016)` to a turbid green-brown (~0.05, 0.06, 0.045 linear), and add a reflection floor of F ≈ 0.06 at near-normal view. Do not damp F by `smoothstep(0.55, 0.9, ctx.r)` for water wider than ~10 m. In `terminals.js`, fade the bank kerbs out beyond ~800 m, or draw them as a ground-shader rim instead of geometry. |
| L1 | low | `review_endtop_36L_pad.png` | **36L blast pad: surface 120 m, chevrons 75 m.** The pad ring is the 120 m S2 / Umbra measurement, but the chevrons use `aip_facts.blast_pad_m` = [120, 75], so the outer 45 m is bare. The docs also disagree: `standards_refs.md` §1.3 / §1.4 say 120 m for both 18R/36L pads, `markings.md` says 75 m at 36L. | Pick one source per end. Either draw the 36L pad 75 m (AIP) or paint chevrons over the whole measured pad, and record the conflict in `airport.md`. Correct `standards_refs.md` §1.4. |
| L2 | low | `view_tower`, `buildings_compare_t1.png` | **The T1 central hall is a flat box.** Photo 02 shows a raised white curved roof volume over the central hall, carrying the red "上海 SHANGHAI" letters. The tower head is a solid frustum where the photo shows a split, two-level head. Proportions otherwise match `buildings_compare_tower`. | In `tools/buildings/build_buildings3d.py`, add a barrel / curved roof part (rise ~6-8 m, inf) on the T1 central hall. The letters and the split tower head are optional. |
| L3 | low | `view_towercab`, `view_phone_towercab` | **The tower cab view is half wasted.** About 20 % of the frame is the white roof of the lower head level and about 12 % is the black console band. The T1 apron and the runway intersections below the tower, the controllers' main view, are hidden; only distant taxiways show. | In the `app.js` tower view, put the eye ~0.5 m inside the glass and pitch -12° to -15°, aimed at the 18L/36R midpoint rather than due west. Alternatively, skip the tower head part (not the cab) in the cab-view pass. |
| L4 | low | `view_stand_102` (background), `view_stand_404` (left), `view_stand_113` | **A field of idle airstairs on the remote aprons.** All 94 idle stair units stand at the heads of empty remote stands, where they read as clutter or as real equipment; they are inferred cues. | Park the idle stairs in the equipment areas (`SHA.markings.apron().equipment`) or in a staging strip at the apron edge, at most one per 3-4 stands. Name them as inf cues in the gates legend line. |
| L5 | low | `view_overview`, `view_t2`, `view_tower`, approach render | **Context buildings and terminal roofs are uniform flat white**, a "snow city" look. Shanghai blocks are grey, beige and brick, and the T1 / T2 roofs are grey metal. | Give each context building an albedo hashed from its OSM id (linear 0.30-0.55, grey / beige / brick palette) with roofs darker than walls. Set the terminal roof albedo to ~0.45 grey. |
| L6 | low | `view_phone_stand_233`, `view_laptop_live_stand_233` | **Card title "T2 APRONS NR. 2"** comes from the data field `area: "T2 aprons Nr. 2"` (95 stands), a German-style copy of the AIP's "Apron Nr.". | In `tools/airport/build_stands.py`, name the areas "T2 apron 2" or "Apron 2 (T2)". |
| L7 | low | `view_laptop_live_stand_233`, `view_phone_*` | **Attribution is hidden or low-contrast.** On the laptop, the open stand card covers "Umbra Open Data (CC BY 4.0)" in the footer. On the phone, the attribution is small grey text on hazy ground under the tab row. | Keep the card's bottom edge above the attribution line, or put the attribution on a fixed dark strip with contrast ≥ 4.5:1. |
| L8 | low | `view_laptop_live_t2`, `view_laptop_live_stand_233` | **"08:31 CST" is ambiguous** in an English UI; CST is also US Central time. | Show "08:31 Beijing (UTC+8)" or "CST (UTC+8)". |
| L9 | low | `view_overview`, `view_t2` | **The overview looks like 5-6 km visibility** although the snapshot METAR is CAVOK with T/Td 13 / -5 °C. The far-ground haze (`terminals.js shaGroundFarHaze`) depends on distance only and ignores the environment's σ. | Scale `uFarHaze.z` (and the strength `.x`) with the current `sigmaSurface`, clamped, so dry clear days show farther. |
| L10 | low (verify) | `view_rwy_18L`, `view_rwy_36R`, `rvm_endtop_18L` | **The first pad chevron at 18L / 36R shows only its two outer legs.** Its apex falls on the runway or the end taxiway (`chevronLastLegFromThr` = X/4 puts the apex W/4 inside the pavement end), and the end taxiway also covers part of the 60 m pad. | Re-read fig. 6.2.25. If the nearest apex belongs on the pad, set the offset so that the first apex is ≥ 0 m outside the pavement end. Either way, do not paint chevrons where taxiway pavement crosses the pad. |

## Checked and found correct (no action)

- **Orientation and scale.** T2 is west and T1 east, and both runways read 177.3°, 365 m apart. The east runway is
  dark asphalt, 45 m, with concrete 100 m ends (AIP `surface_segments_m`); the west runway is pale concrete, 60 m. The
  T2 shape matches the overlay plate. B738 / A321 / B77W against the bridges, stands and taxiways look to scale.
  Shadows fit the snapshot sun (12:15 local, azimuth ~190°, elevation ~37°; tail shadow ~1.3 × height in
  `view_bridge_230`).
- **Runway marking data** (`SHA.markings.plan()` read from the page):
  - stripes 12 × 45 m at 1.45 m gap (18L/36R) and 16 at 1.575 m (18R/36L);
  - letter before number, 9 m CAAC glyphs;
  - 1.8 m threshold bar; 1 arrow at 100 m DTHR, 5 arrows at 300 m (counted in `view_rwy_18R` / `36L`);
  - aiming point at 474 / 393 m;
  - TDZ at 150 / 300 / 600 / 750 / 900 m, with 450 m omitted at all ends (6 positions from 3,200 / 2,700 m between
    thresholds, pattern A).
- **Holds and signs.**
  - Pattern A has solid lines on the holding side, runway-side lines dashed, and a black surround (`view_hold_H1`).
  - Mandatory-marking and sign text order is right (left = threshold on the left). At H1: "18R-36L" facing east at
    x -534, "36L-18R" facing west at x -354, "36R-18L" facing north-west.
  - Location signs are outboard; the enhanced centreline is on the holding side; the hold distance is 90 m.
- **Apron paint.**
  - yellow lead-ins with black edges;
  - yellow pentagon stand plates with black numerals;
  - red stand safety lines and 45° hatching;
  - white equipment boxes with 设备区;
  - CAAC prism stand signs on the rotundas and VDGS signs, yellow with black numerals. Their placement agrees with
    photos 09, 14 and 17.
- **Bridges.** All 8 parked bridge stands dock at door L1 with no visible intersection. No aircraft is on grass, and no
  object floats or is buried.
- **Suspected VDGS clipping at 112 / 113 is not real.** From the other side (`rv_stand112_nopark`) the 112 VDGS post
  stands beside the resting 112 cab; `view_stand_113` only overlaps them in perspective.
- **FAA audit.**
  - `grep` for 0.3048 / 0.9144 / 0.1524 / 1020 / 5340 / AC 150 / FAA / ft finds only the labelled inf placeholders
    (photocell, PAPI timing, obstruction), the METAR and pressure-altitude code, and the aircraft-light rules.
  - No FAA marking, sign or lighting geometry is used.
- **Lead-on lines at the runway ends** run 60 m parallel, 0.9 m off the CL, past the tangent point through the
  designation area (`markings_desig_18L_top`). That is 6.2.8-5 as transcribed, not a defect.
- **Phone UI** (`view_phone_*`, 393 × 659): tabs, sheet, legend and card are legible and usable. The tab row scrolls
  horizontally.

## Extra renders made for this review

Saved in `docs/phase2/` as evidence (our own renders; safe to commit with the report):

| File | Shows |
|---|---|
| `review_stripes_fade.png` | crops: `view_rwy_18R` threshold (16 stripes and the "R 18" numerals blurred to blocks) next to `markings_dthr_36L_top` (16 stripes resolved), and the `view_rwy_36L` lead-ons over the arrows (H1, M4) |
| `review_under233.png` | the T2 pier between stands 229 and 234: the unpaved strip under every fixed link, rotunda and VDGS post (H2) |
| `review_nose233_top.png` | top view at 233 with a DEBUG B738: stop line under the nose tip (M5); VDGS post and bridge-area hatching on the unpaved strip (H2) |
| `review_endtop_36L_pad.png` | 36L pad: 120 m surface, chevrons over 75 m only (L1) |

Not kept (scratch only): `stand:112` / `stand:113` with and without parking (they rejected the VDGS-clipping suspect),
the 18L pad top view, and a 3° approach view of 36R. Commands:

```
SOFTGL=1 OUT=<scratch> PREFIX=rv VIEWS='stand:112,-,60,-1,25@stand112_nopark;stand:113,-,75,1,22@stand113_nopark;park:113+233;stand:113,-,75,1,22@stand113_park;look:-760.58,2.5,-138.65,77,80,40@nose233_top;look:-786,2.5,-118,160,35,70@under233' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=<scratch> PREFIX=rvm VIEWS='endtop:36L,-360,480;endtop:18L,-90,330;end:36R,150,1300,3' node livetest.mjs jobs/markings.mjs
```

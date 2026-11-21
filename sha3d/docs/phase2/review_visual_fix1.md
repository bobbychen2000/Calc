# Phase 2 fix round 1: adversarial visual review

Date: 2026-11-21. This is a report only. Nothing in `js/`, `data/`, `tools/` or `jobs/` was changed, nothing was committed,
and `sfo3d/`, `pc12/` and `hwd3d/` were not touched. There is no scoring. My job was to refute the three fixers' claims
and the integrator's result where I could, and to find regressions and new problems.

**Inputs**
- the previous review `review_visual.md` (H1-H2, M1-M6, L1-L10, plus the lead's extent-ring item);
- the fixers' and the integrator's claims;
- the 25 re-rendered `view_*.png`, each looked at in full and cropped where needed;
- the 18 `fix1_*` composites and the fixers' raw renders in `out/fix1/`;
- the Commons photos 02, 09, 13 and 19, the CAAC parameters (`standards_refs.md`, `caac_markings.js`), and
  MH 5001-2021 itself (6.2.1, 6.2.4, 6.2.8, 6.2.25 and figs. 6.2.8-2 / 6.2.25, read from the local copy);
- the data (`sha_stands.json`, the page's `SHA.markings` / `SHA.qa` hooks).

**My own renders and probes** are in `out/review1/` (SOFTGL, deviceScaleFactor 1):
- 13 day views with a read-only page probe;
- 4 night views;
- the facade-VDGS and turned-rest stands, and two exact "Fly to stand" cameras;
- the overview with and without the far ground.

The probe tested every stand node, class nose tip, mast, idle stair, equipment area and envelope against `pavedAt`. All my
runs in snapshot mode logged 0 console errors, 0 warnings and 0 page errors. Six evidence images are `review1_*.png` (end
of this report).

Severity: **high** = wrong in a named view or against the reference, fix before Phase 3. **Medium** = clearly visible or
against a cited clause or photo. **Low** = cosmetic or small.

## Summary

Most of the round-1 work holds up in the renders:
- The threshold paint now shows 12 / 12 / 16 / 16 stripes in the four named threshold views.
- The brown strip under the T1 / T2 fixed links is gone.
- Water from above is no longer ink-black.
- The night glazing is no longer clipped, and the city is no longer snow-white.
- Masts exist.
- The UI fixes (UTC+8, "T2 APRON 2", the credit strip, the Phase 5 lighting note) are all visible.

Three claims do not survive:
1. **The nose-wheel convention (M5) created a regression at the edge stands.** The stop node, which is now where the
   nose wheel stands, is itself off pavement at 18 stands. The class nose tip is off pavement at 32 stands, and 87 of 261
   painted equipment areas are more than 5 % unpaved. This is much wider than the "286-290 and 401-413, three masts" that
   the integrator reported.
2. **"Backtrack lead-ons are dropped" (M4) is only true at the outermost crossing.** At the crossing about 150 m before the
   18R and 36L thresholds, the pair pointing towards the pavement end still runs its 60 m parallels beside the arrows.
   Also, the bar / arrow cut conflicts with MH 5001-2021 6.2.8-3. That clause makes a taxiway centreline continuous where
   it crosses threshold marking, so the previous review's M4 premise was partly wrong.
3. **The haze "follows the METAR" (L9), but the named overview is not visibly clearer.** CAVOK gives σ = 3.3e-5 /m, so
   the 20 km cap binds, and the luminance contrast in every horizontal band is lower than in Phase 2.

The new masts also stand in the app's own "Fly to stand" camera at 6 of 56 contact stands. They split the named stand-233
views, and at night they draw a 220 px lamp disk. At night the new asphalt fill is a black moat around the piers. That is
exactly where photos 13 and 19 show the brightest light.

## Status of every previous finding

| # | Sev | Status | Evidence (render) | What I saw / why |
|---|---|---|---|---|
| H1 | high | **fixed** | `view_rwy_18L/36R/18R/36L`, `review1_confirmed.png` | Counted in 6× crops: 18L 6+6, 36R 6+6, 18R 8+8, 36L 8+8. A row profile across the stripe band gives 13 / 12 / 18 / 18 white runs, which includes the edge stripes. The centreline dashes resolve, and the "L 18" / "R 36" numerals are glyph shapes (3-4 px; physical size, not blur). The phone composite shows 16 / 12. No moiré in the overview or the T1 view. |
| H2 | high | **fixed** (T1 / T2 facades) | `out/review1/day/rv_under233.png`, `rv_under102.png`, `view_stand_233`, `view_bridge_230`, `view_stand_102` | Asphalt under every fixed link, rotunda and VDGS post at the T2 north pier tip and along the T1 north face; the brown ground is gone. The same OSM apron gap remains at the edge stands; see **R1**. The fill outline at the pier tips is a round disc; see **N6**. |
| M1 (a) apron flood | medium | **partly** | `view_night_t2pier`, `view_night_stand_233`, `out/review1/night/rvn_night_east_apron.png`, `review1_night.png` | The apron is lit warm: mean (113, 100, 78) sRGB, against (25, 24, 22) before. But it is one even sheet with a hard edge at the apron polygon. The asphalt fill gets no flood (**N2**), and aircraft and GSE stay unlit (**N3**). |
| M1 (b, c) airfield lights | medium | **deferred_ok** | `view_night_hold_H1`; legend line "Airfield lighting: not modelled yet (Phase 5)" (`shell.js:53`); About "Not included" (`about.js:99`) | Still black except the signs, but now honestly labelled in the legend and About as Phase 5. |
| M2 | medium | **fixed** (masts exist) | `view_tower`, `view_t1`, `view_bridge_230`, `view_stand_102`, `view_t2pier` | 73 masts: 30 m, platform head, warm lamps at night. New problems they bring: **N1** (in the stand cameras) and **N5** (positions depend on the quality tier). |
| M3 | medium | **fixed** | `view_night_t2pier` vs the Phase 2 render (crop in `out/review1/crops/night_cmp.png`) | Facade crop mean (79, 75, 70) → (41, 35, 27); p95 luminance 223 → 141; no clipped pixels. Warm, dark mullions, per-bay variation visible. |
| M4 | medium | **partly** | `out/review1/day/rv_dthr36L_top.png`, `rv_dthr18R_top.png`, `view_rwy_36L/18R`, `review1_dthr_leadons.png` | No yellow through an arrowhead or the bar now. **Refuted:** at the crossing about 150 m before the 36L and 18R thresholds, the lower pair of curves meets the centreline heading towards the pavement end and keeps both 60 m parallels beside the arrow shafts. `leadOnsDroppedInDisplacedPortion` = 4 covers only the outer crossings (s = 99 / 3191 m). Also see **N8** (6.2.8-3). |
| M5 | medium | **fixed** (convention, contact stands) | `out/review1/day/rv_nose230_low.png`, `rv_nose229_low.png`, `rv_nose233_low.png`, `rv_nose233_top.png` | B738 at 233: nose tip 4.3-4.8 m ahead of the yellow stop line in my 84° top view (model nose gear 4.32 m). B77W at 230: nose wheels on the stop line. A333 at 229: nose wheel at the line. The envelope front now runs about 3.7 m ahead of the nose. All 7 bridge stands I parked docked. The convention's side effect at the edge stands is a **regression, R1**. |
| M6 | medium | **fixed** | `view_overview` (pond (60, 67, 60) sRGB, was (31, 38, 34)), crop `out/review1/crops/ov_pond.png` | No dotted kerb outlines at overview range. Canals now read close to the asphalt roads; see **N7** (low). |
| L1 | low | **fixed** | `fix1_markings_pads.png`; page `plan()` padSrc "paved pad surface 120 m = AIP (mirror) 120 m" | Chevrons cover the 120 m pad at both 18R and 36L. The integrator showed that the "75 m conflict" was a [length, width] misreading. I agree, and so does `blast_pad_m` = [120, 75]. |
| L2 | low | **partly** | `view_tower`, `fix1_buildings_t1_hall.png` vs photo 02 | There is an arch, but in profile it reads as a rounded dome with a blue-grey face. Photo 02 shows a flat-topped hall: straight eaves, white sloping end wedges, the red "上海 SHANGHAI" letters on a white fascia. The 40 m southward offset remains (the fixer's open issue). |
| L3 | low | **partly** | `view_towercab`, `view_phone_towercab` | Re-aimed across the T1 apron at the runways; the console band is gone. Measured column by column, the grey head terrace still covers about 21 % of the laptop frame, the same share as the white roof in Phase 2. The fixer reported "15 %". |
| L4 | low | **fixed** | `view_stand_102` (background), `view_stand_404`, page `idleStairs()` | 20 units, all in equipment areas, all on pavement; none at the stand heads. 6 of 26 groups have no unit because their equipment areas are off pavement (R1). |
| L5 | low | **fixed** | `view_overview`, `view_t1`, `view_t2`, `view_tower` | Mixed grey / beige / brick blocks, darker roofs, grey terminal roofs. |
| L6 | low | **fixed** | `view_phone_stand_233`, `view_laptop_live_stand_233` | Card title "T2 APRON 2". |
| L7 | low | **fixed** | `view_laptop_live_*`, `view_phone_*` | Dark credit strip; the laptop card ends above it; on the phone it sits top right under the tabs and is readable. |
| L8 | low | **fixed** | all UI views, `ui.js:133`, `shell.js:106` | "12:15 UTC+8"; the tooltip says Beijing time. |
| L9 | low | **not_fixed** (mechanism changed, appearance did not) | `view_overview` vs Phase 2 (`review1_partly.png`); `out/review1/haze/far0_overview.png` | Page: `sigmaSurface` 3.3e-5 /m, so 0.8 / σ = 24 km, clamped to the 20 km cap. Band contrast (luminance std) at y = 120 / 180 / 240 / 300 is 8.8 / 13.2 / 20.7 / 26.7, against 10.5 / 16.9 / 23.9 / 28.4 in Phase 2. The fixer's own pair (`r2_overview_far` vs `buildings_overview_far`) also barely differs. The overview still reads hazy. |
| L10 | low | **fixed** (verified) | `fix1_markings_pads.png`; fig. 6.2.25 read from the local MH 5001-2021 | The figure shows the nearest chevron cut at the threshold line: only its outer legs, X/4, with the apex beyond the line. No chevrons on taxiway pavement now. |
| EXT (lead) extent ring | — | **fixed** | `out/review1/day/rv_ext_se.png`, `rv_ext_nw.png` (7 km), `view_overview`, `fix1_integration_extent_edge.png` | No light or dark ring from 7 km in two directions. Only the expected change from detailed to 50 m ground remains. |

## New findings (ranked)

| # | Sev | Status | Owner | Render(s) | What is wrong | Concrete fix |
|---|---|---|---|---|---|---|
| R1 | **high** | regression (from M5 + the envelope shift) | buildings (fill), markings (paint mask), gates (signs / masts) | `view_stand_404`, `out/review1/day/rv_edge290_top.png`, `rv_edge290.png`, `review1_edge_stands.png`, `out/review1/day/rv_probe.json` | **Edge stands: aircraft, paint and equipment on unpaved ground.** Probe with `pavedAt`: the stop node, now the nose wheel, is off pavement at **18 stands** (287-290, 401-413, 602). The class nose tip is off pavement at **32 stands** (adds 214, 218, 279, 286, 319, 322, 601, 603-608). **87 of 261** equipment areas, at 50 stands, are more than 5 % unpaved. That includes 212-214, 218, 279, 306, 318-322, 339-342 and 501-525, not only 286-290 / 401-413, and 65 of the 87 are ≥ 25 % unpaved. **29 of 164** envelopes are more than 5 % unpaved (608 29 %, 413 17 %). **33 of 73** mast bases are off pavement (all 7 west-remote masts, by the 12 m remote tolerance), and the remote stand signs moved onto the band. The integrator's F4.1 names only 286-290 / 401-413 and "three masts". The previous review's "no aircraft on grass" no longer holds. | (1) buildings, `build_buildings3d.py` `airside_fill`: add fill rings ahead of every stand head whose node, class tip or equipment area is unpaved. Use the same S2 "neutral grey, not grass" test as H2, cut to the aerodrome, and give them src inf ("OSM apron gap ahead of stand heads; S2 134-171"). (2) markings, `caac_decals.js`: multiply decal alpha by `paved` (or clip equipment rings to `pavedAt`) so that no paint lands on grass even where the fill is missing. (3) gates: `frontOf(g)` and `placeMasts` should require `pavedAt` ≥ 0.5 at the sign and mast foot for contact and remote stands; drop the 12 m remote tolerance once (1) exists. Re-run the probe: 0 nodes and 0 tips off pavement. |
| N1 | medium | new | gates | `out/review1/gates/rv_fly_248.png`, `rv_fly_274.png`, `rv2_vdgs_115.png`, `view_stand_233`, `view_phone_stand_233`, `view_laptop_live_stand_233`, `view_night_stand_233`, `review1_mast_camera.png` | **Masts stand in the app's stand cameras.** The rotunda-line masts sit in the view corridor of `shell.js flyToStand`. Geometry check over all 56 contact stands: a 30 m pole lies within 3 m of the centre sight line at **109, 115, 121, 248, 264, 274**, and I confirmed two by rendering the exact camera. At 233 the mast (31 m from the node) splits the named day view and covers the docking on the phone. At night its lamp sprite is a **~220 px** disk. | `gate_system.js placeMasts`: reject candidates inside the stand's camera wedge (from the nose tip along `0.75 h + 0.66 left`, ±12 m, up to the class camera distance), or put rotunda-line masts on the facade side of the walkway. `shell.js flyToStand`: try side = ±1 and pick the one with no mast within 5 m of the sight line. Lamp sprite: cap the projected radius (about 24 px) and fade it within 40 m of the camera. |
| N2 | medium | new (H2 × M1) | markings (`ground.js`), with a mask from buildings | `view_night_t2pier`, `view_night_stand_233`, `out/review1/night/rvn_night_233_far.png`, `rvn_night_east_apron.png`, `review1_night.png` | **The asphalt fill is a black moat at night.** `shaApronFlood` lights only apron class (G 255), and the new fill is runway-class asphalt (R 255, G 0). Around the T2 piers and along the T1 faces the ground is black, with the lit apron beside it. Photos 13 and 19 show this area as the brightest part of the apron. | buildings: draw the fill into the airfield map as apron class with an asphalt albedo flag, or expose a 1 m `uAirsideFill` mask. markings: `apronN = paved * max(smoothstep(0.86, 0.95, apt.g), fillMask)` in `shaApronFlood` (decals use the same chunk). Tag inf. |
| N3 | medium | new (deferred by the integrator, but not labelled) | other (aircraft shaders), plus objects.js / `js/world/gates.js` for GSE | `view_night_t2pier` (crop in `review1_night.png`), `view_night_stand_233` | **Aircraft and GSE are unlit black silhouettes on a lit apron.** Photo 19 shows lit fuselages and wings. The legend lists "apron glow" as inf but says nothing about the unlit aircraft. | Include `sha_apron_flood` in the aircraft and object programs. Sample `uAptMap` at `wp.xz` and add `alb * shaApronFlood(...) * uNight * (0.5 + 0.5 * max(N.y, 0))` below about 20 m. Until then, add one clause to the legend's lighting line ("aircraft and vehicles are not lit at night"). |
| N4 | low | new | markings (`ground.js`), with gates positions | `out/review1/night/rvn_night_east_apron.png`, `view_night_t2pier` | **The flood is an even sheet with a hard polygon edge.** It does not fall off with distance from the masts, there are no pools under the lamp heads, and nothing spills onto the taxiway beyond the apron edge. It reads as a glowing carpet. | Per-mast falloff from `SHA.qa.masts()` (for example `1 / (1 + (d / 60 m)^2)`, normalised to the 0.42 mean), plus a 20-30 m soft spill past the apron edge. Tag inf. |
| N5 | low | new | gates | `out/review1/day/rv_probe.json` vs `out/review1/gates/masts.json` | **Mast placement depends on the quality tier.** High-tier runs (snapshot and 21:30) agree with each other. A low-tier run has 3 masts elsewhere (for example (-762.7, 1216.5), (-737.4, 994.1), (-883.9, -1179.7) exist only at high), and different rejection counts (post 8 vs 10, spacing 4299 vs 4287). So the phone and the laptop show different masts. The integrator's "identical rejection counts" held within one tier. | Make the obstacle inputs of `placeMasts` (the "post" list) independent of the quality tier, and sort candidates deterministically. Log a hash of the mast list in `SHA.qa.masts().stats` and compare it across tiers in `jobs/gates.mjs`. |
| N6 | low | new | buildings | `view_t2pier` (crop `out/review1/crops/t2pier_fill.png`), `view_bridge_230` | **The pier-tip fill is a large round dark disc** (the corner discs). Photo 09 shows a straight service road along the facade with white lane lines, text and parking boxes. The fill is plain dark asphalt (about 50 grey, against about 95 in photo 09). | Build the pier-tip fill as a mitred offset of the pier outline, not discs. Raise the asphalt albedo a little for the fill. Optional: service-road edge lines, as inf. |
| N7 | low | new (side effect of M6) | markings | `view_overview`, crop `out/review1/crops/ov_pond.png` | **From above, canals now have nearly the tone of the asphalt roads** (water (60, 67, 60), roads about 70 grey), so they read as roads. | Water body slightly greener and lighter (about 0.055, 0.07, 0.065 linear), or a reflection floor of about 0.1, so water reads as water at overview pitch. |
| N8 | low | new (introduced by the M4 fix; also corrects the previous review) | markings | `out/review1/day/rv_thr18L_top.png`, `rv_thr36R_top.png`, `review1_dthr_leadons.png` | **The lead-on cut at the threshold bar and arrows conflicts with MH 5001-2021 6.2.8-3**: "滑行道中线标志与跑道入口标志交叉时应连续" (a taxiway centreline that crosses threshold marking is continuous; fig. 6.2.8-2 shows it crossing the threshold stripes). The bar is threshold marking (6.2.4-4), and table 6.2.4-2 calls the arrows "入口标志箭头". Now the code is continuous over the 18L / 36R stripes, which is correct, but cuts 0.9 m short of the 1.8 m bar and the arrowheads. The previous review cited only 6.2.1-2. | In `caac_decals.js rwyMarkWins`, remove the bar and the arrow legs from the cut (6.2.8-3), and keep the numeral cut (6.2.1-2). Solve the original M4 symptom with the direction filter alone. That filter must also cover the inner crossings: apply `leadOnAllowed` to the OSM points clamped onto the 0.9 m offset, not only to the `extra` parallels. Record the clause in `caac_markings.js`. |

## Claims refuted or corrected

- **Markings M4** "the 4 lead-ons that point back towards the pavement end are dropped". True for s = 99 / 3191 m only. At
  the next crossing in (about 150 m before the 36L and 18R thresholds) the backtrack pair keeps its parallels (my top
  views `rv_dthr36L_top`, `rv_dthr18R_top`; the fixer's own `a2_endtop_36L_-150_300` shows the same).
- **Integrator F4.1** "286-290 and 401-413 … three masts". The probe finds 18 stop nodes and 32 class tips off pavement,
  87 unpaved equipment areas and 33 mast bases off pavement (R1).
- **Integrator** "masts unchanged (identical rejection counts)". This is true within a quality tier. Across tiers, 3
  masts move (N5).
- **Buildings L9** "mid-distance clearer". It is not visible in the named overview, and the band contrast is lower (L9).
- **Buildings L3** "terrace about 15 % of the frame". I measured about 21 %, the same share as before (L3).
- **Gates M2** "each mast clears … envelopes, lanes, bridges, posts, buildings". True, but not the app's own stand
  cameras (N1).
- **Reviewer self-correction.** Previous review M4 recommended cutting lead-ons at the bar and arrows under 6.2.1-2.
  6.2.8-3 and fig. 6.2.8-2 say they are continuous across threshold marking (N8). I also suspected that the yellow
  lead-ons crossing the 18L / 36R threshold stripes were a defect. They are correct per 6.2.8-3, so I withdrew it.

## Checked and found correct (no action)

- **Stripe counts and pads.** Stripe counts in the four threshold views and on the phone. The 120 m chevrons at 18R and
  36L. The cut nearest chevron at 18L / 36R matches fig. 6.2.25.
- **Stop line and docking.** At 233 (B738), 230 (B77W) and 229 (A333) the nose wheel is at the stop line. All my parked
  bridge stands dock: 229, 230, 231, 233, 234, 113 and 102.
- **Facade VDGS and turned rest poses** (115, 120, 121, 126; 111 at -11°, 250 at +12°; `out/review1/gates/`): no
  clipping or floating seen. At 115 the stand camera is blocked by a mast (N1).
- **UI.** UTC+8, "T2 APRON 2", the credit strip contrast and position, and the Phase 5 lighting statement in the legend
  and About.
- **Console.** All my snapshot runs, with DEBUG parking, logged 0 errors, 0 warnings and 0 page errors.

## Evidence images (our renders, deviceScaleFactor 1)

| File | Shows |
|---|---|
| `review1_edge_stands.png` | R1: `view_stand_404` and a top view of 288 / 290. Noses, envelope fronts, equipment boxes, sign posts and a mast on the unpaved band |
| `review1_mast_camera.png` | N1: the exact "Fly to stand" cameras at 248 and 274, the laptop stand-233 view, and the 220 px night lamp disk |
| `review1_night.png` | N2 / N3 / N4: black fill moat at the T2 pier, even flood with a hard polygon edge, unlit aircraft |
| `review1_dthr_leadons.png` | M4 / N8: 36L and 18R inner crossing (backtrack parallels kept), and 18L (continuous over the stripes, cut at the bar) |
| `review1_confirmed.png` | H1 / H2 confirmed: stripe crops 6+6 / 6+6 / 8+8 / 8+8, asphalt under the T2 pier tip and along the T1 face |
| `review1_partly.png` | L3 / L2 / L9: the tower-cab terrace (about 21 %), the T1 hall dome profile, the overview haze bands then and now |

Commands (from `sha3d/`; jobs in `out/review1/`, read-only):

```
SOFTGL=1 OUT=out/review1/day PREFIX=rv T=snapshot PROBE=1 VIEWS='park:229+230+231+233+234+113+102+403+404+290+288;look:-760.58,2.5,-138.65,77,84,32,40@nose233_top;look:-760.58,3.2,-138.65,197,7,15,45@nose233_low;look:-859.66,3.4,-181.23,117,6,18,45@nose230_low;look:-928.82,3.4,-177.99,118,6,18,45@nose229_low;look:-786,2.5,-118,160,35,70@under233;look:719.2,2.5,-1,200,35,70@under102;look:-723,2.5,1050,60,30,140@edge290;look:-726,2.5,1050,268,86,140,50@edge290_top;endtop:18L,30,160@thr18L_top;endtop:36R,30,160@thr36R_top;look:0,2.5,0,135,32,7000@ext_se;look:0,2.5,0,315,32,7000@ext_nw' node livetest.mjs out/review1/rv.mjs
SOFTGL=1 OUT=out/review1/day PREFIX=rv T=snapshot VIEWS='endtop:36L,-150,300@dthr36L_top;endtop:18R,-150,300@dthr18R_top' node livetest.mjs out/review1/rv.mjs
SOFTGL=1 OUT=out/review1/night PREFIX=rvn T=2026-11-20T13:30:00Z PROBE=1 VIEWS='park:403+404+102+113+233;look:-760.58,2.5,-138.65,250,30,260@night_233_far;look:600,2.5,-300,250,22,900@night_east_apron' node livetest.mjs out/review1/rv.mjs
SOFTGL=1 OUT=out/review1/gates node livetest.mjs out/review1/rv2.mjs      # facade VDGS / turned rest poses
SOFTGL=1 OUT=out/review1/gates node livetest.mjs out/review1/rv3.mjs      # all mast positions (low tier)
SOFTGL=1 OUT=out/review1/gates PREFIX=rv T=snapshot VIEWS='look:-1043.03,2.5,130.94,-133.42,24,120,50@fly_248;look:-1104.91,2.5,655.66,-133.91,24,90,50@fly_274' node livetest.mjs out/review1/rv.mjs
SOFTGL=1 OUT=out/review1/haze PREFIX=far0 T=snapshot QUERY='far=0' VIEWS='overview' node livetest.mjs out/review1/rv.mjs
python3 -I out/review1/compose.py                                         # the review1_*.png composites
```

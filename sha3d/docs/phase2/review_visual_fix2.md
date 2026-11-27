# Phase 2 fix round 2: adversarial visual review

Date: 2026-11-27. This is a report only. Nothing in `js/`, `data/`, `tools/` or `jobs/` was changed, nothing was committed,
and `sfo3d/`, `pc12/` and `hwd3d/` were not touched. There is no scoring. My job was to refute the three fixers' claims
(markings: N2, M1, M4 / N8; buildings: R1, N3; gates: N1) and the integrator's result where I could, and to find
regressions and new problems.

**Inputs**
- the two previous reviews: `review_visual.md` (H1-H2, M1-M6, L1-L10, the lead's extent ring) and `review_visual_fix1.md`
  (R1, N1-N8, M1, M4);
- the fixers' and the integrator's claims, their reports (`markings.md`, `buildings.md`, `gates.md`, `relay_ui.md`,
  `integration.md`, "Fix round 2" sections) and their `fix2_*` composites;
- the 25 re-rendered `view_*.png` (2026-11-27), each looked at in full, cropped and measured where needed;
- the Commons photos (`photos_contact_sheet.jpg`: 09 T2 airside by day, 13 and 19 the apron at night), the CAAC
  parameters (`standards_refs.md`, `js/live/caac_markings.js`) and the data (`sha_stands.json`, `sha_buildings3d.json`).

**My own renders and probe** are in `out/review2/` (gitignored; SOFTGL, 1280 × 720, deviceScaleFactor 1, high tier unless
noted). I looked at every one of them.
- `day/` (snapshot instant): wide and close top views of both displaced thresholds and of the 18L bar, under the T2 north
  pier tip, the 287-290 edge stands from above, the extent from 7 km in two directions, top views of the nose wheels at
  233 (B738), 404 and 608 (A320), the app's own "Fly to stand" at 228, 259, 264 and 270, and the masts placed for 323 / 325
  from above.
- `night/` (21:30 local, the named night instant): the T2 north pier from behind and under 233, the east apron from
  900 m, "Fly to stand" 228 and 238A, 404 with an A320, and the overview.
- `day/rv_probe.json`: a read-only page probe (job `out/review2/rv.mjs`). It tests every stop node, class nose tip, mast
  foot, idle stair, equipment area and envelope against `pavedAt`; reads the light map at every stand node; and, for every
  stand, rebuilds the "Fly to stand" camera on the side the app takes (`gate_system.js standCamWedge`, `SHA.qa.standCam`)
  and lists the masts whose head or pole is inside that frame and how close they are.

Console: every run logged 0 errors and 0 page errors. The only warnings were the driver's "GPU stall due to ReadPixels"
lines from the screenshots, which the harness filters as driver noise (`livetest.mjs`, `jobs/integration.mjs`).

Severity: **high** = wrong in a named view or against the reference, fix before Phase 3. **Medium** = clearly visible or
against a cited clause or photo. **Low** = cosmetic or small.

## Summary

What holds up in my own renders and probe:
- **R1 (edge stands) is fixed for everything the previous review measured.** Probe: 0 of 164 stop nodes and 0 class nose
  tips off pavement (were 18 / 32), 0 of 261 equipment areas more than 5 % unpaved (87), 1 of 164 envelopes (101, 7 %),
  idle stairs 26 / 26 on pavement, mast feet 1 of 67 off pavement (525, on the edge). Top views of 404 and 608 with an
  A320, and of 287-290, show nose, envelope front and equipment boxes on the new stand-head concrete.
- **Nose-wheel convention** still right: B738 at 233 and A320 at 404 / 608 have the nose wheel on the yellow stop bar, the
  nose tip 4.8 / 5.3 m ahead of it (model nose gear 4.32 / 5.07 m), the envelope front about 3.7 m ahead of the nose.
- **Threshold stripes** in the four named views: 6 + 6, 6 + 6, 8 + 8, 8 + 8 (row profile: 14 runs including the two edge
  lines at 18L / 36R).
- **N8**: taxiway centrelines now run unbroken over the 1.8 m threshold bar at 18L (close top view) and across the
  stripes, and stop only at the "L 18" numerals (6.2.8-3, 6.2.1-2).
- **M4**: the markings fixer's explanation is right. In 520 m top views of both displaced portions, the 60 m parallels
  beside the arrow shafts connect at their lower end to the outer crossing's curves, which turn towards the threshold
  (take-off, 6.2.8-5). The inner crossing's backtrack curves end short of them. The previous review misread which pair
  owned the parallels.
- **N3**: parked aircraft, GSE, bridges, stairs and buses are lit at night (B738 fuselage (122, 108, 92) sRGB over an
  apron of (92, 80, 62) at 233; A320 at 404 lit), and the legend and About say so.
- **The lamp-sprite cap works**: no lamp disk larger than about 50 px anywhere in my night renders.

What does not hold up:
1. **N2 / M1: the T2 north pier tip is a dark moat again in both named night views.** The integrator found this, and my
   renders confirm it. Under the 233 bridges the fill measures (32, 27, 22) sRGB in `view_night_stand_233` and (28, 24, 20)
   in my own render, against (90, 78, 61) on the apron beside it. The round-1 "moat" was (32, 28, 21). The light map puts
   14 stand nodes at exactly half the stand mean (231-234, 110-112, 121, 126, 333-337) and 4 more within 0.05 of it (250,
   262, 263, 413). That is less than MH 5001-2021 9.2.6 asks for on a stand. Photos 13 and 19 show this band as the
   brightest part of the apron at night.
2. **N1: masts are still in the "Fly to stand" frames, just not over the subject.** My probe rebuilt every stand's camera
   on the side the app takes. At 21 stands a mast head (or its pole at mid-height) is inside the frame and at most 39 m from
   the camera, so a 3 m head is at least 60 px wide. I rendered five of them, and in every one the mast is the largest
   object in the foreground:
   - 238A: the black six-lamp head fills the lower-right quarter (the integrator's finding);
   - 264: the 265 mast head, 14 m away, fills the upper-left of the frame;
   - 270: the 270 mast head, 15 m away, about 250 px wide, right of centre;
   - 228 and 259: a 30 m pole stands just right of where the parked aircraft's wing tip will be (clearance 1.05 and 1.04 ×
     the 4° margin), with its head 20-23 m from the camera.
   The fixer's claim "no mast in the subject or centre margins" is true. "N1 fixed" is not: the test guards only the subject
   hull and the centre band, not the near field of the camera.
3. **The integrator's "only 238A shows the head in frame" is refuted** by the 228, 259, 264 and 270 renders.
4. **Two masts stand in painted equipment areas** (placed for 323 and 325, business apron). The integrator checked masts
   against envelopes, not against the 设备区 boxes.

Nothing in my runs contradicts the console claims: 0 errors, 0 page errors in snapshot and night runs with DEBUG parking.

## Status of every previous finding

From `review_visual.md` (Phase 2 review) and `review_visual_fix1.md` (fix round 1 review). M1 (a) and M4 carry the fix
round 1 re-review's text; N4 is the shape part of M1.

| # | Sev | Status | Owner | Evidence (render) | What I saw / why |
|---|---|---|---|---|---|
| H1 | high | **fixed** | markings | `view_rwy_18L/36R/18R/36L`, crops in `review2_confirmed.png` | Counted again in 4× crops: 6 + 6, 6 + 6, 8 + 8, 8 + 8. A row profile across the band gives 14 white runs at 18L / 36R (12 stripes plus the two edge lines). Numerals and centreline dashes resolve. |
| H2 | high | **fixed** (day) | buildings | `out/review2/day/rv_under233.png`, `view_stand_233`, `view_bridge_230`, `view_stand_102` | Asphalt under every fixed link, rotunda and VDGS post at the T2 north pier tip and along the T1 face. At night this band is the problem of N2. The disc outline is N6. |
| M1 (a) | medium | **partly** | markings (with gates) | `view_night_t2pier`, `view_night_stand_233`, `out/review2/night/rvn_night_east_apron.png`, `rvn_night_233_far.png`, `review2_pier_tip_night.png`, `review2_night.png` | The shape is better: pools around the mast rows and a soft 20-30 m edge onto the taxiways (east apron from 900 m). But the pools follow the masts, and where gates N1 removed the masts the apron drops to the 0.5 floor. That includes whole stands: 14 stand nodes sit at the floor (231-234, 110-112, 121, 126, 333-337) and 4 just above it (250, 262, 263, 413). The named night views show the darkest part exactly at the stand being viewed (233). See **V1**. |
| M1 (b, c) | medium | **deferred_ok** | other (Phase 5) | `view_night_hold_H1`; legend lighting line (`shell.js:54`), About "Not included" (`about.js:99`) | Black except the lit signs. The legend and About say "Airfield lighting: not modelled yet (Phase 5)". |
| M2 | medium | **fixed** (masts exist) | gates | `view_tower`, `view_t1`, `view_stand_113`, `view_stand_102`, `view_stand_404` | 67 masts, 30 m, six-lamp heads. Their placement creates **V2** (in the "Fly to stand" frames) and **V4** (inside two equipment boxes, plates on the pavement edge). |
| M3 | medium | **fixed** | buildings | `view_night_t2pier`, `out/review2/night/rvn_night_under233.png` | Warm curtain walls with dark mullions and per-bay variation; no clipping. |
| M4 | medium | **fixed** (the previous review's diagnosis was half wrong) | markings | `out/review2/day/rv_dthr36L_wide.png`, `rv_dthr18R_wide.png` (520 m top views), crops in `review2_leadons.png` | The parallels beside the arrow shafts start at the **outer** crossing near the pavement end, whose curves turn towards the threshold (take-off, allowed by 6.2.8-5), and run 60-66 m north. The inner crossing's pair that heads towards the pavement end now stops short of them (`backtrackClear` 0.9 m, inf), and no longer owns a parallel. In the named views the gap is 1-2 px, so it still reads as one line; see **V6** (low). |
| M5 | medium | **fixed** | gates | `out/review2/day/rv2_nose233_top.png`, `rv2_nose404_top.png`, `rv2_nose608_top.png` | B738 at 233: nose wheel on the stop bar, nose tip about 4.8 m ahead (model 4.32 m). A320 at 404 and 608: 5.3 m (5.07 m). Envelope front about 3.7 m ahead of the nose. |
| M6 | medium | **fixed** | buildings | `view_overview` | Unchanged since fix round 1. The canal tone is N7. |
| L1 | low | **fixed** | markings | `out/review2/day/rv_dthr36L_wide.png` | Chevrons over the whole pad at 36L / 18R. |
| L2 | low | **partly** (not in this round) | buildings | `view_tower` | The T1 hall is still a rounded dome with a blue-grey face. Photo 02 shows a flat-topped hall with a white fascia. |
| L3 | low | **partly** (not in this round) | buildings | `view_towercab`, `view_phone_towercab` | The head terrace still covers about 20 % of the laptop frame (column measurement, 19.7 %). |
| L4 | low | **fixed** | gates | probe: `idleStats` 26 placed, 26 in equipment areas, 0 off pavement | All 26 groups have a unit now (20 before R1). |
| L5 | low | **fixed** | buildings | `view_overview`, `view_t1`, `view_t2` | Unchanged. |
| L6 | low | **fixed** | gates | `view_phone_stand_233`, `view_laptop_live_stand_233` | "T2 APRON 2". |
| L7 | low | **fixed** | gates (ui) | `view_laptop_live_*`, `view_phone_*` | Credit strip readable; the laptop card ends above it. |
| L8 | low | **fixed** | gates (ui) | all UI views | "12:15 UTC+8" / "19:49 UTC+8". |
| L9 | low | **not_fixed** | buildings | `view_overview` | Luminance std in 20-row bands at y = 120 / 180 / 240 / 300: 5.7 / 12.8 / 17.7 / 22.8, identical to the committed fix round 1 render. The CAVOK overview still reads as 5-6 km visibility. |
| L10 | low | **fixed** | markings | `view_rwy_18L`, `view_rwy_36R` | First chevron cut at the threshold line (fig. 6.2.25). |
| EXT | — | **fixed** | buildings | `out/review2/day/rv_ext_se.png`, `rv_ext_nw.png` (7 km), `view_overview` | No ring from 7 km in two directions; only the expected change from detailed to 50 m ground. At night the whole surround is black (**V5**). |
| R1 | high | **fixed** (what was measured); residuals low | buildings (fill), gates (posts) | `view_stand_404`, `out/review2/day/rv_edge290_top.png`, `rv2_nose404_top.png`, `rv2_nose608_top.png`, `rv_probe.json`, `review2_confirmed.png` | Probe (the previous review's method): stop nodes 18 → **0**, class nose tips 32 → **0**, equipment areas > 5 % unpaved 87 → **0** of 261, envelopes 29 → **1** of 164 (101, 7 %), mast feet 33 → **1** of 67 (525, pavedAt 0 at its centre). The fill is `src inf` with its evidence and rule in the data. Residuals: the remote stand-number posts stand 3-4 m past the paved head on the grass verge (top view 287-290; allowed by 8.5.3 as the integrator argues, but the previous fix asked for pavement); decal × paved was not applied. |
| N1 | medium | **partly** (fixer: fixed; refuted) | gates | `view_stand_233`, `view_night_stand_233`, `view_phone_stand_233`; `out/review2/day/rv2_fly228.png`, `rv2_fly259.png`, `rv2_fly264.png`, `rv2_fly270.png`, `night/rvn_night_fly228.png`, `rvn_night_fly238A.png`; `review2_fly_masts.png` | The named 233 views are clean, the lamp disk is capped (I saw no glow over about 50 px), and no pole crosses the subject. But the image test only guards the subject hull and the ±8° centre band. My probe finds a mast head inside 21 "Fly to stand" frames at 10-39 m from the camera. In all five I rendered, the mast is a large foreground object: 238A (head fills the lower right quarter, black at night), 264 (head 14 m away, upper left), 270 (head 15 m away, right of centre), 228 and 259 (pole at the wing-tip line, head 20-23 m away). See **V2**. |
| N2 | medium | **partly** | markings (with gates) | `view_night_stand_233`, `view_night_t2pier`, `out/review2/night/rvn_night_under233.png`, `rvn_night_233_far.png`, `review2_pier_tip_night.png` | The fill is no longer black anywhere (round 1 under the 233 bridge: (0, 0, 1), as the markings fixer measured it). But at the T2 north pier tip, the place the review named, it is (32, 27, 22) in `view_night_stand_233` and (33, 28, 22) in my far view. That is the round-1 moat level, against (59, 51, 41) in the markings fixer's own 73-mast render. The two named night views show it. |
| N3 | medium | **fixed** | buildings + integration | `view_night_t2pier`, `view_night_stand_233`, `out/review2/night/rvn_night_404.png` | Aircraft, GSE, bridges, stairs and buses are lit at night. The B738 at 233 is (122, 108, 92) over an apron of (92, 80, 62). The legend says the glow "also lights the aircraft, vehicles and jet bridges". The terminal roofs, which opt out, are **V3**. |
| N4 | low | **fixed** | markings | `out/review2/night/rvn_night_east_apron.png` | Pools around the mast rows; the apron edge falls off over about 10-15 px from 900 m (20-30 m). |
| N5 | low | **not_fixed** (not in this round) | gates | `view_phone_t2_legend` ("Apron floodlight masts: 66") vs `view_laptop_live_t2` ("67") | The phone (low tier) and the laptop (high tier) still show different mast lists, and the light pools follow them. |
| N6 | low | **not_fixed** (not in this round) | buildings | `view_t2pier`, `out/review2/day/rv_under233.png` | The pier-tip fill is still a round dark disc. |
| N7 | low | **not_fixed** (not in this round) | buildings | `view_overview` | Unchanged. |
| N8 | low | **fixed** | markings | `out/review2/day/rv_thr18L_close.png`, `rv_thr18L_top.png` | Both lead-on parallels cross the 1.8 m bar without a gap. The side lead-on crosses the stripes diagonally and is cut only over "L 18" (6.2.8-3, 6.2.1-2; recorded as `taxiway.crossThreshold` / `cutAtDesignation`). |

## New findings (ranked)

| # | Sev | Status | Owner | Render(s) | What is wrong | Concrete fix |
|---|---|---|---|---|---|---|
| V1 | **medium** | new (markings M1 × gates N1; reported by the integrator, confirmed here) | markings (option: gates) | `view_night_stand_233`, `view_night_t2pier`, `out/review2/night/rvn_night_under233.png`, `rvn_night_233_far.png`, `review2_pier_tip_night.png`; probe `lightAtNodes`, `lightLowNodes` | **Stands lit at half the stand level, and the T2 pier tip back to the round-1 moat.** The pools are normalised to the stand mean and clamped at 0.5 (9.2.6-2), and the clamp is applied to stands too. 14 stand nodes sit at 0.50 (231-234, 110-112, 121, 126, 333-337) and 4 more within 0.05 (250, 262, 263, 413). At the T2 north pier tip, the asphalt fill (albedo 0.085) under that light measures (32, 27, 22) sRGB in the named view and (28, 24, 20) under the 233 bridge, next to (90, 78, 61) on the apron. The two named night views show the darkest ground exactly at the viewed stand. Photos 13 / 19 show this band brightest. MH 5001-2021 9.2.6 sets the stand average as the level on stands; the 50 % floor is for other apron areas. | In `markings.js applyMastPools`: after the normalisation, floor every texel inside a painted stand envelope (`SHA.markings.apron().envelopes`), and every airside-fill texel within 60 m of a contact stand node, at 1.0 of the stand mean before the gain. Keep the 0.5 floor only for the rest of the apron, then recompute the gain so that the lit-area mean stays at the accepted level. Record it as `CAAC.apronFlood.standFloor` (9.2.6, inf). Re-measure the fill under 233 (target: at least the markings fixer's (59, 51, 42)). Alternative (gates): re-admit one pier-tip mast with `STAND_CAM.subjDeg` relaxed there. |
| V2 | **medium** | new (the residual of N1; extends the integrator's 238A item) | gates | `out/review2/day/rv2_fly228.png`, `rv2_fly259.png`, `rv2_fly264.png`, `rv2_fly270.png`, `night/rvn_night_fly228.png`, `rvn_night_fly238A.png`, `review2_fly_masts.png`; probe `camsBigHead` | **"Fly to stand" frames still contain a 30 m mast in the near field at 21 stands.** The image test keeps the pole 4° off the subject hull and out of the ±8° centre band, but it allows a pole and head 10-39 m from the camera anywhere else in the frame. Largest: 238A (head 10 m away, lower right quarter, a black silhouette at night), 264 (265 mast, 14 m), 270 (15 m), 228 (20.5 m, pole just right of the wing-tip line, clearance 1.05), 259 (23 m, clearance 1.04), then 223, 275, 329 (side -1), 221, 411, 236, 311, 303, 324, 308, 102, 226, 265, 266, 315. The probe reproduces the app's side choice (`SHA.qa.standCam`) and camera (`standCamWedge`). | `gate_system.js`: add a near-field term to `standCamPos` / `placeMasts`. Reject a candidate when, on any side the app can take, the head or the pole above 10 m projects inside the frame (\|X\| < 1, \|Y\| < 1) at a depth under about 45 m (a 3 m head then stays under about 50 px), or the pole comes within 25 m (3-D) of the camera position. `shell.js standCamSide`: prefer the side with no near-field mast. `jobs/gates.mjs SET=fix2`: print the stands with a near-field head and require 0 for contact stands. Where coverage suffers, move the mast, not the camera. Optional: an emissive lamp face, so a near head is not a black block at night. |
| V3 | low | new (pre-existing; more visible now that the apron around it is lit) | buildings | `out/review2/night/rvn_night_under233.png` (roof (1, 2, 4) sRGB), `view_night_t2pier`, `review2_pier_tip_night.png` | **Terminal and pier roofs are pure black at night**, next to an apron of about (90, 78, 61). They opt out of the object flood (`noFlood`, because the spill made them glow), and nothing else lights them. From the night views they read as holes cut into the picture. | `objects.js`: for `noFlood` items, add a small night ambient on upward faces, about 0.1-0.15 of the apron flood level times albedo with the same warm tint, or a sky-glow term from the environment's night sky colour. Keep it below the facade glow. Tag inf. |
| V4 | low | new | gates | `out/review2/day/rv2_mast323_top.png`, `rv2_mast325_top.png`, `rv2_nose608_top.png`, `docs/phase2/fix2_integration_masts_paved.png`, `review2_masts_misc.png`; probe `mastsInEquipment` | **Two masts stand in painted equipment areas (设备区), and several base plates hang over the pavement edge.** The probe finds the feet of the masts placed for 323 and 325 inside equipment rings; in the top views they stand at a box corner. `placeMasts` tests envelopes, not equipment areas. The "on pavement" rule tests only the pole centre: at 608, 407 and 288-290 the base plate straddles the edge of the stand-head fill, and at 525 the centre itself reads pavedAt 0. | `gates.js` already has `apron.equipment` where it calls `placeMasts` (line 212, used for the idle stairs): pass it in next to `envelopes`, and reject candidates inside an equipment ring plus 2 m. Test `pavedAt` ≥ 0.5 at the four corners of the base plate plus a 1 m margin. Re-run the integrator's probe with the equipment test added. |
| V5 | low | new | buildings (far ground, context) | `out/review2/night/rvn_night_overview.png`, `review2_night.png` | **At night everything outside the two lit aprons is black**: the landside of T1 / T2, the roads, the context blocks and the far ground, apart from a few lit window patches. Shanghai's surroundings are bright at night. In the overview the airport reads as two glowing carpets in a void. This view is not in the named set; the night views that are don't show it. | Give the far ground's built-up class (WorldCover) and the context LOD blocks a dim warm night emissive, scaled by the environment's night factor (`uFloodNight`), labelled inf in the legend's lighting line. Keep it well below the apron flood. |
| V6 | low | new (residual of M4) | markings | `view_rwy_36L`, `view_rwy_18R`, crops in `review2_leadons.png` | **In the named runway views the backtrack curves still read as flowing into the take-off parallels.** The 0.9 m clearance is 1-2 px at that range, and the curve ends exactly where the outer pair's parallels end. So the original M4 picture (yellow from the inner crossing towards the pavement end beside the arrow shafts) is still what a viewer sees, although the geometry is now right. | Stop backtrack curves at the runway edge (or at least 5 m short of the lead-on line), or do not draw them in a displaced portion at all. Either is inf, because ZSSS paint is not observed; record the choice next to `CAAC.taxiway.backtrackClear`. |
| V7 | low | new | other (`jobs/views.mjs`, integration) | `view_laptop_live_t2`, `view_laptop_live_stand_233` (19:46-19:49 local, after dark; day views in round 1) | **The named laptop views depend on the wall clock.** They run in live mode, so this round's set shows night while the previous set showed day. They can't be compared across rounds, and the laptop day UI is no longer in the named set. | Render the live laptop views with the relay mock and a pinned `t=` (or `T=snapshot` plus the live UI), and record the instant in `integration.md`. Keep one deliberate night laptop view if it is wanted. |

## Claims refuted or corrected

- **Gates N1 "fixed"** and **integrator "only 238A shows the head in frame"**: refuted. Of the 21 stands my probe lists,
  I rendered 228, 238A, 259, 264 and 270, and all five show a mast head as the largest foreground object (V2). The fixer's
  narrower claims hold: no pole in the subject or centre margins, the named 233 views are clean, and the lamp disk is capped.
- **Markings N2 "fixed"**: partly. The fixer's (59, 51, 42) under the 233 bridge was measured with the 73 pre-N1 masts.
  With the final 67 it is (32, 27, 22), the round-1 level (V1). This is a conflict between two parallel fixes, not a code
  error in either. The integrator found it and correctly left it open.
- **Markings M1**: "stands × 1.28" is the stand **mean**. 14 stand nodes sit at the 0.5 floor (the integrator says 23; my
  count is 14 at the floor and 18 within 0.05 of it).
- **Integrator "masts inside a painted envelope: 0"**: true, but two stand inside painted equipment areas (V4).
- **Previous review M4**: its premise was half wrong. The parallels belong to the outer take-off lead-ons (6.2.8-5), as
  the markings fixer showed. Confirmed in 520 m top views.

## Checked and found correct (no action)

- **Threshold stripes** 6 + 6 / 6 + 6 / 8 + 8 / 8 + 8 in the named views; chevrons; first chevron cut at 18L / 36R.
- **N8**: lead-ons continuous over the bar and the stripes, cut only at the numerals.
- **Nose wheels on the stop lines** at 233 (B738), 404 and 608 (A320); the 233 bridge docks; the parked A320s get stairs
  and buses.
- **Stand-head fill** (`src inf`, evidence and rule strings in `sha_buildings3d.json`): reads as continuous apron concrete
  in `view_stand_404` and the 287-290, 404 and 608 top views, and ends 3-4 m past the envelope fronts.
- **Night**: aircraft, GSE and bridges lit; no lamp disk over about 50 px; warm glazing; the legend and About lighting
  lines match what is drawn (airfield lighting Phase 5).
- **Extent from 7 km**: no ring.
- **UI**: phone and laptop views legible; "T2 APRON 2", UTC+8, credit strip, DEBUG line first. The phone legend's 66 masts
  against the laptop's 67 is N5.
- **Console**: 0 errors, 0 page errors in all my runs (snapshot, night, DEBUG parking); only the filtered driver lines.

## Evidence images (our renders, deviceScaleFactor 1)

| File | Shows |
|---|---|
| `review2_pier_tip_night.png` | V1 / N2: the named night 233 view, under 233 at 21:30 (fill, apron and roof values), and the T2 pier tip from behind with 73 masts (markings fixer) and with the final 67 |
| `review2_fly_masts.png` | V2 / N1: "Fly to stand" 228 and 238A at night, 264 and 270 by day; the mast head in the near field in each |
| `review2_leadons.png` | M4 / N8 / V6: 520 m top views of the 36L and 18R displaced portions (outer curves into the parallels, inner backtrack curves stopping short), the named-view crops, and 18L (continuous over the bar and stripes, cut at "L 18") |
| `review2_confirmed.png` | R1 / M5 / H1: 287-290 from above, the nose wheels at 233, 404 and 608, `view_stand_404`, stripe crops |
| `review2_night.png` | N3 / N4 / V5: east apron pools from 900 m, the night overview (black surroundings), `view_night_t2pier`, 404 at night |
| `review2_masts_misc.png` | V4 / N5: masts in equipment boxes (323, 325), a base plate on the pavement edge (608), and the phone (66) vs laptop (67) mast counts |

Commands (from `sha3d/`; job and compositor in `out/review2/`, read-only):

```
SOFTGL=1 OUT=out/review2/day PREFIX=rv T=snapshot PROBE=1 VIEWS='endtop:36L,-200,520@dthr36L_wide;endtop:18R,-200,520@dthr18R_wide;endtop:36L,-150,300@dthr36L_top;endtop:18R,-150,300@dthr18R_top;endtop:18L,30,160@thr18L_top;endtop:18L,0,60@thr18L_close;look:-786,2.5,-118,160,35,70@under233;look:-726,2.5,1050,268,86,140,50@edge290_top;look:0,2.5,0,135,32,7000@ext_se;look:0,2.5,0,315,32,7000@ext_nw' node livetest.mjs out/review2/rv.mjs
SOFTGL=1 OUT=out/review2/night PREFIX=rvn T=2026-11-20T13:30:00Z VIEWS='park:233+404;look:-760.58,2.5,-138.65,250,30,260@night_233_far;look:-786,2.5,-118,160,35,70@night_under233;look:600,2.5,-300,250,22,900@night_east_apron;fly:228@night_fly228;fly:238A@night_fly238A;stand:404,-,75,1,22@night_404;overview@night_overview' node livetest.mjs out/review2/rv.mjs
SOFTGL=1 OUT=out/review2/day PREFIX=rv2 T=snapshot VIEWS='park:233+404+608;look:-760.58,2.5,-138.65,77,84,32,40@nose233_top;look:-884.77,2.5,-1374.2,268,84,40,40@nose404_top;look:-727.66,2.5,1622.96,268,84,40,40@nose608_top;fly:228@fly228;fly:264@fly264;fly:270@fly270;fly:259@fly259;masttop:323,90@mast323_top;masttop:325,90@mast325_top' node livetest.mjs out/review2/rv.mjs
python3 -I out/review2/compose.py                                         # the review2_*.png composites
```

(`stand:404,-,75,1,22` in the night run went through `rv.mjs`'s `stand:` kind, which has no ICAO slot, so it became a
low 1° view; it still shows the lit A320 and is kept as such.)

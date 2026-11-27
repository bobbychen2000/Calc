# Phase 2 fix round 3: adversarial visual review

Date: 2026-11-27. This is a report only. Nothing in `js/`, `data/`, `tools/` or `jobs/` was changed, nothing was committed,
and `sfo3d/`, `pc12/` and `hwd3d/` were not touched. There is no scoring. My job was to refute the three fixers' claims
(markings: V1, V6, the stale mast count; gates: V2, V4, N5; buildings: V3, V5, L9, N6, L3) and the integrator's result
(V7, the hand-offs, the 25 re-rendered named views) where I could, and to find regressions and new problems.

**Inputs**
- `review_visual_fix2.md` (V1-V7, N1, N2, N5, M1, L2, L3, L9, N6, N7) and its probe `out/review2/rv.mjs`;
- the fixers' and the integrator's claims, the "Fix round 3" sections of `markings.md`, `gates.md`, `buildings.md`,
  `relay_ui.md`, `integration.md`, and their `fix3_*` composites;
- the 25 re-rendered `view_*.png`, each looked at, cropped and measured where a number was at stake, against the round-2
  set (`git show HEAD:sha3d/docs/phase2/view_*.png`, copied to `out/review3/before/`);
- the Commons photos (`docs/phase1/photos_contact_sheet.jpg`: 09 T2 airside by day, 13 / 18 / 19 the apron at night),
  `js/live/caac_markings.js`, `data/sha_stands.json`, `data/sha_taxigraph.json`, `data/sha_buildings3d.json`.

**My own renders and probe** are in `out/review3/` (gitignored; SOFTGL llvmpipe, 1280 × 720, deviceScaleFactor 1, high
tier unless noted). I looked at every one of them.
- `probe/`: a read-only page probe (`out/review3/rv3.mjs`, an extension of the round-2 probe), run twice: laptop, high
  tier, at the named night instant 2026-11-20T13:30Z (`hi_night_probe.json`), and iPhone 15, low tier, at the snapshot
  instant (`phone_low_probe.json`). It lists the masts (count, hash, signed distance of every foot to the nearest equipment
  area, painted envelope and bridge area, the base-plate corners + 1 m on `pavedAt` at that tier and + 2 m on
  `SHA.qa.pavedVec`, the distance to every taxiway / taxilane / lead-in centreline of the taxi graph); rebuilds every
  stand's "Fly to stand" camera on **both sides** with the app's own `standCamWedge` and `SHA.qa.camSubject` (164 stands,
  238A and 259A included) and runs **my own** near-field test on it (the head as a 4.2 × 2.7 × 2 m box, 9 points; the pole
  every 0.5 m; the 3-D camera-pole distance), next to the app's `standCamNearList`; projects every mast into the app's
  Tower view (laptop and phone framing); and reads the night light map at every stop node, on a 2 m grid over every
  envelope, bridge area and equipment area, and every 2 m along every bridge (attach → rotunda → cab, ±6 m).
- `day/` (snapshot instant): the B738 at 233 from above (nose wheel), "Fly to stand" at the review-2 five (238A, 264,
  270, 228, 259) and at the four contact stands with the largest mast heads left in frame (115, 229, 260, 274) plus 224,
  with DEBUG aircraft parked at 115, 224, 229, 233, 260, 264, 274; the T2 north pier tip from 320 m straight down; the
  gap-fill mast "289" from above; the laptop Tower view.
- `night/` (21:30 local): the review-2 camera under 233, the east apron from 900 m, the overview, the T1 faces, the T2
  middle (the long fixed links of 238-240).
- `crops/`, `tools/px.py` (median sRGB of rectangles), `tools/bands.py` (the round-2 band metric plus a high-pass detail
  contrast), `compose.py` (the `review3_*.png` evidence images).

Console: `jobs/integration.mjs SCENES=snapshot` (which filters the driver lines) → "scene snapshot: 0 error, 0 warning,
page errors 0, HTTP>=400 0, failed requests 0 -> clean". My own probe and render runs logged 0 errors and 0 page errors;
their only warnings are the driver's "GPU stall due to ReadPixels" lines, the noise the harness filters. `node
tools/buildings/test_buildings3d.mjs`: all checks passed.

Severity: **high** = wrong in a named view or against the reference, fix before Phase 3. **Medium** = clearly visible or
against a cited clause or photo. **Low** = cosmetic or small.

## Summary

What holds up, measured by me:
- **V1 / N2 (stand light) is fixed.** Light map at the final 58 masts: standLevel 1.108, **0 of 164 stop nodes below it**
  (33 within 1 LSB of it; ratio min / p10 / median / max 1.000 / 1.000 / 1.204 / 1.726), **0 of 56 bridges** with a sample
  below the level anywhere along attach → rotunda → cab (±6 m), bridge areas 0 / 56 below; `check926` other-apron min /
  stand mean 0.500. Under 233 with the review-2 camera the fill went from (27, 23, 18) to **(147, 132, 107)** sRGB; in
  `view_night_stand_233` from (31, 27, 22) to **(153, 138, 113)** (target was ≥ (59, 51, 42)). The fill is now the brightest
  ground, as photos 13 / 19 show; by how much is F2.
- **V2 (near field) is fixed by its own definition**, which I tested independently: on the side the app takes, **0 of 164**
  cameras have a mast head or pole above 10 m in the 16:9 frame closer than 45 m or a pole within 25 m; the round-2 metric
  (3 m head ≥ 60 px) gives **0** (was 21); my test and the app's `standCamNearList` agree at every stand; no contact stand
  flies from side -1; the nearest pole to any camera is 26.9 m (282). My renders of 238A, 264, 270, 228 and 259 show no
  mast in the foreground. What is left in frame at 45-80 m is F3.
- **V4 is fixed**: no foot within 3.13 m of an equipment area (nearest 3.16 m), no plate corner + 1 m off `pavedAt` on
  either tier, no corner + 2 m off the vector test, no foot inside an envelope or bridge area, and no mast inside the
  table 4.9.5 clearance of a taxiway / taxilane of the code letter its own rule uses (0 of 58, my check against the taxi
  graph). Masts close to envelope lines are F4.
- **N5 is fixed**: phone (iPhone 15, low tier) and laptop (high) both place 58 masts, hash `edc568b`, identical lists; both
  legends read "Apron floodlight masts: 58".
- **V3, V5, V6, V7, N6 are fixed** (numbers in the table). **L3 is fixed on the laptop** (terrace 20.5 % → 5.5 %).

What does not hold up, or is new:
1. **L9 is partly fixed, not fixed.** The haze is weaker and the detail contrast doubled at y 60-120, but the round-2 metric
   itself rose only at y = 120 (5.6 → 6.9), fell at y = 180 (12.7 → 9.1) and did not move at y = 240 / 300; the far plain is clearer but still low-contrast, and the top
   ~45 px of the frame are a flat haze band in both rounds (ground beyond the 20 km land-cover crop).
2. **F1 (medium, new): the app's Tower view now has a 30 m mast as its largest foreground object** on both devices: mast
   "115" 54 m from the eye, head 65 px in the lower middle of the laptop frame, 41 px left of centre on the phone. On the
   phone this is not an L3 effect (the portrait framing did not change); it is the new mast placement.
3. **F2 (low): the fill under the contact bridges is lit at 2.5 × the open apron** (light factor 1.578 against the 0.636
   floor) since `standFillLevel` 1.25 meets the N6 concrete; sRGB 1.75 × (L 135 against 77 at the pier tip). The
   integrator's "1.5-1.8 ×" is the sRGB ratio, not the light ratio.
4. **F3-F7 (low)**: masts just outside the near field still frame the subject at 18 contact stands (274: pole between the
   rotunda and the nose, head 71 px); a gap-fill mast with its plate 0.4 m from a painted envelope line (289); the aerodrome
   is a pure-black, hard-edged hole in the newly lit night surroundings; `stand_head_fill` overlaps the airside fill's apron
   part by 6,918 m² (data only, confirmed); about 1.4 s more start-up on the main thread.

## Status of every open finding of review_visual_fix2.md

| # | Sev | Status | Owner | Evidence (render / probe) | What I saw / why |
|---|---|---|---|---|---|
| V1 | medium | **fixed** | markings | `view_night_stand_233`, `view_night_t2pier`, `out/review3/night/n_night_under233.png`, `n_night_t1west.png`, `n_night_t2_240.png`; probe `nodesBelow`, `light_walks`, `light_bridge`, `light_envelopes`; `review3_night.png` | Light map (58 masts, high tier; the same masts on low): 0 / 164 stop nodes below standLevel 1.108; 0 / 56 bridges below it anywhere along attach → rotunda → cab ±6 m (this includes the long fixed links of 224-228, 238-240 and 256, whose facade end is 57-72 m from the nearest contact node, beyond `standFillR` 60 m; at 240 the minimum, 1.000 × the level, sits on a painted bridge-area texel); bridge areas 0 / 56; check926 0.500. sRGB, review-2 camera under 233: fill (27, 23, 18) → (147, 132, 107), envelope (92, 80, 62) → (136, 121, 97), 12 m asphalt service band along the facade (63-70, 55-62, 46-51); named view: (31, 27, 22) → (153, 138, 113). T1 at 21:30: under the bridges (117-122, 102-106, 80-84) > stand row (103, 90, 70) > apron lane (84, 73, 57). Nit, not a failure: on a 2 m grid 77 / 164 envelopes and 32 / 261 equipment areas have rim samples at 0.89-0.95 × the level (4 m texels whose centre lies just outside the ring; the floor holds per texel as claimed; envelope means ≥ 0.998 × the level). The strength of the fill is F2. |
| V2 | medium | **fixed** (by the near-field definition; residual F3) | gates | probe `cams` (both tiers); `out/review3/day/d2_fly_238A.png`, `d_fly_264.png`, `d2_fly_270.png`, `d2_fly_228.png`, `d2_fly_259.png`; `review3_fly.png` | My own sampled test on the side the app takes: 0 / 164 near-field masts (head or pole > 10 m in the 16:9 frame at depth < 45 m, or pole < 25 m); round-2 metric (3 m head ≥ 60 px) 21 → 0; mine and `standCamNearList` agree at every stand; contact stands on side -1: none; 42 remote stands on side -1; 61 stands have a near-field mast only on the side not taken. Renders: 238A, 228, 259 no mast; 264 no mast (A320 parked); 270 one far pole by the 269 rotunda. The "Fly to stand" path (`SHA.qa.selectStand(n, true)`) returns `near: [[], ...]` on the side taken in every run. |
| V3 | low | **fixed** | buildings | `n_night_under233.png`, `view_night_t2pier`, `n_night_t2_240.png` | Pier roof (1, 2, 4) → (36, 32, 27) under 233; `view_night_t2pier` (4, 4, 5) → (37, 32, 27); T1 roofs (30-35, 26-28, 22). Dark grey, below the curtain walls, no longer holes. |
| V4 | low | **fixed** (residual F4) | gates | probe `mastSummary` (both tiers); `d_mast289_top.png` | Feet within 3.13 m of an equipment area 0 (nearest 3.16 m); in an envelope / bridge area 0; plate corners + 1 m off `pavedAt` 0 (high and low); + 2 m off `pavedVec` 0; centre off 0; table 4.9.5 lane clearance by the rule's own code letter: 0 / 58 violations (taxi-graph links). |
| V5 | low | **fixed** (new F5) | buildings + core `ground.js` (applied) | `out/review3/night/n_night_overview.png` vs `out/review2/night/rvn_night_overview.png`; `review3_night_surround.png` | Landside inside the extent (1, 1, 0) / (3, 2, 1) → (22, 17, 8) / (41, 31, 18); far ground (2, 1, 0) / (5, 3, 1) → (27, 19, 11) / (33, 24, 14); haze top (0, 0, 0) → (29, 22, 14); apron T2 (38, 30, 21) → (51, 43, 32). No ring at the extent edge that I could tell from the canal / cropland pattern. The aerodrome itself stays (0, 0, 0): F5. Legend and About carry the "inf" sentence. |
| V6 | low | **fixed** | markings | `view_rwy_36L`, `view_rwy_18R` vs round 2; `review3_confirmed.png` | My own mask (runway between the edge lines, rows 535-720, the parallels' columns 612-668 masked): yellow pixels 189 → **0** (36L), 198 → **0** (18R). In 4× crops the inner crossing's curves end at the runway edge; the outer pairs' take-off parallels are unchanged. |
| V7 | low | **fixed** | other (integration) | `view_laptop_live_t2`, `view_laptop_live_stand_233` | Day, "Live weather · 12:15 UTC+8", METAR 0400Z, runway line "north flow · arr 36R · dep 36L · tail-wind rule"; the instant is in `integration.md` and `CLAUDE.md`. |
| N1 | medium | **fixed** (via V2) | gates | as V2 | The near-field residual of N1 is gone; what remains in frame is middle-distance (F3). |
| N2 | medium | **fixed** (via V1) | markings | as V1 | No moat at the T2 north pier tip in either named night view or under 233. |
| N5 | low | **fixed** | gates | `phone_low_probe.json` vs `hi_night_probe.json`; `view_phone_t2_legend`, `view_laptop_live_t2` | 58 = 58, hash `edc568b` on both, identical position lists; legends "58" on both; placement 1,114 ms (low) / 1,136 ms (high). |
| M1 (a) | medium | **fixed** | markings | `n_night_east_apron.png` vs `rvn_night_east_apron.png`; probe | Stands no longer drop to the floor; pools still read with soft 20-30 m edges from 900 m (lit-area luminance p50 / p95 67 / 126 → 78 / 112: flatter, as the fixer says). |
| M1 (b, c) | medium | **deferred_ok** | other (Phase 5) | `view_night_hold_H1` (byte-identical to round 2), legend lighting line, About | Airfield lighting not modelled; labelled Phase 5. F5 makes the gap more visible from above. |
| L2 | low | **not_fixed** (not in this round) | buildings | `view_tower` | The T1 hall is still a rounded dome; photo 02 shows a flat-topped hall with a white fascia. |
| L3 | low | **fixed** (laptop; phone unchanged by design) | buildings | `view_towercab` vs round 2 (`band_contrast.py --terrace`: 20.5 % → 5.5 %); `view_phone_towercab` | The terrace is a sliver at the lower right. The new framing brings mast "115" into the lower middle: F1. |
| L9 | low | **partly** | buildings | `view_overview` vs round 2; `review3_overview_haze.png` | Round-2 metric (20-row bands centred on y, full width), y 60 / 120 / 180 / 240 / 300: 3.8 / 5.6 / 12.7 / 17.5 / 22.6 → 3.4 / 6.9 / 9.1 / 17.3 / 22.7, so only y = 120 rose. My detail contrast (high-pass std / mean): 0.010 / 0.023 / 0.040 / 0.122 / 0.099 → 0.023 / 0.042 / 0.051 / 0.129 / 0.101, so the 60-120 bands doubled. The fixer's explanation of the y = 180 drop (the old haze ramp across the extent edge inflated it) is plausible. Per 10-row strip the high-pass std is 1.5-1.9 × round 2 in rows 50-130 (y 60: 1.12 → 2.08; y 100: 2.25 → 3.87), so the far plain reads clearer; above y ≈ 45 (the top ~6 %, about 15 km and more from the camera) it is a featureless band in both rounds, because the land cover ends at the 20 km crop. Better, but the review's metric moved at one band of four and the CAVOK overview still ends in a haze wall. |
| N6 | low | **fixed** | buildings | `view_t2pier`; `out/review3/day/d_piertip_top.png`; `review3_night.png` | From 320 m straight down: no disc, a ~12 m dark service band along the pier faces, no grass or seam between the band, the apron part and the core apron. At night the band reads as a darker strip along the facade (63-70 sRGB), not a moat. |
| N7 | low | **not_fixed** (not in this round) | buildings | `view_overview` | Canals still read as dark lines; at night they are black (plausible for water). |

## New findings (ranked)

| # | Sev | Status | Owner | Render(s) | What is wrong | Concrete fix |
|---|---|---|---|---|---|---|
| F1 | **medium** | new (integrator's I6.2, confirmed and corrected) | gates | `view_towercab`, `view_phone_towercab`, `out/review3/day/d2_towercab.png`, `out/review3/probe/phone_low_phone_towercab.png`; probe `towerCam`; `review3_tower_mast.png` | **The Tower view (a top-level view button) has a 30 m mast as its largest foreground object.** Probe: mast "115" (T1 west face, rotunda line) 54.4 m from the eye; laptop (fov 46°, pitch -7°): head 65 px at (487, 447), the pole across the lower half of the frame; phone (fov 62.8°, pitch -11°): 54.7 m, head 41 px at (100, 347). The next mast in either frame is over 1.1 km away. Round 2's phone Tower view had no mast in frame at all, and its portrait framing did not change in this round, so this is the new placement, not L3; on the laptop L3's narrower field makes it larger. | `gate_system.js placeMasts`: add the app's Tower view cameras (eye = `anchors.tower.pos` + cab offset at `eyeY`, yaw `cabYaw`; the landscape framing (46°, pitch from `terraceHalf / terraceY`) and the portrait one (58-72°, -11°)) to the camera tests, with a near depth of about 70 m (head ≤ ~60 px) and the same subject-free rule as the stand cameras, or reject candidates inside the tower view wedge within 80 m of the eye. Re-place "115" (the T1 west face had 2 masts in round 2, 1 now). Add the tower camera to `jobs/gates.mjs fix3` and require 0. Tag inf. |
| F2 | low | new (the integrator's conflict 1, quantified) | markings | `view_night_t2pier`, `view_night_stand_233`, `n_night_under233.png`; probe `light233`, `lightStats`; `review3_night.png` | **The fill under the contact bridges is lit at 2.5 × the open apron.** `standFillLevel` 1.25 × the stand mean = factor 1.578 (1.425 × standLevel) against the other-apron floor 0.636; it was tuned on asphalt (albedo 0.085), and N6 made most of the band concrete (0.30). sRGB at the pier tip: L 135 against 77 on the open apron (1.75 ×); under 233 the fill (147, 132, 107) is brighter than the 233 envelope (136, 121, 97). Photos 13 / 19 do show this band brightest, so the sign is right; the size is a choice nobody made. The integrator's "1.5-1.8 ×" is the sRGB ratio. | `markings.js applyMastPools`: use `standFillLevel` only on the asphalt service band (`SHA_BUILDINGS3D.airside_fill.polys`) and `standFloor` (1.0) on apron-kind fill (`apron_polys`, `stand_head_fill`), or cap the fill at about 1.1 × the stand mean where the airfield map says apron. Record the split in `CAAC.apronFlood` (inf, photos 13 / 19) and re-measure L under 233 (fill within 1.1-1.3 × the envelope). |
| F3 | low | new (residual of V2) | gates | `out/review3/day/d_fly_274.png`, `d_fly_260.png`, `d_fly_115.png`, `d_fly_229.png`, `d_fly_224.png`; probe `cams.mid`; `review3_fly.png` | **Masts just outside the 45 m near field still frame the subject.** On the side taken, 78 stands (18 contact) have a mast head 40-71 px wide (4.2 m head) at 45-80 m; 9 are ≥ 60 px. Contact: 115, 229, 260, 274 (71 px, 45.4-45.8 m), 224 (68), 261 (63), 268 (61), 269 (58), then 256, 113, 266, 275, 110, 112, 102, 250, 114, 246 (41-52). In the renders: at 274 the pole stands between the 274 rotunda and the A320's nose, head at the top (subject clearance 1.09 × the 4° margin); at 260 it stands mid-frame right of the wing tip; at 115 right of the wing tip. Nothing is occluded, but at three stands the mast is the strongest vertical in the picture, which is what V2 was about. | `STAND_CAM`: either `nearDepth` 45 → 55 m for side +1 of contact stands, or a second band: a pole at depth < 60 m must keep 2 × `subjDeg` from the subject hull. Re-run `jobs/gates.mjs SET=fix3` and let the gap fill recover coverage. Tag inf. |
| F4 | low | new | gates | `out/review3/day/d_mast289_top.png`; probe `mastSummary.envWithin3`; `review3_tower_mast.png` | **A mast hugs a painted stand envelope.** The gap-fill mast "289" stands 1.18 m from the 290 envelope line, so its 1.6 m plate edge is about 0.4 m from the red line and its shadow crosses the envelope; 328 at 2.25 m (8.7 m straight ahead of 323's stop node), 268 at 2.96 m. `placeMasts` tests the inside of the painted ring and the aircraft footprint + table 4.13.5 margin, but has no clearance from the painted line, unlike the equipment areas (V4: plate + 2 m). | Add `MAST_ENV_CLEAR` 2 m: reject a candidate whose base plate is within 2 m of a painted envelope ring (foot ≥ 3.13 m), as for the equipment areas, in the main pass and the gap fill. Tag inf. |
| F5 | low | new (side effect of V5) | markings (`js/shaders/ground.js`; Phase 5 for the lights) | `out/review3/night/n_night_overview.png`, `crops/night_overview_sw.png`; `review3_night_surround.png` | **At night the aerodrome is a pure-black, hard-edged hole.** Inside the aerodrome mask the ground measures (0, 0, 0) (grass and runways), while the landside right at the mask edge is now (22-41, 17-31, 8-18) and the far ground (27-33). From the overview the field reads as a cut-out with straight polygon edges rather than dark ground, which is more striking now that V5 lit everything around it. | `ground.js`: give the aerodrome ground a faint sky-glow ambient at night (e.g. 0.05-0.1 × albedo × `uNight`, the `URBAN_NIGHT` tint), or feather the urban glow 150-300 m across the aerodrome boundary, so the field is dark but not black until the Phase 5 airfield lighting. Tag inf; the legend lighting line already says Phase 5. |
| F6 | low | new (integrator's I2 side effect 2, confirmed) | buildings | data only: `data/sha_buildings3d.json` | **`stand_head_fill` overlaps the airside fill's apron part.** Shapely on the data: stand-head fill 35,099 m², of which 6,918 m² lie inside `airside_fill.apron_polys`, 0 in the service band, 28,181 m² outside both (= the round-2 area). It now lists 37 rings / 98 stands (was 21 / 69). Both draw as apron, so nothing changes on screen, but the data, its stats, `CLAUDE.md` ("37 rings") and the integration log overstate the fill. | `tools/buildings/build_buildings3d.py` (~line 588): build `h2` from `fill['polys'] + fill['apron_polys']`; rebuild and expect 21 rings / 69 stands / 28,181 m²; update the `CLAUDE.md` count. |
| F7 | low | new (start-up cost, reported by the fixers) | gates (markings for the pool pass) | page logs: `gates masts ... ms 1136` (high), 1114 (low); `apron light pools ... ms 244` | **About 1.4 s more start-up on the main thread** (mast placement 1.1 s, was 0.4-0.5 s; pool pass 0.24 s, was 0.07-0.15 s, on llvmpipe). Placement is now deterministic and the same on every tier (hash `edc568b`), so it does not need to run on every page load. | Cache the placement: a node tool writes `data/sha_masts.json` (positions, faces, `stats.hash`) from the same `placeMasts` code, the page uses it when the hash of its inputs matches and falls back to the live pass otherwise; or run the pass in an idle callback after the first frame. |

## Claims refuted or corrected

- **Buildings "L9 fixed"**: partly. The review's own band std rose only at y = 120 (5.6 → 6.9); y = 180 fell (12.7 → 9.1) and
  y = 240 / 300 did not move. The detail-contrast gain (0.023 → 0.042 at y = 120) and the removed horizon step are real,
  but the far plain is still low-contrast and the top ~45 px are a flat haze band (land cover beyond 20 km).
- **Integrator "standFillLevel × N6: 1.5-1.8 ×"**: that is the sRGB ratio. In light it is 2.5 × the open-apron floor
  (1.578 / 0.636) (F2).
- **Integrator "the Tower view frames the 115 mast after L3"**: on the phone the framing did not change in this round; the
  mast is there because of the new placement (round 2's phone Tower view had none). The owner is gates, and it is a named
  view, so medium (F1).
- **Gates "no mast is in a 'Fly to stand' near field any more"**: true; I reproduced it with an independent test on both
  tiers. But "the masts in the middle distance" include heads of 60-71 px at 45-53 m in 9 frames, at 274 right next to the
  subject (F3).
- **Markings "30 nodes exactly at the stand level"**: I count 33 within 1 LSB (0.011). Immaterial.

Nothing else I measured contradicts the fixers or the integrator: V1 (nodes, bridges, sRGB under 233), V2 / V4 / N5 (my
probe, both tiers), V3, V5, V6 (my own mask), V7, N6 and L3 hold.

## Regressions checked (none found)

- **Day runway views**: the threshold-stripe band of all four `view_rwy_*` is pixel-identical to round 2 (0 px differ by
  more than 8 levels in rows 380-470); 4× crops: 6 + 6 (18L), 6 + 6 (36R), 8 + 8 (18R), 8 + 8 (36L).
- **Stand 233 nose wheel**: B738 parked, top view (`d_nose233_top.png`, the round-2 camera): yellow stop bar rows 356-364
  and nose tip row 208 in both rounds, i.e. the nose wheel on the bar and the tip ~4.8 m ahead (model nose gear 4.32 m).
- **No unpaved strips**: T2 north pier tip from 320 m straight down shows the service band, apron part and core apron with
  no grass or seam; `test_buildings3d.mjs` (stand heads, fixed-link points) passes; probe: no mast centre or plate off
  pavement.
- **Phone UI** (`view_phone_*`): "Snapshot · 20 Nov", "12:15 UTC+8", the legend's mast line "58, about one per 3 stands",
  the stand card "T2 APRON 2 / Stand 233" with "Fly to stand", the DEBUG line first; nothing clipped that was not clipped
  before.
- **Named stand views** 233, 113, 102, 404, `bridge_230`: no near-field mast; masts only in the middle distance (113: right
  of the wing tip, head at the top edge; 102: by the nose in the middle distance, as in round 2).
- **Console**: clean in the snapshot scene (0 / 0 / 0, `jobs/integration.mjs`); 0 errors and 0 page errors in all my runs.

## Evidence images (our renders, deviceScaleFactor 1, scaled)

| File | Shows |
|---|---|
| `review3_night.png` | V1 / N2 / V3 / F2: `view_night_stand_233` round 2 vs round 3; under 233 at 21:30 with the review-2 camera, round 2 vs round 3 (fill, envelope, service band, roof values); the pier tip of `view_night_t2pier`, round 2 vs round 3 |
| `review3_night_surround.png` | V5 / F5: night overview round 2 vs round 3 (landside, far ground, the black aerodrome); T2 middle and T1 at 21:30 (roofs, service band, light under the bridges) |
| `review3_fly.png` | V2 / F3: "Fly to stand" 238A, 264, 270, 228, 259 (round 2's offenders, now clear), and 224, 274, 260, 115 (masts at 45-48 m, heads 68-71 px) |
| `review3_tower_mast.png` | L3 / F1 / F4: `view_towercab` and `view_phone_towercab`, round 2 vs round 3 (terrace gone, mast "115" in frame); the gap-fill mast "289" beside the 290 envelope line |
| `review3_confirmed.png` | V6 / H1 / N5 / V7: the inner backtrack curves at 36L / 18R, round 2 vs round 3; stripe crops; the B738 nose at 233; the phone legend's 58; the pinned laptop UI |
| `review3_overview_haze.png` | L9: the top of `view_overview`, round 2 vs round 3, with the band and detail numbers |

Commands (from `sha3d/`; job, helpers and compositor in `out/review3/`, read-only):

```
SOFTGL=1 OUT=out/review3/probe PREFIX=hi_night T=2026-11-20T13:30:00Z PROBE=1 VIEWS='' node livetest.mjs out/review3/rv3.mjs
SOFTGL=1 DEVICE='iPhone 15' QUALITY=low OUT=out/review3/probe PREFIX=phone_low T=snapshot PROBE=1 VIEWS='towercab@phone_towercab' node livetest.mjs out/review3/rv3.mjs
SOFTGL=1 OUT=out/review3/day PREFIX=d T=snapshot VIEWS='park:233+115+229+260+274+224+264;look:-760.58,2.5,-138.65,77,84,32,40@nose233_top;fly:115;fly:229;fly:260;fly:274;fly:224;fly:264;look:-800,2.5,-150,0,85,320,50@piertip_top;masttop:289,70@mast289_top' node livetest.mjs out/review3/rv3.mjs
SOFTGL=1 OUT=out/review3/day PREFIX=d2 T=snapshot VIEWS='fly:238A;fly:270;fly:228;fly:259;towercab@towercab' node livetest.mjs out/review3/rv3.mjs
SOFTGL=1 OUT=out/review3/night PREFIX=n T=2026-11-20T13:30:00Z VIEWS='park:233+113;look:-786,2.5,-118,160,35,70@night_under233;look:600,2.5,-300,250,22,900@night_east_apron;overview@night_overview;look:430,2.5,60,270,30,350@night_t1west;look:-1000,2.5,-60,200,45,240@night_t2_240' node livetest.mjs out/review3/rv3.mjs
SOFTGL=1 OUT=out/review3/integ SCENES=snapshot node livetest.mjs jobs/integration.mjs
python3 -I out/review3/tools/px.py <images> -- x0,y0,x1,y1:label ...      # median sRGB of rectangles
python3 -I out/review3/tools/bands.py <images>                          # band std (round-2 metric) + detail contrast
python3 -I out/review3/compose.py                                       # the review3_*.png composites
```

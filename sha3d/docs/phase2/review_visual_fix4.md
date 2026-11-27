# Phase 2 fix round 4: adversarial visual review

Date: 2026-11-27. Report only: nothing in `js/`, `data/`, `tools/` or `jobs/` was changed, nothing committed, `sfo3d/`,
`pc12/`, `hwd3d/` untouched. I tried to refute the fixer's F1-F7 claims (`review_visual_fix3.md`) and the regression claims
with my own probe and renders.

**How I measured** (all in `out/review4/`, gitignored; SOFTGL llvmpipe, deviceScaleFactor 1; I looked at every render):
- `rv4.mjs`, a read-only probe (extends `out/review3/rv3.mjs`). It takes the app's real cameras (`SHA.rig.camera()` after
  `SHA.qa.view('tower')` and after `SHA.qa.selectStand(n, true)` for all 164 stands, animation finished) and projects every
  mast with my own geometry: a 4.2 × 2.7 × 2 m head box and the pole every 0.5 m. My near-field test is my own (55 m in a
  16:9 frame, pole within 25 m); it does not use `standCamNear` or `towerViewCams`. It also measures each foot and each
  rotated plate corner against the painted envelope lines, the equipment areas and the pavement, and reads the light map.
  For the night views (F2) it projects light-map sample classes into the frame; `occl.py` keeps only ground samples whose line
  of sight is not blocked by the T1 / T2 parts, the jet bridges or the parked aircraft.
- Runs: laptop **1440 × 900**, high tier, 21:30 (`night/`); laptop 1440 × 900, snapshot (`day/`); **iPhone 15** portrait, low
  tier (`phone/`); Full-HD browser window 1920 × 970 and iPhone 15 landscape 734 × 343 (`wide/`); interleaved start-up loads
  (`f7/`); `out/phase3/fix4_verify1/f6_shapely.py` and two scratch rebuilds of `sha_buildings3d`.
- Console: 0 errors, 0 warnings, 0 page errors in all six of my browser runs.

## Status of F1-F7

| # | Claim | My status | Evidence |
|---|---|---|---|
| F1 | pass | **partly** | At 1440 × 900 and at iPhone 15 portrait, no mast within 300 m is in the Tower view. The nearest head in frame is 1.22 km (4 px) on the laptop and 1.34 km (2 px) on the phone. The fixer's 90 m depth was not needed for this: no mast is within 300 m in either frame. But `towerViewCams` tests only a 16:9 landscape frame, while `app.js:190` keeps the vertical field at 46° for any landscape aspect. On a Full-HD browser window (1920 × 970, aspect 1.98) the horizontal field is 80°, and mast **"112"** (139 m, 38.5° off axis) is in frame with a **45 px head** at the right edge. On iPhone 15 landscape (2.14) it is 16 px. This fails the "no head ≥ 20 px within 300 m" test (**N1**). |
| F2 | partly | **fixed** (the fixer's luminance reading is too low) | Light map at 21:30: fill under 233 (apron kind, flag 2, band 0, within 14 m of the walkway) mean **1.407** against the 233 envelope 1.137, so **1.24 ×**. The asphalt band is 1.598 (1.41 ×). Rendered luma, counting only unoccluded samples within 70 m: **1.14 ×** with the review's camera and **1.12 ×** with the named stand-233 camera (n = 67 visible fill samples). Linear luminance is 1.27-1.33 ×. Both readings are inside 1.1-1.3. If occluded samples are kept, the same frames give 0.71-1.06, which explains the fixer's 0.99 / 1.07. The pier tip from 250 m (`t2pier`) reads 1.07 × luma. Caveat: most of the 233 envelope lies under the B738, so the reference is the painted stand texels within 70 m (232 / 234 envelopes, equipment areas). |
| F3 | pass | **partly** | Side taken, my test: near field (55 m) **0 / 164**; heads ≥ 60 px at 720 rows **0** (was 9). Heads ≥ 40 px: **71 stands, 14 contact**, against 78 / 18 with the same metric in round 3 (the fixer reports 66 / 13). The largest heads are 59 px (285, remote) and **56 px at contact stand 259** (the fixer says 54). The seven F3 stands: 274, 229 and 224 are clear; 260 and 115 have a pole 96-114 m away behind the aircraft (35-42 px at 900 rows); 261 has a pole at the right edge (76 m, 53 px at 900); **268 has a gap-fill mast left of the nose, the strongest vertical in the frame (69 m, 59 px at 900)**. The same picture is new at **259** (gap-fill mast at 58 m, 67 px at 900) and remains at 256 and 113 (63 and 62 px at 900). At the brief's laptop size, 1440 × 900, every pixel figure is 1.25 × the 720-row one: 23 stands have a head ≥ 60 px. See **N2**. |
| F4 | pass | **fixed** | 0 feet within 3.13 m of an envelope line; the nearest is "112" at **3.35 m** (worst rotated plate corner 2.30 m), then "115" at 3.68 m. Seen from straight above, the 112 plate sits clear of the red line. |
| F5 | pass | **fixed** | Night overview: aerodrome grass (6-22, 4-17, 1-11), runways (16, 11, 7), taxiways readable, no hard black polygon. The only (0, 0, 0) patch left is the SW pond, which is water and black by day too. In `view_night_hold_H1` the ground went from (0-4) to taxiway (44-47, 35-38, 26-28). That is dusk-like at the 0.10 upper end of the requested range (nit). |
| F6 | pass | **fixed** | Shapely: **21 rings / 69 stands / 28,182 m²**, overlap with the band and with `apron_polys` **0 / 0 m²** (HEAD: 37 / 98 / 35,099, 6,918 m² overlap). Two scratch rebuilds are byte-identical. They differ from the committed file only in the provenance key, which holds the build path. `test_buildings3d.mjs`: all passed. |
| F7 | pass | **fixed** | Page source `cache`, inputs `904af9ec`, hash `84264519`. Placement takes 33-43 ms. Interleaved loads give ready in 4.4 / 5.9 / 6.8 s with the stored list and 7.5 / 7.7 / 8.0 s with `?masts=live` (1.8-1.9 s placement). The stored list is identical to the live list. Note: a stale file now costs 1.8-1.9 s, more than HEAD's 1.1 s (**N4**). |

Regressions (fix-3 requirements), all hold:
- **V1**: 0 of 164 stop nodes are below the stand level 1.1373; 55 sit exactly at it. `check926` is 0.500 on both tiers.
- **V2**: 0 near-field masts on the side taken (my test, 55 m and 45 m); no contact stand flies from side -1; the nearest pole
  is 25.6 m from a camera (227).
- **V4**: equipment areas at least 3.17 m away; 0 plate corners + 1 m off `pavedAt` (high and low tiers); 0 corners + 2 m off
  `pavedVec`.
- **N5**: phone (low) and laptop (high) both have 58 masts, hash `84264519`, identical lists, source `cache`.
- Named views: I diffed all 25 against HEAD and looked at every changed one. They match the fixer's list. What is worse: the
  231 gap-fill pole beside the B77W in `view_bridge_230` and in the day `view_t2pier`, where it cuts across the 230 B77W
  (disclosed by the fixer). `view_night_t2pier` gains that mast's lamp glare next to the B77W. `view_tower` (the outside orbit
  view) now has the re-placed "115" in its foreground, which is acceptable for an outside view.

## New findings (ranked)

| # | Sev | Owner | What | Fix |
|---|---|---|---|---|
| N1 | **medium** | gates (+ core `app.js`) | **The Tower view is clear only up to an aspect of about 1.88:1.** `TOWER_CAM.land.aspect` is 16 / 9 (`gate_system.js:441`), while `app.js:190` keeps a 46° vertical field on every landscape canvas. The most common desktop browser viewports are wider than that (1920 × ~970, 1366 × ~650, 1536 × ~740: 1.98-2.1). On them mast "112" stands in the Tower view at 139 m with a 45 px head (`review4_tower_wide.png`). `jobs/gates.mjs` checks only the job viewport and 393 × 659 (`:214`). | Test the placement with the widest landscape frame the app can show, e.g. `tanX = tanY × 2.4` in `towerViewCams`. Or cap the horizontal field in `app.js` (above 16:9, lower the vertical field so the horizontal stays at about 74°). Then re-run `SET=masts`, and add 1920 × 970 and iPhone 15 landscape to the fix-3 Tower check. inf. |
| N2 | low | gates | **The gap fill puts masts just beyond the 55 m near field of their own stand camera.** It takes the nearest legal grid point (`gate_system.js:2019`). New or moved gap-fill masts: "259" at 58 m in 259's own Fly view (56 px at 720 rows), "268" at 69 m beside 268's nose, "263" in 261's view, and "231" beside the B77W in `view_bridge_230` / `view_t2pier`. This is F3's pattern again, now at 58-69 m instead of 45-48 m. | Order the gap-fill candidates by the largest head they produce in any contact stand's side +1 camera, ascending (prefer positions behind the stand rows), or require ≤ 40 px at 720 rows in the stand's own camera when another candidate allows it. Re-run `SET=masts`. inf. |
| N3 | low | gates / jobs | **Every head-size threshold is defined at 720 rows.** At the brief's laptop 1440 × 900, heads are 1.25 × larger: 23 stands have a head ≥ 60 px (the F3 report says 0). | State the viewport with every pixel figure, or express the rule as an angle (for example a 4.2 m head ≤ 4.7°), and check it at 900 rows too. |
| N4 | low | gates | **A stale `sha_masts.json` is now slower than HEAD.** The live pass of the new rules takes 1.8-1.9 s (HEAD 1.1 s), and fix3 reports FAILED until `SET=masts` is re-run. P3-E is about to edit `gates.js` / `gate_system.js`. | Have P3-E re-run `SET=masts` + `SET='fix3;fix3low' CHECK_ONLY=1` as its last step, as the fixer asked. Consider logging a warning in dev builds when the inputs hash misses. |
| nit | - | markings | The F5 sky glow is at the 0.10 upper end: in `view_night_hold_H1` the unlit taxiway reads at about one third of the flood-lit open apron (linear), which looks like dusk. | 0.05-0.07 × albedo if the owner prefers darker night ground. |

## Claims refuted or corrected

- **F1 "pass"**: true at 16:9, 16:10 and phone portrait. **Refuted for wider landscape viewports**, the default Full-HD
  desktop browser window included (N1).
- **F3 "pass" / "largest now 54 px at 259"**: the 55 m rule holds, but gap-fill masts now frame 259 and 268 just outside it
  (N2). With my head box the largest contact head is 56 px at 720 rows (67 px at 900).
- **F2 "luminance reading not met (0.99 / 1.07)"**: **corrected upward**. Without the samples hidden behind bridges and roofs,
  the rendered fill / envelope ratio is 1.12-1.14 × near 233, so the target is met in both readings.
- **F1 "nearest head in view 1.3-1.4 km"**: 1.22 km at 1440 × 900 (mast "263", 4 px). Immaterial.

Everything else I measured agrees with the fixer: F4, F5, F6, F7, V1, V2, V4 and N5, the 58-mast list on both tiers, and the
named-view diffs.

## Evidence images

| File | Shows |
|---|---|
| `review4_tower_wide.png` | F1 / N1: the Tower view at 1440 × 900 and iPhone 15 portrait (clear), at 1920 × 970 (mast "112", 45 px) and iPhone 15 landscape (16 px) |
| `review4_fly.png` | F3 / N2: Fly to stand 268, 259, 256, 113 (masts at 58-69 m beside the subject) and 274, 229 (clear); `view_bridge_230` / `view_t2pier`, HEAD vs fix 4 |
| `review4_night.png` | F2 / F5: under 233 with the visible sample classes and both ratios; the stand-233 camera; the night overview, round 3 vs round 4 |

Commands (from `sha3d/`):
```
SOFTGL=1 W=1440 H=900 OUT=out/review4/night PREFIX=hn T=2026-11-20T13:30:00Z PROBE=1 VIEWS='park:233;look:-786,2.5,-118,160,35,70@night_under233!;park:229+230+231+234;stand:233,70,1,24@night_stand_233!;t2pier@night_t2pier!;overview@night_overview' node livetest.mjs out/review4/rv4.mjs
SOFTGL=1 W=1440 H=900 OUT=out/review4/day PREFIX=d T=snapshot VIEWS='towercab@towercab;park:274+260+115+229+224+261+268+256+259+113+230+231;fly:274;fly:260;fly:115;fly:229;fly:224;fly:261;fly:268;fly:256;fly:259;fly:113;masttop:112,70@mast112_top;look:-860,2.5,-180,60,22,140@bridge_230' node livetest.mjs out/review4/rv4.mjs
SOFTGL=1 DEVICE='iPhone 15' QUALITY=low OUT=out/review4/phone PREFIX=pl T=snapshot PROBE=1 VIEWS='towercab@towercab' node livetest.mjs out/review4/rv4.mjs
SOFTGL=1 W=1920 H=970 OUT=out/review4/wide PREFIX=fhd T=snapshot PROBE=1 VIEWS='towercab@towercab' node livetest.mjs out/review4/rv4.mjs
SOFTGL=1 DEVICE='iPhone 15 landscape' QUALITY=low OUT=out/review4/wide PREFIX=pland T=snapshot PROBE=1 VIEWS='towercab@towercab' node livetest.mjs out/review4/rv4.mjs
SOFTGL=1 OUT=out/review4/f7 N=3 node livetest.mjs out/review4/rv4_f7.mjs
python3 -I out/review4/occl.py out/review4/night/hn_night_under233.png 233:B738      # F2 luminance, occlusion-aware
python3 -I out/phase3/fix4_verify1/f6_shapely.py data/sha_buildings3d.json           # F6
python3 -I out/review4/compose.py                                                    # review4_*.png
```

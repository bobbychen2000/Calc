# Phase 2 fix round 4: adversarial visual review (with verification round 2)

Date: 2026-11-27. Report only: nothing in `js/`, `data/`, `tools/` or `jobs/` was changed, nothing committed, `sfo3d/`,
`pc12/`, `hwd3d/` untouched. Round 1 of this review (same file, earlier the same day) found N1 (Tower view not clear on
wide windows, medium), N2 (gap fill takes the nearest legal spot), N3 (pixel limits only at 720 rows), N4 (stale cache cost)
and NAMED-231. The fixer answered them in "Verification fixes, round 1" (`gates.md`, `markings.md`, `buildings.md`). This
is verification round 2: I tried to refute those answers and re-checked F1-F7 and the fix-3 requirements.

**How I measured** (all gitignored; SOFTGL llvmpipe, deviceScaleFactor 1; I looked at every render):
- `out/phase3/fix4_verify2/rv5.mjs`: a read-only page probe, a copy of round 1's `out/review4/rv4.mjs` with more output. It
  takes the app's own cameras (`SHA.rig.camera()` after `SHA.qa.view('tower')` and after `SHA.qa.selectStand(n, true)` for all
  164 stands, animation finished) and projects every mast with my own geometry: a 4.2 × 2.7 × 2 m head box and the pole. It
  does not use `standCamNear`, `standCamHead` or `towerViewCams`. New in round 2: a Tower view aspect sweep (same camera, frames
  1.0-3.9 : 1), the fp-mode zoom-out limit (75° vertical), the mast placement kind of each head, the 40-71 px band, and the
  nearest mast to every uncovered stand.
- Runs: laptop 1440 × 900 high tier, snapshot, with the Fly views of 274, 260, 115, 229, 224, 261, 268, 256, 259, 113 and 102
  (`out/review4/r2/day/`). The same at night, 21:30 UTC+8 (`night/`). iPhone 15 portrait on the low tier (`phone/`). Real
  1920 × 970 and 1600 × 450 (32:9) Tower views (`wide/`). Start-up loads: stored, `?masts=live`, a forged stale file and a 404,
  plus dry passes (`f7/`, `out/phase3/fix4_verify2/f7s.mjs`). `jobs/gates.mjs SET='fix3;fix3low' CHECK_ONLY=1`.
  `jobs/integration.mjs` with the mock relay. Shapely on `stand_head_fill`. The no-browser tests.
- Console: 0 errors, 0 warnings, 0 page errors in every run except the two deliberate F7 faults (see F7).

## Status of F1-F7

| # | Fixer | Round 1 | **Round 2 (mine)** | Evidence |
|---|---|---|---|---|
| F1 | partly | partly (N1) | **partly** (as the fixer says) | No head within 300 m is in the frame, measured on the app's real camera at 1440 × 900, at 1920 × 970 (real, 80.1° across) and on iPhone 15 portrait on the low tier. The nearest head is 1.22 km / 1.34 km away (4 / 2 px). With the same camera, the aspect sweep is clear from 1.0 to 3.0 : 1, and also when zoomed out to the 75° limit. `jobs/gates.mjs` fix3 (my run): 0 / 0 at all five viewports on both tiers. **Not met:** (a) the T1 west face cover (113, 114, 115 and 120: the nearest mast is 128, 153, 194 and 247 m away; R2-3); (b) super-wide windows of 3.44 : 1 and wider (R2-1). |
| F2 | pass | fixed | **fixed** | Light map: apron-kind fill under 233 has a mean factor of 1.386 against the 233 envelope's 1.098, so **1.26 ×**. The asphalt band is 1.588 (1.45 ×, by design). Rendered luma, counting unoccluded samples only (`out/review4/occl.py`): **1.28 ×** fill / envelope with the review camera under 233; **1.18 ×** fill / 233 envelope and 1.14 × fill / all envelopes with the named stand-233 camera. The pier tip (`t2pier`) reads 1.08-1.13 ×. The fixer's 1.14-1.28 × is right. |
| F3 | pass | partly (N2) | **partly** | Gap fill: 268 and 113 are clear. 259's mast went from 60 m / 67 px to 90 m / 45 px, and 260's from 96 m to 130 m (31 px). With round 1's metric (720 rows, head box, 16:9) heads ≥ 40 px went 71 (14 contact) → **62 (7 contact)**, heads ≥ 60 px went 9 → **0**, and the 900-row equivalent went 23 → 17. Those are exactly the fixer's numbers. But **main-pass masts still frame the subject** at contact stand 256 (65 m, 63 px at 900 rows, the strongest vertical beside the aircraft), at 102, 110, 246 and 272 (72-81 m) and at 13 remote stands (59-68 m). In the real 1440 × 900 frame, 14 stands have a head ≥ 60 px. The gap fill also still takes the candidate at the edge of its own limit (R2-2). |
| F4 | pass | fixed | **fixed** | 0 feet within 3.13 m of an envelope line. The nearest is "112" at 3.51 m to the 111 line (worst plate corner 2.69 m). Equipment areas: nearest 3.17 m. 0 plate corners + 1 m off `pavedAt` on both tiers; 0 corners + 2 m off `pavedVec`. |
| F5 | pass | fixed | **fixed** | Night overview: 0.15 % of pixels differ by more than 8 levels from round 1. Aerodrome grass is about (20, 15, 10), with soft edges and no black polygon. The dusk-like H1 taxiway (k 0.10) stays a nit for the owner. |
| F6 | pass | fixed | **fixed** | Shapely: 21 rings, 69 stands, 28,182 m². Overlap with the band, with `apron_polys` and with itself: 0 / 0 / 0 m². No invalid rings. `test_buildings3d.mjs`: all checks passed. `sha_buildings3d.json` is unchanged since round 1. |
| F7 | pass | fixed (N4) | **fixed** | Stored file: source `cache`, inputs `db34b7b8`, hash `1b7bccfe`, placement 35-37 ms, ready in 4.8 / 6.5 s. `?masts=live`: 1.95-1.97 s placement, ready in 8.7 / 8.3 s. The two give the same list (my list hash and `mastsLive` equality). A forged stale file gives source `live (cache stale: inputs 0badf00d)` and **one console warning** with the rebuild command. A 404 on the file gives a console error. Either way the clean-console jobs fail. |

Fix-3 requirements (regression), all hold, on both tiers where tiers matter:
- **V1**: 0 / 164 stop nodes below standLevel 1.098 (min / p10 / median 1.000 / 1.000 / 1.125 × the level). `check926` is 0.500.
- **V2**: near field (55 m) 0 / 164 on the side taken; no contact stand flies from side -1. The nearest pole is 25.6 m from a camera (227, 326).
- **V4**: see F4. **N5**: iPhone 15 on low and laptop on high give the identical 57-mast list, hash `1b7bccfe`, source `cache`.
- `jobs/gates.mjs SET='fix3;fix3low' CHECK_ONLY=1` (my run): "fix3 requirements: met" on both tiers, tiers SAME, console clean.
  `jobs/integration.mjs` (snapshot, park, live with the mock relay): all scenes clean. `test_buildings3d`, `test_geo_js` and
  `node --check` pass.
- Named views: I diffed all 25 against the fixer's pre-round state (`out/fix4/v1/before_views`). The changed set equals the
  fixer's list: `view_stand_113` 0.94 % (masts "112" and "115" gone, cleaner), `view_night_t2pier` 1.01 %, `view_tower` 0.40 %
  (no mast in front of the T1 west face), `view_towercab` 0.24 % (mast shadow gone), `view_phone_t2_legend` 2.2 % (legend "58" →
  "57"), the rest ≤ 0.15 %. Nothing is worse. Still there from earlier rounds: the "231" pole across the 230 B77W
  (`view_bridge_230`, `view_t2pier`; NAMED-231) and the "102" rotunda-line mast beside the 102 bridge in `view_stand_102`.

## Round-1 findings re-checked

| Round 1 | Status | Note |
|---|---|---|
| N1 / F1-wide-aspect (medium) | **fixed for 1.0-3.4 : 1** | 1920 × 970: `f1fail` [], nearest head 1.22 km (was "112" at 139 m, 45 px). Beyond 3.44 : 1 see R2-1. |
| N2 / F3 gap fill nearest-first | **mostly fixed** | The examples are gone or moved back. The rule still picks the candidate just inside the limit (R2-2). |
| N3 pixel limits at 720 rows | **fixed** | The limits are now angles (`MAST_GAP_HEAD` 3°, `TOWER_CAM.headDeg` 1°), and the job prints a 1440 × 900 line. |
| N4 stale-cache cost | **fixed** | Warning on a stale file, error on a missing one (above). |
| NAMED-231 (low) | **open** (the fixer agrees) | "231" gap-fill mast at 69 m, **59 px at 900 rows** in the `view_bridge_230` camera, its pole crossing the 230 B77W wing. In app cameras it is ≤ 32 px (230 / 231 Fly, 101-102 m). |

## New findings (ranked)

| # | Sev | Owner | What | Fix |
|---|---|---|---|---|
| R2-1 | low | gates (+ lead for `app.js`) | **The Tower view is clear up to about 3.4 : 1, not "at every aspect the app shows".** `TOWER_CAM.land.aspect` 2.4 is justified as "21:9 monitors 2.33-2.39". That is the screen; a browser window on a 2560 × 1080 screen is about 2560 × 950 = 2.7 : 1. In practice 2.4-3.4 happens to be empty. At 32:9 (3.56 : 1, 113° across) mast **"112" (222 m, 56.6° off the axis)** enters at the right edge with a 2.0° head: 18 px in my 1600 × 450 render, **43 px at 3840 × 1080** and 58 px at 5120 × 1440. "335" (346 m) and "323" (432 m) come in beside it (`review4_tower_wide.png`, bottom). | Either cap the horizontal field in `app.js view('tower')` (lower the vertical field when aspect > 2.4), or raise `TOWER_CAM.land.aspect` to 4 and re-run `SET=masts` then fix3, checking what "112" costs. At the least, state "up to 3.4 : 1" in `CLAUDE.md` / `gates.md` and add a 32:9 viewport to the job. inf. |
| R2-2 | low | gates | **F3 residual: the masts beside the subject are now main-pass masts plus gap-fill masts at the limit.** (a) Rotunda-line masts of the main pass at contact stands: 256 (62-65 m, 52 px at 720 / 63-65 px at 900), 110 (72 m, 45 / 56), 102 (74-77 m, 44 / 53-55), 272 (81 m, 40), 246 (79 m, 41 / 51). Of the remote stands, 285, 286, 281, 326, 301 and 305 have masts at 55-64 m (50-59 px at 720 rows; at 285 and 286 the head is only at the edge of a 16:9 frame, outside the real 16:10 one). (b) "Nearest first among the candidates under `MAST_GAP_HEAD`" puts gap-fill masts just inside the 3° limit: "250" at 79 m (41 px) in 250's own Fly view and "262" at 82-84 m (40 / 48 px) beside 261's tail. This is round 1's "nearest legal spot" pattern, moved from 55 m out to about 84 m. Contact stands with a ≥ 40 px head at 720 rows: 102, 110, 246, 250, 256, 261, 272. | Main pass, contact stands only: apply `MAST_GAP_SUBJ` (the 2 × subject-margin penalty) to the rotunda-line candidates of the stand's own side +1 camera, or try the next rotunda-line slot when the head is > 3°. The fixer found the full main-pass rank cost coverage (311), so limit it to contact stands. Gap fill: keep a margin (rank by head size also under the limit, nearest as the tie-break, or a limit of 0.8 × tan 3°). Re-run `SET=masts` + fix3. inf. |
| R2-3 | low (owner decision) | gates / owner | **The cost of the clear Tower view is confirmed, and it buys only the default framing.** A dry pass without the Tower rule (`mastsLive({tower: false})`) gives 58 masts, with "115" at 99 m (-20.7°) and "112" at 162 m (29.8°) from the eye. Both are in the Tower frame, as the fixer says. With the rule, 113 / 114 / 115 / 120 are 128 / 153 / 194 / 247 m from the nearest mast. They are lit to the stand level by the floors; at night the T1 west face apron reads lit with no lamp near it (`review4_night.png`, bottom). The Tower view is a free-look camera (`controls.js:81`: drag yaw / pitch, wheel field 6-75°): "110" (143 m, 100° off the axis) and "112" (222 m, 57°) are one drag away. | Owner choice between (1) as now; (2) the lead's `app.js` horizontal cap with `TOWER_CAM` back to 16:9 / 90 m, which brings the T1 west face masts back at 99-162 m in the frame; (3) no pole for 113-120: facade- or roof-edge flood units on the T1 west face, inf, and the light map already has the floors. |
| nit | - | gates docs | `CLAUDE.md` (status line and Conventions) says 113-121 have no mast within 120 m "because of it" (the Tower view). 121, 126 and 310 are uncovered without the Tower rule too (my dry pass). `gates.md` has it right ("113, 114, 115 and 120, and, as before, 121, 126 and 310"). | Reword `CLAUDE.md`. |
| nit | - | markings | F5: the H1 taxiway at night still reads like dusk (k 0.10). | `AERO_NIGHT.k` 0.05-0.07 if the owner wants it darker (unchanged advice). |

## Claims refuted or corrected

- **"The Tower view is clear at every aspect the app shows"** (`CLAUDE.md` status line, `gates.md`, the summary): refuted from
  about 3.44 : 1 (R2-1). It is true for every viewport the job and I tested from 0.6 to 3.0 : 1.
- **F3 "pass"**: **partly**. The gap-fill part and all the fixer's counts reproduce exactly (job: 56 / 4 contact, 5 at
  1440 × 900; my probe: 62 / 7, 17). The 5 against 14 heads ≥ 60 px at 1440 × 900 is a question of definition: the job measures
  the head centre, I measure the nearest face of the head box in the real frame. But masts still frame the subject at 45-80 m
  (256, 102, 110, 246; R2-2).
- Confirmed: F1 "partly" (with its stated cost), F2, F4, F5, F6, F7, NAMED-231 "fail", the stored list equal to the live
  pass, the five-viewport Tower check, the light table (0 / 164, check926 0.500), the named-view changes, the console and
  no-browser tests.

## Evidence images

| File | Shows |
|---|---|
| `review4_tower_wide.png` | F1: 1920 × 970, round 1 ("112", 45 px) and round 2 (clear); laptop 1440 × 900 and iPhone 15 portrait (clear); 32:9 1600 × 450 with "112", "335" and "323" at the right edge (R2-1) |
| `review4_fly.png` | F3: Fly to stand 268, 259, 261 (round 1 / round 2); round 2 256 and 102 (main-pass masts beside the subject); `bridge_230` (NAMED-231) and 113 (clear) |
| `review4_night.png` | F2: under 233 and the named stand-233 camera with the luma ratios; T1 west face at night, round 3 against round 2 (no mast near 113-120, lit by the floors) |

Commands (from `sha3d/`; outputs in `out/review4/r2/`):
```
SOFTGL=1 W=1440 H=900 OUT=out/review4/r2/day PREFIX=d T=snapshot PROBE=1 VIEWS='towercab@towercab;park:274+260+115+229+224+261+268+256+259+113+230+231;fly:274;fly:260;fly:115;fly:229;fly:224;fly:261;fly:268;fly:256;fly:259;fly:113;fly:102;look:-860,2.5,-180,60,22,140@bridge_230' node livetest.mjs out/phase3/fix4_verify2/rv5.mjs
SOFTGL=1 W=1440 H=900 OUT=out/review4/r2/night PREFIX=hn T=2026-11-20T13:30:00Z VIEWS='park:233;look:-786,2.5,-118,160,35,70@night_under233!;park:229+230+231+234;stand:233,70,1,24@night_stand_233!;t2pier@night_t2pier!;look:430,2.5,60,270,30,350@night_t1west;overview@night_overview' node livetest.mjs out/phase3/fix4_verify2/rv5.mjs
SOFTGL=1 DEVICE='iPhone 15' QUALITY=low OUT=out/review4/r2/phone PREFIX=pl T=snapshot PROBE=1 VIEWS='towercab@towercab' node livetest.mjs out/phase3/fix4_verify2/rv5.mjs
SOFTGL=1 W=1920 H=970 OUT=out/review4/r2/wide PREFIX=fhd T=snapshot PROBE=1 VIEWS='towercab@towercab' node livetest.mjs out/phase3/fix4_verify2/rv5.mjs
SOFTGL=1 W=1600 H=450 OUT=out/review4/r2/wide PREFIX=uw T=snapshot PROBE=1 VIEWS='towercab@towercab' node livetest.mjs out/phase3/fix4_verify2/rv5.mjs
SOFTGL=1 OUT=out/review4/r2/f7 N=2 node livetest.mjs out/phase3/fix4_verify2/f7s.mjs          # F7 + dry passes (tower: false)
SOFTGL=1 SET='fix3;fix3low' CHECK_ONLY=1 OUT=out/review4/r2/gatesjob node livetest.mjs jobs/gates.mjs
SOFTGL=1 MOCK_RELAY=1 SCENES=snapshot,park,live OUT=out/review4/r2/integ node livetest.mjs jobs/integration.mjs
python3 -I out/review4/occl.py out/review4/r2/night/hn_night_stand_233.png 229:A333,230:B77W,231:A320,233:B738,234:A320   # F2
python3 -I out/phase3/fix4_verify1/f6_shapely.py data/sha_buildings3d.json                                               # F6
python3 -I out/phase3/fix4_verify2/viewdiff.py out/fix4/v1/before_views                                                  # named views
node out/phase3/fix4_verify2/wedge_cmp.mjs out/review4/r2/day/d_probe.json     # job metric (wedge, head centre) vs my probe
python3 -I out/phase3/fix4_verify2/compose2.py                                                                           # review4_*.png
```

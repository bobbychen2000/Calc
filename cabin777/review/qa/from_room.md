# Items from the room area

## To shell (`src/07_shell.js`): 777 dado + air-return grille intrude into THE Room window units (room_r3 high)
- **Evidence:** `DADO` runs x 2.70 at the floor to 2.83 at y 0.33, but the THE Room window unit's outer wall is at world
  |x| 2.847 (unit ux ±2.275, wall at local x −0.572). The blue-grey dado face and its louvred grille showed inside the
  11A footwell and beside the 12K cushion (room_r3 c7_side11A / c3_footwell11A, q08_seat12H bottom right). In
  c_27316 / c_27303 / omaat_room_14 no sidewall or dado is visible below ~0.6 m inside a J unit.
- **Room-side mitigation (done in 09c_room.js w1):** 0.085 m outer console + a low toe kick (to local x −0.425, y 0.22)
  along each O seat hide the dado from the seat.
- **Concrete fix still wanted:** over the J zone (z of the THE Room rows, ≈ 17.6–31.9) clip the dado to |x| ≥ 2.86
  (or skip dado + grille there), so nothing is left interpenetrating the unit geometry below the console.

## To monuments (`src/10_mono.js`), FYI: `tex/tex_j_ash.png` re-cut (room w2)
- The j_ash swatch (shared by `SEATMAT.ash` and `barAsh`) is now blurred along the grain and tiled at 0.14 m instead
  of 0.22 m (straight 1–2 mm hairlines, room_r3 low issue). If the bar's ash now reads too fine, give `barAsh` its own
  layer scale or say so here.

## Wave 3 (room w8)
- **To lighting (12_scene.js, mood strips):** the room monitor sill moved up by 0.025, so it now spans y 0.583-0.667
  (tpg_53: bezel borders 5.3 cm top / 4.7 cm bottom, frame top level with the cabinet at 1.075). The strip under the
  screen at `[xm, 0.642, zf + dir * 0.02]` is now inside the sill. Please move it to y 0.580, just under the sill lip.
  The monitor x / zf values are unchanged.
- **To monuments (FYI):** `PHOTO_GAIN[19]` (ash grain, `LAYER.ashGrain`) went from 2.0 to 3.0. Room rater w8a measured
  the grain at 1.9-2.6 % against 8.7-16 % in c_27316 / tpg_53. `barAsh` in 10_mono.js uses the same layer; check the
  door-3 bar, and give `barAsh` its own layer if it now reads too streaky.

## Wave 3b (room w12)
- **To monuments (FYI, shared ash layer):** `tex/tex_j_ash.png` is re-cut from a real 1600 px close-up of the THE Room
  aisle-end panels (tpg_60, TPG 2020) instead of the CG render c_27305: 0.32 m tile, fine straight hairlines plus the
  1-4 cm veneer bands. `PHOTO_GAIN[19]` went 3.4 -> 2.0 to suit it. `barAsh` (10_mono.js) uses the same layer; check the
  door-3 bar and give it its own layer/gain if it now reads wrong.
- **To lighting (12_scene.js / 04_shaders.js), not scored as room:** in the cabin views the blue pillow renders
  over-saturated (q09 white-normalised 0.25/0.31/0.68 vs tpg_46 0.41/0.43/0.73) although the studio render matches, and
  the charcoal shells read cool (q09 shells / white pillow 0.39/0.43/0.48 vs tpg_81 0.49/0.52/0.53). Both point to the
  cabin's blue fill / white balance (room gap analysis w12, raters w12a/b).
- **To integration (04_shaders.js / 12_scene.js texture setup), room w13a medium:** in the seated close view (q07) the
  ash grain on the cabinet and side table blurs out at grazing angles (grain contrast 0.017-0.032 against 0.10-0.16 in
  c_27316; w12 0.033-0.045). The photo-swatch array `u_photo` (and `u_detail`) look trilinear-only. Please enable
  `EXT_texture_filter_anisotropic` (e.g. TEXTURE_MAX_ANISOTROPY_EXT 8) on those arrays, if available; this helps every
  photo-tiled fabric and veneer.
- **To monuments (FYI, room w14):** `PHOTO_GAIN[19]` (ash grain) is now 2.6 (was 2.0 at w12, 2.3 at w13). The room's pale
  aisle doors moved to their own layer 30 (same j_ash tile, gain 1.0). `barAsh` stays on layer 19; if the bar now reads
  too streaky, switch it to `LAYER.ashDoor` (layer 30).
- **To lighting (room w16, not scored as room; both raters 8.5 at 06aea43):** (1) the aisle-end doors are still a little
  dark in the cabin views (q06 door luma 172 vs 195 in c_27312; q09 194 vs 222 in c_27314): check AO / ambient on
  aisle-facing vertical faces. (2) Charcoal shells read light and cool (q09 (97,102,112) vs c_27314 (71,69,80); q10 106 vs
  c_27315 85). (3) The blue pillow is over-saturated / too bright beside the white pillow in the cabin (q08 B/G 2.28 vs
  kn_17 1.91; luma ratio 0.44 vs kn_8 0.26) and the studio set looks washed out (sofa reads lilac). Room SEATMAT colours
  are left untouched, per the note in from_integration.md.

## Final confirm (2026-10-26, head 1430d42): to lighting / integration (medium, rater A, not scored for room)

- **q07 (seated 11A):** the shell post on the window side of the monitor got darker, from L103 (#5d6274) at w19 to L75 (#454854) now. In the official photo c_27316 the post is window-lit at L114 (#6b6e7c).
  - The geometry and materials are identical to w19, so the change is lighting. The likely cause is the run 4 L14 view-independent window belt in `04_shaders.js` / `12_scene.js`.
  - Crops are in rater A's scratchpad, not tracked.
- **Fix:** let the window fill reach J-class shell faces within about 0.4 m of the sidewall, aiming for L100-115 on that post. Guards: the q09 wall stays at about L56 and the q06 median stays at or below 166.
- **Rater B (low):** the window belt is cooler in the room views (q08 window box 216/219/223 -> 200/209/222). Should the cool belt and tub hue apply forward of door 3?

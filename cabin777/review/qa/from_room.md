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

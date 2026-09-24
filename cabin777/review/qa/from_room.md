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

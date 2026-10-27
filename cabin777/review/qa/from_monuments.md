# Items from the monuments worker

## To lighting + integration (`test/qa.js`, `src/05_layout.js`)

1. **Three QA cameras now sit inside monuments or walls** because the r2 monuments fix (`monoLayoutQA` in `10_mono.js`,
   following the official ANA seat map) moved the door-1, door-3 and PY monuments. Evidence: renders of the current
   head. `q01_door1` is inside the full-height door-1 centre closet (x -0.88..0.28, z 6.00..6.90). `q11_bar3` stands
   among the row-17 seats behind the bar, which now sits aft of the door-3 cross-aisle and faces forward. `q13_pyFront`
   is 0.2 m forward of the J/PY bulkhead and sees only its J face.
   Fix (cameras used by the monuments worker, checked in renders):
   - `q01_door1: walk(-1.35, 1.62, 5.7, 'Math.PI+0.12', -0.08)` (left aisle at door 1, looking aft into THE Suite)
   - `q11_bar3: walk(-1.35, 1.62, 31.6, 'Math.PI+0.35', -0.1)` (left aisle forward of door 3, looking aft at the bar)
   - `q13_pyFront: __rel('25C', 0.35, 1.75, -0.72, Math.PI+0.45, -0.3)` (inside the 0.92 m bulkhead legroom)
2. **Fold `monoLayoutQA` into `buildLayout`** when convenient. It wraps `buildLayout` at the end of `10_mono.js`
   because only that file was editable. It shifts the THE Room pairs, the PY rows, zones, windows and walk areas. Its guard
   skips the pass once the bar already stands aft of door 3, so moving the code into `05_layout.js` is safe.
3. **`q19_rearGalley` never reaches the rear galley** (monuments_w3a, low). From row 41/42 it frames the white back of the
   rear centre closet and lav. The door-5 galley work aisle runs from x -0.58 to 0.55 at z 59.3 to 61.05.
   Suggested camera: `q19_rearGalley: [\`__app.setView([0.0, 1.62, 59.2], Math.PI, -0.15)\`, [], 'rear galley at door 5']`
   (setView, not walk()).
4. **FYI:** the black lower half in the `44e8c06` shader snapshot is fixed at `241c41e` and later (checked in m05).

## Wave 3 (w7)

### To shell (`src/07_shell.js`): move the door viewing window FORWARD, `wz = c - 0.28` (one line, ~l.635)
- **Evidence:** lalf_133.jpeg / lalf_134.jpeg (Live and Let's Fly, ANA 777-300ER door 2L, real photos; liveandletsfly.com
  ana-777-300er-the-room-business-class-review) show the door from the galley passage. They look toward **L2**: the welcome
  galley is on the right, forward of the passage. It sits beside the door-2 lavs (omaat_room_32: the lav door is next to the
  galley), and the ANA map puts those lavs ahead of door 2. The 2L jump seat is on the left, on the aft closet. In those photos
  the viewing window is on the **forward** side (right of the grip). The arming window is upper **aft**, and the arc's
  arrowhead points down on the forward side by the window. Monument raters w7a and w7b both flagged this (w7b high).
- **Done on the monuments side (w7):** the lining furniture in 10_mono.js is mirrored (H = -1): the housing now runs from
  c-0.20 to c+0.48, the arming window is at c+0.41, and the arrowhead is at about c-0.15. **Until the window moves to c - 0.28,
  the housing covers it.** Please flip `wz` (and anything else keyed to the aft window, e.g. the reveal glow or door-carpet
  cut-outs) to `c - 0.28` on both sides. The "forward hinge" note there should read "window forward of the handle".

## Wave 3b (w9)

### To lighting (`src/04_shaders.js` / `src/12_scene.js`): recessed monument faces crushed to black
Both monument raters (w9a, w9b) and the gap analyst measured these. They are material-independent: changing the albedo
moves the rendered value by only a few levels.
- **Door-3 bar blind (m05, q11):** `MONMAT.blind` #3b3a3c renders #070708-#09090a, against #1c1921 in ANA's render.
  The upper unit is set back 0.5 m under the soffit, so the AO volume / crevice term (`amb *= mix(0.4, 1.0, ...)`) seems
  to take almost all of its ambient light.
- **Door-2 welcome galley recess (m03, m16):** the charcoal back wall (`welcomeChar` #5e5a52) renders #191816 against
  omaat_room_32 #3f3a2d-#343024. In the real galley a warm LED strip under the head lights the recess, so it reads lit.
  The recess side walls and ceiling are now light grey (w9), which should help the bounce.
- **Galley upper banks (m01, m09, m12, q19):** a bright-white fog band sits across the upper compartments at about
  1.9-2.1 m, with the lower half grey. sans_38 shows the upper row as an even mid grey. This is probably the ceiling cove
  light or the work light hitting faces that look down the aisle.
- **Suggested fix:** clamp the crevice term for faces in recessed monument bays, or give monument recesses a floor of
  about 0.6 on ambient.

## Wave 3c (w13-w15)

### To lighting (`src/04_shaders.js` / `src/12_scene.js`)
Noted by both raters in all three rounds; not scored against monuments.
- **Galley upper compartments still fogged (m01, m09, m12):** the white wash over the top half of the upper banks
  persists (see wave 3b above). It now also flattens the new aluminium insert frames (w15b: frames read close to the
  face tone).
- **q19 rear galley blows out:** the current q19 camera shows the galley ceiling panel and upper faces near white.
- **Door-1 dark wood streak aliasing (q01, m19):** `LAYER.fWood` on the large door-1 side walls smears into radial
  streaks at grazing angles (w14a, w15b). Probably mip / filtering of the fWood tile; worth a lower-frequency or
  pre-filtered sample at grazing angles.

## Final confirm (head 1430d42, 2026-10-26)

### To lighting (`src/04_shaders.js` / `src/12_scene.js`), medium, not scored against monuments
- **The L14 PY/Y seat-level cool light tints the door-4 and door-5 galley lower faces lavender (q19, m12, m09).**
  `seatC` (04_shaders.js:462) and the `u_bleed` bounce (04_shaders.js:561) are keyed only on `z > u_sLowZ` and height
  (below 1.2-1.5 m / 0.9-1.3 m), so they also reach the white galley faces at doors 4 and 5. Each face now splits
  at about 1.3 m: a lavender lower half and a neutral upper half.
- **Evidence:** my own measurement of the white pixels (L>140), lower band at 60-85 % of frame height against the
  upper band at 20-45 %, B-R:

  | view | 5e5e561 lower / upper | 1430d42 lower / upper |
  |---|---|---|
  | q19 | -3.5 / -2.7 | +7.3 / -3.5 |
  | m12 | -3.9 / -3.1 | +8.1 / -4.3 |
  | m09 | -2.5 / -7.6 | +5.2 / -7.8 |

  Rater A (`monuments_final_a.json`) finds 20.6 % / 24.3 % / 10.0 % of pixels shifted by more than 8 in B-R. The
  galley whites in the official photos are neutral. The cool shift in y_47305 / py_37301 that L14 matched is measured
  on seats, not on galleys.
- **Concrete fix:** leave monument surfaces out of both terms. Either (a) multiply both gates by
  `(1.0 - monoMask)`, where `monoMask` is a new flag in a spare channel of the per-vertex `a_mat` (only r = rough and
  g = metal are read at 04_shaders.js:227; I have not checked whether b/a are free), or (b) if no channel is free, zero both gates inside the monument z-bands from `MONO_LAYOUT` (door-4 galley about
  z 43.6-45.3, door-5 galley z > 58.0) with a 0.3 m smoothstep. Target: lower and upper galley faces within 3 B-R
  of each other, both at about -3, which is the 5e5e561 value.
- **Lighting final touch (71fdda1):** done (both terms x the window LUT seat-zone row sz, 0 in the galley / door zones): q19 white lower / upper B-R -4.5 / -3.6, m12 -4.8 / -6.2, m09 -2.6 / -6.6.

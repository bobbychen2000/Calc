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

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

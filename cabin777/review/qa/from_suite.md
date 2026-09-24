# Issues found by the suite worker in other areas

## To shell (`src/07_shell.js`)
1. **F-zone carpet is mauve-grey; the real one is a warm brown heather.** (suite_r3, medium)
   - Evidence: pixel samples of real in-flight photos: omaat_f33 aisle #5e4d32, omaat_f2 #5b4d3a, omaat_f7 #4d3f31 (B well below G).
     The model's `MAT.carpetJ` '#645554' has B ≈ G, so it renders #433a3a in q02_suiteAisle.
   - Fix: add `carpetF: { c: '#5c4b3a', r: 0.95, l: LAYER.fabric }` and use it for `zn.cls === 'F'` at the carpet line
     (~l.466). Keep carpetJ for THE Room unless the room photos also show brown.

## To lighting / integration (`src/12_scene.js`)
1. **The suite interior renders much darker than the photos when seen from the seat (q03 / q05).** (suite_r3, medium)
   - The ottoman renders #474141 against omaat_f11 #70635c. The table and console tray read near-black while the window
     sidewall beside them blows out to white.
   - The suite worker lightened fInner / fFabric by 12–15 % in SEATMAT. The rest is AO / fill: the 1.3 m shells get heavy
     AO. Suggested fix: raise fill inside the F zone (z in the suiteZ range), or lower the AO weight for suite geometry in computeAO.
2. **Blocky sun patches on the suite bed (q04_suite1Abed).** (suite_r3, low)
   - The window sun patches have stair-stepped edges and are fully clipped white; omaat_f57 / f58 show only soft light.
   - Suggested fix: use PCF / a 3×3 tap for the sun-LUT lookup, or soften the patch edge. The duvet albedo has been lowered
     to #e2dfd8.

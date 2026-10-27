# Issues found by the suite worker in other areas

## To shell (`src/07_shell.js`)
1. **F-zone carpet is mauve-grey; the real one is a warm brown heather.** (suite_r3, medium)
   - Evidence: pixel samples of real in-flight photos: omaat_f33 aisle #5e4d32, omaat_f2 #5b4d3a, omaat_f7 #4d3f31 (B well below G).
     The model's `MAT.carpetJ` '#645554' has B ≈ G, so it renders #433a3a in q02_suiteAisle.
   - Fix: add `carpetF: { c: '#5c4b3a', r: 0.95, l: LAYER.fabric }` and use it for `zn.cls === 'F'` at the carpet line
     (~l.466). Keep carpetJ for THE Room unless the room photos also show brown.
   - Close-up ref/web/suite/pb_30.jpg (daylight, under the ottoman) shows the pattern: brown heather (#6b5b47) with scattered
     navy/slate-blue fleck clusters about 1–3 cm across. Blue-lit photos (tlfl_25, up_empty) read blue-grey only because of mood lighting.

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
3. **Tint the glowing atlas text by the material colour, so THE Suite seat plaques glow blue-violet.** (suite_w2a, medium)
   - Real plaques (omaat_f7 / f9 '2K') show blue-violet lit characters. The suite tag material in 09_seats.js already sets
     `c: '#8f9cff'` on LAYER.atlasGlow, but 04_shaders.js line ~92 ignores base for layers 13–15, so the text stays white.
   - Fix: in that branch, for layer 15 use `emissive = tc * base * u_emisGain * emis * 4.0` (tagGlow and exitGlow are white; the
     10_mono washi materials #f2f3f6 / #d4d3e0 would pick up their intended slight lavender tint, so check q11 after the change).

## Final confirm (head 1430d42) - to lighting / integration
Suite met the bar (A 8.6 / B 8.9). These notes from the raters are not blocking; renders and diffs are in the suite-final scratchpad and can be reproduced with `node test/qa.js <out> 930 575 q03_suite1A q05_suiteBehind`.
1. **The sidewall around F renders cool blue-grey and darker since L7-L15.** (medium, both raters)
   - q05: from 239/241/245 to 199/204/214 (blue 15 above red). q03: from 233/235/237 to 194/197/204. f_17313 shows a neutral 226/228/227.
   - Because of this the suite caps read too pale against the wall: cap/wall luma 0.92, against 0.45-0.5 in f_17313 and up_Empty.
   - Fix: neutralise the sidewall/reveal tint in the F zone (cool fill or the window-belt term in `12_scene.js`) and bring it back to about L225. If the cap/wall ratio is still above about 0.7 afterwards, tell suite: the suite-side fix is `fCap` #8f8a76 -> about #7d7868.
2. **The window view in q03 is nearly clipped.** (low) It went from 237/243/249 to 251/253/255 and the cloud detail is gone. This is acceptable, since f_17313 is also blown out.
3. **Sun patches on the bed and ottoman are still hard-edged parallelograms.** (low) The q04 patch is 245 against 210 shade; f_17304 shows soft light. The window-console wood tray lost its sun stripe and reads flat.
- **Lighting final touch (71fdda1):** item 1 done: q05 wall 222/223/223, q03 219/220/221, B-R +1 (f_17313 226/228/227); the bowls no longer take the tub-sky hue. Suite: please re-check cap / wall (fCap if > 0.7). Items 2 / 3 (low) not changed. See fixed_integration.md "Lighting final touch".

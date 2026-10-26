# Polish E (2026-10-26): shell + ceiling/bins items from from_integration.md (lighting run 2, L9-L11)

Base: 08a2d0b. Shell change in ff6aa2a. Renders: own only (scratchpad); evidence crops in `review/qa/polishE/`.

## 1. Shell (low): day window panes capped below white. **Done, rated, kept.**
- **Evidence check:** c_27316's window pane is blown white (#ffffff), and so is y_47300 (#fcfcfb). On the head, the q14 pane (635-675, 230-300)
  max was 235 / 241 / 244 and p50 233 / 239 / 243, against a cap of 255 x [0.93, 0.95, 0.96] = 237 / 242 / 245. The evidence holds.
- **Change:** `07_shell.js` glass tints [0.93, 0.95, 0.96] -> [0.985, 0.99, 1.0].
- **After:** q14 pane max 249 / 251 / 254, p50 247 / 249 / 253. q14 share above L250 0.01 -> 0.57 %. q07 share above L235 6.6 -> 8.0 %.
  q03 share above L235 14.3 -> 15.4 %. Only glass pixels change; q15, s05 and ra_door2floor are pixel-identical.
- **Targets:**
  - p50 >= 250 is met for B (253), not quite for G (249). The frame under the glass is ~251, so the rest is winExp (lighting's).
  - The PY/Y panes' near-white share is now 64-91 % (rater B), against 59 % in y_47300.
- **q12 (look-out):**
  - The frame's mean L* is +1.0 (50.9 -> 51.9), the interior wall is unchanged, and the exterior seen through the pane is +1.7-2.8 L*
    (a pure 4 % scale).
  - Both raters judged q12 no worse; B called it slightly better, with less veil.
  - For q12 to match to within 2 L*, the exact compensation is lighting's (see from_shell.md).
- **Rating shell w18:** A 8.5 / B 8.5 (w17 8.5 / 8.5), no high or medium issues. Guard passed, so the change is kept.
- **New low, both raters, for lighting:**
  - Panes are still slightly cool (R about 6 below B).
  - The near grazing pane in q07 shows saturated blue sky (154, 192, 230) where c_27316 is blown white.
  - The tint is already near 1.0, so this is sky / exposure. It is handed off in from_shell.md.

## 2. Ceiling (low, carried L7-L11): grey dashes on the "right outboard bin lip" at door 3. **Not done (no geometry fault; neither suggested fix changes it).**
- **Step 1, which mesh:** rendered z04 at DPR 2 (`setView([2.3, 1.62, 32.7], PI/2 - 0.45, 0.25)`), then hid meshes by name from
  `scene.opaque`.
  - Hiding `psu*` + `signPods` removes the dashes (polishE/z04_noPSU.png). Hiding `psuBox` / `psuAir` (the outboard per-bay PSUs)
    does not.
  - So the mesh is **`psuo2`**, the THE Room centre-channel units at x = +-0.15, rows 15 / 16 (z 29.55 / 31.45).
- **What the "lip" is:** the bin in the foreground of z04 is the centre bin seen from the side, not the right outboard bin.
  - The camera stands at x 2.3 and looks forward-left.
  - A close camera on the same sight line (`[1.25, 1.74, 31.95]`, yaw 1.04, pitch 0.15, polishE/z04_close_psuo2.png) resolves the
    dashes: they are the units' sign pill and eyeballs, intact. The near door's curved lower edge (CBIN_DOOR x 0.24-0.42,
    y 1.835-1.842) cuts across them, because the units hang ~19 mm below the door line by design (PSU_DROP).
  - This is ordinary occlusion seen nearly edge-on, not z-fighting and not a mesh poking through. Polish B reached the same
    conclusion with colour tests.
- **Step 2, the suggested fixes:**
  - Ending the run 0.05 m before the door-3 boundary does not apply: the units sit 0.65 m and 2.5 m short of z0 = 32.10.
  - Built and rendered both directions on the F/J centre units only: drop 2 mm, and recess 5 mm. The z04 crops are visually
    unchanged (polishE/z04_variants.png: head / drop / recess).
  - Hiding the units fully from this angle would need them above y ~1.86, i.e. above the bin bottom. That contradicts the photos
    (b_sany_y22: a raised housing in the channel) and would lose them in the up-views rated at 8.5-8.8.
- **No change committed, so no ceiling w16 round.** The same look appears anywhere the centre channel is seen at a grazing angle
  from a cross aisle; it is not specific to door 3. Question in questions_ceiling.md.

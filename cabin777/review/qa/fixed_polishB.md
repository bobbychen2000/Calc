# Cross-area polish B (ceiling/bins + shell): from_integration items, 2026-10-25

Files: `07b_ceiling.js`, `08_bins.js`, `07_shell.js`; shared one-line keys in `03_tex.js` (`LAYER.jCarpet`, `N_LAYERS` 38,
`PHOTO_LAYERS` / `PHOTO_GAIN` / `LAYER_PARAMS` 37); `test/make_swatches.py` `j_carpet`; `tex/tex_j_carpet.png`.
Renders: scratchpad, own renders only (q06 / q13 / q15 / q16 / q17, seated 12H dining, door-3 z04 / w04 at DPR 2, q20 night, q21 amber).

## Ceiling / bins
- **Sky hairline at the outboard-bin lens / lining junction (r3 medium): done.** The lens (0.045 m at |x| 2.80) stopped 3 cm short of
  the lining top (1.60 at |x| 2.854) and the bin corner (2.845) 9 mm short, so the background showed through. Lens now 0.09 x 0.008 at
  |x| 2.83 (7 cm visible, laps ~2 cm behind the lining) plus an opaque bin-colour backing strip behind the lining top. Seated 12H,
  dining, blackouts: sky-blue pixels in the top band 296 (day) vs 56 (night sky) before; 56 / 56 after (the remainder are screens /
  EXIT), i.e. no sky through the junction. +936 triangles.
- **Bin lens size in the amber moods (r2 medium, our call): done** with the item above: 7 cm visible x 8 mm (suggested 6 x 0.8 cm).
- **Aisle vault darker than the bins in the white moods (r3 medium): done, adjusted.** The suggested eFn (0.14 / 0.10 + 0.10 exp(/0.35))
  rendered q06 vault L240 and clipped the joint ribs; settled on 0.11 / 0.06 + 0.07 exp(/0.30): q06 vault L194 -> 232, q16 189 -> 228
  (c_27312 236, y_47301 225-241). `doorC` eFn 0.14-0.20 -> 0.07-0.12: q06 centre bin 220 -> 203. Outboard doors (`BINMAT.door`, no
  emission) `#e3e5e8` -> `#d6d8dc`: q06 221 -> 215 (photos 190-210); vault / outboard bin 0.88 -> 1.08 (photos 1.15-1.37). Going further
  would grey the bins in the other moods; the rest of the gap is the bins' flat shading (lighting).
  Side effect handed to lighting (from_ceiling.md): the night `vaultE` cap 0.09 now binds, night vault L29 -> 62 (photo L13-55).
- **Door-3 bin-lip z-fight (r1-r3 low): not a z-fight, no change.** Three colour tests at DPR 2 on the integration camera
  (`setView([2.3,1.62,32.7], PI/2-0.45, 0.25)` and the w04 camera): outboard lip / lip line / band (red / green / blue), then outboard
  door / bin body / lip, then centre door / lip gap / channel. The "dashes" are on the **centre** bin's channel, not the right outboard
  lip: they are the J centre PSU housings (white pills 1.5 cm proud of the channel) with their dark reading-light sockets, seen
  edge-on at ~7 deg from the door-3 cross-aisle. Nothing is coplanar (housing bottom 7.5 mm below the lowest shingle). The shimmer
  while walking is sub-pixel geometry, which MSAA / the lighting AA would address, not an offset.
- **Night trough grille FYI: done.** `CEILMAT.troughRim` e 0.2 -> 0.19 (fill-lift branch): q20 bars no longer white at night.

## Shell
- **THE Room carpet texture (r2 / r3, third request): done.** New photo tile `j_carpet` (`test/make_swatches.py`): the suggested
  c_27312 mid-aisle crop is ~4 mm/px and foreshortened ~0.4, so its specks became vertical streaks when squared; cut from
  c_27315's footwell carpet instead (seen near-overhead, isotropic specks), 120 px ~ 0.36 m, luminance only. Layer 37 (gain 1.4,
  1.0 gave std 5.5). `carpetJ` `#615553` (#574a4c rendered L46, too dark and too purple). q06 aisle (500-580, 420-560): before L56.8,
  box-4 high-pass std 2.0; after L55.9, std 7.6 (target 4-11; c_27312 L52, 11.9), hue mauve-brown.
- **w12 / w15 creams render neutral, door glass flat white, dado grille near black: no shell change.** The integrator answered these
  in fixed_integration.md (lighting keeps the official photos' cool-neutral reveal; door glass is the cabin pane under winExp; the
  grille is AO). The shell albedos are already cream (`reveal` #ece4d5, door shade #d8d2c6); a warmer albedo to offset the light
  would break the official-photo match the shell was rated on (w15 8.5 / 8.5), and no photo value was given for the grille.

## Re-rating (calibrated two-rater rounds on the pushed head)

| Area | Round | Rater A | Rater B | Note |
|---|---|---|---|---|
| ceiling | w14 (d2627ff) | 8.2 | 8.6 | W14A-1 high / F1 medium: the vault rose, the fittings on it (ribs, speaker, emergency base) kept their old emission -> 0.78x the vault, black planks at night; W14A-2 crest channel 0.40x |
| ceiling | w15 | 8.5 | 8.8 | fittings on the vault's cove-LED layer + eFn (ribs +0.01, speaker face x0.92), shadow crescent #b4b2ae, crest channel #a9acb1 over 0.45 of the chord. No high / medium |
| shell | w16 (d2627ff) | 8.5 | 8.5 | J carpet fixed (high-pass 0.4-0.8 -> 7.5-7.8); w16a-1 medium: F and door-bay carpets now the only flat floors |
| shell | w17 | 8.5 | 8.5 | carpetF / doorCarpet on the heather tile (q03 F floor std 0.5 -> 8.0-8.2, f_17313 7.2), tile re-cut HP 20 (banding 4.2 -> 2.8), gain 1.2 (q06 6.4-6.7 vs c_27312 6.2). No high / medium |

The w14 drop (0.3) was the regression guard case: the change that hurt was the vault eFn lift without the fittings; fixed in w15
rather than reverted, because both raters scored the brighter vault itself as fixed (vault / bin now brighter, as in the photos).

**Left open (all low, recorded, not done):** speaker reads as its crescent only (w15a-1 / S1: bezel at vault tone; a ring 0.95x was
suggested), crest channel two-tone core (W15A-2), PSU band joints 4 vs 8-10 per bin (W14A-3), vault / bin ratio 1.04-1.12 vs 1.15-1.23
(lighting / optional `BINMAT.door` #cfd2d6), door-4 wedge (`lightPanel` e 0.3 -> 0.12, door zones were not in this hand-off), far-side
lens sparkle (LN1), F carpet its own coarser tile from f_17300 and a slightly redder `carpetF` (w17a-1, fcarpet-hue / fleck; asked in
questions_shell.md), J carpet mid-aisle hue (w16b). Out of area: F pillows render lavender in the F aisle (suite).
Triangles: ceiling 501.8k -> 502.7k (+936, ~+21.4 % of the wave-3 start); shell unchanged.

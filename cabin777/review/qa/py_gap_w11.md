# PY gap analysis, w11 (commit 1432360; w10 A 8.2 / B 8.2, target 8.5+ from both)

Question: which 3-5 changes would most raise PY toward 8.5? Constraint: no net triangle growth.
The scratch evidence (crops, montages, scripts) is in
`/tmp/claude-0/-home-user-Calc/c6e420be-be6c-56c3-9e6e-efdc259c79f1/scratchpad/w11/gap/`.
All measurements are PIL/numpy on the 930x575 official photos and the w11 renders. Stats are sRGB L = mean(R,G,B).
S = (max-min)/max. "dark" and "light" are the mean colours of the p10 and p90 pixels.

## Verdict on the caller's first impression

- **Fabric reads as white salt-and-pepper: confirmed.**
  - Studio p8 back: p90/p50 = 1.38, against 1.24 for py_37301 back.
  - The light dashes are near-neutral: S 0.03-0.11 in the render, against 0.12-0.22 in the photos (pale blue `#cedcf1`, not white).
  - q14 near back: p10/p50 = 0.68, against 0.77 for py_37305 R back close-up. Our darks are too deep and our lights too bright, so it reads as static.
  - Mechanism, simulated through the shader's per-channel ACES (`sim.py`, `proto.py`): the tile's light dashes reach 1.9-4.0x the mean (p90 1.90, clipped at ENC 4). The base is lifted 2x by `photoBase`. ACES then pushes the dashes into the shoulder, where they lose chroma. At studio exposure the light-dash S is 0.09, and in the brighter cushion 0.04.
  - The photo cloth is a calmer **block mosaic**: short, chunky cells (h/v correlation aspect 1.3-1.5 on py_37305, against 2.0 rendered) grouped into light and dark 2x2 patches.
- **Wing confetti reads as big white dots: confirmed, with a twist.** The luminance spread now matches: p4 wing p10/50/90 76/94/130, against py_37305 L ear 67/86/130. The problems are **shape and ground**:
  - Our petals are soft, evenly spaced ovals.
  - They sit on dark *dash rows* (`synth_py_confetti` w7 weave). The photo ear ground is a fine boucle mottle with no rows.
  - The photo has more and smaller chips, sharp and angular.
- **Console bluer than the photo: mostly refuted.**
  - py_37301 console face is `#425679` (S 0.45), side strip S 0.37 and inner side S 0.32. The render's p8 face `#414b65` (S 0.35) is inside that range.
  - py_37303 and py_37306 do read greyer (S 0.14-0.22). Our hue is slightly violet: H 224-227 against 215-222.
  - At most a one-line hue nudge. It is not a ranked item.
- **Bigger finding the caller did not list: ANA uses two seat colourways, and we model only one.** See item 1.

## Ranked changes

### 1. Add colourway B: petal back and cushion, dash ears. Expected +0.2-0.3, zero triangles.

**Evidence.** Montage: `gap/ev_colourways.png`.

- **Official photos:**
  - py_37302 is the q13 reference. Its foreground seat has the **petal (confetti) cloth over the whole back**, and its **ears are the dash cloth**. That is the inverse of py_37301.
  - py_37305 shows both on adjacent seats. The left ear is petal (colourway A). The right ear is dash: dark `#18191e` with light `#c3c2c9` dashes, p10/p50 0.36 (colourway B). Crop: `gap/z305.png`.
- **Real in-flight photos:**
  - san_12 (SANspotter, NH 777-300ER PY): the passenger's own seat has a petal back and a petal cushion on a grey ground. The neighbouring seat ahead shows the dash back.
  - san_11: the front-left seat has a petal back and cushion, and a dash skirt on the leg rest.
- So questions_py.md items 4 and 9 ("is row 25 dressed differently?") are answered by evidence. It is not a row-25 special: seats alternate between two trims.
- **Render:** every seat in q13 and q14 is colourway A, so q13 cannot look like py_37302. The 37302 foreground is the single biggest fabric area in that pair.
- The raters' lowest fabric scores trace to this mismatch:
  - B: fabrics 7.5.
  - A: "37301 back is a mosaic, 37302 back is sparse cream flecks".

**Cheapest fix.** Material swap only, so no geometry growth.

- In `09b_py.js`, at the top, add `Object.assign(SEATMAT, {...})`:
  - `pyFabricB: { c: photoBase('#7e8593', 'py_confetti'), r: 0.9, l: LAYER.pyConfetti }`: back and cushion. Same mean as pyFabric, so the tone structure is unchanged.
  - `pyWingB: { c: photoBase('#626876', 'py_back'), r: 0.9, l: LAYER.pyFleck }`: dash ears on a slightly darker ground (py_37305 R ear mean `#6a6a72`).
- `pySeat(B, x0, lod, opts)`:
  - Take `opts.cw` (0 = A, 1 = B).
  - Set `const F = opts.cw ? SEATMAT.pyFabricB : SEATMAT.pyFabric;` and `const W = opts.cw ? SEATMAT.pyWingB : SEATMAT.pyWing;`.
  - Use `W` in the ear loft (line 61), and `F` for the cushion, back, bolsters and headrest loft (it already does for all but the ears).
  - Keep the leg-rest skirt on the dash cloth in both colourways (san_11).
- `pyUnit`:
  - Replace `xs.forEach((x) => pySeat(B, x, lod, opts))` with `xs.forEach((x, k) => pySeat(B, x, lod, { ...opts, cw: (k + (n === 4 && k > 1 ? 1 : 0)) % 2 }))`. That gives A|B pairs and A,B,B,A quads.
  - Do the same in `pyUnitFar`: cushion, back and headrest box use `pyFabricB` for the B seats.
- Instancing repeats the pair, so a 2-seat unit always reads A|B. That still breaks the uniform look and matches py_37305 and san_12, which show neighbours that differ.

### 2. Retune the dash cloth into a calm block mosaic with chroma. Expected +0.15-0.2, zero triangles.

**Evidence.**

| Patch | p10/p50 | p90/p50 | S | Light-dash S | Light-dash colour | Source |
|---|---|---|---|---|---|---|
| Photo py_37301 back | 0.74 | 1.24 | 0.21 | 0.15 | `#cedcf1` | |
| Photo py_37302 near back | | | 0.36 | 0.22 | | |
| Photo py_37305 R close-up | 0.77 | 1.29 | | | | |
| Render p8 back | 0.74 | 1.38 | 0.21 | 0.14 | | |
| Render p8 cushion | | | 0.09 | 0.03 | `#e2e5ea` (white) | |
| Render q13 near back | | | 0.17-0.18 | 0.11 | | |
| Render q14 near back | 0.68 | 1.30 | | | | high-pass SD 0.26 vs 0.17 (py_37305) |
| Tile as is | 0.54 | 1.48 | 0.18 | 0.09 | | `proto.py`, studio exposure |
| Tile proposed | 0.75 | 1.32 | 0.26 | 0.16 | | `proto.py`, same exposure; photo is 0.74 / 1.24 |

- Side-by-side (current left, proposed right): `gap/tile_proto.png`.
- Close-up crops: `gap/fab_side.png` (py_37305 / q14 / py_37302 / q13) and `gap/ph301_back.png` vs `gap/r_back.png`.

**Cheapest fix.** All in `test/make_swatches.py synth_py_back`, then re-run `python3 test/make_swatches.py`:

- Dash length `np.clip(rng.normal(19, 7), 8, 32)` -> `np.clip(rng.normal(14, 4), 8, 22)` (chunkier cells).
- Light band half-height `(3.0 - np.abs` -> `(3.6 - np.abs`.
- `out = (1 + 1.9 * lite) * (1 - 0.76 * dark)` -> `out = (1 + 1.15 * lite) * (1 - 0.5 * dark)`. This removes the near-black and white extremes.
- Brick-patch lattice `rng.normal(0, 0.15, ...)` -> `rng.normal(0, 0.24, ...)`. This makes the 2x2 light and dark mosaic blocks read, as in py_37301 and 37305.
- `ENC['py_back']` 4 -> 3, and `PHOTO_ENC.py_back` 4 -> 3 in `src/03_tex.js` (shared, one line). The tile now peaks at about 2.5x, so the base needs less lift and loses less chroma under ACES.
- `SEATMAT.pyFabric` `#7e8593` (S 0.15) -> `#7a849b` (S 0.21) in `09_seats.js` (shared, one line). This answers rater A's "35 % less saturated".
- Optional: pyFabric `r` 0.9 -> 0.8 for the soft sheen on the bolster crowns. py_37301 back lf (low-frequency SD) is 10.5 against 7.0 rendered.
- Optional: `LAYER_PARAMS[17]` normal 0.3 -> 0.2 (calmer up close in q13b and q14).

Item 1 makes this cloth the ear cloth of colourway B as well, so the retune pays twice.

### 3. Petal (confetti) tile: boucle ground and more, smaller, sharper chips. Expected +0.1 (more once item 1 puts it on whole backs).

**Evidence.** Montage `gap/wing_cmp.png`: py_37305 L ear, py_37301 ear, p4, q14, q13.

- Photo petals are crisp angular chips. There are about 1.5x as many, with many small 2-4 mm ones, on a fine dark boucle mottle with **no dash rows**. The same holds for the B backs in py_37302 and san_12.
- Ours are soft ovals on visible dark horizontal dash rows. At q13 and q14 distance the rows read as stripes and the ovals as polka dots ("big white dots").
- Contrast already matches (see the verdict above), so do not raise the gain.

**Cheapest fix.** In `make_swatches.py synth_py_confetti`:

- Delete the 9x4 dark-dash-row loop (the `for r in range(9)` block).
- Replace it with a boucle mottle: `out *= np.exp(0.18 * _blur_wrap(rng.normal(0, 1, (S, S)), 1.2) / 0.2)` plus about 25 dark specks at x0.6.
- Petal count 20 -> 32, with blue-noise spacing 32 -> 24 px.
- `req = np.clip(rng.normal(5.5, 2.0), 2.5, 8.5)` (smaller on average, more small ones).
- Edge softness `/ 1.0` -> `/ 0.6`, so the facets survive the mip.
- Keep the petal amplitude 6.5 and ENC 6.

### 4. Ear silhouette and flap finish: a domed bean, not a flat-topped block, and smooth satin navy. Expected +0.1, zero triangles.

**Evidence.**

- **Ear shape:**
  - py_37301, 37302 and 37305 ears are round beans. The top curves continuously into the flap fold, and shading runs from a lit crown to dark edges. Photo ear lf is 25-34 (py_37302 25.2, py_37301 33.6).
  - Ours have a near-flat top cap (sections 0.85 -> 0.88 -> 0.898 -> 0.905 collapse in the last 2.5 cm) and are flat-lit. q13 ear lf is 5.8.
  - Crops: q13 near seat in `gap/ev_colourways.png`, and `gap/wing_cmp.png`.
- **Flap:**
  - The flap's grain gradient is 5.6 (q13, p8), against 1.2-3.7 in py_37301 and 37302 (rater A: "slightly too grainy").
  - The q13 flap is `#38456e` (S 0.49), against py_37302 `#293769` (S 0.61).

**Cheapest fix.**

- `09b_py.js` ear loft (line 61): keep the 7 sections and redistribute them as `SEC(0.672,0.05,0.05,0,0.024), SEC(0.69,0.10,0.105,0,0.048), SEC(0.72,0.11,0.12,0,0.055), SEC(0.80,0.11,0.12,0,0.055), SEC(0.855,0.10,0.105,0,0.05), SEC(0.885,0.075,0.08,0,0.036), SEC(0.905,0.03,0.03,0,0.014)`. That gives a long dome over the top 10 cm instead of 5 cm.
- `SEATMAT.pyCover`: `l: LAYER.leather` -> `l: LAYER.plastic` (albedo 0.04 and normal 0.10, against 0.14 and 0.32), and colour `#343f60` -> `#2e3a66` (closer to py_37302 navy). This is shared `09_seats.js`, one line. The hem material on line 75 can stay.

### 5. From behind, hide the headrest top behind the shell rim. Expected +0.05-0.1 (q13b), saves triangles.

**Evidence.**

- In q13b about a third of the frame is the near seat's fabric top: a navy over-top strip and petal domes above the grey shell.
- py_37304 and san_26 (seated camera) show only the grey shell arch. Rater B flagged this in w9 and w10 (low, "not fixed").
- Geometry:
  - The shell top sections (`ds` y 0.925-0.958, d 0.07-0.035) centre at z ≈ 0.08, so their front face is at about +0.045.
  - The headrest top (`SEC(0.91, 0.31, 0.05, -0.002)`) ends at about +0.023.
  - That leaves a 2 cm open trough you look down into.

**Cheapest fix.**

- Delete the navy over-top `gRBox(0.26, 0.008, 0.045 ...)` at `09b_py.js:72`. This frees triangles for anything above.
- Deepen the shell's top sections forward:
  - `ds` entries `[0.905, 0.085, 0.48]`, `[0.925, 0.07, 0.475]`, `[0.938, 0.062, 0.455]` and `[0.95, 0.05, 0.43]` -> d `0.11 / 0.10 / 0.085 / 0.065`.
  - The rim then closes over the headrest top (front face about +0.03 to +0.02).
- Check in the studio from the front that the rim does not show as a grey bar above the flap. py_37301's near seat shows only a thin grey edge behind the top.

## Not ranked

- **Console hue:** optional `pyArm` `#4f5a76` -> `#505b72` (H 224 -> 220). py_37301 is S 0.32-0.45; py_37303 and py_37306 are 0.14-0.22.
- **Literature net:** rated 7.5-7.6 by both raters, but it is a low-visibility rear detail, and a loft that follows the bucket needs more triangles. Do it only with triangles freed by item 5.
- **Gooseneck:** fixed after the w10 rating in 1432360. In p8 and q14 the heads hang near-vertical and apart.

## Expected outcome

- Items 1 and 2 address the two lowest scored details that remain (B fabrics 7.5, A fabric saturation).
- Item 1 also makes q13 match its own reference photo for the first time.
- With items 1-4: about 8.5-8.7 from both raters. Item 5 is insurance against B's repeat low issue.

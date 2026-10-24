# Exterior gap analysis, w16 (from A 7.8 / B 8.0 toward 8.5)

Inputs: r16 renders (head 0f172d3, which already holds the "final" pylon nose and canoe-lift edits and the lighting
"exterior spec follows albedo" change), the photos in `ref/web/exterior/`, the w14/w15 ratings, and `src/11_exterior.js`.
Work files are in `/tmp/claude-0/-home-user-Calc/0185d7bc-6b95-54c6-a367-1813fba44537/scratchpad/gap16/`.
Experiments ran on a scratch copy of the repo (`.../scratchpad/exp/`, builds dA-dE, renders rA-rE, all with
`review/qa/exterior_views.js`). Samples are 11x11 px Rec.709 luma means.

Triangle count, measured in the page with `buildExterior(null)`: r16 = **29,440** (cap ~31.5k). None of the items below
needs new geometry beyond about 200 triangles, and item 4 frees 224.

## Ranked changes

| # | Change | Owner | Cost | Expected gain (A / B) |
|---|---|---|---|---|
| 1 | Near-field fastener rows and hinge stains on the near flap and spoilers | 11_exterior (+ one atlas cell) | ~40 lines, ~+200 tris | +0.15 / +0.10 |
| 2 | Pylon forward fairing as a low, broad blister blended into the cowl (tested) | 11_exterior | 4 lines, 0 tris | +0.08 / +0.08 |
| 3 | Steeper near-to-far albedo ramp (tested). The lighting spec fix is a no-op, so stop waiting on it | 11_exterior | 1 line | +0.08 / +0.05 |
| 4 | Wingtip: flush nav lens with the glow moved into it; 7 finer static dischargers, not a 14-pin comb (tested) | 11_exterior | 4 lines, -224 tris | +0.06 / +0.05 |
| 5 | Cowl weathering from its own mottle tile, plus a polished inlet lip | 11_exterior + make_swatches | ~15 lines | +0.04 / +0.04 |

Items 1-4 together are worth about +0.35 to +0.4. That lifts A to about 8.2 and B to about 8.4. Reaching 8.5 on both
also needs item 5, or the lighting hand-offs at the end.

---

## 1. Near-field fastener rows and stains (surface texture realism, the biggest open gap)

**Evidence**
- `gap16/z_w19A_kn41_crop.jpg` puts the near wing in w19A next to KN41 (`a5_kn_ANA77W_TheRoom_41.jpg`) at about the same
  framing.
  - KN41 shows dotted fastener rows along every spoiler and flap panel edge, a chordwise row on each spoiler, black
    hydraulic/soot smudges at the spoiler-flap hinge fittings, and the step seal lines.
  - The render's near flap and spoiler are blank, apart from soft low-frequency streak banding.
- Fine-detail measure (robust SD of a 3 px high-pass):

  | Region | Fine SD |
  |---|---|
  | w19A flap (480,410)-(560,460) | **0.00** |
  | w19A flap (440,470)-(520,520) | **0.00** |
  | w19A spoiler (560,300)-(620,350) | **0.00** |
  | w17A near skin | 0.00 |
  | KN41 near flap (half-res) | 1.48 (0.9 % of mean) |
  | KN41 panel with rows | 2.97 (2.1 %) |

  `gap16/z_w19A_nearflap_zoom.png` shows the render's near flap at 3x zoom.
- The 4 m x_skin tile is 1.6 cm/texel. At the 4-6 m range of the near flap (about 6 mm/px) it is magnified into smooth
  banding, so it cannot supply fine detail there.

**Why the current approach cannot do it**
- Real fastener pitch is about 25 mm, about 4 px at the near flap.
- Vertex-colour dashes in `wingLine` need about 240 triangles per 6 m row even at a 0.15 m pitch.
- At that pitch they read as stitching. w4 already found that 0.3 m dashes "read as road marking".

**Cheapest way: an atlas-textured strip**
- This route is already used by `07b_ceiling.js` (`slat: { l: LAYER.atlasLit }`) and `07_shell.js` (`decal`).
1. In `06_atlas.js`, add one cell `'rivets'` of about 512x16 px: 20 dark dots (r about 3 px) evenly spaced on a
   transparent-to-paint background, mean about 0.9. This is a shared file, so make one small local edit and say so in the
   commit. The atlas mips fade the row into a faint line at range, which is what the current `riv` hairline does.
2. In `11_exterior.js`, add a `wingDots(B, side, path, mat, w)` next to `wingLine` (l.148).
   - It is a copy of `wingLine` that resamples `path` into 0.5 m segments, each with its own four vertices.
   - Each segment carries `u` = `atlasUV('rivets')` x from 0 to 1 along its length and y from 0 to 1 across it.
   - That costs 2 triangles per 0.5 m.
3. Rows, per side, from s 3.1 to 12 only (the near views w17A/K, w19A, w26K):
   - spanwise along the inboard spoiler hinge (x = 37.82 + 0.06)
   - the flap nose (38.82 + 0.10)
   - mid-flap
   - the rear-spar row (replace the near half of the `riv` line at l.298-302)
   - chordwise either side of each spoiler break (s 4.5 / 6.55 / 8.6, ±0.05)
   - In total that is about 25 m, about 50 segments and about 100 triangles per side.
4. Stains: about 6 per side.
   - Make short dark wingLine blobs, `{ ...paint, c: '#3d3f42', r: 0.9 }`, 0.10 x 0.25 m, chordwise, at the spoiler
     actuator and flap-track positions (`WING.canoes` s values and s 4.5 / 8.6 at x 38.82 + 0.05).
   - Add one or two longer exhaust-soot streaks on the flaperon (s 9.8-11.8).
   - KN41 has these black hinge smudges at the flap junction. This costs about 24 triangles.
   - Keep the stain colour multiplied by `ramp` so it does not pop at range.

**Zero-triangle alternative (lighting/integration hand-off)**
- The wing body vertices carry `v_uv = (chord fraction, span s)`; see `B.u` at l.246.
- A procedural row mask in the layer-27 branch of `04_shaders.js` (l.176-200) could draw rows at fixed chord fractions
  and at the panel break s values, with dots from `fract(s / 0.025)`, faded by `fwidth`.
- It needs its own layer id, because the `wingLine` strips on layer 27 carry u.x 0 to 1 across their width.

**Expected gain:** A rates wing surface detail 7.4 and B rates it 7.8. Both name the fastener rows, so this should lift
that category to about 8.3, which is about +0.10-0.15 overall.

## 2. Pylon forward fairing: a low blister, not a tall slug (silhouette)

**Evidence**
- `gap16/z_pylon_w13A_137.png` compares the r16 w13A crop with the LALF `_137` crop at the same framing.
  - In the photo the forward fairing is a low, broad blister. Its crown rises about **0.12** of its visible length above
    the cowl, its flanks fillet softly into the cowl, and it has a rounded teardrop nose that closes over about 15 % of
    its length.
  - In r16 the crown is about **0.19** of the length. The flanks are near-vertical walls 1.35 m apart standing on the
    cowl. The nose is a blunt full-height bulb, `0.40 * sqrt(smooth(1.65, 2.15))` reaching full height in 0.5 m. In w13A
    and s13A it reads as a separate white tube lying on the nacelle.
- Tone is not the problem. The crown is brighter than the cowl in both: r16 183 vs 160, `_137` 215 vs 138.
- Experiment D (`exp/dD`, renders `exp/rD`; `gap16/x_pylon_r16_vs_D.png` and `x_pylon11_r16_vs_D.png`): w13A, s13A and
  w11A now show a low blister matching `_136` and `_137`. There is no change in triangle count.

**Code (l.450-462)**
```js
const ridge = nacTop(x) + Math.max(0.24 * Math.sqrt(smooth(1.65, 2.6, x)), 0.48 * Math.pow(smooth(1.65, leE - E.x0, x), 0.9));
const bot = x < 6.35 ? nacTop(x) - Math.max(0.30, ridge - nacTop(x) + 0.12) * lerp(0.5, 1, nose) : ...;   // move below ridge (uses it)
const w = (x < 6.35 ? lerp(1.6, 1.15, smooth(2.0, 6.35, x)) : ...) * lerp(0.3, 1, nose);
// l.462: taper the flanks so the section is a tent that fillets into the cowl
{ const fs = secs.slice(0, kLE + 1), gF = gLoft(fs, 8, [true, false]);
  for (let k = 0; k < gF.p.length / 3; k++) { const ay = gF.p[k*3+1]; let j = 0; while (j < fs.length - 1 && Math.abs(fs[j].y - ay) > 1e-6) j++;
    const q = fs[j], t = clamp(-(gF.p[k*3+2] - q.z) / (q.d / 2), 0, 1); gF.p[k*3] = q.x + (gF.p[k*3] - q.x) * lerp(1, 0.4, t * t * (3 - 2 * t)); }
  computeNormals(gF); B.add(gF, M4.trs(0, 0, 0, 0, Math.PI / 2), cowl); }
```
- D used a linear `t`, which left a faceted crown and a small kink where the two `max` terms cross (about x 3.5). Use the
  smoothstep taper above, and blend the two height terms with a soft max, for example
  `0.5 * (a + b + Math.sqrt((a - b) ** 2 + 0.003))`.
- Optional, from `_137`: a dark hairline seam along the fairing/cowl junction, and the thrust-reverser hinge line.

**Expected gain:** pylon 7.5 to about 8.2 for both raters, about +0.08 overall.

## 3. Near-to-far value: fix it in 11_exterior. The lighting fix does nothing here (value structure)

**Evidence**
- w19A (`r16`):

  | Point | L |
  |---|---|
  | near flap (600,440) | 162 |
  | near flap (560,500) | 164 |
  | far skin (680,195) | 169 |
  | far skin (720,220) | 171 |

  KN41 falls 194 to 146. Both raters have flagged this as medium since r12.
- The lighting change in 8d7ae91 (`04_shaders.js` l.443) divides the vertex-colour luma by **0.39**, the old #636466.
  - The wing paint is now #76787a, luma 0.47, so the factor is clamped to 1.0 on nearly every wing vertex.
  - r15 to r16 moved w19A by at most 1 L.
- Experiments:
  - Removing the exterior *sun* specular entirely (`exp/rA`) lowers the far skin by only 5 L.
  - A /0.50 squared normaliser applied to both spec terms (`exp/rB`) changes it by 1 L.
  - So the reversal is diffuse: the aft-sloping near flap turns away from the az -60 / el 30 sun, and the forward wing
    faces it. Only albedo can fix it.
- Experiment E (`exp/rE`, `gap16/x_ramp_r16_vs_E.png`) with the ramp below:
  - near flap 162/164 to **173/176**
  - far (680,195) 169 to **162**, (620,250) 153 to 157
  - The order is now right, near brighter than far.
  - In w26K (K side, sunlit), the near skin (560,270) stays 176 to 177 and (480,200) goes 190 to 188, so the
    registration contrast is unchanged.

**Code (l.252)**
```js
const ramp = lerp(1.22, 0.66, smooth(5, 20, sp));
```
- For more fall-off, try 1.25 to 0.60. The w12 roughness ramp at l.255 stays.
- Tell the lighting owner to drop the l.443 factor or renormalise it to the current paint. As it stands it is dead code
  for the wing.

**Expected gain:** this is the w19A/w17A value issue both raters log as medium. It is "not scored" on paper, but A's
surface-detail note ties its 7.4 to it. About +0.05-0.08.

## 4. Wingtip lights and static dischargers (lowest scored line: A 7.0 / B 7.2, never itemised)

**Evidence** (`gap16/z_tips.jpg`, `gap16/x_tip_r16_vs_E.png`)
- In n19A the red nav light is a sphere sitting *on top* of the tip (`tip.y0 + 0.01`, glow at `+0.05`), a "cherry", not
  a flush lens in the tip fairing.
- In w19A the 14 dischargers at 0.75 m pitch (l.505), 8 mm in #2a2d31, read as a dark comb/fringe along the raked TE.
  KN41's tip shows no such comb at this range.
- Experiment E made the comb disappear into fine wisps and saved 224 triangles.

**Code**
- l.501: `M4.trs(tip.s * side, tip.y0 - 0.02, tip.le + 0.12 + WING.dz, 0, 0, 0, 0.8, 0.35, 1.4)` sinks the lens into the
  LE fairing.
- l.503: move the glow point to the lens too, `[tip.s * side, tip.y0 - 0.01, tip.le + 0.14 + WING.dz]`. E did not move it,
  and the halo still sits above the tip.
- l.505-507:
  ```js
  for (const s of [24.0, 25.5, 27.0, 28.5, 29.9, 31.3, 32.1]) {
    B.add(gCyl(0.006, 0.006, 0.22, 4), M4.trs(p[0], p[1] - 0.01, p[2] + 0.11, 0, Math.PI / 2), { c: '#4a4e54', r: 0.6 });
  }
  ```
- Optional (night): give the tip light a `light` gain so it washes the raked tip red. The pass currently lights only
  down-facing faces (04_shaders l.229-233), so that is a lighting hand-off.

**Expected gain:** lights 7.0/7.2 to about 7.8, about +0.05.

## 5. Cowl weathering and inlet lip (material response)

**Evidence**
- `gap16/p_w11A_136.jpg` and `gap16/z_w11K_knav9.jpg`: the r16 fan cowl is a perfectly even white with no layer
  (l.228).
  - `_136` and `_137` show soft grey mottle, a darker smudge band aft of the strake, and slightly different panel tones.
  - knav `_9` shows a polished lip with a bright outer rim and a dark inner edge. r16's lip is an even matte grey band.
- Putting the wing's x_skin tile on the cowl (experiment E, `gap16/x_cowl_r16_vs_E.png`) gave **vertical streak banding**
  on the inlet cowl through the side projection. Do not reuse x_skin.

**Code**
- Cut an isotropic, unstreaked tile `x_cowl` from `_136`'s cowl in `make_swatches.py`: the `x_skin` recipe without the
  row box blur, SD about 0.08.
- Give it a layer slot. That is one line each in `03_tex.js` `LAYER` / `PHOTO_GAIN` / `LAYER_PARAMS`, a shared file.
- Set `cowl.l` to it at l.228, at a gain of about 0.2.
- Lip (l.383):
  - Use `{ c: '#b9bbbd', r: 0.32, m: 0.7 }`.
  - Add `shadeVerts` for its inner half (lathe x < 0.06: ×0.75) so the rim reads bright outside and dark inside.

**Expected gain:** nacelle colour/materials 7.8/7.9 to about 8.2, about +0.04.

---

## Not recommended now
- Canoes are already at 8.3/8.5. The r16 lift `smooth(9, 15)` × 1.25 is new and still unrated.
- Planform is 7.5 and both raters call it "unchanged, matches", so no geometric defect is named.
- Livery is 7.5/7.7 and correct.

## Lighting-only items (hand-offs)
1. `04_shaders.js` l.443: the albedo-follow normaliser 0.39 is a no-op for the #76787a wing (luma 0.47). It is also not
   what drives the near-far reversal, which is diffuse (rA/rB above). Either drop it or renormalise it, and do not count
   on it for item 3.
2. Long-hairline aliasing in w26K and w30K (A's artefacts 7.4): the hinge and gap strips shimmer at 20-30 m. This needs
   MSAA or a supersampled exterior pass.
3. The night nav light should wash the upper tip, not only down-facing faces (l.229-233).

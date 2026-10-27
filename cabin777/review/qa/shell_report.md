# Shell area report (src/07_shell.js)

Scope: sidewalls and seams, window recesses and linings, glass rim, electric (F/J) and manual (PY/Y) shades, dado,
air-return grilles and placards, carpets, Y seat-track covers, door-area vinyl, Type A door surrounds and their viewing
windows, and the colours of the door-lining parts. Contact sheet: `shell_before_after.jpg` (own renders only; the
"after" column also contains other areas' concurrent changes).

## Scores (two independent raters per round, fresh round first as the brief asked)

| Round | Rater A (skeptic) | Rater B (geometry first) | Mean | Files |
|---|---|---|---|---|
| r2 (previous session) | 6.6 | – | 6.6 | sidewall_r2.json |
| w1 | 5.3 | 6.0 | 5.65 | shell_w1a / w1b.json |
| w2 | 6.2 | 6.8 | 6.5 | shell_w2a / w2b.json |
| w3 | 7.2 | 7.4 | 7.3 | shell_w3a / w3b.json |
| w4 | 7.6 | 7.7 | 7.65 | shell_w4a / w4b.json |

No high-severity shell issue remains after w3. The 8.5 target was not reached in four rounds. What still holds the score
down is mostly outside this file or waiting on the user (see below). The w1 raters were stricter than r2 because they
downloaded about 280 new real photos (SANspotter PY/Y, OMAAT THE Room, MileLion THE Suite) and measured against them.
The w4 fixes (graded upper tub, faint ribs, darker blackout) were made after the w4 rating and verified in renders,
not re-rated.

## What changed (commits 86849fe, 060714f, 87d19d4, ab79912, 361a102, aebf9a1)

- **THE Room footwell intrusion (room_r3 high):** over the J seat zones the dado follows `DADO_J`, flush behind the pod
  walls (|x| ≥ 2.862 against 2.847), with no grilles. Caps close the step where a J zone meets a door surround. [V: 09c_room geometry]
- **PY/Y window tub (`REC_Y`):** the full 777 tub is 0.41 m wide (0.77 of the pitch), with its top at the bin line and
  its bottom about one bezel width below the bezel. [V ratios: y_47303, sans_14, sp_py_13] F/J keep their shorter bowl
  [V: f_17313, omaat Room-24/38, MileLion DSC_1920]. The PY/Y reveals are baked into the shell, so 12_scene.js needed no
  new meshes.
- **Upper tub:** it sinks 45 mm (F/J) or 55 mm (PY/Y) toward the top, and a vertex-colour grade takes it to 0.78 of the
  wall at the top. [V: DSC_1920 about 0.78, sans_14 0.74–0.82]
- **Recess outline:** 56 points, spaced by arc length plus curvature, give smooth corners. The sill has flat normals,
  which removes a light wedge at the corner. A dark seal rim runs round every pane. [V: sp_py_24, DSC_1920]
- **Dado:**
  - The facet runs 0.03–0.36 m under a short ledge.
  - The grilles are squarer, 0.33 × 0.28 m, and fill about 85 % of the dado. [V: py_37303, py_37301]
  - Each grille reads as a cut-out: a low lip, horizontal louvres, and faint ribs in the plenum tone.
  - The panel is near-neutral slate.
  - The placards are 100 mm. [V]
- **Electric shades:**
  - 31 pleats of about 14 mm. [V: Room-24 FFT]
  - The pleats taper to flat hems and are masked at the opening's round corners, so they no longer saw-tooth through
    the lining.
  - The valleys are stronger, and the blackout is darker. [V: Room-24 shade/bezel 0.64; now about 0.68]
- **Manual shades:** a 36 mm cream grip band shows when stowed, with the finger scoop underneath. [V: sp_py_24]
- **Door surrounds:**
  - The viewing window is small and high: 0.19 × 0.25 m at 1.52 m. [V position: sans_09 / sp_py_09; A size]
  - It has a lining tunnel and a seal.
  - It is no longer blocked by the upper-wall sweep.
  - The lining is warm cream, and the perimeter seams are light instead of black.
- **Floors:**
  - Door and galley vinyl is dark mottled grey. [V: sans_09 #666268; render #65646c]
  - The F carpet is its own warm red-brown heather. [V: f_17300, MileLion DSC_1917; from_suite]
- **Triangles:** shell meshes went from 458 k to 558 k (+22 %). The main causes are the denser recess ring
  (instanced), the taller PY/Y tubs and the hemmed pleat columns (+48 k across all shade instances, mostly collapsed
  when open). The PY/Y reveals and the grilles moved from instancing into the static shell mesh; the GPU cost is the
  same.

## Not fixed, and why

- **LIGHTING (12_scene.js / 04_shaders.js):** the blue Boarding wash on the upper wall (#7485d6 against the photos' #b3b5c6),
  the hard-edged pale glow rectangles round open windows, and the sun streaks. Filed in `from_shell.md`, and
  accepted by the integrator in `from_integration.md` (Boarding should be white). Also noted: the in-progress shader
  snapshot 44e8c06 paints the lower wall royal blue with the current 12_scene. The w4 shell renders therefore used the
  previous 04_shaders.js.
- **MONUMENTS (10_mono.js door-lining furniture):** the slide bustle is short (0.36 m against about 0.8–0.9 m), and the
  red flag at 1.62 m should be a red arming arc at about 1.15 m. Filed in `from_shell.md`, with measurements.
- **Door-window glass:** the window has no glass disc, because that needs the glass program in 12_scene.js (low).
- **PY/Y opening centred in its tub:** the photos show more tub above the bezel than below. This needs a lower pane
  centre (CAB.win.yc 1.13 → about 1.06, in the shared 05_layout.js) or higher bins. Asked in `questions_shell.md`.
- **Residual blackout moiré at studio distance** (low): each pleat is only two rows, so the stripe cannot be smoothed
  further without a shader LOD.
- **Rater claims set aside:**
  - Rater B's w1 "raise the recess to 0.83 of the pitch" measured 0.73–0.77 in my own crops of y_47303 and sans_14,
    so 0.77 was kept.
  - Rater B's w1 claim that the lighting added the blue to the dado was wrong. A warm test albedo rendered warm
    (#4a4746), so the dado was retuned from the photo instead.

## Sources used

- Official ANA seat pages: ref/ana py_37301/37303, y_47301/47303/47304, c_27312/27316, f_17300/17313.
- Trip reports, downloaded to ref/web (gitignored):
  - SANspotter ANA 777-300ER PY and Y: sans_09, sans_14, sp_py_09/13/24, sp_y_12/45.
  - OMAAT THE Room: Room-24, Room-38.
  - MileLion THE Suite: DSC_1917, DSC_1920.

## Open questions

See `questions_shell.md`:
- A close photo of the door lining; which jamb the viewing window sits by.
- White or blue Boarding light.
- Whether the pane height is sourced.
- Carpet or vinyl at the door cross-aisle.
- The colour of the PY/Y shade.

## Addendum: open questions resolved by sourcing (d72c593, c4f1130)

- **Pane height.** Changed from 1.13 m to 1.02 m, using the Boeing 777-200LR/-300ER Airplane Characteristics for Airport
  Planning, D6-58329-2:
  - Fig. 2.5.1 cross-section: pane 0.82–1.23 m. Scale checked against the 229 in cabin width and the 6.20 m skin.
  - Fig. 2.2.2 side view: 0.97–0.98 m above the door sill.
  - The recesses were re-anchored to the new height. The PY/Y tub now runs 0.53–1.585 m, with 1.4× more tub above the bezel
    than below, as in sans_14. That clears the w2–w4 "opening centred in the tub" issue. The F/J tub top is at 1.48 m.
  - The two window literals in 04_shaders.js follow the change (shared edit).
- **Door viewing window.** Face-on ANA door-lining photos show a tall narrow slot at the window belt, 0.28 m aft of the door
  centre, on a door hinged at its forward edge. The w1 "small high window" had misread the arming-indicator box in a distant
  photo. The window is fixed in 07_shell. A corrected lining spec (handle housing, red arc, arming box, bustle, grab bar) went
  to monuments in from_shell.md.
- **Door floors.** The cross-aisles are dark warm-brown carpet (TPG door 2L, sans_09); the galleys stay vinyl.

## Wave 3 (2026-10-24): w6-w11

| Round | Rater A | Rater B | Mean | Files |
|---|---|---|---|---|
| w5 (wave 2, rated before c5bc132) | 6.6 | 7.5 | 7.05 | shell_w5a / w5b.json |
| w6 (c5bc132 head) | 7.0 | 7.7 | 7.35 | shell_w6a / w6b.json |
| w7 | 7.5 | 8.0 | 7.75 | shell_w7a / w7b.json |
| w8 | 7.8 | 8.2 | 8.0 | shell_w8a / w8b.json |
| w9 | 8.0 | 8.1 | 8.05 | shell_w9a / w9b.json |
| w10 | 8.2 | 8.3 | 8.25 | shell_w10a / w10b.json |
| w11 (final, 6-round cap) | 8.3 | 8.4 | 8.35 | shell_w11a / w11b.json |

No high or medium shell issue is left after w11. The target of 8.5 from both raters was not reached; the remaining items are low (below).
Contact sheet: `shell_before_after.jpg` (w5c = the shell before c5bc132, against w11; own renders only, the cabin columns also carry the
other areas' concurrent changes).

**First job (w5 regression).** The w5 ratings were made on the shell before c5bc132's code, so c5bc132 itself was unrated. Both w6
raters compared w5c (the pre-c5bc132 shell built with the current head) with the c5bc132 head: every change helped except a
slightly over-dark blackout. c5bc132 was kept and the blackout eased in w6. The w4 -> w5 drop came from the w4 post-rating upper-tub
grade, which ran the wrong way (darkest at the recess top), plus stricter raters with new photos; c5bc132 had already reversed it.

**What changed (73b8696, a746e65, 593892d, b5c58b3, 36fe8fd, 42e362c, 03d7532, 220b46f):**
- **Window tub / bowl:** the hood grade is darkest just above the bezel, rising evenly to the lip with a darker band under it (PY/Y
  x0.38, F/J x0.55), fades toward the tub sides, and is baked on a tub floor lofted through 3 segments (no streaks). The top
  extension is eased (no side-wall kink). PY/Y bezel is a raised frame ring with a warm outline. [V: sp_py14, sans_14, tt_window, y_47303]
- **Pane tunnel:** darker lining graded toward the pane, with a dark shade-channel line at its mouth. [V: tt_window 0.58-0.64]
- **Shades:** blackout tone tuned to 0.63-0.65 of the wall with crisper pleats (stripe 0.62, 5 mm zig-zag), closed hem down to the
  sill; stowed manual shade band darker with a deeper grip and a dark finger-scoop line; saturated blue-violet LED ring. [V: omaat
  room24/38, y_47303, sp_py24, tt_window]
- **Floors:** door cross-aisles are grey vinyl between the galley blocks with brown carpet only in the door bays (hue 30); vinyl
  lighter with a cloudy stone mottle (03_tex.js layer 7, shared, vinyl only). [V: sans_09 / sp_py09]
- **Door:** viewing window moved forward to c - 0.30 to match monuments' mirrored lining (lalf_133/134). Jamb stop fittings were
  added in w9 and removed in w10: fr_123806 turned out to be an exterior view.
- **Triangles:** shell meshes 555k -> 648k (+17 %, budget +25 %).

**Hand-offs:** to monuments (arc vs window, w6; since solved by their mirrored lining); to lighting (closed-blackout darkening,
tub-crown darkening from the down-face reveal-glow cut; both largely resolved by 1582aaa, the crown cut should still stop at
dy < 0.44; bowls still render neutral instead of cream).

**Still open (all low):** blackout pleat moire on mid-distance windows (vertex-colour stripe; needs fewer rows or a mip-mapped
layer); sidewall has no fine linen weave (tt_window; a normal-only layer ~0.06); door viewing window slightly narrow (aspect 0.39
vs ~0.52 in lalf_134) with no cream bezel or shade tab; shade-button pill a little small (22x46 vs ~28x52 mm); vinyl faintly cool;
[exterior] a pale bar behind the nearest J pane in s01; [monuments/integration] a cabin window visible beside the door-4 jamb.

**Sources added in wave 3:** SANspotter sans_09 / sp_py09 (door-2 floor), lalf_133 / lalf_134 (Live and Let's Fly, door 2L),
knaviation THE Room (kn_room_8/16), plus the 73 wave-2 photos re-downloaded to ref/web/shell (gitignored).

**Open questions:** `questions_shell.md` (wave 3): an inside photo of an ANA 777 door lining; whether the door-floor split applies at all doors.

## Wave 3c (2026-10-24): w12-w14, confirm and polish

| Round | Rater A | Rater B | Mean | Files |
|---|---|---|---|---|
| w12 (fresh, current head; shell unchanged since 220b46f) | 8.3 | 8.4 | 8.35 | shell_w12a / w12b.json |
| w13 (23c5d63) | 8.4 | 8.5 | 8.45 | shell_w13a / w13b.json |
| w14 (06f9c5a, final, 3-round cap) | 8.4 | 8.5 | 8.45 | shell_w14a / w14b.json |

No high shell issue in any round; the one shell medium (w12a/w13a, blackout pleat character) dropped to low in w14a. Rater B
reached 8.5 in w13 and w14, rater A stayed at 8.4, so the target (both >= 8.5) was not met within the 3-round cap.
Review cameras are now in git (`review/qa/shell_views.js`, 18 views; the w6-w11 camera set had been lost with its scratchpad).
Contact sheet: `shell_before_after_w12-w14.jpg` (own renders only).

**What changed:**
- **Blackout pleats** (23c5d63, 06f9c5a): the valley stripe moved from per-row vertex colour (could not filter: moire on the
  3rd-7th windows) into a mip-mapped synthetic tile, `s_pleat` (layer 32), phase-locked to the closed-shade valleys
  (world y 0.795846 + k 0.0144755, measured in the page). Profile: quick rise, lit crest, long shaded fall. Far shades now
  average to flat taupe (w13b: s05 beat measure 30.5 -> 3.9). Tone 0.61 of the wall, B-R -13. [V: omaat_room24 0.57, -16]
- **Door viewing window:** reveal 0.20 x 0.46 -> 0.26 x 0.64 (bottom 0.69, top 1.33), light rim instead of the dark seal,
  and its own cream shade pulled ~0.13 m down with a dark finger slot. [V ratios: lalf_133 / 134 against the arm-arc box]
- **Grilles:** lit louvres over a darker plenum (louvre cv 0.03 -> 0.14-0.21; py_37303 ~0.45), then eased a step (w14a: field
  0.82 of the dado vs ~0.68).
- **Small:** shade-button pill 25 x 50 mm (w13: 0.088-0.089 of the pane vs 0.084-0.094); vinyl warmer #6f6a69 (B-R -2 vs -3).
- **Post-w14 (verified in renders, not re-rated):** finger slot made visible (it sat behind the shade face; both w14
  raters), door shade #d8d2c6 to separate it from the lining (226 vs 227), window 0.58 -> 0.64 tall, grille #74777e.
- **Triangles:** unchanged in practice (shade geometry the same; door shade + slot are 10 small boxes; no grille geometry
  added), within the 648k wave-3 count.

**Hand-offs to lighting (from_shell.md, wave 3c):** cream finishes render neutral (bowls s 0.005 vs 0.13-0.23, w12a-w14a
medium); grey band under the PY/Y tub lip. Both are lighting code; the shell albedos are already cream.

**Still open (all low):** pleat contrast cv 0.17 vs 0.32-0.35 in omaat_room24 (photo is a crisp two-tone 50/50 pleat; a
flat-band tile would get closer); faint far bands from the zig-zag geometry on s05 windows 4-5; door window still ~1.25 x
the arm-arc box vs ~1.4 (cell top 1.36 limits it); no linen weave on the sidewall (a normal-only layer needs a new shared
layer: the fabric layer's normal strength 0.26 is shared with the seats); vinyl fine speckle about half the photo's
(03_tex.js LAYER_PARAMS 7, shared); light card on the PY/Y tub floor; louvre pitch finer than py_37303.
**Harness note:** studio.js's first shot can fire before the studio scene is up (w14 win_front showed the cabin); re-render it.

## Wave 3d (2026-10-24): w15, confirm

| Round | Rater A | Rater B | Mean | Files |
|---|---|---|---|---|
| w15 (fresh, head 7301cfe; shell = 1523626, the unrated post-w14 fixes) | 8.5 | 8.5 | 8.5 | shell_w15a / w15b.json |

**The shell meets the bar:** both raters score 8.5 and there is no high or medium shell issue, so wave 3d stopped after this one round,
with no code change. Cameras: `review/qa/shell_views.js` (18 views) plus the 22 `test/qa.js` views. The raters were also given the
06f9c5a shell (the build w14 rated) on the current head for the four changed views.
- **Post-w14 fixes confirmed:** the door-shade finger slot now renders (min pixel 23-135 on the shade; w14 194-198). The shade
  separates from the lining and the glass (lining 229 / shade 222 / glass 240). The taller window now rises above the arm-arc housing.
  The darker grille is barely measurable (helps, no regression). Door lining/window detail went from 8.0-8.1 to 8.3 in both ratings.
- **Still open (all low):**
  - The door window is still ~15 % short (1.13x the housing against ~1.36x in lalf_133), and the arm-arc housing overlaps its bezel with no gap (w15b). One fix would cover both: move the window ~0.03-0.04 m away from the housing and raise its top ~0.07 m. That needs the cell top (1.36) raised, and the monuments' housing position checked.
  - Blackout pleat contrast is about half the photo's (cv 0.17 against ~0.33).
  - No linen weave on the sidewall.
  - The vinyl speckle is low (shared LAYER_PARAMS 7).
  - The PY/Y tub floor has a light card.
  - The grille louvre pitch is finer than py_37303.
- **Triangles:** unchanged (648k wave-3 count).
- **Harness:** the head at 3ea3f24 failed to load (`gPlate` was declared twice). 67a7fbc fixed it and made build.py reject duplicate names. lalf_133 / lalf_134 are not
  re-downloadable from the rating files (no URL recorded), so the door proportions rest on the w13-w14 measurements.
- **Lighting hand-offs (from_shell.md, wave 3d):** the door viewing-window glass is flat 240 with no sky detail; the creams are still neutral; the grille under the seats is near black.

## Post-wave polish B (2026-10-25): from_integration items

- Done: THE Room carpet texture (third request). New photo tile `j_carpet` (`test/make_swatches.py`, cut from c_27315's footwell
  carpet: the suggested c_27312 aisle crop is too foreshortened and smeared into streaks), layer 37 (`LAYER.jCarpet`, gain 1.2),
  `carpetJ` #615553. The F and door-bay carpets share the tile (w16a-1). q06 aisle high-pass 0.4-2.0 -> 6.4-6.7 (c_27312 6.2),
  q03 F floor 0.5 -> 8.0 (f_17313 7.2), colours unchanged in mean.
- Not changed: the creams / door glass / dado-grille notes (the integrator kept them in lighting; shell albedos are already cream).
- Ratings: w16 A 8.5 / B 8.5, **w17 A 8.5 / B 8.5, no high / medium: the shell stays at the bar.** Carpet J 8.6-8.8.
- Open (low): F carpet its own coarser tile and a slightly redder tone if the F carpet differs from J (questions_shell.md);
  details in `fixed_polishB.md`. Triangles unchanged.

## Polish E (2026-10-26): pane tint (integration L10 / L11)

- Done: day panes are no longer capped below white. Glass tint [0.93, 0.95, 0.96] -> [0.985, 0.99, 1.0]; q14 pane p50 G 239 -> 249,
  now above the lining, as in c_27316 / y_47300. Only glass pixels change.
- **w18 A 8.5 / B 8.5, no high / medium (w17 8.5 / 8.5): kept.**
- Handed to lighting (from_shell.md): q12 exact-match compensation (optional), and the near grazing pane in q07 is still saturated
  blue. Details: `fixed_polishE.md`. Triangles unchanged.

## Final confirm (2026-10-27): after lighting runs 2-4

| Round | Rater A | Rater B | Mean | Files |
|---|---|---|---|---|
| final (fresh, head 1430d42; 07_shell.js as rated in w18) | 8.4 | 8.5 | 8.45 | shell_final_a / final_b.json |
| final2 (lip takes the wall albedo) | 8.5 | 8.5 | 8.5 | shell_final2_a / final2_b.json |

- **Cause of the drop (final, A 8.4):** lighting only. The 07_shell.js renders against w18 (617dd99, rebuilt) differ only where the
  lighting run's cool wash and tub hue act. That wash cooled the wall and the tub but not the 16 mm roll-in lip, which kept the cream reveal
  albedo, so every window got a beige ring (fA-1, medium; b_jClose lip R-B +5 against wall -11; c_27316 bezel -1 to -7).
- **Fix (shell):** the lip takes the sidewall albedo #e9e7e2 (reveal roughness). The tub, sill and bezel stay cream. Lip pixels only (0-7 %
  per view; q12 includes cloud motion); no seam at the sill; the reveal outline still reads through shading.
- **Confirmed:** both raters 8.5, with no high issue and no shell medium. Otherwise the lighting run moved the shell toward the photos
  (cooler lining, near-white panes, Y carpet blue). Triangles: unchanged (shell meshes 660k with instances, identical before and after).
- **Handed to lighting** (from_shell.md, final confirm): fb-1 medium, the THE Suite bowls take the PY/Y tub-sky hue (s09 B-R +22 against
  f_17313 +1); gate tubHue / tubSky to the PY/Y zones. Lows: q12 surround charcoal, clipped panes, lavender J wall at grazing, washed
  nacelle in ra_jWin, flat door glass.
- **Still open (low, shell, carried):** the door viewing window is short; blackout pleat contrast; no sidewall weave; vinyl speckle;
  the PY/Y tub-floor card; the grille pitch; the F carpet grain and hue.

## Final confirm 2 (2026-10-27): after the lighting final touch

| Round | Rater A | Rater B | Mean | Files |
|---|---|---|---|---|
| confirm2 (fresh, head 8467f01; 07_shell.js unchanged since 6c64e2b) | 8.5 | 8.6 | 8.55 | shell_confirm2_a / confirm2_b.json |

- **Shell confirmed:** both raters score 8.5 or above, with no high or medium issue. No code change. Since 6c64e2b only `04_shaders.js` and
  `12_scene.js` changed. Renders of 6c64e2b (git worktree) were diffed against the head: every change is lighting, and it moves the shell toward the photos.
- **Routed lighting items that now read fixed:**
  - fb-1, the THE Suite bowls' tub-sky hue: s09 bowl B-R +22 -> -3/-4, q03 +23 -> -2; f_17313 ~0.
  - fA-1 and its follow-up, the cream lip ring: still gone (s09 lip B-R -2 against the wall's +2).
  - fA-2, the charcoal q12 surround: L71 -> 103-104.
  - fA-4 / fb-2, the lavender THE Room wall at grazing: B-R reduced. A reads +12 -> +7; B reads b_jClose +27 -> +20.
- **Not fixed (accepted, low):** fA-3 clipped panes, fb-3 the washed nacelle in ra_jWin, fb-4 the flat door glass. B finds the glass now fully
  clipped (sd 2.4 -> 1.1).
- **New lows (lighting, optional):**
  - The q12 reveal is about 8-15 L over the photo (L118-125 against L104-110); lookOut 0.87 -> 0.86 or cap beltK on the near reveal.
  - THE Suite bowls are no lighter than the wall (A: 222 vs 224; f_17313 239 vs 226) and faintly warm (B-R -3).
  - The THE Room wall at grazing reads B-R +20 against c_27316 ~+10 (B).
- **Carried shell lows unchanged:** door window short, pleat contrast, no sidewall weave, vinyl speckle, PY/Y tub-floor card, grille pitch,
  F carpet grain and hue. Triangles unchanged.

## Integration lows (confirm 3, 2026-10-27, commit 87a5f4c)

- **Item:** L16 integration low, bright 1 px specks along the sidewall panel joint beside the q12 window.
- **Cause (found by elimination):** not the seam strip. With `wallSeamGeo` removed the specks stay, and with the seam
  tinted red they sit beside it. Each window cell spans a full 21 in bay (hw = pitch / 2), so cell edges fall at mid-pier,
  under the joint. The recess rings' right and left side columns carry different v rows (J: 19 / 19 at different heights,
  e.g. -0.48114 vs -0.4912; PY/Y: 17 vs 18), and the fillers use a third set. The shared edges therefore have T-junctions,
  which open hairline cracks on the curved lining, and the sky behind showed through.
- **Fix:** `wallBackGeo` adds a lining-coloured (MAT.sidewall) ribbon 16 mm wide, 2 mm behind the lining, over
  v 0.48-1.60 at every cell edge in the seat runs. No visible surface moves; the joint strip is unchanged.
- **Speck rows** (q12 box x 95-145, y 150-470, > median + 25): DPR 1 base 13-17 -> 0 (two base renders gave 16 and 13,
  rater A 17); DPR 2 head 0 (rater A: 0 at +10 too).
- **Pixel diff base -> head (DPR 1, > 8 levels):** q01 0.000 %, q03 0.002 %, q06 0.003 %, q07 0.002 %, q11 0, q13 0,
  q14 0.001 %, q15 0.002 %, q16 0.024 %, q17 0.029 %, all isolated crack pixels on other cell edges (sky specks gone there
  too). q12 2.3 %, of which all but the joint is the animated clouds (baseline vs baseline re-render: 3.3 %).
- **Score:** one rater, as the diff stayed under 0.5 % outside the defect: rater A **8.6** (confirm2 8.5), no high or
  medium; all earlier mediums still fixed (`shell_confirm3_a.json`). New low c3A-1: one q07 pixel 18 L darker, not visible.
- **Triangles:** shell mesh +7.5 k (20 rows x 2 tris per edge; the 40-row first build was +15 k).

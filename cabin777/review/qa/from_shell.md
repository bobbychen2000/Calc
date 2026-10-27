# Items from the shell worker

## To lighting (`src/12_scene.js`, `src/04_shaders.js`)

1. **Saturated blue wash over the upper sidewall and the door linings in the default Boarding mood** (shell_w1a high, shell_w1b).
   - Evidence: upper wall in the renders #7485d6 (s03), #7282ce (s01), #7081d5 (s08); saturation 0.35–0.47. A hard fade line
     sits at mid-window (s05, column 400: luminance 141 → 216 over 40 px). Photos at the same place: y_47303 #b3b5c6,
     py_37301 #a9b3c5, sans_14 (SANspotter, real boarding photo at HND) #f6f4eb; saturation ≤ 0.16. The blue band
     is only in the in-flight mood photos (sans_36, sans_39) and one boarding shot (sp_y_12), and there it stays a narrow
     band under the bins, not a wash down to the windows.
   - Fix: `MOODS.boarding.sideLed` → about `[0.10, 0.10, 0.11]` (near-white). Keep a blue band for Cruise only, lower,
     around `[0.03, 0.03, 0.22]`, and limit it to about 0.15 m below the lens. Keep the band term off the door
     linings (MAT.door faces).
2. **Hard-edged pale rectangle round each open window on the sidewall** (both raters).
   - Evidence: s05 row 160: #9ea9db → #c3cbe5 within ~20 px at x 380–420, and back at x 820–840; the same block in s01 and s08.
     No photo shows it.
   - Fix: feather the window LUT in z (linear filtering, or a cosine falloff over ~0.08 m past each window's ±0.22 m).
     Alternatively mask the reveal glow with the recess outline. `sdRecess(px, py, rec)` in 07_shell.js now takes the
     recess (REC for F/J, REC_Y for PY/Y).
3. **Sun patches are thin streaks with hard stair-step edges, not pane-sized pools** (low; also from_suite item 2).
   - Evidence: q14 seat backs show 20–30 px bands; q07 shows a diagonal band across the ash panel.
   - The stowed electric shades are already collapsed to zero size (07_shell `shadeMats`), so the stowed shades don't
     cast them. Check the sun LUT and shadow term against the pane rectangle (W.w × W.h = 0.254 × 0.381).

## To monuments (`src/10_mono.js`, Type A door linings)

The door surround and its viewing window are in 07_shell.js. The window is now small and high: 0.19 × 0.25 m centred
at 1.52 m, following sp_py_09 and sans_09, where a dark square sits at head height above the red arming arc. The lining
colours (`MAT.door`, `MAT.doorGap`, `MAT.slide`, `MAT.handleRed`) are also in 07_shell.js; the door-gap outline is now a
light shadowed seam (#8f8a82) instead of black. The lining furniture is in 10_mono.js, and these items there disagree with
sans_09 / sp_py_09 (ref/web/shell/sans_09.jpg, the door at L2 seen across the galley, an FA of ~1.6 m for scale):
1. **Slide bustle too small.** The photo shows a full-width, off-white box from the floor to about 0.80 m with a ledge
   on top. The model has `gRBox(0.10, 0.36, 0.92)` at v 0.30. Fix: `gRBox(0.16, 0.78, 0.98, 0.05, 2)` centred at v 0.41,
   plus a 0.03 m ledge at 0.80.
2. **Red arming indicator.** The photo shows a red arc (a semicircle about 0.2 m across) at about 1.1–1.3 m on the
   door's centre line. The model has a small red block at v 1.62, z c − 0.25, which now sits beside the viewing window.
   Fix: a red half-ring (`gTube` half-circle, r 0.10 m) at v 1.15 about z = c.
3. **Door gap outline.** Now light (see above). If it still reads as a drawn line, narrow the strips from 12 mm to 5 mm and
   inset them 2 mm.

## To lighting: in-progress shader snapshot 44e8c06 (FYI)

- With 04_shaders.js from 44e8c06 and the current 12_scene.js, the lower sidewall below the windows renders a saturated
  royal blue (s03_yClose, s05_jShades: #1a2fa8-ish from the dado top up to the window sills). The upper wall turns pale
  lilac. `u_lowTint` / `u_bandCut` / `u_vault` look unset by 12_scene.js (zero), which would explain it. Shell w4 renders
  were made with the previous 04_shaders.js so that the shell is rated on its own.

## To monuments: CORRECTED Type A door lining (supersedes items 1-2 above, which were based on a misread distant photo)

Sources (ref/web/door/, gitignored):
- `yt_vEERVra5lKs.jpg`: ANA 777 door lining, face-on (YouTube vEERVra5lKs).
- `yt_R7MKjYHQ1Uk.jpg`, `yt_YJFoMH98yHo.jpg`: close-ups.
- `tpg_ANA-777-The-Room-plane-door_58.jpg`: ANA 777-300ER door 2L, open (TPG).
- A 777 door trainer.

The small square high on the forward side in sans_09 is the **arming-indicator box**, not the viewing window. The door hinges on
its **forward** edge on both sides. Below, "fwd" means the forward jamb (z = c - 0.53) and heights are above the floor.

1. **Viewing window (07_shell, done).** A tall narrow slot, 0.20 × 0.46 m reveal with glass ~0.14 × 0.32 m, centred at
   z = c + 0.28 (aft of centre) and y 0.98.
   - Please move the lining's vertical lever at z = c + 0.26: it now sits in front of the window.
2. **Handle housing.** A cream box across the upper-middle of the door, ~0.79 m wide (z from c - 0.48 to c + 0.27, so its aft end
   just overlaps the window's forward edge), y 0.85–1.28, standing ~0.15 m proud. It has a small oval recess at its fwd upper corner.
   - In it sits a horizontal pocket ~0.33 × 0.14 m with a brushed-aluminium grip block, 0.22 × 0.12 m, centred at z c - 0.26, y 0.97.
3. **Red arc** on the housing face, painted and ~25 mm wide: radius 0.29 m, centred at z c - 0.10, y 0.93, so its top is at ~1.22.
   - It runs from a red stop bar (0.035 × 0.095) beside the grip, up over the top, to an arrowhead on the aft side, with a red
     "開 OPEN" label at the lower aft end. This replaces the arc at 1.15 m on the centre line.
4. **Arming-indicator box.** A recessed window ~0.19 wide × 0.27 tall in the **upper fwd corner**, centred at z c - 0.41,
   y 1.54. Inside: a pictogram strip, a lever with a green/red band, and a red flag. Placards sit just aft at 1.45–1.55.
   - Remove the old red flag at 1.62 m.
5. **Slide bustle.** Nearly full width (~1.0 m), top at ~0.75 m, ~0.25 m deep, with a sloped top and a 0.05 m rounded front
   edge, a rib round the lower front at ~0.40, and the lining colour. A black gauge window (~0.10 m) sits at the aft end of the
   top face.
6. **Assist grab bar.** Horizontal, brushed aluminium, 0.51 m long, Ø 0.04 m on 0.08 m standoffs, centre y 0.70, running from
   z c - 0.50 to ~c + 0.01. A red-orange strap (0.13 × 0.14 m) hangs from its forward half.
7. **Jamb assist handles.** Vertical grips in recessed pockets, ~0.25 m long, centred at y ~1.45 on both jamb liners. There is a
   small EXIT placard on the aft jamb at ~1.05 m. The upper door is plain, with a horizontal seam at ~1.73 m.

Floor: the door cross-aisles are now carpet (MAT.doorCarpet, dark warm brown, from the TPG door-2L photo and sans_09). The
galley and lav floors stay vinyl.

## To all areas: window height changed (d72c593)

`CAB.win.yc` is now 1.02 (was 1.13), from Boeing's ACAPS cross-section (D6-58329-2 fig. 2.5.1): the pane runs 0.82–1.23 m. The two
window literals in 04_shaders.js (the sun LUT band and the reveal glow) were changed from 1.13 to 1.02 to match; lighting,
please keep them in step. Anything placed relative to the window, such as pod consoles, window-side lamps or look-out
cameras, should be checked. q07 and q12 look fine.
## Wave 2 (w5)

### To lighting (`src/04_shaders.js`): the reveal glow flattens the upper window tub
- **Evidence:** w5 raters (shell_w5a/b) and every real photo (sans_14, tt_window, sp_py14, MileLion DSC_1920) show the tub
  darkest just above the opening, at 0.65-0.78 of the pier. In the render (s03_yClose, column x520) the upper tub stays at
  0.90-0.92 of the pier from lip to opening. The shell now grades the tub in vertex colour down to x0.60 just above the
  opening, but that moves the screen value only from 209 to 203 of 255. The `reveal` term (04_shaders ~l.192, |y - 1.13| < 0.2-0.34)
  lights the whole tub (the band is now centred on 1.02), and at this level `aces` compresses whites.
- **Fix:** weight `reveal` by how much the face looks at the pane: fade it on down-facing faces above the opening, e.g.
  `reveal *= mix(1.0, 0.35, smoothstep(0.24, 0.40, v_wpos.y - 1.02) * down)`. Or narrow it to `smoothstep(0.14, 0.24, ...)`,
  so it lights the tunnel and the sill but not the upper tub.

## Wave 3 (w6)

### To monuments (`src/10_mono.js`): the red arming arc runs over the door viewing window
- **Evidence:** shell_w6a (rater A). The window glass sits at z = c + 0.28 (0.18-0.38), y 0.75-1.21 (07_shell, from the face-on ANA
  door-lining frame). The arc arrowhead is at about c + 0.25, y 1.10 (10_mono ~l.757-761), so it overlaps the window's forward edge.
- **Fix:** end the arc forward of c + 0.15 (the corrected spec above: radius 0.29 centred at c - 0.10, top at ~1.22), so the
  arrowhead sits on the housing face, clear of the window.

## Wave 3 (w10)

### To lighting: the closed blackout went darker with no shell change (shell_w10a medium)
- **Evidence:** b_jClose / s05 closed blackout 0.45 of the wall in w10 against 0.64 in w9 (omaat_room24 0.65); the blackout albedo
  (#aaa498) and the stripe did not change between the two rounds. The lighting snapshots between them (282136c / 9f2d20e) are the
  likely cause, perhaps the window-glow or sun term that lit the back of the shade. The bowls also render dead neutral (s 0.005-0.014
  against the photos' cream 0.13).
- **Ask:** keep closed electric shades at about 0.6 of the wall; if the darker look is intended, tell shell and the blackout
  albedo will go to about #c8c1b3.

### To lighting (`src/04_shaders.js` ~l.264): the down-face reveal-glow cut darkens the PY/Y tub crowns (shell_w10b medium)
- **Evidence:** the x0.35 cut on downward-facing faces above the window also hits the round top of the tall PY/Y tub (0.36-0.56 m
  above the pane centre). It renders at 0.46 of the wall in q14, s02, s08 and b_pyClose, where sp_py14 / sans_14 show the crown
  bright (~1.0 of the pier; the darkest part is just above the bezel, which the shell already grades in vertex colour). There is
  a thin dark line on the F/J bowl tops too.
- **Fix:** fade the cut back out over 0.36-0.44 m above the window centre, e.g.
  `* mix(1.0, 0.35, down * smoothstep(0.24, 0.30, dy) * (1.0 - smoothstep(0.36, 0.44, dy)))` with dy = v_wpos.y - 1.02.

## Wave 3c (w12)

### To lighting: cream finishes render neutral grey-white (shell_w12a medium, w12b low)
- Evidence: the F/J bowl renders s 0.005 (w11 0.013) and the door lining B/R 0.98, from cream albedos `MAT.reveal` #ece4d5 and
  `MAT.door` #e4dccb. The real photos show s 0.13 (omaat_room24 bowl), s 0.23 (tt_window) and door-lining B/R 0.93 (lalf_134).
  The shell albedos are already cream, so the neutralisation happens in the boarding light colour or in the tone map's
  highlight desaturation.
- Fix (lighting's call): warm the boarding / white cabin light slightly, or ease the highlight desaturation so that #ece4d5
  lands at s 0.08-0.10. Bowls, bezels, door linings and the wall would all move toward the photos' cream.

### To lighting (`04_shaders.js`, down-face reveal-glow cut): soft grey band under the PY/Y tub lip (w12a/b low)
- Evidence: ra_yWin / s02 / s08: the crown runs at 0.55-0.61 of the pier, against ~0.85 in sp_py14 (hairline rim only).
- Fix, as in w10b / w11b: fade the cut back out above dy ~0.40 (where the tub top meets the wall).

## Wave 3d (w15)

### To lighting: door viewing-window glass renders flat white, and the earlier items are still open (w15a / w15b low)
- **Door glass:** in b_doorWin / s06 the door viewing-window glass reads a flat 240 with no sky gradient or detail. The cabin panes
  show sky, and lalf_133 shows a bloomed but graded pane. The door glass is the cabin pane mapped into the door seal
  (`doorGlass` instances in 07_shell.js), so it is probably the window-glow / exposure term saturating. Ask: let it keep some sky
  gradient.
- **Still open:** the creams render neutral (door shade #d8d2c6 lands at 222,222,221); the dado grille under the seats is near black in
  b_dadoY2 (mean ~21); there is a grey band under the PY/Y tub lip.

## Polish E (2026-10-26): to lighting, after the pane tint change (shell w18)

### q12 look-out exact match (optional, low)
- The glass tint is now [0.985, 0.99, 1.0] (was [0.93, 0.95, 0.96]). The view through the pane in q12 rose by a pure ~4 %
  (+1.7-2.8 L* on the wing; frame mean +1.0). Both w18 raters judged q12 no worse.
- **If q12 must match the old frame exactly:** in `12_scene.js` l.828, let winExp ease to 0.955 instead of 1 at the window, e.g.
  multiply by `1 - 0.045 * clamp((Math.abs(cam.pos[0]) - 2.0) / 0.45, 0, 1)`. Cabin views (|x| < 2.0) are untouched.

### Near pane still saturated blue in seat views (low, both w18 raters)
- In q07 the near grazing pane reads (154, 192, 230), and in ra_jWin the left pane also stays blue. In c_27316 the same window
  is blown white. The PY/Y panes still sit slightly cool (R about 6 below B) and rarely reach 250 in all channels (0.1-16 % vs 40-89 %
  in the photos).
- The shell tint can't go higher (it is already about 1.0). This needs the sky / winExp side, or the u_glassT idea from L10
  step 2: transmittance applied before aces(), so a bright day sky can clip to white.

## Final confirm (2026-10-27): to lighting, after lighting runs 2-4 (head 1430d42)

Shell ratings on 1430d42: A 8.4 / B 8.5 (`shell_final_a/b.json`; w18 was 8.5 / 8.5 on the same 07_shell.js). Every render change
since w18 comes from the lighting run. Most of it moved the shell toward the photos (cooler lining, near-white panes, Y carpet blue).
Two items are lighting's:

### fb-1 (medium, rater B): THE Suite bowls take the PY/Y tub-sky hue
- s09_fWin bowl 210/213/219 (B-R +9) in w18 -> 191/200/213 (+22) on 1430d42; q03 +23. The bowl is now no lighter than the wall. In
  f_17313 the F bowl is neutral (+1) and lighter than the wall (238 vs 225). THE Room bowls are fine (+5).
- Fix: gate `tubLow` / `crownW`'s sky hue (`u_tubHue`, `u_tubSky`, 04_shaders.js l.639-646) to the PY/Y zones, e.g. multiply by the
  seat-zone step already used for `seatC` (`step(u_sLowZ, v_wpos.z)`), or add an F-zone fade at z < ~13.
- Shell can't fix this without cooling the cream reveal, which would make it worse.

### fA-1 (medium, rater A): warm bezel lip against the cooled wall: fixed in shell, follow-up optional
- The new cool wash (coolW) and tub hue cool the wall and the tub, but the 16 mm roll-in lip kept the cream reveal albedo, so every
  F/J window got a beige outline (b_jClose lip R-B +5/+7 vs wall -11; c_27316 bezel -1..-7).
- Shell fix: the lip now takes the wall albedo (`07_shell.js`, final confirm). Optional on your side: run the coolW / tub hue
  transition 2-3 cm past the tub edge (`recd` smoothstep xLin+0.004..0.02), so the cooled tub and the wall blend without a step.

### Low (both raters)
- fA-2: q12 window surround round the wing view went charcoal (~121-125 -> 68-71).
- fA-3: clipped panes lose cloud detail (s09 pane spread 5.1 -> 2.0). The photos are blown too: a trade-off.
- fA-4 / fb-2: the J wall at grazing reads lavender (b_jClose R-B -23, s 9.7 % vs c_27316 -12, 5.8 %; s05 wall B-R +25 beside a
  neutral bowl). Ease the cool wash about a third at grazing.
- fb-3: the ra_jWin look-out washes out the GE90 nacelle (240/250/255), while the q07 near pane stays blue (192/203/215).
- fb-4 (carried): door viewing-window glass is flat (217/216/214), with no sky detail.

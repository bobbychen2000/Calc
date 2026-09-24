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

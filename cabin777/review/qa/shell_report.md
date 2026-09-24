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

# >>> NOTE TO ALL AREAS (wave 3, 2026-10-24 16:00 UTC) - lighting is mid-iteration <<<

The lighting loop's round-1 fixer is still editing `04_shaders.js` / `12_scene.js`. Commits 282136c and 9f2d20e are
snapshots of its unfinished work. They raise the exposure (boarding 1.38, cruise 1.12) and add a crevice term
(`amb *= mix(0.4, 1.0, smoothstep(0.06, 0.5, ao))`) plus a lower AO weight on faces that do not look up. Together these
darken the dense economy / PY seat block (from_econ w10, HIGH: q15 fabric L -36 %, q18 hood -31 %).
- **Do not retune your SEATMAT colours or fabric gains to compensate.** The lighting loop will fix the regression in the
  lighting code; from_econ w10 is queued as high for its next round.
- If your rating round falls between now and the next lighting commit, note it in your report and judge geometry and
  materials in the studio renders, which are unaffected.

# >>> CORRECTION FOR ROOM (wave 2) - READ FIRST <<<

**Restore the boarding bundle that e45db15 removed.** The line "pillows only, no wrapped duvet" in the first wave-2 brief was an
integrator default. It was never the user's decision, and it was withdrawn in c308f51. The user asked for judgement calls,
and the rule is that real in-flight photos win. tpg_31 and tpg_42 show the folded duvet and pad in clear plastic under
the pillows at boarding, so keep `roomBundle` (5a42e29) in the boarding (non-bed) state. The current `WORKER_BRIEF.md`
says the same.

# Items from lighting + integration

## To suite (replies to `questions_suite.md`)

1. **Centre-suite width: keep 1.10 m.**
   - 14 CFR 25.815 requires passenger aisles of at least 20 in (0.508 m) from 25 in above the floor, on aircraft with 20 or more passenger seats. [V]
   - The suite walls stand 1.30 m tall, so the whole aisle height counts.
   - Widening the centre suites to 1.20 m would leave 0.46 m aisles, which the rule does not allow. [D]
   - Keep the pill-mirror pier as the slim strip, or shift its visible face inboard within the 1.10 m.
2. **Divider toggle.** Yes, please keep `suiteUnit({divider: 1})` for the raised panel. The integrator will add a raise/lower control to the seat card in `13_app.js`. Default stays lowered.
3. **Closed doors.** Please add a `doors` option to `suiteUnit`, with 0 = parked open (default) and 1 = closed leaf positions. Keep it geometry-only, so the integrator can wire an open/close control on the seat card in `13_app.js`.

## To lighting (the integrator's own fixer)

- **Blue sidewall band, depending on mood.**
  - `boarding` is the default mood and should match ANA's official photos (c_27312, y_47300, py_37302), which show white sidewalls and window belt with no blue band. [V]
  - In-flight trip photos show the saturated blue band. These are `cruise` and night scenes, so the band belongs to `cruise` and `sleep`. [V]
  - Keep `boarding` `sideLed` near-white.
- **Sun patches on beds and seats.** q04 shows hard white ovals from the window sun on the Suite bed. Soften their edges and cap the intensity so the fabric keeps its texture. Seen in the q04 before/after renders.

## To room (wave 2)

- The wave-1 room session (5a42e29) recorded evidence-based decisions in `questions_room.md`, including the wrapped duvet and pad bundle at boarding from tpg_31/42. Keep them. They supersede the "no wrapped duvet" line in the first version of the wave-2 brief, which is now corrected.

## To suite and room (seat-card toggles are wired: f2bfdf2)

- `13_app.js` now builds `seatVariantGeo(meshKey, {bed, doors, divider})` (`09_seats.js`) for the occupied unit.
  - Room `doors` works already (65166ef).
  - Suite `divider` works. When raised, the neighbouring centre suite is redrawn too.
  - Suite `doors`: the "Close door" button is already there. Implement `suiteUnit({doors: 1})` and it takes effect with no other change.
  - Combinations the viewer can reach: `bed` + `doors`, and `divider` with either (centre suites). Please make sure they combine cleanly.
- The prebuilt `bed_*` meshes are gone. Bed geometry now comes from the same variant path (`{bed: true}`), so render your bed mode via `seatVariantGeo` or the `UNITS` entries.

# Items from the lighting fixer (QA r1, light group)

The r1 light changes (04_shaders.js / 12_scene.js) are: boarding exposure 1.38 / cruise 1.12 with a black-only toe, a
crevice term limited to low pockets (below ~0.75 m, not up-facing, not the sidewall), the lens band / bin shade only in
the seat zones (none over doors, galleys, lavs), cove-LED specular line lights, a superellipse sun gate per pane, a sun
soft-clip on pale faces, warm-dim amber phase at seat level, a neutral night. Re-check your area in the renders after
this commit, but judge material albedos in the studio first.

## To room (`09_seats.js` SEATMAT, shared one-line keys)
- **Charcoal shells read flat matte; no sheen line on the cap rims** (lighting r1 medium). Evidence: c_27312 bright sheen
  lines along the rounded charcoal cap rims and monitor-shell edges (shell back #5c626a, dark side #4e4f55); tlfl_IMG_9217
  specular streaks on the cap rails; q06 shell_top_L (150-180, 330-345) #626874, cap #474c56 with no highlight.
  The cove LED line lights are now in the interior specular (mainFS `coveSpec`), but at r 0.45-0.46 the lobe is broad.
  **Fix:** `jShell` r 0.46 -> 0.34 and `jCap` r 0.45 -> 0.34 (satin). Target: shell top edges about 1.3x the face.

## To suite (`09_seats.js` SEATMAT / `09d_suite.js`)
- **`fShell` r 0.45 -> 0.34** for the same sheen lines (lighting r1 medium; omaat_f2 / f5 shell rims).
- **Bed sheet / duvet too bright under cabin light** (lighting r1 low). q04 bed shade (520-560, 320-360) #e0dfdd L224,
  sun patch L246; omaat_f59 (real THE Suite bed) #d8bfa2 L194. The shader now soft-clips the sun on pale faces, but at L224
  without sun the ACES shoulder leaves no room for a patch. **Fix:** sheet albedo about #d4cfc6 (renders ~L200-205),
  duvet a step darker; the patch then reads as soft light, not clipped white.

## To econ (`09_seats.js` SEATMAT)
- **`yShell` r 0.42 -> 0.34** (satin white shells and armrests; lighting r1 medium). Evidence: y_47303 armrest tops p50
  189-194, p99 248-251 (glossy streaks); y_47300 satin armrests. The cove specular needs the narrower lobe to show.
- **yCover (headrest flap) lighter** (integration r1 medium). Evidence: y_47301 flaps (460-580, 400-520) #3a3e5d L63,
  y_47300 #393e5b L63, y_47306 flap face #445072 L80 vs q16 flaps #232a48 L42 (rated on `#343a52`; econ w7 has since set
  `#474c5e`). **Fix:** re-measure q16 flaps after this lighting commit; target face about #3a4060 (L60-65), still darker
  than the Y fabric mean. Note from_econ w10 (the economy darkening from the snapshot commits) is addressed in the
  lighting code (low-face-only AO weight / crevice), so do not retune the fabrics to the snapshot renders.

## To ceiling/bins (`08_bins.js`)
- **Z-fight dashes on the lower lip of an outboard bin near door 3** (integration r1 low). Evidence:
  scratchpad/integ/shots3/w04_d3_cross.png (bin right, y ~185 px), crops w04_bin.png / z04_psu.png: irregular dark dashes
  along ~0.6 m of the lip, flicker while walking; c_27312 / y_47300 lips are clean. **Fix:** find the strip whose end
  coincides with the door-3 zone boundary (seamR / band / lens on the outboard module ending at z ~32.0-33.3) and offset it
  1.5 mm off the body along the face normal, or shorten it 2 cm at the zone end; re-render z04 at DPR 2.

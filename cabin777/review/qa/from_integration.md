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

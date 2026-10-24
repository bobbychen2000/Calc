# Open questions from the PY worker (not blocking)

1. **Seat width and console width.** ANA gives a pitch of 38 in and a width of "about 19 in". The real console face
   carries two universal sockets side by side (alv_08), and both raters measured it at 0.13-0.15 m. With the
   layout's seat spacing of 0.5525 m (`05_layout` pySp), the model compromises: a 0.12 m console and a 0.43 m cushion.
   Do you know the real armrest-to-armrest width, or the seat spacing from an aeroLOPA drawing?
2. **Fabric.** ANA's official photos (py_37301/03/05) show mostly the dash weave. Real trip-report photos
   (SANspotter 2023, JA793A; The Alviator 2026) show the same cloth as a large-repeat mix: cream streak weave, speckle
   chips, and lighter "cloud" zones. The model uses a 0.163 m synthesised tile: crisp streaks and chips, with the
   mottling taken from the py_37305 photo. Is that close enough, or should a larger repeat (about 0.33 m, costing page
   size) carry the cloud zones?
3. **Bulkhead row 25.** Real photos (alv_14/15, san_03, py_37303) show monitors mounted on the bulkhead wall, so the
   row-25 seats carry no seatback screen. The model matches this (`noScreen`); please confirm if you know otherwise.

## Wave 3 (w5, not blocking)

4. **Petal fabric on the upper back?** In py_37302 the petal fleck seems to continue from the wings onto the top of the
   back. The model keeps the dash grid on the whole back and the petals on the wings only (py_37301 / 37305). Do you
   know otherwise?
5. **Gooseneck position.** The model now shows it stowed, hanging by the shell flank (py_37301 / 37303, san_26), not
   pulled out as in the py_37305 close-up.
6. **Literature pocket.** ANA's photos never show the lower seat back, so the model follows the 2023 SANspotter photos
   (san_20 / san_26): a moulded bucket with a mesh band across its lower front.
7. **Gooseneck (resolved by evidence, w10):** every stowed view (py_37301 / 37302 / 37303, san_26) shows the heads
   near-vertical and apart. py_37305 looks like a pulled-out pose, so the model follows the stowed views.
8. **Flap aspect:** py_37301 / 37302 give a visible h/w of about 0.90 and py_37305 about 1.25 (perhaps a raised
   headrest). The model sits in between (~1.0 head-on).
9. **Back cloth in py_37301 vs py_37302:** 37301 reads as a blocky brick mosaic, 37302's foreground seat as sparse cream
   flecks, with petals over the upper back. Is row 25 dressed differently? The model uses the 37301 / 37305 cloth everywhere.

## Wave 3b (w11, not blocking)

10. **Two seat trims (answers 4 and 9 by evidence).** ANA dresses PY in two trims: A has a dash-weave back and cushion
    with petal ears, and B has a petal back and cushion with dash-weave ears. py_37302's foreground seat (a centre-block
    aisle seat) is B, and so is SANspotter's 26G (san_12) next to a trim-A 26F. Both seats of the py_37301 window pair are A.
    The model puts B on the centre block's aisle seats D / G and A everywhere else. If you know the real pattern (per row,
    per seat letter or random), say so; it is one line in `pyUnit`.
11. **Literature pocket.** It now follows san_26, an open tray in a dark recess with a smile-shaped grey rim and mesh
    across the lower bulge. Is it the same on every row? Row 25 faces the bulkhead, so it has none.

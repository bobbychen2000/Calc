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

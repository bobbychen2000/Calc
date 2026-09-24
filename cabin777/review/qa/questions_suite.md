# Questions from the suite worker (none blocking)

1. **Centre-suite width (1D/1G/2D/2G).** In the real centre suites a full pill-mirror pier sits beside the 43 in screen
   (up_forward_look '1D', omaat_f3, omaat_f5). The model's 1.10 m centre suite (the layout in `05_layout.js`, which the suite
   worker does not own) leaves only about 0.05 m for that pier, so the mirror is a thin strip there. The window suites (1.24 m)
   now match omaat_f10. Is there a source for the F suite widths? Widening the centre suites to about 1.20 m would narrow
   each aisle from about 0.51 m to about 0.46 m.
2. **Centre divider default.** It is now modelled lowered, as in most in-flight photos (omaat_f1/f3/f5, tlfl_21).
   `suiteUnit({divider: 1})` gives the raised panel of up_privacy_wall / f_17314. Would you like a raise/lower toggle on the
   seat card? That lives in 13_app.js, which belongs to the integrator.
3. **Closed doors.** The doors are always parked open, as when boarding (omaat_f7). Closed doors (pb_20, omaat_f49, roame_20)
   would need an animated leaf mesh plus a seat-card toggle in 13_app.js. Is that wanted?
4. **Wood between the centre screens.** omaat_f3 / f4 show dark wood between the D and G screens. It is now modelled as one
   solid wedge (each centre unit builds half). If you know it is two separate angled panels, or one flat panel, say so.

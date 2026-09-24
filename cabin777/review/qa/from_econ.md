# From econ (09a_econ.js) to other areas

## To lighting / integration (04_shaders.js, 12_scene.js)
- **Economy rear shells are under-lit in the seated view** (econ w2 rater B). In q18_seat35C the off-white Recaro shells
  render ~30 % darker than in y_47305 / sanspotter 15 (shell #c8c9cb-ish in the photo under cabin light). Suggested fix: cap
  the AO-volume darkening on seat-back rear faces (e.g. clamp ao >= 0.75 for the `yShell` material) or add ~15 % fill from
  the PSU downlights.
- **Hairline light streak across a seat back in q15_econFronts** (thin bright diagonal line on the right-hand foreground
  seat). It looks like a window sun-shaft projection: clamp the shafts to the floor and sidewall, or soften their edge
  (smoothstep width ~0.05 m).
- **w4 re-measure (still open):** the q18 hood reads L 136 against 193 in y_47305, and the tray reads L 132 against
  195-208 in sanspotter 20, so the seat backs are ~30 % too dark from a seat (econ_w4b.json). The seat materials already
  match the photo albedos (`yShell` #d9dbde, `yTray` #cfd2d6), so the gap is shading/AO.
- **Plastic grain (03_tex.js layer 4, shared):** in harsh light the off-white shells read slightly as stucco. A ~40 %
  lower normal amplitude on layer 4 would fix it, but it affects every area, so I left it to the integrator.

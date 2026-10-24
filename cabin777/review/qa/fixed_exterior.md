# Exterior: hand-offs addressed to exterior, fixed

- from_integration "To exterior" (from_exterior 10, sun-side cowl near white): cowl r 0.3 -> 0.5 and a day-sun-facing bake
  (x0.7 at full n.L) on the nacelle: w11K sun side L227 -> L202, lower cowl L208 -> L168, while the 11A shade side keeps
  L159 / L142 (LALF _136 L133-148). A flat albedo cut was tried first and rejected: it took the 11A shade side to L89-103.
  done (w12 fixes commit, see git log "cabin777 exterior w12 fixes")
- from_integration (r2, FYI): drop the w26K / w30K `[-0.06, 0.12, -0.06]` offsets in `exterior_views.js` now that `lookOut` puts
  the eye at the glass. done (40b5b85)

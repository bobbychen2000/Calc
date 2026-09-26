# Request from the bridges workflow to the aircraft workflow, 26 Sep 2026

From: owner of `js/live/gates.js` bridge geometry. `doorOf()` (your docking math for doors 1 and 2) is unchanged; I added
`which === 3` for the A380 upper-deck bridges (`bridges_upper` of A6 / A11 / G13).

## `js/aircraft/fit.js` / `types.js`: A380 upper-deck door U1L fields

Please add, for `a388`, `T.dockX3` (U1L centre station from the nose, of the rendered model), `T.dockSill3` (U1L sill)
and `T.dockHW3` (rendered fuselage half width at U1L mid height). Until then gates.js uses the published values and an
ellipse estimate:

- Airbus A380 Aircraft Characteristics - Airport and Maintenance Planning (Dec 01/25, cached
  `refs/cache/acap/airbus_AC_A380_20251201.pdf`): U1L at 20.94 m from the nose (FIGURE-2-7-0-991-002, Door Location
  Sheet 2; M1L 6.32 m and M2L 16.50 m on the same sheet match types.js `doors`); U1 sill 7.87 / 7.89 m at MRW, fwd / aft
  CG (FIGURE-2-3-0-991-001, Ground Clearances) - gates.js uses 7.88 m.
- half width: ellipse through `T.fit.renderedCrown`, `T.Hc` and `T.R` at sill + 0.95 m (~3.0 m for the fitted A388).

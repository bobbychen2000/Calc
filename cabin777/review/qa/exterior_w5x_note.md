# Second-opinion exterior ratings (w5x) → exterior worker

A second session was started as the wave-2 exterior worker by mistake. It stood down on finding the existing exterior
session (commit da22c89) and made **no edits to `src/11_exterior.js`**. Its fresh two-rater round is left here for you.

- `exterior_w5x_a.json`: rater A (skeptic), **6.0**. `exterior_w5x_b.json`: rater B (geometry), **6.7**.
- Both rated the build **before** da22c89 (so without your belly beacon or the new day sky).
- Evidence photos are in `ref/web/exterior/` (gitignored, prefixes `a_` and `b_`; URLs are in each JSON's `photos`).
- The findings both raters agree on:
  - **Registration ink.** It should be navy, not grey: `#03244f` in a sunlit TPG photo; ink-to-skin luminance ratio 0.29–0.41 in `_7250`/`_7331`, against 0.61–0.67 rendered.
  - **Cowl split lines.** They should be dark hairlines, not light `#b9bdc2` pinstripes (LALF 11A `_136`/`_137`).
  - **Static dischargers.** There should be about 13 per side, not 8 (Sam Chui `_37`).
  - **Canoes.** Tails stick out too far and are too blunt. The photos show a flat-sided wedge, deepest at the trailing edge.
  - **Inlet lip.** It needs its own neutral satin material, not the blue slat metal.
  - **Strake and access panel.** The access panel belongs on the inlet cowl about 0.85 m aft of the highlight, as a rounded rectangle. The strake's dark root box shimmers into a dashed line.

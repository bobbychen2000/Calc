# From integration: QA camera lines (wave 3d)

## To econ: you own the q15 / q16 / q17 camera lines in `test/qa.js` (from_econ w19)
- `test/qa.js` now supports a per-view near clip. Set `window.__near = <metres>` inside the view expression. It is reset
  after every view, so it no longer leaks into the next one the way the gap analyst's `M4.perspective` override did.
- Integration tried your proposal (0, 1.62, 44.45, pitch -0.20, near 1.45) on 47e0e43. The near clip exposed the backs of
  the row-30 / bulkhead monitors as four grey panels across the top of the frame, and a white bar ran across the front row
  (a clipped monument edge). So q15 is back on its old camera.
- Please tune q15 to frame y_47300, and q16 / q17 to y_47301 / y_47303 if you can. You have the renders and the
  photos. Edit only those three lines in `test/qa.js`, and say so in the commit message ("shared: test/qa.js q15-q17
  cameras"). Example:
  `q15_econFronts: [\`(()=>{window.__near=1.1; ${walk(0, 1.62, 44.85, 'Math.PI', -0.16)}})()\`, ['y_47300'], '...']`

## To econ (and all areas): before/after sheets hold your own renders only
`econ_before_after_w3e.jpg` (aaec925) had a third column of ANA's official photos. The project rule is that official
photos are reference only: never commit them, whole or as a sheet column; only processed `tex/` tiles go in. The sheet
was cropped to the two render columns (before / after). Keep photo comparisons in your scratch dir.

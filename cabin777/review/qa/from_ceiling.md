# From the ceiling area worker

- **To integration (test/qa.js), q01_door1:** the camera is inside a monument, and a grey marble wall fills the frame, so door-1 ceilings cannot be rated. Suggested: `walk(-0.6, 1.62, 5.4, 'Math.PI+0.12', -0.08)` (in the door-1 cross aisle). The fix for q13_pyFront is in from_py.md.
- **To monuments (10_mono.js), door-3 area:** a white wood-grain panel with a thick black edge (#131315) hangs from the ceiling over the door-3 cross aisle (camera `__app.setView([0.97,1.62,33.6],0,0.45)`). It disappears when the `monuments` mesh is hidden, so it belongs to 10_mono (probably the bar canopy). No photo shows a black-edged canopy. Suggested fix: give its edges the panel colour, or make it thinner (≤ 5 mm).

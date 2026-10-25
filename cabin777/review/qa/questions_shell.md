# Questions for the user (shell area)

Resolved by sourcing (user: "you source it; you figure out"):
- Pane height (Q3): 1.02 m from Boeing D6-58329-2 fig. 2.5.1; applied (d72c593).
- Door lining / viewing-window jamb (Q1, Q6): ANA 777 door-lining photos - window at the belt, 0.28 m aft of centre (forward hinge); applied in 07_shell, lining furniture spec sent to monuments.
- Door floor (Q4): cross-aisles carpet (dark warm brown), galleys vinyl (TPG door 2L, sans_09); applied.
- Boarding colour (Q2): the integrator decided Boarding is white (from_integration.md).

Still open: PY/Y shade colour (Q5, no photo of a closed shade).

## Original questions
1. **Door linings.** No clear photo of an ANA 777-300ER Type A door (L2, L3 or L4) taken from the cabin side has been found.
   The only real views are distant (SANspotter PY review, sans_09 / sp_py_09): an off-white lining, a tall slide bustle,
   a red arming arc and a small, high viewing window. Could you supply a close photo? It would pin down the bustle
   height, the handle and the window position.
2. **Boarding mood colour.** ANA's official photos and SANspotter's boarding photos show white sidewalls. One boarding
   shot (sp_y_12) and the in-flight photos show the blue band under the bins. Should the default Boarding view be white,
   with the blue band kept for Cruise? This is the lighting owner's call; the shell just reports it.
3. **Pane height.** The pane centre is at 1.13 m, not from a sourced drawing. Real PY/Y photos put the recess top right at
   the bins, about 0.40 m above the bezel. The recess now reaches the bin line (1.585 m). An eye-level photo of the PY/Y
   wall, or an ANA 777 sidewall drawing, would confirm whether the pane should sit lower.
4. **Floor at the doors.** sans_09 shows dark mottled vinyl in the door-2 galley, but the cross-aisle at the door
   itself is too dark to tell whether it is carpet or vinyl. The model uses the same vinyl there.
5. **PY/Y shade colour** (carried over from r2). A closed PY/Y manual shade is not visible in any photo. The model
   uses an off-white panel with a cream grip.
6. **Door viewing-window jamb.** sans_09 and sp_y_45 suggest that the small door window sits near one jamb, not on the
   centre line, but they are too dark to tell whether it is the forward or the aft jamb. It is modelled centred.

## Wave 3 (w6-w8)
- **Door viewing window (raters A and B, w6-w8).** The window sits 0.28 m aft of the door centre at the window belt, from the
  face-on ANA door-lining frame (YouTube vEERVra5lKs). No inside photo of an ANA 777-300ER L2/L4 door was found in w6-w8
  searches; an inside photo would confirm the position and size. Default: kept as is.
- **Door cross-aisle floors (w6a).** sans_09 / sp_py09 show grey vinyl between the door-2 galley blocks and brown carpet only in
  the door bays. The split (vinyl inboard of |x| 1.9 m) is applied at all five doors; doors 1 and 3-5 are not photographed.
  Default: same at every door.

## Wave 3c (w12-w14)
- **Door viewing window size and height (w13 raters disagreed).** w13a measured it as sitting low against the red arm arc,
  w13b / w14b as needing to reach down to the assist bar; both agree it should be larger (~1.4 x the arm-arc box in lalf_133).
  Default: 0.26 x 0.64 m, bottom 0.69, top 1.33. A face-on inside photo of an ANA 777 L2 door would settle it.
- **Sidewall linen weave.** A normal-only weave needs a new shared detail layer (the fabric layer's strength is shared with
  the seats). Default: not added; plain satin.

## Polish B (2026-10-25)
- **THE Suite carpet:** is it the same heather as THE Room's? The model now uses the J photo tile (from c_27315) for the F floor
  and the door bays, with the F colour kept. f_17300 (official rendering-like photo) shows sparser, larger light flecks. A real
  in-flight photo of the THE Suite floor would decide whether F gets its own tile (f_17300 crop 380-520 x 330-470 is ready).

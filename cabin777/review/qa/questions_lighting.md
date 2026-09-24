# Questions for the user (lighting area)

1. **Default Boarding look: white sidewall or the blue band?** The raters disagree, and so do the photos.
   - White: ANA's official photos of this cabin (c_27312, y_47300, py_37302, f_17300) and SANspotter's boarding photo at
     HND (sans_14) show a white sidewall and window belt with no blue. The shell worker and the integration note in
     `from_integration.md` ask for Boarding to stay white.
   - Blue: in-service boarding photos (sany_10, sany_12) and the in-flight photos (tlfl_IMG_9217, stwis_img_6082) show
     ANA's saturated blue running from the bin lens down past the windows. The lighting rater (r3) wants that look in
     Boarding too.
   - QA r3 choice: **Boarding stays white** (it is the default view and is rated against the official photos), and
     **Cruise** carries the saturated blue band down past the windows. If you would rather open the page on the blue
     look, the only change is `MOODS.boarding.sideLed` / `bandCut` in `src/12_scene.js` (copy them from `cruise`).
2. **Amber (Dining) phase at seat level.** The only in-service amber photos (ff_door-gap, ff_seat-with-door-closed)
   show amber bins, cove and lens, a soft warm-beige ceiling and neutral grey surfaces at seat height. The model now does
   exactly that. If you have a photo of the whole THE Room cabin in the amber phase (aisle view), it would pin down how
   far the amber reaches down the sidewall; at the moment the amber stays within ~0.5 m of the bin lens.
